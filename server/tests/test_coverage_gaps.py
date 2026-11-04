"""Bo sung test cho cac endpoint ban goc chua co test (hoac chi test nhanh bi tu choi):
PATCH /units, GET+DELETE /staff, PATCH /locations, /parents (danh sach, sua, go lien ket,
phu huynh xem con va chuyen can cua con), GET /classes/{id}, PATCH /students/{id},
DELETE /classes/{id}, DELETE /rooms/{id}. Do do phu bang server/tools/route_coverage_plugin.py.
"""
from datetime import date

import pytest

from app.core.security import hash_password
from app.db import models
from tests.conftest import auth_headers, login


@pytest.fixture()
def admin_h(client, seed):
    return auth_headers(login(client, "admin@test.local", "admin123"))


def _user(db, email, role, password="secret123"):
    user = models.User(email=email, password_hash=hash_password(password), role=role,
                       full_name=email.split("@")[0])
    db.add(user)
    db.flush()
    return user


def _parent_of(db, student_id, email="ph@test.local"):
    parent = models.Parent(user_id=_user(db, email, "parent", "ph123456").id, phone="0900")
    db.add(parent)
    db.flush()
    db.add(models.ParentStudent(parent_id=parent.id, student_id=student_id))
    db.commit()
    return parent


# ---------------- PH2: don vi, can bo, dia diem, phong ----------------

def test_update_unit_renames_but_keeps_type(client, db_session, admin_h):
    unit = models.Unit(code="K-A", name="Khoa A", type="faculty")
    other = models.Unit(code="K-B", name="Khoa B", type="faculty")
    db_session.add_all([unit, other])
    db_session.commit()

    r = client.patch(f"/units/{unit.id}", json={"name": "Khoa A moi", "type": "board"}, headers=admin_h)
    assert r.status_code == 200
    assert r.json()["name"] == "Khoa A moi" and r.json()["type"] == "faculty"

    r = client.patch(f"/units/{unit.id}", json={"code": "K-B"}, headers=admin_h)
    assert r.status_code == 400 and r.json()["detail"] == "Ma don vi da ton tai"
    assert client.patch("/units/999999", json={"name": "x"}, headers=admin_h).status_code == 404


def test_list_and_delete_staff(client, db_session, admin_h):
    unit = models.Unit(code="P-DT", name="Phong Dao tao", type="training")
    db_session.add(unit)
    db_session.flush()
    keep = _user(db_session, "dt.a@test.local", "training_office")
    gone = _user(db_session, "dt.b@test.local", "training_office")
    staff_keep = models.Staff(user_id=keep.id, unit_id=unit.id, position="CV")
    staff_gone = models.Staff(user_id=gone.id, unit_id=unit.id, position="CV")
    db_session.add_all([staff_keep, staff_gone])
    db_session.commit()

    r = client.get("/staff", params={"q": "dt.", "limit": 1}, headers=admin_h)
    assert r.status_code == 200 and r.headers["X-Total-Count"] == "2" and len(r.json()) == 1

    r = client.delete(f"/staff/{staff_gone.id}", headers=admin_h)
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert db_session.get(models.User, gone.id) is None

    # Can bo da tung sua diem danh: giu lai tai khoan de doi chieu.
    session = models.AttendanceSession(schedule_id=db_session.query(models.Schedule).first().id,
                                       session_date=date(2026, 1, 5), status="closed")
    db_session.add(session)
    db_session.flush()
    student_id = db_session.query(models.Student).first().id
    record = models.AttendanceRecord(session_id=session.id, student_id=student_id, status="absent")
    db_session.add(record)
    db_session.flush()
    db_session.add(models.AttendanceAudit(record_id=record.id, changed_by=keep.id,
                                          old_status="absent", new_status="excused", reason="don"))
    db_session.commit()
    r = client.delete(f"/staff/{staff_keep.id}", headers=admin_h)
    assert r.status_code == 409 and r.json()["code"] == "conflict"
    assert client.delete("/staff/999999", headers=admin_h).status_code == 404


def test_update_location_and_single_default(client, db_session, admin_h):
    a = models.Location(code="CS-A", name="Co so A", latitude=16.0, longitude=108.2, is_default=True)
    b = models.Location(code="CS-B", name="Co so B", latitude=16.1, longitude=108.3)
    db_session.add_all([a, b])
    db_session.commit()

    r = client.patch(f"/locations/{b.id}", json={"is_default": True, "radius_m": 200}, headers=admin_h)
    assert r.status_code == 200 and r.json()["is_default"] is True and r.json()["radius_m"] == 200
    db_session.refresh(a)
    assert a.is_default is False

    assert client.patch(f"/locations/{b.id}", json={"code": "CS-A"}, headers=admin_h).status_code == 400
    assert client.patch(f"/locations/{b.id}", json={"radius_m": 5}, headers=admin_h).status_code == 422
    assert client.patch("/locations/999999", json={"name": "x"}, headers=admin_h).status_code == 404


def test_delete_unused_room(client, db_session, admin_h):
    loc = models.Location(code="CS-R", name="Khu R", latitude=16.0, longitude=108.2)
    db_session.add(loc)
    db_session.flush()
    room = models.Room(code="R-1", name="Phong R1", location_id=loc.id)
    db_session.add(room)
    db_session.commit()
    assert client.delete(f"/rooms/{room.id}", headers=admin_h).json() == {"ok": True}
    assert client.delete(f"/rooms/{room.id}", headers=admin_h).status_code == 404


# ---------------- PH3: lop hoc phan ----------------

def test_get_class_detail_and_delete_empty_class(client, seed, admin_h):
    r = client.get(f"/classes/{seed['class1_id']}", headers=admin_h)
    assert r.status_code == 200
    assert r.json()["class_code"] == "C1" and r.json()["student_count"] == 1

    gv1 = auth_headers(login(client, "gv1@test.local", "gv123"))
    assert client.get(f"/classes/{seed['class1_id']}", headers=gv1).status_code == 200

    created = client.post("/classes", json={"class_code": "C9", "subject_name": "Mon 9",
                                            "lecturer_id": r.json()["lecturer_id"],
                                            "semester": "2026.1"}, headers=admin_h).json()
    r = client.delete(f"/classes/{created['id']}", headers=admin_h)
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert client.get(f"/classes/{created['id']}", headers=admin_h).status_code == 404


# ---------------- PH4: sinh vien, phu huynh ----------------

def test_update_student_profile(client, seed, admin_h):
    r = client.patch(f"/students/{seed['sv1_id']}",
                     json={"full_name": "SV Mot Moi", "major": "KTPM", "cohort": 2025}, headers=admin_h)
    assert r.status_code == 200
    body = r.json()
    assert (body["full_name"], body["major"], body["cohort"]) == ("SV Mot Moi", "KTPM", 2025)


def test_list_and_update_parents(client, db_session, seed, admin_h):
    p1 = _parent_of(db_session, seed["sv1_id"], "ph.an@test.local")
    _parent_of(db_session, seed["sv2_id"], "ph.binh@test.local")

    r = client.get("/parents", params={"q": "ph.", "limit": 1}, headers=admin_h)
    assert r.status_code == 200 and r.headers["X-Total-Count"] == "2" and len(r.json()) == 1
    r = client.get("/parents", params={"q": "an@"}, headers=admin_h)
    assert [p["email"] for p in r.json()] == ["ph.an@test.local"]
    assert r.json()[0]["child_count"] == 1

    r = client.patch(f"/parents/{p1.id}", json={"full_name": "Phu huynh An", "phone": "0911"},
                     headers=admin_h)
    assert r.status_code == 200
    assert (r.json()["full_name"], r.json()["phone"]) == ("Phu huynh An", "0911")

    # Giang vien khong xem duoc danh sach phu huynh.
    gv1 = auth_headers(login(client, "gv1@test.local", "gv123"))
    assert client.get("/parents", headers=gv1).status_code == 403


def test_unlink_child(client, db_session, seed, admin_h):
    parent = _parent_of(db_session, seed["sv1_id"])
    r = client.delete(f"/parents/{parent.id}/children/{seed['sv1_id']}", headers=admin_h)
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert client.get(f"/parents/{parent.id}/children", headers=admin_h).json() == []
    r = client.delete(f"/parents/{parent.id}/children/{seed['sv1_id']}", headers=admin_h)
    assert r.status_code == 404 and r.json()["detail"] == "Chua lien ket voi sinh vien nay"


# ---------------- PH8: phu huynh xem con ----------------

def test_parent_sees_children_and_child_attendance(client, db_session, seed):
    _parent_of(db_session, seed["sv1_id"])
    session = models.AttendanceSession(schedule_id=seed["schedule1_id"],
                                       session_date=date(2026, 1, 5), status="closed")
    db_session.add(session)
    db_session.flush()
    db_session.add(models.AttendanceRecord(session_id=session.id, student_id=seed["sv1_id"],
                                           status="absent"))
    db_session.commit()
    headers = auth_headers(login(client, "ph@test.local", "ph123456"))

    r = client.get("/parents/me/children", headers=headers)
    assert r.status_code == 200
    children = r.json()
    assert [c["student_code"] for c in children] == ["SV0001"]
    assert [c["class_code"] for c in children[0]["classes"]] == ["C1"]

    r = client.get(f"/parents/me/children/{seed['sv1_id']}/attendance", headers=headers)
    assert r.status_code == 200
    [cls] = r.json()
    assert cls["class_code"] == "C1" and cls["absent"] == 1 and cls["total_sessions"] == 1
    assert cls["warning"] is True and cls["sessions"][0]["status"] == "absent"

    # Khong phai con cua minh.
    r = client.get(f"/parents/me/children/{seed['sv2_id']}/attendance", headers=headers)
    assert r.status_code == 403
    # SV khong goi duoc API cua phu huynh.
    sv1 = auth_headers(login(client, "sv1@test.local", "sv123"))
    assert client.get("/parents/me/children", headers=sv1).status_code == 403

"""Nghiep vu moi theo gop y (11/2026):
- don xin phep vang: SV nop -> GV lop / Lanh dao Khoa duyet hoac tu choi (bat buoc ly do khong hop le)
  -> he thong gui ket qua cho SV -> SV xac nhan; don duoc duyet => buoi do tinh vang co phep;
- canh bao vang sau thong ke (dong phien) gui cho SV va phu huynh;
- bo han ma QR;
- chuan hoa schedules.room (khong luu lai ma phong khi da chon phong trong danh muc).
"""
from datetime import date, datetime, timedelta

import pytest

from app.core.security import hash_password
from app.db import models
from tests.conftest import auth_headers, login


# ---------------------------------------------------------------- tien ich
@pytest.fixture()
def sv1(client, seed):
    return auth_headers(login(client, "sv1@test.local", "sv123"))


@pytest.fixture()
def gv1(client, seed):
    return auth_headers(login(client, "gv1@test.local", "gv123"))


@pytest.fixture()
def gv2(client, seed):
    return auth_headers(login(client, "gv2@test.local", "gv123"))


def _staff(db, email, role, unit):
    user = models.User(email=email, password_hash=hash_password("staff123"), role=role, full_name=email)
    db.add(user)
    db.flush()
    db.add(models.Staff(user_id=user.id, unit_id=unit.id, position="Can bo"))
    return user


@pytest.fixture()
def faculty(db_session, seed):
    """Khoa CNTT quan ly lop 1 va SV1; Khoa KT khong lien quan; Lanh dao Khoa moi ben; can bo P.CTSV."""
    db = db_session
    cntt = models.Unit(code="K-CNTT-L", name="Khoa CNTT", type="faculty")
    kt = models.Unit(code="K-KT-L", name="Khoa KT", type="faculty")
    ctsv = models.Unit(code="P-CTSV-L", name="P.CTSV", type="student_affairs")
    db.add_all([cntt, kt, ctsv])
    db.flush()
    _staff(db, "ldk.cntt.l@test.local", "faculty_leader", cntt)
    _staff(db, "ldk.kt.l@test.local", "faculty_leader", kt)
    _staff(db, "ctsv.l@test.local", "student_affairs", ctsv)
    db.get(models.Class, seed["class1_id"]).faculty_id = cntt.id
    db.get(models.Student, seed["sv1_id"]).faculty_id = cntt.id
    db.commit()
    return {"cntt": cntt.id}


def _h(client, email):
    return auth_headers(login(client, email, "staff123"))


def _next_lesson_day(weekday: int, weeks_ahead: int = 1) -> date:
    today = date.today()
    return today + timedelta(days=(weekday - today.weekday()) % 7 + 7 * weeks_ahead)


def _leave(client, headers, schedule_id, day, reason="Om, co giay kham"):
    return client.post("/leave-requests", json={"schedule_id": schedule_id, "absence_date": str(day),
                                                 "reason": reason}, headers=headers)


def _kinds(db, user_email):
    user = db.query(models.User).filter_by(email=user_email).one()
    return [n.kind for n in db.query(models.Notification).filter_by(user_id=user.id)
            .order_by(models.Notification.id).all()]


# ---------------------------------------------------------------- nop don
def test_student_submits_leave_and_lecturer_is_notified(client, db_session, seed, sv1):
    weekday = db_session.get(models.Schedule, seed["schedule1_id"]).weekday
    resp = _leave(client, sv1, seed["schedule1_id"], _next_lesson_day(weekday))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "pending" and body["class_code"] == "C1" and body["student_code"] == "SV0001"
    assert _kinds(db_session, "gv1@test.local") == ["leave_submitted"]


def test_leave_validation_rules(client, db_session, seed, sv1):
    schedule = db_session.get(models.Schedule, seed["schedule1_id"])
    good_day = _next_lesson_day(schedule.weekday)
    assert _leave(client, sv1, seed["schedule1_id"], good_day + timedelta(days=1)).status_code == 400  # sai thu
    assert _leave(client, sv1, seed["schedule2_id"], _next_lesson_day(
        db_session.get(models.Schedule, seed["schedule2_id"]).weekday)).status_code == 403            # khong ghi danh
    assert _leave(client, sv1, seed["schedule1_id"], good_day - timedelta(days=28)).status_code == 400  # qua cu
    assert _leave(client, sv1, seed["schedule1_id"], good_day, reason="   ").status_code == 400         # thieu ly do
    assert _leave(client, sv1, seed["schedule1_id"], good_day).status_code == 200
    assert _leave(client, sv1, seed["schedule1_id"], good_day).status_code == 400                       # trung
    assert _leave(client, sv1, 999999, good_day).status_code == 404


def test_cannot_request_leave_for_lesson_already_attended(client, db_session, seed, sv1, gv1):
    session_id = client.post("/sessions", json={"schedule_id": seed["schedule1_id"],
                                                "session_date": str(date.today())}, headers=gv1).json()["id"]
    assert client.post(f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
                       headers=gv1).status_code == 200
    assert _leave(client, sv1, seed["schedule1_id"], date.today()).status_code == 400


# ---------------------------------------------------------------- duyet / tu choi
def test_only_class_lecturer_or_faculty_leader_reviews(client, db_session, seed, sv1, gv1, gv2, faculty):
    weekday = db_session.get(models.Schedule, seed["schedule1_id"]).weekday
    leave_id = _leave(client, sv1, seed["schedule1_id"], _next_lesson_day(weekday)).json()["id"]
    admin = auth_headers(login(client, "admin@test.local", "admin123"))
    ctsv = _h(client, "ctsv.l@test.local")
    for headers in (admin, ctsv, sv1):                                   # khong co vai tro duyet don
        assert client.patch(f"/leave-requests/{leave_id}/approve", json={}, headers=headers).status_code == 403
    assert client.patch(f"/leave-requests/{leave_id}/approve", json={}, headers=gv2).status_code == 403
    assert client.patch(f"/leave-requests/{leave_id}/approve", json={},
                        headers=_h(client, "ldk.kt.l@test.local")).status_code == 403    # Khoa khac
    # Admin, P.CTSV van xem duoc danh sach; GV2 khong thay don cua lop GV1.
    assert len(client.get("/leave-requests", headers=admin).json()) == 1
    assert len(client.get("/leave-requests", headers=ctsv).json()) == 1
    assert client.get("/leave-requests", headers=gv2).json() == []
    resp = client.patch(f"/leave-requests/{leave_id}/approve", json={"note": "Dong y"},
                        headers=_h(client, "ldk.cntt.l@test.local"))
    assert resp.status_code == 200 and resp.json()["status"] == "approved"
    assert client.patch(f"/leave-requests/{leave_id}/reject", json={"reason": "x"}, headers=gv1).status_code == 400


def test_reject_requires_invalid_reason_and_student_confirms(client, db_session, seed, sv1, gv1):
    weekday = db_session.get(models.Schedule, seed["schedule1_id"]).weekday
    leave_id = _leave(client, sv1, seed["schedule1_id"], _next_lesson_day(weekday)).json()["id"]
    assert client.post(f"/leave-requests/{leave_id}/acknowledge", headers=sv1).status_code == 400  # chua duyet
    assert client.patch(f"/leave-requests/{leave_id}/reject", json={"reason": " "}, headers=gv1).status_code == 400
    resp = client.patch(f"/leave-requests/{leave_id}/reject", json={"reason": "Khong co giay to"}, headers=gv1)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected" and resp.json()["review_note"] == "Khong co giay to"

    inbox = client.get("/notifications", headers=sv1).json()
    assert inbox[0]["kind"] == "leave_rejected" and "Khong co giay to" in inbox[0]["body"]
    acked = client.post(f"/leave-requests/{leave_id}/acknowledge", headers=sv1)
    assert acked.status_code == 200 and acked.json()["student_ack_at"] is not None
    sv2 = auth_headers(login(client, "sv2@test.local", "sv123"))
    assert client.post(f"/leave-requests/{leave_id}/acknowledge", headers=sv2).status_code == 404
    assert [r["id"] for r in client.get("/leave-requests", headers=sv1).json()] == [leave_id]
    assert client.get("/leave-requests", headers=sv2).json() == []


# ---------------------------------------------------------------- tac dong toi diem danh
def test_approved_leave_makes_absence_excused_when_session_closes(client, db_session, seed, sv1, gv1):
    leave_id = _leave(client, sv1, seed["schedule1_id"], date.today()).json()["id"]
    assert client.patch(f"/leave-requests/{leave_id}/approve", json={}, headers=gv1).status_code == 200
    session_id = client.post("/sessions", json={"schedule_id": seed["schedule1_id"],
                                                "session_date": str(date.today())}, headers=gv1).json()["id"]
    closed = client.patch(f"/sessions/{session_id}/close", headers=gv1).json()
    assert closed["absent"] == 0 and closed["excused"] == 1
    record = db_session.query(models.AttendanceRecord).filter_by(session_id=session_id).one()
    assert record.status == "excused"
    assert client.get("/leave-requests", headers=sv1).json()[0]["attendance_status"] == "excused"


def test_leave_approved_after_close_turns_absent_into_excused(client, db_session, seed, sv1, gv1):
    session_id = client.post("/sessions", json={"schedule_id": seed["schedule1_id"],
                                                "session_date": str(date.today())}, headers=gv1).json()["id"]
    client.patch(f"/sessions/{session_id}/close", headers=gv1)
    record = db_session.query(models.AttendanceRecord).filter_by(session_id=session_id).one()
    assert record.status == "absent"

    leave_id = _leave(client, sv1, seed["schedule1_id"], date.today()).json()["id"]
    assert client.patch(f"/leave-requests/{leave_id}/approve", json={}, headers=gv1).status_code == 200
    db_session.refresh(record)
    assert record.status == "excused"
    audits = client.get(f"/sessions/{session_id}/records/{record.id}/audits", headers=gv1).json()
    assert audits[0]["old_status"] == "absent" and audits[0]["new_status"] == "excused"
    assert f"#{leave_id}" in audits[0]["reason"]


# ---------------------------------------------------------------- canh bao sau thong ke
def test_absence_warning_after_statistics(client, db_session, seed, gv1):
    parent_user = models.User(email="ph.warn@test.local", password_hash=hash_password("ph123"),
                              role="parent", full_name="PH")
    db_session.add(parent_user)
    db_session.flush()
    parent = models.Parent(user_id=parent_user.id)
    db_session.add(parent)
    db_session.flush()
    db_session.add(models.ParentStudent(parent_id=parent.id, student_id=seed["sv1_id"]))
    db_session.commit()

    session_id = client.post("/sessions", json={"schedule_id": seed["schedule1_id"],
                                                "session_date": str(date.today())}, headers=gv1).json()["id"]
    closed = client.patch(f"/sessions/{session_id}/close", headers=gv1).json()
    assert [r["student_code"] for r in closed["newly_warned"]] == ["SV0001"]   # vang 1/1 buoi = 100%
    assert _kinds(db_session, "sv1@test.local") == ["absence_warning"]
    assert _kinds(db_session, "ph.warn@test.local") == ["attendance_absent", "absence_warning"]

    # Phien sau, SV van vuot nguong nhung KHONG phai "vua" vuot => khong bao lai.
    old = models.AttendanceSession(schedule_id=seed["schedule1_id"], status="open",
                                   session_date=date.today() - timedelta(days=7))
    db_session.add(old)
    db_session.commit()
    client.patch(f"/sessions/{old.id}/close", headers=gv1)
    assert _kinds(db_session, "sv1@test.local") == ["absence_warning"]


# ---------------------------------------------------------------- bo ma QR
def test_qr_endpoints_and_fields_are_gone(client, seed, gv1):
    session = client.post("/sessions", json={"schedule_id": seed["schedule1_id"],
                                             "session_date": str(date.today())}, headers=gv1).json()
    assert "require_qr" not in session
    assert client.get(f"/sessions/{session['id']}/checkin-code", headers=gv1).status_code == 404
    assert client.patch(f"/sessions/{session['id']}", json={"require_qr": True}, headers=gv1).status_code == 405
    sv = auth_headers(login(client, "sv1@test.local", "sv123"))
    assert set(client.get(f"/sessions/{session['id']}/checkin-info", headers=sv).json()) == {"session_id", "room"}


# ---------------------------------------------------------------- chuan hoa schedules.room
def test_schedule_room_is_not_duplicated_when_room_selected(client, db_session, seed):
    location = models.Location(code="CS1", name="Co so 1", latitude=16.0, longitude=108.2, radius_m=150)
    db_session.add(location)
    db_session.flush()
    room = models.Room(code="E2-101", name="Phong E2-101", location_id=location.id)
    db_session.add(room)
    db_session.commit()
    admin = auth_headers(login(client, "admin@test.local", "admin123"))

    resp = client.post("/classes/schedules", json={
        "class_id": seed["class2_id"], "weekday": 3, "room_id": room.id, "room": "E2-101",
        "start_time": "07:00:00", "end_time": "09:00:00"}, headers=admin)
    assert resp.status_code == 200, resp.text
    assert resp.json()["room"] == "E2-101"                                  # API giu nhu cu
    assert db_session.get(models.Schedule, resp.json()["id"]).room is None  # CSDL khong luu ban sao

    custom = client.post("/classes/schedules", json={
        "class_id": seed["class2_id"], "weekday": 4, "room": "Hoi truong A",
        "start_time": "07:00:00", "end_time": "09:00:00"}, headers=admin)
    assert custom.status_code == 200 and custom.json()["room"] == "Hoi truong A"
    # Khong chon phong, khong nhap ten phong: schema chan ngay (422) nhu truoc.
    assert client.post("/classes/schedules", json={
        "class_id": seed["class2_id"], "weekday": 5,
        "start_time": "07:00:00", "end_time": "09:00:00"}, headers=admin).status_code == 422
    # Doi sang chon phong => xoa ten tu nhap.
    moved = client.patch(f"/classes/schedules/{custom.json()['id']}", json={"room_id": room.id, "weekday": 6},
                         headers=admin)
    assert moved.status_code == 200 and moved.json()["room"] == "E2-101"
    assert db_session.get(models.Schedule, custom.json()["id"]).room is None

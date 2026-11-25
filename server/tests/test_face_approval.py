"""Test luong duyet khuon mat: embedding moi la 'pending', chi 'approved' duoc dung
de nhan dien/kiem tra trung, va cac endpoint GET /faces/pending, PATCH approve/reject."""
import cv2
import numpy as np
import pytest

from app.db import models
from app.services import antispoof_service, face_service
from tests.conftest import auth_headers, login


class _FakeFace:
    def __init__(self, bbox, embedding):
        self.bbox = bbox
        self.normed_embedding = embedding


class _FakeEngine:
    def __init__(self, face):
        self._face = face

    def get(self, img):
        return [self._face]


def _unit_norm_embedding(seed_value):
    rng = np.random.RandomState(seed_value)
    emb = rng.rand(512).astype(np.float32)
    return emb / np.linalg.norm(emb)


def _tiny_jpeg_bytes():
    return cv2.imencode(".jpg", np.zeros((200, 200, 3), dtype=np.uint8))[1].tobytes()


def _mock_engine_for_enroll(monkeypatch, embedding):
    """Bypass detect/quality/liveness de test rieng logic pending/duplicate cua enroll_face."""
    bbox = np.array([0, 0, 200, 200], dtype=np.float32)
    fake_face = _FakeFace(bbox, embedding)
    monkeypatch.setattr(face_service, "get_engine", lambda: _FakeEngine(fake_face))
    monkeypatch.setattr(face_service, "_check_quality", lambda img, face: None)
    monkeypatch.setattr(antispoof_service, "check_liveness", lambda img, bbox: (True, 0.95))


# ---------------- Muc service: face_service ----------------

def test_new_embedding_defaults_to_pending(db_session, seed, monkeypatch):
    _mock_engine_for_enroll(monkeypatch, _unit_norm_embedding(1))
    ok, _msg = face_service.enroll_face(db_session, seed["sv1_id"], _tiny_jpeg_bytes())
    assert ok is True

    emb = db_session.query(models.FaceEmbedding).filter_by(student_id=seed["sv1_id"]).first()
    assert emb.status == "pending"


def test_recognize_ignores_pending_embedding(db_session, seed, monkeypatch):
    embedding = _unit_norm_embedding(2)
    db_session.add(models.FaceEmbedding(student_id=seed["sv1_id"], embedding=embedding.tolist(),
                                        status="pending"))
    db_session.commit()

    bbox = np.array([0, 0, 20, 20], dtype=np.float32)
    monkeypatch.setattr(face_service, "get_engine",
                        lambda: _FakeEngine(_FakeFace(bbox, embedding)))
    monkeypatch.setattr(antispoof_service, "check_liveness", lambda img, bbox: (True, 0.95))

    results = face_service.recognize_frame(db_session, _tiny_jpeg_bytes(), seed["class1_id"])
    assert results[0]["student_id"] is None  # pending -> khong duoc dung de nhan dien


def test_duplicate_check_ignores_other_students_pending_embedding(db_session, seed, monkeypatch):
    """SV2 co embedding pending giong het embedding SV1 dang dang ky - khong bi chan
    vi ban ghi trung do chua duoc duyet, chua du tin cay de dung lam can cu."""
    embedding = _unit_norm_embedding(3)
    db_session.add(models.FaceEmbedding(student_id=seed["sv2_id"], embedding=embedding.tolist(),
                                        status="pending"))
    db_session.commit()

    _mock_engine_for_enroll(monkeypatch, embedding)
    ok, _msg = face_service.enroll_face(db_session, seed["sv1_id"], _tiny_jpeg_bytes())
    assert ok is True


def test_duplicate_check_flags_against_approved_embedding(db_session, seed, monkeypatch):
    embedding = _unit_norm_embedding(4)
    db_session.add(models.FaceEmbedding(student_id=seed["sv2_id"], embedding=embedding.tolist(),
                                        status="approved"))
    db_session.commit()

    _mock_engine_for_enroll(monkeypatch, embedding)
    ok, msg = face_service.enroll_face(db_session, seed["sv1_id"], _tiny_jpeg_bytes())
    assert ok is False
    assert "giong" in msg.lower() or "trung" in msg.lower()


# ---------------- Muc endpoint: /faces/pending, /faces/{id}/approve|reject ----------------

def _add_pending_embedding(db_session, student_id, seed_value):
    emb = models.FaceEmbedding(student_id=student_id,
                               embedding=_unit_norm_embedding(seed_value).tolist(),
                               status="pending")
    db_session.add(emb)
    db_session.commit()
    db_session.refresh(emb)
    return emb


def test_list_pending_requires_admin(client, seed, db_session):
    _add_pending_embedding(db_session, seed["sv1_id"], 10)
    gv_token = login(client, "gv1@test.local", "gv123")
    resp = client.get("/faces/pending", headers=auth_headers(gv_token))
    assert resp.status_code == 403


def test_list_pending_returns_student_info(client, seed, db_session, ctsv_headers):
    _add_pending_embedding(db_session, seed["sv1_id"], 11)
    resp = client.get("/faces/pending", headers=ctsv_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["student_code"] == "SV0001"
    assert body[0]["duplicate_warning"] is False


def test_list_pending_flags_duplicate_with_approved_embedding(client, seed, db_session, ctsv_headers):
    embedding = _unit_norm_embedding(12)
    db_session.add(models.FaceEmbedding(student_id=seed["sv2_id"], embedding=embedding.tolist(),
                                        status="approved"))
    db_session.add(models.FaceEmbedding(student_id=seed["sv1_id"], embedding=embedding.tolist(),
                                        status="pending"))
    db_session.commit()

    resp = client.get("/faces/pending", headers=ctsv_headers)
    body = resp.json()
    assert body[0]["duplicate_warning"] is True
    assert body[0]["duplicate_student_code"] == "SV0002"


def test_approve_face_sets_status(client, seed, db_session, ctsv_headers):
    emb = _add_pending_embedding(db_session, seed["sv1_id"], 13)
    resp = client.patch(f"/faces/{emb.id}/approve", headers=ctsv_headers)
    assert resp.status_code == 200

    db_session.refresh(emb)
    assert emb.status == "approved"
    assert emb.reviewed_by is not None and emb.reviewed_at is not None


def test_reject_face_requires_reason(client, seed, db_session, ctsv_headers):
    emb = _add_pending_embedding(db_session, seed["sv1_id"], 14)
    resp = client.patch(f"/faces/{emb.id}/reject", json={"reason": ""}, headers=ctsv_headers)
    assert resp.status_code == 400


def test_reject_face_stores_reason(client, seed, db_session, ctsv_headers):
    emb = _add_pending_embedding(db_session, seed["sv1_id"], 15)
    resp = client.patch(f"/faces/{emb.id}/reject", json={"reason": "Anh mo, khong ro mat"},
                        headers=ctsv_headers)
    assert resp.status_code == 200

    db_session.refresh(emb)
    assert emb.status == "rejected"
    assert emb.reject_reason == "Anh mo, khong ro mat"


def test_approve_reject_requires_admin(client, seed, db_session):
    emb = _add_pending_embedding(db_session, seed["sv1_id"], 16)
    gv_token = login(client, "gv1@test.local", "gv123")
    resp = client.patch(f"/faces/{emb.id}/approve", headers=auth_headers(gv_token))
    assert resp.status_code == 403


# ---------------- Quy trinh duyet moi: chi P.CTSV, gui ket qua cho SV, SV xac nhan ----------------

def test_admin_no_longer_reviews_faces(client, seed, db_session):
    """Gop y nghiep vu: bo quan tri vien khoi viec xet duyet khuon mat."""
    emb = _add_pending_embedding(db_session, seed["sv1_id"], 17)
    admin = auth_headers(login(client, "admin@test.local", "admin123"))
    assert client.get("/faces/pending", headers=admin).status_code == 403
    assert client.patch(f"/faces/{emb.id}/approve", headers=admin).status_code == 403
    assert client.patch(f"/faces/{emb.id}/reject", json={"reason": "x"}, headers=admin).status_code == 403


def test_result_is_sent_to_student_and_student_confirms(client, seed, db_session, ctsv_headers):
    emb = _add_pending_embedding(db_session, seed["sv1_id"], 18)
    sv = auth_headers(login(client, "sv1@test.local", "sv123"))
    # Chua co ket qua thi chua xac nhan duoc.
    assert client.post(f"/faces/mine/{emb.id}/acknowledge", headers=sv).status_code == 400

    assert client.patch(f"/faces/{emb.id}/reject", json={"reason": "Anh nguoc sang"},
                        headers=ctsv_headers).status_code == 200
    inbox = client.get("/notifications", headers=sv).json()
    assert inbox[0]["kind"] == "face_rejected" and "Anh nguoc sang" in inbox[0]["body"]

    mine = client.get("/faces/mine", headers=sv).json()
    assert mine[0]["student_ack_at"] is None and mine[0]["reviewed_at"] is not None
    acked = client.post(f"/faces/mine/{emb.id}/acknowledge", headers=sv)
    assert acked.status_code == 200 and acked.json()["student_ack_at"] is not None
    # SV khac khong xac nhan ho duoc.
    sv2 = auth_headers(login(client, "sv2@test.local", "sv123"))
    assert client.post(f"/faces/mine/{emb.id}/acknowledge", headers=sv2).status_code == 404


def test_decided_face_cannot_be_decided_again(client, seed, db_session, ctsv_headers):
    emb = _add_pending_embedding(db_session, seed["sv1_id"], 19)
    assert client.patch(f"/faces/{emb.id}/approve", headers=ctsv_headers).status_code == 200
    assert client.patch(f"/faces/{emb.id}/reject", json={"reason": "x"},
                        headers=ctsv_headers).status_code == 400
    sv = auth_headers(login(client, "sv1@test.local", "sv123"))
    assert client.get("/notifications", headers=sv).json()[0]["kind"] == "face_approved"

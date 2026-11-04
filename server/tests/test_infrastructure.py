"""Ha tang API sau tai cau truc: versioning, dinh dang loi thong nhat, request id, log, health."""
import logging

from app.core.config import settings

ROOT = "http://testserver"


def _token(client, email="admin@test.local", password="admin123"):
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_root_health_outside_version_prefix(client):
    r = client.get(f"{ROOT}/")
    assert r.status_code == 200
    assert r.json() == {"app": "FAMS", "status": "ok"}


def test_versioned_health_checks_database(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert body["version"] == settings.APP_VERSION


def test_business_endpoints_only_under_version_prefix(client, seed):
    assert settings.API_PREFIX == "/api/v1"
    r = client.post(f"{ROOT}/auth/login", data={"username": "admin@test.local", "password": "admin123"})
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"
    r = client.post(f"{ROOT}/api/v1/auth/login", data={"username": "admin@test.local", "password": "admin123"})
    assert r.status_code == 200


def test_request_id_generated_and_echoed(client):
    r = client.get("/health")
    assert len(r.headers["X-Request-ID"]) >= 8
    r = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert r.headers["X-Request-ID"] == "abc-123"
    # Gia tri la (khoang trang, qua dai) bi thay bang ma moi, khong phan chieu nguyen van.
    r = client.get("/health", headers={"X-Request-ID": "bad id <script>"})
    assert r.headers["X-Request-ID"] != "bad id <script>"


def test_error_format_unauthorized(client):
    r = client.get("/auth/me")
    assert r.status_code == 401
    assert set(r.json()) == {"detail", "code"}
    assert r.json()["code"] == "unauthorized"
    assert "X-Request-ID" in r.headers


def test_error_format_business_errors_keep_detail(client, seed):
    token = _token(client, "sv1@test.local", "sv123")
    r = client.get("/units", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert r.json() == {"detail": "Khong du quyen", "code": "forbidden"}

    admin = _token(client)
    r = client.get("/classes/999999", headers={"Authorization": f"Bearer {admin}"})
    assert r.status_code == 404
    assert r.json() == {"detail": "Lop hoc phan khong ton tai", "code": "not_found"}


def test_validation_error_keeps_field_list(client, seed):
    admin = _token(client)
    r = client.post("/units", json={"code": "X"}, headers={"Authorization": f"Bearer {admin}"})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_error"
    assert isinstance(body["detail"], list) and body["detail"][0]["loc"]


def test_access_log_has_request_id(client, caplog):
    with caplog.at_level(logging.INFO, logger="fams.access"):
        client.get("/health", headers={"X-Request-ID": "log-check-1"})
    lines = [r for r in caplog.records if r.name == "fams.access"]
    assert any("GET /api/v1/health -> 200" in r.getMessage() for r in lines)
    assert any(getattr(r, "request_id", None) == "log-check-1" for r in lines)


def test_openapi_lists_versioned_paths_and_tags(client):
    r = client.get(f"{ROOT}/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    paths = spec["paths"]
    assert "/api/v1/auth/login" in paths and "/api/v1/sessions/{session_id}/self-checkin" in paths
    assert all(p == "/" or p.startswith("/api/v1/") for p in paths)
    assert {t["name"] for t in spec["tags"]} >= {"auth", "attendance", "reports"}
    # Nut Authorize tren Swagger dung dung duong dan dang nhap moi.
    flows = spec["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]
    assert flows["password"]["tokenUrl"] == "/api/v1/auth/login"

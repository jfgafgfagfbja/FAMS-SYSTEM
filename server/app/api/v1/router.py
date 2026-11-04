"""Gom moi controller cua API v1 (gan tien to settings.API_PREFIX trong main.py)."""
from fastapi import APIRouter

from app.api.v1.endpoints import (audit_logs, auth, classes, faces, health, lecturers, locations,
                                  media, notifications, parents, reports, rooms, schedules,
                                  sessions, staff, students, units)

api_router = APIRouter()

for module in (health, auth, units, staff, locations, rooms, lecturers, classes, schedules,
               students, parents, faces, sessions, reports, notifications, audit_logs, media):
    api_router.include_router(module.router)

# Mo ta nhom endpoint tren Swagger UI (/docs).
OPENAPI_TAGS = [
    {"name": "health", "description": "Kiem tra suc khoe dich vu"},
    {"name": "auth", "description": "PH1 - Dang nhap, token, mat khau, thong tin tai khoan"},
    {"name": "units", "description": "PH2 - Don vi (Khoa, phong, ban)"},
    {"name": "staff", "description": "PH2 - Tai khoan can bo"},
    {"name": "locations", "description": "PH2 - Dia diem diem danh (toa do, ban kinh)"},
    {"name": "rooms", "description": "PH2 - Phong hoc"},
    {"name": "lecturers", "description": "PH3 - Giang vien, lich day hom nay"},
    {"name": "classes", "description": "PH3 - Lop hoc phan, ghi danh, lich hoc cua lop"},
    {"name": "schedules", "description": "PH3 - Tra cuu lich, lich tuan"},
    {"name": "students", "description": "PH4 - Sinh vien, dong y sinh trac, chuyen can 1 SV"},
    {"name": "parents", "description": "PH4/PH7/PH8 - Phu huynh, lien ket con, tuy chon thong bao"},
    {"name": "faces", "description": "PH5 - Dang ky, duyet du lieu khuon mat"},
    {"name": "attendance", "description": "PH6 - Phien diem danh, quet camera, tu diem danh, sua ket qua"},
    {"name": "reports", "description": "PH8 - Thong ke, canh bao vang, xuat Excel"},
    {"name": "notifications", "description": "PH7 - Hop thu thong bao"},
    {"name": "audit", "description": "PH9 - Nhat ky he thong"},
    {"name": "media", "description": "Anh bang chung qua URL co chu ky"},
]

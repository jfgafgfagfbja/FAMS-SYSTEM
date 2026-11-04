# Cơ sở dữ liệu

| Tài liệu | Nội dung |
|---|---|
| [../DATABASE_ANALYSIS.md](../DATABASE_ANALYSIS.md) | 21 bảng, ràng buộc, chỉ mục, chuỗi 15 migration, truy vấn trọng yếu, phương án dữ liệu |
| [erd.mermaid](erd.mermaid) | Sơ đồ quan hệ **sinh từ `models.py`** (`scripts/export_erd.py`) — mở bằng trình xem Mermaid |
| [../deployment/BACKUP_RESTORE.md](../deployment/BACKUP_RESTORE.md) | Sao lưu, khôi phục, nhập dữ liệu bản gốc |

Quy tắc thay đổi schema:

1. Sửa `server/app/db/models.py`.
2. `cd server && alembic revision --autogenerate -m "mo ta"` — **đọc lại** tệp sinh ra (Alembic không tự nhận đổi tên cột,
   kiểu `Vector`, chỉ mục dùng `postgresql_using`).
3. `alembic upgrade head` trên DB dev; chạy `pytest tests/test_migrations.py` (đảm bảo migration khớp models).
4. Không xóa cột/bảng đang có dữ liệu trong cùng một lần: thêm mới → chuyển dữ liệu → lần phát hành sau mới xóa.
5. Sao lưu trước khi nâng cấp production (`scripts/backup.sh --prod`); server tự `alembic upgrade head` khi khởi động.
6. Sinh lại sơ đồ: `server/venv/Scripts/python scripts/export_erd.py`.

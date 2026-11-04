# FAMS-SYSTEM — Face Attendance Management System (Client–Server)

Hệ thống quản lý sinh viên tích hợp điểm danh bằng nhận diện khuôn mặt — Trường Đại học Kiến trúc Đà Nẵng.
Đây là bản **tái cấu trúc Client–Server** của dự án FAMS gốc (`D:\FAMS`): giữ nguyên toàn bộ chức năng, nghiệp vụ
và dữ liệu; tách lớp rõ ràng Client ↔ API `/api/v1` ↔ Server (Controller → Service → Repository) ↔ PostgreSQL.
Bản này chạy **song song, độc lập** với bản gốc (cổng, CSDL, container, app id riêng).

```
client/  Flutter (Web, Android, iOS) ── HTTPS/JSON /api/v1 ──►  server/  FastAPI ── SQL ──►  PostgreSQL 16 + pgvector
         giao diện, gọi API                                     nghiệp vụ, phân quyền,         (chỉ server truy cập)
                                                                transaction, nhận diện
```

## Cấu trúc thư mục

```
FAMS-SYSTEM/
├── client/                    Flutter — chỉ giao diện
│   ├── lib/api/               lớp gọi API theo module (mỗi endpoint khai báo một lần)
│   ├── lib/core/              ApiClient (token, tự làm mới, lỗi), cấu hình máy chủ, quyền hiển thị
│   ├── lib/features/          33 trang theo vai trò · lib/widgets/ · lib/models/ · lib/router.dart
│   ├── nginx.conf, Dockerfile bản web + proxy /api/ → server
│   └── .env.example           API_BASE_URL (địa chỉ máy chủ)
├── server/                    FastAPI — toàn bộ nghiệp vụ
│   ├── app/api/v1/endpoints/  17 controller
│   ├── app/services/          nghiệp vụ theo module (+ nhận diện, GPS, mã QR, nhật ký, thông báo)
│   ├── app/repositories/      truy cập dữ liệu
│   ├── app/schemas/ · app/db/ · app/core/ · app/jobs/
│   ├── alembic/               15 migration · tests/ 279 test · tools/
│   └── .env.example
├── docs/                      phân tích, kiến trúc, API, CSDL, triển khai, báo cáo kiểm thử
├── scripts/                   sao lưu, khôi phục, nhập dữ liệu gốc, kiểm tra hợp đồng API, xuất OpenAPI/ERD
├── deploy/                    production: Caddy HTTPS (docker-compose.prod.yml)
├── docker-compose.yml         db + server + client
└── .github/workflows/ci.yml   test server, client, dựng thử stack
```

## Chạy nhanh

| | Lệnh | Mở |
|---|---|---|
| Docker (cả hệ thống) | `copy .env.example .env` → `docker compose up -d --build` → `docker compose exec server python seed.py` | http://localhost:5273 |
| Dev — CSDL | `docker compose up -d db` | cổng 5433 |
| Dev — server | `cd server` → `python -m venv venv` → `venv\Scripts\activate` → `pip install -r requirements.txt` → `copy .env.example .env` → `alembic upgrade head` → `python seed.py` → `uvicorn app.main:app --reload --port 8100` | http://localhost:8100/docs |
| Dev — client | `cd client` → `copy .env.example .env` → `flutter pub get` → `flutter run -d chrome --web-port 5274 --dart-define-from-file=.env` | http://localhost:5274 |

Chi tiết (Linux/macOS, production HTTPS, biến môi trường, log): [docs/deployment/DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md).

| Dịch vụ | Cổng | | Tài khoản mẫu (`seed.py`) | Mật khẩu | Vai trò |
|---|---|---|---|---|---|
| PostgreSQL | 127.0.0.1:5433 | | admin@fams.edu.vn | admin123 | Quản trị |
| Server API | 127.0.0.1:8100 | | gv01@fams.edu.vn | gv123 | Giảng viên |
| Web (nginx) | 5273 | | sv01@fams.edu.vn | sv123 | Sinh viên |
| Flutter web dev | 5274 | | ph01@fams.edu.vn | ph123 | Phụ huynh |
| | | | pdt01@ / ctsv01@ / khoa.cntt@ / ldk.cntt@ / ban01@fams.edu.vn | pdt12345 / ctsv1234 / khoa1234 / ldk12345 / ban12345 | P.ĐT / P.CTSV / VP Khoa / LĐ Khoa / Ban ngành |

**Đổi mật khẩu mẫu và `SECRET_KEY` trước khi đưa lên mạng** (`server/tools/doi_mat_khau.py`).

## API

- Tiền tố `/api/v1`, xác thực Bearer JWT (+ refresh token xoay vòng), lỗi `{"detail", "code"}`, header `X-Request-ID`,
  phân trang `limit`/`offset` + `X-Total-Count`. Quy ước: [docs/api/API.md](docs/api/API.md).
- 98 endpoint: [docs/api/ENDPOINTS.md](docs/api/ENDPOINTS.md) · OpenAPI: [docs/api/openapi.json](docs/api/openapi.json) ·
  Swagger UI khi chạy: `/docs`.

## Kiểm thử

```bash
cd server && venv\Scripts\python -m pytest -q                         # 279 test (Postgres thật, DB fams_system_test tự tạo/xóa)
cd client && flutter analyze && flutter test -j 1                     # 55 test
server\venv\Scripts\python scripts\check_api_contract.py              # mọi endpoint client có trên server
```

Kết quả và phạm vi đã/chưa kiểm: [docs/TEST_REPORT.md](docs/TEST_REPORT.md). Trạng thái từng chức năng:
[docs/FEATURE_INVENTORY.md](docs/FEATURE_INVENTORY.md) (sinh tự động từ kết quả test).

## Sao lưu / khôi phục

```bash
scripts/backup.sh                          # CSDL (pg_dump) + ảnh bằng chứng + sha256 → backups/
scripts/restore.sh backups/<tệp>.dump --evidence backups/<tệp>_evidence.tgz --yes
```
Xem [docs/deployment/BACKUP_RESTORE.md](docs/deployment/BACKUP_RESTORE.md) (lịch cron, nhập dữ liệu bản gốc).

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [PROJECT_OVERVIEW](docs/PROJECT_OVERVIEW.md) | Mục tiêu, vai trò, công nghệ, quy mô |
| [CURRENT_ARCHITECTURE](docs/CURRENT_ARCHITECTURE.md) | Kiến trúc bản gốc và khoảng trống |
| [BUSINESS_LOGIC](docs/BUSINESS_LOGIC.md) | Toàn bộ quy tắc nghiệp vụ, ngưỡng, ma trận quyền |
| [DATABASE_ANALYSIS](docs/DATABASE_ANALYSIS.md) | 21 bảng, quan hệ, migration ([ERD](docs/database/erd.mermaid)) |
| [FEATURE_INVENTORY](docs/FEATURE_INVENTORY.md) | 126 chức năng + trạng thái chuyển đổi/kiểm thử |
| [MIGRATION_PLAN](docs/MIGRATION_PLAN.md) | Kế hoạch, cô lập bản gốc, danh sách thay đổi |
| [TARGET_ARCHITECTURE](docs/architecture/TARGET_ARCHITECTURE.md) | Kiến trúc Client–Server sau tái cấu trúc, cách thêm module |
| [DEPLOYMENT](docs/deployment/DEPLOYMENT.md) · [BACKUP_RESTORE](docs/deployment/BACKUP_RESTORE.md) | Vận hành |
| [TEST_REPORT](docs/TEST_REPORT.md) | Kết quả kiểm thử |
| [docs/legacy/](docs/legacy/) | Tài liệu thiết kế của bản gốc |

## Nghiệp vụ chính (giữ nguyên bản gốc)

Xác thực JWT + refresh xoay vòng, khóa tạm khi đăng nhập sai · Phân quyền 9 vai trò + phạm vi Khoa · Danh mục đơn vị,
cán bộ, địa điểm, phòng · Lớp học phần, ghi danh, lịch học chống trùng phòng · Hồ sơ SV, đồng ý sinh trắc có phiên bản,
phụ huynh · Đăng ký/duyệt khuôn mặt (InsightFace + chống giả mạo) · Phiên điểm danh: quét camera xác nhận 2 khung,
SV tự điểm danh (ảnh + GPS + mã QR luân phiên), xác nhận tay, sửa có lý do + lịch sử · Thông báo phụ huynh (app +
email) · Chuyên cần, cảnh báo vắng ≥ 20 %, xuất Excel, thống kê theo Khoa · Nhật ký hệ thống tự động.
Chi tiết: [docs/BUSINESS_LOGIC.md](docs/BUSINESS_LOGIC.md).

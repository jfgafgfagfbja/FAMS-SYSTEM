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
│   ├── lib/modules/           MVC theo mô-đun: mXX_<tên>/{models,controllers,views} (m01_auth, m10_shell đã chuyển)
│   ├── lib/features/          các trang chưa chuyển sang modules/ · lib/widgets/ · lib/models/ · lib/router.dart
│   ├── nginx.conf, Dockerfile bản web + proxy /api/ → server
│   └── .env.example           API_BASE_URL (địa chỉ máy chủ)
├── server/                    FastAPI — toàn bộ nghiệp vụ
│   ├── app/modules/           MVC theo mô-đun: mXX_<tên>/{models,repository,schemas,service,controller}.py + README
│   │                          (m01_auth đã chuyển; MOD-02…09 do TV2–TV5 chuyển – docs/nhom/)
│   ├── app/api/v1/endpoints/  controller của các mô-đun chưa chuyển
│   ├── app/services/          nghiệp vụ theo module (+ nhận diện, GPS, đơn xin phép, nhật ký, thông báo)
│   ├── app/repositories/      truy cập dữ liệu
│   ├── app/schemas/ · app/db/ · app/core/ · app/jobs/
│   ├── alembic/               16 migration · tests/ 277 test · tools/
│   └── .env.example
├── docs/                      phân tích, kiến trúc, API, CSDL, triển khai, báo cáo kiểm thử
├── scripts/                   sao lưu, khôi phục, nhập dữ liệu gốc, kiểm tra hợp đồng API, xuất OpenAPI/ERD
├── deploy/                    production: Caddy HTTPS (docker-compose.prod.yml) · render/Dockerfile (cloud)
├── render.yaml                triển khai Render: PostgreSQL + 1 web service (web + API cùng link)
├── docker-compose.yml         db + server + client
└── .github/                   workflows/ci.yml (test mỗi lần push / PR) · CODEOWNERS · mẫu Pull Request
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

## Triển khai cloud (Render)

Bản chạy trên cloud: **https://fams-system-ug8s.onrender.com** (Render, máy chủ Singapore; API: `/api/v1`, kiểm tra: `/api/v1/health`). `render.yaml` khai báo 1 PostgreSQL 16 (pgvector) + 1 web
service Docker (`deploy/render/Dockerfile`: build Flutter web + server, chạy `server/single_port.py` ⇒ giao diện và
`/api/v1` cùng một link). Mỗi lần push nhánh `main`, Render tự build và deploy lại; lần khởi động đầu tự nạp dữ liệu
mẫu (`SEED_ON_START=1`). Cách làm + giới hạn gói miễn phí: [docs/nhom/KE_HOACH_NHIEM_VU_MVC_CLOUD.md](docs/nhom/KE_HOACH_NHIEM_VU_MVC_CLOUD.md).

## Làm việc nhóm (5 thành viên, MVC theo mô-đun)

Mỗi mô-đun một thư mục `server/app/modules/mXX_<tên>/` + `client/lib/modules/mXX_<tên>/`, người phụ trách ghi trong
`README.md` của mô-đun và `.github/CODEOWNERS`. Mỗi người làm trên nhánh riêng, mở Pull Request bằng tài khoản GitHub của
mình. Phân công và quy trình: [docs/nhom/KE_HOACH_NHIEM_VU_MVC_CLOUD.md](docs/nhom/KE_HOACH_NHIEM_VU_MVC_CLOUD.md).

## API

- Tiền tố `/api/v1`, xác thực Bearer JWT (+ refresh token xoay vòng), lỗi `{"detail", "code"}`, header `X-Request-ID`,
  phân trang `limit`/`offset` + `X-Total-Count`. Quy ước: [docs/api/API.md](docs/api/API.md).
- 102 endpoint: [docs/api/ENDPOINTS.md](docs/api/ENDPOINTS.md) · OpenAPI: [docs/api/openapi.json](docs/api/openapi.json) ·
  Swagger UI khi chạy: `/docs`.

## Kiểm thử

```bash
cd server && venv\Scripts\python -m pytest -q                         # 277 test (Postgres thật, DB fams_system_test tự tạo/xóa)
cd client && flutter analyze && flutter test -j 1                     # 43 test
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
| [DATABASE_ANALYSIS](docs/DATABASE_ANALYSIS.md) | 22 bảng, quan hệ, 16 migration ([ERD](docs/database/erd.mermaid)), chuẩn hóa 4NF |
| [FEATURE_INVENTORY](docs/FEATURE_INVENTORY.md) | 134 chức năng + trạng thái chuyển đổi/kiểm thử |
| [Sơ đồ luồng dữ liệu và CSDL](docs/so-do-luong-du-lieu-va-csdl/README.md) | Phân rã chức năng đến 134 chức năng lá, DFD ngữ cảnh / mức 0 / 1 / 2 (45 sơ đồ), đặc tả + truy vết màn hình → API → service → repository → bảng, ERD, chuẩn hóa CSDL đến 4NF, cây chức năng theo vai trò (HTML mở bằng trình duyệt) |
| [MIGRATION_PLAN](docs/MIGRATION_PLAN.md) | Kế hoạch, cô lập bản gốc, danh sách thay đổi |
| [TARGET_ARCHITECTURE](docs/architecture/TARGET_ARCHITECTURE.md) | Kiến trúc Client–Server sau tái cấu trúc, cách thêm module |
| [DEPLOYMENT](docs/deployment/DEPLOYMENT.md) · [BACKUP_RESTORE](docs/deployment/BACKUP_RESTORE.md) | Vận hành |
| [TEST_REPORT](docs/TEST_REPORT.md) | Kết quả kiểm thử |
| [docs/legacy/](docs/legacy/) | Tài liệu thiết kế của bản gốc |

## Nghiệp vụ chính

Xác thực JWT + refresh xoay vòng, khóa tạm khi đăng nhập sai · Phân quyền 9 vai trò + phạm vi Khoa · Danh mục đơn vị,
cán bộ, địa điểm, phòng · Lớp học phần, ghi danh, lịch học chống trùng phòng (ghi danh + xếp lịch: Quản trị viên, Phòng Đào tạo) · Hồ sơ SV, đồng ý sinh trắc có phiên bản,
phụ huynh · Đăng ký khuôn mặt (InsightFace + chống giả mạo), Phòng CTSV duyệt / từ chối có lý do, SV nhận phản hồi và xác nhận · Phiên điểm danh: quét camera xác nhận 2 khung,
SV tự điểm danh (ảnh + GPS), xác nhận tay, sửa có lý do + lịch sử · Đơn xin phép vắng: GV lớp / Lãnh đạo Khoa duyệt hoặc từ chối có lý do, SV nhận phản hồi và xác nhận, buổi được phép ghi `excused` · Thông báo phụ huynh (app +
email) · Chuyên cần, cảnh báo vắng ≥ 20 % gửi SV + phụ huynh ngay sau thống kê khi đóng phiên, xuất Excel, thống kê theo Khoa · Nhật ký hệ thống tự động.
Chi tiết: [docs/BUSINESS_LOGIC.md](docs/BUSINESS_LOGIC.md). Các thay đổi theo góp ý 10/11/2026 (bỏ mã QR, bỏ Quản trị viên duyệt khuôn mặt, bỏ ghi danh/xếp lịch của Văn phòng Khoa, thêm đơn xin phép, phản hồi + xác nhận kết quả duyệt, cảnh báo sau thống kê, CSDL chuẩn 4NF) đánh dấu ★ trong tài liệu; kết quả kiểm thử: [TEST_REPORT §7](docs/TEST_REPORT.md).

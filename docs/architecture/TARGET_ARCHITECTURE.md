# Kiến trúc Client–Server của FAMS-SYSTEM

> Kiến trúc **sau** tái cấu trúc. Hiện trạng ban đầu: [CURRENT_ARCHITECTURE.md](../CURRENT_ARCHITECTURE.md).
> Quy ước API: [api/API.md](../api/API.md). Triển khai: [deployment/DEPLOYMENT.md](../deployment/DEPLOYMENT.md).

## 1. Tổng thể

```
┌────────────────────────── CLIENT (client/, Flutter) ──────────────────────────┐
│ Web (nginx) · Android · iOS                                                    │
│  features/<nhóm>/…_page  ──►  lib/api/<module>_api  ──►  core/ApiClient (Dio)   │
│  giao diện, trạng thái UI,     ghép đường dẫn +           địa chỉ máy chủ, token, │
│  kiểm tra nhập liệu cơ bản     tham số theo nghiệp vụ     tự làm mới, chuẩn hóa lỗi│
└──────────────────────────────────────────┬─────────────────────────────────────┘
                                           │ HTTPS · JSON · Bearer JWT · /api/v1/...
┌──────────────────────────── SERVER (server/, FastAPI) ─────────────────────────┐
│ middleware: request-id + log · CORS · xử lý lỗi thống nhất · giới hạn tần suất   │
│  api/v1/endpoints (Controller)  →  services (Business Logic)  →  repositories    │
│  khai báo route, vai trò,            nghiệp vụ, phạm vi dữ liệu,    truy vấn SQLAlchemy│
│  đọc tham số, gọi service            transaction, ném AppError      (không commit)    │
│  jobs/ (tự đóng phiên, dọn ảnh, gửi email)  ·  core/ (cấu hình, bảo mật, phân quyền)  │
└──────────────────────────────────────────┬─────────────────────────────────────┘
                                           │ SQL (chỉ server)
                              ┌────────────▼────────────┐
                              │ PostgreSQL 16 + pgvector │
                              └──────────────────────────┘
```

Nguyên tắc: client **không** truy cập CSDL, **không** giữ bí mật (chỉ token của chính người dùng), **không**
quyết định quyền; mọi quy tắc nghiệp vụ, phân quyền, validate cuối cùng, transaction và thống kê nằm ở server.

## 2. Server

### 2.1 Cấu trúc thư mục

```
server/
├── app/
│   ├── main.py                  create_app(): middleware, xử lý lỗi, router, tác vụ nền (lifespan)
│   ├── api/
│   │   ├── deps.py              DbSession, CurrentUser, require_roles
│   │   └── v1/
│   │       ├── router.py        gom 17 controller + mô tả nhóm cho Swagger
│   │       └── endpoints/       health, auth, units, staff, locations, rooms, lecturers, classes,
│   │                            schedules, students, parents, faces, sessions, reports,
│   │                            notifications, audit_logs, media
│   ├── services/                nghiệp vụ theo module (bảng 2.2) + service kỹ thuật sẵn có
│   ├── repositories/            base (Page, paginate) + 15 repository theo bảng/nhóm bảng
│   ├── schemas/                 Pydantic theo module (auth, organization, locations, …) — `from app import schemas`
│   ├── db/                      database.py (engine, SessionLocal, get_db), models.py (21 bảng)
│   ├── core/                    config, security (JWT/refresh), authz (ma trận quyền), exceptions,
│   │                            logging (request id), rate_limit, media (URL ký), consent, timeutil
│   └── jobs/scheduler.py        3 vòng lặp nền gọi hàm nghiệp vụ trong services/
├── alembic/                     15 migration (không đổi)
├── tests/                       29 tệp test + conftest, 279 test (Postgres thật)
└── tools/                       route_coverage_plugin.py, doi_mat_khau.py, do_hieu_nang.py
```

### 2.2 Ánh xạ module

| Controller (`endpoints/`) | Service | Repository | Phân hệ |
|---|---|---|---|
| auth | auth_service | user, staff, lecturer, student, class | PH1 |
| units, staff | unit_service, staff_service, account_service | unit, staff, user | PH2 |
| locations, rooms | location_service, room_service | location, room | PH2 |
| lecturers | lecturer_service, schedule_service | lecturer, schedule, session | PH3 |
| classes, schedules | class_service, schedule_service | class, schedule, session, student | PH3 |
| students | student_service, report_service | student | PH4/PH8 |
| parents | parent_service | parent, student | PH4/PH7/PH8 |
| faces | face_data_service (+ face_service, antispoof_service, user_notify) | face, student | PH5 |
| sessions | session_service, attendance_service (+ geo) | session, class, schedule, student, leave | PH6 |
| leave_requests ★ | leave_service (+ user_notify) | leave, schedule, student | PH6 |
| reports | report_service (+ attendance_stats) | report, session, class | PH8 |
| notifications | notification_service (+ parent_notify, user_notify) | notification | PH7 |
| audit_logs | audit_log_service (+ audit) | audit_log | PH9 |
| media | media_service | — (tệp) | PH1 |
| health | — | — | vận hành |

### 2.3 Trách nhiệm từng lớp

| Lớp | Được làm | Không được làm |
|---|---|---|
| Controller | Khai báo route, kiểu dữ liệu vào/ra, vai trò (`require_roles`), đặt header phản hồi (`X-Total-Count`, `Content-Disposition`), giới hạn tần suất | Truy vấn DB, commit, quy tắc nghiệp vụ, ném `HTTPException` |
| Service | Quy tắc nghiệp vụ, kiểm phạm vi (`core/authz`), điều phối repository, **commit** (một use case = một transaction, đúng điểm commit của bản gốc), ném `AppError` | Phụ thuộc vào HTTP (trừ `Request` để ghi IP vào nhật ký, `UploadFile` để đọc ảnh) |
| Repository | Truy vấn SQLAlchemy theo bảng/nhóm bảng, nhận `Session` của request | Commit, ném lỗi nghiệp vụ, tự mở phiên |

Kiểm tra tự động khi tái cấu trúc: controller không còn `db.query`/`db.commit`/`HTTPException`; không service/core
nào còn `HTTPException`; repository không commit.

Ngoại lệ có chủ đích — một số service **kỹ thuật** có sẵn vẫn truy vấn trực tiếp vì gắn với cơ chế riêng:
`face_service` (tìm láng giềng gần nhất bằng toán tử pgvector), `audit` và `parent_notify` (chạy trong sự kiện
`after_flush`/`before_flush` của SQLAlchemy, phải dùng đúng phiên đang flush), `evidence_cleanup` (cập nhật hàng loạt).

### 2.4 Xử lý lỗi, log, transaction

- `core/exceptions.py`: `AppError` → 400/401/403/404/409/429; handler chung cho `AppError`, `HTTPException`,
  lỗi validate (422), `IntegrityError` (409), vượt tần suất (429) và lỗi bất ngờ (500, có log stack trace).
  Định dạng: `{"detail", "code"}` — giữ `detail` như bản gốc.
- `core/logging.py`: middleware ASGI gắn `X-Request-ID`, đo thời gian, ghi `fams.access`; mọi dòng log có `[request_id]`.
- Một request = một `Session` (`api/deps.DbSession`); service commit cuối use case. Sự kiện SQLAlchemy
  (`services/audit.py`, `services/parent_notify.py`) được import tường minh trong `main.py`.

### 2.5 Tác vụ nền (`jobs/scheduler.py`)

| Vòng lặp | Chu kỳ | Gọi |
|---|---|---|
| auto_close_sessions_loop | 60 s | `session_service.auto_close_expired_sessions` |
| cleanup_evidence_loop | 24 h | `evidence_cleanup.cleanup_expired_evidence` |
| send_notification_emails_loop | 15 s (khi có SMTP) | `parent_notify.send_pending_emails` |

Chạy trong cùng tiến trình uvicorn ⇒ triển khai **một** tiến trình/container (như bản gốc). Muốn nhiều worker:
chuyển bộ đếm (đăng nhập sai, giới hạn tần suất, khung hình xác nhận) sang Redis và tách `jobs/` thành tiến trình riêng.

## 3. Client

```
client/lib/
├── api/            MỚI — api.dart (extension FamsApi trên ApiClient) + 5 tệp theo phân hệ:
│                   catalog_api (auth, units, staff, locations, rooms), training_api (lecturers, classes,
│                   schedules), people_api (students, parents, faces), attendance_api (sessions),
│                   report_api (reports, notifications, auditLogs)
├── core/           api_client (truyền tải), config (địa chỉ máy chủ + /api/v1), auth_controller,
│                   roles (Perms: chỉ ẩn/hiện), token_storage, theme, formatters
├── features/       33 trang theo nhóm vai trò (giữ nguyên giao diện)
├── models/         lớp dữ liệu + fromJson
├── widgets/        11 widget dùng chung
└── router.dart     go_router, chặn route theo đăng nhập + quyền hiển thị
```

- Trang gọi theo tên nghiệp vụ: `api.sessions.close(id)`, `api.classes.page(query: {...})` thay cho đường dẫn viết
  tay (113 lời gọi trong 36 tệp đã chuyển). Mỗi endpoint khai báo **một lần** trong `lib/api/`.
- `scripts/check_api_contract.py` đối chiếu mọi endpoint client khai báo với route thật của server (đúng động từ).
- Cấu hình: `--dart-define=API_BASE_URL=<địa chỉ máy chủ>` (rỗng = cùng origin cho bản web), hoặc người dùng
  nhập ở màn đăng nhập; client tự ghép `/api/v1`.

## 4. Cơ sở dữ liệu

Không đổi schema (21 bảng, 15 migration, head `d4f8a2c6e913`) — dữ liệu bản gốc khôi phục thẳng được.
★ Sau góp ý 10/11/2026: 22 bảng, 16 migration, head `e2a7c4b91f6d` (bảng `leave_requests`, bỏ `require_qr`) — dữ
liệu bản gốc vẫn khôi phục được rồi `alembic upgrade head`.
`models.py` khai báo thêm 4 chỉ mục vốn đã có trong DB thật (do migration tạo) để `models` khớp DB:
HNSW `face_embeddings.embedding`, chỉ mục một phần hàng đợi email, `rooms.location_id`, `schedules.room_id`.
Chi tiết: [DATABASE_ANALYSIS.md](../DATABASE_ANALYSIS.md).

## 5. Mở rộng thêm module

1. `app/db/models.py` + `alembic revision --autogenerate` (đọc lại tệp sinh ra).
2. `app/schemas/<module>.py` (+ thêm vào `schemas/__init__.py`).
3. `app/repositories/<module>_repository.py` → `app/services/<module>_service.py` → `app/api/v1/endpoints/<module>.py`
   (+ đăng ký trong `api/v1/router.py`, mô tả nhóm trong `OPENAPI_TAGS`).
4. Quyền: hằng vai trò trong controller, phạm vi dữ liệu trong `core/authz.py`.
5. Test trong `server/tests/`; chạy kèm `route_coverage_plugin` để chắc route mới có test.
6. Client: thêm lớp vào `lib/api/`, getter trong `FamsApi`, trang trong `features/`, route trong `router.dart`.
7. `scripts/export_openapi.py`, `scripts/check_api_contract.py`, sinh lại `docs/FEATURE_INVENTORY.md`.

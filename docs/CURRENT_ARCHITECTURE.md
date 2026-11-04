# Kiến trúc hiện tại của FAMS (bản gốc)

> Mô tả hệ thống tại `D:\FAMS` trước khi tái cấu trúc. Kiến trúc mới: xem
> [MIGRATION_PLAN.md](MIGRATION_PLAN.md) và [architecture/TARGET_ARCHITECTURE.md](architecture/TARGET_ARCHITECTURE.md).

## 1. Kết luận chính

FAMS **đã là hệ thống Client–Server**: client Flutter chỉ giao tiếp với server qua HTTP/JSON,
không truy cập database, và server là nơi duy nhất kiểm tra quyền. Việc "chuyển sang Client–Server"
vì vậy là **chuẩn hóa và tách lớp sâu hơn** chứ không phải viết lại. Các khoảng trống thực sự nằm
ở mục 6.

## 2. Sơ đồ triển khai

```
┌──────────────────────────┐      HTTPS (production: Caddy)       ┌───────────────────────────┐
│ Trình duyệt (Flutter Web)│ ───────────────┐                     │  docker compose           │
└──────────────────────────┘                ▼                     │                           │
┌──────────────────────────┐        ┌───────────────┐  /api/*     │  ┌─────────────────────┐  │
│ Android / iOS (Flutter)  │ ─────▶ │ nginx (web)   │ ──────────▶ │  │ backend FastAPI     │  │
└──────────────────────────┘        │ tệp tĩnh +    │  bỏ "/api"  │  │ uvicorn :8000       │  │
                                    │ proxy /api/   │             │  │ + tác vụ nền        │  │
                                    └───────────────┘             │  └─────────┬───────────┘  │
                                                                  │            │ SQL          │
                                                                  │  ┌─────────▼───────────┐  │
                                                                  │  │ PostgreSQL 16       │  │
                                                                  │  │ + pgvector (HNSW)   │  │
                                                                  │  └─────────────────────┘  │
                                                                  │  volume: pgdata, evidence,│
                                                                  │          insightface      │
                                                                  └───────────────────────────┘
```

- `db` và `backend` chỉ mở cổng trên `127.0.0.1`; người dùng đi qua nginx (`/api/` → backend,
  nginx **cắt** tiền tố `/api`).
- Production (`deploy/docker-compose.prod.yml`): Caddy nhận 80/443, tự xin chứng chỉ Let's
  Encrypt; không dịch vụ nào khác mở cổng ra ngoài.

## 3. Server (`backend/`)

```
backend/
├── alembic/versions/        15 migration (baseline 0b5e1a7c2d90 → d4f8a2c6e913)
├── app/
│   ├── main.py              tạo FastAPI, CORS, rate limit, handler IntegrityError→409,
│   │                        đăng ký 16 router, khởi động 3 tác vụ nền (lifespan)
│   ├── api/                 16 router = "controller" NHƯNG chứa phần lớn nghiệp vụ
│   │   └── serializers.py   ORM → schema + vài hàm kiểm tra (email trùng, lịch sử sửa)
│   ├── core/
│   │   ├── config.py        Settings (pydantic-settings, đọc .env) — mọi ngưỡng nghiệp vụ
│   │   ├── security.py      JWT, refresh token xoay vòng, get_current_user, require_roles
│   │   ├── authz.py         ma trận quyền + lọc phạm vi Khoa/giảng viên
│   │   ├── media.py         ký/kiểm HMAC URL ảnh
│   │   ├── consent.py       nội dung đồng ý sinh trắc có phiên bản
│   │   └── timeutil.py      chuỗi thời gian kèm múi giờ +07:00
│   ├── db/                  database.py (engine, SessionLocal, get_db), models.py (21 bảng)
│   ├── services/            11 service: face, antispoof, session, attendance_stats, geo,
│   │                        checkin_code, consent, audit, parent_notify, email, evidence_cleanup
│   └── schemas.py           842 dòng — toàn bộ schema Pydantic trong một file
├── tests/                   26 file, 258 test, Postgres thật (tạo/xóa DB test tự động)
├── seed.py                  dữ liệu mẫu + đơn vị + tài khoản cán bộ
└── Dockerfile, entrypoint.sh (alembic upgrade head → uvicorn --proxy-headers)
```

### 3.1 Cách một request được xử lý

```
HTTP → slowapi (chỉ /auth/*) → Router function
        ├─ Depends(get_db)                 phiên SQLAlchemy cho request
        ├─ Depends(get_current_user)       giải JWT, kiểm jti bị thu hồi, token_version,
        │                                  gắn người thao tác vào db.info (nhật ký)
        ├─ Depends(require_roles(...))     kiểm vai trò
        ├─ authz.ensure_* / filter_*       kiểm phạm vi (Khoa, lớp mình dạy, con mình…)
        ├─ NGHIỆP VỤ viết trực tiếp trong router (truy vấn ORM, kiểm tra, ghi)
        ├─ db.commit()  → sự kiện SQLAlchemy:
        │     before_flush: parent_notify tạo thông báo phụ huynh
        │     after_flush : audit ghi audit_logs cho mọi thay đổi
        └─ trả schema Pydantic (URL ảnh được ký khi serialize)
```

### 3.2 Tác vụ nền (asyncio, trong cùng tiến trình)

| Tác vụ | Chu kỳ | Việc |
|---|---|---|
| `run_auto_close_loop` | 60 s | Đóng phiên quá hạn (giờ kết thúc + 30 phút), sinh bản ghi vắng |
| `run_cleanup_loop` | 24 h | Xóa ảnh bằng chứng quá `EVIDENCE_RETENTION_DAYS` (90 ngày) |
| `run_notification_email_loop` | 15 s | Gửi email thông báo phụ huynh theo hàng đợi (chỉ khi cấu hình SMTP) |

## 4. Client (`mobile/`)

```
mobile/lib/
├── main.dart, app.dart      khởi tạo ApiClient, AuthController, ThemeController, GoRouter
├── router.dart              go_router: chặn route theo đăng nhập + quyền (Perms)
├── core/
│   ├── api_client.dart      Dio: gắn Bearer, tự refresh khi 401 (hàng đợi), chuẩn hóa lỗi
│   │                        từ trường "detail", phân trang qua header X-Total-Count
│   ├── auth_controller.dart trạng thái đăng nhập, /auth/me
│   ├── config.dart          API_BASE_URL (--dart-define) / URL người dùng nhập / mặc định
│   ├── roles.dart           Roles + Perms: CHỈ ẩn/hiện giao diện (server kiểm tra cuối cùng)
│   ├── token_storage.dart   flutter_secure_storage
│   └── formatters.dart, theme.dart
├── models/models.dart       825 dòng: lớp dữ liệu + fromJson cho mọi response
├── features/<nhóm>/…_page   33 trang (admin, auth, home, lecturer, office, parent,
│                            schedule, student)
└── widgets/                 11 widget dùng chung (khung app, camera, QR, form, danh sách phân trang…)
```

- **Không truy cập database**, không giữ secret: chỉ access/refresh token của chính người dùng.
- Các trang gọi `api.get('/students')`… **trực tiếp** (78 chỗ) — chưa có lớp dịch vụ API theo module.
- Nghiệp vụ phía client chỉ gồm hiển thị (định dạng ngày, nhãn trạng thái, phần trăm), lấy GPS,
  chụp ảnh, quét QR, in lịch ra PDF. Mọi phép tính chuyên cần/cảnh báo do server trả về.

## 5. Luồng dữ liệu chính

| Luồng | Đường đi |
|---|---|
| Đăng nhập | Client `POST /auth/login` (form) → JWT 480 phút + refresh token 30 ngày → lưu secure storage |
| Làm mới phiên | 401 → interceptor `POST /auth/refresh` → token mới, gửi lại request; dùng lại refresh token cũ ⇒ server thu hồi tất cả |
| Quét camera | GV mở phiên → camera gửi khung hình `POST /sessions/{id}/recognize` → server nhận diện (pgvector) → xác nhận 2 khung → ghi bản ghi → nhật ký + thông báo phụ huynh |
| Tự điểm danh | SV `GET /sessions/{id}/checkin-info` → chụp ảnh + GPS (+ QR) → `POST /sessions/{id}/self-checkin` → server kiểm tra ghi danh, đồng ý, QR, GPS, khuôn mặt, chống giả mạo |
| Ảnh bằng chứng | Server trả `/evidence/...?exp=&sig=` → client ghép base URL → `GET /evidence/...` kiểm chữ ký |
| Báo cáo | Client gọi `/reports/*` → server tính từ các phiên **đã đóng** → JSON hoặc file `.xlsx` |

## 6. Đánh giá so với mô hình Client–Server mục tiêu

| Tiêu chí | Hiện trạng | Đánh giá |
|---|---|---|
| Tách Client / Server | Hai dự án độc lập (`mobile/`, `backend/`), giao tiếp HTTP | ✅ Đạt |
| Client không truy cập DB | Đúng | ✅ Đạt |
| Nghiệp vụ ở server | Đúng; client chỉ ẩn/hiện chức năng | ✅ Đạt |
| Xác thực, phân quyền ở server | JWT + refresh xoay vòng + ma trận quyền + phạm vi Khoa | ✅ Đạt |
| Migration, toàn vẹn dữ liệu | Alembic, UNIQUE/FK, IntegrityError → 409 | ✅ Đạt |
| Swagger/OpenAPI | Có `/docs` mặc định của FastAPI | ⚠️ Chưa có mô tả nhóm, phiên bản, xuất file |
| **API versioning** | Đường dẫn trần `/auth`, `/classes`… | ❌ Thiếu |
| **Tách lớp Controller / Service / Repository** | Nghiệp vụ và truy vấn nằm trong router (`sessions.py` 618 dòng, `classes.py` 326, `reports.py` 309, `students.py` 306); service phát `HTTPException` (dính HTTP) | ❌ Thiếu |
| **Định dạng lỗi thống nhất** | `{"detail": ...}` mặc định; lỗi 422 là danh sách; không có mã lỗi máy đọc được | ⚠️ Một phần |
| **Logging vận hành** | `logging` mặc định, không request-id, không cấu hình định dạng | ⚠️ Một phần |
| Lớp API phía client | 78 lời gọi đường dẫn viết thẳng trong trang | ⚠️ Một phần |
| Schema | Một file 842 dòng | ⚠️ Khó bảo trì |
| **Backup / restore** | Một dòng `pg_dump` trong `deploy/README.md`; không có restore, không sao lưu ảnh | ❌ Thiếu |
| Cấu hình môi trường | `.env.example` cho compose, backend, deploy | ✅ Đạt |
| Test | 258 test server + 10 file test Flutter + CI dựng cả stack | ✅ Đạt |

## 7. Điểm cần lưu ý khi tái cấu trúc

1. **Thứ tự route** trong `parents.py`, `students.py`: `/me/...` phải khai báo trước `/{id}/...`.
2. **Sự kiện SQLAlchemy toàn cục** (`audit`, `parent_notify`) đăng ký khi import module — phải
   giữ import, nếu không nhật ký và thông báo phụ huynh sẽ âm thầm ngừng hoạt động.
3. `get_current_user` gắn người thao tác vào `db.info["audit_actor"]` — mọi lớp mới phải dùng
   **cùng phiên DB** của request.
4. `_confirm_counts` (đếm khung hình xác nhận) lưu trong bộ nhớ tiến trình — chỉ đúng khi chạy
   **một** tiến trình uvicorn. Giữ nguyên, ghi rõ giới hạn.
5. Bộ đếm đăng nhập sai và slowapi cũng lưu trong bộ nhớ tiến trình — cùng giới hạn trên.
6. URL ảnh ký HMAC theo **đường dẫn tương đối** `/evidence/...`; client ghép với base URL. Đổi
   tiền tố API phải đổi đồng bộ cả route ảnh và cách client ghép URL.
7. `OAuth2PasswordBearer(tokenUrl="/auth/login")` — phải đổi theo tiền tố mới để nút Authorize
   của Swagger hoạt động.

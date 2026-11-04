# Kế hoạch chuyển đổi FAMS sang kiến trúc Client–Server chuẩn hóa

> Đầu vào: [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md) (hiện trạng, khoảng trống),
> [BUSINESS_LOGIC.md](BUSINESS_LOGIC.md) (chuẩn nghiệp vụ), [FEATURE_INVENTORY.md](FEATURE_INVENTORY.md) (danh mục kiểm tra).
> Kiến trúc đích chi tiết: [architecture/TARGET_ARCHITECTURE.md](architecture/TARGET_ARCHITECTURE.md).

## 1. Nguyên tắc

1. **Tương đương chức năng**: cùng đường dẫn tài nguyên (chỉ thêm tiền tố `/api/v1`), cùng tham số, cùng mã HTTP,
   cùng thông báo lỗi, cùng dữ liệu trả về. Không đổi nghiệp vụ, không đổi schema DB.
2. **Kiểm soát bằng test**: 258 test của bản gốc là lưới an toàn; chạy lại sau **từng** module. Không sửa kỳ vọng của
   test cũ, chỉ đổi tiền tố đường dẫn (qua `base_url` của client test) và thêm test mới.
3. **Không ảnh hưởng bản gốc** (mục 2).
4. Thay đổi nào khác bản gốc đều ghi ở mục 6 và trong `FEATURE_INVENTORY.md`.

## 2. Cô lập với bản gốc `D:\FAMS`

| Tài nguyên | Bản gốc | Bản mới `FAMS-SYSTEM` |
|---|---|---|
| Thư mục mã nguồn | `D:\FAMS` (chỉ đọc, không commit/stash/đổi nhánh) | `D:\LTM\FAMS-SYSTEM` |
| Git | repo gốc, remote GitHub | repo mới, **không có remote** |
| Docker Compose project | `fams` | `fams-system` (dev), `fams-system-prod` (production) |
| Container DB / cổng | `fams-db-1` / 5432 | `fams-system-db-1` / **5433** |
| DB / tài khoản DB | `fams` / `fams:fams123` | `fams_system` / `fams_system:fams_system_dev` (sai cổng vẫn bị từ chối đăng nhập) |
| DB test | `fams_test` | `fams_system_test` |
| Server / Web | 8000 / 5173 | **8100** / **5273** (Flutter web dev 5274) |
| Volume | `fams_pgdata`, `fams_evidence`, `fams_insightface` | `fams-system_*` |
| Python venv | `D:\FAMS\backend\venv` | `server\venv` riêng |
| App di động | `vn.edu.fams.fams_app` / `vn.edu.fams.famsApp`, tên "FAMS" | `vn.edu.fams.fams_system` / `vn.edu.fams.famsSystem`, tên "FAMS System" (cài song song, không ghi đè) |
| Triển khai công khai | Tailscale Funnel, Hugging Face Space + Neon | **không sao chép** các script này (chúng trỏ vào đúng địa chỉ công khai của bản gốc) |

Ảnh bằng chứng thật (`backend/evidence`) và `.env` **không** sao chép. Nhập dữ liệu bản gốc là thao tác tùy chọn,
chỉ đọc (`pg_dump`), do người dùng chủ động chạy — xem [deployment/BACKUP_RESTORE.md](deployment/BACKUP_RESTORE.md).

## 3. Kiến trúc đích

```
FAMS-SYSTEM/
├── client/                         Flutter (Web, Android, iOS) — chỉ giao diện
│   ├── lib/
│   │   ├── api/                    MỚI: lớp gọi API theo module (auth, units, classes, sessions…)
│   │   ├── core/                   ApiClient (HTTP, token, lỗi), cấu hình, quyền hiển thị, theme
│   │   ├── features/<nhóm>/        trang giao diện (giữ nguyên giao diện)
│   │   ├── models/                 lớp dữ liệu
│   │   ├── widgets/                widget dùng chung
│   │   └── router.dart             điều hướng + chặn route theo quyền
│   ├── nginx.conf, Dockerfile      phục vụ web + proxy /api/ → server (giữ nguyên tiền tố)
│   └── .env.example
├── server/                         FastAPI — toàn bộ nghiệp vụ
│   ├── app/
│   │   ├── main.py                 create_app(): middleware, xử lý lỗi, router, tác vụ nền
│   │   ├── api/
│   │   │   ├── deps.py             phụ thuộc dùng chung (DB, người dùng hiện tại, vai trò)
│   │   │   └── v1/                 router.py + endpoints/ — CONTROLLER mỏng
│   │   ├── services/               NGHIỆP VỤ theo module (+ service nhận diện, GPS, QR… sẵn có)
│   │   ├── repositories/           TRUY CẬP DỮ LIỆU theo bảng/nhóm bảng
│   │   ├── schemas/                Pydantic theo module (tách từ schemas.py 842 dòng)
│   │   ├── db/                     engine, session, models (không đổi)
│   │   ├── core/                   config, security, authz, exceptions, logging, rate_limit, media…
│   │   └── jobs/                   tác vụ nền (tự đóng phiên, dọn ảnh, gửi email)
│   ├── alembic/                    migration (không đổi)
│   ├── tests/                      258 test gốc + test mới
│   └── .env.example
├── docs/                           phân tích, kiến trúc, API, CSDL, triển khai, báo cáo test
├── scripts/                        sao lưu, khôi phục, nhập dữ liệu bản gốc
├── deploy/                         production: Caddy HTTPS
├── docker-compose.yml              db + server + client (nginx)
└── README.md
```

Luồng một request sau tái cấu trúc:

```
Client (api/<module>_api.dart) ──HTTP /api/v1/...──▶ nginx ──▶ Controller (api/v1/endpoints)
   ▲                                                              │ kiểm vai trò (deps)
   │ JSON {data} hoặc {"detail", "code"}                          ▼
   └──────────────────────────────────────────────── Service (nghiệp vụ, phạm vi, transaction)
                                                                  │ ném AppError (không phụ thuộc HTTP)
                                                                  ▼
                                                     Repository (truy vấn SQLAlchemy) ──▶ PostgreSQL
```

### 3.1 Quy ước API
- Tiền tố `/api/v1`; tài nguyên danh từ số nhiều; `GET` đọc, `POST` tạo/hành động, `PATCH` sửa, `DELETE` xóa.
- Phân trang: `limit`, `offset` (+ header `X-Total-Count`); tìm kiếm `q`; lọc theo trường (`semester`, `faculty_id`…) —
  giữ nguyên như bản gốc để client không phải đổi.
- Lỗi thống nhất: `{"detail": <thông báo>, "code": <mã máy đọc>}` cho mọi lỗi (giữ `detail` vì client đang đọc trường này;
  lỗi 422 giữ `detail` là danh sách và thêm `code="validation_error"`). Mọi response có header `X-Request-ID`.
- `GET /` và `GET /api/v1/health` kiểm tra sức khỏe (bản thứ hai có kiểm DB, đi qua được nginx).
- Swagger UI `/docs`, OpenAPI `/openapi.json`; bản xuất tĩnh `docs/api/openapi.json`.

### 3.2 Xử lý lỗi và log
- `core/exceptions.py`: `AppError` → `BadRequestError` (400), `UnauthorizedError` (401), `ForbiddenError` (403),
  `NotFoundError` (404), `ConflictError` (409), `TooManyRequestsError` (429). Service/authz ném các lỗi này thay vì
  `HTTPException`.
- `core/logging.py`: định dạng thống nhất có `request_id`; middleware ghi mỗi request một dòng
  (method, path, status, thời gian xử lý, người dùng). Lỗi không lường trước ⇒ log stack trace + trả 500 chung.

## 4. Kế hoạch theo bước (mỗi bước: sửa → chạy toàn bộ test → ghi trạng thái)

| Bước | Nội dung | Kiểm tra |
|---|---|---|
| 0 | Sao chép, cô lập, mốc test (258 đạt), mốc độ phủ route (88/97) | ✅ đã xong |
| 1 | Hạ tầng server: `core/exceptions`, `core/logging`, middleware request-id, `api/deps`, `create_app`, tiền tố `/api/v1`, Swagger | 258 test (đổi `base_url`) + test hạ tầng mới |
| 2 | Tách `schemas.py` thành gói `schemas/` (giữ `from app import schemas`) | 258 test |
| 3 | Repository + service + controller cho từng module, theo thứ tự phụ thuộc: units → staff → locations → rooms → lecturers → classes/schedules → students → parents → faces → sessions → reports → notifications → audit_logs → auth → media | 258 test sau **mỗi** module |
| 4 | Tác vụ nền sang `jobs/` | test vòng đời phiên, dọn ảnh, email |
| 5 | Bổ sung test cho 9 route chưa có test + nhánh thành công còn thiếu + migration Alembic trên DB trống | độ phủ route 97/97 |
| 6 | Client: cấu hình `API_BASE_URL` = địa chỉ máy chủ (tự ghép `/api/v1`), lớp `lib/api/`, thay 78 lời gọi | `flutter analyze`, `flutter test` |
| 7 | Docker: đổi tên dịch vụ `server`/`client`, nginx giữ tiền tố `/api`, healthcheck; CI theo cấu trúc mới | dựng stack, đăng nhập qua nginx |
| 8 | Sao lưu/khôi phục: script + thử khôi phục vòng tròn trên DB của bản mới | so số dòng trước/sau |
| 9 | Kiểm thử đầu-cuối trên trình duyệt (đăng nhập theo vai trò, CRUD, phiên, báo cáo) | `docs/TEST_REPORT.md` |
| 10 | Hoàn thiện tài liệu: README, API, kiến trúc, triển khai, sinh lại `FEATURE_INVENTORY.md` | không còn chức năng "chưa hoàn thành" |

## 5. Rủi ro và cách kiểm soát

| Rủi ro | Kiểm soát |
|---|---|
| Đổi thông báo/mã lỗi khi chuyển `HTTPException` → `AppError` | Giữ nguyên chuỗi; test gốc kiểm `status_code` và `detail` |
| Mất sự kiện nhật ký/thông báo phụ huynh khi di chuyển module | Import tường minh trong `main.py`; test `test_audit_log`, `test_parent_notifications` |
| Thứ tự route `/me` vs `/{id}` | Giữ thứ tự khai báo; test phụ huynh/SV |
| Sai phiên DB (repository mở phiên riêng) | Repository nhận `Session` của request, không tự tạo |
| Client ghép sai URL ảnh/API | URL ảnh vẫn là đường dẫn tương đối ghép với base `/api/v1`; test client + E2E xem ảnh |
| Chạy nhiều tiến trình uvicorn làm sai bộ đếm trong bộ nhớ | Ghi rõ: 1 tiến trình/1 container (như bản gốc) |
| Ảnh hưởng bản gốc | Mục 2; mỗi lần chạy test in địa chỉ DB; container cũ không bị đụng tới |

## 6. Thay đổi so với hệ thống cũ

| # | Thay đổi | Lý do | Ảnh hưởng nghiệp vụ |
|---|---|---|---|
| 1 | Tiền tố `/api/v1` cho mọi endpoint (trừ `GET /`) | Versioning | Không |
| 2 | Lỗi thêm trường `code`; header `X-Request-ID` | Chuẩn hóa | Không (giữ `detail`) |
| 3 | Thêm `GET /api/v1/health` (kiểm DB) | Healthcheck qua nginx | Không |
| 4 | `API_BASE_URL` của client là địa chỉ máy chủ, client tự thêm `/api/v1` | Một chỗ cấu hình | Không |
| 5 | Cổng, tên DB, app id khác bản gốc | Cô lập | Không |
| 6 | Không mang theo script công khai Tailscale/Hugging Face | Tránh ghi đè bản công khai của bản gốc | Không |
| 7 | Thư mục `backend/` → `server/`, `mobile/` → `client/`; dịch vụ Compose `backend`/`frontend` → `server`/`client` | Cấu trúc theo yêu cầu | Không |
| 8 | Router tách thành controller (`api/v1/endpoints`) + 17 service nghiệp vụ mới (+ `session_service` mở rộng) + 15 repository; `schemas.py` → gói `schemas/` | Tách lớp | Không (279 test đạt sau mỗi bước) |
| 9 | Service/phân quyền ném `AppError` thay cho `HTTPException` | Service không phụ thuộc HTTP | Không (giữ mã HTTP + thông báo) |
| 10 | Vòng lặp nền chuyển sang `app/jobs/scheduler.py`; vòng dọn ảnh nay **ghi log** lỗi thay vì bỏ qua im lặng | Tách tác vụ nền, dễ vận hành | Không |
| 11 | `models.py` khai báo 4 chỉ mục vốn đã có trong DB (HNSW, hàng đợi email, `rooms.location_id`, `schedules.room_id`) | Models khớp migration (phát hiện nhờ test migration) | Không (DB không đổi) |
| 12 | `alembic/env.py` nhận kết nối truyền sẵn, tùy chọn không cấu hình lại logging | Test migration trên DB tạm | Không |
| 13 | `create_engine(..., pool_pre_ping=True)` | Tự nối lại sau khi DB khởi động lại | Không |
| 14 | uvicorn `--no-access-log` (log truy cập do middleware ghi, kèm request id); Dockerfile server có `HEALTHCHECK`; `client` chờ `server` healthy | Vận hành | Không |
| 15 | Client: lớp `lib/api/` (113 lời gọi trong 36 tệp), `ApiClient.serverUrl`, ô nhập máy chủ chấp nhận cả địa chỉ có `/api/v1`/`/api` | Tách lớp gọi API | Không (giao diện giữ nguyên) |
| 16 | `nginx.conf`, `tool/web_proxy.py`, `single_port.py` giữ nguyên tiền tố `/api` khi chuyển tiếp | Server phục vụ ở `/api/v1` | Không |
| 17 | Pydantic `class Config` → `model_config` | Bỏ cảnh báo lỗi thời | Không |
| 18 | Thêm `scripts/` (backup, restore, import_legacy, check_api_contract, export_openapi, export_erd), `docs/` mới | Vận hành, tài liệu | Không |

## 7. Trạng thái thực hiện (03/11/2026)

| Bước | Trạng thái | Kiểm chứng |
|---|---|---|
| 0. Sao chép, cô lập, mốc | ✅ | 258/258 test bản gốc trên môi trường cô lập; độ phủ 88/97 route |
| 1. Hạ tầng server | ✅ | 258 + 9 test hạ tầng |
| 2. Tách schema | ✅ | 69/69 lớp, JSON Schema trùng khớp từng lớp |
| 3. Controller/Service/Repository 16 module | ✅ | 267/267 sau từng nhóm; kiểm tự động không còn truy vấn/`HTTPException` ở controller |
| 4. Tác vụ nền → `jobs/` | ✅ | test vòng đời phiên, dọn ảnh, email |
| 5. Bổ sung test, test migration | ✅ | 279/279; 98/98 route có test |
| 6. Client: cấu hình + lớp API | ✅ | `flutter analyze` 0 vấn đề; 55/55 test; hợp đồng 95/95 endpoint |
| 7. Docker, nginx, CI | ✅ (04/11/2026) | Build `server`/`client`, `docker compose up`: 3 container khỏe; 43/43 GET qua nginx với 9 vai trò — [TEST_REPORT §5](TEST_REPORT.md) |
| 8. Sao lưu/khôi phục | ✅ | Khôi phục vòng tròn 22 bảng trùng số dòng |
| 9. Kiểm thử đầu-cuối trên trình duyệt | ✅ (04/11/2026) | Flutter web qua nginx: đăng nhập, 13 trang quản trị, giao diện sáng/tối, lấy GPS (giả lập) |
| 10. Tài liệu | ✅ | README, docs/, `FEATURE_INVENTORY.md` sinh từ kết quả test (126/126 chức năng có bằng chứng) |

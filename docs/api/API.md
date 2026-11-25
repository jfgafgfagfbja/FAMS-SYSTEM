# Quy ước API FAMS-SYSTEM (v1)

> Danh sách đầy đủ 98 endpoint: [ENDPOINTS.md](ENDPOINTS.md) (sinh tự động).
> Đặc tả máy đọc: [openapi.json](openapi.json). Khi server chạy: Swagger UI `http://localhost:8100/docs`.
> Sinh lại cả hai tệp: `server/venv/Scripts/python scripts/export_openapi.py`.

## 1. Địa chỉ và phiên bản

| Thành phần | Giá trị |
|---|---|
| Tiền tố | `/api/v1` (cấu hình `API_PREFIX`) — mọi endpoint nghiệp vụ |
| Ngoài tiền tố | `GET /` (tiến trình còn sống), `/docs`, `/redoc`, `/openapi.json` |
| Qua nginx (web, Docker) | `http://<máy chủ>:5273/api/v1/...` — cùng origin với giao diện |
| Gọi thẳng server (dev) | `http://localhost:8100/api/v1/...` |
| Client Flutter | cấu hình **địa chỉ máy chủ**, client tự ghép `/api/v1` (`lib/core/config.dart`) |

Đổi phiên bản lớn: thêm router `/api/v2` song song, giữ `/api/v1` cho client cũ cho đến khi ngừng hỗ trợ.

## 2. Xác thực

1. `POST /api/v1/auth/login` — `application/x-www-form-urlencoded`: `username` (email), `password`.
   Trả về `{access_token, refresh_token, token_type, role, expires_in}`.
2. Mọi request sau: header `Authorization: Bearer <access_token>`.
3. Hết hạn (401): `POST /api/v1/auth/refresh` `{"refresh_token": "..."}` → cặp token mới (token cũ bị thu hồi;
   dùng lại token cũ ⇒ mọi phiên của tài khoản bị thu hồi).
4. `POST /api/v1/auth/logout` `{"refresh_token": "..."}` thu hồi cả hai token.

Quyền được kiểm **ở server** theo vai trò + phạm vi dữ liệu (Khoa, lớp mình dạy, con mình) — xem
[BUSINESS_LOGIC.md §3](../BUSINESS_LOGIC.md). Client chỉ ẩn/hiện chức năng, không quyết định quyền.

## 3. Request / response

- Thân request JSON (`application/json`), trừ đăng nhập (form) và tải ảnh (`multipart/form-data`:
  `POST /faces/enroll/{id}` trường `images`; `POST /sessions/{id}/recognize` trường `frame`;
  `POST /sessions/{id}/self-checkin` trường `frame` + `latitude`, `longitude`, `accuracy`, `is_mocked`; ★ trường `checkin_code` đã bỏ cùng mã QR).
- Thời gian trả về ISO 8601 **kèm múi giờ** (`2026-11-03T08:00:00+07:00`); ngày dạng `YYYY-MM-DD`; giờ `HH:MM:SS`.
- Ảnh trả về là đường dẫn tương đối đã ký: `/evidence/<...>.jpg?exp=<unix>&sig=<hmac>` — ghép với địa chỉ API
  (`/api/v1`) để tải, hết hạn sau 60 phút.
- Xuất Excel: `GET /reports/attendance/export?class_id=&semester=` trả tệp `.xlsx`
  (`Content-Disposition: attachment; filename="diemdanh_<lớp>_<học kỳ>.xlsx"`).

## 4. Danh sách, phân trang, tìm kiếm, lọc

| Tham số | Ý nghĩa |
|---|---|
| `limit`, `offset` | Phân trang; không truyền `limit` ⇒ trả hết (dùng cho dropdown) |
| `q` | Tìm kiếm (mã/tên tùy tài nguyên) |
| `semester`, `faculty_id`, `class_id`, `status`, `unit_id`, `location_id`, `building`, `only_active`, `date_from`, `date_to`, `action`, `success`, `unread_only` | Lọc theo trường tương ứng |
| Header `X-Total-Count` | Tổng số bản ghi khớp bộ lọc (trước phân trang) |

Endpoint có phân trang: `/students`, `/lecturers`, `/classes`, `/schedules`, `/parents`, `/staff`, `/audit-logs`.

## 5. Lỗi

Mọi lỗi cùng một dạng:

```json
{"detail": "Lop hoc phan khong ton tai", "code": "not_found"}
```

| HTTP | `code` | Khi nào |
|---|---|---|
| 400 | `bad_request` | Vi phạm quy tắc nghiệp vụ (trùng mã, ngoài khung giờ mở phiên, thiếu lý do…) |
| 401 | `unauthorized` | Thiếu/sai/hết hạn/bị thu hồi token, sai mật khẩu |
| 403 | `forbidden` | Không đủ vai trò hoặc ngoài phạm vi dữ liệu |
| 404 | `not_found` | Không tồn tại (hoặc không phải của bạn — không lộ sự tồn tại) |
| 409 | `conflict` | Dữ liệu đang được tham chiếu, trùng ràng buộc DB, sai phiên bản nội dung đồng ý |
| 422 | `validation_error` | Sai định dạng dữ liệu — `detail` là **danh sách** lỗi từng trường (`loc`, `msg`, `type`) |
| 429 | `too_many_requests` | Vượt giới hạn tần suất / khóa tạm do đăng nhập sai |
| 500 | `internal_error` | Lỗi không lường trước (đã ghi log kèm request id) |
| 503 | — | `GET /api/v1/health` khi mất kết nối CSDL |

Kết quả nghiệp vụ "không thành công nhưng hợp lệ" của tự điểm danh/quét camera **không** dùng mã lỗi HTTP: trả 200
với `status` (`recognized`, `confirming`, `unknown`, `spoof`, `already_checked`, `not_matched`, `no_face`,
`multiple_faces`, `consent_required`, `qr_required`, `qr_invalid`, `location_required`, `location_mocked`,
`location_inaccurate`, `out_of_range`) và `message` để giao diện hiển thị.

## 6. Truy vết

Mọi response có header `X-Request-ID` (client có thể tự gửi header này). Log server ghi mỗi request một dòng
`[request_id] fams.access: GET /api/v1/... -> 200 12ms user=<id>` — người dùng báo lỗi kèm mã này là tìm được log.

## 7. Giới hạn tần suất (theo IP)

| Endpoint | Giới hạn |
|---|---|
| `/auth/login` | 30/phút (+ khóa tài khoản 5 phút sau 5 lần sai) |
| `/auth/refresh` | 60/phút |
| `/auth/forgot-password` | 3/giờ |
| `/auth/reset-password` | 10/giờ |
| `/auth/change-password` | 10/phút (+ khóa sau 5 lần sai mật khẩu hiện tại) |

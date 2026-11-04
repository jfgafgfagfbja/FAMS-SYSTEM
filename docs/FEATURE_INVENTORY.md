# Danh mục chức năng FAMS (FEATURE_INVENTORY)

> **Tệp sinh tự động** từ `docs/tools/feature_inventory.py` — sửa dữ liệu ở đó rồi chạy lại,
> không sửa tay tệp này. Trạng thái lấy từ: danh sách route thực tế của server, độ phủ route khi
> chạy toàn bộ test (`server/tools/route_coverage_plugin.py`), kết quả pytest (JUnit XML),
> kết quả `flutter test` và kiểm thử tích hợp ghi trong `docs/TEST_REPORT.md`.

- Tiền tố API của phiên bản này: `/api/v1` — đường dẫn tài nguyên giữ nguyên như bản gốc.
- Tổng: **126** chức năng — ✅ hoạt động bình thường: **126**, đã chuyển đổi nhưng chưa kiểm thử: **0**, chưa hoàn thành/chưa đánh giá: **0**.
- Cột *Kiểm thử* với API: các mã HTTP mà bộ test đã thực sự nhận được từ endpoint (cả nhánh thành công
  lẫn nhánh bị từ chối). Với chức năng nội bộ/client: tên test làm bằng chứng.

## PH1. Xác thực và tài khoản

| Mã | Chức năng | Tác nhân | API / nơi xử lý | Màn hình | Chuyển đổi | Kiểm thử | Trạng thái |
|---|---|---|---|---|---|---|---|
| 1.01 | Đăng nhập email + mật khẩu | Mọi người dùng | `POST /api/v1/auth/login` | Đăng nhập | ✅ | ✅ HTTP 200, 401, 429 | Hoạt động bình thường |
| 1.02 | Khóa tạm sau 5 lần sai/5 phút, giới hạn 30 lần/phút/IP | Hệ thống | nội bộ: /auth/login | Đăng nhập | ✅ | ✅ `test_auth.py::test_login_rate_limited_after_five_attempts` | Hoạt động bình thường |
| 1.03 | Làm mới token xoay vòng, dùng lại token cũ ⇒ thu hồi tất cả | App | `POST /api/v1/auth/refresh` | (interceptor ApiClient) | ✅ | ✅ HTTP 200, 401 | Hoạt động bình thường |
| 1.04 | Đổi mật khẩu (giữ phiên hiện tại, đăng xuất phiên khác) | Mọi người dùng | `POST /api/v1/auth/change-password` | Tài khoản | ✅ | ✅ HTTP 200, 400, 401, 422, 429 | Hoạt động bình thường |
| 1.05 | Gửi OTP quên mật khẩu | Mọi người dùng | `POST /api/v1/auth/forgot-password` | Quên mật khẩu | ✅ | ✅ HTTP 200, 429 | Hoạt động bình thường |
| 1.06 | Đặt lại mật khẩu bằng OTP | Mọi người dùng | `POST /api/v1/auth/reset-password` | Đặt lại mật khẩu | ✅ | ✅ HTTP 200, 400, 422 | Hoạt động bình thường |
| 1.07 | Xem thông tin tài khoản + hồ sơ theo vai trò | Mọi người dùng | `GET /api/v1/auth/me` | Tài khoản, Trang chủ | ✅ | ✅ HTTP 200, 401 | Hoạt động bình thường |
| 1.08 | Đăng xuất (thu hồi access + refresh token) | Mọi người dùng | `POST /api/v1/auth/logout` | Khung ứng dụng | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 1.09 | Kiểm tra vai trò, phạm vi Khoa | Hệ thống | nội bộ: core/authz | (mọi trang) | ✅ | ✅ `test_authorization.py`, `test_unit_roles.py` | Hoạt động bình thường |
| 1.10 | Ảnh bằng chứng qua URL ký HMAC, hết hạn 60 phút | Hệ thống, cán bộ | `GET /api/v1/evidence/{file_path:path}` | Ảnh bằng chứng | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường · Thay đổi: Ảnh phục vụ ở /api/v1/evidence/... |
| 1.11 | Thu hồi token khi đổi/đặt lại mật khẩu (token_version) | Hệ thống | nội bộ: core/security | — | ✅ | ✅ `test_tokens_and_media.py::test_reset_password_revokes_refresh_tokens` | Hoạt động bình thường |
| 1.12 | Kiểm tra sức khỏe dịch vụ | Hệ thống, vận hành | `GET /` | — | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 1.13 | Kiểm tra sức khỏe kèm kết nối CSDL (đi qua nginx) | Vận hành | `GET /api/v1/health` | — | ✅ | ✅ HTTP 200 | Hoạt động bình thường · Thay đổi: Mới (healthcheck qua /api/v1) |
| 1.14 | Định dạng lỗi thống nhất {detail, code} + X-Request-ID | Mọi client | nội bộ: core/exceptions | (ApiClient đọc detail) | ✅ | ✅ `test_infrastructure.py` | Hoạt động bình thường · Thay đổi: Mới: thêm trường code, header X-Request-ID |

## PH2. Quản trị danh mục hệ thống

| Mã | Chức năng | Tác nhân | API / nơi xử lý | Màn hình | Chuyển đổi | Kiểm thử | Trạng thái |
|---|---|---|---|---|---|---|---|
| 2.01 | Xem danh sách đơn vị | Cán bộ | `GET /api/v1/units` | Đơn vị | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 2.02 | Thêm đơn vị | QTV | `POST /api/v1/units` | Đơn vị | ✅ | ✅ HTTP 200, 403, 422 | Hoạt động bình thường |
| 2.03 | Sửa đơn vị (không đổi loại) | QTV | `PATCH /api/v1/units/{unit_id}` | Đơn vị | ✅ | ✅ HTTP 200, 400, 404 | Hoạt động bình thường |
| 2.04 | Xóa đơn vị (chặn khi còn dữ liệu) | QTV | `DELETE /api/v1/units/{unit_id}` | Đơn vị | ✅ | ✅ HTTP 200, 409 | Hoạt động bình thường |
| 2.05 | Tra cứu cán bộ | QTV | `GET /api/v1/staff` | Cán bộ | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 2.06 | Tạo tài khoản cán bộ, vai trò suy ra từ đơn vị | QTV | `POST /api/v1/staff` | Cán bộ | ✅ | ✅ HTTP 200, 400 | Hoạt động bình thường |
| 2.07 | Sửa cán bộ | QTV | `PATCH /api/v1/staff/{staff_id}` | Cán bộ | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 2.08 | Xóa cán bộ (chặn khi đã sửa điểm danh) | QTV | `DELETE /api/v1/staff/{staff_id}` | Cán bộ | ✅ | ✅ HTTP 200, 404, 409 | Hoạt động bình thường |
| 2.09 | Xem danh sách địa điểm | Cán bộ, GV | `GET /api/v1/locations` | Địa điểm | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 2.10 | Thêm địa điểm (tối đa 1 mặc định) | QTV, P.ĐT | `POST /api/v1/locations` | Địa điểm | ✅ | ✅ HTTP 200, 403, 422 | Hoạt động bình thường |
| 2.11 | Sửa địa điểm | QTV, P.ĐT | `PATCH /api/v1/locations/{location_id}` | Địa điểm | ✅ | ✅ HTTP 200, 400, 404, 422 | Hoạt động bình thường |
| 2.12 | Xóa địa điểm (chặn khi gắn lịch) | QTV, P.ĐT | `DELETE /api/v1/locations/{location_id}` | Địa điểm | ✅ | ✅ HTTP 200, 409 | Hoạt động bình thường |
| 2.13 | Tra cứu phòng học | Cán bộ, GV | `GET /api/v1/rooms` | Phòng học | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 2.14 | Danh sách tòa nhà | Cán bộ, GV | `GET /api/v1/rooms/buildings` | Phòng học | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 2.15 | Thêm phòng học | QTV, P.ĐT | `POST /api/v1/rooms` | Phòng học | ✅ | ✅ HTTP 200, 400, 403, 422 | Hoạt động bình thường |
| 2.16 | Sửa, ngừng sử dụng phòng | QTV, P.ĐT | `PATCH /api/v1/rooms/{room_id}` | Phòng học | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 2.17 | Xóa phòng (chặn khi còn lịch) | QTV, P.ĐT | `DELETE /api/v1/rooms/{room_id}` | Phòng học | ✅ | ✅ HTTP 200, 400, 404 | Hoạt động bình thường |
| 2.18 | Lấy vị trí hiện tại khi nhập tọa độ | QTV, P.ĐT | client `geolocator` | Địa điểm, Phòng học | ✅ | ✅ `e2e:geolocator` | Hoạt động bình thường |

## PH3. Quản lý đào tạo

| Mã | Chức năng | Tác nhân | API / nơi xử lý | Màn hình | Chuyển đổi | Kiểm thử | Trạng thái |
|---|---|---|---|---|---|---|---|
| 3.01 | Tra cứu giảng viên | QTV, P.ĐT, Khoa | `GET /api/v1/lecturers` | Giảng viên | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 3.02 | Thêm giảng viên | QTV, P.ĐT | `POST /api/v1/lecturers` | Giảng viên | ✅ | ✅ HTTP 200, 400, 403 | Hoạt động bình thường |
| 3.03 | Sửa giảng viên | QTV, P.ĐT | `PATCH /api/v1/lecturers/{lecturer_id}` | Giảng viên | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 3.04 | Xóa giảng viên (chặn khi đang dạy/đã sửa điểm danh) | QTV, P.ĐT | `DELETE /api/v1/lecturers/{lecturer_id}` | Giảng viên | ✅ | ✅ HTTP 200, 409 | Hoạt động bình thường |
| 3.05 | Tra cứu lớp học phần | Cán bộ, GV | `GET /api/v1/classes` | Lớp học phần | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 3.06 | Xem chi tiết lớp | Cán bộ, GV | `GET /api/v1/classes/{class_id}` | Chi tiết lớp | ✅ | ✅ HTTP 200, 403, 404 | Hoạt động bình thường |
| 3.07 | Thêm lớp (VP Khoa: chỉ Khoa mình) | QTV, P.ĐT, VP Khoa | `POST /api/v1/classes` | Lớp học phần | ✅ | ✅ HTTP 200, 400, 403 | Hoạt động bình thường |
| 3.08 | Sửa lớp | QTV, P.ĐT, VP Khoa | `PATCH /api/v1/classes/{class_id}` | Chi tiết lớp | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 3.09 | Xóa lớp (chặn khi có SV/lịch) | QTV, P.ĐT, VP Khoa | `DELETE /api/v1/classes/{class_id}` | Chi tiết lớp | ✅ | ✅ HTTP 200, 403, 409 | Hoạt động bình thường |
| 3.10 | Danh sách SV của lớp | Cán bộ, GV | `GET /api/v1/classes/{class_id}/students` | Chi tiết lớp | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 3.11 | Ghi danh sinh viên | QTV, P.ĐT, VP Khoa | `POST /api/v1/classes/{class_id}/enroll/{student_id}` | Chi tiết lớp | ✅ | ✅ HTTP 200, 404 | Hoạt động bình thường |
| 3.12 | Rút sinh viên khỏi lớp | QTV, P.ĐT, VP Khoa | `DELETE /api/v1/classes/{class_id}/enroll/{student_id}` | Chi tiết lớp | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 3.13 | Lịch của một lớp | Cán bộ, GV, SV | `GET /api/v1/classes/{class_id}/schedules` | Chi tiết lớp | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 3.14 | Tra cứu toàn bộ lịch | Cán bộ | `GET /api/v1/schedules` | Lịch học | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 3.15 | Thêm lịch (chống trùng phòng) | QTV, P.ĐT, VP Khoa | `POST /api/v1/classes/schedules` | Chi tiết lớp | ✅ | ✅ HTTP 200, 400, 403, 422 | Hoạt động bình thường |
| 3.16 | Sửa lịch (chống trùng phòng) | QTV, P.ĐT, VP Khoa | `PATCH /api/v1/classes/schedules/{schedule_id}` | Chi tiết lớp | ✅ | ✅ HTTP 200, 400 | Hoạt động bình thường |
| 3.17 | Xóa lịch (chặn khi đã có phiên) | QTV, P.ĐT, VP Khoa | `DELETE /api/v1/classes/schedules/{schedule_id}` | Chi tiết lớp | ✅ | ✅ HTTP 200, 409 | Hoạt động bình thường |
| 3.18 | Lịch theo tuần (kèm trạng thái phiên, điểm danh) | SV, GV, cán bộ | `GET /api/v1/schedules/week` | Lịch tuần | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 3.19 | Lịch dạy hôm nay | GV | `GET /api/v1/lecturers/me/today-schedules` | Trang chủ GV | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 3.20 | In lịch tuần ra PDF | SV, GV | client `schedule_pdf` | Lịch tuần | ✅ | ✅ `flutter:schedule_pdf_test.dart` | Hoạt động bình thường |

## PH4. Quản lý người học

| Mã | Chức năng | Tác nhân | API / nơi xử lý | Màn hình | Chuyển đổi | Kiểm thử | Trạng thái |
|---|---|---|---|---|---|---|---|
| 4.01 | Tra cứu sinh viên | Cán bộ, GV | `GET /api/v1/students` | Sinh viên | ✅ | ✅ HTTP 200, 401, 403 | Hoạt động bình thường |
| 4.02 | Xem chi tiết sinh viên | Cán bộ, GV | `GET /api/v1/students/{student_id}` | Chi tiết SV | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 4.03 | Hồ sơ của chính SV | SV | `GET /api/v1/students/me` | Tài khoản | ✅ | ✅ HTTP 200, 401 | Hoạt động bình thường |
| 4.04 | Thêm sinh viên | QTV, P.CTSV | `POST /api/v1/students` | Sinh viên | ✅ | ✅ HTTP 200, 400, 403 | Hoạt động bình thường |
| 4.05 | Sửa sinh viên | QTV, P.CTSV | `PATCH /api/v1/students/{student_id}` | Chi tiết SV | ✅ | ✅ HTTP 200, 400, 403 | Hoạt động bình thường |
| 4.06 | Xóa sinh viên (chặn khi có dữ liệu) | QTV, P.CTSV | `DELETE /api/v1/students/{student_id}` | Chi tiết SV | ✅ | ✅ HTTP 200, 409 | Hoạt động bình thường |
| 4.07 | Nội dung đồng ý sinh trắc (có phiên bản) | Mọi người dùng | `GET /api/v1/students/consent-policy` | Khuôn mặt | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 4.08 | Ghi nhận đồng ý (SV tự / cán bộ nhập bản giấy) | SV, QTV, P.CTSV | `POST /api/v1/students/{student_id}/consent` | Khuôn mặt, Chi tiết SV | ✅ | ✅ HTTP 200, 400, 403, 409 | Hoạt động bình thường |
| 4.09 | Rút đồng ý (xóa toàn bộ dữ liệu khuôn mặt) | SV, QTV, P.CTSV | `POST /api/v1/students/{student_id}/consent/withdraw` | Khuôn mặt, Chi tiết SV | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 4.10 | Xem danh sách phụ huynh | QTV, P.CTSV, P.ĐT | `GET /api/v1/parents` | Phụ huynh | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 4.11 | Thêm phụ huynh | QTV, P.CTSV | `POST /api/v1/parents` | Phụ huynh | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 4.12 | Sửa phụ huynh | QTV, P.CTSV | `PATCH /api/v1/parents/{parent_id}` | Phụ huynh | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 4.13 | Xóa phụ huynh | QTV, P.CTSV | `DELETE /api/v1/parents/{parent_id}` | Phụ huynh | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 4.14 | Xem con đã liên kết | QTV, P.CTSV, P.ĐT | `GET /api/v1/parents/{parent_id}/children` | Phụ huynh | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 4.15 | Liên kết con bằng MSSV | QTV, P.CTSV | `POST /api/v1/parents/{parent_id}/children` | Phụ huynh | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 4.16 | Gỡ liên kết con | QTV, P.CTSV | `DELETE /api/v1/parents/{parent_id}/children/{student_id}` | Phụ huynh | ✅ | ✅ HTTP 200, 404 | Hoạt động bình thường |

## PH5. Sinh trắc khuôn mặt

| Mã | Chức năng | Tác nhân | API / nơi xử lý | Màn hình | Chuyển đổi | Kiểm thử | Trạng thái |
|---|---|---|---|---|---|---|---|
| 5.01 | Đăng ký khuôn mặt (quyền, đồng ý, chất lượng, chống giả mạo, trùng) | SV, P.CTSV, QTV, GV | `POST /api/v1/faces/enroll/{student_id}` | Khuôn mặt, Đăng ký hộ | ✅ | ✅ HTTP 200, 400, 403 | Hoạt động bình thường |
| 5.02 | Danh sách chờ duyệt kèm cảnh báo trùng | QTV, P.CTSV | `GET /api/v1/faces/pending` | Duyệt khuôn mặt | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 5.03 | Duyệt khuôn mặt (xóa ảnh tạm) | QTV, P.CTSV | `PATCH /api/v1/faces/{embedding_id}/approve` | Duyệt khuôn mặt | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 5.04 | Từ chối khuôn mặt có lý do (xóa ảnh tạm) | QTV, P.CTSV | `PATCH /api/v1/faces/{embedding_id}/reject` | Duyệt khuôn mặt | ✅ | ✅ HTTP 200, 400 | Hoạt động bình thường |
| 5.05 | SV xem dữ liệu khuôn mặt của mình | SV | `GET /api/v1/faces/mine` | Khuôn mặt | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 5.06 | SV xóa dữ liệu khuôn mặt | SV | `DELETE /api/v1/faces/mine` | Khuôn mặt | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 5.07 | Chụp ảnh bằng camera (web/di động) | SV, GV, cán bộ | client `camera_capture` | Khuôn mặt, Quét lớp, Tự điểm danh | ✅ | ✅ `flutter:camera_lifecycle_test.dart` | Hoạt động bình thường |
| 5.08 | Chống giả mạo MiniFASNet (tự tắt khi thiếu model) | Hệ thống | nội bộ: antispoof_service | — | ✅ | ✅ `test_antispoof.py` | Hoạt động bình thường |

## PH6. Điểm danh

| Mã | Chức năng | Tác nhân | API / nơi xử lý | Màn hình | Chuyển đổi | Kiểm thử | Trạng thái |
|---|---|---|---|---|---|---|---|
| 6.01 | Mở phiên (khung giờ, mỗi lịch 1 phiên/ngày) | GV, QTV | `POST /api/v1/sessions` | Lịch dạy, Phiên | ✅ | ✅ HTTP 200, 400, 403 | Hoạt động bình thường |
| 6.02 | Tra cứu phiên | Cán bộ, GV | `GET /api/v1/sessions` | Phiên điểm danh | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 6.03 | Xem chi tiết phiên | Cán bộ, GV | `GET /api/v1/sessions/{session_id}` | Kết quả phiên | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 6.04 | Bật/tắt yêu cầu quét QR | GV, QTV | `PATCH /api/v1/sessions/{session_id}` | Kết quả phiên | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 6.05 | Đóng phiên, sinh vắng, báo SV vừa vượt ngưỡng | GV, QTV | `PATCH /api/v1/sessions/{session_id}/close` | Kết quả phiên | ✅ | ✅ HTTP 200, 400 | Hoạt động bình thường |
| 6.06 | Tự đóng phiên quá hạn (60 s/lần) | Hệ thống | nền: run_auto_close_loop | — | ✅ | ✅ `test_flow_fixes.py::test_auto_close_expired_sessions_marks_absent`, `test_flow_fixes.py::test_auto_close_keeps_sessions_within_deadline` | Hoạt động bình thường |
| 6.07 | Quét camera cả lớp, nhận diện nhiều mặt | GV, QTV | `POST /api/v1/sessions/{session_id}/recognize` | Quét lớp | ✅ | ✅ HTTP 200, 400 | Hoạt động bình thường |
| 6.08 | Xác nhận 2 khung hình trước khi ghi | Hệ thống | nội bộ: /recognize | Quét lớp | ✅ | ✅ `test_confirm_frames.py` | Hoạt động bình thường |
| 6.09 | SV xem yêu cầu buổi học (QR, phòng) | SV | `GET /api/v1/sessions/{session_id}/checkin-info` | Tự điểm danh | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 6.10 | Chiếu mã QR luân phiên 30 s | GV, QTV | `GET /api/v1/sessions/{session_id}/checkin-code` | Mã QR phiên | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 6.11 | Quét mã QR / nhập 6 chữ số | SV | client `qr_scanner` | Tự điểm danh | ✅ | ✅ `flutter:checkin_qr_test.dart` | Hoạt động bình thường |
| 6.12 | Đối chiếu GPS (giả lập, sai số, bán kính) | Hệ thống | nội bộ: geo_service | Tự điểm danh | ✅ | ✅ `test_location_checkin.py` | Hoạt động bình thường |
| 6.13 | SV tự điểm danh bằng ảnh + GPS + QR | SV | `POST /api/v1/sessions/{session_id}/self-checkin` | Tự điểm danh | ✅ | ✅ HTTP 200, 400 | Hoạt động bình thường |
| 6.14 | Xác nhận tay | GV, QTV | `POST /api/v1/sessions/{session_id}/manual` | Kết quả phiên | ✅ | ✅ HTTP 200, 400 | Hoạt động bình thường |
| 6.15 | Danh sách lớp trong phiên (roster) | Cán bộ, GV | `GET /api/v1/sessions/{session_id}/roster` | Kết quả phiên | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 6.16 | Danh sách bản ghi của phiên | Cán bộ, GV | `GET /api/v1/sessions/{session_id}/records` | Kết quả phiên | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 6.17 | Sửa trạng thái / duyệt có phép (bắt buộc lý do) | GV, QTV, P.CTSV, LĐ Khoa | `PATCH /api/v1/sessions/{session_id}/records/{record_id}` | Kết quả phiên | ✅ | ✅ HTTP 200, 400, 403, 422 | Hoạt động bình thường |
| 6.18 | Xem lịch sử sửa điểm danh | Cán bộ, GV | `GET /api/v1/sessions/{session_id}/records/{record_id}/audits` | Kết quả phiên | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |

## PH7. Thông báo

| Mã | Chức năng | Tác nhân | API / nơi xử lý | Màn hình | Chuyển đổi | Kiểm thử | Trạng thái |
|---|---|---|---|---|---|---|---|
| 7.01 | Sinh thông báo phụ huynh khi điểm danh/đổi trạng thái | Hệ thống | nội bộ: parent_notify | — | ✅ | ✅ `test_parent_notifications.py::test_checkin_notifies_parent`, `test_parent_notifications.py::test_status_correction_sends_update`, `test_parent_notifications.py::test_flipping_back_does_not_duplicate` | Hoạt động bình thường |
| 7.02 | Xem hộp thư thông báo | PH | `GET /api/v1/notifications` | Thông báo | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 7.03 | Đếm chưa đọc (chuông) | PH | `GET /api/v1/notifications/unread-count` | Chuông thông báo | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 7.04 | Đánh dấu đã đọc | PH | `POST /api/v1/notifications/{notification_id}/read` | Thông báo | ✅ | ✅ HTTP 200, 404 | Hoạt động bình thường |
| 7.05 | Đánh dấu đọc tất cả | PH | `POST /api/v1/notifications/read-all` | Thông báo | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 7.06 | Gửi email theo hàng đợi, thử lại tối đa 3 lần | Hệ thống | nền: run_notification_email_loop | — | ✅ | ✅ `test_parent_notifications.py::test_pending_email_is_sent`, `test_parent_notifications.py::test_failed_email_retried_then_given_up`, `test_parent_notifications.py::test_smtp_down_does_not_lose_mail` | Hoạt động bình thường |
| 7.07 | Xem tùy chọn nhận thông báo | PH | `GET /api/v1/parents/me/preferences` | Tài khoản | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 7.08 | Cập nhật tùy chọn nhận thông báo | PH | `PATCH /api/v1/parents/me/preferences` | Tài khoản | ✅ | ✅ HTTP 200 | Hoạt động bình thường |

## PH8. Báo cáo, thống kê

| Mã | Chức năng | Tác nhân | API / nơi xử lý | Màn hình | Chuyển đổi | Kiểm thử | Trạng thái |
|---|---|---|---|---|---|---|---|
| 8.01 | SV xem chuyên cần chi tiết theo học kỳ | SV | `GET /api/v1/students/me/attendance` | Chuyên cần | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 8.02 | SV xem tóm tắt chuyên cần | SV | `GET /api/v1/reports/my-attendance` | Chuyên cần | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 8.03 | Cán bộ xem chuyên cần một SV | Cán bộ | `GET /api/v1/students/{student_id}/attendance` | Chi tiết SV | ✅ | ✅ HTTP 200 | Hoạt động bình thường |
| 8.04 | Thống kê chuyên cần theo lớp | Cán bộ, GV | `GET /api/v1/reports/attendance/{class_id}` | Báo cáo | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 8.05 | Cảnh báo vắng ≥ 20 % | Cán bộ, GV | `GET /api/v1/reports/attendance/warnings` | Báo cáo | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 8.06 | Xuất Excel bảng điểm danh | Cán bộ, GV | `GET /api/v1/reports/attendance/export` | Báo cáo | ✅ | ✅ HTTP 200, 400, 403 | Hoạt động bình thường |
| 8.07 | Danh sách con của phụ huynh | PH | `GET /api/v1/parents/me/children` | Con của tôi | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 8.08 | Chuyên cần của con | PH | `GET /api/v1/parents/me/children/{student_id}/attendance` | Chuyên cần của con | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 8.09 | Thống kê tổng hợp, so sánh theo Khoa | QTV, P.ĐT, P.CTSV, Khoa, Ban ngành | `GET /api/v1/reports/overview` | Tổng quan | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 8.10 | Biểu đồ chuyên cần | Mọi vai trò xem báo cáo | client `fl_chart` | Tổng quan, Chuyên cần | ✅ | ✅ `flutter:feedback_pages_test.dart` | Hoạt động bình thường |

## PH9. Nhật ký hệ thống

| Mã | Chức năng | Tác nhân | API / nơi xử lý | Màn hình | Chuyển đổi | Kiểm thử | Trạng thái |
|---|---|---|---|---|---|---|---|
| 9.01 | Ghi vết sửa điểm danh (attendance_audits) | Hệ thống | nội bộ: PATCH records | — | ✅ | ✅ `test_session_detail_and_records.py` | Hoạt động bình thường |
| 9.02 | Ghi đăng nhập, đăng nhập sai, khóa, đăng xuất | Hệ thống | nội bộ: services/audit | — | ✅ | ✅ `test_audit_log.py::test_login_success_is_logged`, `test_audit_log.py::test_failed_login_logged_without_password`, `test_audit_log.py::test_logout_is_logged` | Hoạt động bình thường |
| 9.03 | Ghi tự động mọi thêm/sửa/xóa dữ liệu quản lý | Hệ thống | nội bộ: services/audit | — | ✅ | ✅ `test_audit_log.py::test_create_is_logged_with_actor`, `test_audit_log.py::test_update_records_old_and_new_values`, `test_audit_log.py::test_password_change_never_stores_the_hash` | Hoạt động bình thường |
| 9.04 | Ghi xuất báo cáo | Hệ thống | nội bộ: services/audit | — | ✅ | ✅ `test_audit_log.py::test_report_export_is_logged` | Hoạt động bình thường |
| 9.05 | Tra cứu, lọc nhật ký (LĐ Khoa chỉ Khoa mình) | QTV, LĐ Khoa | `GET /api/v1/audit-logs` | Nhật ký hệ thống | ✅ | ✅ HTTP 200, 403 | Hoạt động bình thường |
| 9.06 | Dọn ảnh bằng chứng quá 90 ngày | Hệ thống | nền: run_cleanup_loop | — | ✅ | ✅ `test_evidence_cleanup.py` | Hoạt động bình thường |
| 9.07 | Nhật ký ứng dụng (log dịch vụ) | Vận hành | nội bộ: logging | — | ✅ | ✅ `test_infrastructure.py` | Hoạt động bình thường · Thay đổi: Mới: log có request-id, định dạng thống nhất |

## PH10. Giao diện chung (client)

| Mã | Chức năng | Tác nhân | API / nơi xử lý | Màn hình | Chuyển đổi | Kiểm thử | Trạng thái |
|---|---|---|---|---|---|---|---|
| 10.01 | Điều hướng theo vai trò, chặn route không có quyền | Mọi người dùng | client `router.dart` | (toàn ứng dụng) | ✅ | ✅ `flutter:access_test.dart` | Hoạt động bình thường |
| 10.02 | Đăng nhập, nhập địa chỉ máy chủ | Mọi người dùng | client `login_page` | Đăng nhập | ✅ | ✅ `flutter:login_page_test.dart` | Hoạt động bình thường |
| 10.03 | Đổi mật khẩu trên giao diện | Mọi người dùng | client `account_page` | Tài khoản | ✅ | ✅ `flutter:change_password_test.dart` | Hoạt động bình thường |
| 10.04 | Thông báo phụ huynh trên giao diện | PH | client `notification_bell` | Thông báo | ✅ | ✅ `flutter:parent_notifications_test.dart` | Hoạt động bình thường |
| 10.05 | Đọc dữ liệu API (models) | — | client `models.dart` | — | ✅ | ✅ `flutter:models_test.dart` | Hoạt động bình thường |
| 10.06 | Định dạng ngày, phần trăm, trạng thái | — | client `formatters.dart` | — | ✅ | ✅ `flutter:formatters_test.dart` | Hoạt động bình thường |
| 10.07 | Giao diện sáng/tối | Mọi người dùng | client `theme` | Tài khoản | ✅ | ✅ `e2e:theme` | Hoạt động bình thường |

## Đối chiếu route ↔ danh mục

Mọi route của server (98) đều đã có trong danh mục.


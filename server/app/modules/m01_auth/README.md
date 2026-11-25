# MOD-01 – Xác thực và tài khoản (PH1)

| Mục | Nội dung |
|---|---|
| Người phụ trách | **TV1 – trưởng nhóm** (GitHub: [@jfgafgfagfbja](https://github.com/jfgafgfagfbja)) |
| Phạm vi | Đăng nhập, refresh token xoay vòng, đăng xuất (thu hồi token), đổi / quên / đặt lại mật khẩu bằng OTP, thông tin tài khoản theo vai trò, tạo / xóa tài khoản dùng chung cho các mô-đun khác, ảnh bằng chứng qua URL ký HMAC, kiểm tra sức khỏe dịch vụ |
| Chức năng trong báo cáo | MOD-01-01 … MOD-01-04 (1.1.1 – 1.4.4) |

## Tổ chức theo MVC

| Tệp | Vai trò MVC | Nội dung |
|---|---|---|
| `models.py` | **Model** | `User`, `RefreshToken`, `RevokedToken`, `PasswordReset` + hằng số vai trò `ROLE_*` |
| `repository.py` | Model (truy cập dữ liệu) | Truy vấn `users`, OTP, refresh token, dọn dữ liệu khi xóa tài khoản |
| `schemas.py` | **View** (dữ liệu vào / ra JSON) | `Token`, `MeOut`, `RefreshRequest`, `LogoutRequest`, `ForgotPasswordRequest`, `ResetPasswordRequest`, `ChangePasswordRequest` |
| `controller.py` | **Controller** | Router `/api/v1/auth/*` – chỉ nhận request, gọi service |
| `health_controller.py`, `media_controller.py` | Controller | `GET /`, `GET /api/v1/health`, `GET /api/v1/evidence/...` |
| `service.py` | Nghiệp vụ | Đăng nhập (khóa tạm sau 5 lần sai / 5 phút), refresh, OTP, đổi mật khẩu, `me` |
| `account_service.py` | Nghiệp vụ dùng chung | Tạo / xóa tài khoản cho cán bộ, giảng viên, sinh viên, phụ huynh (MOD-02, 03, 04 gọi) |
| `media_service.py` | Nghiệp vụ | Kiểm chữ ký, hạn URL ảnh |

Client: `client/lib/modules/m01_auth/` – `controllers/auth_controller.dart` (trạng thái đăng nhập), `views/`
(đăng nhập, quên / đặt lại mật khẩu, tài khoản, splash). Test: `server/tests/m01_auth/`, `client/test/login_page_test.dart`,
`client/test/change_password_test.dart`.

## API (10)

| Method | Đường dẫn | Xác thực |
|---|---|---|
| POST | `/api/v1/auth/login` | — (form `username`, `password`) |
| POST | `/api/v1/auth/refresh` | — |
| POST | `/api/v1/auth/logout` | Bearer |
| POST | `/api/v1/auth/change-password` | Bearer |
| POST | `/api/v1/auth/forgot-password` | — |
| POST | `/api/v1/auth/reset-password` | — |
| GET | `/api/v1/auth/me` | Bearer |
| GET | `/`, `/api/v1/health` | — |
| GET | `/api/v1/evidence/{file_path}?exp=&sig=` | URL có chữ ký |

## Bảng CSDL

`users`, `refresh_tokens`, `revoked_tokens`, `password_resets` (kho D1 trong DFD).

## Quy ước cho các mô-đun khác (mẫu để TV2 – TV5 làm theo)

1. Tạo `server/app/modules/mXX_<ten>/` với `models.py`, `repository.py`, `schemas.py`, `service.py`, `controller.py`, `README.md`.
2. Chuyển tệp bằng `git mv` (giữ lịch sử), sửa import, chuyển test vào `server/tests/mXX_<ten>/`.
3. Model: chuyển lớp từ `app/db/models.py` sang `models.py` của mô-đun, rồi thêm dòng import lại trong `app/db/models.py`
   (như khối MOD-01 ở đầu tệp) để code cũ và Alembic vẫn chạy.
4. Đăng ký router trong `app/api/v1/router.py`, chạy `pytest` (phải đạt 100 %) trước khi mở Pull Request.
5. Thêm thư mục của mình vào `.github/CODEOWNERS`.

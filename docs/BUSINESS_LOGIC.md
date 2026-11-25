# Nghiệp vụ của FAMS

> Trích từ mã nguồn bản gốc (`D:\FAMS`, 03/11/2026). Đây là **chuẩn đối chiếu**: sau tái cấu trúc,
> mọi quy tắc dưới đây phải giữ nguyên (cùng mã HTTP, cùng thông báo lỗi). Các ngưỡng có ghi
> `BIẾN` đọc từ cấu hình môi trường (`server/app/core/config.py`).
>
> **Cập nhật 10/11/2026 theo góp ý nghiệp vụ** (các mục đánh dấu ★): chỉ P.CTSV duyệt khuôn mặt; kết quả duyệt
> (khuôn mặt, đơn xin phép) gửi cho sinh viên và sinh viên xác nhận đã nhận; từ chối phải ghi lý do không hợp lệ;
> Văn phòng Khoa không ghi danh, không xếp lịch; thêm đơn xin phép vắng (GV lớp / Lãnh đạo Khoa duyệt); bỏ hẳn mã QR;
> cảnh báo vắng phát ra sau khi thống kê (gửi SV + phụ huynh); `schedules.room` chuẩn hóa (3NF).

## 1. Ngưỡng và tham số nghiệp vụ

| Tham số (`BIẾN`) | Mặc định | Ý nghĩa |
|---|---|---|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 480 | Hạn access token (JWT HS256) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 30 | Hạn refresh token |
| `OTP_EXPIRE_MINUTES` | 10 | Hạn OTP quên mật khẩu (6 chữ số) |
| `LOGIN_RATE_LIMIT` | 30/minute | Giới hạn đăng nhập theo IP |
| `LOGIN_MAX_FAILED_PER_ACCOUNT` / `LOGIN_FAILED_WINDOW_MINUTES` | 5 / 5 | Khóa tạm tài khoản sau 5 lần sai trong 5 phút |
| (cố định) | 60/phút, 3/giờ, 10/giờ, 10/phút | Giới hạn `/auth/refresh`, `/forgot-password`, `/reset-password`, `/change-password` theo IP |
| `RECOGNITION_THRESHOLD` | 0.45 | Độ giống cosine tối thiểu để nhận ra SV |
| `DUPLICATE_THRESHOLD` | 0.60 | Cảnh báo/từ chối khi khuôn mặt giống SV khác |
| `CONFIRM_FRAMES` | 2 | Số khung hình phải nhận ra SV trước khi ghi điểm danh (quét camera) |
| `LATE_AFTER_MINUTES` | 15 | Sau giờ bắt đầu + 15 phút ⇒ "muộn" |
| `EARLY_OPEN_MINUTES` | 15 | Được mở phiên sớm 15 phút trước giờ học |
| `SESSION_GRACE_MINUTES` | 30 | Sau giờ kết thúc + 30 phút: ngừng nhận điểm danh và tự đóng phiên |
| `ABSENCE_WARN_RATIO` | 0.2 | Tỉ lệ vắng (không tính có phép) ≥ 20 % ⇒ cảnh báo |
| `SELF_CHECKIN_REQUIRE_LOCATION` | True | Bắt buộc đối chiếu GPS khi đã cấu hình địa điểm |
| `SELF_CHECKIN_MAX_ACCURACY_M` | 100 | Sai số GPS tối đa chấp nhận |
| `ROOM_MIN_RADIUS_M` | 50 | Bán kính tối thiểu khi dùng tọa độ riêng của phòng |
| `LEAVE_REQUEST_MAX_PAST_DAYS` ★ | 7 | Đơn xin phép được nộp bổ sung cho buổi đã qua tối đa 7 ngày |
| `MEDIA_URL_EXPIRE_MINUTES` | 60 | Hạn URL ảnh có chữ ký (làm tròn khối 5 phút) |
| `EVIDENCE_RETENTION_DAYS` | 90 | Ảnh bằng chứng quá hạn bị xóa tự động |
| `ANTISPOOF_ENABLED` / `ANTISPOOF_THRESHOLD` | True / 0.5 | Chống giả mạo (tự tắt nếu thiếu model) |
| `NOTIFY_EMAIL_INTERVAL_SECONDS` / `NOTIFY_EMAIL_MAX_ATTEMPTS` | 15 / 3 | Hàng đợi email phụ huynh |
| `APP_UTC_OFFSET_MINUTES` | 420 | Múi giờ (+07:00) gắn vào chuỗi thời gian trả về |
| (cố định, face_service) | 112 px / 40 / 60 | Ảnh đăng ký: cạnh mặt ≥ 112 px, độ sáng TB ≥ 40, độ nét (Laplacian) ≥ 60 |
| (validator) | 8 ký tự | Độ dài tối thiểu mật khẩu khi tạo cán bộ/đặt lại/đổi mật khẩu |
| (validator) | 10–5000 m | Bán kính địa điểm |

## 2. Xác thực (PH1)

1. **Đăng nhập** `POST /auth/login` (form `username`, `password`):
   - Quá 5 lần sai/5 phút cho cùng email ⇒ 429 "Dang nhap sai qua nhieu lan…" (ghi nhật ký `auth.login_locked`).
   - Sai email hoặc mật khẩu ⇒ 401 "Sai email hoac mat khau" (ghi `auth.login_failed`, có email, không có mật khẩu).
   - Thành công ⇒ access token (claim `sub`, `role`, `jti`, `tv`=token_version) + refresh token + `role`, `expires_in`; ghi `auth.login`.
2. **Refresh xoay vòng** `POST /auth/refresh`: chỉ lưu SHA-256 của refresh token. Mỗi lần đổi ⇒ token cũ thu hồi, cấp token mới.
   Dùng lại token đã thu hồi ⇒ **thu hồi mọi refresh token của tài khoản** và trả 401.
3. **Kiểm token mỗi request**: chữ ký + hạn; `jti` không nằm trong `revoked_tokens`; user tồn tại;
   `tv` trong token = `users.token_version` (token không có `tv` coi như 0).
4. **Đăng xuất**: thêm `jti` vào `revoked_tokens`; thu hồi refresh token gửi kèm (chỉ của chính user).
5. **Quên mật khẩu**: luôn trả thông báo chung (không lộ email tồn tại); tạo OTP 6 số, lưu bcrypt hash, hạn 10 phút;
   SMTP chưa cấu hình ⇒ ghi OTP ra log (chế độ DEV).
6. **Đặt lại mật khẩu**: OTP phải khớp **một trong các** yêu cầu còn hạn, chưa dùng ⇒ đánh dấu đã dùng, đổi mật khẩu,
   tăng `token_version` (mọi access token cũ chết), thu hồi mọi refresh token.
7. **Đổi mật khẩu**: phải đúng mật khẩu hiện tại (sai 5 lần/5 phút ⇒ 429); mật khẩu mới phải khác cũ;
   tăng `token_version`, thu hồi refresh token, **cấp token mới cho phiên hiện tại**.
8. **`GET /auth/me`**: thông tin cơ bản + hồ sơ theo vai trò (SV: mã, ngành, khóa, Khoa, đồng ý, trạng thái khuôn mặt,
   cờ `consent_outdated`, lớp đã ghi danh; GV: mã, bộ môn, Khoa, lớp đang dạy; cán bộ: đơn vị, chức vụ).

## 3. Phân quyền (core/authz.py)

| Chức năng | Admin | P.ĐT | P.CTSV | Lãnh đạo Khoa | VP Khoa | Ban ngành | GV | SV | PH |
|---|---|---|---|---|---|---|---|---|---|
| Đơn vị, tài khoản cán bộ | Sửa | – | – | – | – | – | – | – | – |
| Lớp học phần ★ | Sửa | Sửa | Xem | Xem* | Sửa* | – | Xem (lớp mình) | – | – |
| Ghi danh, xếp lịch ★ | Sửa | Sửa | Xem | Xem* | **Xem*** | – | Xem (lớp mình) | lịch lớp mình | – |
| Phòng học, địa điểm | Sửa | Sửa | Xem | Xem | Xem | – | Xem | – | – |
| Hồ sơ giảng viên | Sửa | Sửa | – | Xem* | Xem* | – | – | – | – |
| Hồ sơ SV | Sửa | Xem | Sửa | Xem* | Xem* | – | Xem (SV lớp mình) | của mình | con mình |
| Phụ huynh | Sửa | Xem | Sửa | – | – | – | – | – | – |
| Duyệt khuôn mặt ★ | **–** | – | Sửa | – | – | – | – | xác nhận kết quả | – |
| Đăng ký khuôn mặt hộ | Có | – | Có | – | – | – | SV lớp mình | của mình | – |
| Mở phiên, quét, xác nhận tay, sửa mọi trạng thái | Có | – | – | – | – | – | lớp mình | – | – |
| Đơn xin phép vắng ★ | Xem | – | Xem | Duyệt* | – | – | Duyệt (lớp mình) | Nộp, xác nhận kết quả | – |
| Duyệt "Có phép" / hủy duyệt | Có | – | Có | Có* | – | – | (sửa mọi trạng thái) | – | – |
| Điểm danh chi tiết, cảnh báo, xuất Excel | Xem | Xem | Xem | Xem* | Xem* | – | lớp mình | – | – |
| Thống kê tổng hợp | Xem | Xem | Xem | Xem* | Xem* | Xem | – | – | – |
| Nhật ký hệ thống | Xem | – | – | Xem* | – | – | – | – | – |

`*` chỉ trong Khoa của đơn vị cán bộ. Quy tắc phạm vi:
- **Lớp**: Khoa xem lớp có `classes.faculty_id` = đơn vị mình; GV xem lớp có `lecturer_id` = mình.
- **SV**: Khoa xem SV có `students.faculty_id` = đơn vị mình; GV xem SV có ghi danh vào lớp mình dạy; PH xem con đã liên kết.
- **Lãnh đạo Khoa duyệt có phép** khi SV thuộc Khoa **hoặc** lớp thuộc Khoa.
- **VP Khoa tạo lớp** ⇒ lớp luôn thuộc Khoa mình; chỉ định Khoa khác ⇒ 403; tài khoản chưa gắn Khoa ⇒ 403.
- ★ **Ghi danh SV và xếp lịch** chỉ Quản trị viên / P. Đào tạo; VP Khoa gọi ⇒ 403 "Chi Quan tri vien hoac Phong Dao tao
  duoc ghi danh va xep lich hoc" (kể cả lớp thuộc Khoa mình).
- ★ **Duyệt đơn xin phép**: GV dạy lớp của buổi; Lãnh đạo Khoa khi SV hoặc lớp thuộc Khoa; người khác ⇒ 403.
- Tài khoản Khoa chưa gắn đơn vị ⇒ thấy danh sách rỗng (lọc theo id −1).
- `faculty_id` truyền lên phải là đơn vị loại `faculty`, không thì 400 "Khoa khong hop le".
- Thiếu vai trò ⇒ 403 "Khong du quyen"; sai phạm vi ⇒ 403 với thông báo riêng của từng đối tượng.

## 4. Danh mục hệ thống (PH2)

- **Đơn vị**: mã duy nhất (400); không đổi loại khi sửa; xóa bị chặn (409) khi còn cán bộ, SV, GV hoặc lớp gắn với đơn vị.
- **Cán bộ**: email duy nhất; vai trò suy ra từ loại đơn vị; đơn vị loại Khoa có hai vai trò (cờ `faculty_leader`:
  Lãnh đạo Khoa / Văn phòng Khoa); cờ này với đơn vị khác ⇒ 400 "Chi don vi loai Khoa moi co Lanh dao Khoa";
  xóa bị chặn (409) nếu từng sửa điểm danh (giữ vết).
- **Địa điểm**: mã duy nhất; tọa độ hợp lệ, bán kính 10–5000 m; **tối đa một địa điểm mặc định** (bật mặc định cho
  một nơi ⇒ tắt ở nơi khác); xóa bị chặn (409) khi đang gắn với lịch học.
- **Phòng học**: mã duy nhất; thuộc một khu vực (location) tồn tại; tọa độ riêng phải đủ cả vĩ độ lẫn kinh độ hoặc
  bỏ trống cả hai; bán kính hiệu lực = max(bán kính phòng, 50 m); phòng **ngừng sử dụng** bị ẩn khi xếp lịch mới
  nhưng lịch cũ giữ nguyên; xóa phòng đang có lịch ⇒ 400, gợi ý ngừng sử dụng.

## 5. Đào tạo (PH3)

- **Giảng viên**: email, mã GV duy nhất; xóa bị chặn (409) khi đang phụ trách lớp hoặc có lịch sử sửa điểm danh.
- **Lớp học phần**: mã lớp duy nhất (400); giảng viên phải tồn tại (400); xóa bị chặn (409) khi đã có SV ghi danh
  hoặc đã có lịch học. Danh sách kèm sĩ số, lọc `q` (mã lớp/tên môn), học kỳ, Khoa, phân trang `limit/offset` +
  header `X-Total-Count`.
- **Ghi danh**: SV phải tồn tại (404); đã ghi danh ⇒ 400; rút khỏi lớp chưa ghi danh ⇒ 404.
- **Lịch học**: thứ 0–6 (0 = thứ Hai); giờ bắt đầu < giờ kết thúc; phải chọn phòng hoặc nhập tên phòng; phòng phải
  đang sử dụng; **chống trùng phòng**: cùng phòng, cùng thứ, khung giờ giao nhau ⇒ 400 nêu lớp đang chiếm
  (hai tiết liền nhau — kết thúc = bắt đầu — hợp lệ); ★ cột chữ `room` chỉ lưu **tên phòng tự nhập** khi không chọn phòng trong danh mục (đã chọn
  `room_id` thì để trống — mã phòng lấy qua `room_id`, chuẩn 3NF); API vẫn trả trường `room` = tên tự nhập hoặc mã phòng;
  xóa lịch đã có phiên điểm danh ⇒ 409.
- **Lịch tuần** `GET /schedules/week?start=`: tuần thứ Hai–CN chứa ngày `start`. SV theo lớp ghi danh; GV/cán bộ theo
  phạm vi xem lớp. Mỗi buổi: phòng, giờ, giờ được mở phiên (= bắt đầu − 15'), phiên (nếu có), địa điểm + bán kính;
  SV thấy trạng thái của mình; GV/cán bộ thấy số có mặt (present+late+manual) / sĩ số khi phiên đã đóng.
- **Lịch dạy hôm nay** (GV): các buổi hôm nay, giờ được mở phiên, phiên đang có.
- **In lịch PDF**: thực hiện ở client từ dữ liệu lịch tuần.

## 6. Người học (PH4)

- **Sinh viên**: email, MSSV duy nhất; xóa bị chặn (409) khi đã ghi danh/đã có khuôn mặt, hoặc đã có điểm danh
  (giữ để đối chiếu); xóa SV xóa luôn liên kết phụ huynh, OTP, refresh token, tài khoản.
- **Đồng ý sinh trắc** (`core/consent.py`, phiên bản `2026-10`):
  - Chỉ chính SV (`method=self`) hoặc admin/P.CTSV (`method=paper`, khi SV đã ký giấy; ghi email cán bộ nhập).
  - Phải tick đồng ý (400), phải gửi đúng phiên bản hiện hành (409), đúng phương thức theo người gửi (400).
  - SV đã đồng ý phiên bản cũ ⇒ `/auth/me` trả `consent_outdated=true` để app nhắc đồng ý lại.
  - **Rút đồng ý** (SV hoặc admin/P.CTSV): xóa ngay mọi vector + ảnh khuôn mặt, xóa dấu đồng ý.
- **Phụ huynh**: admin/P.CTSV tạo và liên kết thủ công bằng MSSV (không tự đăng ký); liên kết trùng ⇒ 400;
  MSSV không tồn tại ⇒ 404; xóa phụ huynh xóa liên kết, không xóa SV. P.ĐT chỉ xem.
- **Tùy chọn thông báo** (phụ huynh tự đổi): nhận email, nhận cả tin "có mặt".

## 7. Khuôn mặt (PH5) ★

- **Đăng ký** `POST /faces/enroll/{sid}` (nhiều ảnh): người gửi là chính SV, admin/P.CTSV, hoặc GV có SV trong lớp;
  SV **chưa đồng ý** ⇒ 400. Mỗi ảnh: đúng 1 khuôn mặt, đạt chất lượng (mục 1), qua chống giả mạo, không giống SV
  khác > 0.60 ⇒ lưu vector **`pending`** + ảnh cắt tạm. `ok=true` chỉ khi **mọi** ảnh đạt.
- **Duyệt** ★: CHỈ **Phòng Công tác SV** (quản trị viên ⇒ 403). Danh sách chờ kèm cảnh báo trùng (so với vector
  **đã duyệt** của SV khác, hiện MSSV + độ giống); chỉ xử lý ảnh đang chờ (đã xử lý ⇒ 400); duyệt ⇒ `approved`;
  từ chối bắt buộc **lý do không hợp lệ** (400) ⇒ `rejected`; ghi `reviewed_by`, `reviewed_at`. **Ảnh tạm bị xóa ngay
  khi có quyết định.**
- **Phản hồi kết quả** ★: mỗi quyết định tạo thông báo cho SV (`face_approved` / `face_rejected` kèm lý do).
  SV **xác nhận đã nhận** `POST /faces/mine/{id}/acknowledge` (ảnh của chính mình — khác ⇒ 404; chưa có kết quả ⇒ 400)
  ⇒ `student_ack_at`.
- Chỉ vector `approved` dùng để nhận diện. Trạng thái khuôn mặt của SV: approved > pending > rejected > none.
- SV xem danh sách vector của mình; `DELETE /faces/mine` = rút đồng ý (xóa toàn bộ).

## 8. Điểm danh (PH6)

### 8.1 Phiên
- **Mở phiên** (GV lớp mình/admin): lịch tồn tại (404); ngày = hôm nay; đúng thứ của lịch; trong khung
  `[bắt đầu − 15', kết thúc]`; mỗi lịch tối đa một phiên/ngày (kiểm trước + UNIQUE DB, cả hai trả 400 cùng thông báo).
- **Hạn nhận điểm danh** = ngày phiên + giờ kết thúc + 30'. Sau hạn ⇒ 400 "Da het gio nhan diem danh…".
  Phiên không mở ⇒ 404.
- **Đóng phiên** (thủ công hoặc tự động mỗi 60 s khi quá hạn): SV ghi danh chưa có bản ghi ⇒ `absent`, hoặc
  ★ `excused` nếu có **đơn xin phép đã duyệt** cho buổi đó; sau đó **thống kê lại** chuyên cần và ★ **cảnh báo**
  SV **vừa** vượt ngưỡng (mục 10); trả `absent`, `excused`, `present` (= số bản ghi đã có), `newly_warned`;
  xóa bộ đếm xác nhận khung hình của phiên. Đóng phiên đã đóng ⇒ 400.
- ★ Đã bỏ hẳn mã QR (bật/tắt, chiếu mã, quét mã); `GET /sessions/{id}/checkin-info` chỉ trả tên phòng.

### 8.2 Quét camera (`/recognize`)
- Với mỗi khuôn mặt trong khung hình: so với vector đã duyệt của SV **trong lớp**; độ giống < 0.45 ⇒ `unknown`.
- Nghi giả mạo ⇒ lưu ảnh bằng chứng, trả `spoof`, **không ghi** điểm danh.
- Đã có bản ghi ⇒ `already_checked`.
- Chưa đủ 2 khung ⇒ `confirming` (kèm `confirm_count/needed`); đủ ⇒ ghi bản ghi `present`/`late`, nguồn `camera`,
  ảnh bằng chứng (một ảnh cho cả khung hình). Đụng UNIQUE do thiết bị khác ghi trước ⇒ `already_checked`.

### 8.3 Sinh viên tự điểm danh (`/self-checkin`) — thứ tự kiểm tra
1. Phiên mở và còn hạn → 2. Có hồ sơ SV (404) → 3. Ghi danh lớp (403) → 4. Đã đồng ý (`consent_required`) →
5. Chưa có bản ghi (`already_checked`) → 6. **GPS trước khi nhận diện** (tiết kiệm tài nguyên) →
7. Khuôn mặt chỉ so với **chính SV** (`no_face`, `multiple_faces`, `spoof` — có lưu bằng chứng, `not_matched`) →
8. Ghi bản ghi `present`/`late`, nguồn `selfie`, lưu tọa độ, sai số, khoảng cách. (★ Bỏ bước mã QR.)

**Vùng địa lý** (theo thứ tự ưu tiên): tọa độ riêng của phòng (bán kính ≥ 50 m) → khu vực chứa phòng → địa điểm gắn
trực tiếp vào lịch (dữ liệu cũ) → địa điểm mặc định. Không có vùng nào hoặc tắt cấu hình ⇒ không chặn (vẫn tính
khoảng cách nếu được). Chặn khi: thiếu tọa độ (`location_required`), vị trí giả lập (`location_mocked`), sai số
> 100 m (`location_inaccurate`), `khoảng cách − sai số > bán kính` (`out_of_range`). Khoảng cách tính Haversine.


### 8.4 Xác nhận tay và hiệu chỉnh
- **Xác nhận tay** (GV lớp/admin): chỉ khi phiên mở (400); SV phải thuộc lớp (400); chưa có bản ghi (400) ⇒
  bản ghi `manual`, nguồn `manual`.
- **Sửa trạng thái** `PATCH /sessions/{sid}/records/{rid}`: bản ghi phải thuộc phiên (404); trạng thái mới ∈
  {present, late, absent, excused} (400); **lý do bắt buộc** (400); sửa được cả khi phiên đã đóng.
  - GV lớp/admin: mọi trạng thái.
  - P.CTSV / Lãnh đạo Khoa (trong phạm vi): **chỉ** `→ excused` hoặc `excused → absent` (403 nếu khác).
  - Mỗi lần sửa ghi một dòng `attendance_audits` (cũ, mới, người sửa, lý do, thời điểm). Xem lịch sử: mới nhất trước.

### 8.5 Đơn xin phép vắng ★
- **Nộp** `POST /leave-requests` (SV): lịch tồn tại (404); SV ghi danh lớp của lịch (403); ngày vắng đúng thứ của lịch
  (400); nộp bổ sung tối đa `LEAVE_REQUEST_MAX_PAST_DAYS` ngày sau buổi học (400); bắt buộc lý do (400); mỗi
  (SV, lịch, ngày) một đơn (400 + UNIQUE DB); đã có mặt buổi đó ⇒ 400. Giảng viên lớp nhận thông báo `leave_submitted`.
- **Xem** `GET /leave-requests`: SV đơn của mình; GV lớp mình dạy; Lãnh đạo Khoa SV / lớp thuộc Khoa; admin, P.CTSV
  toàn trường (chỉ xem); kèm trạng thái điểm danh của SV ở buổi đó.
- **Duyệt** `PATCH …/approve` / **từ chối** `PATCH …/reject` (GV lớp, Lãnh đạo Khoa trong phạm vi — 403): đơn phải đang
  chờ (400); từ chối bắt buộc **lý do không hợp lệ** (400); ghi người duyệt, thời điểm, ghi chú / lý do.
- **Áp dụng**: duyệt khi phiên của buổi đó đã ghi SV `absent` ⇒ đổi ngay sang `excused` + dòng `attendance_audits`
  (lý do "Đơn xin phép #id: …"); chưa đóng phiên ⇒ đóng phiên ghi `excused` thay vì `absent`.
- **Phản hồi kết quả**: thông báo cho SV (`leave_approved` / `leave_rejected` kèm lý do); SV **xác nhận đã nhận**
  `POST …/acknowledge` (đơn của mình — khác ⇒ 404; chưa có kết quả ⇒ 400) ⇒ `student_ack_at`.

## 9. Thông báo (PH7)

- Sự kiện SQLAlchemy `before_flush`: khi bản ghi điểm danh được **tạo** hoặc **đổi trạng thái** ⇒ tạo thông báo cho
  mọi phụ huynh liên kết với SV. Loại: `attendance_present` (bỏ qua nếu phụ huynh tắt tin có mặt), `_late`,
  `_absent`, `_excused`. `manual` tính như có mặt.
- UNIQUE (user, record, loại) ⇒ mỗi bản ghi chỉ báo một lần cho mỗi loại; đổi trạng thái là loại khác nên báo thêm.
- Email: thông báo vào hàng đợi (`email_status=pending`) nếu phụ huynh bật email và máy chủ có SMTP, ngược lại
  `skipped`. Tác vụ nền gửi theo lô, thử tối đa 3 lần rồi `failed` kèm lỗi. Việc điểm danh **không chờ** email.
- Hộp thư: danh sách, số chưa đọc, đánh dấu một/tất cả đã đọc (chỉ thông báo của chính mình, 404 nếu không phải).
- ★ **Thông báo cho SV / GV** (`services/user_notify.py`): kết quả duyệt khuôn mặt và đơn xin phép (SV), đơn xin phép
  mới (GV lớp), cảnh báo chuyên cần (SV + phụ huynh — phụ huynh vào hàng đợi email nếu bật email). Hộp thư mở cho
  phụ huynh, sinh viên, giảng viên, Lãnh đạo Khoa.

## 10. Báo cáo, thống kê (PH8)

- Mọi thống kê **chỉ tính phiên đã đóng** (cả tử số lẫn mẫu số).
- **Tỉ lệ vắng** = số buổi `absent` / tổng số phiên đã đóng của lớp; `excused` **không** tính vắng;
  cảnh báo khi ≥ 0.2.
- **Thống kê lớp** / **cảnh báo**: mỗi SV có bản ghi: số buổi theo 5 trạng thái, tổng phiên, tỉ lệ (4 chữ số), cờ cảnh báo;
  sắp xếp theo MSSV.
- ★ **Cảnh báo sau thống kê**: mỗi lần đóng phiên (thủ công / tự động) hệ thống thống kê lại lớp; SV **vừa** vượt ngưỡng
  (trước đóng phiên chưa vượt) nhận thông báo `absence_warning`, mọi phụ huynh liên kết cũng nhận. SV đã ở trên ngưỡng
  từ trước không bị báo lặp.
- **Chuyên cần một SV** (SV tự xem, PH xem con, cán bộ xem 1 SV): lọc học kỳ (mặc định học kỳ lớn nhất trong các lớp đã
  ghi danh), mỗi lớp: số buổi theo trạng thái, tỉ lệ, ngưỡng, cảnh báo, GV + email, **chi tiết từng buổi** (giờ, ảnh,
  nguồn, GPS, khoảng cách).
- `GET /reports/my-attendance` (SV): bản tóm tắt theo lớp (không lọc học kỳ).
- **Xuất Excel** `?class_id=&semester=`: học kỳ phải khớp lớp (400). Sheet "Diem danh": MSSV, họ tên, mỗi phiên một cột
  ký hiệu P/L/A/E/M, tổng vắng, % vắng; dòng vượt ngưỡng tô đỏ. Sheet "Thong ke lop": mã lớp, môn, học kỳ, Khoa,
  sĩ số, số buổi, số SV vượt ngưỡng, ngưỡng. Tên file `diemdanh_<mã lớp>_<học kỳ>.xlsx`. **Ghi nhật ký `report.exported`.**
- **Thống kê tổng hợp** `GET /reports/overview?semester=`: không truyền ⇒ học kỳ mới nhất; Khoa chỉ thấy Khoa mình
  (`scope=faculty`), còn lại `scope=school`. Tổng + theo từng Khoa ("Chua gan Khoa" xếp cuối): số lớp, SV (khác nhau),
  GV, phiên đã đóng, bản ghi, 5 trạng thái, tỉ lệ đi học = (present+late+manual)/bản ghi, tỉ lệ vắng = absent/bản ghi,
  số SV bị cảnh báo. **Không có tên, ảnh** (Ban ngành xem được).

## 11. Nhật ký hệ thống (PH9)

- Sự kiện `after_flush`: mọi thêm/sửa/xóa trên 16 loại đối tượng (★ thêm đơn xin phép) (user, đơn vị, cán bộ, SV, GV, phụ huynh, liên kết,
  lớp, ghi danh, lịch, phòng, địa điểm, khuôn mặt, phiên, điểm danh) ⇒ một dòng `audit_logs`: người thao tác (email,
  vai trò snapshot), hành động, đối tượng + nhãn snapshot, Khoa liên quan, IP, kết quả, chi tiết `{trường: [cũ, mới]}`.
- Không ghi: **tạo** bản ghi điểm danh (luồng thường); giá trị cột nhạy cảm (mật khẩu, vector, OTP, token — chỉ ghi
  "đã thay đổi"); cột nhiễu (token_version, các mốc thời gian tự động).
- Ghi tường minh: đăng nhập, đăng nhập sai, bị khóa, đăng xuất, xuất báo cáo. Thay đổi từ tác vụ nền ghi là "hệ thống".
- Tra cứu (admin toàn trường, Lãnh đạo Khoa chỉ Khoa mình): lọc từ khóa, nhóm hành động (tiền tố), kết quả, khoảng
  ngày; mới nhất trước; `limit` 1–500 (mặc định 50).

## 12. Ảnh và quyền riêng tư

- DB lưu đường dẫn thô `/evidence/<phiên>/<file>.jpg`; API trả URL ký `?exp=&sig=` (HMAC-SHA256 32 ký tự với
  `SECRET_KEY`). `GET /evidence/...` kiểm chữ ký + hạn (403), chống thoát thư mục `../` (404).
- Ảnh tạm duyệt khuôn mặt nằm trong `evidence/faces/`, xóa khi duyệt/từ chối/rút đồng ý.
- Ảnh bằng chứng tự xóa sau 90 ngày (tác vụ nền mỗi 24 h).

## 13. Toàn vẹn dữ liệu và lỗi

- Vi phạm ràng buộc DB chưa được kiểm trước ⇒ 409 "Du lieu bi trung hoac dang duoc su dung o noi khac".
- Ghi đồng thời (mở phiên, ghi điểm danh) được UNIQUE ở DB chặn và trả kết quả thân thiện thay vì 500.
- Mọi thời gian lưu dạng naive giờ địa phương; khi trả về gắn `+07:00`.

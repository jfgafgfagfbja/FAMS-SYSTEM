# Phân tích cơ sở dữ liệu FAMS

> PostgreSQL 16 + extension `pgvector`. Định nghĩa: `server/app/db/models.py` (SQLAlchemy 2.0),
> lịch sử thay đổi: `server/alembic/versions/` (15 migration). Chỉ **server** truy cập DB.

## 1. Sơ đồ quan hệ (rút gọn)

```
units ─┬─< staff >── users ──┬──< students >──┬──< enrollments >── classes >── lecturers >── users
       │                     │                │                     │  │
       │ (faculty_id)        │                ├──< face_embeddings  │  └──< schedules >── rooms >── locations
       └── students, lecturers, classes, audit_logs                 │          │    └────────────── locations
                             │                ├──< parent_students >── parents >── users
                             │                └──< attendance_records >── attendance_sessions >── schedules
                             │                          │
                             │                          ├──< attendance_audits >── users (changed_by)
                             │                          └──< notifications >── users
                             ├──< refresh_tokens
                             ├──< password_resets
                             └──< audit_logs (actor_id)
revoked_tokens (độc lập, theo jti)
```
`A ─< B`: một A có nhiều B. Chi tiết đầy đủ: `docs/legacy/erd.mermaid` (bản gốc) và mục 2.

## 2. Danh mục bảng (21 bảng)

### 2.1 Tài khoản và tổ chức
| Bảng | Cột chính | Ràng buộc / ghi chú |
|---|---|---|
| `users` | id, email, password_hash (bcrypt), role, full_name, credentials_changed_at, token_version | email UNIQUE; role ∈ 9 vai trò; token_version tăng khi đặt lại/đổi mật khẩu |
| `units` | id, code, name, type | code UNIQUE; type ∈ faculty, training, student_affairs, board |
| `staff` | id, user_id, unit_id, position | user_id UNIQUE (1 user ↔ 1 hồ sơ cán bộ) |
| `students` | id, user_id, student_code, major, cohort, faculty_id, consent_given, consent_given_at, consent_version, consent_method, consent_recorded_by | student_code UNIQUE; faculty_id → units |
| `lecturers` | id, user_id, lecturer_code, department, faculty_id | lecturer_code UNIQUE |
| `parents` | id, user_id, phone, notify_email, notify_present | |
| `parent_students` | id, parent_id, student_id | UNIQUE(parent_id, student_id); xóa parent ⇒ cascade (ORM) |

### 2.2 Đào tạo
| Bảng | Cột chính | Ràng buộc / ghi chú |
|---|---|---|
| `classes` | id, class_code, subject_name, lecturer_id, semester ("YYYY.N"), faculty_id | class_code UNIQUE |
| `enrollments` | id, student_id, class_id | UNIQUE(student_id, class_id) |
| `locations` | id, code, name, latitude, longitude, radius_m (mặc định 150), is_default | code UNIQUE; tối đa 1 is_default (kiểm ở ứng dụng) |
| `rooms` | id, code, name, building, floor, capacity, latitude, longitude, radius_m, location_id, is_active | code UNIQUE; index location_id |
| `schedules` | id, class_id, weekday (0 = thứ Hai), start_time, end_time, room (chữ), room_id, location_id | index room_id; chống trùng phòng kiểm ở ứng dụng |

### 2.3 Điểm danh và sinh trắc
| Bảng | Cột chính | Ràng buộc / ghi chú |
|---|---|---|
| `attendance_sessions` | id, schedule_id, session_date, opened_at, closed_at, status (open/closed), require_qr | **UNIQUE(schedule_id, session_date)** |
| `attendance_records` | id, session_id, student_id, checked_at, status (present/late/absent/manual/excused), confidence, evidence_image, source (camera/selfie/manual), latitude, longitude, location_accuracy, distance_m | **UNIQUE(session_id, student_id)** |
| `attendance_audits` | id, record_id, changed_by, old_status, new_status, reason, changed_at | không có API xóa |
| `face_embeddings` | id, student_id, embedding `Vector(512)`, source_image, status (pending/approved/rejected), reject_reason, created_at | **index HNSW `vector_cosine_ops`** |

### 2.4 Bảo mật, thông báo, nhật ký
| Bảng | Cột chính | Ràng buộc / ghi chú |
|---|---|---|
| `revoked_tokens` | id, jti, expires_at | jti UNIQUE |
| `refresh_tokens` | id, user_id, token_hash (SHA-256), expires_at, revoked_at | token_hash UNIQUE |
| `password_resets` | id, user_id, otp_hash (bcrypt), expires_at, used, created_at | |
| `notifications` | id, user_id, kind, title, body, link, record_id, created_at, read_at, email_status, email_attempts, email_error, emailed_at | UNIQUE(user_id, record_id, kind); FK user ON DELETE CASCADE, record ON DELETE SET NULL; index user_id, index một phần cho hàng đợi email |
| `audit_logs` | id, created_at, actor_id, actor_email, actor_role, action, target_type, target_id, target_label, faculty_id, ip, success, detail (JSON text) | index created_at, actor_id, action, faculty_id; FK ON DELETE SET NULL |

## 3. Kiểu dữ liệu và quy ước

- Thời gian lưu `timestamp without time zone` theo **giờ Việt Nam** (DB đặt `timezone = Asia/Ho_Chi_Minh` qua
  migration `a18f6c2b9e40`; container đặt `TZ`). Riêng `refresh_tokens.expires_at/revoked_at`,
  `password_resets.expires_at`, `revoked_tokens.expires_at` tính bằng **UTC** (`datetime.utcnow`).
- Trạng thái lưu bằng chuỗi (không dùng enum DB) ⇒ thêm trạng thái không cần migration nhưng phải kiểm ở ứng dụng.
- Ảnh không lưu trong DB: chỉ lưu đường dẫn tương đối `/evidence/...`; file nằm trong volume `evidence`.
- Không lưu mật khẩu, OTP, refresh token dạng thô.

## 4. Chuỗi migration

| # | Revision | Nội dung |
|---|---|---|
| 1 | `0b5e1a7c2d90` | Baseline: bảng gốc (bỏ qua nếu đã tồn tại do `create_all` trước đây) |
| 2 | `150e85d92f65` | Cột đồng ý sinh trắc, bảng `revoked_tokens` |
| 3 | `619a843979a7` | Bảng `attendance_audits` |
| 4 | `3425299cc20d` | Index HNSW cho `face_embeddings.embedding` |
| 5 | `1d8874f7a39c` | Trạng thái duyệt + lý do từ chối cho khuôn mặt |
| 6 | `3243764e3dbd` | Bảng `password_resets`, `users.credentials_changed_at` |
| 7 | `b41f0a7c9d2e` | UNIQUE(schedule_id, session_date) |
| 8 | `d7c9a3f21b4e` | `parents`, `parent_students`; vị trí + nguồn trên bản ghi điểm danh |
| 9 | `a18f6c2b9e40` | Múi giờ mặc định của database |
| 10 | `e5b8c1d4f7a2` | `units`, `staff`, `refresh_tokens`, `users.token_version`, `faculty_id` |
| 11 | `f7c2a9d1e3b4` | `locations`, `schedules.location_id`, `attendance_records.distance_m` |
| 12 | `c3d9f61a84b7` | `rooms`, `schedules.room_id` |
| 13 | `a71c4e9d3b82` | `attendance_sessions.require_qr` |
| 14 | `b8e2d5f1c947` | `notifications`, tùy chọn nhận tin của phụ huynh |
| 15 | `d4f8a2c6e913` | `audit_logs`; chi tiết đồng ý (phiên bản, cách, người ghi) — **head** |

## 5. Truy vấn trọng yếu và hiệu năng

| Truy vấn | Cách làm | Ghi chú |
|---|---|---|
| Nhận diện | `ORDER BY embedding <=> :vec` (cosine) giới hạn SV trong lớp, chỉ `approved` | Dùng HNSW |
| Cảnh báo trùng khi duyệt | Láng giềng gần nhất của từng vector chờ duyệt | N truy vấn cho N vector chờ (chấp nhận được với hàng đợi nhỏ) |
| Thống kê lớp | GROUP BY (student, status) trên phiên đã đóng | Sau đó `db.get` từng SV (N+1 nhỏ) |
| Thống kê tổng hợp | Gom theo Khoa; tính cảnh báo bằng thống kê từng lớp | Tốn nhất hệ thống; giữ nguyên thuật toán để không đổi kết quả |
| Danh sách có phân trang | `count()` + `offset/limit` + header `X-Total-Count` | |

## 6. Toàn vẹn dữ liệu

- Ràng buộc DB (UNIQUE, FK) là lớp bảo vệ cuối; ứng dụng kiểm trước để trả thông báo dễ hiểu, và handler
  `IntegrityError → 409` bắt phần còn lại.
- Các thao tác xóa có điều kiện (đơn vị, cán bộ, GV, SV, lớp, lịch, phòng, địa điểm) giữ dữ liệu lịch sử điểm danh.
- Không có xóa mềm; nhật ký `audit_logs` giữ nhãn snapshot để đọc được sau khi đối tượng bị xóa.

## 7. Phương án dữ liệu cho bản tái cấu trúc

1. **Không đổi schema** trong giai đoạn tái cấu trúc kiến trúc: giữ nguyên 21 bảng, 15 migration và revision head
   `d4f8a2c6e913` ⇒ dữ liệu của bản gốc khôi phục thẳng vào bản mới mà không cần chuyển đổi.
2. Database của bản mới là **database riêng** (`fams_system` trên container `fams-system-db-1`, cổng 5433).
3. Nhập dữ liệu từ bản gốc (khi cần): `pg_dump` chỉ-đọc từ DB gốc → `pg_restore` vào DB mới, rồi
   `alembic upgrade head` (không làm gì nếu đã ở head). Script: `scripts/` — xem
   [deployment/BACKUP_RESTORE.md](deployment/BACKUP_RESTORE.md).
4. Thêm kiểm thử: chạy `alembic upgrade head` trên DB trống và so với models (bản gốc test bằng `create_all`
   nên chưa kiểm được migration).

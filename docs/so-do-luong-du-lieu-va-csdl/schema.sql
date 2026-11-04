-- =====================================================================
-- CSDL: HỆ THỐNG FAMS – QUẢN LÝ SINH VIÊN VÀ ĐIỂM DANH BẰNG NHẬN DIỆN KHUÔN MẶT (PostgreSQL 16 + pgvector)
-- 21 bảng. Sinh tự động từ server/app/db/models.py (docs/tools/gen_so_do_csdl.py).
-- Môi trường thật tạo / nâng cấp schema bằng Alembic (server/alembic, head d4f8a2c6e913);
-- tệp này dùng để đọc, đưa vào báo cáo hoặc dựng CSDL thử nghiệm.
-- =====================================================================
-- CREATE DATABASE fams_system ENCODING 'UTF8';  -- \c fams_system
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------- locations (Địa điểm / khu vực điểm danh · Tổ chức & danh mục)
CREATE TABLE locations (
  id SERIAL NOT NULL,  -- Mã địa điểm
  code VARCHAR(30) NOT NULL,  -- Mã, không trùng
  name VARCHAR(255) NOT NULL,  -- Tên
  latitude FLOAT NOT NULL,  -- Vĩ độ
  longitude FLOAT NOT NULL,  -- Kinh độ
  radius_m FLOAT NOT NULL,  -- Bán kính cho phép (m), 10 – 5000
  is_default BOOLEAN NOT NULL,  -- Áp dụng cho lịch học chưa gắn phòng/địa điểm
  PRIMARY KEY (id),
  UNIQUE (code)
);
COMMENT ON TABLE locations IS 'Địa điểm / khu vực điểm danh: Cơ sở, tòa nhà dùng để đối chiếu GPS khi sinh viên tự điểm danh. Tối đa một địa điểm mặc định.';
COMMENT ON COLUMN locations.id IS 'Mã địa điểm';
COMMENT ON COLUMN locations.code IS 'Mã, không trùng';
COMMENT ON COLUMN locations.name IS 'Tên';
COMMENT ON COLUMN locations.latitude IS 'Vĩ độ';
COMMENT ON COLUMN locations.longitude IS 'Kinh độ';
COMMENT ON COLUMN locations.radius_m IS 'Bán kính cho phép (m), 10 – 5000';
COMMENT ON COLUMN locations.is_default IS 'Áp dụng cho lịch học chưa gắn phòng/địa điểm';

-- ---------------------------------------------------------------- revoked_tokens (Access token bị thu hồi · Tài khoản & bảo mật)
CREATE TABLE revoked_tokens (
  id SERIAL NOT NULL,  -- Mã
  jti VARCHAR(36) NOT NULL,  -- Mã định danh JWT (claim jti)
  expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,  -- Hết hạn của token (UTC)
  PRIMARY KEY (id),
  UNIQUE (jti)
);
COMMENT ON TABLE revoked_tokens IS 'Access token bị thu hồi: Danh sách đen access token (JWT) bị thu hồi trước hạn khi đăng xuất; kiểm tra mỗi request theo jti.';
COMMENT ON COLUMN revoked_tokens.id IS 'Mã';
COMMENT ON COLUMN revoked_tokens.jti IS 'Mã định danh JWT (claim jti)';
COMMENT ON COLUMN revoked_tokens.expires_at IS 'Hết hạn của token (UTC)';

-- ---------------------------------------------------------------- units (Đơn vị · Tổ chức & danh mục)
CREATE TABLE units (
  id SERIAL NOT NULL,  -- Mã đơn vị
  code VARCHAR(30) NOT NULL,  -- Mã viết tắt, không trùng
  name VARCHAR(255) NOT NULL,  -- Tên đơn vị
  type VARCHAR(20) NOT NULL,  -- faculty | training | student_affairs | board (không đổi sau khi tạo)
  PRIMARY KEY (id),
  UNIQUE (code)
);
COMMENT ON TABLE units IS 'Đơn vị: Đơn vị trong trường: Khoa, Phòng Đào tạo, Phòng Công tác SV, Ban ngành. Loại đơn vị quyết định vai trò cán bộ.';
COMMENT ON COLUMN units.id IS 'Mã đơn vị';
COMMENT ON COLUMN units.code IS 'Mã viết tắt, không trùng';
COMMENT ON COLUMN units.name IS 'Tên đơn vị';
COMMENT ON COLUMN units.type IS 'faculty | training | student_affairs | board (không đổi sau khi tạo)';

-- ---------------------------------------------------------------- users (Người dùng · Tài khoản & bảo mật)
CREATE TABLE users (
  id SERIAL NOT NULL,  -- Mã người dùng
  email VARCHAR(255) NOT NULL,  -- Email đăng nhập, không trùng
  password_hash VARCHAR(255) NOT NULL,  -- Mật khẩu đã băm bcrypt, không lưu mật khẩu thô
  role VARCHAR(20) NOT NULL,  -- admin | training_office | student_affairs | faculty_office | faculty_leader | board | lecturer | student | parent
  full_name VARCHAR(255) NOT NULL,  -- Họ và tên
  credentials_changed_at TIMESTAMP WITHOUT TIME ZONE,  -- Thời điểm đổi / đặt lại mật khẩu gần nhất (đối soát)
  token_version INTEGER DEFAULT '0' NOT NULL,  -- Tăng mỗi lần đổi mật khẩu; access token mang claim tv khác giá trị này bị từ chối
  PRIMARY KEY (id),
  UNIQUE (email)
);
COMMENT ON TABLE users IS 'Người dùng: Tài khoản đăng nhập của cả 9 vai trò (admin, cán bộ phòng ban, giảng viên, sinh viên, phụ huynh). Hồ sơ chi tiết nằm ở staff / lecturers / students / parents.';
COMMENT ON COLUMN users.id IS 'Mã người dùng';
COMMENT ON COLUMN users.email IS 'Email đăng nhập, không trùng';
COMMENT ON COLUMN users.password_hash IS 'Mật khẩu đã băm bcrypt, không lưu mật khẩu thô';
COMMENT ON COLUMN users.role IS 'admin | training_office | student_affairs | faculty_office | faculty_leader | board | lecturer | student | parent';
COMMENT ON COLUMN users.full_name IS 'Họ và tên';
COMMENT ON COLUMN users.credentials_changed_at IS 'Thời điểm đổi / đặt lại mật khẩu gần nhất (đối soát)';
COMMENT ON COLUMN users.token_version IS 'Tăng mỗi lần đổi mật khẩu; access token mang claim tv khác giá trị này bị từ chối';

-- ---------------------------------------------------------------- audit_logs (Nhật ký hệ thống · Thông báo & nhật ký)
CREATE TABLE audit_logs (
  id SERIAL NOT NULL,  -- Mã
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,  -- Thời điểm
  actor_id INTEGER,  -- Người thao tác
  actor_email VARCHAR(255),  -- Email (bản chụp lúc ghi)
  actor_role VARCHAR(30),  -- Vai trò (bản chụp)
  action VARCHAR(50) NOT NULL,  -- Hành động, VD auth.login, student.update
  target_type VARCHAR(30),  -- Loại đối tượng
  target_id INTEGER,  -- Mã đối tượng
  target_label VARCHAR(255),  -- Nhãn đối tượng (bản chụp)
  faculty_id INTEGER,  -- Khoa liên quan (Lãnh đạo Khoa chỉ xem Khoa mình)
  ip VARCHAR(64),  -- Địa chỉ IP
  success BOOLEAN NOT NULL,  -- Thành công / thất bại
  detail TEXT,  -- Chi tiết JSON {trường: [cũ, mới]}
  PRIMARY KEY (id),
  FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL,
  FOREIGN KEY(faculty_id) REFERENCES units (id) ON DELETE SET NULL
);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_actor_id ON audit_logs (actor_id);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);
CREATE INDEX ix_audit_logs_faculty_id ON audit_logs (faculty_id);
COMMENT ON TABLE audit_logs IS 'Nhật ký hệ thống: Ai, lúc nào, làm gì, với đối tượng nào, từ IP nào. Ghi tự động mọi thêm / sửa / xóa dữ liệu quản lý (sự kiện after_flush), ghi tường minh đăng nhập, đăng xuất, xuất báo cáo. Không lưu mật khẩu, OTP, vector, ảnh.';
COMMENT ON COLUMN audit_logs.id IS 'Mã';
COMMENT ON COLUMN audit_logs.created_at IS 'Thời điểm';
COMMENT ON COLUMN audit_logs.actor_id IS 'Người thao tác';
COMMENT ON COLUMN audit_logs.actor_email IS 'Email (bản chụp lúc ghi)';
COMMENT ON COLUMN audit_logs.actor_role IS 'Vai trò (bản chụp)';
COMMENT ON COLUMN audit_logs.action IS 'Hành động, VD auth.login, student.update';
COMMENT ON COLUMN audit_logs.target_type IS 'Loại đối tượng';
COMMENT ON COLUMN audit_logs.target_id IS 'Mã đối tượng';
COMMENT ON COLUMN audit_logs.target_label IS 'Nhãn đối tượng (bản chụp)';
COMMENT ON COLUMN audit_logs.faculty_id IS 'Khoa liên quan (Lãnh đạo Khoa chỉ xem Khoa mình)';
COMMENT ON COLUMN audit_logs.ip IS 'Địa chỉ IP';
COMMENT ON COLUMN audit_logs.success IS 'Thành công / thất bại';
COMMENT ON COLUMN audit_logs.detail IS 'Chi tiết JSON {trường: [cũ, mới]}';

-- ---------------------------------------------------------------- lecturers (Giảng viên · Đào tạo)
CREATE TABLE lecturers (
  id SERIAL NOT NULL,  -- Mã giảng viên
  user_id INTEGER NOT NULL,  -- Tài khoản
  lecturer_code VARCHAR(20) NOT NULL,  -- Mã GV, không trùng
  department VARCHAR(100) NOT NULL,  -- Bộ môn
  faculty_id INTEGER,  -- Khoa quản lý
  PRIMARY KEY (id),
  FOREIGN KEY(user_id) REFERENCES users (id),
  UNIQUE (lecturer_code),
  FOREIGN KEY(faculty_id) REFERENCES units (id)
);
COMMENT ON TABLE lecturers IS 'Giảng viên: Hồ sơ giảng viên gắn với một tài khoản; thuộc một Khoa để cán bộ Khoa thấy trong phạm vi.';
COMMENT ON COLUMN lecturers.id IS 'Mã giảng viên';
COMMENT ON COLUMN lecturers.user_id IS 'Tài khoản';
COMMENT ON COLUMN lecturers.lecturer_code IS 'Mã GV, không trùng';
COMMENT ON COLUMN lecturers.department IS 'Bộ môn';
COMMENT ON COLUMN lecturers.faculty_id IS 'Khoa quản lý';

-- ---------------------------------------------------------------- parents (Phụ huynh · Người học & sinh trắc)
CREATE TABLE parents (
  id SERIAL NOT NULL,  -- Mã phụ huynh
  user_id INTEGER NOT NULL,  -- Tài khoản
  phone VARCHAR(20) NOT NULL,  -- Số điện thoại
  notify_email BOOLEAN NOT NULL,  -- Nhận email thông báo
  notify_present BOOLEAN NOT NULL,  -- Nhận cả tin "có mặt"
  PRIMARY KEY (id),
  FOREIGN KEY(user_id) REFERENCES users (id)
);
COMMENT ON TABLE parents IS 'Phụ huynh: Tài khoản phụ huynh do P. CTSV tạo và liên kết thủ công với con; có tùy chọn nhận thông báo.';
COMMENT ON COLUMN parents.id IS 'Mã phụ huynh';
COMMENT ON COLUMN parents.user_id IS 'Tài khoản';
COMMENT ON COLUMN parents.phone IS 'Số điện thoại';
COMMENT ON COLUMN parents.notify_email IS 'Nhận email thông báo';
COMMENT ON COLUMN parents.notify_present IS 'Nhận cả tin "có mặt"';

-- ---------------------------------------------------------------- password_resets (Yêu cầu đặt lại mật khẩu · Tài khoản & bảo mật)
CREATE TABLE password_resets (
  id SERIAL NOT NULL,  -- Mã
  user_id INTEGER NOT NULL,  -- Tài khoản
  otp_hash VARCHAR(255) NOT NULL,  -- OTP đã băm bcrypt
  expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,  -- Hết hạn (UTC)
  used BOOLEAN NOT NULL,  -- Đã dùng
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,  -- Thời điểm yêu cầu
  PRIMARY KEY (id),
  FOREIGN KEY(user_id) REFERENCES users (id)
);
COMMENT ON TABLE password_resets IS 'Yêu cầu đặt lại mật khẩu: Mã OTP 6 số gửi qua email khi quên mật khẩu; chỉ lưu bản băm, hết hạn sau 10 phút, dùng một lần.';
COMMENT ON COLUMN password_resets.id IS 'Mã';
COMMENT ON COLUMN password_resets.user_id IS 'Tài khoản';
COMMENT ON COLUMN password_resets.otp_hash IS 'OTP đã băm bcrypt';
COMMENT ON COLUMN password_resets.expires_at IS 'Hết hạn (UTC)';
COMMENT ON COLUMN password_resets.used IS 'Đã dùng';
COMMENT ON COLUMN password_resets.created_at IS 'Thời điểm yêu cầu';

-- ---------------------------------------------------------------- refresh_tokens (Refresh token · Tài khoản & bảo mật)
CREATE TABLE refresh_tokens (
  id SERIAL NOT NULL,  -- Mã
  user_id INTEGER NOT NULL,  -- Tài khoản sở hữu
  token_hash VARCHAR(64) NOT NULL,  -- SHA-256 của refresh token
  expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,  -- Hết hạn (UTC)
  revoked_at TIMESTAMP WITHOUT TIME ZONE,  -- Thời điểm thu hồi (UTC), NULL = còn hiệu lực
  PRIMARY KEY (id),
  FOREIGN KEY(user_id) REFERENCES users (id),
  UNIQUE (token_hash)
);
COMMENT ON TABLE refresh_tokens IS 'Refresh token: Refresh token (30 ngày) của app. Chỉ lưu SHA-256; mỗi lần làm mới thì xoay vòng sang token mới. Dùng lại token đã thu hồi ⇒ thu hồi toàn bộ token của tài khoản.';
COMMENT ON COLUMN refresh_tokens.id IS 'Mã';
COMMENT ON COLUMN refresh_tokens.user_id IS 'Tài khoản sở hữu';
COMMENT ON COLUMN refresh_tokens.token_hash IS 'SHA-256 của refresh token';
COMMENT ON COLUMN refresh_tokens.expires_at IS 'Hết hạn (UTC)';
COMMENT ON COLUMN refresh_tokens.revoked_at IS 'Thời điểm thu hồi (UTC), NULL = còn hiệu lực';

-- ---------------------------------------------------------------- rooms (Phòng học · Tổ chức & danh mục)
CREATE TABLE rooms (
  id SERIAL NOT NULL,  -- Mã phòng
  code VARCHAR(30) NOT NULL,  -- Mã phòng, không trùng (VD E2-101)
  name VARCHAR(255) NOT NULL,  -- Tên hiển thị
  building VARCHAR(100),  -- Tòa nhà
  floor INTEGER,  -- Tầng
  capacity INTEGER,  -- Sức chứa
  latitude FLOAT,  -- Vĩ độ riêng (tùy chọn)
  longitude FLOAT,  -- Kinh độ riêng (tùy chọn)
  radius_m FLOAT,  -- Bán kính riêng (m)
  location_id INTEGER NOT NULL,  -- Khu vực chứa phòng
  is_active BOOLEAN NOT NULL,  -- Đang sử dụng (ngừng dùng thì ẩn khi xếp lịch mới)
  PRIMARY KEY (id),
  UNIQUE (code),
  FOREIGN KEY(location_id) REFERENCES locations (id)
);
CREATE INDEX ix_rooms_location_id ON rooms (location_id);
COMMENT ON TABLE rooms IS 'Phòng học: Danh mục phòng để xếp lịch. Phòng có thể có tọa độ riêng (bán kính tối thiểu 50 m), không có thì dùng tọa độ khu vực chứa phòng.';
COMMENT ON COLUMN rooms.id IS 'Mã phòng';
COMMENT ON COLUMN rooms.code IS 'Mã phòng, không trùng (VD E2-101)';
COMMENT ON COLUMN rooms.name IS 'Tên hiển thị';
COMMENT ON COLUMN rooms.building IS 'Tòa nhà';
COMMENT ON COLUMN rooms.floor IS 'Tầng';
COMMENT ON COLUMN rooms.capacity IS 'Sức chứa';
COMMENT ON COLUMN rooms.latitude IS 'Vĩ độ riêng (tùy chọn)';
COMMENT ON COLUMN rooms.longitude IS 'Kinh độ riêng (tùy chọn)';
COMMENT ON COLUMN rooms.radius_m IS 'Bán kính riêng (m)';
COMMENT ON COLUMN rooms.location_id IS 'Khu vực chứa phòng';
COMMENT ON COLUMN rooms.is_active IS 'Đang sử dụng (ngừng dùng thì ẩn khi xếp lịch mới)';

-- ---------------------------------------------------------------- staff (Cán bộ phòng ban · Tổ chức & danh mục)
CREATE TABLE staff (
  id SERIAL NOT NULL,  -- Mã cán bộ
  user_id INTEGER NOT NULL,  -- Tài khoản (1 : 1)
  unit_id INTEGER NOT NULL,  -- Đơn vị công tác
  position VARCHAR(100) NOT NULL,  -- Chức vụ
  PRIMARY KEY (id),
  UNIQUE (user_id),
  FOREIGN KEY(user_id) REFERENCES users (id),
  FOREIGN KEY(unit_id) REFERENCES units (id)
);
COMMENT ON TABLE staff IS 'Cán bộ phòng ban: Hồ sơ cán bộ: mỗi tài khoản thuộc đúng một đơn vị. Đơn vị loại Khoa có hai vai trò: Văn phòng Khoa / Lãnh đạo Khoa.';
COMMENT ON COLUMN staff.id IS 'Mã cán bộ';
COMMENT ON COLUMN staff.user_id IS 'Tài khoản (1 : 1)';
COMMENT ON COLUMN staff.unit_id IS 'Đơn vị công tác';
COMMENT ON COLUMN staff.position IS 'Chức vụ';

-- ---------------------------------------------------------------- students (Sinh viên · Người học & sinh trắc)
CREATE TABLE students (
  id SERIAL NOT NULL,  -- Mã sinh viên
  user_id INTEGER NOT NULL,  -- Tài khoản
  student_code VARCHAR(20) NOT NULL,  -- MSSV, không trùng
  major VARCHAR(100) NOT NULL,  -- Ngành
  cohort INTEGER NOT NULL,  -- Khóa
  faculty_id INTEGER,  -- Khoa quản lý
  consent_given BOOLEAN NOT NULL,  -- Đã đồng ý sinh trắc
  consent_given_at TIMESTAMP WITHOUT TIME ZONE,  -- Thời điểm đồng ý
  consent_version VARCHAR(20),  -- Phiên bản nội dung đã đồng ý
  consent_method VARCHAR(10),  -- self (SV tự xác nhận) | paper (cán bộ nhập bản giấy)
  consent_recorded_by VARCHAR(255),  -- Email người ghi nhận
  PRIMARY KEY (id),
  FOREIGN KEY(user_id) REFERENCES users (id),
  UNIQUE (student_code),
  FOREIGN KEY(faculty_id) REFERENCES units (id)
);
COMMENT ON TABLE students IS 'Sinh viên: Hồ sơ sinh viên và trạng thái đồng ý sử dụng dữ liệu khuôn mặt (có phiên bản nội dung, cách đồng ý, người ghi nhận).';
COMMENT ON COLUMN students.id IS 'Mã sinh viên';
COMMENT ON COLUMN students.user_id IS 'Tài khoản';
COMMENT ON COLUMN students.student_code IS 'MSSV, không trùng';
COMMENT ON COLUMN students.major IS 'Ngành';
COMMENT ON COLUMN students.cohort IS 'Khóa';
COMMENT ON COLUMN students.faculty_id IS 'Khoa quản lý';
COMMENT ON COLUMN students.consent_given IS 'Đã đồng ý sinh trắc';
COMMENT ON COLUMN students.consent_given_at IS 'Thời điểm đồng ý';
COMMENT ON COLUMN students.consent_version IS 'Phiên bản nội dung đã đồng ý';
COMMENT ON COLUMN students.consent_method IS 'self (SV tự xác nhận) | paper (cán bộ nhập bản giấy)';
COMMENT ON COLUMN students.consent_recorded_by IS 'Email người ghi nhận';

-- ---------------------------------------------------------------- classes (Lớp học phần · Đào tạo)
CREATE TABLE classes (
  id SERIAL NOT NULL,  -- Mã lớp
  class_code VARCHAR(30) NOT NULL,  -- Mã lớp, không trùng
  subject_name VARCHAR(255) NOT NULL,  -- Tên môn học
  lecturer_id INTEGER NOT NULL,  -- Giảng viên phụ trách
  semester VARCHAR(20) NOT NULL,  -- Học kỳ (VD 2026.1)
  faculty_id INTEGER,  -- Khoa quản lý
  PRIMARY KEY (id),
  UNIQUE (class_code),
  FOREIGN KEY(lecturer_id) REFERENCES lecturers (id),
  FOREIGN KEY(faculty_id) REFERENCES units (id)
);
COMMENT ON TABLE classes IS 'Lớp học phần: Lớp học phần do một giảng viên phụ trách, thuộc một học kỳ và một Khoa (quyết định phạm vi xem của cán bộ Khoa).';
COMMENT ON COLUMN classes.id IS 'Mã lớp';
COMMENT ON COLUMN classes.class_code IS 'Mã lớp, không trùng';
COMMENT ON COLUMN classes.subject_name IS 'Tên môn học';
COMMENT ON COLUMN classes.lecturer_id IS 'Giảng viên phụ trách';
COMMENT ON COLUMN classes.semester IS 'Học kỳ (VD 2026.1)';
COMMENT ON COLUMN classes.faculty_id IS 'Khoa quản lý';

-- ---------------------------------------------------------------- face_embeddings (Dữ liệu khuôn mặt · Người học & sinh trắc)
CREATE TABLE face_embeddings (
  id SERIAL NOT NULL,  -- Mã vector
  student_id INTEGER NOT NULL,  -- Sinh viên
  embedding VECTOR(512) NOT NULL,  -- Vector ArcFace 512 chiều
  source_image VARCHAR(500) NOT NULL,  -- Ảnh khuôn mặt lưu tạm chờ duyệt (/evidence/faces/...)
  status VARCHAR(10) NOT NULL,  -- pending | approved | rejected
  reject_reason VARCHAR(500) NOT NULL,  -- Lý do từ chối
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,  -- Ngày đăng ký
  PRIMARY KEY (id),
  FOREIGN KEY(student_id) REFERENCES students (id)
);
CREATE INDEX ix_face_embeddings_embedding_hnsw ON face_embeddings USING hnsw (embedding vector_cosine_ops);
COMMENT ON TABLE face_embeddings IS 'Dữ liệu khuôn mặt: Vector đặc trưng khuôn mặt 512 chiều (pgvector, chỉ mục HNSW cosine). Ảnh cắt chỉ lưu tạm để duyệt, xóa ngay khi duyệt / từ chối.';
COMMENT ON COLUMN face_embeddings.id IS 'Mã vector';
COMMENT ON COLUMN face_embeddings.student_id IS 'Sinh viên';
COMMENT ON COLUMN face_embeddings.embedding IS 'Vector ArcFace 512 chiều';
COMMENT ON COLUMN face_embeddings.source_image IS 'Ảnh khuôn mặt lưu tạm chờ duyệt (/evidence/faces/...)';
COMMENT ON COLUMN face_embeddings.status IS 'pending | approved | rejected';
COMMENT ON COLUMN face_embeddings.reject_reason IS 'Lý do từ chối';
COMMENT ON COLUMN face_embeddings.created_at IS 'Ngày đăng ký';

-- ---------------------------------------------------------------- parent_students (Liên kết phụ huynh – sinh viên · Người học & sinh trắc)
CREATE TABLE parent_students (
  id SERIAL NOT NULL,  -- Mã
  parent_id INTEGER NOT NULL,  -- Phụ huynh
  student_id INTEGER NOT NULL,  -- Sinh viên
  PRIMARY KEY (id),
  UNIQUE (parent_id, student_id),
  FOREIGN KEY(parent_id) REFERENCES parents (id),
  FOREIGN KEY(student_id) REFERENCES students (id)
);
COMMENT ON TABLE parent_students IS 'Liên kết phụ huynh – sinh viên: Một phụ huynh theo dõi nhiều con, một sinh viên có thể có nhiều phụ huynh (quan hệ N – N).';
COMMENT ON COLUMN parent_students.id IS 'Mã';
COMMENT ON COLUMN parent_students.parent_id IS 'Phụ huynh';
COMMENT ON COLUMN parent_students.student_id IS 'Sinh viên';

-- ---------------------------------------------------------------- enrollments (Ghi danh · Đào tạo)
CREATE TABLE enrollments (
  id SERIAL NOT NULL,  -- Mã
  student_id INTEGER NOT NULL,  -- Sinh viên
  class_id INTEGER NOT NULL,  -- Lớp học phần
  PRIMARY KEY (id),
  UNIQUE (student_id, class_id),
  FOREIGN KEY(student_id) REFERENCES students (id),
  FOREIGN KEY(class_id) REFERENCES classes (id)
);
COMMENT ON TABLE enrollments IS 'Ghi danh: Sinh viên ghi danh vào lớp học phần (quan hệ N – N giữa students và classes).';
COMMENT ON COLUMN enrollments.id IS 'Mã';
COMMENT ON COLUMN enrollments.student_id IS 'Sinh viên';
COMMENT ON COLUMN enrollments.class_id IS 'Lớp học phần';

-- ---------------------------------------------------------------- schedules (Lịch học · Đào tạo)
CREATE TABLE schedules (
  id SERIAL NOT NULL,  -- Mã lịch
  class_id INTEGER NOT NULL,  -- Lớp học phần
  weekday INTEGER NOT NULL,  -- Thứ (0 = thứ Hai … 6 = Chủ nhật)
  start_time TIME WITHOUT TIME ZONE NOT NULL,  -- Giờ bắt đầu
  end_time TIME WITHOUT TIME ZONE NOT NULL,  -- Giờ kết thúc
  room VARCHAR(50) NOT NULL,  -- Tên phòng dạng chữ (dữ liệu cũ, hiển thị khi chưa gắn phòng)
  room_id INTEGER,  -- Phòng trong danh mục
  location_id INTEGER,  -- Địa điểm gắn trực tiếp (dữ liệu cũ)
  PRIMARY KEY (id),
  FOREIGN KEY(class_id) REFERENCES classes (id),
  FOREIGN KEY(room_id) REFERENCES rooms (id),
  FOREIGN KEY(location_id) REFERENCES locations (id)
);
CREATE INDEX ix_schedules_room_id ON schedules (room_id);
COMMENT ON TABLE schedules IS 'Lịch học: Buổi học cố định trong tuần của lớp. Server chặn xếp hai lớp cùng phòng, cùng thứ, khung giờ giao nhau; giờ bắt đầu phải trước giờ kết thúc.';
COMMENT ON COLUMN schedules.id IS 'Mã lịch';
COMMENT ON COLUMN schedules.class_id IS 'Lớp học phần';
COMMENT ON COLUMN schedules.weekday IS 'Thứ (0 = thứ Hai … 6 = Chủ nhật)';
COMMENT ON COLUMN schedules.start_time IS 'Giờ bắt đầu';
COMMENT ON COLUMN schedules.end_time IS 'Giờ kết thúc';
COMMENT ON COLUMN schedules.room IS 'Tên phòng dạng chữ (dữ liệu cũ, hiển thị khi chưa gắn phòng)';
COMMENT ON COLUMN schedules.room_id IS 'Phòng trong danh mục';
COMMENT ON COLUMN schedules.location_id IS 'Địa điểm gắn trực tiếp (dữ liệu cũ)';

-- ---------------------------------------------------------------- attendance_sessions (Phiên điểm danh · Điểm danh)
CREATE TABLE attendance_sessions (
  id SERIAL NOT NULL,  -- Mã phiên
  schedule_id INTEGER NOT NULL,  -- Lịch học
  session_date DATE NOT NULL,  -- Ngày điểm danh
  opened_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,  -- Thời điểm mở
  closed_at TIMESTAMP WITHOUT TIME ZONE,  -- Thời điểm đóng
  status VARCHAR(10) NOT NULL,  -- open | closed
  require_qr BOOLEAN NOT NULL,  -- Bắt buộc quét mã QR chiếu trong phòng khi tự điểm danh
  PRIMARY KEY (id),
  UNIQUE (schedule_id, session_date),
  FOREIGN KEY(schedule_id) REFERENCES schedules (id)
);
COMMENT ON TABLE attendance_sessions IS 'Phiên điểm danh: Một buổi điểm danh của một lịch học trong một ngày. Chỉ mở trong khung [giờ bắt đầu − 15 phút, giờ kết thúc]; tự đóng sau giờ kết thúc 30 phút.';
COMMENT ON COLUMN attendance_sessions.id IS 'Mã phiên';
COMMENT ON COLUMN attendance_sessions.schedule_id IS 'Lịch học';
COMMENT ON COLUMN attendance_sessions.session_date IS 'Ngày điểm danh';
COMMENT ON COLUMN attendance_sessions.opened_at IS 'Thời điểm mở';
COMMENT ON COLUMN attendance_sessions.closed_at IS 'Thời điểm đóng';
COMMENT ON COLUMN attendance_sessions.status IS 'open | closed';
COMMENT ON COLUMN attendance_sessions.require_qr IS 'Bắt buộc quét mã QR chiếu trong phòng khi tự điểm danh';

-- ---------------------------------------------------------------- attendance_records (Kết quả điểm danh · Điểm danh)
CREATE TABLE attendance_records (
  id SERIAL NOT NULL,  -- Mã bản ghi
  session_id INTEGER NOT NULL,  -- Phiên
  student_id INTEGER NOT NULL,  -- Sinh viên
  checked_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,  -- Thời điểm ghi nhận
  status VARCHAR(10) NOT NULL,  -- present | late | absent | manual | excused
  confidence FLOAT NOT NULL,  -- Độ giống khuôn mặt (cosine)
  evidence_image VARCHAR(500) NOT NULL,  -- Ảnh bằng chứng (/evidence/..., tự xóa sau 90 ngày)
  source VARCHAR(10) NOT NULL,  -- camera | selfie | manual
  latitude FLOAT,  -- Vĩ độ khi tự điểm danh
  longitude FLOAT,  -- Kinh độ khi tự điểm danh
  location_accuracy FLOAT,  -- Sai số GPS (m)
  distance_m FLOAT,  -- Khoảng cách tới địa điểm (m)
  PRIMARY KEY (id),
  UNIQUE (session_id, student_id),
  FOREIGN KEY(session_id) REFERENCES attendance_sessions (id),
  FOREIGN KEY(student_id) REFERENCES students (id)
);
COMMENT ON TABLE attendance_records IS 'Kết quả điểm danh: Kết quả của một sinh viên trong một phiên. Nguồn: camera (GV quét cả lớp), selfie (SV tự chụp + GPS), manual (xác nhận tay).';
COMMENT ON COLUMN attendance_records.id IS 'Mã bản ghi';
COMMENT ON COLUMN attendance_records.session_id IS 'Phiên';
COMMENT ON COLUMN attendance_records.student_id IS 'Sinh viên';
COMMENT ON COLUMN attendance_records.checked_at IS 'Thời điểm ghi nhận';
COMMENT ON COLUMN attendance_records.status IS 'present | late | absent | manual | excused';
COMMENT ON COLUMN attendance_records.confidence IS 'Độ giống khuôn mặt (cosine)';
COMMENT ON COLUMN attendance_records.evidence_image IS 'Ảnh bằng chứng (/evidence/..., tự xóa sau 90 ngày)';
COMMENT ON COLUMN attendance_records.source IS 'camera | selfie | manual';
COMMENT ON COLUMN attendance_records.latitude IS 'Vĩ độ khi tự điểm danh';
COMMENT ON COLUMN attendance_records.longitude IS 'Kinh độ khi tự điểm danh';
COMMENT ON COLUMN attendance_records.location_accuracy IS 'Sai số GPS (m)';
COMMENT ON COLUMN attendance_records.distance_m IS 'Khoảng cách tới địa điểm (m)';

-- ---------------------------------------------------------------- attendance_audits (Lịch sử sửa điểm danh · Điểm danh)
CREATE TABLE attendance_audits (
  id SERIAL NOT NULL,  -- Mã
  record_id INTEGER NOT NULL,  -- Bản ghi điểm danh
  changed_by INTEGER NOT NULL,  -- Người sửa
  old_status VARCHAR(10) NOT NULL,  -- Trạng thái cũ
  new_status VARCHAR(10) NOT NULL,  -- Trạng thái mới
  reason VARCHAR(500) NOT NULL,  -- Lý do (bắt buộc)
  changed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,  -- Thời điểm sửa
  PRIMARY KEY (id),
  FOREIGN KEY(record_id) REFERENCES attendance_records (id),
  FOREIGN KEY(changed_by) REFERENCES users (id)
);
COMMENT ON TABLE attendance_audits IS 'Lịch sử sửa điểm danh: Mỗi lần sửa trạng thái (kể cả duyệt / hủy duyệt có phép) ghi một dòng; lý do bắt buộc, không có chức năng xóa.';
COMMENT ON COLUMN attendance_audits.id IS 'Mã';
COMMENT ON COLUMN attendance_audits.record_id IS 'Bản ghi điểm danh';
COMMENT ON COLUMN attendance_audits.changed_by IS 'Người sửa';
COMMENT ON COLUMN attendance_audits.old_status IS 'Trạng thái cũ';
COMMENT ON COLUMN attendance_audits.new_status IS 'Trạng thái mới';
COMMENT ON COLUMN attendance_audits.reason IS 'Lý do (bắt buộc)';
COMMENT ON COLUMN attendance_audits.changed_at IS 'Thời điểm sửa';

-- ---------------------------------------------------------------- notifications (Thông báo · Thông báo & nhật ký)
CREATE TABLE notifications (
  id SERIAL NOT NULL,  -- Mã thông báo
  user_id INTEGER NOT NULL,  -- Người nhận (phụ huynh)
  kind VARCHAR(30) NOT NULL,  -- attendance_present | attendance_late | attendance_absent | attendance_excused
  title VARCHAR(255) NOT NULL,  -- Tiêu đề
  body TEXT NOT NULL,  -- Nội dung
  link VARCHAR(255),  -- Đường dẫn trong app
  record_id INTEGER,  -- Bản ghi điểm danh liên quan
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,  -- Thời điểm tạo
  read_at TIMESTAMP WITHOUT TIME ZONE,  -- Thời điểm đọc (NULL = chưa đọc)
  email_status VARCHAR(10) NOT NULL,  -- pending | sent | failed | skipped
  email_attempts INTEGER NOT NULL,  -- Số lần thử gửi
  email_error VARCHAR(255),  -- Lỗi gửi gần nhất
  emailed_at TIMESTAMP WITHOUT TIME ZONE,  -- Thời điểm gửi email
  PRIMARY KEY (id),
  UNIQUE (user_id, record_id, kind),
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
  FOREIGN KEY(record_id) REFERENCES attendance_records (id) ON DELETE SET NULL
);
CREATE INDEX ix_notifications_email_pending ON notifications (id) WHERE email_status = 'pending';
CREATE INDEX ix_notifications_user_id ON notifications (user_id);
COMMENT ON TABLE notifications IS 'Thông báo: Hộp thư trong app và hàng đợi email. Sinh tự động khi bản ghi điểm danh của con được tạo / đổi trạng thái; mỗi bản ghi chỉ báo một lần cho mỗi loại.';
COMMENT ON COLUMN notifications.id IS 'Mã thông báo';
COMMENT ON COLUMN notifications.user_id IS 'Người nhận (phụ huynh)';
COMMENT ON COLUMN notifications.kind IS 'attendance_present | attendance_late | attendance_absent | attendance_excused';
COMMENT ON COLUMN notifications.title IS 'Tiêu đề';
COMMENT ON COLUMN notifications.body IS 'Nội dung';
COMMENT ON COLUMN notifications.link IS 'Đường dẫn trong app';
COMMENT ON COLUMN notifications.record_id IS 'Bản ghi điểm danh liên quan';
COMMENT ON COLUMN notifications.created_at IS 'Thời điểm tạo';
COMMENT ON COLUMN notifications.read_at IS 'Thời điểm đọc (NULL = chưa đọc)';
COMMENT ON COLUMN notifications.email_status IS 'pending | sent | failed | skipped';
COMMENT ON COLUMN notifications.email_attempts IS 'Số lần thử gửi';
COMMENT ON COLUMN notifications.email_error IS 'Lỗi gửi gần nhất';
COMMENT ON COLUMN notifications.emailed_at IS 'Thời điểm gửi email';

"""Noi dung tieng Viet cho bo "So do luong du lieu va CSDL" cua FAMS.

Cau truc bang (cot, kieu, khoa, quan he) KHONG khai bao o day: gen_so_do_csdl.py doc truc tiep tu
server/app/db/models.py. File nay chi chua phan dien giai: mo ta bang/cot, nhom, kho DFD, quy trinh
nghiep vu (moi buoc ghi bang doc R / ghi W) va cay chuc nang theo vai tro.
"""

PROJECT = {
    "name": "Hệ thống FAMS – Quản lý sinh viên và điểm danh bằng nhận diện khuôn mặt",
    "short": "FAMS",
    "org": "Trường Đại học Kiến trúc Đà Nẵng",
    "arch": "Mô hình Client – Server (Flutter ↔ REST API /api/v1 ↔ FastAPI ↔ PostgreSQL)",
    "course": "ĐỒ ÁN LẬP TRÌNH MẠNG",
}

# (ten nhom, mau, cac bang theo thu tu hien thi)
GROUPS = [
    ("Tài khoản & bảo mật", "#2563eb", ["users", "refresh_tokens", "revoked_tokens", "password_resets"]),
    ("Tổ chức & danh mục", "#475569", ["units", "staff", "locations", "rooms"]),
    ("Đào tạo", "#059669", ["lecturers", "classes", "enrollments", "schedules"]),
    ("Người học & sinh trắc", "#7c3aed", ["students", "parents", "parent_students", "face_embeddings"]),
    ("Điểm danh", "#d97706", ["attendance_sessions", "attendance_records", "attendance_audits", "leave_requests"]),
    ("Thông báo & nhật ký", "#db2777", ["notifications", "audit_logs"]),
]

# Kho du lieu trong so do DFD -> bang CSDL
STORES = [
    ("D1", "Tài khoản (Users, Tokens)", ["users", "staff", "refresh_tokens", "revoked_tokens", "password_resets"]),
    ("D2", "Danh mục (Units, Locations, Rooms)", ["units", "locations", "rooms"]),
    ("D3", "Đào tạo (Lecturers, Classes, Schedules)", ["lecturers", "classes", "enrollments", "schedules"]),
    ("D4", "Người học (Students, Parents)", ["students", "parents", "parent_students"]),
    ("D5", "Dữ liệu khuôn mặt (Face embeddings)", ["face_embeddings"]),
    ("D6", "Điểm danh (Sessions, Records)", ["attendance_sessions", "attendance_records"]),
    ("D7", "Lịch sử sửa điểm danh (Audits)", ["attendance_audits"]),
    ("D8", "Thông báo (Notifications)", ["notifications"]),
    ("D9", "Nhật ký hệ thống (Audit logs)", ["audit_logs"]),
    ("D10", "Đơn xin phép vắng (Leave requests)", ["leave_requests"]),
]

# Mo ta bang + tung cot. "title": ten tieng Viet; "model": lop SQLAlchemy trong app/db/models.py.
TABLES = {
    "users": {
        "title": "Người dùng", "model": "User",
        "desc": "Tài khoản đăng nhập của cả 9 vai trò (admin, cán bộ phòng ban, giảng viên, sinh viên, phụ huynh). "
                "Hồ sơ chi tiết nằm ở staff / lecturers / students / parents.",
        "cols": {
            "id": "Mã người dùng",
            "email": "Email đăng nhập, không trùng",
            "password_hash": "Mật khẩu đã băm bcrypt, không lưu mật khẩu thô",
            "role": "admin | training_office | student_affairs | faculty_office | faculty_leader | board | lecturer | student | parent",
            "full_name": "Họ và tên",
            "credentials_changed_at": "Thời điểm đổi / đặt lại mật khẩu gần nhất (đối soát)",
            "token_version": "Tăng mỗi lần đổi mật khẩu; access token mang claim tv khác giá trị này bị từ chối",
        },
    },
    "refresh_tokens": {
        "title": "Refresh token", "model": "RefreshToken",
        "desc": "Refresh token (30 ngày) của app. Chỉ lưu SHA-256; mỗi lần làm mới thì xoay vòng sang token mới. "
                "Dùng lại token đã thu hồi ⇒ thu hồi toàn bộ token của tài khoản.",
        "cols": {
            "id": "Mã", "user_id": "Tài khoản sở hữu", "token_hash": "SHA-256 của refresh token",
            "expires_at": "Hết hạn (UTC)", "revoked_at": "Thời điểm thu hồi (UTC), NULL = còn hiệu lực",
        },
    },
    "revoked_tokens": {
        "title": "Access token bị thu hồi", "model": "RevokedToken",
        "desc": "Danh sách đen access token (JWT) bị thu hồi trước hạn khi đăng xuất; kiểm tra mỗi request theo jti.",
        "cols": {"id": "Mã", "jti": "Mã định danh JWT (claim jti)", "expires_at": "Hết hạn của token (UTC)"},
    },
    "password_resets": {
        "title": "Yêu cầu đặt lại mật khẩu", "model": "PasswordReset",
        "desc": "Mã OTP 6 số gửi qua email khi quên mật khẩu; chỉ lưu bản băm, hết hạn sau 10 phút, dùng một lần.",
        "cols": {
            "id": "Mã", "user_id": "Tài khoản", "otp_hash": "OTP đã băm bcrypt",
            "expires_at": "Hết hạn (UTC)", "used": "Đã dùng", "created_at": "Thời điểm yêu cầu",
        },
    },
    "units": {
        "title": "Đơn vị", "model": "Unit",
        "desc": "Đơn vị trong trường: Khoa, Phòng Đào tạo, Phòng Công tác SV, Ban ngành. Loại đơn vị quyết định vai trò cán bộ.",
        "cols": {"id": "Mã đơn vị", "code": "Mã viết tắt, không trùng", "name": "Tên đơn vị",
                 "type": "faculty | training | student_affairs | board (không đổi sau khi tạo)"},
    },
    "staff": {
        "title": "Cán bộ phòng ban", "model": "Staff",
        "desc": "Hồ sơ cán bộ: mỗi tài khoản thuộc đúng một đơn vị. Đơn vị loại Khoa có hai vai trò: Văn phòng Khoa / Lãnh đạo Khoa.",
        "cols": {"id": "Mã cán bộ", "user_id": "Tài khoản (1 : 1)", "unit_id": "Đơn vị công tác", "position": "Chức vụ"},
    },
    "locations": {
        "title": "Địa điểm / khu vực điểm danh", "model": "Location",
        "desc": "Cơ sở, tòa nhà dùng để đối chiếu GPS khi sinh viên tự điểm danh. Tối đa một địa điểm mặc định.",
        "cols": {"id": "Mã địa điểm", "code": "Mã, không trùng", "name": "Tên", "latitude": "Vĩ độ",
                 "longitude": "Kinh độ", "radius_m": "Bán kính cho phép (m), 10 – 5000",
                 "is_default": "Áp dụng cho lịch học chưa gắn phòng/địa điểm"},
    },
    "rooms": {
        "title": "Phòng học", "model": "Room",
        "desc": "Danh mục phòng để xếp lịch. Phòng có thể có tọa độ riêng (bán kính tối thiểu 50 m), không có thì dùng tọa độ khu vực chứa phòng.",
        "cols": {"id": "Mã phòng", "code": "Mã phòng, không trùng (VD E2-101)", "name": "Tên hiển thị",
                 "building": "Tòa nhà", "floor": "Tầng", "capacity": "Sức chứa", "latitude": "Vĩ độ riêng (tùy chọn)",
                 "longitude": "Kinh độ riêng (tùy chọn)", "radius_m": "Bán kính riêng (m)",
                 "location_id": "Khu vực chứa phòng", "is_active": "Đang sử dụng (ngừng dùng thì ẩn khi xếp lịch mới)"},
    },
    "lecturers": {
        "title": "Giảng viên", "model": "Lecturer",
        "desc": "Hồ sơ giảng viên gắn với một tài khoản; thuộc một Khoa để cán bộ Khoa thấy trong phạm vi.",
        "cols": {"id": "Mã giảng viên", "user_id": "Tài khoản", "lecturer_code": "Mã GV, không trùng",
                 "department": "Bộ môn", "faculty_id": "Khoa quản lý"},
    },
    "classes": {
        "title": "Lớp học phần", "model": "Class",
        "desc": "Lớp học phần do một giảng viên phụ trách, thuộc một học kỳ và một Khoa (quyết định phạm vi xem của cán bộ Khoa).",
        "cols": {"id": "Mã lớp", "class_code": "Mã lớp, không trùng", "subject_name": "Tên môn học",
                 "lecturer_id": "Giảng viên phụ trách", "semester": "Học kỳ (VD 2026.1)", "faculty_id": "Khoa quản lý"},
    },
    "enrollments": {
        "title": "Ghi danh", "model": "Enrollment",
        "desc": "Sinh viên ghi danh vào lớp học phần (quan hệ N – N giữa students và classes).",
        "cols": {"id": "Mã", "student_id": "Sinh viên", "class_id": "Lớp học phần"},
    },
    "schedules": {
        "title": "Lịch học", "model": "Schedule",
        "desc": "Buổi học cố định trong tuần của lớp. Server chặn xếp hai lớp cùng phòng, cùng thứ, khung giờ giao nhau; giờ bắt đầu phải trước giờ kết thúc.",
        "cols": {"id": "Mã lịch", "class_id": "Lớp học phần", "weekday": "Thứ (0 = thứ Hai … 6 = Chủ nhật)",
                 "start_time": "Giờ bắt đầu", "end_time": "Giờ kết thúc",
                 "room": "Tên phòng TỰ NHẬP — chỉ có khi không chọn phòng trong danh mục (đã chọn phòng thì để trống: "
                         "mã phòng lấy qua room_id, tránh phụ thuộc bắc cầu room_id → mã phòng)",
                 "room_id": "Phòng trong danh mục", "location_id": "Địa điểm gắn trực tiếp (dữ liệu cũ)"},
    },
    "students": {
        "title": "Sinh viên", "model": "Student",
        "desc": "Hồ sơ sinh viên và trạng thái đồng ý sử dụng dữ liệu khuôn mặt (có phiên bản nội dung, cách đồng ý, người ghi nhận).",
        "cols": {"id": "Mã sinh viên", "user_id": "Tài khoản", "student_code": "MSSV, không trùng",
                 "major": "Ngành", "cohort": "Khóa", "faculty_id": "Khoa quản lý",
                 "consent_given": "Đã đồng ý sinh trắc", "consent_given_at": "Thời điểm đồng ý",
                 "consent_version": "Phiên bản nội dung đã đồng ý", "consent_method": "self (SV tự xác nhận) | paper (cán bộ nhập bản giấy)",
                 "consent_recorded_by": "Email người ghi nhận"},
    },
    "parents": {
        "title": "Phụ huynh", "model": "Parent",
        "desc": "Tài khoản phụ huynh do P. CTSV tạo và liên kết thủ công với con; có tùy chọn nhận thông báo.",
        "cols": {"id": "Mã phụ huynh", "user_id": "Tài khoản", "phone": "Số điện thoại",
                 "notify_email": "Nhận email thông báo", "notify_present": "Nhận cả tin \"có mặt\""},
    },
    "parent_students": {
        "title": "Liên kết phụ huynh – sinh viên", "model": "ParentStudent",
        "desc": "Một phụ huynh theo dõi nhiều con, một sinh viên có thể có nhiều phụ huynh (quan hệ N – N).",
        "cols": {"id": "Mã", "parent_id": "Phụ huynh", "student_id": "Sinh viên"},
    },
    "face_embeddings": {
        "title": "Dữ liệu khuôn mặt", "model": "FaceEmbedding",
        "desc": "Vector đặc trưng khuôn mặt 512 chiều (pgvector, chỉ mục HNSW cosine). Ảnh cắt chỉ lưu tạm để duyệt, xóa ngay khi duyệt / từ chối. "
                "Chỉ Phòng Công tác SV duyệt; kết quả được gửi cho sinh viên và sinh viên xác nhận đã nhận.",
        "cols": {"id": "Mã vector", "student_id": "Sinh viên", "embedding": "Vector ArcFace 512 chiều",
                 "source_image": "Ảnh khuôn mặt lưu tạm chờ duyệt (/evidence/faces/...)",
                 "status": "pending | approved | rejected", "reject_reason": "Lý do không hợp lệ (khi từ chối)",
                 "created_at": "Ngày đăng ký", "reviewed_by": "Cán bộ P.CTSV đã duyệt / từ chối",
                 "reviewed_at": "Thời điểm duyệt / từ chối", "student_ack_at": "Thời điểm SV xác nhận đã nhận kết quả"},
    },
    "attendance_sessions": {
        "title": "Phiên điểm danh", "model": "AttendanceSession",
        "desc": "Một buổi điểm danh của một lịch học trong một ngày. Chỉ mở trong khung [giờ bắt đầu − 15 phút, giờ kết thúc]; "
                "tự đóng sau giờ kết thúc 30 phút.",
        "cols": {"id": "Mã phiên", "schedule_id": "Lịch học", "session_date": "Ngày điểm danh",
                 "opened_at": "Thời điểm mở", "closed_at": "Thời điểm đóng", "status": "open | closed"},
    },
    "leave_requests": {
        "title": "Đơn xin phép vắng", "model": "LeaveRequest",
        "desc": "Sinh viên xin phép vắng một buổi học (lịch học + ngày). Giảng viên lớp hoặc Lãnh đạo Khoa duyệt / từ chối "
                "(bắt buộc lý do không hợp lệ); kết quả gửi cho sinh viên, sinh viên xác nhận đã nhận. Đơn đã duyệt ⇒ buổi đó "
                "ghi vắng có phép.",
        "cols": {"id": "Mã đơn", "student_id": "Sinh viên", "schedule_id": "Lịch học (lớp, thứ, giờ)",
                 "absence_date": "Ngày vắng (đúng thứ của lịch)", "reason": "Lý do xin phép",
                 "status": "pending | approved | rejected", "created_at": "Thời điểm nộp",
                 "reviewed_by": "Người duyệt / từ chối (GV lớp, Lãnh đạo Khoa)", "reviewed_at": "Thời điểm duyệt / từ chối",
                 "review_note": "Lý do không hợp lệ (khi từ chối) hoặc ghi chú khi duyệt",
                 "student_ack_at": "Thời điểm SV xác nhận đã nhận kết quả"},
    },
    "attendance_records": {
        "title": "Kết quả điểm danh", "model": "AttendanceRecord",
        "desc": "Kết quả của một sinh viên trong một phiên. Nguồn: camera (GV quét cả lớp), selfie (SV tự chụp + GPS), manual (xác nhận tay).",
        "cols": {"id": "Mã bản ghi", "session_id": "Phiên", "student_id": "Sinh viên", "checked_at": "Thời điểm ghi nhận",
                 "status": "present | late | absent | manual | excused", "confidence": "Độ giống khuôn mặt (cosine)",
                 "evidence_image": "Ảnh bằng chứng (/evidence/..., tự xóa sau 90 ngày)", "source": "camera | selfie | manual",
                 "latitude": "Vĩ độ khi tự điểm danh", "longitude": "Kinh độ khi tự điểm danh",
                 "location_accuracy": "Sai số GPS (m)", "distance_m": "Khoảng cách tới địa điểm (m)"},
    },
    "attendance_audits": {
        "title": "Lịch sử sửa điểm danh", "model": "AttendanceAudit",
        "desc": "Mỗi lần sửa trạng thái (kể cả duyệt / hủy duyệt có phép) ghi một dòng; lý do bắt buộc, không có chức năng xóa.",
        "cols": {"id": "Mã", "record_id": "Bản ghi điểm danh", "changed_by": "Người sửa",
                 "old_status": "Trạng thái cũ", "new_status": "Trạng thái mới", "reason": "Lý do (bắt buộc)",
                 "changed_at": "Thời điểm sửa"},
    },
    "notifications": {
        "title": "Thông báo", "model": "Notification",
        "desc": "Hộp thư trong app và hàng đợi email. Phụ huynh: khi bản ghi điểm danh của con được tạo / đổi trạng thái "
                "(mỗi bản ghi chỉ báo một lần cho mỗi loại). Sinh viên: kết quả duyệt khuôn mặt / đơn xin phép, cảnh báo "
                "chuyên cần sau thống kê. Giảng viên: đơn xin phép mới.",
        "cols": {"id": "Mã thông báo", "user_id": "Người nhận (phụ huynh, sinh viên, giảng viên)",
                 "kind": "attendance_present | _late | _absent | _excused | face_approved | face_rejected | leave_submitted "
                         "| leave_approved | leave_rejected | absence_warning",
                 "title": "Tiêu đề", "body": "Nội dung", "link": "Đường dẫn trong app", "record_id": "Bản ghi điểm danh liên quan",
                 "created_at": "Thời điểm tạo", "read_at": "Thời điểm đọc (NULL = chưa đọc)",
                 "email_status": "pending | sent | failed | skipped", "email_attempts": "Số lần thử gửi",
                 "email_error": "Lỗi gửi gần nhất", "emailed_at": "Thời điểm gửi email"},
    },
    "audit_logs": {
        "title": "Nhật ký hệ thống", "model": "AuditLog",
        "desc": "Ai, lúc nào, làm gì, với đối tượng nào, từ IP nào. Ghi tự động mọi thêm / sửa / xóa dữ liệu quản lý (sự kiện after_flush), "
                "ghi tường minh đăng nhập, đăng xuất, xuất báo cáo. Không lưu mật khẩu, OTP, vector, ảnh.",
        "cols": {"id": "Mã", "created_at": "Thời điểm", "actor_id": "Người thao tác", "actor_email": "Email (bản chụp lúc ghi)",
                 "actor_role": "Vai trò (bản chụp)", "action": "Hành động, VD auth.login, student.update",
                 "target_type": "Loại đối tượng", "target_id": "Mã đối tượng", "target_label": "Nhãn đối tượng (bản chụp)",
                 "faculty_id": "Khoa liên quan (Lãnh đạo Khoa chỉ xem Khoa mình)", "ip": "Địa chỉ IP",
                 "success": "Thành công / thất bại", "detail": "Chi tiết JSON {trường: [cũ, mới]}"},
    },
}

# ----------------------------------------------------------------------------- quy trinh
# Moi buoc: k = start | step | dec | end; t = tieu de; s = mo ta ngan; db = ["R:bang", "W:bang"].
# Buoc "dec" co nhanh "no" (khung net dut) khi dieu kien KHONG thoa.
def _s(k, t, s="", db=(), no=None):
    d = {"k": k, "t": t, "s": s, "db": list(db)}
    if no is not None:
        d["no"] = {"t": no[0], "s": no[1], "db": list(no[2])}
    return d


FLOWS = [
    {"key": "master", "tab": "Toàn cảnh (Master)", "func": True,
     "title": "Toàn cảnh: từ danh mục đến báo cáo chuyên cần",
     "desc": "Chuỗi nghiệp vụ xuyên suốt của 9 vai trò. Mỗi bước ghi rõ bảng CSDL được đọc (R) hoặc ghi (W). "
             "Mọi thao tác ghi dữ liệu quản lý đều tự động sinh một dòng audit_logs.",
     "steps": [
         _s("start", "Quản trị tạo đơn vị, cán bộ", "vai trò suy ra từ loại đơn vị", ["W:units", "W:users", "W:staff"]),
         _s("step", "P.ĐT tạo lớp, lịch, ghi danh", "chặn trùng phòng cùng giờ", ["W:classes", "W:schedules", "W:enrollments"]),
         _s("dec", "SV đồng ý sinh trắc?", db=["W:students"], no=("Chỉ điểm danh tay", "GV xác nhận trực tiếp", [])),
         _s("step", "SV đăng ký khuôn mặt", "kiểm chất lượng, chống giả mạo", ["W:face_embeddings"]),
         _s("dec", "P.CTSV duyệt khuôn mặt?", no=("Từ chối + lý do không hợp lệ", "gửi kết quả, SV xác nhận, chụp lại",
                                                ["W:face_embeddings", "W:notifications"])),
         _s("step", "Gửi kết quả cho SV, SV xác nhận", "thông báo trong app", ["W:notifications", "W:face_embeddings"]),
         _s("step", "SV nộp đơn xin phép (nếu vắng)", "GV lớp / LĐ Khoa duyệt", ["W:leave_requests"]),
         _s("step", "GV mở phiên điểm danh", "từ 15 phút trước giờ học", ["R:schedules", "W:attendance_sessions"]),
         _s("step", "Quét camera / SV tự điểm danh", "khuôn mặt + GPS", ["R:face_embeddings", "W:attendance_records"]),
         _s("dec", "Nhận diện và kiểm tra đạt?", no=("GV xác nhận tay", "trạng thái manual", ["W:attendance_records"])),
         _s("step", "Báo phụ huynh", "trong app + email", ["R:parent_students", "W:notifications"]),
         _s("step", "Đóng phiên, sinh vắng / có phép", "đơn đã duyệt ⇒ vắng có phép", ["R:leave_requests", "W:attendance_records"]),
         _s("step", "Thống kê chuyên cần", "chỉ tính phiên đã đóng", ["R:attendance_sessions", "R:attendance_records"]),
         _s("end", "Cảnh báo sau thống kê (≥ 20%)", "gửi SV + phụ huynh; báo cáo, Excel", ["W:notifications"]),
     ]},
    {"key": "ph1", "tab": "PH1. Xác thực & tài khoản", "func": True,
     "title": "Phân hệ PH1: Đăng nhập, token và mật khẩu",
     "desc": "Access token 480 phút + refresh token xoay vòng 30 ngày. Khóa tạm sau 5 lần sai trong 5 phút. "
             "Đổi / đặt lại mật khẩu làm mọi phiên cũ mất hiệu lực.",
     "steps": [
         _s("start", "Nhập email + mật khẩu", "form OAuth2"),
         _s("dec", "Chưa bị khóa tạm?", no=("Từ chối (429)", "ghi nhật ký login_locked", ["W:audit_logs"])),
         _s("dec", "Đúng mật khẩu?", db=["R:users"], no=("Từ chối (401)", "đếm lần sai, ghi nhật ký", ["W:audit_logs"])),
         _s("step", "Cấp access + refresh token", "chỉ lưu SHA-256 của refresh token", ["W:refresh_tokens", "W:audit_logs"]),
         _s("step", "Gọi API kèm Bearer token", "kiểm jti, token_version", ["R:revoked_tokens", "R:users"]),
         _s("dec", "Access token còn hạn?", no=("Làm mới, xoay vòng token", "dùng lại token cũ ⇒ thu hồi hết", ["W:refresh_tokens"])),
         _s("step", "Quên mật khẩu: gửi OTP", "6 số, hết hạn 10 phút", ["W:password_resets"]),
         _s("step", "Đặt lại / đổi mật khẩu", "tăng token_version", ["R:password_resets", "W:users", "W:refresh_tokens"]),
         _s("end", "Đăng xuất", "thu hồi jti + refresh token", ["W:revoked_tokens", "W:refresh_tokens"]),
     ]},
    {"key": "ph2", "tab": "PH2. Danh mục hệ thống", "func": True,
     "title": "Phân hệ PH2: Đơn vị, cán bộ, địa điểm, phòng học",
     "desc": "Quản trị viên quản lý đơn vị và tài khoản cán bộ; Quản trị viên và P. Đào tạo quản lý địa điểm điểm danh và phòng học.",
     "steps": [
         _s("start", "Tạo đơn vị", "Khoa, P.ĐT, P.CTSV, Ban ngành", ["W:units"]),
         _s("dec", "Mã đơn vị chưa trùng?", db=["R:units"], no=("Báo lỗi trùng mã", "", [])),
         _s("step", "Tạo tài khoản cán bộ", "vai trò suy ra từ loại đơn vị", ["W:users", "W:staff"]),
         _s("step", "Khai báo địa điểm", "tọa độ, bán kính, mặc định", ["W:locations"]),
         _s("step", "Khai báo phòng học", "thuộc khu vực, bán kính ≥ 50 m", ["R:locations", "W:rooms"]),
         _s("dec", "Không còn dữ liệu liên quan?", db=["R:staff", "R:schedules"],
            no=("Từ chối xóa (409)", "gợi ý ngừng sử dụng phòng", [])),
         _s("end", "Xóa / ngừng sử dụng", "nhật ký ghi tự động", ["W:units", "W:rooms", "W:audit_logs"]),
     ]},
    {"key": "ph3", "tab": "PH3. Đào tạo", "func": True,
     "title": "Phân hệ PH3: Giảng viên, lớp học phần, ghi danh, lịch học",
     "desc": "P. Đào tạo nhập lớp, ghi danh, xếp lịch toàn trường; Văn phòng Khoa chỉ nhập lớp học phần của Khoa mình "
             "(không ghi danh, không xếp lịch); server chặn trùng phòng.",
     "steps": [
         _s("start", "Tạo hồ sơ giảng viên", "email, mã GV, bộ môn, Khoa", ["W:users", "W:lecturers"]),
         _s("step", "Tạo lớp học phần", "VP Khoa: lớp luôn thuộc Khoa mình", ["R:lecturers", "W:classes"]),
         _s("step", "Ghi danh sinh viên", "chỉ QTV / P.ĐT", ["R:students", "W:enrollments"]),
         _s("step", "Chọn thứ, giờ, phòng", "chỉ QTV / P.ĐT xếp lịch", ["R:rooms"]),
         _s("dec", "Phòng trống khung giờ?", db=["R:schedules"], no=("Từ chối: trùng phòng", "nêu lớp đang chiếm", [])),
         _s("step", "Lưu lịch học", "", ["W:schedules"]),
         _s("end", "Lịch tuần, lịch dạy hôm nay", "kèm trạng thái phiên", ["R:schedules", "R:attendance_sessions"]),
     ]},
    {"key": "ph4", "tab": "PH4. Người học", "func": True,
     "title": "Phân hệ PH4: Sinh viên, đồng ý sinh trắc, phụ huynh",
     "desc": "P. CTSV quản lý hồ sơ sinh viên và phụ huynh; sinh viên tự đồng ý (hoặc cán bộ nhập bản giấy) theo nội dung có phiên bản.",
     "steps": [
         _s("start", "Tạo hồ sơ sinh viên", "MSSV, ngành, khóa, Khoa", ["W:users", "W:students"]),
         _s("step", "SV đọc nội dung đồng ý", "phiên bản 2026-10"),
         _s("dec", "Đồng ý đúng phiên bản?", no=("Yêu cầu đọc lại (409)", "", [])),
         _s("step", "Ghi nhận đồng ý", "self / paper, người ghi nhận", ["W:students"]),
         _s("step", "Tạo tài khoản phụ huynh", "", ["W:users", "W:parents"]),
         _s("step", "Liên kết phụ huynh với con", "bằng MSSV", ["R:students", "W:parent_students"]),
         _s("end", "Rút đồng ý (khi cần)", "xóa ngay vector + ảnh", ["W:students", "W:face_embeddings"]),
     ]},
    {"key": "ph5", "tab": "PH5. Sinh trắc khuôn mặt", "func": True,
     "title": "Phân hệ PH5: Đăng ký và duyệt dữ liệu khuôn mặt",
     "desc": "Server kiểm chất lượng ảnh, chống giả mạo, chống trùng với sinh viên khác; CHỈ P. CTSV duyệt (từ chối phải ghi lý do "
             "không hợp lệ); kết quả gửi cho sinh viên, sinh viên xác nhận đã nhận; ảnh tạm xóa ngay sau quyết định.",
     "steps": [
         _s("start", "Gửi một hoặc nhiều ảnh", "SV, P.CTSV hoặc GV lớp mình", ["R:students"]),
         _s("dec", "Đã đồng ý sinh trắc?", db=["R:students"], no=("Từ chối", "yêu cầu đồng ý trước", [])),
         _s("dec", "Ảnh đạt, là mặt thật?", no=("Loại ảnh + lý do", "mặt ≥ 112 px, đủ sáng, đủ nét", [])),
         _s("dec", "Không giống SV khác?", db=["R:face_embeddings"], no=("Loại ảnh", "độ giống > 0.60", [])),
         _s("step", "Lưu vector chờ duyệt", "ảnh cắt lưu tạm", ["W:face_embeddings"]),
         _s("dec", "P.CTSV duyệt?", db=["R:face_embeddings"],
            no=("Từ chối + lý do không hợp lệ", "xóa ảnh tạm, SV chụp lại", ["W:face_embeddings"])),
         _s("step", "Approved, xóa ảnh tạm", "dùng để nhận diện", ["W:face_embeddings"]),
         _s("step", "Gửi kết quả duyệt cho SV", "thông báo trong app", ["W:notifications"]),
         _s("end", "SV xác nhận đã nhận kết quả", "student_ack_at", ["W:face_embeddings"]),
     ]},
    {"key": "ph6", "tab": "PH6. Điểm danh", "func": True,
     "title": "Phân hệ PH6: Phiên điểm danh và ghi nhận kết quả",
     "desc": "Quét camera cả lớp (xác nhận đủ 2 khung hình) hoặc sinh viên tự điểm danh (GPS + khuôn mặt chính mình); "
             "sinh viên nộp đơn xin phép, GV lớp / Lãnh đạo Khoa duyệt; đóng phiên thì sinh bản ghi vắng hoặc vắng có phép.",
     "steps": [
         _s("start", "GV mở phiên", "đúng ngày, đúng thứ", ["R:schedules"]),
         _s("dec", "Trong khung giờ, chưa có phiên?", db=["R:attendance_sessions"],
            no=("Từ chối mở phiên", "chưa đến giờ / đã kết thúc", [])),
         _s("step", "Phiên đang mở", "nhận điểm danh tới giờ kết thúc + 30'", ["W:attendance_sessions"]),
         _s("step", "Quét camera / SV tự chụp", "kiểm GPS trước nhận diện", ["R:enrollments", "R:rooms", "R:locations"]),
         _s("dec", "Khớp khuôn mặt, ảnh thật?", db=["R:face_embeddings"],
            no=("Không ghi nhận", "giả mạo: lưu ảnh bằng chứng", [])),
         _s("step", "Ghi present / late", "nguồn camera / selfie", ["W:attendance_records"]),
         _s("step", "Xác nhận tay (khi cần)", "trạng thái manual", ["W:attendance_records"]),
         _s("step", "SV nộp đơn xin phép", "đúng thứ của lịch, có lý do", ["R:enrollments", "W:leave_requests"]),
         _s("dec", "GV lớp / LĐ Khoa duyệt đơn?", db=["R:leave_requests"],
            no=("Từ chối + lý do không hợp lệ", "gửi kết quả, SV xác nhận", ["W:leave_requests", "W:notifications"])),
         _s("step", "Đóng phiên", "GV đóng hoặc tự đóng +30 phút", ["W:attendance_sessions"]),
         _s("step", "Sinh vắng / vắng có phép", "đơn đã duyệt ⇒ excused", ["R:leave_requests", "W:attendance_records"]),
         _s("end", "Sửa kết quả (có lý do)", "lưu lịch sử sửa", ["W:attendance_records", "W:attendance_audits"]),
     ]},
    {"key": "ph7", "tab": "PH7. Thông báo", "func": True,
     "title": "Phân hệ PH7: Thông báo cho phụ huynh, sinh viên, giảng viên",
     "desc": "Phụ huynh: sinh tự động trong cùng giao dịch ghi điểm danh. Sinh viên: kết quả duyệt khuôn mặt / đơn, cảnh báo chuyên cần. "
             "Giảng viên: đơn xin phép mới. Email gửi sau bằng tác vụ nền nên mạng chậm không làm chậm nghiệp vụ.",
     "steps": [
         _s("start", "Bản ghi điểm danh tạo / đổi", "sự kiện before_flush", ["R:attendance_records"]),
         _s("dec", "SV có phụ huynh liên kết?", db=["R:parent_students"], no=("Không tạo thông báo", "", [])),
         _s("dec", "Phụ huynh nhận loại này?", db=["R:parents"], no=("Bỏ qua tin \"có mặt\"", "phụ huynh đã tắt", [])),
         _s("step", "Tạo thông báo trong app", "mỗi loại một lần / bản ghi", ["W:notifications"]),
         _s("step", "Gửi email theo hàng đợi", "15 giây / lần, thử tối đa 3 lần", ["W:notifications"]),
         _s("step", "Phụ huynh xem hộp thư", "chuông đếm chưa đọc", ["R:notifications"]),
         _s("end", "Đánh dấu đã đọc", "", ["W:notifications"]),
     ]},
    {"key": "ph8", "tab": "PH8. Báo cáo, thống kê", "func": True,
     "title": "Phân hệ PH8: Chuyên cần, cảnh báo vắng, thống kê",
     "desc": "Chỉ tính phiên đã đóng. Tỉ lệ vắng = số buổi absent / tổng phiên đã đóng; có phép không tính vắng; cảnh báo khi ≥ 20%.",
     "steps": [
         _s("start", "Chọn lớp / học kỳ", "theo phạm vi xem", ["R:classes"]),
         _s("step", "Đếm phiên đã đóng", "", ["R:attendance_sessions"]),
         _s("step", "Gom bản ghi theo SV", "present, late, absent, excused, manual", ["R:attendance_records"]),
         _s("step", "Thống kê theo lớp", "tỉ lệ vắng, có phép không tính", ["R:attendance_records"]),
         _s("dec", "Sau thống kê: tỉ lệ vắng ≥ 20%?", no=("Không cảnh báo", "", [])),
         _s("step", "Gửi cảnh báo cho SV + phụ huynh", "SV vừa vượt ngưỡng khi đóng phiên", ["R:parent_students", "W:notifications"]),
         _s("step", "Xuất Excel", "ghi nhật ký report.exported", ["R:students", "W:audit_logs"]),
         _s("end", "Thống kê tổng hợp theo Khoa", "chỉ số liệu, không tên / ảnh", ["R:units", "R:enrollments"]),
     ]},
    {"key": "ph9", "tab": "PH9. Nhật ký hệ thống", "func": True,
     "title": "Phân hệ PH9: Ghi và tra cứu nhật ký hệ thống",
     "desc": "Ghi tự động ở tầng CSDL nên không phụ thuộc từng chức năng nhớ ghi log; cột nhạy cảm chỉ ghi là \"đã thay đổi\".",
     "steps": [
         _s("start", "Thêm / sửa / xóa dữ liệu", "15 loại đối tượng quản lý"),
         _s("step", "Ghi nhật ký tự động", "sự kiện after_flush", ["W:audit_logs"]),
         _s("step", "Ghi đăng nhập, xuất báo cáo", "ghi tường minh", ["W:audit_logs"]),
         _s("step", "Che cột nhạy cảm", "mật khẩu, vector, OTP, token"),
         _s("dec", "Người xem là Quản trị?", db=["R:staff"],
            no=("Lãnh đạo Khoa: Khoa mình", "lọc theo faculty_id", ["R:audit_logs"])),
         _s("end", "Tra cứu, lọc nhật ký", "từ khóa, nhóm, kết quả, ngày", ["R:audit_logs"]),
     ]},
    # ---- theo vai tro ----
    {"key": "qt", "tab": "1. Quản trị viên", "func": False,
     "title": "Quy trình nghiệp vụ của Quản trị viên",
     "desc": "Quản lý đơn vị, tài khoản cán bộ, danh mục; có toàn quyền điểm danh, xem đơn xin phép và nhật ký toàn trường. "
             "Không xét duyệt khuôn mặt (việc của P. CTSV).",
     "steps": [
         _s("start", "Đăng nhập", "", ["R:users"]),
         _s("step", "Quản lý đơn vị", "", ["W:units"]),
         _s("step", "Tạo, sửa tài khoản cán bộ", "", ["W:users", "W:staff"]),
         _s("step", "Địa điểm, phòng học", "", ["W:locations", "W:rooms"]),
         _s("step", "Mở phiên, sửa điểm danh", "mọi lớp", ["W:attendance_sessions", "W:attendance_records"]),
         _s("step", "Xem đơn xin phép", "chỉ xem, không duyệt", ["R:leave_requests"]),
         _s("step", "Xem thống kê toàn trường", "", ["R:attendance_records"]),
         _s("end", "Xem nhật ký hệ thống", "", ["R:audit_logs"]),
     ]},
    {"key": "dt", "tab": "2. Phòng Đào tạo", "func": False,
     "title": "Quy trình nghiệp vụ của Phòng Đào tạo",
     "desc": "Quản lý giảng viên, lớp học phần, ghi danh, lịch học, phòng và địa điểm toàn trường; xem điểm danh, báo cáo.",
     "steps": [
         _s("start", "Hồ sơ giảng viên", "", ["W:lecturers"]),
         _s("step", "Lớp học phần, ghi danh", "", ["W:classes", "W:enrollments"]),
         _s("step", "Xếp lịch học", "", ["R:rooms"]),
         _s("dec", "Phòng trống khung giờ?", db=["R:schedules"], no=("Chọn phòng / giờ khác", "", [])),
         _s("step", "Lưu lịch học", "", ["W:schedules"]),
         _s("step", "Địa điểm, phòng học", "", ["W:locations", "W:rooms"]),
         _s("end", "Xem điểm danh, cảnh báo, Excel", "toàn trường", ["R:attendance_records"]),
     ]},
    {"key": "ctsv", "tab": "3. Phòng CTSV", "func": False,
     "title": "Quy trình nghiệp vụ của Phòng Công tác sinh viên",
     "desc": "Quản lý hồ sơ sinh viên, phụ huynh, đồng ý sinh trắc; là đơn vị DUY NHẤT duyệt khuôn mặt (gửi kết quả cho sinh viên); "
             "duyệt vắng có phép toàn trường.",
     "steps": [
         _s("start", "Hồ sơ sinh viên", "", ["W:students"]),
         _s("step", "Ghi nhận đồng ý bản giấy", "method = paper", ["W:students"]),
         _s("step", "Phụ huynh, liên kết con", "", ["W:parents", "W:parent_students"]),
         _s("step", "Xem khuôn mặt chờ duyệt", "kèm cảnh báo trùng", ["R:face_embeddings"]),
         _s("dec", "Ảnh hợp lệ, không trùng?", no=("Từ chối + lý do không hợp lệ", "gửi kết quả cho SV",
                                                   ["W:face_embeddings", "W:notifications"])),
         _s("step", "Duyệt khuôn mặt, gửi kết quả", "SV xác nhận đã nhận", ["W:face_embeddings", "W:notifications"]),
         _s("step", "Duyệt vắng có phép", "toàn trường", ["W:attendance_records", "W:attendance_audits"]),
         _s("end", "Xem báo cáo, cảnh báo vắng", "", ["R:attendance_records"]),
     ]},
    {"key": "vpk", "tab": "4. Văn phòng Khoa", "func": False,
     "title": "Quy trình nghiệp vụ của Văn phòng Khoa",
     "desc": "Nhập liệu trong phạm vi Khoa mình: lớp học phần, phân công giảng viên; KHÔNG ghi danh, KHÔNG xếp lịch (việc của "
             "P. Đào tạo); xem dữ liệu của Khoa.",
     "steps": [
         _s("start", "Đăng nhập (gắn Khoa)", "", ["R:staff"]),
         _s("step", "Lớp học phần của Khoa", "lớp luôn thuộc Khoa mình", ["W:classes"]),
         _s("step", "Xem lịch, danh sách ghi danh", "do P. Đào tạo nhập", ["R:enrollments", "R:schedules"]),
         _s("step", "Phân công GV dạy lớp", "", ["R:lecturers", "W:classes"]),
         _s("step", "Xem SV, GV của Khoa", "", ["R:students", "R:lecturers"]),
         _s("end", "Xem điểm danh, báo cáo Khoa", "", ["R:attendance_records"]),
     ]},
    {"key": "ldk", "tab": "5. Lãnh đạo Khoa", "func": False,
     "title": "Quy trình nghiệp vụ của Lãnh đạo Khoa",
     "desc": "Giám sát và phê duyệt trong Khoa mình; không nhập liệu (việc của Văn phòng Khoa).",
     "steps": [
         _s("start", "Đăng nhập (gắn Khoa)", "", ["R:staff"]),
         _s("step", "Giám sát điểm danh Khoa", "", ["R:attendance_sessions", "R:attendance_records"]),
         _s("step", "Xem cảnh báo vắng", "", ["R:attendance_records"]),
         _s("step", "Xem đơn xin phép của Khoa", "", ["R:leave_requests"]),
         _s("dec", "Đơn xin phép hợp lệ?", no=("Từ chối + lý do không hợp lệ", "gửi kết quả, SV xác nhận",
                                             ["W:leave_requests", "W:notifications"])),
         _s("step", "Duyệt đơn ⇒ vắng có phép", "gửi kết quả cho SV", ["W:leave_requests", "W:attendance_records"]),
         _s("step", "Thống kê tổng hợp Khoa", "", ["R:classes"]),
         _s("end", "Xem nhật ký của Khoa", "", ["R:audit_logs"]),
     ]},
    {"key": "bn", "tab": "6. Ban ngành", "func": False,
     "title": "Quy trình nghiệp vụ của Ban ngành",
     "desc": "Chỉ xem số liệu thống kê tổng hợp toàn trường; không có tên, ảnh sinh viên.",
     "steps": [
         _s("start", "Đăng nhập", "", ["R:users"]),
         _s("step", "Chọn học kỳ", "mặc định học kỳ mới nhất", ["R:classes"]),
         _s("step", "Thống kê tổng hợp", "tỉ lệ đi học, tỉ lệ vắng", ["R:attendance_sessions", "R:attendance_records"]),
         _s("end", "So sánh giữa các Khoa", "", ["R:units"]),
     ]},
    {"key": "gv", "tab": "7. Giảng viên", "func": False,
     "title": "Quy trình nghiệp vụ của Giảng viên",
     "desc": "Mở phiên, quét camera, xác nhận tay, đóng phiên, sửa kết quả và duyệt đơn xin phép cho lớp mình dạy.",
     "steps": [
         _s("start", "Xem lịch dạy hôm nay", "", ["R:schedules"]),
         _s("step", "Mở phiên", "", ["W:attendance_sessions"]),
         _s("step", "Duyệt / từ chối đơn xin phép", "lý do không hợp lệ khi từ chối", ["W:leave_requests", "W:notifications"]),
         _s("step", "Quét camera cả lớp", "", ["R:face_embeddings", "W:attendance_records"]),
         _s("dec", "SV được nhận diện?", no=("Xác nhận tay", "", ["W:attendance_records"])),
         _s("step", "Đóng phiên, sinh vắng", "", ["W:attendance_sessions", "W:attendance_records"]),
         _s("step", "Sửa kết quả (có lý do)", "", ["W:attendance_records", "W:attendance_audits"]),
         _s("end", "Báo cáo lớp, xuất Excel", "", ["R:attendance_records"]),
     ]},
    {"key": "sv", "tab": "8. Sinh viên", "func": False,
     "title": "Quy trình nghiệp vụ của Sinh viên",
     "desc": "Đồng ý sinh trắc → đăng ký khuôn mặt → nhận và xác nhận kết quả duyệt → tự điểm danh (GPS + ảnh) → "
             "nộp đơn xin phép khi vắng → xem chuyên cần, cảnh báo.",
     "steps": [
         _s("start", "Đăng nhập, xem lịch tuần", "", ["R:schedules"]),
         _s("step", "Đồng ý sinh trắc", "", ["W:students"]),
         _s("step", "Đăng ký khuôn mặt", "", ["W:face_embeddings"]),
         _s("dec", "Được duyệt?", no=("Chụp lại ảnh khác", "xem lý do không hợp lệ", ["W:face_embeddings"])),
         _s("step", "Xác nhận đã nhận kết quả", "", ["R:notifications", "W:face_embeddings"]),
         _s("step", "Vào buổi học đang mở", "", ["R:attendance_sessions"]),
         _s("step", "Bật GPS, chụp ảnh", "", ["R:rooms", "R:locations"]),
         _s("dec", "Đạt kiểm tra?", no=("Báo lý do, thử lại", "hoặc nhờ GV xác nhận tay", [])),
         _s("step", "Ghi điểm danh", "present / late", ["W:attendance_records"]),
         _s("step", "Nộp đơn xin phép (khi vắng)", "nhận kết quả, xác nhận", ["W:leave_requests"]),
         _s("end", "Xem chuyên cần, cảnh báo", "", ["R:attendance_records", "R:notifications"]),
     ]},
    {"key": "ph", "tab": "9. Phụ huynh", "func": False,
     "title": "Quy trình nghiệp vụ của Phụ huynh",
     "desc": "Theo dõi chuyên cần và nhận thông báo điểm danh của con đã được liên kết.",
     "steps": [
         _s("start", "Đăng nhập", "", ["R:users"]),
         _s("step", "Xem danh sách con", "", ["R:parent_students"]),
         _s("step", "Nhận thông báo điểm danh, cảnh báo", "chuông + email", ["R:notifications"]),
         _s("step", "Xem chuyên cần của con", "chi tiết từng buổi", ["R:attendance_records"]),
         _s("step", "Đánh dấu đã đọc", "", ["W:notifications"]),
         _s("end", "Tùy chọn nhận email", "", ["W:parents"]),
     ]},
]

# ----------------------------------------------------------------------------- cay chuc nang
# Moi vai tro: groups[menu, rows[[chuc nang, input, output]], readonly?]
ROLES = [
    {"id": "qt", "name": "Quản trị viên", "role": "admin", "color": "#DC2626", "letter": "QT",
     "desc": "Quản trị đơn vị, tài khoản cán bộ và danh mục; toàn quyền thao tác điểm danh; xem đơn xin phép, nhật ký toàn trường; không xét duyệt khuôn mặt.",
     "groups": [
         {"menu": "Quản lý\nđơn vị", "rows": [
             ["Xem danh sách đơn vị", "Loại đơn vị (tùy chọn)", "Danh sách: mã, tên, loại"],
             ["Thêm đơn vị", "Mã, tên, loại (Khoa, P.ĐT, P.CTSV, Ban ngành)", "Đơn vị mới; mã trùng thì báo lỗi"],
             ["Sửa đơn vị", "Mã, tên", "Đơn vị đã sửa (không đổi loại)"],
             ["Xóa đơn vị", "Mã đơn vị", "Đơn vị bị xóa; còn cán bộ / SV / GV / lớp thì từ chối"],
         ]},
         {"menu": "Tài khoản\ncán bộ", "rows": [
             ["Tra cứu cán bộ", "Từ khóa, đơn vị, phân trang", "Danh sách cán bộ: đơn vị, vai trò, chức vụ"],
             ["Tạo tài khoản cán bộ", "Email, mật khẩu, họ tên, đơn vị, chức vụ, Lãnh đạo Khoa?", "Tài khoản mới, vai trò suy ra từ loại đơn vị"],
             ["Sửa / chuyển đơn vị", "Họ tên, đơn vị, chức vụ", "Hồ sơ đã sửa, vai trò đổi theo đơn vị mới"],
             ["Xóa cán bộ", "Mã cán bộ", "Xóa; đã từng sửa điểm danh thì từ chối (giữ vết)"],
         ]},
         {"menu": "Điểm danh\n(mọi lớp)", "rows": [
             ["Mở phiên, quét camera, xác nhận tay", "Lịch học, khung hình, mã SV", "Phiên đang mở, bản ghi điểm danh"],
             ["Sửa kết quả điểm danh", "Mã bản ghi, trạng thái mới, lý do", "Bản ghi đã sửa + lịch sử sửa"],
         ]},
         {"menu": "Nhật ký\nhệ thống", "rows": [
             ["Tra cứu nhật ký", "Từ khóa, nhóm hành động, kết quả, khoảng ngày", "Danh sách nhật ký, mới nhất trước"],
         ]},
     ]},
    {"id": "dt", "name": "Phòng Đào tạo", "role": "training_office", "color": "#2563EB", "letter": "ĐT",
     "desc": "Quản lý giảng viên, lớp học phần, ghi danh, lịch học, phòng học và địa điểm toàn trường.",
     "groups": [
         {"menu": "Giảng viên", "rows": [
             ["Tra cứu giảng viên", "Từ khóa (mã, họ tên), Khoa, phân trang", "Danh sách giảng viên"],
             ["Thêm giảng viên", "Email, mật khẩu, họ tên, mã GV, bộ môn, Khoa", "Hồ sơ và tài khoản giảng viên"],
             ["Sửa giảng viên", "Họ tên, bộ môn, Khoa", "Hồ sơ đã sửa"],
             ["Xóa giảng viên", "Mã giảng viên", "Xóa; đang dạy lớp hoặc đã sửa điểm danh thì từ chối"],
         ]},
         {"menu": "Lớp học phần\n& ghi danh", "rows": [
             ["Tra cứu lớp", "Từ khóa, học kỳ, Khoa, phân trang", "Danh sách lớp: giảng viên, Khoa, sĩ số"],
             ["Thêm / sửa lớp, phân công GV", "Mã lớp, tên môn, giảng viên, học kỳ, Khoa", "Lớp mới / đã sửa; mã trùng thì báo lỗi"],
             ["Xóa lớp", "Mã lớp", "Xóa; đã có SV hoặc lịch thì từ chối"],
             ["Ghi danh / rút sinh viên", "Mã lớp, mã SV", "Danh sách SV của lớp cập nhật"],
         ]},
         {"menu": "Lịch học", "rows": [
             ["Tra cứu toàn bộ lịch", "Từ khóa (mã lớp, môn, phòng), phân trang", "Lịch kèm lớp, phòng, địa điểm"],
             ["Thêm / sửa lịch học", "Lớp, thứ, giờ bắt đầu, giờ kết thúc, phòng", "Lịch mới; trùng phòng cùng giờ thì từ chối"],
             ["Xóa lịch học", "Mã lịch", "Xóa; đã có phiên điểm danh thì từ chối"],
         ]},
         {"menu": "Địa điểm\n& phòng học", "rows": [
             ["Thêm / sửa địa điểm", "Mã, tên, vĩ độ, kinh độ, bán kính, mặc định", "Địa điểm (tối đa một mặc định)"],
             ["Lấy vị trí hiện tại", "GPS của thiết bị", "Vĩ độ, kinh độ điền sẵn"],
             ["Thêm / sửa / ngừng dùng phòng", "Mã, tên, khu vực, tòa, tầng, sức chứa, tọa độ", "Phòng mới / đã sửa"],
         ]},
         {"menu": "Theo dõi\nđiểm danh", "readonly": True, "rows": [
             ["Xem phiên và kết quả điểm danh", "Lớp, phiên", "Danh sách SV kèm trạng thái, ảnh bằng chứng"],
             ["Cảnh báo vắng, xuất Excel", "Lớp, học kỳ", "SV vắng ≥ 20%, tệp .xlsx"],
             ["Thống kê tổng hợp", "Học kỳ", "Chỉ số toàn trường, theo Khoa"],
         ]},
     ]},
    {"id": "ctsv", "name": "Phòng Công tác SV", "role": "student_affairs", "color": "#0891B2", "letter": "CT",
     "desc": "Quản lý hồ sơ sinh viên, phụ huynh, đồng ý sinh trắc; DUY NHẤT duyệt dữ liệu khuôn mặt và gửi kết quả cho sinh viên; duyệt vắng có phép toàn trường.",
     "groups": [
         {"menu": "Hồ sơ\nsinh viên", "rows": [
             ["Tra cứu sinh viên", "Từ khóa (MSSV, họ tên), Khoa, phân trang", "Danh sách SV kèm trạng thái khuôn mặt, đồng ý"],
             ["Thêm / sửa sinh viên", "Email, mật khẩu, họ tên, MSSV, ngành, khóa, Khoa", "Hồ sơ và tài khoản SV"],
             ["Xóa sinh viên", "Mã SV", "Xóa; đã ghi danh / có khuôn mặt / có điểm danh thì từ chối"],
         ]},
         {"menu": "Đồng ý\nsinh trắc", "rows": [
             ["Ghi nhận đồng ý bản giấy", "Mã SV, phiên bản nội dung, method = paper", "SV đã đồng ý, lưu người ghi nhận"],
             ["Rút đồng ý thay SV", "Mã SV (theo đơn)", "Xóa toàn bộ vector và ảnh khuôn mặt"],
         ]},
         {"menu": "Phụ huynh", "rows": [
             ["Thêm / sửa / xóa phụ huynh", "Email, mật khẩu, họ tên, số điện thoại", "Tài khoản phụ huynh"],
             ["Liên kết con", "Mã phụ huynh, MSSV", "Liên kết mới; đã có thì báo lỗi"],
             ["Gỡ liên kết", "Mã phụ huynh, mã SV", "Liên kết bị gỡ"],
         ]},
         {"menu": "Duyệt\nkhuôn mặt", "rows": [
             ["Danh sách chờ duyệt", "—", "Ảnh cắt, MSSV, cảnh báo giống SV khác (kèm độ giống)"],
             ["Duyệt", "Mã vector", "Trạng thái approved; ảnh tạm bị xóa"],
             ["Từ chối kèm lý do", "Mã vector, lý do", "Trạng thái rejected; ảnh tạm bị xóa"],
             ["Đăng ký khuôn mặt hộ SV", "Mã SV, ảnh", "Vector chờ duyệt"],
         ]},
         {"menu": "Duyệt\ncó phép", "rows": [
             ["Xem chuyên cần một SV", "Mã SV, học kỳ", "Chuyên cần theo lớp, chi tiết từng buổi"],
             ["Duyệt / hủy duyệt có phép", "Mã bản ghi, lý do", "Vắng → có phép (hoặc ngược lại) + lịch sử sửa"],
         ]},
     ]},
    {"id": "vpk", "name": "Văn phòng Khoa", "role": "faculty_office", "color": "#059669", "letter": "VK",
     "desc": "Giáo vụ Khoa: nhập lớp học phần, phân công giảng viên trong Khoa mình; không ghi danh, không xếp lịch.",
     "groups": [
         {"menu": "Lớp học phần\ncủa Khoa", "rows": [
             ["Tra cứu lớp của Khoa", "Từ khóa, học kỳ", "Danh sách lớp thuộc Khoa"],
             ["Thêm lớp", "Mã lớp, tên môn, giảng viên, học kỳ", "Lớp mới, luôn thuộc Khoa mình"],
             ["Sửa lớp, phân công GV", "Thông tin lớp, giảng viên", "Lớp đã sửa (không chuyển sang Khoa khác)"],
         ]},
         {"menu": "Ghi danh\n& lịch học", "rows": [
             ["Ghi danh / rút sinh viên", "Mã lớp, mã SV", "Danh sách SV của lớp cập nhật"],
             ["Xếp / sửa lịch học", "Thứ, giờ, phòng", "Lịch học; trùng phòng thì từ chối"],
         ]},
         {"menu": "Theo dõi\nKhoa", "readonly": True, "rows": [
             ["Xem SV, GV của Khoa", "Từ khóa", "Danh sách trong phạm vi Khoa"],
             ["Xem điểm danh, báo cáo Khoa", "Lớp, học kỳ", "Kết quả, cảnh báo vắng, tệp Excel"],
             ["Thống kê tổng hợp Khoa", "Học kỳ", "Chỉ số của Khoa"],
         ]},
     ]},
    {"id": "ldk", "name": "Lãnh đạo Khoa", "role": "faculty_leader", "color": "#D97706", "letter": "LK",
     "desc": "Trưởng / Phó khoa: giám sát, duyệt đơn xin phép và vắng có phép trong Khoa mình, không nhập liệu.",
     "groups": [
         {"menu": "Giám sát\nđiểm danh", "readonly": True, "rows": [
             ["Xem phiên và kết quả các lớp Khoa", "Lớp, phiên", "Danh sách SV, trạng thái, ảnh bằng chứng"],
             ["Cảnh báo vắng, xuất Excel", "Lớp, học kỳ", "SV vắng ≥ 20%, tệp .xlsx"],
         ]},
         {"menu": "Phê duyệt", "rows": [
             ["Duyệt có phép", "Mã bản ghi (SV hoặc lớp thuộc Khoa), lý do", "Vắng → có phép + lịch sử sửa"],
             ["Hủy duyệt có phép", "Mã bản ghi, lý do", "Có phép → vắng + lịch sử sửa"],
             ["Xem lịch sử sửa", "Mã bản ghi", "Trạng thái cũ / mới, người sửa, lý do, thời điểm"],
         ]},
         {"menu": "Thống kê\n& nhật ký", "readonly": True, "rows": [
             ["Thống kê tổng hợp Khoa", "Học kỳ", "Chỉ số của Khoa"],
             ["Nhật ký thao tác của Khoa", "Bộ lọc nhật ký", "Nhật ký có faculty_id là Khoa mình"],
         ]},
     ]},
    {"id": "bn", "name": "Ban ngành", "role": "board", "color": "#475569", "letter": "BN",
     "desc": "Ban ngành khác trong trường (VD Thanh tra): chỉ xem số liệu tổng hợp, không có tên, ảnh sinh viên.",
     "groups": [
         {"menu": "Thống kê\ntổng hợp", "readonly": True, "rows": [
             ["Chọn học kỳ", "Học kỳ (mặc định mới nhất)", "Danh sách học kỳ có lớp"],
             ["Xem chỉ số toàn trường", "Học kỳ", "Số lớp, SV, GV, phiên; tỉ lệ đi học, tỉ lệ vắng; số SV bị cảnh báo"],
             ["So sánh theo Khoa", "Học kỳ", "Bảng chỉ số từng Khoa"],
         ]},
     ]},
    {"id": "gv", "name": "Giảng viên", "role": "lecturer", "color": "#7C3AED", "letter": "GV",
     "desc": "Điểm danh lớp mình dạy: mở phiên, quét camera, xác nhận tay, sửa kết quả, duyệt đơn xin phép, xem báo cáo lớp.",
     "groups": [
         {"menu": "Lịch dạy", "rows": [
             ["Lịch dạy hôm nay", "Tài khoản giảng viên", "Buổi dạy, giờ được mở phiên, phiên đang có"],
             ["Lịch tuần", "Tuần cần xem", "Các buổi kèm trạng thái phiên, số SV có mặt"],
             ["In lịch ra PDF", "Tuần đang xem", "Tệp PDF lịch dạy"],
         ]},
         {"menu": "Phiên\nđiểm danh", "rows": [
             ["Mở phiên", "Lịch học, ngày", "Phiên đang mở; ngoài khung giờ thì từ chối"],
             ["Đóng phiên", "Mã phiên", "SV chưa có bản ghi bị ghi vắng; SV vừa vượt ngưỡng cảnh báo"],
         ]},
         {"menu": "Ghi nhận\nđiểm danh", "rows": [
             ["Quét camera cả lớp", "Mã phiên, khung hình", "Mỗi mặt: MSSV, độ tin cậy, khung bao, kết quả"],
             ["Xác nhận tay", "Mã phiên, mã SV", "Bản ghi trạng thái manual"],
             ["Danh sách lớp trong phiên", "Mã phiên", "Trạng thái, giờ, ảnh, nguồn, khoảng cách từng SV"],
         ]},
         {"menu": "Hiệu chỉnh\n& báo cáo", "rows": [
             ["Sửa trạng thái điểm danh", "Mã bản ghi, trạng thái mới, lý do", "Bản ghi đã sửa + lịch sử sửa"],
             ["Thống kê, cảnh báo vắng lớp", "Mã lớp", "Tỉ lệ vắng, cờ cảnh báo từng SV"],
             ["Xuất Excel", "Mã lớp, học kỳ", "Tệp .xlsx bảng điểm danh"],
             ["Đăng ký khuôn mặt hộ SV lớp mình", "Mã SV, ảnh", "Vector chờ duyệt"],
         ]},
     ]},
    {"id": "sv", "name": "Sinh viên", "role": "student", "color": "#0E9594", "letter": "SV",
     "desc": "Tự điểm danh bằng khuôn mặt và GPS; nộp đơn xin phép; nhận và xác nhận kết quả duyệt; xem chuyên cần, cảnh báo.",
     "groups": [
         {"menu": "Tài khoản\n(mọi vai trò)", "rows": [
             ["Đăng nhập", "Email, mật khẩu", "Access token, refresh token, vai trò"],
             ["Quên / đặt lại mật khẩu", "Email; OTP, mật khẩu mới", "OTP qua email; mật khẩu được đổi"],
             ["Đổi mật khẩu", "Mật khẩu hiện tại, mật khẩu mới", "Token mới cho phiên đang dùng"],
             ["Đăng xuất", "Access token, refresh token", "Hai token bị thu hồi"],
         ]},
         {"menu": "Lịch học", "rows": [
             ["Lịch tuần", "Tuần cần xem", "Buổi học: phòng, giờ, trạng thái phiên, điểm danh của mình"],
             ["In lịch ra PDF", "Tuần đang xem", "Tệp PDF"],
         ]},
         {"menu": "Dữ liệu\nkhuôn mặt", "rows": [
             ["Đọc và đồng ý sinh trắc", "Nội dung có phiên bản, xác nhận", "Trạng thái đã đồng ý"],
             ["Đăng ký khuôn mặt", "Một hoặc nhiều ảnh", "Kết quả từng ảnh, số vector chờ duyệt"],
             ["Xem trạng thái dữ liệu", "Tài khoản SV", "Danh sách vector: trạng thái, lý do từ chối"],
             ["Xóa dữ liệu / rút đồng ý", "Xác nhận", "Toàn bộ vector và ảnh bị xóa"],
         ]},
         {"menu": "Tự\nđiểm danh", "rows": [
             ["Xem phòng học của buổi", "Mã phiên", "Tên phòng"],
             ["Chụp ảnh + gửi vị trí", "Ảnh, vĩ độ, kinh độ, sai số GPS, cờ giả lập", "present / late hoặc lý do từ chối, khoảng cách"],
         ]},
         {"menu": "Chuyên cần", "rows": [
             ["Xem chuyên cần theo học kỳ", "Học kỳ", "Theo lớp: số buổi từng trạng thái, tỉ lệ vắng, chi tiết từng buổi"],
             ["Nhận cảnh báo vắng", "—", "Cờ cảnh báo khi vắng ≥ 20%"],
         ]},
     ]},
    {"id": "ph", "name": "Phụ huynh", "role": "parent", "color": "#DB2777", "letter": "PH",
     "desc": "Theo dõi chuyên cần và nhận thông báo điểm danh của con đã được P. CTSV liên kết.",
     "groups": [
         {"menu": "Con của tôi", "rows": [
             ["Danh sách con", "Tài khoản phụ huynh", "Các con đã liên kết và lớp đang học"],
             ["Chuyên cần của con", "Mã SV, học kỳ", "Theo lớp, chi tiết từng buổi kèm ảnh, giờ, vị trí"],
         ]},
         {"menu": "Thông báo", "rows": [
             ["Hộp thư thông báo", "Chỉ chưa đọc (tùy chọn)", "Danh sách: tiêu đề, nội dung, thời điểm"],
             ["Số thông báo chưa đọc", "—", "Số trên chuông"],
             ["Đánh dấu đã đọc / đọc tất cả", "Mã thông báo", "Thông báo đã đọc"],
         ]},
         {"menu": "Tùy chọn", "rows": [
             ["Nhận email thông báo", "Bật / tắt", "Tùy chọn đã lưu"],
             ["Nhận tin \"có mặt\"", "Bật / tắt", "Tùy chọn đã lưu (muộn, vắng luôn được báo)"],
         ]},
     ]},
]

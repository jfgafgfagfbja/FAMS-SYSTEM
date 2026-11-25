"""Danh muc chuc nang FAMS + bo sinh docs/FEATURE_INVENTORY.md.

Moi chuc nang: (ma, ten, tac nhan, tham chieu, man hinh client, bang chung test).
  - tham chieu "GET /auth/me"   : chuc nang la mot endpoint; trang thai tu dong suy ra tu
                                  danh sach route cua server va do phu test (route_coverage).
  - tham chieu "noi bo: ..."    : quy tac/xu ly ben trong mot endpoint hoac service.
  - tham chieu "nen: ..."       : tac vu nen cua server.
  - tham chieu "client: ..."    : chuc nang chi o phia client (Flutter).
Bang chung test: danh sach node pytest "file.py::ten_test" (doi chieu ket qua JUnit XML) hoac
"flutter:<file>_test.dart" (doi chieu ket qua flutter test --machine), hoac "e2e:<mo ta>" (kiem
tra tich hop thu cong/tu dong ghi trong docs/TEST_REPORT.md).

Chay (tu thu muc goc FAMS-SYSTEM):
  python docs/tools/feature_inventory.py --coverage server/route_coverage.json \
      --junit server/junit.xml --flutter client/flutter_results.json --prefix /api/v1
"""
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

# ----------------------------------------------------------------------------- du lieu
# (ma, ten, tac nhan, tham chieu, man hinh, [bang chung], ghi chu thay doi so voi ban goc)
# Chuc nang da bo theo gop y nghiep vu 11/2026 (giu ma cu de doi chieu, khong dung lai ma).
REMOVED = [
    ("6.04", "Bật/tắt yêu cầu quét QR", "Bỏ hẳn mã QR khi SV tự điểm danh (ảnh khuôn mặt + GPS là đủ)"),
    ("6.10", "Chiếu mã QR luân phiên 30 s", "Bỏ hẳn mã QR"),
    ("6.11", "Quét mã QR / nhập 6 chữ số", "Bỏ hẳn mã QR"),
]

PHAN_HE = [
 ("PH1", "Xác thực và tài khoản", [
  ("1.01", "Đăng nhập email + mật khẩu", "Mọi người dùng", "POST /auth/login", "Đăng nhập", [], ""),
  ("1.02", "Khóa tạm sau 5 lần sai/5 phút, giới hạn 30 lần/phút/IP", "Hệ thống", "nội bộ: /auth/login",
   "Đăng nhập", ["test_auth.py::test_login_rate_limited_after_five_attempts"], ""),
  ("1.03", "Làm mới token xoay vòng, dùng lại token cũ ⇒ thu hồi tất cả", "App", "POST /auth/refresh",
   "(interceptor ApiClient)", ["test_tokens_and_media.py::test_refresh_rotates_and_old_token_reuse_revokes_all"], ""),
  ("1.04", "Đổi mật khẩu (giữ phiên hiện tại, đăng xuất phiên khác)", "Mọi người dùng",
   "POST /auth/change-password", "Tài khoản", [], ""),
  ("1.05", "Gửi OTP quên mật khẩu", "Mọi người dùng", "POST /auth/forgot-password", "Quên mật khẩu", [], ""),
  ("1.06", "Đặt lại mật khẩu bằng OTP", "Mọi người dùng", "POST /auth/reset-password", "Đặt lại mật khẩu", [], ""),
  ("1.07", "Xem thông tin tài khoản + hồ sơ theo vai trò", "Mọi người dùng", "GET /auth/me", "Tài khoản, Trang chủ", [], ""),
  ("1.08", "Đăng xuất (thu hồi access + refresh token)", "Mọi người dùng", "POST /auth/logout", "Khung ứng dụng", [], ""),
  ("1.09", "Kiểm tra vai trò, phạm vi Khoa", "Hệ thống", "nội bộ: core/authz",
   "(mọi trang)", ["test_authorization.py", "test_unit_roles.py"], ""),
  ("1.10", "Ảnh bằng chứng qua URL ký HMAC, hết hạn 60 phút", "Hệ thống, cán bộ",
   "GET /evidence/{file_path:path}", "Ảnh bằng chứng", [], "Ảnh phục vụ ở /api/v1/evidence/..."),
  ("1.11", "Thu hồi token khi đổi/đặt lại mật khẩu (token_version)", "Hệ thống", "nội bộ: core/security",
   "", ["test_tokens_and_media.py::test_reset_password_revokes_refresh_tokens"], ""),
  ("1.12", "Kiểm tra sức khỏe dịch vụ", "Hệ thống, vận hành", "GET /", "", [], ""),
  ("1.13", "Kiểm tra sức khỏe kèm kết nối CSDL (đi qua nginx)", "Vận hành", "GET /health", "",
   ["test_infrastructure.py::test_versioned_health_checks_database"], "Mới (healthcheck qua /api/v1)"),
  ("1.14", "Định dạng lỗi thống nhất {detail, code} + X-Request-ID", "Mọi client", "nội bộ: core/exceptions",
   "(ApiClient đọc detail)", ["test_infrastructure.py"], "Mới: thêm trường code, header X-Request-ID"),
 ]),
 ("PH2", "Quản trị danh mục hệ thống", [
  ("2.01", "Xem danh sách đơn vị", "Cán bộ", "GET /units", "Đơn vị", [], ""),
  ("2.02", "Thêm đơn vị", "QTV", "POST /units", "Đơn vị", [], ""),
  ("2.03", "Sửa đơn vị (không đổi loại)", "QTV", "PATCH /units/{unit_id}", "Đơn vị", [], ""),
  ("2.04", "Xóa đơn vị (chặn khi còn dữ liệu)", "QTV", "DELETE /units/{unit_id}", "Đơn vị", [], ""),
  ("2.05", "Tra cứu cán bộ", "QTV", "GET /staff", "Cán bộ", [], ""),
  ("2.06", "Tạo tài khoản cán bộ, vai trò suy ra từ đơn vị", "QTV", "POST /staff", "Cán bộ", [], ""),
  ("2.07", "Sửa cán bộ", "QTV", "PATCH /staff/{staff_id}", "Cán bộ", [], ""),
  ("2.08", "Xóa cán bộ (chặn khi đã sửa điểm danh)", "QTV", "DELETE /staff/{staff_id}", "Cán bộ", [], ""),
  ("2.09", "Xem danh sách địa điểm", "Cán bộ, GV", "GET /locations", "Địa điểm", [], ""),
  ("2.10", "Thêm địa điểm (tối đa 1 mặc định)", "QTV, P.ĐT", "POST /locations", "Địa điểm", [], ""),
  ("2.11", "Sửa địa điểm", "QTV, P.ĐT", "PATCH /locations/{location_id}", "Địa điểm", [], ""),
  ("2.12", "Xóa địa điểm (chặn khi gắn lịch)", "QTV, P.ĐT", "DELETE /locations/{location_id}", "Địa điểm", [], ""),
  ("2.13", "Tra cứu phòng học", "Cán bộ, GV", "GET /rooms", "Phòng học", [], ""),
  ("2.14", "Danh sách tòa nhà", "Cán bộ, GV", "GET /rooms/buildings", "Phòng học", [], ""),
  ("2.15", "Thêm phòng học", "QTV, P.ĐT", "POST /rooms", "Phòng học", [], ""),
  ("2.16", "Sửa, ngừng sử dụng phòng", "QTV, P.ĐT", "PATCH /rooms/{room_id}", "Phòng học", [], ""),
  ("2.17", "Xóa phòng (chặn khi còn lịch)", "QTV, P.ĐT", "DELETE /rooms/{room_id}", "Phòng học", [], ""),
  ("2.18", "Lấy vị trí hiện tại khi nhập tọa độ", "QTV, P.ĐT", "client: geolocator",
   "Địa điểm, Phòng học", ["e2e:geolocator"], ""),
 ]),
 ("PH3", "Quản lý đào tạo", [
  ("3.01", "Tra cứu giảng viên", "QTV, P.ĐT, Khoa", "GET /lecturers", "Giảng viên", [], ""),
  ("3.02", "Thêm giảng viên", "QTV, P.ĐT", "POST /lecturers", "Giảng viên", [], ""),
  ("3.03", "Sửa giảng viên", "QTV, P.ĐT", "PATCH /lecturers/{lecturer_id}", "Giảng viên", [], ""),
  ("3.04", "Xóa giảng viên (chặn khi đang dạy/đã sửa điểm danh)", "QTV, P.ĐT",
   "DELETE /lecturers/{lecturer_id}", "Giảng viên", [], ""),
  ("3.05", "Tra cứu lớp học phần", "Cán bộ, GV", "GET /classes", "Lớp học phần", [], ""),
  ("3.06", "Xem chi tiết lớp", "Cán bộ, GV", "GET /classes/{class_id}", "Chi tiết lớp", [], ""),
  ("3.07", "Thêm lớp (VP Khoa: chỉ Khoa mình)", "QTV, P.ĐT, VP Khoa", "POST /classes", "Lớp học phần", [], ""),
  ("3.08", "Sửa lớp", "QTV, P.ĐT, VP Khoa", "PATCH /classes/{class_id}", "Chi tiết lớp", [], ""),
  ("3.09", "Xóa lớp (chặn khi có SV/lịch)", "QTV, P.ĐT, VP Khoa", "DELETE /classes/{class_id}", "Chi tiết lớp", [], ""),
  ("3.10", "Danh sách SV của lớp", "Cán bộ, GV", "GET /classes/{class_id}/students", "Chi tiết lớp", [], ""),
  ("3.11", "Ghi danh sinh viên", "QTV, P.ĐT", "POST /classes/{class_id}/enroll/{student_id}", "Chi tiết lớp", [], ""),
  ("3.12", "Rút sinh viên khỏi lớp", "QTV, P.ĐT", "DELETE /classes/{class_id}/enroll/{student_id}", "Chi tiết lớp", [], ""),
  ("3.13", "Lịch của một lớp", "Cán bộ, GV, SV", "GET /classes/{class_id}/schedules", "Chi tiết lớp", [], ""),
  ("3.14", "Tra cứu toàn bộ lịch", "Cán bộ", "GET /schedules", "Lịch học", [], ""),
  ("3.15", "Thêm lịch (chống trùng phòng)", "QTV, P.ĐT", "POST /classes/schedules", "Chi tiết lớp", [], ""),
  ("3.16", "Sửa lịch (chống trùng phòng)", "QTV, P.ĐT", "PATCH /classes/schedules/{schedule_id}", "Chi tiết lớp", [], ""),
  ("3.17", "Xóa lịch (chặn khi đã có phiên)", "QTV, P.ĐT", "DELETE /classes/schedules/{schedule_id}", "Chi tiết lớp",
   ["test_unit_roles.py::test_faculty_office_edits_only_own_faculty_classes"],
   "Góp ý 11/2026: Văn phòng Khoa không còn ghi danh, xếp lịch"),
  ("3.18", "Lịch theo tuần (kèm trạng thái phiên, điểm danh)", "SV, GV, cán bộ", "GET /schedules/week", "Lịch tuần", [], ""),
  ("3.19", "Lịch dạy hôm nay", "GV", "GET /lecturers/me/today-schedules", "Trang chủ GV", [], ""),
  ("3.20", "In lịch tuần ra PDF", "SV, GV", "client: schedule_pdf", "Lịch tuần",
   ["flutter:schedule_pdf_test.dart"], ""),
 ]),
 ("PH4", "Quản lý người học", [
  ("4.01", "Tra cứu sinh viên", "Cán bộ, GV", "GET /students", "Sinh viên", [], ""),
  ("4.02", "Xem chi tiết sinh viên", "Cán bộ, GV", "GET /students/{student_id}", "Chi tiết SV", [], ""),
  ("4.03", "Hồ sơ của chính SV", "SV", "GET /students/me", "Tài khoản", [], ""),
  ("4.04", "Thêm sinh viên", "QTV, P.CTSV", "POST /students", "Sinh viên", [], ""),
  ("4.05", "Sửa sinh viên", "QTV, P.CTSV", "PATCH /students/{student_id}", "Chi tiết SV", [], ""),
  ("4.06", "Xóa sinh viên (chặn khi có dữ liệu)", "QTV, P.CTSV", "DELETE /students/{student_id}", "Chi tiết SV", [], ""),
  ("4.07", "Nội dung đồng ý sinh trắc (có phiên bản)", "Mọi người dùng", "GET /students/consent-policy", "Khuôn mặt", [], ""),
  ("4.08", "Ghi nhận đồng ý (SV tự / cán bộ nhập bản giấy)", "SV, QTV, P.CTSV", "POST /students/{student_id}/consent",
   "Khuôn mặt, Chi tiết SV", [], ""),
  ("4.09", "Rút đồng ý (xóa toàn bộ dữ liệu khuôn mặt)", "SV, QTV, P.CTSV",
   "POST /students/{student_id}/consent/withdraw", "Khuôn mặt, Chi tiết SV", [], ""),
  ("4.10", "Xem danh sách phụ huynh", "QTV, P.CTSV, P.ĐT", "GET /parents", "Phụ huynh", [], ""),
  ("4.11", "Thêm phụ huynh", "QTV, P.CTSV", "POST /parents", "Phụ huynh", [], ""),
  ("4.12", "Sửa phụ huynh", "QTV, P.CTSV", "PATCH /parents/{parent_id}", "Phụ huynh", [], ""),
  ("4.13", "Xóa phụ huynh", "QTV, P.CTSV", "DELETE /parents/{parent_id}", "Phụ huynh", [], ""),
  ("4.14", "Xem con đã liên kết", "QTV, P.CTSV, P.ĐT", "GET /parents/{parent_id}/children", "Phụ huynh", [], ""),
  ("4.15", "Liên kết con bằng MSSV", "QTV, P.CTSV", "POST /parents/{parent_id}/children", "Phụ huynh", [], ""),
  ("4.16", "Gỡ liên kết con", "QTV, P.CTSV", "DELETE /parents/{parent_id}/children/{student_id}", "Phụ huynh", [], ""),
 ]),
 ("PH5", "Sinh trắc khuôn mặt", [
  ("5.01", "Đăng ký khuôn mặt (quyền, đồng ý, chất lượng, chống giả mạo, trùng)", "SV, P.CTSV, QTV, GV",
   "POST /faces/enroll/{student_id}", "Khuôn mặt, Đăng ký hộ", [], ""),
  ("5.02", "Danh sách chờ duyệt kèm cảnh báo trùng", "P.CTSV", "GET /faces/pending", "Duyệt khuôn mặt", [], ""),
  ("5.03", "Duyệt khuôn mặt (chỉ ảnh đang chờ, xóa ảnh tạm)", "P.CTSV", "PATCH /faces/{embedding_id}/approve",
   "Duyệt khuôn mặt", ["test_face_approval.py::test_admin_no_longer_reviews_faces"],
   "Góp ý 11/2026: bỏ quản trị viên khỏi xét duyệt; ghi người duyệt, thời điểm"),
  ("5.04", "Từ chối khuôn mặt kèm lý do không hợp lệ (xóa ảnh tạm)", "P.CTSV", "PATCH /faces/{embedding_id}/reject",
   "Duyệt khuôn mặt", [], "Góp ý 11/2026: chỉ P.CTSV"),
  ("5.05", "SV xem dữ liệu khuôn mặt của mình", "SV", "GET /faces/mine", "Khuôn mặt", [], ""),
  ("5.06", "SV xóa dữ liệu khuôn mặt", "SV", "DELETE /faces/mine", "Khuôn mặt", [], ""),
  ("5.09", "Phản hồi kết quả duyệt khuôn mặt cho SV (thông báo)", "Hệ thống", "nội bộ: face_data_service._decide",
   "Thông báo", ["test_face_approval.py::test_result_is_sent_to_student_and_student_confirms"], "Mới (góp ý 11/2026)"),
  ("5.10", "SV xác nhận đã nhận kết quả duyệt khuôn mặt", "SV", "POST /faces/mine/{embedding_id}/acknowledge",
   "Khuôn mặt", [], "Mới (góp ý 11/2026)"),
  ("5.07", "Chụp ảnh bằng camera (web/di động)", "SV, GV, cán bộ", "client: camera_capture",
   "Khuôn mặt, Quét lớp, Tự điểm danh", ["flutter:camera_lifecycle_test.dart"], ""),
  ("5.08", "Chống giả mạo MiniFASNet (tự tắt khi thiếu model)", "Hệ thống", "nội bộ: antispoof_service", "",
   ["test_antispoof.py"], ""),
 ]),
 ("PH6", "Điểm danh", [
  ("6.01", "Mở phiên (khung giờ, mỗi lịch 1 phiên/ngày)", "GV, QTV", "POST /sessions", "Lịch dạy, Phiên", [], ""),
  ("6.02", "Tra cứu phiên", "Cán bộ, GV", "GET /sessions", "Phiên điểm danh", [], ""),
  ("6.03", "Xem chi tiết phiên", "Cán bộ, GV", "GET /sessions/{session_id}", "Kết quả phiên", [], ""),
  ("6.05", "Đóng phiên: sinh vắng / vắng có phép theo đơn, thống kê lại, cảnh báo SV vừa vượt ngưỡng", "GV, QTV",
   "PATCH /sessions/{session_id}/close", "Kết quả phiên", [], "Góp ý 11/2026: cảnh báo sau thống kê, đơn xin phép"),
  ("6.06", "Tự đóng phiên quá hạn (60 s/lần)", "Hệ thống", "nền: run_auto_close_loop", "",
   ["test_flow_fixes.py::test_auto_close_expired_sessions_marks_absent",
    "test_flow_fixes.py::test_auto_close_keeps_sessions_within_deadline"], ""),
  ("6.07", "Quét camera cả lớp, nhận diện nhiều mặt", "GV, QTV", "POST /sessions/{session_id}/recognize", "Quét lớp", [], ""),
  ("6.08", "Xác nhận 2 khung hình trước khi ghi", "Hệ thống", "nội bộ: /recognize", "Quét lớp",
   ["test_confirm_frames.py"], ""),
  ("6.09", "SV xem phòng học của buổi trước khi tự điểm danh", "SV", "GET /sessions/{session_id}/checkin-info",
   "Tự điểm danh", [], "Góp ý 11/2026: bỏ mã QR"),
  ("6.12", "Đối chiếu GPS (giả lập, sai số, bán kính)", "Hệ thống", "nội bộ: geo_service", "Tự điểm danh",
   ["test_location_checkin.py"], ""),
  ("6.13", "SV tự điểm danh bằng ảnh + GPS", "SV", "POST /sessions/{session_id}/self-checkin", "Tự điểm danh", [],
   "Góp ý 11/2026: bỏ mã QR"),
  ("6.14", "Xác nhận tay", "GV, QTV", "POST /sessions/{session_id}/manual", "Kết quả phiên", [], ""),
  ("6.15", "Danh sách lớp trong phiên (roster)", "Cán bộ, GV", "GET /sessions/{session_id}/roster", "Kết quả phiên", [], ""),
  ("6.16", "Danh sách bản ghi của phiên", "Cán bộ, GV", "GET /sessions/{session_id}/records", "Kết quả phiên", [], ""),
  ("6.17", "Sửa trạng thái / duyệt có phép (bắt buộc lý do)", "GV, QTV, P.CTSV, LĐ Khoa",
   "PATCH /sessions/{session_id}/records/{record_id}", "Kết quả phiên", [], ""),
  ("6.18", "Xem lịch sử sửa điểm danh", "Cán bộ, GV", "GET /sessions/{session_id}/records/{record_id}/audits",
   "Kết quả phiên", [], ""),
  ("6.19", "SV nộp đơn xin phép vắng một buổi học", "SV", "POST /leave-requests", "Đơn xin phép",
   ["test_leave_and_warnings.py::test_leave_validation_rules"], "Mới (góp ý 11/2026)"),
  ("6.20", "Xem đơn xin phép theo phạm vi", "SV, GV, LĐ Khoa, QTV, P.CTSV", "GET /leave-requests", "Đơn xin phép", [],
   "Mới (góp ý 11/2026)"),
  ("6.21", "Duyệt đơn xin phép (GV lớp / Lãnh đạo Khoa)", "GV, LĐ Khoa", "PATCH /leave-requests/{leave_id}/approve",
   "Đơn xin phép", ["test_leave_and_warnings.py::test_only_class_lecturer_or_faculty_leader_reviews"], "Mới (góp ý 11/2026)"),
  ("6.22", "Từ chối đơn kèm lý do không hợp lệ", "GV, LĐ Khoa", "PATCH /leave-requests/{leave_id}/reject", "Đơn xin phép",
   [], "Mới (góp ý 11/2026)"),
  ("6.23", "Phản hồi kết quả duyệt đơn cho SV (thông báo)", "Hệ thống", "nội bộ: leave_service.approve/reject",
   "Thông báo", ["test_leave_and_warnings.py::test_reject_requires_invalid_reason_and_student_confirms"],
   "Mới (góp ý 11/2026)"),
  ("6.24", "SV xác nhận đã nhận kết quả duyệt đơn", "SV", "POST /leave-requests/{leave_id}/acknowledge",
   "Đơn xin phép", [], "Mới (góp ý 11/2026)"),
  ("6.25", "Đơn đã duyệt ⇒ vắng có phép (khi đóng phiên hoặc đổi bản ghi vắng)", "Hệ thống",
   "nội bộ: leave_service._apply_excused", "",
   ["test_leave_and_warnings.py::test_approved_leave_makes_absence_excused_when_session_closes",
    "test_leave_and_warnings.py::test_leave_approved_after_close_turns_absent_into_excused"], "Mới (góp ý 11/2026)"),
 ]),
 ("PH7", "Thông báo", [
  ("7.01", "Sinh thông báo phụ huynh khi điểm danh/đổi trạng thái", "Hệ thống", "nội bộ: parent_notify", "",
   ["test_parent_notifications.py::test_checkin_notifies_parent",
    "test_parent_notifications.py::test_status_correction_sends_update",
    "test_parent_notifications.py::test_flipping_back_does_not_duplicate"], ""),
  ("7.02", "Xem hộp thư thông báo", "PH, SV, GV", "GET /notifications", "Thông báo", [], ""),
  ("7.03", "Đếm chưa đọc (chuông)", "PH, SV", "GET /notifications/unread-count", "Chuông thông báo", [], ""),
  ("7.04", "Đánh dấu đã đọc", "PH, SV, GV", "POST /notifications/{notification_id}/read", "Thông báo", [], ""),
  ("7.05", "Đánh dấu đọc tất cả", "PH, SV, GV", "POST /notifications/read-all", "Thông báo", [], ""),
  ("7.06", "Gửi email theo hàng đợi, thử lại tối đa 3 lần", "Hệ thống", "nền: run_notification_email_loop", "",
   ["test_parent_notifications.py::test_pending_email_is_sent",
    "test_parent_notifications.py::test_failed_email_retried_then_given_up",
    "test_parent_notifications.py::test_smtp_down_does_not_lose_mail"], ""),
  ("7.07", "Xem tùy chọn nhận thông báo", "PH", "GET /parents/me/preferences", "Tài khoản", [], ""),
  ("7.08", "Cập nhật tùy chọn nhận thông báo", "PH", "PATCH /parents/me/preferences", "Tài khoản", [], ""),
  ("7.09", "Thông báo cho SV / GV: kết quả duyệt, đơn xin phép mới, cảnh báo", "Hệ thống", "nội bộ: user_notify",
   "Thông báo", ["test_leave_and_warnings.py::test_student_submits_leave_and_lecturer_is_notified"], "Mới (góp ý 11/2026)"),
 ]),
 ("PH8", "Báo cáo, thống kê", [
  ("8.01", "SV xem chuyên cần chi tiết theo học kỳ", "SV", "GET /students/me/attendance", "Chuyên cần", [], ""),
  ("8.02", "SV xem tóm tắt chuyên cần", "SV", "GET /reports/my-attendance", "Chuyên cần", [], ""),
  ("8.03", "Cán bộ xem chuyên cần một SV", "Cán bộ", "GET /students/{student_id}/attendance", "Chi tiết SV", [], ""),
  ("8.04", "Thống kê chuyên cần theo lớp", "Cán bộ, GV", "GET /reports/attendance/{class_id}", "Báo cáo", [], ""),
  ("8.05", "Xem danh sách cảnh báo vắng ≥ 20 % (sau thống kê lớp)", "Cán bộ, GV", "GET /reports/attendance/warnings",
   "Báo cáo", [], ""),
  ("8.11", "Gửi cảnh báo chuyên cần sau thống kê cho SV và phụ huynh", "Hệ thống",
   "nội bộ: user_notify.notify_absence_warnings", "Thông báo",
   ["test_leave_and_warnings.py::test_absence_warning_after_statistics"], "Mới (góp ý 11/2026)"),
  ("8.06", "Xuất Excel bảng điểm danh", "Cán bộ, GV", "GET /reports/attendance/export", "Báo cáo", [], ""),
  ("8.07", "Danh sách con của phụ huynh", "PH", "GET /parents/me/children", "Con của tôi", [], ""),
  ("8.08", "Chuyên cần của con", "PH", "GET /parents/me/children/{student_id}/attendance", "Chuyên cần của con", [], ""),
  ("8.09", "Thống kê tổng hợp, so sánh theo Khoa", "QTV, P.ĐT, P.CTSV, Khoa, Ban ngành", "GET /reports/overview",
   "Tổng quan", [], ""),
  ("8.10", "Biểu đồ chuyên cần", "Mọi vai trò xem báo cáo", "client: fl_chart", "Tổng quan, Chuyên cần",
   ["flutter:feedback_pages_test.dart"], ""),
 ]),
 ("PH9", "Nhật ký hệ thống", [
  ("9.01", "Ghi vết sửa điểm danh (attendance_audits)", "Hệ thống", "nội bộ: PATCH records",
   "", ["test_session_detail_and_records.py"], ""),
  ("9.02", "Ghi đăng nhập, đăng nhập sai, khóa, đăng xuất", "Hệ thống", "nội bộ: services/audit", "",
   ["test_audit_log.py::test_login_success_is_logged", "test_audit_log.py::test_failed_login_logged_without_password",
    "test_audit_log.py::test_logout_is_logged"], ""),
  ("9.03", "Ghi tự động mọi thêm/sửa/xóa dữ liệu quản lý", "Hệ thống", "nội bộ: services/audit", "",
   ["test_audit_log.py::test_create_is_logged_with_actor", "test_audit_log.py::test_update_records_old_and_new_values",
    "test_audit_log.py::test_password_change_never_stores_the_hash"], ""),
  ("9.04", "Ghi xuất báo cáo", "Hệ thống", "nội bộ: services/audit", "",
   ["test_audit_log.py::test_report_export_is_logged"], ""),
  ("9.05", "Tra cứu, lọc nhật ký (LĐ Khoa chỉ Khoa mình)", "QTV, LĐ Khoa", "GET /audit-logs", "Nhật ký hệ thống", [], ""),
  ("9.06", "Dọn ảnh bằng chứng quá 90 ngày", "Hệ thống", "nền: run_cleanup_loop", "",
   ["test_evidence_cleanup.py"], ""),
  ("9.07", "Nhật ký ứng dụng (log dịch vụ)", "Vận hành", "nội bộ: logging", "",
   ["test_infrastructure.py"], "Mới: log có request-id, định dạng thống nhất"),
 ]),
 ("PH10", "Giao diện chung (client)", [
  ("10.01", "Điều hướng theo vai trò, chặn route không có quyền", "Mọi người dùng", "client: router.dart",
   "(toàn ứng dụng)", ["flutter:access_test.dart"], ""),
  ("10.02", "Đăng nhập, nhập địa chỉ máy chủ", "Mọi người dùng", "client: login_page", "Đăng nhập",
   ["flutter:login_page_test.dart"], ""),
  ("10.03", "Đổi mật khẩu trên giao diện", "Mọi người dùng", "client: account_page", "Tài khoản",
   ["flutter:change_password_test.dart"], ""),
  ("10.04", "Thông báo phụ huynh trên giao diện", "PH", "client: notification_bell", "Thông báo",
   ["flutter:parent_notifications_test.dart"], ""),
  ("10.05", "Đọc dữ liệu API (models)", "—", "client: models.dart", "", ["flutter:models_test.dart"], ""),
  ("10.06", "Định dạng ngày, phần trăm, trạng thái", "—", "client: formatters.dart", "",
   ["flutter:formatters_test.dart"], ""),
  ("10.07", "Giao diện sáng/tối", "Mọi người dùng", "client: theme", "Tài khoản", ["e2e:theme"], ""),
 ]),
]

# ----------------------------------------------------------------------------- sinh tai lieu
METHOD_RE = re.compile(r"^(GET|POST|PATCH|PUT|DELETE) (/\S*)$")


def _load_junit(path: Path | None) -> dict[str, str]:
    """{"file.py::ten_test": "passed"|"failed"|"skipped"} tu file JUnit XML cua pytest."""
    if not path or not path.exists():
        return {}
    result = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        file = case.get("classname", "").split(".")[-1] + ".py"
        status = "passed"
        if case.find("failure") is not None or case.find("error") is not None:
            status = "failed"
        elif case.find("skipped") is not None:
            status = "skipped"
        result[f"{file}::{case.get('name')}"] = status
    return result


def _load_flutter(path: Path | None) -> dict[str, str]:
    """{"ten_test.dart": "passed"|"failed"} tu file json (xem client/tool/flutter_results.py)."""
    if not path or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _evidence_status(evidence: list[str], junit: dict, flutter: dict, e2e: dict) -> tuple[bool | None, str]:
    """(dat?, mo ta). None = chua co ket qua de doi chieu."""
    if not evidence:
        return None, ""
    notes, ok = [], True
    for ev in evidence:
        if ev.startswith("flutter:"):
            st = flutter.get(ev[len("flutter:"):])
        elif ev.startswith("e2e:"):
            st = e2e.get(ev[len("e2e:"):])
        elif "::" in ev:
            st = junit.get(ev)
        else:  # ca file pytest
            sts = [v for k, v in junit.items() if k.startswith(ev + "::")]
            st = None if not sts else ("failed" if "failed" in sts else "passed")
        if st is None:
            return None, f"chưa có kết quả cho `{ev}`"
        if st != "passed":
            ok = False
            notes.append(f"`{ev}` {st}")
    return ok, "; ".join(notes)


def build(coverage: dict | None, junit: dict, flutter: dict, e2e: dict, prefix: str) -> str:
    routes = set(coverage["routes"]) if coverage else set()
    hits = coverage["hits"] if coverage else {}
    lines = []
    total = {"ok": 0, "partial": 0, "todo": 0}

    def api_key(ref: str) -> str | None:
        m = METHOD_RE.match(ref)
        if not m:
            return None
        method, path = m.groups()
        # "GET /" la kiem tra suc khoe o goc, nam ngoai tien to phien ban.
        return f"{method} {path if path == '/' else prefix + path}"

    mapped = {api_key(f[3]) for _, _, features in PHAN_HE for f in features} - {None}
    unmapped = sorted(r for r in routes if r not in mapped)

    for code, title, features in PHAN_HE:
        lines += [f"## {code}. {title}", "",
                  "| Mã | Chức năng | Tác nhân | API / nơi xử lý | Màn hình | Chuyển đổi | Kiểm thử | Trạng thái |",
                  "|---|---|---|---|---|---|---|---|"]
        for (fid, name, actor, ref, screen, evidence, change) in features:
            key = api_key(ref)
            if key is not None:
                converted = key in routes if coverage else None
                statuses = hits.get(key)
                tested_ok = bool(statuses) and any(s < 500 for s in statuses)
                test_txt = ("HTTP " + ", ".join(str(s) for s in statuses)) if statuses else "chưa có test"
                ev_ok, ev_note = _evidence_status(evidence, junit, flutter, e2e)
                if ev_ok is False:
                    tested_ok = False
                ref_txt = f"`{key}`"
            else:
                converted = True if (ref.startswith("client:") or ref.startswith("nội bộ") or ref.startswith("nền")) else None
                ev_ok, ev_note = _evidence_status(evidence, junit, flutter, e2e)
                tested_ok = bool(ev_ok)
                test_txt = ", ".join(f"`{e}`" for e in evidence) if evidence else "—"
                if ev_note:
                    test_txt += f" ({ev_note})"
                ref_txt = ref.replace("client: ", "client `").rstrip() + ("`" if ref.startswith("client:") else "")

            if converted is None:
                conv_txt, state = "⏳", "Chưa đánh giá"
                total["todo"] += 1
            elif not converted:
                conv_txt, state = "❌", "**Chưa hoàn thành**"
                total["todo"] += 1
            elif tested_ok:
                conv_txt, state = "✅", "Hoạt động bình thường"
                total["ok"] += 1
            else:
                conv_txt, state = "✅", "Đã chuyển đổi, **chưa kiểm thử**"
                total["partial"] += 1
            if change:
                state += f" · Thay đổi: {change}"
            test_mark = "✅ " if tested_ok else "⚠️ "
            lines.append(f"| {fid} | {name} | {actor} | {ref_txt} | {screen or '—'} | {conv_txt} | "
                         f"{test_mark}{test_txt} | {state} |")
        lines.append("")

    if coverage:
        lines += ["## Đối chiếu route ↔ danh mục", ""]
        if unmapped:
            lines.append("Route có trên server nhưng **chưa có trong danh mục** (phải bổ sung):")
            lines += [f"- `{r}`" for r in unmapped]
        else:
            lines.append(f"Mọi route của server ({len(routes)}) đều đã có trong danh mục.")
        lines.append("")

    lines += ["## Chức năng đã bỏ theo góp ý nghiệp vụ (11/2026)", "",
              "| Mã cũ | Chức năng | Lý do |", "|---|---|---|"]
    lines += [f"| {fid} | {name} | {why} |" for fid, name, why in REMOVED]
    lines.append("")

    n = sum(total.values())
    header = [
        "# Danh mục chức năng FAMS (FEATURE_INVENTORY)",
        "",
        "> **Tệp sinh tự động** từ `docs/tools/feature_inventory.py` — sửa dữ liệu ở đó rồi chạy lại,",
        "> không sửa tay tệp này. Trạng thái lấy từ: danh sách route thực tế của server, độ phủ route khi",
        "> chạy toàn bộ test (`server/tools/route_coverage_plugin.py`), kết quả pytest (JUnit XML),",
        "> kết quả `flutter test` và kiểm thử tích hợp ghi trong `docs/TEST_REPORT.md`.",
        "",
        f"- Tiền tố API của phiên bản này: `{prefix or '(không có)'}` — đường dẫn tài nguyên giữ nguyên như bản gốc.",
        f"- Tổng: **{n}** chức năng — ✅ hoạt động bình thường: **{total['ok']}**, "
        f"đã chuyển đổi nhưng chưa kiểm thử: **{total['partial']}**, chưa hoàn thành/chưa đánh giá: **{total['todo']}**.",
        "- Cột *Kiểm thử* với API: các mã HTTP mà bộ test đã thực sự nhận được từ endpoint (cả nhánh thành công",
        "  lẫn nhánh bị từ chối). Với chức năng nội bộ/client: tên test làm bằng chứng.",
        "",
    ]
    return "\n".join(header + lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--coverage", type=Path)
    p.add_argument("--junit", type=Path)
    p.add_argument("--flutter", type=Path)
    p.add_argument("--e2e", type=Path, help='json {"ten": "passed"} cho bang chung e2e:')
    p.add_argument("--prefix", default="/api/v1")
    p.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "FEATURE_INVENTORY.md")
    a = p.parse_args()
    coverage = json.loads(a.coverage.read_text(encoding="utf-8")) if a.coverage and a.coverage.exists() else None
    e2e = json.loads(a.e2e.read_text(encoding="utf-8")) if a.e2e and a.e2e.exists() else {}
    text = build(coverage, _load_junit(a.junit), _load_flutter(a.flutter), e2e, a.prefix)
    a.out.write_text(text + "\n", encoding="utf-8")
    print(f"Da ghi {a.out}")


if __name__ == "__main__":
    main()

# Danh sach endpoint (sinh tu dong)

> Sinh boi `scripts/export_openapi.py` tu server phien ban 2.0.0. Dac ta day du: [openapi.json](openapi.json) (mo bang Swagger Editor) hoac `/docs` khi server chay.

Tong: **102** endpoint.

## health

Kiem tra suc khoe dich vu

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/` | — |  | Root |
| GET | `/api/v1/health` | — |  | Health |

## auth

PH1 - Dang nhap, token, mat khau, thong tin tai khoan

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| POST | `/api/v1/auth/change-password` | Bearer | JSON | Doi mat khau (phai dung mat khau hien tai); cap token moi cho phien hien tai. |
| POST | `/api/v1/auth/forgot-password` | — | JSON | Gui ma OTP qua email; luon tra thong bao chung (khong lo email ton tai hay khong). |
| POST | `/api/v1/auth/login` | — | form | Form `username` (email), `password`. Tra access token + refresh token + vai tro. |
| POST | `/api/v1/auth/logout` | Bearer | JSON | Logout |
| GET | `/api/v1/auth/me` | Bearer |  | Thong tin tai khoan dang dang nhap kem ho so theo vai tro. |
| POST | `/api/v1/auth/refresh` | — | JSON | Doi refresh token lay cap token moi (token cu bi thu hoi - xoay vong). |
| POST | `/api/v1/auth/reset-password` | — | JSON | Dat lai mat khau bang OTP; moi token cu mat hieu luc. |

## units

PH2 - Don vi (Khoa, phong, ban)

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/units` | Bearer | `type` | List Units |
| POST | `/api/v1/units` | Bearer | JSON | Create Unit |
| PATCH | `/api/v1/units/{unit_id}` | Bearer | JSON | Update Unit |
| DELETE | `/api/v1/units/{unit_id}` | Bearer |  | Delete Unit |

## staff

PH2 - Tai khoan can bo

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/staff` | Bearer | `q`, `unit_id`, `limit`, `offset` | List Staff |
| POST | `/api/v1/staff` | Bearer | JSON | Create Staff |
| PATCH | `/api/v1/staff/{staff_id}` | Bearer | JSON | Update Staff |
| DELETE | `/api/v1/staff/{staff_id}` | Bearer |  | Delete Staff |

## locations

PH2 - Dia diem diem danh (toa do, ban kinh)

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/locations` | Bearer |  | List Locations |
| POST | `/api/v1/locations` | Bearer | JSON | Create Location |
| PATCH | `/api/v1/locations/{location_id}` | Bearer | JSON | Update Location |
| DELETE | `/api/v1/locations/{location_id}` | Bearer |  | Delete Location |

## rooms

PH2 - Phong hoc

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/rooms` | Bearer | `location_id`, `building`, `q`, `only_active` | List Rooms |
| POST | `/api/v1/rooms` | Bearer | JSON | Create Room |
| GET | `/api/v1/rooms/buildings` | Bearer |  | Danh sach toa nha dang co - de loc nhanh o man quan ly va o chon phong. |
| PATCH | `/api/v1/rooms/{room_id}` | Bearer | JSON | Update Room |
| DELETE | `/api/v1/rooms/{room_id}` | Bearer |  | Delete Room |

## lecturers

PH3 - Giang vien, lich day hom nay

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/lecturers` | Bearer | `q`, `faculty_id`, `limit`, `offset` | q loc theo ma GV/ho ten, limit/offset phan trang - khong truyen limit thi tra ve toan |
| POST | `/api/v1/lecturers` | Bearer | JSON | Create Lecturer |
| GET | `/api/v1/lecturers/me/today-schedules` | Bearer |  | Lich day hom nay cua giang vien dang dang nhap, kem phien da mo hom nay (neu co). |
| PATCH | `/api/v1/lecturers/{lecturer_id}` | Bearer | JSON | Update Lecturer |
| DELETE | `/api/v1/lecturers/{lecturer_id}` | Bearer |  | Delete Lecturer |

## classes

PH3 - Lop hoc phan, ghi danh, lich hoc cua lop

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/classes` | Bearer | `mine`, `q`, `semester`, `faculty_id`, `limit`, `offset` | Danh sach lop trong pham vi xem cua user: admin/P.DT/P.CTSV toan truong, Khoa chi |
| POST | `/api/v1/classes` | Bearer | JSON | Create Class |
| POST | `/api/v1/classes/schedules` | Bearer | JSON | Create Schedule |
| PATCH | `/api/v1/classes/schedules/{schedule_id}` | Bearer | JSON | Update Schedule |
| DELETE | `/api/v1/classes/schedules/{schedule_id}` | Bearer |  | Delete Schedule |
| GET | `/api/v1/classes/{class_id}` | Bearer |  | Get Class |
| PATCH | `/api/v1/classes/{class_id}` | Bearer | JSON | Update Class |
| DELETE | `/api/v1/classes/{class_id}` | Bearer |  | Delete Class |
| POST | `/api/v1/classes/{class_id}/enroll/{student_id}` | Bearer |  | Enroll Student |
| DELETE | `/api/v1/classes/{class_id}/enroll/{student_id}` | Bearer |  | Unenroll Student |
| GET | `/api/v1/classes/{class_id}/schedules` | Bearer |  | Lich hoc cua lop: nguoi xem duoc lop, hoac SV dang ghi danh lop do. |
| GET | `/api/v1/classes/{class_id}/students` | Bearer |  | List Class Students |

## schedules

PH3 - Tra cuu lich, lich tuan

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/schedules` | Bearer | `q`, `limit`, `offset` | Lich hoc kem thong tin lop trong pham vi xem - loc theo q (ma lop/ten mon/phong), |
| GET | `/api/v1/schedules/week` | Bearer | `start` | Lich hoc/day theo tuan (Thu 2 - CN) chua ngay `start` (mac dinh hom nay). |

## students

PH4 - Sinh vien, dong y sinh trac, chuyen can 1 SV

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/students` | Bearer | `q`, `faculty_id`, `limit`, `offset` | Danh sach SV trong pham vi xem cua user, loc theo q (MSSV hoac ho ten)/faculty_id va |
| POST | `/api/v1/students` | Bearer | JSON | Create Student |
| GET | `/api/v1/students/consent-policy` | Bearer |  | Consent Policy Text |
| GET | `/api/v1/students/me` | Bearer |  | Get My Student Record |
| GET | `/api/v1/students/me/attendance` | Bearer | `semester` | Get My Attendance |
| GET | `/api/v1/students/{student_id}` | Bearer |  | Get Student |
| PATCH | `/api/v1/students/{student_id}` | Bearer | JSON | Update Student |
| DELETE | `/api/v1/students/{student_id}` | Bearer |  | Delete Student |
| GET | `/api/v1/students/{student_id}/attendance` | Bearer | `semester` | Phong ban/Khoa xem chuyen can chi tiet 1 SV (vd de duyet don xin phep). |
| POST | `/api/v1/students/{student_id}/consent` | Bearer | JSON | SV tu xac nhan (method=self) hoac admin/P.CTSV nhap ban giay (method=paper). |
| POST | `/api/v1/students/{student_id}/consent/withdraw` | Bearer |  | Rut dong y: xoa ngay toan bo anh va vector khuon mat. |

## parents

PH4/PH7/PH8 - Phu huynh, lien ket con, tuy chon thong bao

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/parents` | Bearer | `q`, `limit`, `offset` | Tim theo ten/email, phan trang (X-Total-Count qua header). |
| POST | `/api/v1/parents` | Bearer | JSON | Create Parent |
| GET | `/api/v1/parents/me/children` | Bearer |  | My Children |
| GET | `/api/v1/parents/me/children/{student_id}/attendance` | Bearer | `semester` | Child Attendance |
| GET | `/api/v1/parents/me/preferences` | Bearer |  | My Preferences |
| PATCH | `/api/v1/parents/me/preferences` | Bearer | JSON | Update My Preferences |
| PATCH | `/api/v1/parents/{parent_id}` | Bearer | JSON | Update Parent |
| DELETE | `/api/v1/parents/{parent_id}` | Bearer |  | Delete Parent |
| GET | `/api/v1/parents/{parent_id}/children` | Bearer |  | List Parent Children |
| POST | `/api/v1/parents/{parent_id}/children` | Bearer | JSON | Link Child |
| DELETE | `/api/v1/parents/{parent_id}/children/{student_id}` | Bearer |  | Unlink Child |

## faces

PH5 - Dang ky khuon mat, P.CTSV duyet, SV xac nhan ket qua

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| POST | `/api/v1/faces/enroll/{student_id}` | Bearer | multipart | Dang ky khuon mat: chinh SV, admin/P.CTSV, hoac GV voi SV lop minh day. |
| GET | `/api/v1/faces/mine` | Bearer |  | My Faces |
| DELETE | `/api/v1/faces/mine` | Bearer |  | Delete My Faces |
| POST | `/api/v1/faces/mine/{embedding_id}/acknowledge` | Bearer |  | SV xac nhan da nhan ket qua duyet (duyet / tu choi kem ly do) cua anh khuon mat. |
| GET | `/api/v1/faces/pending` | Bearer |  | List Pending |
| PATCH | `/api/v1/faces/{embedding_id}/approve` | Bearer |  | P.CTSV duyet anh dang cho -> gui ket qua cho SV. |
| PATCH | `/api/v1/faces/{embedding_id}/reject` | Bearer | JSON | P.CTSV tu choi kem ly do khong hop le (bat buoc) -> gui ket qua cho SV. |

## attendance

PH6 - Phien diem danh, quet camera, tu diem danh, sua ket qua

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/sessions` | Bearer | `status`, `class_id`, `mine`, `limit` | Phien trong pham vi xem lop cua user, loc theo status (open/closed) va class_id. |
| POST | `/api/v1/sessions` | Bearer | JSON | Mo phien: dung ngay hom nay, dung thu cua lich, trong khung |
| GET | `/api/v1/sessions/{session_id}` | Bearer |  | Get Session |
| GET | `/api/v1/sessions/{session_id}/checkin-info` | Bearer |  | SV xem phong hoc cua buoi truoc khi tu diem danh (anh khuon mat + GPS). |
| PATCH | `/api/v1/sessions/{session_id}/close` | Bearer |  | Dong phien: SV chua co record -> absent; tra kem SV vua vuot nguong canh bao. |
| POST | `/api/v1/sessions/{session_id}/manual` | Bearer | JSON | Manual Check |
| POST | `/api/v1/sessions/{session_id}/recognize` | Bearer | multipart | Nhan 1 frame tu camera lop hoc, nhan dien va tu dong ghi diem danh. |
| GET | `/api/v1/sessions/{session_id}/records` | Bearer |  | List Records |
| PATCH | `/api/v1/sessions/{session_id}/records/{record_id}` | Bearer | JSON | Sua trang thai (bat buoc ly do, luu lich su). Phong ban chi duyet/huy "Co phep". |
| GET | `/api/v1/sessions/{session_id}/records/{record_id}/audits` | Bearer |  | Lich su sua diem danh cua 1 record. |
| GET | `/api/v1/sessions/{session_id}/roster` | Bearer |  | Danh sach SV cua lop gop voi trang thai diem danh cua phien nay. |
| POST | `/api/v1/sessions/{session_id}/self-checkin` | Bearer | multipart | SV tu diem danh: anh tu chup + GPS. |

## leave

PH6 - Don xin phep vang: SV nop, GV lop / Lanh dao Khoa duyet, SV xac nhan ket qua

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/leave-requests` | Bearer | `status`, `class_id`, `limit` | SV: don cua minh; GV: lop minh day; Lanh dao Khoa: SV/lop thuoc Khoa; admin, P.CTSV: toan truong. |
| POST | `/api/v1/leave-requests` | Bearer | JSON | SV nop don xin phep vang mot buoi hoc (lich hoc + ngay); giang vien lop nhan thong bao. |
| POST | `/api/v1/leave-requests/{leave_id}/acknowledge` | Bearer |  | SV xac nhan da nhan ket qua duyet don. |
| PATCH | `/api/v1/leave-requests/{leave_id}/approve` | Bearer | JSON | Duyet don => buoi do tinh vang co phep; gui ket qua cho SV. |
| PATCH | `/api/v1/leave-requests/{leave_id}/reject` | Bearer | JSON | Tu choi don kem ly do khong hop le (bat buoc); gui ket qua cho SV. |

## reports

PH8 - Thong ke, canh bao vang, xuat Excel

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/reports/attendance/export` | Bearer | `class_id`, `semester` | File Excel diem danh: sheet 1 ma tran SV x buoi hoc, sheet 2 thong ke lop. |
| GET | `/api/v1/reports/attendance/warnings` | Bearer | `class_id` | Danh sach SV vuot nguong vang (absent / tong buoi da hoc >= ABSENCE_WARN_RATIO). |
| GET | `/api/v1/reports/attendance/{class_id}` | Bearer |  | Thong ke chuyen can theo lop: ti le vang tung SV + canh bao. |
| GET | `/api/v1/reports/my-attendance` | Bearer |  | Sinh vien tu xem tom tat chuyen can theo tung lop (chi tinh phien da dong). |
| GET | `/api/v1/reports/overview` | Bearer | `semester` | Thong ke tong hop theo hoc ky, chia theo Khoa (chi so lieu, khong ten/anh). |

## notifications

PH7 - Hop thu thong bao (phu huynh, sinh vien, giang vien)

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/notifications` | Bearer | `unread_only`, `limit` | List Notifications |
| POST | `/api/v1/notifications/read-all` | Bearer |  | Mark All Read |
| GET | `/api/v1/notifications/unread-count` | Bearer |  | Unread Count |
| POST | `/api/v1/notifications/{notification_id}/read` | Bearer |  | Mark Read |

## audit

PH9 - Nhat ky he thong

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/audit-logs` | Bearer | `q`, `action`, `success`, `date_from`, `date_to`, `limit`, `offset` | List Audit Logs |

## media

Anh bang chung qua URL co chu ky

| Method | Duong dan | Xac thuc | Tham so / body | Mo ta |
|---|---|---|---|---|
| GET | `/api/v1/evidence/{file_path}` | — | `exp`, `sig` | Tra anh khi URL co chu ky hop le va con han. |

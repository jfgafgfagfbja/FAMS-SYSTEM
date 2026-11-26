# Kế hoạch Nhiệm vụ 1 (MVC + GitHub) và Nhiệm vụ 2 (Cloud) – Nhóm 5 người, dự án FAMS

> Lập ngày 25/11/2026. Thông tin gói miễn phí của các cloud được tra cứu cùng ngày (nguồn ở cuối tài liệu) – các nhà
> cung cấp đổi giá thường xuyên, **kiểm tra lại trang giá trước khi đăng ký**.

## 0. Yêu cầu của thầy và những gì thầy sẽ kiểm tra

| Nhiệm vụ | Yêu cầu | Thầy kiểm tra | Bằng chứng nhóm cần có |
|---|---|---|---|
| 1 | Tổ chức code theo **MVC**, chia **thư mục theo mô-đun** cho từng thành viên, kết nối GitHub | Tài khoản GitHub từng bạn, thư mục mỗi bạn phụ trách | Repo có 5 thành viên; mỗi mô-đun 1 thư mục có `README.md` ghi người phụ trách; file `.github/CODEOWNERS`; **commit + pull request từ chính tài khoản của từng bạn** trong thư mục của mình |
| 2 | Đăng ký 1 cloud kết nối GitHub để chạy code, cloud có hỗ trợ CSDL đã chọn | Truy cập link trong báo cáo cuối kỳ | 1 đường link chạy được (web + API), tự cập nhật khi push lên nhánh `main`; tài khoản đăng nhập mẫu ghi trong báo cáo |

## 1. Phân tích: FAMS đã theo MVC, nhưng đang tổ chức theo **lớp** chứ chưa theo **mô-đun**

| Thành phần MVC | Trong FAMS hiện tại | Thư mục hiện tại |
|---|---|---|
| **Model** – dữ liệu, truy cập CSDL | ORM SQLAlchemy (22 bảng) + Repository | `server/app/db/models.py` (1 tệp chung), `server/app/repositories/` |
| **View** – hiển thị | Giao diện Flutter (web, Android, iOS); phía server là dữ liệu JSON trả về (schema Pydantic) | `client/lib/features/` (chia theo **vai trò**: admin, lecturer, student…), `server/app/schemas/` |
| **Controller** – nhận yêu cầu, điều phối | 18 controller FastAPI; nghiệp vụ tách sang lớp **Service** | `server/app/api/v1/endpoints/`, `server/app/services/` |

**Vấn đề với yêu cầu của thầy:** code của một mô-đun đang nằm rải ở 5–6 thư mục (endpoints, services, repositories,
schemas, models, features…), nên không có "thư mục của bạn A". Thầy không thấy rõ ai làm phần nào.

**Giải pháp:** tổ chức lại theo **mô-đun** (feature-first). **Bên trong mỗi mô-đun vẫn tách M – V – C.** Mã mô-đun
lấy đúng mã phân hệ trong báo cáo giữa kỳ (MOD-01…MOD-10), nên báo cáo và code khớp nhau.

## 2. Cấu trúc thư mục đề xuất

```
FAMS-SYSTEM/
├── .github/
│   ├── CODEOWNERS                 # thư mục nào thuộc thành viên nào (GitHub tự gắn người review)
│   ├── pull_request_template.md
│   └── workflows/ci.yml           # chạy test mỗi lần push / PR (đã có)
├── render.yaml                    # cấu hình triển khai Render (Nhiệm vụ 2)
├── server/app/
│   ├── core/  db/  main.py        # dùng chung: cấu hình, bảo mật, phân quyền, kết nối CSDL  – TV1
│   └── modules/
│       ├── m01_auth/              # MOD-01 Xác thực và tài khoản                              – TV1
│       │   ├── models.py          #   M: User, RefreshToken, RevokedToken, PasswordReset
│       │   ├── repository.py      #   M: truy vấn CSDL
│       │   ├── schemas.py         #   V: dữ liệu vào / ra (JSON)
│       │   ├── service.py         #   nghiệp vụ
│       │   ├── controller.py      #   C: router FastAPI (/api/v1/auth/...)
│       │   ├── tests/             #   test của mô-đun
│       │   └── README.md          #   người phụ trách, phạm vi, API, bảng CSDL
│       ├── m02_catalog/           # MOD-02 Danh mục: đơn vị, cán bộ, địa điểm, phòng          – TV2
│       ├── m03_training/          # MOD-03 Đào tạo: giảng viên, lớp, ghi danh, lịch           – TV5
│       ├── m04_learners/          # MOD-04 Người học: sinh viên, đồng ý sinh trắc, phụ huynh  – TV3
│       ├── m05_faces/             # MOD-05 Sinh trắc khuôn mặt                                 – TV3
│       ├── m06_attendance/        # MOD-06 Điểm danh + đơn xin phép                            – TV4
│       ├── m07_notifications/     # MOD-07 Thông báo                                           – TV2
│       ├── m08_reports/           # MOD-08 Báo cáo, thống kê                                   – TV5
│       └── m09_audit/             # MOD-09 Nhật ký hệ thống                                    – TV2
└── client/lib/
    ├── core/  widgets/  app.dart  router.dart   # MOD-10 Khung giao diện chung                  – TV1
    └── modules/
        └── m0x_<tên>/
            ├── models/            #   M: lớp dữ liệu (fromJson)
            ├── controllers/       #   C: gọi API, giữ trạng thái màn hình
            └── views/             #   V: các trang (*_page.dart), widget riêng
```

Quy ước: mô-đun chỉ gọi mô-đun khác qua **service** (không truy vấn thẳng bảng của mô-đun khác), quan hệ ORM giữa
các mô-đun khai báo bằng tên lớp dạng chuỗi. `server/app/db/models.py` giữ lại làm nơi **gom** (import lại) mọi model
để Alembic và code cũ vẫn chạy trong lúc chuyển dần.

## 3. Phân công 5 thành viên (chia lại ngày 26/11/2026)

**Vì sao chia lại:** ngày 26/11 nhóm đo lại lượng code thực tế phải chuyển của từng mô-đun. Phía server gồm controller,
service, repository và schema; phía client gồm các trang và widget riêng. Bản chia ngày 25/11 bị lệch:

- TV2 (MOD-02 + MOD-03) khoảng **3 790 dòng, 36 API**;
- TV5 (MOD-07, 08, 09) chỉ khoảng **2 420 dòng, 10 API**.

Bản mới đổi chéo giữa TV2 và TV5: **MOD-03 Đào tạo chuyển sang TV5**, **MOD-07 Thông báo và MOD-09 Nhật ký chuyển
sang TV2**. TV1, TV3, TV4 giữ nguyên. Chênh lệch giữa TV2–TV5 giảm từ khoảng 1 370 dòng xuống khoảng 340 dòng.

### 3.1 Khối lượng từng mô-đun (đo ngày 26/11/2026)

| Mô-đun | Server (dòng) | Client (dòng) | API | Bảng CSDL | Người |
|---|---|---|---|---|---|
| MOD-02 Danh mục | ≈ 770 | ≈ 950 | 17 | units, staff, locations, rooms | TV2 |
| MOD-07 Thông báo | ≈ 430 | ≈ 230 | 4 + tác vụ gửi email | notifications | TV2 |
| MOD-09 Nhật ký hệ thống | ≈ 360 | ≈ 300 | 1 + ghi nhật ký tự động | audit_logs, attendance_audits | TV2 |
| MOD-04 Người học | ≈ 690 | ≈ 610 | 22 | students, parents, parent_students | TV3 |
| MOD-05 Khuôn mặt | ≈ 680 | ≈ 870 | 7 | face_embeddings | TV3 |
| MOD-06 Điểm danh, đơn xin phép | ≈ 1 350 | ≈ 1 580 | 17 + 2 tác vụ nền | attendance_sessions, attendance_records, leave_requests | TV4 |
| MOD-03 Đào tạo | ≈ 1 050 | ≈ 1 020 | 19 | lecturers, classes, enrollments, schedules | TV5 |
| MOD-08 Báo cáo, thống kê | ≈ 570 | ≈ 550 | 5 | không có bảng riêng (đọc dữ liệu điểm danh) | TV5 |

### 3.2 Bảng phân công

| TV | Tài khoản GitHub | Phụ trách | Code phải chuyển | API | Tệp test server | Trạng thái 26/11 |
|---|---|---|---|---|---|---|
| **TV1** (trưởng nhóm) | [@jfgafgfagfbja](https://github.com/jfgafgfagfbja) | MOD-01 Xác thực, MOD-10 Giao diện chung, phần dùng chung, **Nhiệm vụ 2 (cloud)**, review và gộp PR | đã chuyển (≈ 520 dòng + phần dùng chung ≈ 1 300 dòng) | 10 | 4 | ✅ phần code và cloud xong; còn các việc ở 3.3 |
| **TV2** | [@nguyenthai9351-code](https://github.com/nguyenthai9351-code) | MOD-02 Danh mục, MOD-07 Thông báo, MOD-09 Nhật ký | ≈ 3 030 dòng | 22 | 3 | đã vào repo, chưa có PR |
| **TV3** | [@YNCoder205](https://github.com/YNCoder205) | MOD-04 Người học, MOD-05 Khuôn mặt | ≈ 2 840 dòng | 29 | 3 | đã vào repo, chưa có PR |
| **TV4** | [@vuong557](https://github.com/vuong557) | MOD-06 Điểm danh, đơn xin phép | ≈ 2 930 dòng (nhiều quy tắc nghiệp vụ nhất) | 17 | 7 | **chưa chấp nhận lời mời vào repo** |
| **TV5** | [@dphu05](https://github.com/dphu05) | MOD-03 Đào tạo, MOD-08 Báo cáo | ≈ 3 180 dòng | 24 | 6 | đã vào repo, chưa có PR |

### 3.3 Việc cụ thể của từng người

Mỗi mô-đun làm trên 1 nhánh riêng và mở 1 pull request **từ tài khoản của chính người phụ trách**. Đường dẫn server
tính từ `server/app/`, client tính từ `client/lib/`, test tính từ `server/tests/`. Mẫu để làm theo:
`server/app/modules/m01_auth/README.md`. Mô-đun có nhiều tài nguyên thì đặt tên tệp `<tài nguyên>_controller.py`,
`<tài nguyên>_service.py`, `<tài nguyên>_repository.py` (công cụ truy vết tài liệu nhận diện theo hậu tố tên tệp).

**Việc chung cho TV2–TV5, lặp lại với mỗi mô-đun:**

1. **Chuyển tệp server.** Dùng `git mv` để giữ lịch sử commit, sau đó sửa import.
   - Model chuyển từ `db/models.py` sang `models.py` của mô-đun, rồi import lại trong `db/models.py` (xem khối MOD-01).
   - Hàm mapper của mô-đun trong `services/mappers.py` chuyển theo.
2. **Chuyển tệp client.**
   - Các trang chuyển vào `views/`.
   - Lớp gọi API của mô-đun (tách khỏi `api/*.dart`) chuyển vào `controllers/`.
   - Lớp dữ liệu (tách khỏi `models/models.dart`) chuyển vào `models/`, rồi `export` lại để code cũ vẫn chạy.
3. **Chuyển test và chạy lại.**
   - Test của mô-đun chuyển vào `tests/mXX_<tên>/`.
   - `pytest -q` (277 test), `flutter analyze` và `flutter test -j 1` đều phải sạch.
4. **Viết `README.md` của mô-đun:** người phụ trách, bảng M–V–C, API, bảng CSDL, quy tắc nghiệp vụ.
5. **Cập nhật `.github/CODEOWNERS`:** bỏ dấu `#` ở các dòng của mình.
6. **Trước khi mở PR, đồng bộ với `main`:** chạy `git pull --rebase origin main`.
   - Xung đột thường chỉ nằm ở các tệp gom: `db/models.py`, `api/v1/router.py`, `schemas/__init__.py`, `services/mappers.py`, `lib/models/models.dart`, `lib/api/api.dart`.
   - Khi gộp các tệp này, giữ dòng của cả hai phía.
7. **Kiểm tra trên cloud:** sau khi PR được gộp, Render tự deploy lại; kiểm tra mô-đun của mình trên
   https://fams-system-ug8s.onrender.com.

#### TV1 – @jfgafgfagfbja (trưởng nhóm)

| Việc | Trạng thái |
|---|---|
| Khung `modules/`, MOD-01, MOD-10, `CODEOWNERS`, mẫu PR, mời 4 thành viên | ✅ 25/11 |
| Nhiệm vụ 2: `render.yaml`, `deploy/render/Dockerfile`, tự nạp dữ liệu mẫu, đăng ký Render, link trong README | ✅ 25/11 |
| Chuyển `AuthApi` từ `api/catalog_api.dart` sang `modules/m01_auth/controllers/` (để TV2 tách tệp này gọn) | chưa |
| Bật bảo vệ nhánh `main` (bắt buộc qua PR, CI đạt) | chưa |
| Review và gộp PR của TV2–TV5; giữ các test dùng chung ở `tests/`: `test_authorization`, `test_infrastructure`, `test_migrations`, `test_flow_fixes`, `test_coverage_gaps`, `test_unit_roles` | khi có PR |
| Trước buổi chấm: CSDL Render còn hạn (hết hạn khoảng 25/12/2026), đổi mật khẩu mẫu, ghi link và tài khoản demo vào báo cáo cuối kỳ | trước buổi chấm |

#### TV2 – @nguyenthai9351-code: MOD-02 Danh mục, MOD-07 Thông báo, MOD-09 Nhật ký

| Mô-đun / nhánh | Server → `modules/…` | Client → `modules/…` | Test → `tests/…` |
|---|---|---|---|
| MOD-02 · `tv2/m02-catalog` → `m02_catalog/` | `api/v1/endpoints/{units,staff,locations,rooms}.py`, `services/{unit,staff,location,room}_service.py`, `repositories/{unit,staff,location,room}_repository.py`, `schemas/{organization,locations}.py`; model `Unit`, `Staff`, `Location`, `Room` | `features/admin/{units,staff,locations,rooms}_page.dart`; `UnitsApi`, `StaffApi`, `LocationsApi`, `RoomsApi` (trong `api/catalog_api.dart`) | `test_rooms.py` → `m02_catalog/` |
| MOD-07 · `tv2/m07-notifications` → `m07_notifications/` | `endpoints/notifications.py`, `services/{notification_service,parent_notify,user_notify,email_service}.py`, `repositories/notification_repository.py`, `schemas/notifications.py`; model `Notification`; vòng gửi email trong `jobs/scheduler.py` chỉ sửa import | `features/parent/notifications_page.dart`, `widgets/notification_bell.dart`; `NotificationsApi` (trong `api/report_api.dart`) | `test_parent_notifications.py` → `m07_notifications/` |
| MOD-09 · `tv2/m09-audit` → `m09_audit/` | `endpoints/audit_logs.py`, `services/{audit,audit_log_service}.py`, `repositories/audit_log_repository.py`, `schemas/audit_logs.py`; model `AuditLog`, `AttendanceAudit` | `features/admin/audit_logs_page.dart`; `AuditLogsApi` (trong `api/report_api.dart`) | `test_audit_log.py` → `m09_audit/` |

**Việc thêm của TV2:**

- **(a) Lọc phòng theo tòa nhà.** Trang Phòng dùng API `GET /rooms/buildings` để lọc. Client đã có hàm `RoomsApi.buildings()` nhưng chưa trang nào gọi.
- **(b) Email trên cloud.** Ghi trong README mô-đun các biến SMTP cần đặt trên Render. Bản demo có thể để trống; khi đó chỉ gửi thông báo trong app.
- **(c) Chuyển `services/audit.py` cuối cùng.** Tệp này gắn vào sự kiện `after_flush` của SQLAlchemy và được nhiều nơi gọi: `main.py`, `core/security.py`, MOD-01, MOD-08. Chuyển xong thì chạy lại toàn bộ test.

#### TV3 – @YNCoder205: MOD-04 Người học, MOD-05 Khuôn mặt (giữ nguyên)

| Mô-đun / nhánh | Server → `modules/…` | Client → `modules/…` | Test → `tests/…` |
|---|---|---|---|
| MOD-04 · `tv3/m04-learners` → `m04_learners/` | `api/v1/endpoints/{students,parents}.py`, `services/{student_service,parent_service,consent_service}.py`, `repositories/{student,parent}_repository.py`, `schemas/{students,parents}.py`; model `Student`, `Parent`, `ParentStudent` | `features/admin/{students,student_detail,parents}_page.dart`, `features/parent/children_page.dart`, `widgets/consent_form.dart`; `StudentsApi`, `ParentsApi` (trong `api/people_api.dart`) | `test_consent.py` → `m04_learners/` |
| MOD-05 · `tv3/m05-faces` → `m05_faces/` | `endpoints/faces.py`, `services/{face_service,face_data_service,antispoof_service}.py`, `repositories/face_repository.py`, `schemas/faces.py`; model `FaceEmbedding` | `features/admin/face_review_page.dart`, `features/student/{enroll_face,enroll_for_student}_page.dart`, `widgets/camera_capture.dart`; `FacesApi` (trong `api/people_api.dart`) | `test_face_approval.py`, `test_antispoof.py` → `m05_faces/` |

**Việc thêm của TV3:**

- **(a) Chọn mô hình khuôn mặt bằng biến môi trường `FACE_MODEL`.** Dùng `buffalo_l` trên máy, `buffalo_s` trên cloud 512 MB. Hiện code chưa có biến này.
- **(b) Tải sẵn mô hình trong bước build.** Sửa `deploy/render/Dockerfile`; đây là tệp của TV1 nên PR cần TV1 duyệt.
- **(c) Nút "Xóa dữ liệu khuôn mặt của tôi" cho sinh viên.** Client đã có `FacesApi.deleteMine()` gọi `DELETE /faces/mine`, nhưng chưa trang nào dùng.

#### TV4 – @vuong557: MOD-06 Điểm danh, đơn xin phép (giữ nguyên)

| Mô-đun / nhánh | Server → `modules/…` | Client → `modules/…` | Test → `tests/…` |
|---|---|---|---|
| MOD-06 · `tv4/m06-attendance` → `m06_attendance/` | `api/v1/endpoints/{sessions,leave_requests}.py`, `services/{session_service,attendance_service,leave_service,geo_service,evidence_cleanup}.py`, `repositories/{session,leave}_repository.py`, `schemas/{attendance,leaves}.py`; model `AttendanceSession`, `AttendanceRecord`, `LeaveRequest`; 2 vòng nền (tự đóng phiên, dọn ảnh bằng chứng) trong `jobs/scheduler.py` chỉ sửa import | `features/lecturer/{attendance_scan,sessions,session_records}_page.dart`, `features/student/self_checkin_page.dart`, `features/leave/leave_requests_page.dart`, `widgets/{attendance_views,evidence_image}.dart`; `SessionsApi`, `LeaveRequestsApi` (trong `api/attendance_api.dart`) | `test_session_lifecycle.py`, `test_open_session_rules.py`, `test_session_detail_and_records.py`, `test_confirm_frames.py`, `test_location_checkin.py`, `test_leave_and_warnings.py`, `test_evidence_cleanup.py` → `m06_attendance/` |

**Việc thêm của TV4:**

- **(a) Việc đầu tiên: chấp nhận lời mời vào repo** tại https://github.com/jfgafgfagfbja/FAMS-SYSTEM/invitations. Lời mời hết hạn khoảng ngày 02/12/2026.
- **(b) README mô-đun.** Ghi luật mở / đóng phiên, đi muộn, bán kính GPS, đơn xin phép.
- **(c) Kiểm thử trên cloud.**
  - Mở phiên, quét camera, duyệt đơn.
  - Sinh viên tự điểm danh bằng GPS (cần HTTPS; Render có sẵn).
  - Ghi lại mức RAM khi nhận diện (phối hợp với TV3).
- **(d) Ghi chú lưu trữ ảnh.** Ảnh bằng chứng nằm trên ổ đĩa tạm nên mất khi dịch vụ khởi động lại.

#### TV5 – @dphu05: MOD-03 Đào tạo, MOD-08 Báo cáo

| Mô-đun / nhánh | Server → `modules/…` | Client → `modules/…` | Test → `tests/…` |
|---|---|---|---|
| MOD-03 · `tv5/m03-training` → `m03_training/` | `api/v1/endpoints/{lecturers,classes,schedules}.py`, `services/{lecturer,class,schedule}_service.py`, `repositories/{lecturer,class,schedule}_repository.py`, `schemas/{lecturers,classes,schedules}.py`; model `Lecturer`, `Class`, `Enrollment`, `Schedule` | `features/admin/{lecturers,classes,class_detail,schedules}_page.dart`, `features/schedule/{week_schedule_page,schedule_pdf}.dart`; `api/training_api.dart` | `test_admin_crud.py`, `test_admin_management.py`, `test_week_schedule.py` → `m03_training/` |
| MOD-08 · `tv5/m08-reports` → `m08_reports/` | `endpoints/reports.py`, `services/{report_service,attendance_stats}.py`, `repositories/report_repository.py`, `schemas/reports.py` | `features/lecturer/reports_page.dart`, `features/office/overview_page.dart`, `features/student/my_attendance_page.dart`, `features/parent/child_attendance_page.dart`; `ReportsApi` (trong `api/report_api.dart`) | `test_reports.py`, `test_reports_export_and_warnings.py`, `test_my_attendance_detail.py` → `m08_reports/` |

**Việc thêm của TV5:**

- **(a) Xử lý API trùng chức năng.** API `GET /reports/my-attendance` có ở cả server và client (`ReportsApi.myAttendance()`), nhưng trang sinh viên đang gọi `/students/me/attendance`. Chọn một trong hai: dùng API này, hoặc bỏ API thừa.
- **(b) README mô-đun.** Ghi các quy tắc:
  - chống trùng phòng;
  - chỉ Quản trị viên / Phòng Đào tạo được ghi danh và xếp lịch;
  - ngưỡng cảnh báo vắng 20 %.
- **(c) Kiểm tra trên cloud:** xếp lịch trùng phòng bị chặn, xuất Excel, xuất PDF lịch tuần.

Mỗi người **tự làm phần của mình bằng tài khoản của mình**. Thầy kiểm tra lịch sử commit, nên không ai commit hộ
người khác.

## 4. Quy trình làm việc trên GitHub

1. **Repo chung:** nên tạo một **GitHub Organization** miễn phí (vd `fams-nhom-xx`), chuyển repo `FAMS-SYSTEM` vào,
   thêm 5 thành viên quyền *Write*. (Hoặc giữ repo cá nhân và thêm *Collaborators* ở Settings → Collaborators.)
2. **Bảo vệ nhánh `main`** (Settings → Branches): bắt buộc qua Pull Request, cần 1 người duyệt, CI phải đạt.
3. **Mỗi thành viên:**
   ```bash
   git clone https://github.com/<org>/FAMS-SYSTEM.git
   git config user.name  "Họ Tên"
   git config user.email "email-đã-đăng-ký-GitHub@..."   # sai email => commit không hiện tên tài khoản
   git switch -c tv4/m06-attendance
   # ... chuyển / sửa code trong thư mục mô-đun của mình (dùng git mv để giữ lịch sử) ...
   cd server && venv\Scripts\python -m pytest -q          # test phải đạt trước khi đẩy
   git add -A && git commit -m "feat(m06): chuyen module diem danh vao modules/m06_attendance"
   git push -u origin tv4/m06-attendance                  # rồi mở Pull Request trên GitHub
   ```
4. **Thứ tự để không giẫm chân nhau:** TV1 làm khung + MOD-01 trước (vài ngày đầu). Sau đó TV2…TV5 làm song song:
   mỗi người chỉ sửa trong thư mục mô-đun của mình. Phần dùng chung (`db/models.py` gom model, `api/v1/router.py`
   đăng ký router) chỉ thêm 1–2 dòng, xung đột nếu có rất dễ gộp.
5. **`.github/CODEOWNERS`** đã điền sẵn tài khoản theo bảng phân công 26/11. Dòng của TV2–TV5 đang có dấu `#`; mỗi
   bạn tự bỏ dấu này trong PR đầu tiên của mình:
   ```
   /server/app/core/                      @jfgafgfagfbja
   /server/app/modules/m01_auth/          @jfgafgfagfbja
   /server/app/modules/m02_catalog/       @nguyenthai9351-code
   /server/app/modules/m07_notifications/ @nguyenthai9351-code
   /server/app/modules/m09_audit/         @nguyenthai9351-code
   /server/app/modules/m04_learners/      @YNCoder205
   /server/app/modules/m05_faces/         @YNCoder205
   /server/app/modules/m06_attendance/    @vuong557
   /server/app/modules/m03_training/      @dphu05
   /server/app/modules/m08_reports/       @dphu05
   # ... và các dòng tương ứng cho client/lib/modules/
   ```
6. **Quy ước commit:** `feat(m06): ...`, `fix(m04): ...`, `docs(m07): ...`, `test(m02): ...`.

## 5. Nhiệm vụ 2 – Các cloud chạy Java / Python / C#, kết nối GitHub, có CSDL trên cùng nền tảng

| Nền tảng | Java | Python | C# (.NET) | Kết nối GitHub | CSDL có sẵn trên nền tảng | Miễn phí / chi phí (tra 25/11/2026) | Hợp với FAMS (Python + PostgreSQL + pgvector)? |
|---|---|---|---|---|---|---|---|
| **Render** | Docker | Có sẵn | Docker | Tự deploy khi push; cấu hình bằng `render.yaml` trong repo | PostgreSQL (có **pgvector**), Key Value (Redis) | Web service miễn phí 512 MB RAM, ngủ sau 15 phút không truy cập (lần đầu chờ ~1 phút); Postgres miễn phí **hết hạn sau 30 ngày** | **Khuyến nghị** |
| **Railway** | Có | Có | Có | Tự deploy khi push | PostgreSQL, MySQL, MongoDB, Redis (1 click); SQL Server và Postgres + pgvector qua template | Dùng thử $5 (30 ngày, không cần thẻ), sau đó gói Free $1/tháng; Hobby $5/tháng; dữ liệu của tài khoản dùng thử bị xóa 30 ngày sau khi hết credit | Tốt (đủ RAM) nếu chấp nhận $5/tháng |
| **Koyeb** | Có | Có | Docker | Tự deploy khi push | PostgreSQL (có hướng dẫn dùng pgvector) | 1 web service 512 MB + 1 Postgres giới hạn 50 giờ hoạt động/tháng | Được, nhưng giờ CSDL dễ hết |
| **Northflank** | Có | Có | Có | CI/CD từ GitHub | PostgreSQL, MySQL, MongoDB, Redis | Gói Sandbox: 2 service, 2 job, 1 CSDL, chạy liên tục | Cần kiểm tra pgvector |
| **Microsoft Azure** | Có sẵn (App Service) | Có sẵn | Có sẵn | Deployment Center / GitHub Actions | **Azure SQL (SQL Server)**, PostgreSQL Flexible (bật pgvector qua `azure.extensions`), MySQL Flexible, Cosmos DB | **Azure for Students**: $100 dùng trong 12 tháng, **không cần thẻ** (cần email sinh viên); Azure SQL serverless miễn phí 100.000 vCore-giây/tháng | Được; cấu hình phức tạp hơn, credit tiêu nhanh nếu bật CSDL cả tháng |
| **Google Cloud** | Cloud Run (container) | Có | Có | Cloud Build lấy code từ GitHub | Cloud SQL: PostgreSQL, MySQL, SQL Server | Dùng thử $300 trong 90 ngày (cần tài khoản thanh toán); Cloud Run có hạn mức miễn phí, Cloud SQL tính phí | Được nhưng cần thẻ |
| **AWS** | Elastic Beanstalk | Có | Có | CodePipeline / GitHub Actions | RDS: PostgreSQL, MySQL, MariaDB, SQL Server, Oracle | Gói Free cho tài khoản mới: tối đa $200 credit, tối đa 6 tháng (cần thẻ) | Được nhưng phức tạp |
| **Heroku** | Có | Có | Qua buildpack .NET | Tự deploy khi push | Heroku Postgres (có pgvector); MySQL qua add-on | Không có gói miễn phí; sinh viên có GitHub Student Pack được credit hằng tháng | Được nếu có Student Pack |
| **Fly.io** | Docker | Docker | Docker | GitHub Actions (flyctl) | Managed Postgres (trả phí); tự chạy MySQL / SQL Server trên volume | Tài khoản mới không còn gói miễn phí lâu dài (chỉ dùng thử ngắn) | Tốn phí |
| **DigitalOcean App Platform** | Có | Có | Có | Tự deploy khi push | PostgreSQL (pgvector), MySQL, MongoDB, Redis / Valkey, Kafka | Trả phí; credit cho sinh viên được báo là đã ngừng năm 2026 | Tốn phí |

Gợi ý cho các nhóm dùng **C# + SQL Server**: Azure (App Service + Azure SQL) là tự nhiên nhất. **Java / Python +
MySQL hoặc PostgreSQL**: Render, Railway. Nhóm mình dùng **Python + PostgreSQL + pgvector** nên chọn Render.

## 6. Chọn cloud cho FAMS: Render

**Yêu cầu kỹ thuật của FAMS:** server Python 3.11 (Docker), **PostgreSQL có pgvector** (lưu vector khuôn mặt),
giao diện Flutter web, HTTPS (camera và GPS trên trình duyệt chỉ chạy trên HTTPS), mô hình nhận diện InsightFace.

**Vì sao Render:** miễn phí; Postgres có pgvector (migration của FAMS tự chạy `CREATE EXTENSION vector`); deploy tự
động mỗi lần push `main`; cấu hình nằm trong repo (`render.yaml`) nên thầy thấy được trên GitHub; có HTTPS sẵn. Dự
án đã có `server/single_port.py` chạy **web + API trên cùng một cổng**, nên chỉ cần **1 web service + 1 CSDL**, và
thầy chỉ cần **1 đường link**.

| Rủi ro | Cách xử lý | Người làm |
|---|---|---|
| RAM 512 MB, mô hình `buffalo_l` cần khoảng 1 GB khi nhận diện | Biến môi trường chọn `buffalo_s` (nhẹ hơn nhiều) trên cloud; nếu vẫn thiếu thì nâng gói trả phí thấp nhất | TV3 |
| Dịch vụ ngủ sau 15 phút, lần đầu mở chờ khoảng 1 phút | Ghi chú trong báo cáo; mở link trước giờ thầy chấm | TV1 |
| Postgres miễn phí hết hạn sau 30 ngày | Tạo CSDL **trong vòng 30 ngày trước buổi chấm**, hoặc nâng gói; sao lưu bằng `pg_dump` | TV1 |
| Gói miễn phí không có shell để nạp dữ liệu mẫu | Thêm biến `SEED_ON_START=1`: khởi động lần đầu tự chạy `seed.py` nếu CSDL trống | TV1 |
| Ổ đĩa tạm: ảnh bằng chứng, ảnh chờ duyệt mất khi dịch vụ khởi động lại | Chấp nhận cho bản demo, ghi rõ trong báo cáo (bản thật dùng ổ đĩa / kho lưu ảnh trả phí) | TV3 (ảnh chờ duyệt), TV4 (ảnh bằng chứng) |
| Lần đầu nhận diện phải tải mô hình (vài chục đến vài trăm MB) | Tải sẵn mô hình trong bước build Docker | TV3 |

**Phương án dự phòng:** Railway (Hobby $5/tháng, đủ RAM cho `buffalo_l`, CSDL không hết hạn), hoặc Azure for
Students nếu cả nhóm có email sinh viên.

### Các bước triển khai trên Render (TV1 chủ trì)
1. Đăng ký Render bằng tài khoản GitHub (người đăng ký tự làm; cấp quyền cho repo `FAMS-SYSTEM`).
2. Thêm vào repo: `render.yaml` (1 Postgres + 1 web service Docker), Dockerfile nhiều giai đoạn: build Flutter web
   → image Python chạy `single_port.py`; biến môi trường `DATABASE_URL` (lấy từ CSDL Render), `SECRET_KEY` (Render tự
   sinh), `FACE_MODEL=buffalo_s`, `SEED_ON_START=1`, `CORS_ORIGINS`.
3. Render → New → Blueprint → chọn repo → Apply. Theo dõi log: `alembic upgrade head`, seed, uvicorn chạy.
4. Kiểm tra: `https://<tên>.onrender.com/api/v1/health` trả `{"status":"ok","database":"ok"}`; đăng nhập bằng 9 tài
   khoản mẫu; thử luồng chính của từng mô-đun (mỗi TV kiểm phần mình).
5. **Đổi mật khẩu mẫu** trước khi đưa link vào báo cáo; ghi link + tài khoản demo vào README và báo cáo cuối kỳ.

## 7. Lịch thực hiện

| Thời gian | Việc | Người |
|---|---|---|
| 25/11 ✅ | Mời thành viên, CODEOWNERS, mẫu PR; khung `modules/` + MOD-01 làm mẫu; `render.yaml`, Dockerfile, seed tự động, deploy Render | TV1 |
| 26/11 – 28/11 | TV4 chấp nhận lời mời; mỗi người clone repo, cấu hình email Git, đọc mục 3.3 và `m01_auth/README.md` | TV2 – TV5 |
| 29/11 – 05/12 | Mỗi người chuyển mô-đun của mình (1 PR / mô-đun) + README + test; TV1 review, gộp lần lượt | TV2 – TV5, TV1 |
| 03/12 – 08/12 | Việc thêm ở mục 3.3: `FACE_MODEL` + tải sẵn mô hình (TV3), lọc phòng theo tòa nhà + SMTP (TV2), API trùng `my-attendance` (TV5) | TV2, TV3, TV5 |
| 08/12 – 12/12 | Mỗi người kiểm tra mô-đun của mình trên link cloud, sửa lỗi; TV4 kiểm luồng điểm danh GPS + camera | Cả nhóm |
| Trước buổi chấm | CSDL còn hạn (hết hạn khoảng 25/12/2026), mở link "đánh thức" dịch vụ, đổi mật khẩu mẫu, cập nhật link + tài khoản demo vào báo cáo | TV1 |

(Nếu lịch nộp báo cáo cuối kỳ khác, dời các mốc cho phù hợp.)

## 8. Việc nhóm phải tự làm

- Mỗi thành viên có **tài khoản GitHub riêng**, cấu hình đúng email để commit hiện đúng tên.
- Đăng ký cloud, xác minh email / thẻ / sinh viên do **chính người đăng ký** thực hiện.
- Commit, mở PR, review: do từng thành viên làm bằng tài khoản của mình.

## 9. Tiến độ

| Ngày | Việc | Người | Trạng thái |
|---|---|---|---|
| 25/11/2026 | Khung `server/app/modules/` + MOD-01 làm mẫu (models, repository, schemas, service, controller, README, test riêng `tests/m01_auth/`); client `lib/modules/m01_auth/{controllers,views}`, `m10_shell/views`; bộ truy vết tài liệu nhận thư mục mô-đun | TV1 | ✅ 277 test server, 43 test client đạt |
| 25/11/2026 | `.github/CODEOWNERS`, mẫu Pull Request | TV1 | ✅ (các TV tự thêm dòng của mình) |
| 25/11/2026 | `render.yaml`, `deploy/render/Dockerfile`, `.dockerignore`, `SEED_ON_START` trong `entrypoint.sh` | TV1 | ✅ |
| 25/11/2026 | Đăng ký Render (kết nối GitHub, Blueprint `fams-system`), deploy: **https://fams-system-ug8s.onrender.com** – tự deploy lại mỗi lần push `main` | TV1 | ✅ |
| 25/11/2026 | Sửa lỗi build trên Render: `TAR_OPTIONS=--no-same-owner` (tar không đổi được chủ sở hữu tệp trong user namespace) | TV1 | ✅ |
| 25/11/2026 | Mời collaborator quyền Write: TV2 @nguyenthai9351-code, TV3 @YNCoder205, TV4 @vuong557, TV5 @dphu05 | TV1 | ✅ 26/11: 4/5 đã vào repo; @vuong557 chưa chấp nhận |
| 26/11/2026 | Chia lại theo khối lượng code đo thực tế: MOD-03 sang TV5; MOD-07, MOD-09 sang TV2 (mục 3); cập nhật `CODEOWNERS`, `client/lib/modules/README.md` | TV1 | ✅ |
| — | MOD-02, MOD-07, MOD-09 | TV2 | chưa |
| — | MOD-04, MOD-05 | TV3 | chưa |
| — | MOD-06 | TV4 | chưa |
| — | MOD-03, MOD-08 | TV5 | chưa |

## Nguồn tham khảo (tra ngày 25/11/2026)

- Render: [Deploy for Free](https://render.com/docs/free), [Supported extensions (pgvector)](https://render.com/docs/postgresql-extensions), [Native runtimes](https://render.com/docs/native-runtimes), [Docker](https://render.com/docs/docker), [Blueprint YAML](https://render.com/docs/blueprint-spec), [Platforms with a real free tier 2026](https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026)
- Railway: [Pricing plans](https://docs.railway.com/pricing/plans), [Free trial](https://docs.railway.com/pricing/free-trial), [SQL Server template](https://railway.com/deploy/microsoft-sql-server--mssql), [Postgres with pgvector](https://railway.com/deploy/postgres-with-pgvector-engine)
- Koyeb: [Pricing FAQ](https://koyeb.com/docs/faq/pricing), [pgvector tutorials](https://www.koyeb.com/tutorials/tag/pgvector)
- Northflank: [Pricing](https://northflank.com/pricing)
- Fly.io: [Pricing](https://fly.io/pricing), [Managed Postgres](https://fly.io/docs/mpg), [Discontinued plans](https://fly.io/docs/about/discontinued-plans/)
- Azure: [Azure for Students](https://azure.microsoft.com/free/students/), [pgvector trên PostgreSQL Flexible Server](https://learn.microsoft.com/azure/postgresql/extensions/how-to-use-pgvector)
- Google Cloud: [Free features and trial](https://docs.cloud.google.com/free)
- AWS: [Free Tier FAQs](https://aws.amazon.com/free/faqs/)
- Heroku: [Heroku for GitHub Students](https://heroku.com/github-students)
- DigitalOcean: [GitHub Students](https://www.digitalocean.com/github-students), [It's FOSS – credits ended](https://itsfoss.com/news/digitalocean-open-source-credits-end.md)

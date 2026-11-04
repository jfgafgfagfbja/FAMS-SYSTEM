# Tổng quan dự án FAMS

> **FAMS — Face Attendance Management System**: hệ thống quản lý sinh viên tích hợp điểm danh
> bằng nhận diện khuôn mặt cho Trường Đại học Kiến trúc Đà Nẵng.
>
> Tài liệu này mô tả **hệ thống gốc** (nguồn sự thật nghiệp vụ) và phạm vi của bản tái cấu trúc
> `FAMS-SYSTEM`. Ngày phân tích: 03/11/2026.

## 1. Nguồn gốc và phạm vi

| Hạng mục | Giá trị |
|---|---|
| Mã nguồn gốc | `D:\FAMS` — nhánh `feature/flutter-phan-quyen`, commit cuối `b9a6ca8` (09/10/2026) **cộng 67 thay đổi chưa commit** (nhật ký hệ thống, đồng ý sinh trắc có phiên bản, vai trò Lãnh đạo Khoa…) |
| Bản tái cấu trúc | `D:\LTM\FAMS-SYSTEM` — sao chép nguyên trạng thư mục làm việc ở trên (gồm cả phần chưa commit), sau đó tái cấu trúc |
| Nguyên tắc cô lập | Bản gốc chỉ được **đọc**. Bản mới có Docker project, cổng, database, tài khoản DB, volume, mã ứng dụng di động riêng — xem [MIGRATION_PLAN.md](MIGRATION_PLAN.md) §2 |
| "Farm" | Tên gọi nhầm của FAMS trong yêu cầu ban đầu (đã xác nhận với người dùng) |

## 2. Mục tiêu nghiệp vụ

1. Điểm danh sinh viên nhanh, chống gian lận: giảng viên quét camera cả lớp, hoặc sinh viên tự
   điểm danh bằng ảnh tự chụp + GPS + mã QR luân phiên chiếu trong phòng.
2. Quản lý dữ liệu đào tạo phục vụ điểm danh: đơn vị, cán bộ, giảng viên, sinh viên, phụ huynh,
   lớp học phần, ghi danh, lịch học, phòng học, địa điểm.
3. Theo dõi chuyên cần, cảnh báo vắng (≥ 20 % số buổi), xuất Excel, thống kê tổng hợp theo Khoa.
4. Bảo vệ dữ liệu sinh trắc: đồng ý có phiên bản, duyệt khuôn mặt, ảnh tạm xóa sau duyệt, ảnh
   bằng chứng tự xóa sau 90 ngày, URL ảnh có chữ ký hết hạn.
5. Minh bạch: nhật ký sửa điểm danh bắt buộc lý do, nhật ký hệ thống ghi tự động mọi thay đổi.

## 3. Tác nhân (vai trò)

| Mã vai trò | Tên | Phạm vi dữ liệu |
|---|---|---|
| `admin` | Quản trị viên | Toàn trường, mọi quyền |
| `training_office` | Phòng Đào tạo | Toàn trường: lớp, lịch, giảng viên, phòng, địa điểm |
| `student_affairs` | Phòng Công tác SV | Toàn trường: sinh viên, phụ huynh, duyệt khuôn mặt, duyệt "có phép" |
| `faculty_office` | Văn phòng Khoa | Chỉ Khoa mình: nhập liệu lớp/lịch/ghi danh |
| `faculty_leader` | Lãnh đạo Khoa | Chỉ Khoa mình: giám sát, duyệt "có phép", xem nhật ký Khoa |
| `board` | Ban ngành | Chỉ số liệu thống kê tổng hợp (không tên, không ảnh) |
| `lecturer` | Giảng viên | Lớp mình dạy: mở phiên, quét, xác nhận tay, sửa điểm danh |
| `student` | Sinh viên | Dữ liệu của mình: lịch, tự điểm danh, chuyên cần, khuôn mặt |
| `parent` | Phụ huynh | Con đã liên kết: chuyên cần, thông báo |

Vai trò cán bộ được **suy ra từ loại đơn vị** khi tạo tài khoản (Khoa → `faculty_office`,
P. Đào tạo → `training_office`, P. CTSV → `student_affairs`, Ban ngành → `board`).

## 4. Công nghệ

| Tầng | Công nghệ |
|---|---|
| Server | Python 3.10/3.11, FastAPI 0.115, SQLAlchemy 2.0, Pydantic 2, Alembic 1.18, slowapi (rate limit), python-jose (JWT), passlib/bcrypt, openpyxl (Excel) |
| Nhận diện | InsightFace `buffalo_l` (SCRFD + ArcFace 512 chiều) trên ONNX Runtime CPU; chống giả mạo MiniFASNetV2 (ONNX, tự tắt nếu thiếu model) |
| Database | PostgreSQL 16 + pgvector (cột `Vector(512)`, chỉ mục HNSW cosine) |
| Client | Flutter 3.47 (một mã nguồn cho Web/Android/iOS): Dio, go_router, provider, flutter_secure_storage, camera, geolocator, mobile_scanner, fl_chart, pdf/printing |
| Triển khai | Docker Compose (db, server, web nginx), Caddy HTTPS cho production, GitHub Actions CI |

## 5. Quy mô mã nguồn (bản gốc)

| Thành phần | Số liệu |
|---|---|
| Server | 16 router, 96 endpoint (+ `GET /`), 11 service, 21 bảng, 15 migration, ~6 500 dòng `app/` |
| Test server | 26 file pytest, **258 test — tất cả đạt** trên bản gốc (03/11/2026) |
| Client | 33 trang/màn hình, 11 widget dùng chung, 10 file test |
| Phân hệ | 9 phân hệ, 38 chức năng, 126 module (theo tài liệu phân tích `D:\LTM\phan-tich-chi-tiet-fams`) |

## 6. Bộ tài liệu

| Tài liệu | Nội dung |
|---|---|
| [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md) | Kiến trúc hiện tại, luồng dữ liệu, đánh giá so với mô hình Client–Server mục tiêu |
| [BUSINESS_LOGIC.md](BUSINESS_LOGIC.md) | Toàn bộ quy tắc nghiệp vụ, ngưỡng, ma trận phân quyền |
| [DATABASE_ANALYSIS.md](DATABASE_ANALYSIS.md) | 21 bảng, quan hệ, ràng buộc, chỉ mục, migration |
| [FEATURE_INVENTORY.md](FEATURE_INVENTORY.md) | Danh mục đầy đủ chức năng + trạng thái chuyển đổi/kiểm thử |
| [MIGRATION_PLAN.md](MIGRATION_PLAN.md) | Kiến trúc đích, kế hoạch chuyển đổi từng bước, rủi ro |
| [architecture/TARGET_ARCHITECTURE.md](architecture/TARGET_ARCHITECTURE.md) | Kiến trúc Client–Server sau tái cấu trúc |
| [api/API.md](api/API.md) · [api/ENDPOINTS.md](api/ENDPOINTS.md) | Quy ước API, danh sách 98 endpoint (sinh tự động) |
| [database/](database/README.md) | ERD sinh từ models, quy tắc đổi schema |
| [deployment/DEPLOYMENT.md](deployment/DEPLOYMENT.md) · [BACKUP_RESTORE.md](deployment/BACKUP_RESTORE.md) | Triển khai, vận hành, sao lưu |
| [TEST_REPORT.md](TEST_REPORT.md) | Kết quả kiểm thử, phần chưa kiểm được |

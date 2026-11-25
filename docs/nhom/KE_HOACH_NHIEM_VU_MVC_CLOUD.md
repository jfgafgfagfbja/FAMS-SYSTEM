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
│       ├── m03_training/          # MOD-03 Đào tạo: giảng viên, lớp, ghi danh, lịch           – TV2
│       ├── m04_learners/          # MOD-04 Người học: sinh viên, đồng ý sinh trắc, phụ huynh  – TV3
│       ├── m05_faces/             # MOD-05 Sinh trắc khuôn mặt                                 – TV3
│       ├── m06_attendance/        # MOD-06 Điểm danh + đơn xin phép                            – TV4
│       ├── m07_notifications/     # MOD-07 Thông báo                                           – TV5
│       ├── m08_reports/           # MOD-08 Báo cáo, thống kê                                   – TV5
│       └── m09_audit/             # MOD-09 Nhật ký hệ thống                                    – TV5
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

## 3. Phân công 5 thành viên

Khối lượng tính theo số dòng code **đang có** (server: controller + service + repository + schema) và số API, để chia
đều. TV1 ít code nghiệp vụ hơn nhưng giữ phần dùng chung, tích hợp và **triển khai cloud**.

| TV | Mô-đun | Thư mục server | Màn hình client chuyển vào `modules/` | Bảng CSDL | API | Code server hiện có |
|---|---|---|---|---|---|---|
| **TV1** (trưởng nhóm) | MOD-01 Xác thực, MOD-10 Giao diện chung, hạ tầng | `core/`, `db/`, `main.py`, `modules/m01_auth/` | `auth/*` (đăng nhập, quên / đặt lại mật khẩu, tài khoản, splash), `home/home_page`, `app_shell`, `router`, `core/*`, widget dùng chung | users, refresh_tokens, revoked_tokens, password_resets | 10 | ≈ 520 dòng + phần dùng chung ≈ 1 300 dòng |
| **TV2** | MOD-02 Danh mục, MOD-03 Đào tạo | `m02_catalog/`, `m03_training/` | `admin/units, staff, locations, rooms, lecturers, classes, class_detail, schedules`; `schedule/week_schedule_page, schedule_pdf` | units, staff, locations, rooms, lecturers, classes, enrollments, schedules | 36 | ≈ 1 800 dòng |
| **TV3** | MOD-04 Người học, MOD-05 Khuôn mặt | `m04_learners/`, `m05_faces/` | `admin/students, student_detail, parents, face_review`; `student/enroll_face, enroll_for_student`; `parent/children_page`; widget `consent_form, camera_capture` | students, parents, parent_students, face_embeddings | 29 | ≈ 1 350 dòng |
| **TV4** | MOD-06 Điểm danh, đơn xin phép | `m06_attendance/` | `lecturer/attendance_scan, sessions, session_records`; `student/self_checkin`; `leave/leave_requests`; widget `attendance_views, evidence_image` | attendance_sessions, attendance_records, leave_requests | 17 | ≈ 1 300 dòng (nhiều quy tắc nghiệp vụ nhất) |
| **TV5** | MOD-07 Thông báo, MOD-08 Báo cáo, MOD-09 Nhật ký | `m07_notifications/`, `m08_reports/`, `m09_audit/` | `parent/notifications_page, child_attendance_page`; `lecturer/reports_page`; `office/overview_page`; `student/my_attendance_page`; `admin/audit_logs_page` | notifications, audit_logs, attendance_audits | 10 + 3 tác vụ nền | ≈ 1 400 dòng |

### Việc cụ thể của từng người (mỗi việc = 1 pull request từ tài khoản của chính người đó)

| TV | Việc |
|---|---|
| TV1 | (1) Tạo GitHub Organization / mời thành viên, bảo vệ nhánh `main`, `CODEOWNERS`, mẫu PR. (2) Tạo khung `modules/`, chuyển `core/`, `db/`, MOD-01 trước để làm mẫu cho cả nhóm. (3) Chuyển khung client (`router`, `app_shell`, `core`). (4) Nhiệm vụ 2: viết `render.yaml` + Dockerfile triển khai, nạp dữ liệu mẫu khi khởi động lần đầu, đăng ký Render, gắn link vào README và báo cáo. (5) Review và gộp PR của cả nhóm. |
| TV2 | (1) Chuyển MOD-02, MOD-03 (server + client) vào thư mục mô-đun, chạy test. (2) README cho 2 mô-đun (API, bảng, quy tắc: chống trùng phòng, chỉ QTV / P.ĐT ghi danh – xếp lịch). (3) Bổ sung: client dùng API `GET /rooms/buildings` (đang có ở server nhưng chưa màn hình nào gọi). |
| TV3 | (1) Chuyển MOD-04, MOD-05. (2) README. (3) Cho phép chọn mô hình khuôn mặt bằng biến môi trường (`buffalo_l` trên máy, `buffalo_s` nhẹ hơn trên cloud 512 MB). (4) Thêm nút "Xóa dữ liệu khuôn mặt của tôi" (API `DELETE /faces/mine` đã có, giao diện chưa có). |
| TV4 | (1) Chuyển MOD-06. (2) README (luật mở / đóng phiên, đi muộn, GPS, đơn xin phép). (3) Kiểm thử luồng điểm danh trên bản cloud (tự điểm danh bằng GPS cần HTTPS – Render có sẵn). |
| TV5 | (1) Chuyển MOD-07, MOD-08, MOD-09 + 3 tác vụ nền. (2) README. (3) Client dùng API `GET /reports/my-attendance` (chưa màn hình nào gọi) hoặc bỏ API thừa. (4) Cấu hình email thông báo trên cloud (SMTP, có thể để trống ở bản demo). |

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
5. **`.github/CODEOWNERS`** (điền tên tài khoản thật):
   ```
   /server/app/core/                    @tv1-github
   /server/app/modules/m01_auth/        @tv1-github
   /server/app/modules/m02_catalog/     @tv2-github
   /server/app/modules/m03_training/    @tv2-github
   /server/app/modules/m04_learners/    @tv3-github
   /server/app/modules/m05_faces/       @tv3-github
   /server/app/modules/m06_attendance/  @tv4-github
   /server/app/modules/m07_notifications/ @tv5-github
   /server/app/modules/m08_reports/     @tv5-github
   /server/app/modules/m09_audit/       @tv5-github
   /client/lib/modules/m02_*/           @tv2-github
   # ... tương tự cho client
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
| Ổ đĩa tạm: ảnh bằng chứng, ảnh chờ duyệt mất khi dịch vụ khởi động lại | Chấp nhận cho bản demo, ghi rõ trong báo cáo (bản thật dùng ổ đĩa / kho lưu ảnh trả phí) | TV4, TV5 |
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
| 25/11 – 28/11 | Lập Organization, mời thành viên, bảo vệ nhánh, CODEOWNERS; khung `modules/` + MOD-01 làm mẫu | TV1 (cả nhóm tạo tài khoản GitHub) |
| 29/11 – 05/12 | Mỗi người chuyển mô-đun của mình + README + test, mở PR; TV1 review, gộp | TV2 – TV5 |
| 03/12 – 08/12 | Chuẩn bị triển khai: `render.yaml`, Dockerfile, chọn mô hình nhẹ, seed tự động | TV1, TV3 |
| 08/12 – 12/12 | Triển khai Render, mỗi người kiểm tra mô-đun của mình trên link thật, sửa lỗi | Cả nhóm |
| Trước buổi chấm | CSDL còn hạn, mở link "đánh thức" dịch vụ, cập nhật link + tài khoản demo vào báo cáo | TV1 |

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
| — | Đăng ký Render, deploy, ghi link | TV1 | đang làm |
| — | MOD-02 … MOD-09 | TV2 – TV5 | chưa |

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

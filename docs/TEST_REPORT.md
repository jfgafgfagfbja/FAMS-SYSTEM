# Báo cáo kiểm thử FAMS-SYSTEM

> Ngày: 03/11/2026, bổ sung 04/11/2026 (build Docker + kiểm thử đầu-cuối, mục 5) và 10/11/2026 (thay đổi
> nghiệp vụ theo góp ý, **mục 7 — số liệu hiện hành**). Mục 1–5 là số liệu của mốc tái cấu trúc.
> Môi trường: Windows 11, Python 3.10.11 (venv riêng của server), Flutter 3.47.4,
> PostgreSQL 16 + pgvector trong container riêng `fams-system-db-1` (cổng 5433).
> Kết quả theo từng chức năng: [FEATURE_INVENTORY.md](FEATURE_INVENTORY.md).

## 1. Tổng hợp

| Hạng mục | Bản gốc (mốc) | Sau tái cấu trúc | Ghi chú |
|---|---|---|---|
| Test server (pytest, Postgres thật) | 258/258 đạt | **279/279 đạt** | +21 test mới, không sửa kỳ vọng test cũ |
| Route server có test gọi tới | 88/97 | **98/98** | Mọi route có cả nhánh thành công (2xx) |
| `flutter analyze` | 0 vấn đề | **0 vấn đề** | |
| Test client (`flutter test -j 1`) | 10 tệp / 51 test đạt | **11 tệp / 55 test đạt** | +`api_layer_test.dart` |
| Hợp đồng client ↔ server | — | **95/95 endpoint client tồn tại trên server, đúng động từ** | `scripts/check_api_contract.py` |
| Migration Alembic trên DB trống = models | chưa kiểm | **Đạt** (+ downgrade/upgrade, 1 head) | Phát hiện và sửa lệch 4 chỉ mục |
| Sao lưu → khôi phục vòng tròn | — | **Đạt** (22 bảng trùng số dòng, ảnh, sha256) | |
| Cú pháp `docker-compose.yml`, `deploy/docker-compose.prod.yml` | — | **Hợp lệ** (`docker compose config`) | |
| Build image Docker + chạy stack qua nginx | — | **Đạt** — 3 container khỏe; 43/43 GET, 9/9 vai trò | Mục 5 |
| Kiểm thử đầu-cuối trên trình duyệt | — | **Đạt** — 13 trang, sáng/tối, lấy GPS | Mục 5 |

## 2. Server

Lệnh: `cd server && venv\Scripts\python -m pytest -q -p no:cacheprovider` (279 passed, ~40 s).

Kiểm thử sau **mỗi** bước tái cấu trúc (luôn 100 % đạt): hạ tầng `/api/v1` → tách schema → nhóm danh mục → nhóm đào
tạo → nhóm người học + báo cáo → khuôn mặt → điểm danh → thông báo, nhật ký, xác thực, ảnh.

Thay đổi trong bộ test cũ — chỉ **đường dẫn kỹ thuật**, không đổi kỳ vọng:
- `conftest.py`: `TestClient(base_url=".../api/v1")`; import `limiter` từ `app.core.rate_limit`; DB test `fams_system_test`.
- `test_confirm_frames.py`: import `_confirm_counts` từ `app.services.session_service`.
- `test_open_session_rules.py`: điểm giả lập giờ chuyển từ `app.api.sessions.datetime` sang
  `app.services.attendance_service.datetime` (nghiệp vụ "đi muộn" đã chuyển sang service).

Test mới:

| Tệp | Số test | Nội dung |
|---|---|---|
| `test_infrastructure.py` | 9 | Tiền tố `/api/v1` (đường dẫn cũ ⇒ 404), health có kiểm DB, `X-Request-ID` (sinh/giữ/lọc giá trị lạ), định dạng lỗi 401/403/404/422, log access có request id, OpenAPI (đường dẫn, nhóm, `tokenUrl`) |
| `test_coverage_gaps.py` | 9 | 9 route bản gốc chưa có test + 5 route chỉ test nhánh bị từ chối: sửa đơn vị, danh sách/xóa cán bộ (kể cả chặn 409), sửa địa điểm + một mặc định, xóa phòng, chi tiết/xóa lớp, sửa SV, danh sách/sửa phụ huynh, gỡ liên kết, phụ huynh xem con + chuyên cần của con (403 với con người khác) |
| `test_migrations.py` | 3 | Một head; `alembic upgrade head` trên DB trống khớp `models.py`; nâng cấp lặp lại không lỗi, `downgrade -1` rồi `upgrade` |

Đo độ phủ route: `PYTHONPATH=tools ROUTE_COV_OUT=route_coverage.json pytest -p route_coverage_plugin --junitxml=junit.xml`
(plugin ghi lại mọi cặp method + route và mã HTTP mà test thực sự nhận được).

### Lỗi đã phát hiện nhờ kiểm thử

| # | Vấn đề (có sẵn từ bản gốc) | Ảnh hưởng | Xử lý |
|---|---|---|---|
| 1 | 4 chỉ mục do migration tạo (HNSW khuôn mặt, hàng đợi email, `rooms.location_id`, `schedules.room_id`) không khai báo trong `models.py` | `alembic revision --autogenerate` sẽ đề xuất **xóa** chỉ mục HNSW (nhận diện chậm hẳn); DB test thiếu chỉ mục | Khai báo vào `models.py`; DB thật không đổi, không cần migration |
| 2 | 9 endpoint không có test nào | Lỗi ở đó không bị phát hiện | Bổ sung test (bảng trên) |
| 3 | `test_checkin_qr.py::test_lecturer_gets_rotating_code` thỉnh thoảng trượt (~1/30 lần chạy) | Test phụ thuộc thời gian: `expires_in_seconds = int(...)` bằng 0 nếu chạy đúng giây cuối của chu kỳ QR 30 s | **Giữ nguyên** (không đổi nghiệp vụ hiển thị); đã gặp 1 lần trong quá trình, chạy lại đạt. Đề xuất: dùng `ceil` cho số giây còn lại. ★ 10/11/2026: không còn — mã QR đã bỏ hẳn, tệp test đã xóa (mục 7) |

## 3. Client

- `flutter analyze`: 0 vấn đề (đã sửa 1 lỗi kiểu `int?` → `Object` phát sinh khi chuyển lớp API, đúng ý định gốc
  vì nút "Lịch sử sửa" chỉ hiện khi bản ghi tồn tại).
- `flutter test -j 1 --machine` → `client/tool/flutter_results.py`: 11/11 tệp đạt, 55 test. Test mới
  `api_layer_test.dart`: cấu hình địa chỉ máy chủ (chuẩn hóa, ghép `/api/v1`, URL ảnh) + 39 phương thức lớp API gọi
  đúng động từ/đường dẫn.
- Chạy song song (mặc định) bị **sập Dart VM** do máy thiếu bộ nhớ ảo (ổ C: đầy) — không liên quan mã nguồn; chạy
  tuần tự `-j 1` đạt cả bản gốc lẫn bản mới.

## 4. Dữ liệu và vận hành

| Kiểm tra | Kết quả |
|---|---|
| `alembic upgrade head` + `seed.py` trên DB mới `fams_system` | Đạt — 15 migration, dữ liệu mẫu 10 tài khoản |
| `scripts/backup.sh` (CSDL + ảnh, sha256) | Đạt |
| `scripts/restore.sh --target-db fams_system_restore_check` | Đạt — 22 bảng trùng số dòng, `alembic_version = d4f8a2c6e913`, ảnh giải nén đúng nội dung |
| Script chạy trên Git Bash (Windows) | Đã sửa 2 lỗi chuyển đổi đường dẫn của MSYS (`MSYS_NO_PATHCONV`, `pwd -W`) |
| `scripts/import_legacy.sh` | **Không chạy** — chỉ người vận hành quyết định nhập dữ liệu bản gốc |
| Cô lập bản gốc | Sau mỗi lần chạy test: container `fams-db-1` chỉ có `fams`, `fams_flutter_demo`, `fams_public`; không có DB test nào của bản mới |

## 5. Docker và kiểm thử đầu-cuối (04/11/2026)

Thực hiện sau khi chuyển đĩa ảo Docker sang ổ D: (`D:\DockerDesktop\docker-data`).

**Build và chạy stack** (`docker compose build server client` → `docker compose up -d`):

| Kiểm tra | Kết quả |
|---|---|
| Build image | Đạt — `fams-system-server` 1,97 GB, `fams-system-client` 154 MB (Flutter 3.47.4 build web), ~3 phút nhờ cache |
| Lỗi phát hiện khi build | `server/entrypoint.sh` mang kết thúc dòng CRLF (thư mục chép từ Windows, không qua git nên `.gitattributes` không có tác dụng) ⇒ container sẽ báo `exec ./entrypoint.sh: no such file or directory`. **Đã sửa**: đổi các tệp chạy trong Linux sang LF và thêm bước bỏ byte CR trong `server/Dockerfile` |
| Khởi động | `db`, `server` (healthy, `alembic upgrade head` không lỗi), `client` (nginx) đều chạy; `GET /api/v1/health` qua cổng 5273 ⇒ `{"status":"ok","database":"ok"}` |
| API qua nginx, 9 vai trò (tài khoản mẫu `seed.py`) | 9/9 đăng nhập; **43/43 GET đúng 200**; mỗi phản hồi có `X-Request-ID`; đăng xuất ⇒ dùng lại token cũ bị 401 (9/9) |
| Phân quyền qua nginx | 5/5 đúng ma trận mục 3 BUSINESS_LOGIC: SV bị 403 ở nhật ký / danh sách SV / đơn vị; Ban ngành bị 403 ở nhật ký và cảnh báo vắng theo lớp (chỉ xem thống kê tổng hợp); sai mật khẩu ⇒ 401 |
| Swagger | `http://localhost:8100/docs` (cổng server, chỉ mở trên máy chủ); cổng web 5273 chỉ chuyển tiếp `/api/` — đúng thiết kế |

**Trình duyệt** (Flutter web tại `http://localhost:5273`, tài khoản quản trị mẫu):

| Kiểm tra | Kết quả |
|---|---|
| Đăng nhập, trang Tổng quan | Đạt — số liệu khớp CSDL (1 lớp, 2 SV, 1 GV) |
| 13 trang quản trị: lớp, lịch, phòng, địa điểm, phiên, báo cáo, SV, duyệt khuôn mặt, GV, phụ huynh, cán bộ, đơn vị, nhật ký | Đạt — mọi request `/api/v1/...` trả 200, không lỗi console; nhật ký hiển thị đúng các lần đăng nhập/đăng xuất/đăng nhập sai vừa tạo |
| 10.07 Giao diện sáng/tối | Đạt — Sáng, Tối, Theo hệ thống; lựa chọn giữ sau khi tải lại trang |
| 2.18 Lấy vị trí hiện tại | Đạt — GPS **giả lập** trong trang (không dùng vị trí thật của máy); bấm nút ⇒ ô vĩ độ/kinh độ điền đúng tọa độ; hủy form, không lưu |

Kết quả `e2e:` ghi ở `docs/tools/e2e_results.json`; `FEATURE_INVENTORY.md` sinh lại với `--e2e` ⇒ **126/126**.

**Còn lại, chưa kiểm được:**

| Hạng mục | Lý do | Cách hoàn tất |
|---|---|---|
| Nhận diện khuôn mặt với model thật (đăng ký, quét, tự điểm danh selfie) | Cần camera và khuôn mặt người thật; test tự động dùng giả lập `face_service` như bản gốc. Model InsightFace (~300 MB) tải về volume `insightface` ở lần dùng đầu | Mở app trên máy có camera (localhost hoặc HTTPS), đăng ký khuôn mặt một SV mẫu, mở phiên, quét |
| Chống giả mạo (liveness) | Thiếu tệp model `server/models/2.7_80x80_MiniFASNetV2.onnx` — **bản gốc cũng không có** nên hệ thống bỏ qua bước này (log cảnh báo khi khởi động), hành vi giống bản gốc | Tải model theo `server/models/README.md` nếu muốn bật |

## 6. Sự cố trong quá trình làm

- **Ổ C: đầy**: trong phiên này đã ghi 209 MB cache pip và 63 MB tệp tạm Flutter lên ổ C: — đã xóa đúng các tệp đó.
  Mọi tệp tạm sau đó chuyển sang `D:\LTM\FAMS-SYSTEM\.tmp`.
- **Docker Desktop sập** khi build image (23:46, 03/11/2026), container `fams-db-1` của bản gốc dừng (exit 255).
  Đã `docker start fams-db-1`; PostgreSQL phục hồi WAL bình thường; kiểm tra lại: healthy, 3 database còn nguyên,
  truy vấn dữ liệu bình thường. Image/cache build dở của bản mới nằm trong đĩa ảo Docker.

## 7. Thay đổi nghiệp vụ theo góp ý (10/11/2026)

Nội dung góp ý và cách làm: [BUSINESS_LOGIC.md](BUSINESS_LOGIC.md) (các mục đánh dấu ★),
[MIGRATION_PLAN.md §8](MIGRATION_PLAN.md). Migration mới `e2a7c4b91f6d` (16 migration, 22 bảng).

### 7.1 Số liệu hiện hành

| Hạng mục | Kết quả | Ghi chú |
|---|---|---|
| Test server (pytest, Postgres thật) | **277/277 đạt** (0 lỗi, 0 bỏ qua) | `server/junit.xml`; trước góp ý 279 — bỏ tệp test QR, thêm test nghiệp vụ mới |
| Route server có test gọi tới | **102/102** | `server/route_coverage.json` (101 route dưới `/api/v1` + `GET /`) |
| Migration trên DB trống = models | **Đạt** (1 head `e2a7c4b91f6d`, downgrade/upgrade) | `test_migrations.py` 3/3; DB dev đã nâng lên head |
| `flutter analyze` | **0 vấn đề** | |
| Test client (`flutter test -j 1`) | **10 tệp / 43 test đạt** | Bỏ `checkin_qr_test.dart` (màn hình QR không còn) |
| Hợp đồng client ↔ server | **99/99 endpoint client tồn tại trên server, đúng động từ** | 2 route server client không gọi: `GET /health`, `GET /students/me` |
| Danh mục chức năng | **134/134** chức năng có bằng chứng | [FEATURE_INVENTORY.md](FEATURE_INVENTORY.md); 3 chức năng QR chuyển sang mục "đã bỏ" |
| Bộ sơ đồ phân rã / DFD / CSDL | 134 chức năng lá, 45 DFD **cân bằng 44/44**, 22 bảng, **0 liên kết hỏng / 1750** | `docs/tools/gen_phan_ra.py`, `docs/tools/check_links.py` |

### 7.2 Test thêm / sửa theo nghiệp vụ mới

| Tệp | Thay đổi | Nội dung kiểm |
|---|---|---|
| `test_leave_and_warnings.py` (mới) | 10 test | SV gửi đơn xin phép vắng ⇒ GV lớp nhận thông báo; kiểm hợp lệ (ngày quá xa, đúng thứ của lịch, trùng đơn); không xin phép cho buổi đã có mặt; chỉ **GV của lớp** hoặc **Lãnh đạo Khoa** của Khoa đó được duyệt; **từ chối bắt buộc nêu lý do không hợp lệ**, SV nhận phản hồi rồi **xác nhận đã xem**; đơn được duyệt ⇒ đóng phiên ghi `excused` (cả khi duyệt sau khi đóng phiên); **cảnh báo vắng gửi SV + phụ huynh ngay sau thống kê** khi đóng phiên; endpoint/trường QR đã biến mất; `schedules.room` không lặp mã phòng |
| `test_face_approval.py` | +3 test, đổi người duyệt | Chỉ **Phòng CTSV** duyệt khuôn mặt (Quản trị viên ⇒ 403); kết quả duyệt/từ chối (kèm lý do) gửi thông báo cho SV, SV xác nhận; ảnh đã quyết định không quyết định lại |
| `test_unit_roles.py` | đổi kỳ vọng | Văn phòng Khoa **không còn** ghi danh SV và xếp lịch học (403); vẫn quản lý lớp, xem báo cáo trong Khoa |
| `test_parent_notifications.py`, `test_audit_log.py`, `test_tokens_and_media.py` | đổi kỳ vọng | Phụ huynh nhận thêm cảnh báo vắng sau thống kê; nhật ký ghi thêm loại `leave_request`; bỏ đường dẫn mã QR |
| `test_checkin_qr.py` | **xóa** | Bỏ hẳn mã QR khi SV tự điểm danh |
| Client: `access_test`, `api_layer_test`, `models_test`, `parent_notifications_test`, `feedback_pages_test` | cập nhật | Quyền mới (`reviewFaces` = CTSV, `planClasses`, `requestLeave`, `reviewLeaves`), API đơn xin phép + xác nhận khuôn mặt, mô hình `LeaveRequest`, SV mở được trang thông báo |

### 7.3 Cô lập bản gốc

Trong suốt đợt sửa chỉ chạy container `fams-system-db-1` (cổng 5433). Container `fams-db-1` của bản gốc **không bị
đụng tới**: nó đã dừng (exit 255) khi Docker Desktop tắt trước đợt sửa; đợt sửa không khởi động, không ghi vào nó.
Mã nguồn `D:\FAMS` chỉ được đọc.

Image Docker `fams-system-server`/`fams-system-client` đã build lại theo mã mới — mục 7.4.

### 7.4 Build Docker lại và kiểm thử đầu-cuối (10/11/2026)

`docker compose build server client` → `docker compose up -d`: 3 container khỏe, CSDL ở head `e2a7c4b91f6d`,
`GET /api/v1/health` qua nginx (cổng 5273) ⇒ `{"status":"ok","database":"ok"}`.

| Kiểm tra qua nginx (`/api/v1`) | Kết quả |
|---|---|
| 9 vai trò đăng nhập, `/auth/me` có `X-Request-ID`, GET theo vai trò; đăng xuất ⇒ token cũ 401 | Đạt |
| Quản trị viên xem hàng chờ duyệt khuôn mặt ⇒ 403; P.CTSV ⇒ 200 | Đạt |
| Văn phòng Khoa ghi danh SV / thêm lịch học ⇒ 403; Văn phòng Khoa, phụ huynh xem đơn xin phép ⇒ 403 (đúng ma trận quyền) | Đạt |
| `GET /sessions/{id}/checkin-code`, `PATCH /sessions/{id}` (bật QR) không còn | Đạt |
| SV nộp đơn ⇒ GV lớp nhận thông báo; đơn trùng bị chặn; Ban ngành duyệt ⇒ 403; từ chối thiếu lý do bị chặn; từ chối có lý do ⇒ SV nhận thông báo kèm lý do ⇒ SV xác nhận; đơn đã quyết định không duyệt lại | Đạt |
| **Tổng** | **81/81 đạt** (`.tmp/e2e_nghiep_vu.log`) |

Trên trình duyệt (Flutter web, cổng 5273): menu Quản trị viên không còn "Duyệt khuôn mặt", có "Đơn xin phép"; SV có
"Đơn xin phép" + "Thông báo"; form nộp đơn chặn ngày quá 7 ngày trước, tự chọn đúng buổi học theo thứ, khóa nút khi
chưa có lý do; nộp đơn ⇒ hiện "Chờ duyệt", đúng phòng P101. Đơn, thông báo do kiểm thử tạo đã xóa khỏi CSDL dev
(nhật ký hệ thống vẫn giữ các dòng ghi lại thao tác kiểm thử).

# Báo cáo kiểm thử FAMS-SYSTEM

> Ngày: 03/11/2026, bổ sung 04/11/2026 (build Docker + kiểm thử đầu-cuối, mục 5).
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
| 3 | `test_checkin_qr.py::test_lecturer_gets_rotating_code` thỉnh thoảng trượt (~1/30 lần chạy) | Test phụ thuộc thời gian: `expires_in_seconds = int(...)` bằng 0 nếu chạy đúng giây cuối của chu kỳ QR 30 s | **Giữ nguyên** (không đổi nghiệp vụ hiển thị); đã gặp 1 lần trong quá trình, chạy lại đạt. Đề xuất: dùng `ceil` cho số giây còn lại |

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

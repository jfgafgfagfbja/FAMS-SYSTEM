# Sơ đồ luồng dữ liệu và CSDL - Hệ thống FAMS (Điểm danh bằng nhận diện khuôn mặt)

Mở file bằng trình duyệt (bấm đúp), không cần cài gì. Nên mở `phan_ra_chuc_nang.html` hoặc `workflow_tong_quan.html` trước.
Mọi trang có chung thanh điều hướng và liên kết chéo hai chiều.

> ★ Cập nhật 10/11/2026 theo góp ý nghiệp vụ: bỏ mã QR; chỉ Phòng CTSV duyệt khuôn mặt, kết quả gửi SV và SV xác nhận; Văn phòng Khoa không còn ghi danh / xếp lịch; đơn xin phép vắng (GV lớp / Lãnh đạo Khoa duyệt, từ chối có lý do); cảnh báo vắng sau thống kê; CSDL chuẩn 4NF. Mọi trang sinh lại từ code và kết quả test sau khi sửa.

| File | Nội dung |
|---|---|
| `workflow_tong_quan.html` | Sơ đồ quy trình: 2 chế độ (theo phân hệ PH1–PH9 + toàn cảnh, theo 9 vai trò). Mỗi bước ghi bảng CSDL đọc / ghi; mỗi quy trình có liên kết sang DFD và đặc tả |
| `phan_ra_chuc_nang.html` | **Sơ đồ phân rã chức năng (BFD)**: hệ thống → 10 phân hệ → 37 chức năng cấp 2 → **134 chức năng lá** (tận cùng), số hiệu chuẩn PTTK (vd 6.3.5) |
| `dfd.html` | **DFD các mức** theo ký hiệu giáo trình PTTK: sơ đồ ngữ cảnh, mức 0, mức 1 (9 phân hệ), mức 2 (34 chức năng cấp 2) — 45 sơ đồ, bấm tiến trình để đi xuống mức sâu hơn; mỗi sơ đồ có bảng từ điển luồng |
| `dac_ta_chuc_nang.html` | **Đặc tả & truy vết từng chức năng lá**: vào/ra, các bước xử lý, luồng mức lá, bảng đọc/ghi (đo khi chạy), API (tham số, thân, phản hồi, quyền), **chuỗi gọi controller → service → repository** (liên kết tới dòng code trên GitHub), lỗi có thể trả về, màn hình client, test. Trang mở đầu là **ma trận truy vết** 134 dòng |
| `erd_csdl.html` | ERD 22 bảng (PK, FK, kiểu, 33 quan hệ), đối chiếu kho DFD D1–D10 với bảng |
| `chuan_hoa_csdl.html` | ★ **Chuẩn hóa CSDL đến 4NF** theo 3 bước: (1) gom mọi thuộc tính vào **một bảng** (quan hệ phổ quát), (2) **tách bảng** theo phụ thuộc hàm / đa trị, (3) **phân rã** 1NF → 2NF → 3NF → BCNF → 4NF; ghi chú từng bảng và vi phạm 3NF đã sửa (`schedules.room`) |
| `csdl_chi_tiet.html` | Chi tiết từng bảng: cột, kiểu, khóa, quan hệ, quy trình dùng bảng, **các chức năng lá đọc / ghi bảng** (liên kết), CREATE TABLE |
| `chuc_nang_cay.html` | Cây chức năng theo 9 vai trò, **dựng từ quyền thật trong code** (require_roles, phạm vi Khoa/lớp); mỗi dòng dẫn tới đặc tả |
| `schema.sql` | Script tạo CSDL PostgreSQL 16 + pgvector (22 bảng, 33 khóa ngoại, 49 chỉ mục, chú thích tiếng Việt) |
| `erd.png`, `erd.svg`, `phan_ra_chuc_nang.png/.svg`, `dfd/*.png/.svg` | Hình để chèn vào báo cáo (mỗi DFD một file) |

## Cách các phần nối với nhau

```
Phân hệ (DFD mức 0) ── Chức năng cấp 2 (DFD mức 1) ── Chức năng lá (DFD mức 2, đặc tả)
                                                          │
          ┌──────────────┬───────────────┬────────────────┼──────────────┬─────────────┐
     Màn hình client   Endpoint API   Chuỗi gọi code   Bảng CSDL / kho DFD   Test    Vai trò được dùng
```

- **Luồng dữ liệu chỉ khai báo ở mức lá**, các mức trên được gộp tự động ⇒ các mức **luôn cân bằng** (bộ sinh kiểm tra: 44/44 sơ đồ).
- **Bảng đọc/ghi không viết tay**: đo bằng cách chạy 277 test với plugin ghi SQL (`server/tools/sql_trace_plugin.py`), tách theo nguồn
  (nghiệp vụ / xác thực–phân quyền / trình nghe thông báo / ghi nhật ký) nhờ ngăn xếp lời gọi.
- **Chuỗi gọi, lỗi, quyền, tham số** đọc tĩnh từ mã nguồn (`docs/tools/trace_code.py`): AST + `require_roles` + OpenAPI.
- Ghi "ngầm" qua trình nghe sự kiện được vẽ thành luồng tới tiến trình phụ trách: ghi nhật ký → 9.1.x, sinh thông báo phụ huynh → 7.1.1;
  ★ thông báo cho SV / GV (kết quả duyệt, đơn xin phép mới, cảnh báo vắng sau thống kê) → 7.1.2.
- Kiểm tra tự động khi sinh: 102/102 route, 3/3 tác vụ nền thuộc ít nhất một chức năng lá; 22/22 bảng có chức năng đọc/ghi;
  127/127 chức năng lá (trừ PH10 hỗ trợ giao diện) có luồng dữ liệu; 0 liên kết hỏng.

Kho trong DFD: **D1–D10** là nhóm bảng CSDL (★ D10 = `leave_requests`); **M1** bộ đếm tạm trong bộ nhớ tiến trình (đăng nhập sai, giới hạn tần suất,
xác nhận 2 khung hình); **F1** thư mục ảnh `evidence/` (ảnh bằng chứng, ảnh khuôn mặt chờ duyệt).

## Phát hiện khi truy vết (ghi trong đặc tả)

- 7 endpoint không có màn hình nào gọi: `GET /`, `/health` (vận hành), `/rooms/buildings` (client tự tính),
  `/students/me` (dùng `/auth/me`), `/sessions/{id}/records` (dùng roster), `/reports/my-attendance` (dùng chuyên cần chi tiết),
  **`DELETE /faces/mine`** (giao diện chưa có nút; SV xóa dữ liệu khuôn mặt qua "Rút đồng ý").
- Chống giả mạo khuôn mặt (5.1.2) đang tự tắt vì thiếu tệp model — giống bản gốc.

## Sinh lại

Từ thư mục gốc `FAMS-SYSTEM` (cần container `fams-system-db-1` đang chạy để có CSDL test):

```bash
cd server && PYTHONPATH=tools SQL_TRACE_OUT=../docs/tools/trace/sql_trace.json ./venv/Scripts/python.exe -m pytest -q -p sql_trace_plugin && cd ..
./server/venv/Scripts/python.exe docs/tools/trace_code.py
./server/venv/Scripts/python.exe docs/tools/gen_phan_ra.py --png-all
```

- Bước 1 đo bảng đọc/ghi thật; bước 2 truy vết code; bước 3 sinh 3 trang mới **và** gọi `gen_so_do_csdl.py` để sinh lại 4 trang cũ kèm liên kết, cùng trang `chuan_hoa_csdl.html` (`gen_chuan_hoa.py`).
- Kiểm tra liên kết chéo: `./server/venv/Scripts/python.exe docs/tools/check_links.py` (hiện 0 hỏng / 1750).
- Sửa nghiệp vụ / phân rã: `docs/tools/phan_ra_data.py`. Sửa mô tả bảng, quy trình: `docs/tools/so_do_data.py`.
- `--png` xuất PNG cho sơ đồ ngữ cảnh, mức 0, mức 1 và BFD; `--png-all` thêm mức 2 (cần Microsoft Edge).
- Liên kết tới code trỏ vào nhánh `main` trên GitHub (`jfgafgfagfbja/FAMS-SYSTEM`); đổi code thì chạy lại để số dòng khớp.

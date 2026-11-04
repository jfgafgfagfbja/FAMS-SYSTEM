# Sơ đồ luồng dữ liệu và CSDL - Hệ thống FAMS (Điểm danh bằng nhận diện khuôn mặt)

Mở file bằng trình duyệt (bấm đúp), không cần cài gì. Nên mở `workflow_tong_quan.html` trước.

| File | Nội dung |
|---|---|
| `workflow_tong_quan.html` | Sơ đồ quy trình tương tác: 2 chế độ (theo phân hệ PH1-PH9 + sơ đồ toàn cảnh, theo 9 vai trò). Mỗi bước ghi bảng CSDL đọc / ghi, bấm chip để mở chi tiết bảng |
| `erd_csdl.html` | ERD 21 bảng (PK, FK, kiểu dữ liệu, 29 quan hệ 1:N / 1:1), có phóng to / thu nhỏ; bảng đối chiếu kho DFD (D1-D9) với bảng CSDL |
| `csdl_chi_tiet.html` | Chi tiết từng bảng: cột, kiểu, khóa, quan hệ, quy trình dùng bảng, câu lệnh CREATE TABLE |
| `chuc_nang_cay.html` | Cây chức năng con theo 9 vai trò (96 chức năng, mỗi chức năng ghi đầu vào / đầu ra) |
| `schema.sql` | Script tạo CSDL PostgreSQL 16 + pgvector (21 bảng, 29 khóa ngoại, 45 chỉ mục, chú thích tiếng Việt cho mọi bảng và cột) |
| `erd.png`, `erd.svg` | Hình ERD để chèn vào báo cáo |

## 9 vai trò

Quản trị viên (`admin`), Phòng Đào tạo (`training_office`), Phòng Công tác sinh viên (`student_affairs`),
Văn phòng Khoa (`faculty_office`), Lãnh đạo Khoa (`faculty_leader`), Ban ngành (`board`),
Giảng viên (`lecturer`), Sinh viên (`student`), Phụ huynh (`parent`).

## 9 phân hệ

| Mã | Phân hệ |
|---|---|
| PH1 | Đăng nhập, token và mật khẩu |
| PH2 | Đơn vị, cán bộ, địa điểm, phòng học |
| PH3 | Giảng viên, lớp học phần, ghi danh, lịch học |
| PH4 | Sinh viên, đồng ý sinh trắc, phụ huynh |
| PH5 | Đăng ký và duyệt dữ liệu khuôn mặt |
| PH6 | Phiên điểm danh và ghi nhận kết quả |
| PH7 | Thông báo điểm danh cho phụ huynh |
| PH8 | Chuyên cần, cảnh báo vắng, thống kê |
| PH9 | Ghi và tra cứu nhật ký hệ thống |

## Ghi chú

- Khác với bộ mẫu (dữ liệu lưu tệp JSON, CSDL chỉ là thiết kế), CSDL ở đây là **CSDL thật** của FAMS-SYSTEM:
  sinh trực tiếp từ các model SQLAlchemy trong `server/app/db/models.py`. Cột "Tên trường (code)" là tên cột thật.
- `schema.sql` đã được kiểm tra bằng cách chạy trên một CSDL trống rồi so với CSDL do Alembic tạo:
  147/147 cột (tên, kiểu, NULL), 45/45 chỉ mục và 29/29 khóa ngoại giống hệt nhau.
- Hệ thống chạy thật bằng Alembic (`alembic upgrade head`). `schema.sql` dùng để đọc, đưa vào báo cáo, hoặc dựng nhanh một CSDL trống.
  Dựng thử: `psql -U <user> -d <db_trong> -f schema.sql` (cần cài extension `vector`).
- Kiểu `VECTOR(512)` lưu vector khuôn mặt ArcFace. Chỉ mục HNSW (`vector_cosine_ops`) dùng để tìm khuôn mặt gần nhất.

## Sinh lại bộ tài liệu

Khi đổi model hoặc nghiệp vụ, sửa mô tả trong `docs/tools/so_do_data.py` rồi chạy (từ thư mục gốc `FAMS-SYSTEM`):

```bash
./server/venv/Scripts/python.exe docs/tools/gen_so_do_csdl.py --png
```

Script tự kiểm tra mô tả có khớp model không (thiếu hoặc thừa bảng / cột sẽ báo lỗi). Tùy chọn `--png` cần Microsoft Edge để xuất `erd.png`.
Giao diện (CSS, cách vẽ) lấy từ bộ mẫu qua `docs/tools/make_so_do_templates.py`, lưu ở `docs/tools/so_do_templates/`.

## Mô-đun / thành viên

- Mô-đun: MOD-xx `<ten>` (thư mục `server/app/modules/mXX_<ten>/`, `client/lib/modules/mXX_<ten>/`)
- Người thực hiện: TVx – Họ tên – MSSV

## Thay đổi

- 

## Kiểm tra trước khi gửi

- [ ] `cd server && venv\Scripts\python -m pytest -q` đạt 100 %
- [ ] `cd client && flutter analyze` không lỗi, `flutter test -j 1` đạt
- [ ] Chỉ sửa trong thư mục mô-đun của mình (phần dùng chung: chỉ thêm dòng import / đăng ký router)
- [ ] Cập nhật `README.md` của mô-đun nếu thêm / đổi API, bảng, quy tắc

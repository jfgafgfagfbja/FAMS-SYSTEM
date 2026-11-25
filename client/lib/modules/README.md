# Client theo mô-đun (MVC)

Mỗi thư mục `mXX_<ten>/` là một mô-đun, cùng mã với server (`server/app/modules/`) và báo cáo (MOD-01…MOD-10):

```
mXX_<ten>/
├── models/        M – lớp dữ liệu (fromJson)
├── controllers/   C – gọi API, giữ trạng thái (ChangeNotifier)
└── views/         V – các trang *_page.dart và widget riêng của mô-đun
```

| Mô-đun | Người phụ trách | Đã chuyển |
|---|---|---|
| `m01_auth/` – Xác thực và tài khoản | TV1 @jfgafgfagfbja | ✅ `controllers/auth_controller.dart`, `views/` (5 trang) |
| `m10_shell/` – Khung giao diện chung | TV1 @jfgafgfagfbja | ✅ `views/home_page.dart` (khung: `lib/core/`, `lib/widgets/`, `router.dart`, `app.dart`) |
| `m02_catalog/`, `m03_training/` | TV2 @nguyenthai9351-code | chưa – đang ở `lib/features/admin/`, `lib/features/schedule/` |
| `m04_learners/`, `m05_faces/` | TV3 @YNCoder205 | chưa – `lib/features/admin/`, `lib/features/student/`, `lib/features/parent/` |
| `m06_attendance/` | TV4 @vuong557 | chưa – `lib/features/lecturer/`, `lib/features/student/`, `lib/features/leave/` |
| `m07_notifications/`, `m08_reports/`, `m09_audit/` | TV5 | chưa – `lib/features/parent/`, `lib/features/lecturer/`, `lib/features/office/`, `lib/features/admin/` |

Danh sách trang của từng người: `docs/nhom/KE_HOACH_NHIEM_VU_MVC_CLOUD.md` mục 3. Lớp dữ liệu hiện vẫn nằm chung trong
`lib/models/models.dart`; mỗi người tách phần của mình sang `models/` của mô-đun và `export` lại trong `models.dart`.
Chạy `flutter analyze` và `flutter test -j 1` (phải sạch) trước khi mở Pull Request.

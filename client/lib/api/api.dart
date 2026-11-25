/// Lop goi API theo module nghiep vu (tuong ung cac nhom endpoint /api/v1/... cua server).
///
/// Moi endpoint duoc khai bao DUNG MOT LAN o day; trang giao dien goi theo ten nghiep vu:
///
///     final api = context.read<ApiClient>();
///     final page = await api.classes.page(query: {'q': q});
///     await api.sessions.close(sessionId);
///
/// ApiClient (core/api_client.dart) lo phan truyen tai: dia chi may chu, token, tu lam moi
/// token, chuan hoa loi. Cac lop o day chi ghep duong dan va tham so, tra ve dung kieu du lieu
/// ma ApiClient tra ve (JSON da giai ma, PageResult, bytes) - trang tu doi sang model.
library;

import '../core/api_client.dart';
import 'attendance_api.dart';
import 'catalog_api.dart';
import 'people_api.dart';
import 'report_api.dart';
import 'training_api.dart';

export 'attendance_api.dart';
export 'catalog_api.dart';
export 'people_api.dart';
export 'report_api.dart';
export 'training_api.dart';

extension FamsApi on ApiClient {
  AuthApi get auth => AuthApi(this);
  UnitsApi get units => UnitsApi(this);
  StaffApi get staff => StaffApi(this);
  LocationsApi get locations => LocationsApi(this);
  RoomsApi get rooms => RoomsApi(this);
  LecturersApi get lecturers => LecturersApi(this);
  ClassesApi get classes => ClassesApi(this);
  SchedulesApi get schedules => SchedulesApi(this);
  StudentsApi get students => StudentsApi(this);
  ParentsApi get parents => ParentsApi(this);
  FacesApi get faces => FacesApi(this);
  SessionsApi get sessions => SessionsApi(this);
  LeaveRequestsApi get leaveRequests => LeaveRequestsApi(this);
  ReportsApi get reports => ReportsApi(this);
  NotificationsApi get notifications => NotificationsApi(this);
  AuditLogsApi get auditLogs => AuditLogsApi(this);
}

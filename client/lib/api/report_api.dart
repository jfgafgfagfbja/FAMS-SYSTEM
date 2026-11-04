/// PH7-PH9: bao cao, thong ke, thong bao, nhat ky he thong.
library;

import 'dart:typed_data';

import '../core/api_client.dart';

class ReportsApi {
  const ReportsApi(this._c);
  final ApiClient _c;

  Future<dynamic> classAttendance(Object classId) => _c.get('/reports/attendance/$classId');
  Future<dynamic> warnings({Map<String, dynamic>? query}) => _c.get('/reports/attendance/warnings', query: query);
  Future<Uint8List> exportExcel({Map<String, dynamic>? query}) => _c.getBytes('/reports/attendance/export', query: query);
  Future<dynamic> overview({Map<String, dynamic>? query}) => _c.get('/reports/overview', query: query);
  Future<dynamic> myAttendance() => _c.get('/reports/my-attendance');
}

class NotificationsApi {
  const NotificationsApi(this._c);
  final ApiClient _c;

  Future<dynamic> list({Map<String, dynamic>? query}) => _c.get('/notifications', query: query);
  Future<dynamic> unreadCount() => _c.get('/notifications/unread-count');
  Future<dynamic> readAll() => _c.post('/notifications/read-all');
  Future<dynamic> read(Object id) => _c.post('/notifications/$id/read');
}

class AuditLogsApi {
  const AuditLogsApi(this._c);
  final ApiClient _c;

  Future<PageResult<Map<String, dynamic>>> page({Map<String, dynamic>? query}) => _c.getPage('/audit-logs', query: query);
}

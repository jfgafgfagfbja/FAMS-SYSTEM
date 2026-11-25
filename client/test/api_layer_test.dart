import 'dart:typed_data';

import 'package:fams_app/api/api.dart';
import 'package:fams_app/core/api_client.dart';
import 'package:fams_app/core/config.dart';
import 'package:fams_app/core/token_storage.dart';
import 'package:flutter_test/flutter_test.dart';

/// Ghi lai (dong tu, duong dan) ma lop API goi xuong ApiClient - khong goi mang.
class _RecordingClient extends ApiClient {
  _RecordingClient() : super(storage: TokenStorage());

  final calls = <String>[];

  @override
  Future<dynamic> get(String path, {Map<String, dynamic>? query}) async => calls.add('GET $path');

  @override
  Future<PageResult<Map<String, dynamic>>> getPage(String path, {Map<String, dynamic>? query}) async {
    calls.add('GET $path');
    return const PageResult([], 0);
  }

  @override
  Future<dynamic> post(String path, {Object? data}) async => calls.add('POST $path');

  @override
  Future<dynamic> patch(String path, {Object? data}) async => calls.add('PATCH $path');

  @override
  Future<dynamic> delete(String path) async => calls.add('DELETE $path');

  @override
  Future<dynamic> postMultipart(String path,
          {Map<String, Object?> fields = const {}, required List<UploadFile> files}) async =>
      calls.add('POST $path');

  @override
  Future<Uint8List> getBytes(String path, {Map<String, dynamic>? query}) async {
    calls.add('GET $path');
    return Uint8List(0);
  }
}

void main() {
  group('AppConfig', () {
    test('dia chi may chu duoc chuan hoa, API luon nam duoi /api/v1', () {
      expect(AppConfig.apiPrefix, '/api/v1');
      expect(AppConfig.normalizeServer(' http://10.0.0.5:8100/ '), 'http://10.0.0.5:8100');
      // Nguoi dung lo nhap kem tien to API (ca dang cu /api) van ra dung dia chi may chu.
      expect(AppConfig.normalizeServer('http://10.0.0.5:8100/api/v1/'), 'http://10.0.0.5:8100');
      expect(AppConfig.normalizeServer('https://fams.example.edu.vn/api'), 'https://fams.example.edu.vn');
      expect(AppConfig.apiBaseUrl('http://10.0.0.5:8100/'), 'http://10.0.0.5:8100/api/v1');
    });

    test('ApiClient tach dia chi may chu va dia chi API', () async {
      final api = ApiClient(storage: TokenStorage());
      expect(api.baseUrl, '${api.serverUrl}/api/v1');
      expect(api.mediaUrl('/evidence/3/a.jpg?exp=1&sig=x'), '${api.serverUrl}/api/v1/evidence/3/a.jpg?exp=1&sig=x');
      expect(api.mediaUrl(null), '');
    });
  });

  test('moi phuong thuc cua lop API goi dung dong tu va duong dan', () async {
    final c = _RecordingClient();
    const files = <UploadFile>[];
    final expected = <Future<dynamic> Function(), String>{
      () => c.auth.me(): 'GET /auth/me',
      () => c.auth.forgotPassword(): 'POST /auth/forgot-password',
      () => c.auth.resetPassword(): 'POST /auth/reset-password',
      () => c.units.list(): 'GET /units',
      () => c.units.update(2): 'PATCH /units/2',
      () => c.staff.delete(3): 'DELETE /staff/3',
      () => c.locations.create(): 'POST /locations',
      () => c.rooms.buildings(): 'GET /rooms/buildings',
      () => c.lecturers.todaySchedules(): 'GET /lecturers/me/today-schedules',
      () => c.classes.page(): 'GET /classes',
      () => c.classes.enroll(1, 9): 'POST /classes/1/enroll/9',
      () => c.classes.unenroll(1, 9): 'DELETE /classes/1/enroll/9',
      () => c.classes.createSchedule(): 'POST /classes/schedules',
      () => c.classes.updateSchedule(4): 'PATCH /classes/schedules/4',
      () => c.schedules.week(): 'GET /schedules/week',
      () => c.students.myAttendance(): 'GET /students/me/attendance',
      () => c.students.attendance(7): 'GET /students/7/attendance',
      () => c.students.consentPolicy(): 'GET /students/consent-policy',
      () => c.students.giveConsent(7): 'POST /students/7/consent',
      () => c.students.withdrawConsent(7): 'POST /students/7/consent/withdraw',
      () => c.parents.unlinkChild(5, 7): 'DELETE /parents/5/children/7',
      () => c.parents.myPreferences(): 'GET /parents/me/preferences',
      () => c.parents.childAttendance(7): 'GET /parents/me/children/7/attendance',
      () => c.faces.enroll(7, files: files): 'POST /faces/enroll/7',
      () => c.faces.reject(11): 'PATCH /faces/11/reject',
      () => c.faces.acknowledge(11): 'POST /faces/mine/11/acknowledge',
      () => c.leaveRequests.list(): 'GET /leave-requests',
      () => c.leaveRequests.create(): 'POST /leave-requests',
      () => c.leaveRequests.approve(5): 'PATCH /leave-requests/5/approve',
      () => c.leaveRequests.reject(5): 'PATCH /leave-requests/5/reject',
      () => c.leaveRequests.acknowledge(5): 'POST /leave-requests/5/acknowledge',
      () => c.sessions.open(): 'POST /sessions',
      () => c.sessions.close(8): 'PATCH /sessions/8/close',
      () => c.sessions.recognize(8, files: files): 'POST /sessions/8/recognize',
      () => c.sessions.selfCheckin(8, files: files): 'POST /sessions/8/self-checkin',
      () => c.sessions.updateRecord(8, 20): 'PATCH /sessions/8/records/20',
      () => c.sessions.recordAudits(8, 20): 'GET /sessions/8/records/20/audits',
      () => c.reports.classAttendance(1): 'GET /reports/attendance/1',
      () => c.reports.warnings(): 'GET /reports/attendance/warnings',
      () => c.reports.exportExcel(): 'GET /reports/attendance/export',
      () => c.reports.overview(): 'GET /reports/overview',
      () => c.notifications.read(6): 'POST /notifications/6/read',
      () => c.notifications.readAll(): 'POST /notifications/read-all',
      () => c.auditLogs.page(): 'GET /audit-logs',
    };
    for (final entry in expected.entries) {
      c.calls.clear();
      await entry.key();
      expect(c.calls, [entry.value]);
    }
  });
}

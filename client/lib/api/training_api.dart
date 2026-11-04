/// PH3: giang vien, lop hoc phan, ghi danh, lich hoc.
library;

import '../core/api_client.dart';

class LecturersApi {
  const LecturersApi(this._c);
  final ApiClient _c;

  Future<PageResult<Map<String, dynamic>>> page({Map<String, dynamic>? query}) => _c.getPage('/lecturers', query: query);
  Future<dynamic> create({Object? data}) => _c.post('/lecturers', data: data);
  Future<dynamic> update(Object id, {Object? data}) => _c.patch('/lecturers/$id', data: data);
  Future<dynamic> delete(Object id) => _c.delete('/lecturers/$id');
  Future<dynamic> todaySchedules() => _c.get('/lecturers/me/today-schedules');
}

class ClassesApi {
  const ClassesApi(this._c);
  final ApiClient _c;

  Future<PageResult<Map<String, dynamic>>> page({Map<String, dynamic>? query}) => _c.getPage('/classes', query: query);
  Future<dynamic> get(Object id) => _c.get('/classes/$id');
  Future<dynamic> create({Object? data}) => _c.post('/classes', data: data);
  Future<dynamic> update(Object id, {Object? data}) => _c.patch('/classes/$id', data: data);
  Future<dynamic> delete(Object id) => _c.delete('/classes/$id');
  Future<dynamic> students(Object id) => _c.get('/classes/$id/students');
  Future<dynamic> schedules(Object id) => _c.get('/classes/$id/schedules');
  Future<dynamic> enroll(Object classId, Object studentId) => _c.post('/classes/$classId/enroll/$studentId');
  Future<dynamic> unenroll(Object classId, Object studentId) => _c.delete('/classes/$classId/enroll/$studentId');
  Future<dynamic> createSchedule({Object? data}) => _c.post('/classes/schedules', data: data);
  Future<dynamic> updateSchedule(Object id, {Object? data}) => _c.patch('/classes/schedules/$id', data: data);
  Future<dynamic> deleteSchedule(Object id) => _c.delete('/classes/schedules/$id');
}

class SchedulesApi {
  const SchedulesApi(this._c);
  final ApiClient _c;

  Future<PageResult<Map<String, dynamic>>> page({Map<String, dynamic>? query}) => _c.getPage('/schedules', query: query);
  Future<dynamic> week({Map<String, dynamic>? query}) => _c.get('/schedules/week', query: query);
}

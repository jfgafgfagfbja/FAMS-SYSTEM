/// PH6: phien diem danh va ghi nhan diem danh.
library;

import '../core/api_client.dart';

class SessionsApi {
  const SessionsApi(this._c);
  final ApiClient _c;

  Future<dynamic> list({Map<String, dynamic>? query}) => _c.get('/sessions', query: query);
  Future<dynamic> get(Object id) => _c.get('/sessions/$id');
  Future<dynamic> open({Object? data}) => _c.post('/sessions', data: data);
  Future<dynamic> close(Object id) => _c.patch('/sessions/$id/close');
  Future<dynamic> checkinInfo(Object id) => _c.get('/sessions/$id/checkin-info');
  Future<dynamic> roster(Object id) => _c.get('/sessions/$id/roster');
  Future<dynamic> recognize(Object id, {Map<String, Object?> fields = const {}, required List<UploadFile> files}) =>
      _c.postMultipart('/sessions/$id/recognize', fields: fields, files: files);
  Future<dynamic> selfCheckin(Object id, {Map<String, Object?> fields = const {}, required List<UploadFile> files}) =>
      _c.postMultipart('/sessions/$id/self-checkin', fields: fields, files: files);
  Future<dynamic> manual(Object id, {Object? data}) => _c.post('/sessions/$id/manual', data: data);
  Future<dynamic> records(Object id) => _c.get('/sessions/$id/records');
  Future<dynamic> updateRecord(Object sessionId, Object recordId, {Object? data}) =>
      _c.patch('/sessions/$sessionId/records/$recordId', data: data);
  Future<dynamic> recordAudits(Object sessionId, Object recordId) =>
      _c.get('/sessions/$sessionId/records/$recordId/audits');
}


/// PH6: don xin phep vang - SV nop, GV lop / Lanh dao Khoa duyet, SV xac nhan ket qua.
class LeaveRequestsApi {
  const LeaveRequestsApi(this._c);
  final ApiClient _c;

  Future<dynamic> list({Map<String, dynamic>? query}) => _c.get('/leave-requests', query: query);
  Future<dynamic> create({Object? data}) => _c.post('/leave-requests', data: data);
  Future<dynamic> approve(Object id, {Object? data}) => _c.patch('/leave-requests/$id/approve', data: data);
  Future<dynamic> reject(Object id, {Object? data}) => _c.patch('/leave-requests/$id/reject', data: data);
  Future<dynamic> acknowledge(Object id) => _c.post('/leave-requests/$id/acknowledge');
}

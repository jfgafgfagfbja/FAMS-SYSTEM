/// PH6: phien diem danh va ghi nhan diem danh.
library;

import '../core/api_client.dart';

class SessionsApi {
  const SessionsApi(this._c);
  final ApiClient _c;

  Future<dynamic> list({Map<String, dynamic>? query}) => _c.get('/sessions', query: query);
  Future<dynamic> get(Object id) => _c.get('/sessions/$id');
  Future<dynamic> open({Object? data}) => _c.post('/sessions', data: data);
  Future<dynamic> update(Object id, {Object? data}) => _c.patch('/sessions/$id', data: data);
  Future<dynamic> close(Object id) => _c.patch('/sessions/$id/close');
  Future<dynamic> checkinInfo(Object id) => _c.get('/sessions/$id/checkin-info');
  Future<dynamic> checkinCode(Object id) => _c.get('/sessions/$id/checkin-code');
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

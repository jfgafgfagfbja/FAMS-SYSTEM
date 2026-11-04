/// PH4-PH5: sinh vien, dong y sinh trac, phu huynh, du lieu khuon mat.
library;

import '../core/api_client.dart';

class StudentsApi {
  const StudentsApi(this._c);
  final ApiClient _c;

  Future<PageResult<Map<String, dynamic>>> page({Map<String, dynamic>? query}) => _c.getPage('/students', query: query);
  Future<dynamic> get(Object id) => _c.get('/students/$id');
  Future<dynamic> create({Object? data}) => _c.post('/students', data: data);
  Future<dynamic> update(Object id, {Object? data}) => _c.patch('/students/$id', data: data);
  Future<dynamic> delete(Object id) => _c.delete('/students/$id');
  Future<dynamic> attendance(Object id, {Map<String, dynamic>? query}) => _c.get('/students/$id/attendance', query: query);
  Future<dynamic> myAttendance({Map<String, dynamic>? query}) => _c.get('/students/me/attendance', query: query);
  Future<dynamic> consentPolicy() => _c.get('/students/consent-policy');
  Future<dynamic> giveConsent(Object id, {Object? data}) => _c.post('/students/$id/consent', data: data);
  Future<dynamic> withdrawConsent(Object id) => _c.post('/students/$id/consent/withdraw');
}

class ParentsApi {
  const ParentsApi(this._c);
  final ApiClient _c;

  Future<PageResult<Map<String, dynamic>>> page({Map<String, dynamic>? query}) => _c.getPage('/parents', query: query);
  Future<dynamic> create({Object? data}) => _c.post('/parents', data: data);
  Future<dynamic> update(Object id, {Object? data}) => _c.patch('/parents/$id', data: data);
  Future<dynamic> delete(Object id) => _c.delete('/parents/$id');
  Future<dynamic> children(Object parentId) => _c.get('/parents/$parentId/children');
  Future<dynamic> linkChild(Object parentId, {Object? data}) => _c.post('/parents/$parentId/children', data: data);
  Future<dynamic> unlinkChild(Object parentId, Object studentId) =>
      _c.delete('/parents/$parentId/children/$studentId');
  Future<dynamic> myPreferences() => _c.get('/parents/me/preferences');
  Future<dynamic> updateMyPreferences({Object? data}) => _c.patch('/parents/me/preferences', data: data);
  Future<dynamic> myChildren() => _c.get('/parents/me/children');
  Future<dynamic> childAttendance(Object studentId, {Map<String, dynamic>? query}) =>
      _c.get('/parents/me/children/$studentId/attendance', query: query);
}

class FacesApi {
  const FacesApi(this._c);
  final ApiClient _c;

  Future<dynamic> enroll(Object studentId,
          {Map<String, Object?> fields = const {}, required List<UploadFile> files}) =>
      _c.postMultipart('/faces/enroll/$studentId', fields: fields, files: files);
  Future<dynamic> mine() => _c.get('/faces/mine');
  Future<dynamic> deleteMine() => _c.delete('/faces/mine');
  Future<dynamic> pending() => _c.get('/faces/pending');
  Future<dynamic> approve(Object id) => _c.patch('/faces/$id/approve');
  Future<dynamic> reject(Object id, {Object? data}) => _c.patch('/faces/$id/reject', data: data);
}

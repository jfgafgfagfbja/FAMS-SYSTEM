/// PH1-PH2: xac thuc va danh muc he thong (don vi, can bo, dia diem, phong hoc).
library;

import '../core/api_client.dart';

/// Dang nhap, dang xuat, doi mat khau (luu token) nam o ApiClient; o day la cac endpoint con lai.
class AuthApi {
  const AuthApi(this._c);
  final ApiClient _c;

  Future<dynamic> me() => _c.get('/auth/me');
  Future<dynamic> forgotPassword({Object? data}) => _c.post('/auth/forgot-password', data: data);
  Future<dynamic> resetPassword({Object? data}) => _c.post('/auth/reset-password', data: data);
}

class UnitsApi {
  const UnitsApi(this._c);
  final ApiClient _c;

  Future<dynamic> list({Map<String, dynamic>? query}) => _c.get('/units', query: query);
  Future<dynamic> create({Object? data}) => _c.post('/units', data: data);
  Future<dynamic> update(Object id, {Object? data}) => _c.patch('/units/$id', data: data);
  Future<dynamic> delete(Object id) => _c.delete('/units/$id');
}

class StaffApi {
  const StaffApi(this._c);
  final ApiClient _c;

  Future<PageResult<Map<String, dynamic>>> page({Map<String, dynamic>? query}) => _c.getPage('/staff', query: query);
  Future<dynamic> create({Object? data}) => _c.post('/staff', data: data);
  Future<dynamic> update(Object id, {Object? data}) => _c.patch('/staff/$id', data: data);
  Future<dynamic> delete(Object id) => _c.delete('/staff/$id');
}

class LocationsApi {
  const LocationsApi(this._c);
  final ApiClient _c;

  Future<dynamic> list({Map<String, dynamic>? query}) => _c.get('/locations', query: query);
  Future<dynamic> create({Object? data}) => _c.post('/locations', data: data);
  Future<dynamic> update(Object id, {Object? data}) => _c.patch('/locations/$id', data: data);
  Future<dynamic> delete(Object id) => _c.delete('/locations/$id');
}

class RoomsApi {
  const RoomsApi(this._c);
  final ApiClient _c;

  Future<dynamic> list({Map<String, dynamic>? query}) => _c.get('/rooms', query: query);
  Future<dynamic> buildings() => _c.get('/rooms/buildings');
  Future<dynamic> create({Object? data}) => _c.post('/rooms', data: data);
  Future<dynamic> update(Object id, {Object? data}) => _c.patch('/rooms/$id', data: data);
  Future<dynamic> delete(Object id) => _c.delete('/rooms/$id');
}

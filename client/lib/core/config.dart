import 'package:flutter/foundation.dart';

/// Cau hinh dia chi may chu.
///
/// Client chi can biet DIA CHI MAY CHU (vd http://192.168.1.10:8100); duong dan API luon la
/// [apiPrefix] (/api/v1) ghep phia sau - doi phien ban API chi sua mot cho nay.
///
/// Thu tu uu tien: dia chi nguoi dung tu nhap o man hinh dang nhap (luu trong TokenStorage)
/// > --dart-define=API_BASE_URL=... > mac dinh theo nen tang:
/// - Web (build production, phuc vu qua nginx): cung origin voi trang web.
/// - Android emulator: 10.0.2.2 tro ve may dang chay server.
/// - iOS simulator / khac: localhost.
class AppConfig {
  static const apiPrefix = '/api/v1';
  static const _definedUrl = String.fromEnvironment('API_BASE_URL');

  /// Dia chi may chu mac dinh (khong kem /api/v1).
  static String defaultServerUrl() {
    if (_definedUrl.isNotEmpty) return normalizeServer(_definedUrl);
    if (kIsWeb) return normalizeServer('');
    if (defaultTargetPlatform == TargetPlatform.android) return 'http://10.0.2.2:8100';
    return 'http://localhost:8100';
  }

  /// Chuan hoa dia chi may chu: bo "/" cuoi va bo tien to API neu nguoi dung lo nhap kem
  /// (/api/v1, hoac /api cua cach cau hinh cu); tren web, chuoi rong hoac duong dan tuong doi
  /// duoc doi thanh URL day du theo origin hien tai de Dio va Image.network ghep cung mot cach.
  static String normalizeServer(String url) {
    var value = url.trim();
    if (kIsWeb && (value.isEmpty || value.startsWith('/'))) {
      value = Uri.base.resolve(value.isEmpty ? '/' : value).toString();
    }
    value = value.replaceAll(RegExp(r'/+$'), '');
    for (final suffix in const [apiPrefix, '/api']) {
      if (value.endsWith(suffix)) {
        value = value.substring(0, value.length - suffix.length);
        break;
      }
    }
    return value.replaceAll(RegExp(r'/+$'), '');
  }

  /// Dia chi goc cua API = may chu + /api/v1.
  static String apiBaseUrl(String serverUrl) => '${normalizeServer(serverUrl)}$apiPrefix';
}

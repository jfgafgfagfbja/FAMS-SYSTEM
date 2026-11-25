import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/roles.dart';
import '../models/models.dart';
import '../api/api.dart';

/// Trang xu ly canh bao khi bam chuong, theo vai tro (null = khong hien chuong).
String? alertTargetFor(String role) => switch (role) {
      Roles.affairs => '/face-review',
      Roles.lecturer || Roles.facultyLeader => '/leave-requests',
      Roles.admin || Roles.training || Roles.faculty => '/reports',
      Roles.student || Roles.parent => '/notifications',
      Roles.board => '/',
      _ => null,
    };

String alertLabelFor(String role) => switch (role) {
      Roles.affairs => 'khuôn mặt chờ duyệt',
      Roles.lecturer || Roles.facultyLeader => 'đơn xin phép chờ duyệt',
      Roles.student || Roles.parent => 'thông báo mới',
      _ => 'sinh viên vượt ngưỡng vắng',
    };

/// So muc can chu y, lay tu du lieu that: P.CTSV -> khuon mat cho duyet; GV / Lanh dao Khoa ->
/// don xin phep cho duyet trong pham vi; admin/P.DT/VP Khoa/Ban -> SV vuot nguong vang;
/// SV, phu huynh -> thong bao chua doc (ket qua duyet, canh bao, diem danh cua con).
Future<int> countAlerts(ApiClient api, String role) async {
  switch (role) {
    case Roles.affairs:
      return (await api.faces.pending() as List<dynamic>).length;
    case Roles.lecturer || Roles.facultyLeader:
      return (await api.leaveRequests.list(query: {'status': 'pending'}) as List<dynamic>).length;
    case Roles.admin || Roles.training || Roles.faculty || Roles.board:
      final overview = Overview.fromJson(await api.reports.overview() as Json);
      return overview.totals.warnedStudents;
    case Roles.student || Roles.parent:
      final data = await api.notifications.unreadCount() as Json;
      return data['count'] as int;
    default:
      return 0;
  }
}

/// Chuong canh bao tren thanh tieu de, tu cap nhat moi 2 phut.
class NotificationBell extends StatefulWidget {
  const NotificationBell({super.key, required this.role});

  final String role;

  @override
  State<NotificationBell> createState() => _NotificationBellState();
}

class _NotificationBellState extends State<NotificationBell> {
  static const _refreshEvery = Duration(minutes: 2);
  Timer? _timer;
  int _count = 0;

  @override
  void initState() {
    super.initState();
    _refresh();
    _timer = Timer.periodic(_refreshEvery, (_) => _refresh());
  }

  @override
  void didUpdateWidget(covariant NotificationBell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.role != widget.role) _refresh();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final count = await countAlerts(context.read<ApiClient>(), widget.role);
      if (mounted) setState(() => _count = count);
    } catch (_) {
      // Loi mang/het phien: giu so cu, lan sau thu lai (khong lam phien nguoi dung).
    }
  }

  @override
  Widget build(BuildContext context) {
    final target = alertTargetFor(widget.role);
    if (target == null) return const SizedBox.shrink();
    return IconButton(
      tooltip: _count > 0 ? '$_count ${alertLabelFor(widget.role)}' : 'Không có cảnh báo mới',
      onPressed: () {
        context.go(target);
        _refresh();
      },
      icon: Badge(
        isLabelVisible: _count > 0,
        label: Text(_count > 99 ? '99+' : '$_count'),
        child: Icon(_count > 0 ? Icons.notifications_active_outlined : Icons.notifications_outlined),
      ),
    );
  }
}

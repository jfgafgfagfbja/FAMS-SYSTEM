import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/api.dart';
import '../../core/api_client.dart';
import '../../modules/m01_auth/controllers/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';

/// Don xin phep vang.
/// - Sinh vien: nop don cho mot buoi hoc, xem ket qua, XAC NHAN da nhan ket qua.
/// - Giang vien lop / Lanh dao Khoa: duyet hoac tu choi kem ly do khong hop le.
/// - Quan tri vien, P.CTSV: chi xem.
class LeaveRequestsPage extends StatefulWidget {
  const LeaveRequestsPage({super.key});

  @override
  State<LeaveRequestsPage> createState() => _LeaveRequestsPageState();
}

class _LeaveRequestsPageState extends State<LeaveRequestsPage> {
  String? _status; // null = tat ca

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    final role = context.watch<AuthController>().role;
    final perms = Perms(role);
    return AsyncLoader<List<LeaveRequest>>(
      loadKey: _status,
      load: () async => (await api.leaveRequests.list(query: {if (_status != null) 'status': _status}) as List<dynamic>)
          .map((e) => LeaveRequest.fromJson(e as Json))
          .toList(),
      builder: (context, items, reload) => PageBody(
        maxWidth: 860,
        onRefresh: reload,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              for (final (value, label) in const [(null, 'Tất cả'), ('pending', 'Chờ duyệt'), ('approved', 'Đã duyệt'), ('rejected', 'Từ chối')])
                ChoiceChip(label: Text(label), selected: _status == value, onSelected: (_) => setState(() => _status = value)),
              if (perms.requestLeave)
                FilledButton.icon(
                  onPressed: () async {
                    if (await _newRequest(context)) reload();
                  },
                  icon: const Icon(Icons.post_add),
                  label: const Text('Nộp đơn xin phép'),
                ),
            ],
          ),
          const SizedBox(height: 12),
          if (items.isEmpty)
            EmptyView(
              icon: Icons.event_busy_outlined,
              message: perms.requestLeave
                  ? 'Chưa có đơn nào. Bấm "Nộp đơn xin phép" khi bạn cần vắng một buổi học.'
                  : 'Không có đơn xin phép nào.',
            )
          else
            for (final item in items) _LeaveCard(item: item, perms: perms, reload: reload),
        ],
      ),
    );
  }
}

class _LeaveCard extends StatelessWidget {
  const _LeaveCard({required this.item, required this.perms, required this.reload});

  final LeaveRequest item;
  final Perms perms;
  final VoidCallback reload;

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    final (label, color) = switch (item.status) {
      'approved' => ('Đã duyệt', AppColors.success),
      'rejected' => ('Không hợp lệ', AppColors.danger),
      _ => ('Chờ duyệt', AppColors.warning),
    };
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('${item.classCode} — ${item.subjectName}',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                ),
                StatusChip(label: label, color: color),
              ],
            ),
            const SizedBox(height: 6),
            InfoLine(icon: Icons.event, text: '${fmtDate(item.absenceDate)} · ${hhmm(item.startTime)}–${hhmm(item.endTime)} · ${roomLabel(item.room)}'),
            if (!perms.requestLeave) InfoLine(icon: Icons.person_outline, text: '${item.fullName} (${item.studentCode})'),
            InfoLine(icon: Icons.notes, text: 'Lý do xin phép: ${item.reason}'),
            if (item.status != 'pending')
              InfoLine(
                icon: item.status == 'approved' ? Icons.verified_outlined : Icons.report_gmailerrorred_outlined,
                text: [
                  '${item.status == 'approved' ? 'Duyệt' : 'Từ chối'} bởi ${item.reviewerName ?? '—'} lúc ${fmtDateTime(item.reviewedAt)}',
                  if (item.reviewNote.isNotEmpty) item.status == 'rejected' ? 'Lý do không hợp lệ: ${item.reviewNote}' : 'Ghi chú: ${item.reviewNote}',
                ].join(' · '),
              ),
            if (item.attendanceStatus != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Row(children: [
                  const Text('Điểm danh buổi này: '),
                  StatusChip.attendance(item.attendanceStatus),
                ]),
              ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (perms.reviewLeaves && item.status == 'pending') ...[
                  FilledButton.icon(
                    onPressed: () async {
                      if (await runAction(context, () => api.leaveRequests.approve(item.id, data: {'note': ''}),
                          success: 'Đã duyệt — kết quả đã gửi cho sinh viên')) {
                        reload();
                      }
                    },
                    icon: const Icon(Icons.check),
                    label: const Text('Duyệt'),
                  ),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(foregroundColor: AppColors.danger),
                    onPressed: () async {
                      final reason = await promptText(context,
                          title: 'Từ chối đơn xin phép', label: 'Lý do không hợp lệ (bắt buộc)', confirmLabel: 'Từ chối');
                      if (reason == null || !context.mounted) return;
                      if (await runAction(context, () => api.leaveRequests.reject(item.id, data: {'reason': reason}),
                          success: 'Đã từ chối — kết quả đã gửi cho sinh viên')) {
                        reload();
                      }
                    },
                    icon: const Icon(Icons.close),
                    label: const Text('Từ chối'),
                  ),
                ],
                if (perms.requestLeave && item.status != 'pending')
                  item.studentAckAt == null
                      ? FilledButton.tonalIcon(
                          onPressed: () async {
                            if (await runAction(context, () => api.leaveRequests.acknowledge(item.id),
                                success: 'Đã xác nhận nhận kết quả')) {
                              reload();
                            }
                          },
                          icon: const Icon(Icons.mark_email_read_outlined),
                          label: const Text('Xác nhận đã nhận kết quả'),
                        )
                      : StatusChip(
                          icon: Icons.done_all,
                          label: 'Đã xác nhận lúc ${fmtDateTime(item.studentAckAt)}',
                          color: AppColors.neutral,
                        ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// SV chon ngay -> chon buoi hoc cua ngay do (lay tu lich tuan) -> nhap ly do.
Future<bool> _newRequest(BuildContext context) async {
  final api = context.read<ApiClient>();
  final now = DateTime.now();
  final day = await showDatePicker(
    context: context,
    initialDate: now,
    firstDate: now.subtract(const Duration(days: 7)),
    lastDate: now.add(const Duration(days: 180)),
    helpText: 'Chọn ngày vắng',
  );
  if (day == null || !context.mounted) return false;
  final slots = (await api.schedules.week(query: {'start': isoDate(day)}) as List<dynamic>)
      .map((e) => WeekSlot.fromJson(e as Json))
      .where((s) => isoDate(s.date) == isoDate(day))
      .toList();
  if (!context.mounted) return false;
  if (slots.isEmpty) {
    showSnack(context, 'Ngày ${fmtDate(day)} bạn không có buổi học nào', error: true);
    return false;
  }
  WeekSlot chosen = slots.first;
  final reason = TextEditingController();
  final ok = await showDialog<bool>(
    context: context,
    builder: (context) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        title: Text('Xin phép vắng ngày ${fmtDate(day)}'),
        content: SizedBox(
          width: 440,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<WeekSlot>(
                initialValue: chosen,
                decoration: const InputDecoration(labelText: 'Buổi học'),
                items: [
                  for (final s in slots)
                    DropdownMenuItem(value: s, child: Text('${s.classCode} · ${hhmm(s.startTime)}–${hhmm(s.endTime)}')),
                ],
                onChanged: (s) => setState(() => chosen = s ?? chosen),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: reason,
                maxLines: 3,
                minLines: 2,
                decoration: const InputDecoration(labelText: 'Lý do xin phép (bắt buộc)'),
                onChanged: (_) => setState(() {}),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Hủy')),
          FilledButton(
            onPressed: reason.text.trim().isEmpty ? null : () => Navigator.pop(context, true),
            child: const Text('Nộp đơn'),
          ),
        ],
      ),
    ),
  );
  if (ok != true || !context.mounted) return false;
  return runAction(
    context,
    () => api.leaveRequests.create(data: {
      'schedule_id': chosen.scheduleId,
      'absence_date': isoDate(day),
      'reason': reason.text.trim(),
    }),
    success: 'Đã nộp đơn — giảng viên lớp sẽ nhận được thông báo',
  );
}

"""Trang CHUAN HOA CSDL (den dang chuan 4 - 4NF) cua FAMS -> docs/so-do-luong-du-lieu-va-csdl/chuan_hoa_csdl.html.

Trinh bay dung 3 buoc:
  1. Nhom chung  : gom moi thuoc tinh cua he thong vao MOT bang (quan he pho quat U) -> chi ra di thuong.
  2. Tu duy tach bang: xac dinh thuc the, khoa, phu thuoc ham (PTH), phu thuoc da tri (PTĐT).
  3. Phan ra thong tin: 1NF -> 2NF -> 3NF -> BCNF -> 4NF, moi buoc mot vi du that cua FAMS.
Danh sach thuoc tinh, khoa chinh, khoa ung vien (UNIQUE), khoa ngoai lay TU DONG tu server/app/db/models.py;
phan lap luan (PTH nghiep vu, vi du, ket luan) viet tay o day. Goi tu gen_phan_ra.py (khong chay rieng).
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(TOOLS))

from sqlalchemy import UniqueConstraint  # noqa: E402

from app.db import models  # noqa: E402,F401
from app.db.database import Base  # noqa: E402
from so_do_data import GROUPS, STORES, TABLES  # noqa: E402

esc = html.escape
META = {t.name: t for t in Base.metadata.sorted_tables}
ORDER = [name for _g, _c, names in GROUPS for name in names]
GROUP_OF = {name: (g, c) for g, c, names in GROUPS for name in names}
STORE_OF = {name: code for code, _n, names in STORES for name in names}

# PTH nghiep vu "dang chu y" cua tung bang (ngoai PTH khoa -> moi thuoc tinh), va ghi chu chuan hoa.
NOTES = {
    "users": "role không suy ra được hoàn toàn từ bảng khác (Lãnh đạo Khoa / VP Khoa cùng loại đơn vị) nên là thuộc tính "
             "của chính tài khoản. Hai khóa ứng viên: id, email.",
    "staff": "Một tài khoản cán bộ thuộc đúng một đơn vị (user_id là khóa ứng viên).",
    "students": "consent_recorded_by là email chụp lại tại thời điểm ghi nhận (dữ kiện lịch sử), không phải bản sao của "
                "users.email hiện tại ⇒ không dư thừa. Khóa ứng viên: id, student_code.",
    "lecturers": "faculty_id của giảng viên độc lập với faculty_id của lớp (GV có thể dạy lớp Khoa khác) ⇒ không có PTH bắc cầu.",
    "classes": "Tên giảng viên KHÔNG lưu ở đây (chỉ lecturer_id) — tránh PTH bắc cầu id → lecturer_id → tên GV (3NF).",
    "enrollments": "Bảng tách ra ở bước 4NF: SV →→ lớp (đa trị, độc lập với SV →→ phụ huynh).",
    "schedules": "Đã sửa trong đợt này: trước kia cột room luôn chép lại mã phòng khi đã chọn room_id "
                 "(id → room_id → mã phòng: PTH bắc cầu, vi phạm 3NF). Nay room chỉ lưu tên phòng tự nhập khi room_id rỗng.",
    "rooms": "Tọa độ riêng của phòng (latitude, longitude, radius_m) là thuộc tính của phòng; tọa độ khu vực nằm ở locations "
             "— không chép lại.",
    "attendance_sessions": "Không lưu class_id / giờ học (suy ra qua schedule_id) — tránh PTH bắc cầu. Đã bỏ cột require_qr.",
    "attendance_records": "Khóa ứng viên (session_id, student_id). Không lưu tên SV / mã lớp (PTH bộ phận: chỉ phụ thuộc "
                          "student_id hoặc session_id ⇒ vi phạm 2NF nếu để ở đây).",
    "attendance_audits": "Mỗi lần sửa là một sự kiện riêng: (record_id, changed_at) không phải khóa vì có thể sửa nhiều lần "
                         "trong cùng giây ⇒ dùng id.",
    "face_embeddings": "Vector 512 chiều là MỘT giá trị nguyên tố của miền VECTOR (pgvector) — hệ thống không truy cập từng "
                       "phần tử riêng ⇒ thỏa 1NF. reviewed_by / student_ack_at thêm trong đợt này.",
    "parents": "Tùy chọn nhận thông báo là thuộc tính của phụ huynh.",
    "parent_students": "Bảng tách ra ở bước 4NF: SV →→ phụ huynh (đa trị, độc lập với SV →→ lớp).",
    "notifications": "title / body là nội dung đã gửi (bản chụp tại thời điểm gửi), không tính lại từ dữ liệu hiện tại ⇒ "
                     "không dư thừa.",
    "audit_logs": "actor_email, actor_role, target_label là bản chụp lịch sử (vẫn đọc được khi tài khoản / đối tượng đã bị "
                  "xóa) — dữ kiện của sự kiện, không phải bản sao dữ liệu hiện tại.",
    "leave_requests": "Bảng mới trong đợt này. Khóa ứng viên (student_id, schedule_id, absence_date): mỗi SV một đơn cho "
                      "một buổi. Không lưu tên lớp / giờ học (suy ra qua schedule_id).",
    "refresh_tokens": "Chỉ lưu SHA-256 của token; token_hash là khóa ứng viên.",
    "revoked_tokens": "jti là khóa ứng viên.",
    "password_resets": "Mỗi yêu cầu OTP là một dòng; chỉ lưu bản băm.",
    "units": "code là khóa ứng viên.",
    "locations": "code là khóa ứng viên.",
}


def candidate_keys(table) -> list[list[str]]:
    keys = [[c.name for c in table.primary_key.columns]]
    for c in table.columns:
        if c.unique and [c.name] not in keys:
            keys.append([c.name])
    for con in table.constraints:
        if isinstance(con, UniqueConstraint):
            cols = [c.name for c in con.columns]
            if cols not in keys:
                keys.append(cols)
    return keys


def fk_text(table) -> list[str]:
    out = []
    for c in table.columns:
        for fk in c.foreign_keys:
            out.append(f"{c.name} → {fk.column.table.name}.{fk.column.name}")
    return out


def short(table: str, col: str) -> str:
    desc = TABLES[table]["cols"].get(col, col)
    desc = desc.split(" (")[0].split(",")[0].split(" — ")[0]
    return desc[:34]


# ----------------------------------------------------------------------------- noi dung viet tay
STEP1_ROWS = [
    # mot dong = mot SV o mot buoi hoc, gop moi thong tin lien quan (vi du minh hoa)
    ["SV0001", "Tran Thi Sinh", "sv01@…", "CNTT", "Lê Văn Bố", "0905…", "INT3306.1", "Phát triển Web", "GV01",
     "Nguyen Van Giang", "Thứ 2", "07:00–09:00", "E2-101", "16.03, 108.22", "05/01/2026", "present", "selfie", "—"],
    ["SV0001", "Tran Thi Sinh", "sv01@…", "CNTT", "Nguyễn Thị Mẹ", "0912…", "INT3306.1", "Phát triển Web", "GV01",
     "Nguyen Van Giang", "Thứ 2", "07:00–09:00", "E2-101", "16.03, 108.22", "05/01/2026", "present", "selfie", "—"],
    ["SV0001", "Tran Thi Sinh", "sv01@…", "CNTT", "Lê Văn Bố", "0905…", "INT3306.1", "Phát triển Web", "GV01",
     "Nguyen Van Giang", "Thứ 2", "07:00–09:00", "E2-101", "16.03, 108.22", "12/01/2026", "excused", "—", "Ốm, có giấy"],
    ["SV0002", "Le Van Vien", "sv02@…", "CNTT", "—", "—", "INT3306.1", "Phát triển Web", "GV01",
     "Nguyen Van Giang", "Thứ 2", "07:00–09:00", "E2-101", "16.03, 108.22", "05/01/2026", "absent", "—", "—"],
]
STEP1_HEAD = ["MSSV", "Họ tên SV", "Email SV", "Khoa SV", "Phụ huynh", "SĐT PH", "Mã lớp", "Môn", "Mã GV", "Tên GV",
              "Thứ", "Giờ", "Phòng", "Tọa độ phòng", "Ngày buổi", "Trạng thái", "Nguồn", "Đơn xin phép"]

ANOMALIES = [
    ("Dư thừa", "Tên môn, tên GV, giờ học, phòng, tọa độ… lặp lại ở MỌI dòng của MỌI SV ở MỌI buổi; một SV có 2 phụ huynh "
                "thì mọi kết quả điểm danh của SV đó bị nhân đôi (dòng 1 và 2)."),
    ("Dị thường khi thêm", "Không thêm được phòng học, giảng viên hay lớp mới khi chưa có sinh viên nào được điểm danh "
                           "(thiếu giá trị khóa của bảng gộp)."),
    ("Dị thường khi sửa", "Đổi tên GV / giờ học / mã phòng phải sửa ở hàng nghìn dòng; sót một dòng là dữ liệu mâu thuẫn."),
    ("Dị thường khi xóa", "Xóa dòng điểm danh cuối cùng của một lớp làm mất luôn thông tin lớp, GV, lịch học; gỡ liên kết "
                          "phụ huynh có thể làm mất kết quả điểm danh."),
]

ENTITIES = [
    ("Người dùng", "users", "id (hoặc email)"), ("Đơn vị", "units", "id (hoặc code)"), ("Cán bộ", "staff", "id (hoặc user_id)"),
    ("Sinh viên", "students", "id (hoặc student_code)"), ("Giảng viên", "lecturers", "id (hoặc lecturer_code)"),
    ("Phụ huynh", "parents", "id"), ("Lớp học phần", "classes", "id (hoặc class_code)"), ("Địa điểm", "locations", "id (hoặc code)"),
    ("Phòng học", "rooms", "id (hoặc code)"), ("Lịch học", "schedules", "id"),
    ("Phiên điểm danh", "attendance_sessions", "id (hoặc schedule_id + session_date)"),
    ("Kết quả điểm danh", "attendance_records", "id (hoặc session_id + student_id)"),
    ("Đơn xin phép vắng", "leave_requests", "id (hoặc student_id + schedule_id + absence_date)"),
    ("Vector khuôn mặt", "face_embeddings", "id"), ("Thông báo", "notifications", "id"),
    ("Lịch sử sửa điểm danh", "attendance_audits", "id"), ("Nhật ký hệ thống", "audit_logs", "id"),
    ("Token / OTP", "refresh_tokens, revoked_tokens, password_resets", "id (hoặc token_hash / jti)"),
]

FDS = [
    "MaSV → MSSV, HọTênSV, EmailSV, Ngành, Khóa, MaKhoaSV, ĐồngÝSinhTrắc…",
    "MaGV → MãGV, HọTênGV, BộMôn, MaKhoaGV",
    "MaLớp → MãLớp, TênMôn, HọcKỳ, MaGV, MaKhoaLớp",
    "MaPhòng → MãPhòng, TênPhòng, TòaNhà, TọaĐộPhòng, BánKính, MaĐịaĐiểm",
    "MaĐịaĐiểm → MãĐịaĐiểm, TọaĐộ, BánKính, MặcĐịnh",
    "MaLịch → MaLớp, Thứ, GiờBắtĐầu, GiờKếtThúc, MaPhòng | TênPhòngTựNhập",
    "(MaLịch, NgàyBuổi) → MaPhiên;  MaPhiên → MaLịch, NgàyBuổi, TrạngTháiPhiên, MởLúc, ĐóngLúc",
    "(MaPhiên, MaSV) → TrạngThái, Nguồn, ĐộGiống, ẢnhBằngChứng, ViĐộ, KinhĐộ, SaiSố, KhoảngCách",
    "(MaSV, MaLịch, NgàyVắng) → LýDoXinPhép, TrạngTháiĐơn, NgườiDuyệt, LýDoKhôngHợpLệ, SVXácNhậnLúc",
    "MaPH → HọTênPH, SĐT, NhậnEmail, NhậnTinCóMặt",
]
MVDS = [
    ("MaSV →→ MaLớp", "một SV học nhiều lớp (ghi danh)"),
    ("MaSV →→ MaPH", "một SV có nhiều phụ huynh theo dõi"),
    ("MaLớp →→ MaLịch", "một lớp có nhiều buổi trong tuần"),
    ("MaLớp →→ MaSV", "một lớp có nhiều SV"),
]

STEPS = [
    ("1NF — giá trị nguyên tố, không nhóm lặp",
     "Bảng gộp có nhóm lặp: một SV có nhiều phụ huynh (Phụ huynh, SĐT PH), nhiều lớp, mỗi lớp nhiều buổi. Tách mỗi giá trị "
     "lặp thành một dòng / một quan hệ riêng; mọi thuộc tính một giá trị nguyên tố.",
     ["Vector khuôn mặt 512 chiều lưu là MỘT giá trị của miền VECTOR(512); hệ thống không đọc / ghi từng phần tử ⇒ nguyên tố.",
      "audit_logs.detail (JSON) là văn bản mô tả thay đổi, chỉ để đọc, không truy vấn theo thành phần ⇒ coi như một giá trị.",
      "Kết quả: mỗi dòng của mọi bảng đều xác định duy nhất bởi khóa chính id."]),
    ("2NF — bỏ phụ thuộc bộ phận vào khóa",
     "Với khóa ghép (MaPhiên, MaSV) của kết quả điểm danh: HọTênSV chỉ phụ thuộc MaSV, NgàyBuổi chỉ phụ thuộc MaPhiên "
     "⇒ phụ thuộc bộ phận. Tách ra quan hệ Sinh viên và Phiên điểm danh; kết quả điểm danh chỉ giữ thuộc tính phụ thuộc "
     "ĐẦY ĐỦ vào (MaPhiên, MaSV).",
     ["attendance_records(session_id, student_id, status, source, confidence, …) — không còn tên SV / ngày buổi.",
      "enrollments(student_id, class_id) — không lưu tên môn (chỉ phụ thuộc class_id).",
      "leave_requests(student_id, schedule_id, absence_date, reason, …) — không lưu tên lớp, giờ học."]),
    ("3NF — bỏ phụ thuộc bắc cầu",
     "Thuộc tính không khóa không được phụ thuộc vào một thuộc tính không khóa khác. Ví dụ: MaLớp → MaGV → HọTênGV; "
     "MaLịch → MaPhòng → MãPhòng; MaPhòng → MaĐịaĐiểm → TọaĐộĐịaĐiểm.",
     ["classes chỉ giữ lecturer_id; tên GV ở lecturers / users.",
      "SỬA TRONG ĐỢT NÀY: schedules.room trước đây chép lại mã phòng khi đã chọn room_id (id → room_id → mã phòng). "
      "Nay chỉ lưu tên phòng TỰ NHẬP khi room_id rỗng; migration e2a7c4b91f6d xóa các bản sao trùng mã phòng.",
      "attendance_sessions không lưu class_id / giờ học — suy ra qua schedule_id.",
      "rooms giữ location_id, không chép tọa độ khu vực."]),
    ("BCNF — mọi định thuộc đều là siêu khóa",
     "Kiểm từng quan hệ: vế trái của mọi PTH không tầm thường đều là khóa ứng viên (id, hoặc các cột UNIQUE / khóa ghép "
     "UNIQUE). Không còn PTH nào có vế trái là thuộc tính không khóa.",
     ["users: id, email đều là khóa; students: id, student_code; attendance_sessions: id, (schedule_id, session_date); "
      "attendance_records: id, (session_id, student_id); leave_requests: id, (student_id, schedule_id, absence_date).",
      "Bảng bên dưới liệt kê khóa ứng viên của từng quan hệ, lấy tự động từ ràng buộc PRIMARY KEY / UNIQUE trong CSDL."]),
    ("4NF — tách các phụ thuộc đa trị độc lập",
     "Quan hệ SV–Lớp–PhụHuynh(MaSV, MaLớp, MaPH) ở dạng BCNF (khóa là cả ba thuộc tính) nhưng chứa hai PTĐT ĐỘC LẬP: "
     "MaSV →→ MaLớp và MaSV →→ MaPH. SV học 5 lớp, có 2 phụ huynh ⇒ phải lưu 10 dòng; thêm một lớp phải thêm 2 dòng.",
     ["Phân rã thành enrollments(student_id, class_id) và parent_students(parent_id, student_id) — mỗi bảng chỉ còn "
      "PTĐT tầm thường ⇒ đạt 4NF.",
      "Tương tự Lớp →→ Lịch và Lớp →→ SV độc lập ⇒ schedules(class_id, …) tách khỏi enrollments(class_id, student_id).",
      "Kiểm toàn bộ 22 quan hệ: không quan hệ nào chứa hai tập thuộc tính đa trị độc lập ⇒ CSDL FAMS đạt 4NF."]),
]


def build(base_css: str, nav: str) -> str:
    n_attr = sum(len(META[t].columns) for t in ORDER)
    # ---- Buoc 1: quan he pho quat
    groups_html = []
    for g, color, names in GROUPS:
        attrs = ", ".join(f"<span class='code' title='{esc(TABLES[t]['cols'].get(c.name, ''))}'>{esc(t)}.{esc(c.name)}</span>"
                          for t in names for c in META[t].columns)
        groups_html.append(f"<p><b style='color:{color}'>{esc(g)}:</b> {attrs}</p>")
    head = "".join(f"<th>{esc(h)}</th>" for h in STEP1_HEAD)
    rows = "".join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in r) + "</tr>" for r in STEP1_ROWS)
    anomalies = "".join(f"<li><b>{esc(a)}:</b> {esc(b)}</li>" for a, b in ANOMALIES)
    # ---- Buoc 2
    ent_rows = "".join(f"<tr><td>{esc(a)}</td><td><code>{esc(b)}</code></td><td>{esc(c)}</td></tr>" for a, b, c in ENTITIES)
    fds = "".join(f"<li><code>{esc(f)}</code></li>" for f in FDS)
    mvds = "".join(f"<li><code>{esc(a)}</code> — {esc(b)}</li>" for a, b in MVDS)
    # ---- Buoc 3
    steps = "".join(
        f"<div class='card'><h3>{i}. {esc(t)}</h3><p>{esc(d)}</p><ul>{''.join(f'<li>{esc(x)}</li>' for x in xs)}</ul></div>"
        for i, (t, d, xs) in enumerate(STEPS, 1))
    final = []
    for name in ORDER:
        tb = META[name]
        g, color = GROUP_OF[name]
        keys = candidate_keys(tb)
        key_txt = "<br>".join("(" + ", ".join(k) + ")" for k in keys)
        attrs = [c.name for c in tb.columns]
        fd = "<br>".join(f"{'(' + ', '.join(k) + ')' if len(k) > 1 else k[0]} → mọi thuộc tính còn lại" for k in keys)
        fks = "<br>".join(esc(x) for x in fk_text(tb)) or "—"
        final.append(
            f"<tr><td><a href='csdl_chi_tiet.html#{name}'><b>{name}</b></a><br><span class='muted'>{esc(TABLES[name]['title'])}"
            f" · {STORE_OF.get(name, '')}</span></td><td>{len(attrs)}</td><td class='code'>{key_txt}</td>"
            f"<td class='code'>{fd}</td><td class='code'>{fks}</td>"
            f"<td>{''.join('<span class=nf>' + x + '</span>' for x in ('1NF', '2NF', '3NF', 'BCNF', '4NF'))}</td>"
            f"<td>{esc(NOTES.get(name, ''))}</td></tr>")
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Chuẩn hóa CSDL (4NF) - FAMS</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><style>{base_css}
.wrap{{padding:20px 26px;max-width:1500px}}.scroll{{overflow-x:auto}}.u td,.u th{{white-space:nowrap;font-size:12px}}
.nf{{display:inline-block;background:#dcfce7;color:#166534;border-radius:5px;padding:1px 6px;margin:1px;font-size:11px;font-weight:700}}
.code{{font-family:Consolas,monospace;font-size:12px}}.step{{display:inline-block;background:#0f2a3d;color:#fff;border-radius:999px;
padding:3px 12px;font-size:12.5px;font-weight:800;margin-right:8px}}p span[title]{{border-bottom:1px dotted #94a3b8}}
</style></head><body>{nav}<div class="wrap">
<h1>Chuẩn hóa cơ sở dữ liệu FAMS đến dạng chuẩn 4 (4NF)</h1>
<div class="sbt">Quy trình 3 bước: <b>(1) nhóm chung</b> mọi thông tin vào một bảng → <b>(2) tư duy tách bảng</b> theo thực thể,
khóa, phụ thuộc → <b>(3) phân rã thông tin</b> qua 1NF, 2NF, 3NF, BCNF, 4NF. Danh sách thuộc tính, khóa và khóa ngoại ở bảng
cuối được lấy tự động từ CSDL thật (server/app/db/models.py); {len(ORDER)} quan hệ, {n_attr} thuộc tính.</div>

<h2><span class="step">Bước 1</span>Nhóm chung — gom mọi thông tin vào một bảng</h2>
<div class="card"><p>Quan hệ phổ quát <b>U(FAMS)</b> chứa toàn bộ {n_attr} thuộc tính của hệ thống, ghi theo tên thật trong CSDL (rê chuột để xem ý nghĩa):</p>
{''.join(groups_html)}
<p><b>Ví dụ vài dòng của bảng gộp</b> (mỗi dòng = một SV ở một buổi học, dữ liệu minh họa):</p>
<div class="scroll"><table class="u"><tr>{head}</tr>{rows}</table></div>
<p><b>Vấn đề của bảng gộp:</b></p><ul>{anomalies}</ul></div>

<h2><span class="step">Bước 2</span>Tư duy tách bảng — thực thể, khóa, phụ thuộc</h2>
<div class="card"><table style="max-width:900px"><tr><th>Thực thể</th><th>Quan hệ</th><th>Khóa</th></tr>{ent_rows}</table>
<h3>Phụ thuộc hàm chính (PTH)</h3><ul>{fds}</ul>
<h3>Phụ thuộc đa trị (PTĐT) — căn cứ cho 4NF</h3><ul>{mvds}</ul></div>

<h2><span class="step">Bước 3</span>Phân rã thông tin — từng dạng chuẩn</h2>
{steps}

<h2>Kết quả: {len(ORDER)} quan hệ đạt 4NF</h2>
<div class="card scroll"><table><tr><th>Quan hệ</th><th>Số thuộc tính</th><th>Khóa ứng viên</th><th>PTH (vế trái là khóa)</th>
<th>Khóa ngoại</th><th>Dạng chuẩn</th><th>Ghi chú chuẩn hóa</th></tr>{''.join(final)}</table></div>
</div></body></html>"""


def write(out_dir: Path, base_css: str, nav: str) -> None:
    (out_dir / "chuan_hoa_csdl.html").write_text(build(base_css, nav), encoding="utf-8")

# Sao lưu và khôi phục

Dữ liệu cần giữ gồm **hai phần**: CSDL PostgreSQL (mọi bảng) và thư mục ảnh `evidence` (ảnh bằng chứng điểm danh,
ảnh tạm chờ duyệt khuôn mặt). Model nhận diện (volume `insightface`) tải lại được, không cần sao lưu.

Các script chạy bằng bash (Linux, macOS, **Git Bash trên Windows**) và gọi lệnh bên trong container `db`/`server`
nên máy chạy không cần cài PostgreSQL.

## 1. Sao lưu

```bash
scripts/backup.sh                                  # stack Docker dev
scripts/backup.sh --prod                           # stack production (deploy/.env)
scripts/backup.sh --evidence-dir server/evidence   # server chạy bằng venv
scripts/backup.sh --out /mnt/backup --no-evidence  # chỉ CSDL, thư mục khác
```

Kết quả trong `backups/` (đã nằm trong `.gitignore`):

| Tệp | Nội dung |
|---|---|
| `fams_system_<ngày_giờ>.dump` | `pg_dump -Fc` (nén, khôi phục chọn lọc được) |
| `fams_system_<ngày_giờ>_evidence.tgz` | toàn bộ thư mục ảnh |
| `fams_system_<ngày_giờ>.sha256` | tổng kiểm tra hai tệp trên |

`pg_dump` chỉ đọc và không khóa ghi — chạy được khi hệ thống đang hoạt động. Script từ chối chạy nếu container `db`
không phải CSDL `fams_system*` (tránh sao lưu nhầm hệ thống khác).

**Lịch đề xuất** (cron trên máy chủ Linux):

```cron
# 02:00 hằng ngày: sao lưu, giữ 14 bản gần nhất
0 2 * * * cd /opt/fams-system && scripts/backup.sh --prod --out /var/backups/fams >> /var/log/fams-backup.log 2>&1 && ls -1t /var/backups/fams/*.dump | tail -n +15 | xargs -r rm --
```

Sao chép thư mục sao lưu ra **máy khác** (rsync/S3/ổ ngoài) — bản sao nằm cùng máy chủ không chống được hỏng ổ đĩa.

## 2. Khôi phục

```bash
# Thử trước vào CSDL phụ (không đụng dữ liệu đang chạy), kiểm tra xong thì xóa
scripts/restore.sh backups/fams_system_20261103_234151.dump --target-db fams_system_check --yes

# Khôi phục thật (GHI ĐÈ): tự tạm dừng server nếu đang chạy, khôi phục, bật lại
scripts/restore.sh backups/fams_system_20261103_234151.dump \
    --evidence backups/fams_system_20261103_234151_evidence.tgz --yes
scripts/restore.sh <file.dump> --prod --yes                      # production
```

Các bước script thực hiện: kiểm `sha256` (nếu có tệp `.sha256`) → kiểm tên CSDL `fams_system*` → tạm dừng server
(khi ghi vào CSDL chính) → tạo CSDL nếu chưa có → `pg_restore --clean --if-exists --no-owner --exit-on-error`
→ giải nén ảnh → bật lại server (server tự `alembic upgrade head` nên bản sao lưu schema cũ hơn vẫn dùng được).

## 3. Đã kiểm chứng (03/11/2026)

Sao lưu CSDL có dữ liệu mẫu → khôi phục vào `fams_system_restore_check` → so số dòng **22 bảng** (21 bảng + `alembic_version`):
giống hệt; phiên bản migration `d4f8a2c6e913` giữ nguyên; tệp ảnh giải nén đúng nội dung; `sha256 -c` đạt.
Chi tiết: [TEST_REPORT.md](../TEST_REPORT.md).

## 4. Nhập dữ liệu từ hệ thống FAMS gốc (tùy chọn)

Schema hai bên giống nhau (cùng chuỗi migration) nên chỉ cần sao chép dữ liệu:

```bash
scripts/import_legacy.sh --legacy-container fams-db-1 --legacy-db fams --legacy-user fams \
    --legacy-evidence "D:/FAMS/backend/evidence" --yes
```

- Hệ thống gốc chỉ bị **đọc**: `pg_dump` trên container DB gốc, `tar` thư mục ảnh gốc. Không ghi, không dừng gì.
- Dữ liệu hiện có của FAMS-SYSTEM bị **ghi đè**.
- Sau khi nhập: tài khoản và mật khẩu là của hệ thống gốc; `SECRET_KEY` của FAMS-SYSTEM khác bản gốc nên mọi
  phiên đăng nhập cũ và link ảnh cũ tự mất hiệu lực (người dùng đăng nhập lại là xong).
- Script **chưa được chạy** trong quá trình tái cấu trúc — người vận hành tự quyết định thời điểm.

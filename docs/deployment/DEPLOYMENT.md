# Triển khai và vận hành FAMS-SYSTEM

> Sao lưu/khôi phục: [BACKUP_RESTORE.md](BACKUP_RESTORE.md). Cấu hình HTTPS công khai chi tiết (tên miền,
> DuckDNS, đổi mật khẩu mẫu): [deploy/README.md](../../deploy/README.md).

## 1. Ba cách chạy

| Cách | Dùng khi | Thành phần |
|---|---|---|
| A. Dev tách rời | Phát triển, gỡ lỗi | DB trong Docker · server bằng venv (`uvicorn --reload`) · client `flutter run` |
| B. Docker Compose (`docker-compose.yml`) | Chạy thử cả hệ thống trên một máy | `db` + `server` + `client` (nginx) |
| C. Production (`deploy/docker-compose.prod.yml`) | Máy chủ thật có tên miền | như B + **Caddy** HTTPS, không mở cổng db/server |

Cổng mặc định (khác bản FAMS gốc để chạy song song được):

| Dịch vụ | Cổng trên máy | Ghi chú |
|---|---|---|
| PostgreSQL | `127.0.0.1:5433` | chỉ máy chủ truy cập |
| Server API | `127.0.0.1:8100` | Swagger: `http://localhost:8100/docs` |
| Web (nginx) | `5273` | `http://localhost:5273` — API qua `/api/v1/...` |
| Flutter web dev | `5274` | thêm vào `CORS_ORIGINS` |

## 2. Yêu cầu

- Docker Desktop / Docker Engine + Compose v2.
- Cách A thêm: Python 3.10–3.11, Flutter 3.47 (Dart 3.13).
- Lần đầu nhận diện khuôn mặt, server tự tải model InsightFace `buffalo_l` (~300 MB) vào volume `insightface`.
- Camera trên trình duyệt chỉ hoạt động trên **HTTPS hoặc localhost**.

## 3. Cách A — dev tách rời

```bash
# 1) CSDL (container riêng fams-system-db-1, cổng 5433)
docker compose up -d db

# 2) Server
cd server
python -m venv venv
venv\Scripts\activate                      # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                      # Linux/macOS: cp .env.example .env
alembic upgrade head                        # tạo/nâng cấp schema
python seed.py                              # dữ liệu mẫu (tài khoản trong README)
uvicorn app.main:app --reload --port 8100

# 3) Client (cửa sổ khác)
cd client
copy .env.example .env                      # API_BASE_URL=http://localhost:8100
flutter pub get
flutter run -d chrome --web-port 5274 --dart-define-from-file=.env
```

Điện thoại thật trong mạng LAN: chạy server với `--host 0.0.0.0`, mở app, bấm biểu tượng máy chủ ở màn đăng nhập,
nhập `http://<IP-máy-chạy-server>:8100` (bản release bắt buộc HTTPS).

## 4. Cách B — Docker Compose

```bash
copy .env.example .env          # sửa SECRET_KEY, mật khẩu DB nếu cần
docker compose up -d --build    # lần đầu build lâu: cài thư viện nhận diện + Flutter SDK
docker compose exec server python seed.py
```

- Mở `http://localhost:5273`. Kiểm tra: `curl http://localhost:5273/api/v1/health` → `{"status":"ok","database":"ok",...}`.
- `server` tự chạy `alembic upgrade head` khi khởi động (`server/entrypoint.sh`), healthcheck `GET /`;
  `client` chỉ khởi động khi `server` đã healthy.
- Dừng: `docker compose down` (giữ dữ liệu) · Xóa cả dữ liệu: `docker compose down -v` (**mất CSDL và ảnh**).

## 5. Cách C — Production (HTTPS)

```bash
cp deploy/.env.example deploy/.env          # FAMS_DOMAIN, SECRET_KEY (openssl rand -hex 32), mật khẩu DB, SMTP
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env exec server python seed.py   # tùy chọn
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env exec server python tools/doi_mat_khau.py
```

Chỉ Caddy mở 80/443 (tự xin/gia hạn chứng chỉ Let's Encrypt); `db`, `server`, `client` chỉ nói chuyện trong mạng nội
bộ Docker. **Bắt buộc** đổi `SECRET_KEY` và mật khẩu tài khoản mẫu trước khi mở ra Internet.

## 6. Biến môi trường

| Biến | Thành phần | Mặc định | Ý nghĩa |
|---|---|---|---|
| `DATABASE_URL` | server | `postgresql://fams_system:fams_system_dev@localhost:5433/fams_system` | Chuỗi kết nối (chỉ server có) |
| `SECRET_KEY` | server | `change-me` | Ký JWT, URL ảnh, mã QR — **đổi khi triển khai** |
| `API_PREFIX` | server | `/api/v1` | Tiền tố API |
| `CORS_ORIGINS` | server | `http://localhost:5273` | Danh sách origin, cách nhau dấu phẩy |
| `LOG_LEVEL` | server | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR` |
| `SMTP_HOST/PORT/USER/PASSWORD`, `MAIL_FROM` | server | rỗng | Email OTP và thông báo phụ huynh; rỗng = ghi OTP ra log (dev) |
| `APP_PUBLIC_URL` | server | rỗng | Link trong email thông báo |
| `TZ` | db, server | `Asia/Ho_Chi_Minh` | Múi giờ |
| Ngưỡng nghiệp vụ (`LATE_AFTER_MINUTES`, `ABSENCE_WARN_RATIO`…) | server | xem [BUSINESS_LOGIC.md §1](../BUSINESS_LOGIC.md) | |
| `POSTGRES_USER/PASSWORD/DB` | db | `fams_system` / `fams_system_dev` / `fams_system` | |
| `API_BASE_URL` | client (lúc build) | rỗng | Địa chỉ máy chủ; client tự ghép `/api/v1` |
| `FAMS_DOMAIN` | Caddy (prod) | — | Tên miền đã trỏ về máy chủ |

Bí mật (mật khẩu DB, `SECRET_KEY`, SMTP) chỉ nằm ở server/`.env` — **không bao giờ** vào client.

## 7. Log và giám sát

| Nguồn | Xem |
|---|---|
| Server (mỗi request 1 dòng `fams.access` kèm request id, thời gian, user id; lỗi kèm stack trace) | `docker compose logs -f server` |
| nginx (web) | `docker compose logs -f client` |
| Caddy (prod) | volume `caddy_data`, tệp `/data/access.log` (xoay vòng 10 MB × 5) |
| Nhật ký nghiệp vụ (ai làm gì) | trang **Nhật ký hệ thống** / `GET /api/v1/audit-logs` |
| Sức khỏe | `GET /api/v1/health` (có kiểm DB; 503 khi mất DB) |

Đổi định dạng log: `server/app/core/logging.py` (`LOG_FORMAT`).

## 8. Kiểm thử trước khi phát hành

```bash
cd server && venv\Scripts\python -m pytest -q                       # 279 test
cd client && flutter analyze && flutter test -j 1                   # 55 test
server\venv\Scripts\python scripts\check_api_contract.py            # hợp đồng client ↔ server
```
CI (`.github/workflows/ci.yml`) chạy cả ba và dựng thử stack Docker, đăng nhập qua `/api/v1`.

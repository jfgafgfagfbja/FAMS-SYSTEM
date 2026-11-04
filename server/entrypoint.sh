#!/bin/sh
set -e

alembic upgrade head
# --proxy-headers: lay IP that cua nguoi dung tu X-Forwarded-For do nginx gan vao -
# thieu co nay moi request deu mang IP cua nginx va rate limit dang nhap tinh chung ca
# truong. Chi an toan vi cong 8000 chi mo tren 127.0.0.1 (xem docker-compose.yml).
# --no-access-log: moi request da duoc ghi 1 dong (kem request id, thoi gian, nguoi dung)
# boi RequestContextMiddleware (app/core/logging.py) - tranh ghi trung.
# MOT tien trinh: bo dem dang nhap sai, gioi han tan suat, dem khung hinh xac nhan luu trong
# bo nho tien trinh (xem app/core/rate_limit.py).
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips "*" --no-access-log

#!/bin/sh
set -e

alembic upgrade head

# Cloud khong co shell de chay seed.py bang tay (vd goi mien phi cua Render): dat SEED_ON_START=1 thi
# moi lan khoi dong nap du lieu mau - seed.py tu bo qua neu CSDL da co tai khoan, nen chay lai an toan.
if [ "${SEED_ON_START:-0}" = "1" ]; then
    python seed.py
fi

# Duong dan cong khai (lien ket trong email): mac dinh lay URL ma Render cap cho dich vu.
if [ -z "${APP_PUBLIC_URL:-}" ] && [ -n "${RENDER_EXTERNAL_URL:-}" ]; then
    export APP_PUBLIC_URL="$RENDER_EXTERNAL_URL"
fi

# APP_MODULE: app.main:app (chi API - docker-compose, co nginx rieng) hoac single_port:app (giao dien
# web + API tren CUNG mot cong - dung tren cloud chi mo duoc mot cong, xem deploy/render/Dockerfile).
# PORT: docker-compose dung 8000; Render dat 10000 (render.yaml).
# --proxy-headers: lay IP that cua nguoi dung tu X-Forwarded-For do nginx / proxy cua cloud gan vao -
# thieu co nay moi request deu mang IP cua proxy va rate limit dang nhap tinh chung ca truong. Chi an
# toan vi cong cua container khong mo thang ra Internet (compose: 127.0.0.1; Render: sau proxy).
# --no-access-log: moi request da duoc ghi 1 dong (kem request id, thoi gian, nguoi dung)
# boi RequestContextMiddleware (app/core/logging.py) - tranh ghi trung.
# MOT tien trinh: bo dem dang nhap sai, gioi han tan suat, dem khung hinh xac nhan luu trong
# bo nho tien trinh (xem app/core/rate_limit.py).
exec uvicorn "${APP_MODULE:-app.main:app}" --host 0.0.0.0 --port "${PORT:-8000}" \
    --proxy-headers --forwarded-allow-ips "*" --no-access-log

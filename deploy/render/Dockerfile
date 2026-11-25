# Image trien khai FAMS-SYSTEM tren Render: MOT web service chua ca giao dien Flutter web va server
# FastAPI, chay server/single_port.py => web + API /api/v1 tren CUNG mot cong, CUNG mot duong link.
# Build tu thu muc GOC cua repo (render.yaml dat dockerContext: .):
#     docker build -f deploy/render/Dockerfile -t fams-render .

# ---------------------------------------------------------------- 1. build Flutter web (giong client/Dockerfile)
FROM debian:bookworm-slim AS web

ARG FLUTTER_VERSION=3.47.4
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl unzip xz-utils ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch ${FLUTTER_VERSION} https://github.com/flutter/flutter.git /opt/flutter
ENV PATH="/opt/flutter/bin:${PATH}"
RUN flutter config --no-analytics && flutter precache --web

WORKDIR /client
COPY client/pubspec.yaml client/pubspec.lock ./
RUN flutter pub get
COPY client/ ./
# API_BASE_URL de trong: trinh duyet goi /api/v1/... cung origin voi trang web (single_port chuyen vao API).
RUN flutter build web --release --dart-define=API_BASE_URL=

# ---------------------------------------------------------------- 2. server Python + ban web da build
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./
COPY --from=web /client/build/web ./web

# Bo ky tu CR neu entrypoint.sh bi doi sang CRLF khi checkout tren Windows.
RUN python -c "import pathlib; p = pathlib.Path('entrypoint.sh'); p.write_bytes(p.read_bytes().replace(bytes([13]), b''))" \
    && chmod +x entrypoint.sh

ENV WEB_DIR=/app/web \
    APP_MODULE=single_port:app \
    PORT=10000 \
    TZ=Asia/Ho_Chi_Minh
EXPOSE 10000
ENTRYPOINT ["./entrypoint.sh"]

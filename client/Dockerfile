# Build ban Flutter web va phuc vu bang nginx.
# API_BASE_URL = dia chi MAY CHU (client tu them /api/v1). De trong = cung origin voi trang web:
# trinh duyet goi /api/v1/... va nginx chuyen sang server (xem nginx.conf).
FROM debian:bookworm-slim AS build

ARG FLUTTER_VERSION=3.47.4
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl unzip xz-utils ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch ${FLUTTER_VERSION} https://github.com/flutter/flutter.git /opt/flutter
ENV PATH="/opt/flutter/bin:${PATH}"
RUN flutter config --no-analytics && flutter precache --web

WORKDIR /app
COPY pubspec.yaml pubspec.lock ./
RUN flutter pub get
COPY . .
ARG API_BASE_URL=
RUN flutter build web --release --dart-define=API_BASE_URL=${API_BASE_URL}

FROM nginx:alpine
COPY --from=build /app/build/web /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

#!/usr/bin/env bash
# Khoi phuc CSDL (+ anh bang chung) cua FAMS-SYSTEM tu ban sao luu cua scripts/backup.sh.
#
#   scripts/restore.sh backups/fams_system_20261103_120000.dump --yes
#   scripts/restore.sh <file.dump> --evidence <file_evidence.tgz> --yes
#   scripts/restore.sh <file.dump> --target-db fams_system_check --yes   # khoi phuc ra DB khac de kiem tra
#   scripts/restore.sh <file.dump> --prod --yes                           # stack production
#   scripts/restore.sh <file.dump> --evidence <tgz> --evidence-dir server/evidence --yes  # server chay venv
#
# Khoi phuc vao DB chinh se GHI DE du lieu hien tai (pg_restore --clean): bat buoc --yes.
# Neu container server dang chay, script tam dung no trong luc khoi phuc roi bat lai.
# Sau khi khoi phuc, server tu chay `alembic upgrade head` luc khoi dong (entrypoint.sh), nen
# ban sao luu tu phien ban schema cu hon van dung duoc.
set -euo pipefail
# Git Bash tren Windows tu doi tham so dang /duong/dan thanh C:/... khi goi docker - tat di
# (khong anh huong khi chay tren Linux).
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"

# pwd -W: duong dan dang Windows (D:/...) cho docker.exe khi chay Git Bash; Linux dung pwd.
ROOT="$(cd "$(dirname "$0")/.." && (pwd -W 2>/dev/null || pwd))"
COMPOSE=(docker compose -f "$ROOT/docker-compose.yml")
DUMP=""; EVIDENCE=""; EVIDENCE_DIR=""; TARGET_DB=""; CONFIRMED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prod) COMPOSE=(docker compose -f "$ROOT/deploy/docker-compose.prod.yml" --env-file "$ROOT/deploy/.env"); shift ;;
    --evidence) EVIDENCE="$2"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    --target-db) TARGET_DB="$2"; shift 2 ;;
    --yes) CONFIRMED=1; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    -*) echo "Tham so khong hop le: $1" >&2; exit 2 ;;
    *) DUMP="$1"; shift ;;
  esac
done

[[ -n "$DUMP" && -s "$DUMP" ]] || { echo "Thieu file .dump hop le" >&2; exit 2; }
[[ "$CONFIRMED" == 1 ]] || { echo "Khoi phuc se ghi de du lieu. Chay lai kem --yes de xac nhan." >&2; exit 2; }

# Kiem tra tong kiem tra neu co file .sha256 cung ten.
SUMS="${DUMP%.dump}.sha256"
if [[ -f "$SUMS" ]]; then
  echo ">> Kiem tra sha256"
  ( cd "$(dirname "$SUMS")" && sha256sum -c "$(basename "$SUMS")" )
fi

DB_USER="$("${COMPOSE[@]}" exec -T db printenv POSTGRES_USER | tr -d '\r')"
MAIN_DB="$("${COMPOSE[@]}" exec -T db printenv POSTGRES_DB | tr -d '\r')"
TARGET_DB="${TARGET_DB:-$MAIN_DB}"
for name in "$MAIN_DB" "$TARGET_DB"; do
  case "$name" in
    fams_system*) ;;
    *) echo "Tu choi: '$name' khong phai CSDL cua FAMS-SYSTEM." >&2; exit 1 ;;
  esac
done
psql_admin() { "${COMPOSE[@]}" exec -T db psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -Atc "$1"; }

SERVER_WAS_RUNNING=0
if [[ "$TARGET_DB" == "$MAIN_DB" ]] && [[ -n "$("${COMPOSE[@]}" ps -q --status running server 2>/dev/null)" ]]; then
  echo ">> Tam dung server trong luc khoi phuc"
  "${COMPOSE[@]}" stop server
  SERVER_WAS_RUNNING=1
fi

if [[ -z "$(psql_admin "SELECT 1 FROM pg_database WHERE datname = '$TARGET_DB'")" ]]; then
  echo ">> Tao CSDL $TARGET_DB"
  psql_admin "CREATE DATABASE \"$TARGET_DB\""
fi

echo ">> pg_restore $DUMP -> $TARGET_DB"
"${COMPOSE[@]}" cp "$DUMP" db:/tmp/fams_restore.dump
"${COMPOSE[@]}" exec -T db pg_restore -U "$DB_USER" -d "$TARGET_DB" --clean --if-exists --no-owner \
  --exit-on-error /tmp/fams_restore.dump
"${COMPOSE[@]}" exec -T db rm -f /tmp/fams_restore.dump

if [[ -n "$EVIDENCE" ]]; then
  echo ">> Giai nen anh bang chung $EVIDENCE"
  if [[ -n "$EVIDENCE_DIR" ]]; then
    mkdir -p "$EVIDENCE_DIR" && tar xzf "$EVIDENCE" -C "$EVIDENCE_DIR"
  else
    "${COMPOSE[@]}" run --rm --no-deps -T --entrypoint sh server -c "tar xzf - -C /app/evidence" < "$EVIDENCE"
  fi
fi

if [[ "$SERVER_WAS_RUNNING" == 1 ]]; then
  echo ">> Bat lai server (tu chay alembic upgrade head)"
  "${COMPOSE[@]}" start server
fi
echo ">> Khoi phuc xong vao $TARGET_DB"

#!/usr/bin/env bash
# Sao luu CSDL + anh bang chung cua FAMS-SYSTEM.
#
#   scripts/backup.sh                      # stack dev (docker-compose.yml)
#   scripts/backup.sh --prod               # stack production (deploy/docker-compose.prod.yml + deploy/.env)
#   scripts/backup.sh --out D:/backups     # thu muc dich khac (mac dinh ./backups)
#   scripts/backup.sh --no-evidence        # chi sao luu CSDL
#   scripts/backup.sh --evidence-dir server/evidence   # server chay bang venv (khong container)
#
# Tao ra:
#   <out>/fams_system_<thoi-gian>.dump          pg_dump dang custom (-Fc): nen, khoi phuc chon loc
#   <out>/fams_system_<thoi-gian>_evidence.tgz  anh bang chung + anh doi chieu khuon mat (volume evidence)
#   <out>/fams_system_<thoi-gian>.sha256        tong kiem tra de phat hien file hong
#
# pg_dump chay BEN TRONG container db (khong can cai Postgres tren may), chi DOC du lieu va
# khong khoa ghi - chay duoc khi he thong dang hoat dong.
set -euo pipefail
# Git Bash tren Windows tu doi tham so dang /duong/dan thanh C:/... khi goi docker - tat di
# (khong anh huong khi chay tren Linux).
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"

# pwd -W: duong dan dang Windows (D:/...) cho docker.exe khi chay Git Bash; Linux dung pwd.
ROOT="$(cd "$(dirname "$0")/.." && (pwd -W 2>/dev/null || pwd))"
OUT="$ROOT/backups"
COMPOSE=(docker compose -f "$ROOT/docker-compose.yml")
EVIDENCE=1
EVIDENCE_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prod) COMPOSE=(docker compose -f "$ROOT/deploy/docker-compose.prod.yml" --env-file "$ROOT/deploy/.env"); shift ;;
    --out) OUT="$2"; shift 2 ;;
    --no-evidence) EVIDENCE=0; shift ;;
    --evidence-dir) EVIDENCE_DIR="$2"; shift 2 ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "Tham so khong hop le: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$OUT"
STAMP="$(date +%Y%m%d_%H%M%S)"
BASE="$OUT/fams_system_$STAMP"

# Doc ten user/DB tu chinh container (khong phu thuoc .env tren may chay script).
DB_USER="$("${COMPOSE[@]}" exec -T db printenv POSTGRES_USER | tr -d '\r')"
DB_NAME="$("${COMPOSE[@]}" exec -T db printenv POSTGRES_DB | tr -d '\r')"
case "$DB_NAME" in
  fams_system*) ;;
  *) echo "Tu choi: container db hien tai dung CSDL '$DB_NAME', khong phai cua FAMS-SYSTEM." >&2; exit 1 ;;
esac

echo ">> Sao luu CSDL $DB_NAME -> $BASE.dump"
"${COMPOSE[@]}" exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc --no-owner > "$BASE.dump"
[[ -s "$BASE.dump" ]] || { echo "pg_dump khong tao ra du lieu" >&2; exit 1; }

FILES=("$(basename "$BASE").dump")
if [[ "$EVIDENCE" == 1 ]]; then
  echo ">> Sao luu anh bang chung -> ${BASE}_evidence.tgz"
  if [[ -n "$EVIDENCE_DIR" ]]; then
    tar czf "${BASE}_evidence.tgz" -C "$EVIDENCE_DIR" .
  else
    # tar ngay trong container server: khong can biet ten volume, dung duoc ca dev lan prod.
    "${COMPOSE[@]}" exec -T server tar czf - -C /app/evidence . > "${BASE}_evidence.tgz"
  fi
  FILES+=("$(basename "$BASE")_evidence.tgz")
fi

( cd "$OUT" && sha256sum "${FILES[@]}" > "$(basename "$BASE").sha256" )
echo ">> Xong:"
ls -l "$BASE"*

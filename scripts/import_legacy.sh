#!/usr/bin/env bash
# TUY CHON - nhap du lieu tu he thong FAMS goc vao FAMS-SYSTEM.
#
#   scripts/import_legacy.sh --yes
#   scripts/import_legacy.sh --legacy-container fams-db-1 --legacy-db fams --legacy-user fams \
#       --legacy-evidence "D:/FAMS/backend/evidence" --yes
#
# An toan voi he thong goc:
#   - Chi CHAY pg_dump (doc) tren container DB goc; khong ghi, khong khoa ghi, khong dung container.
#   - Anh bang chung goc chi duoc DOC de nen lai; khong xoa/sua thu muc goc.
# Ghi DE du lieu hien co cua FAMS-SYSTEM (qua scripts/restore.sh): bat buoc --yes.
# Schema hai ben giong nhau (cung chuoi migration, head d4f8a2c6e913) nen khong can chuyen doi.
set -euo pipefail
# Git Bash tren Windows tu doi tham so dang /duong/dan thanh C:/... khi goi docker - tat di
# (khong anh huong khi chay tren Linux).
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"

# pwd -W: duong dan dang Windows (D:/...) cho docker.exe khi chay Git Bash; Linux dung pwd.
ROOT="$(cd "$(dirname "$0")/.." && (pwd -W 2>/dev/null || pwd))"
LEGACY_CONTAINER="fams-db-1"; LEGACY_DB="fams"; LEGACY_USER="fams"; LEGACY_EVIDENCE=""
CONFIRMED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --legacy-container) LEGACY_CONTAINER="$2"; shift 2 ;;
    --legacy-db) LEGACY_DB="$2"; shift 2 ;;
    --legacy-user) LEGACY_USER="$2"; shift 2 ;;
    --legacy-evidence) LEGACY_EVIDENCE="$2"; shift 2 ;;
    --yes) CONFIRMED=1; shift ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Tham so khong hop le: $1" >&2; exit 2 ;;
  esac
done
[[ "$CONFIRMED" == 1 ]] || { echo "Se ghi de du lieu cua FAMS-SYSTEM. Chay lai kem --yes." >&2; exit 2; }

mkdir -p "$ROOT/backups"
STAMP="$(date +%Y%m%d_%H%M%S)"
DUMP="$ROOT/backups/legacy_${LEGACY_DB}_$STAMP.dump"

echo ">> Doc du lieu goc: pg_dump $LEGACY_DB trong container $LEGACY_CONTAINER (chi doc)"
docker exec "$LEGACY_CONTAINER" pg_dump -U "$LEGACY_USER" -d "$LEGACY_DB" -Fc --no-owner > "$DUMP"
[[ -s "$DUMP" ]] || { echo "pg_dump khong tao ra du lieu" >&2; exit 1; }

ARGS=("$DUMP" --yes)
if [[ -n "$LEGACY_EVIDENCE" ]]; then
  EVID="$ROOT/backups/legacy_evidence_$STAMP.tgz"
  echo ">> Nen anh bang chung goc tu $LEGACY_EVIDENCE (chi doc)"
  tar czf "$EVID" -C "$LEGACY_EVIDENCE" .
  ARGS+=(--evidence "$EVID")
fi

"$ROOT/scripts/restore.sh" "${ARGS[@]}"
echo ">> Da nhap du lieu goc. Ban sao doc ra nam trong backups/ (co the xoa sau khi kiem tra)."

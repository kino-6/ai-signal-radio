#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Prune old local ai-signal-radio generated data.

This script is dry-run by default. Add --apply to delete files.
It preserves latest.json, latest-metadata.json, daily.md, deep-dive.md,
*.tts.txt, and .gitkeep files.

Usage:
  bash scripts/prune-data.sh [options]

Options:
  --days N          Keep run archives newer than N days. Default: 14
  --audio-days N    Keep wav files newer than N days. Default: 7
  --data-dir PATH   Data directory. Default: data
  --apply           Actually delete matched files/directories.
  --dry-run         Print matched files/directories without deleting. Default.
  -h, --help        Show this help.

Examples:
  bash scripts/prune-data.sh
  bash scripts/prune-data.sh --days 30
  bash scripts/prune-data.sh --days 14 --audio-days 3 --apply
USAGE
}

is_non_negative_integer() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

DATA_DIR="data"
DAYS="14"
AUDIO_DAYS="7"
APPLY="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --days)
      DAYS="${2:-}"
      shift 2
      ;;
    --audio-days)
      AUDIO_DAYS="${2:-}"
      shift 2
      ;;
    --data-dir)
      DATA_DIR="${2:-}"
      shift 2
      ;;
    --apply)
      APPLY="1"
      shift
      ;;
    --dry-run)
      APPLY="0"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! is_non_negative_integer "$DAYS"; then
  echo "error: --days must be a non-negative integer" >&2
  exit 2
fi

if ! is_non_negative_integer "$AUDIO_DAYS"; then
  echo "error: --audio-days must be a non-negative integer" >&2
  exit 2
fi

cd "$(dirname "$0")/.."

if [[ ! -d "$DATA_DIR" ]]; then
  echo "error: data directory does not exist: $DATA_DIR" >&2
  exit 2
fi

CUTOFF_DATE="$(
  python3 - "$DAYS" <<'PY'
from datetime import date, timedelta
import sys

days = int(sys.argv[1])
print((date.today() - timedelta(days=days)).isoformat())
PY
)"
CUTOFF_COMPACT="${CUTOFF_DATE//-/}"
MATCHED=0

prune_path() {
  local path="$1"
  MATCHED=$((MATCHED + 1))
  if [[ "$APPLY" == "1" ]]; then
    echo "delete: $path"
    rm -rf -- "$path"
  else
    echo "would delete: $path"
  fi
}

scan_files() {
  local label="$1"
  shift
  echo "==> $label"
  while IFS= read -r -d '' path; do
    prune_path "$path"
  done < <(find "$@" -print0 2>/dev/null || true)
}

scan_raw_archives() {
  echo "==> raw run archives"
  while IFS= read -r -d '' path; do
    local base
    local stamp
    base="$(basename "$path")"
    stamp="${base:0:8}"
    if [[ "$stamp" =~ ^[0-9]{8}$ && "$stamp" < "$CUTOFF_COMPACT" ]]; then
      prune_path "$path"
    fi
  done < <(
    find "$DATA_DIR/raw" \
      -type f \
      \( -name '*-items.json' -o -name '*-dedupe.json' \) \
      -print0 2>/dev/null || true
  )
}

scan_dated_dirs() {
  local label="$1"
  local root="$2"
  echo "==> $label"
  while IFS= read -r -d '' path; do
    local day
    day="$(basename "$path")"
    if [[ "$day" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ && "$day" < "$CUTOFF_DATE" ]]; then
      prune_path "$path"
    fi
  done < <(
    find "$root" \
      -mindepth 1 \
      -maxdepth 1 \
      -type d \
      -name '????-??-??' \
      -print0 2>/dev/null || true
  )
}

scan_dated_scripts() {
  echo "==> dated daily scripts"
  while IFS= read -r -d '' path; do
    local base
    local day
    base="$(basename "$path")"
    day="${base:0:10}"
    if [[ "$day" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ && "$day" < "$CUTOFF_DATE" ]]; then
      prune_path "$path"
    fi
  done < <(
    find "$DATA_DIR/scripts" \
      -type f \
      -name '????-??-??-*-daily.md' \
      -print0 2>/dev/null || true
  )
}

echo "Pruning data directory: $DATA_DIR"
echo "Run archive retention:  $DAYS days"
echo "Run archive cutoff:     before $CUTOFF_DATE"
echo "Audio retention:        $AUDIO_DAYS days"
if [[ "$APPLY" == "1" ]]; then
  echo "Mode:                   apply"
else
  echo "Mode:                   dry-run"
fi

scan_raw_archives
scan_dated_dirs "processed daily run directories" "$DATA_DIR/processed"
scan_dated_dirs "wiki daily run directories" "$DATA_DIR/wiki"
scan_dated_scripts

scan_files \
  "audio wav files" \
  "$DATA_DIR/audio" \
  -type f \
  -name '*.wav' \
  -mtime +"$AUDIO_DAYS"

if [[ "$MATCHED" -eq 0 ]]; then
  echo "No matching old generated data found."
elif [[ "$APPLY" != "1" ]]; then
  echo "Dry run only. Re-run with --apply to delete $MATCHED item(s)."
else
  echo "Deleted $MATCHED item(s)."
fi

#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Set up ai-signal-radio for local development and daily use.

Usage:
  bash scripts/setup.sh [options]

Options:
  --skip-sync       Do not run uv sync.
  --skip-smoke      Do not run the local demo smoke test.
  --check-ollama    Check local Ollama availability.
  --check-voicevox  Check local VOICEVOX availability.
  --venv PATH       Virtual environment to activate. Default: .venv
  -h, --help        Show this help.

Examples:
  bash scripts/setup.sh
  bash scripts/setup.sh --check-ollama --check-voicevox
  bash scripts/setup.sh --skip-sync --skip-smoke
USAGE
}

SKIP_SYNC="0"
SKIP_SMOKE="0"
CHECK_OLLAMA="0"
CHECK_VOICEVOX="0"
PROJECT_VENV=".venv"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-sync)
      SKIP_SYNC="1"
      shift
      ;;
    --skip-smoke)
      SKIP_SMOKE="1"
      shift
      ;;
    --check-ollama)
      CHECK_OLLAMA="1"
      shift
      ;;
    --check-voicevox)
      CHECK_VOICEVOX="1"
      shift
      ;;
    --venv)
      PROJECT_VENV="${2:-}"
      shift 2
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

cd "$(dirname "$0")/.."

activate_project_venv() {
  if [[ -f "$PROJECT_VENV/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "$PROJECT_VENV/bin/activate"
  fi
}

uv_sync() {
  local project_venv_path
  project_venv_path="$(pwd)/${PROJECT_VENV#./}"
  if [[ -n "${VIRTUAL_ENV:-}" && "$VIRTUAL_ENV" != "$project_venv_path" ]]; then
    env -u VIRTUAL_ENV uv sync
  else
    uv sync
  fi
}

ensure_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "error: required command not found: $command_name" >&2
    return 1
  fi
}

ensure_data_dirs() {
  mkdir -p data/raw data/processed data/wiki data/scripts data/audio
  touch data/.gitkeep \
    data/raw/.gitkeep \
    data/processed/.gitkeep \
    data/wiki/.gitkeep \
    data/scripts/.gitkeep \
    data/audio/.gitkeep
}

check_http() {
  local label="$1"
  local url="$2"
  if curl --fail --silent --show-error --max-time 3 "$url" >/dev/null; then
    echo "ok: $label is reachable at $url"
  else
    echo "warning: $label is not reachable at $url"
  fi
}

echo "==> Checking required commands"
ensure_command uv
ensure_command curl

if [[ "$SKIP_SYNC" != "1" ]]; then
  echo "==> Syncing Python environment"
  uv_sync
else
  echo "==> Skipping uv sync"
fi

activate_project_venv

echo "==> Ensuring local data directories"
ensure_data_dirs

if [[ "$SKIP_SMOKE" != "1" ]]; then
  echo "==> Running local smoke test"
  uv run ai-signal demo --limit 1
else
  echo "==> Skipping smoke test"
fi

if [[ "$CHECK_OLLAMA" == "1" ]]; then
  echo "==> Checking Ollama"
  check_http "Ollama" "http://127.0.0.1:11434/api/tags"
fi

if [[ "$CHECK_VOICEVOX" == "1" ]]; then
  echo "==> Checking VOICEVOX"
  check_http "VOICEVOX" "http://127.0.0.1:50021/version"
fi

echo "==> Setup complete"
echo "Next: bash scripts/best-current-run.sh"

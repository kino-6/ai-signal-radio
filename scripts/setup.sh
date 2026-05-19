#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Set up ai-signal-radio for local development and daily use.

Usage:
  bash scripts/setup.sh [options]

Options:
  --install-uv           Install uv with the official installer if uv is missing.
  --skip-sync            Do not run uv sync.
  --skip-smoke           Do not run the local demo smoke test.
  --check-ollama         Check local Ollama availability.
  --start-ollama         Try to start local Ollama if it is not reachable.
  --pull-ollama-model    Pull the configured Ollama model if it is missing.
  --ollama-model MODEL   Ollama model to check or pull. Default: gemma4:latest
  --ollama-url URL       Ollama base URL. Default: http://127.0.0.1:11434
  --check-voicevox       Check local VOICEVOX availability.
  --start-voicevox       Try to start the local VOICEVOX app if it is not reachable.
  --voicevox-url URL     VOICEVOX base URL. Default: http://127.0.0.1:50021
  --voicevox-app NAME    macOS app name for VOICEVOX. Default: VOICEVOX
  --venv PATH            Virtual environment to activate. Default: .venv
  -h, --help             Show this help.

Examples:
  bash scripts/setup.sh
  bash scripts/setup.sh --check-ollama --check-voicevox
  OLLAMA_MODEL=gemma4:latest bash scripts/setup.sh --start-ollama --pull-ollama-model --start-voicevox
  bash scripts/setup.sh --install-uv --skip-smoke
  bash scripts/setup.sh --skip-sync --skip-smoke
USAGE
}

INSTALL_UV="0"
SKIP_SYNC="0"
SKIP_SMOKE="0"
CHECK_OLLAMA="0"
START_OLLAMA="0"
PULL_OLLAMA_MODEL="0"
CHECK_VOICEVOX="0"
START_VOICEVOX="0"
PROJECT_VENV=".venv"
OLLAMA_MODEL="${OLLAMA_MODEL:-gemma4:latest}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
VOICEVOX_URL="${VOICEVOX_URL:-http://127.0.0.1:50021}"
VOICEVOX_APP_NAME="${VOICEVOX_APP_NAME:-VOICEVOX}"

require_option_value() {
  local option_name="$1"
  local option_value="${2:-}"

  if [[ -z "$option_value" || "$option_value" == --* ]]; then
    echo "error: $option_name requires a value" >&2
    usage >&2
    exit 2
  fi

  printf '%s' "$option_value"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-uv)
      INSTALL_UV="1"
      shift
      ;;
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
    --start-ollama)
      START_OLLAMA="1"
      CHECK_OLLAMA="1"
      shift
      ;;
    --pull-ollama-model)
      PULL_OLLAMA_MODEL="1"
      CHECK_OLLAMA="1"
      shift
      ;;
    --ollama-model)
      OLLAMA_MODEL="$(require_option_value "$1" "${2:-}")"
      shift 2
      ;;
    --ollama-url)
      OLLAMA_URL="$(require_option_value "$1" "${2:-}")"
      shift 2
      ;;
    --check-voicevox)
      CHECK_VOICEVOX="1"
      shift
      ;;
    --start-voicevox)
      START_VOICEVOX="1"
      CHECK_VOICEVOX="1"
      shift
      ;;
    --voicevox-url)
      VOICEVOX_URL="$(require_option_value "$1" "${2:-}")"
      shift 2
      ;;
    --voicevox-app)
      VOICEVOX_APP_NAME="$(require_option_value "$1" "${2:-}")"
      shift 2
      ;;
    --venv)
      PROJECT_VENV="$(require_option_value "$1" "${2:-}")"
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

OLLAMA_URL="${OLLAMA_URL%/}"
VOICEVOX_URL="${VOICEVOX_URL%/}"
OLLAMA_TAGS_URL="$OLLAMA_URL/api/tags"
VOICEVOX_VERSION_URL="$VOICEVOX_URL/version"

activate_project_venv() {
  if [[ -f "$PROJECT_VENV/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "$PROJECT_VENV/bin/activate"
  fi
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
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
  if ! command_exists "$command_name"; then
    echo "error: required command not found: $command_name" >&2
    return 1
  fi
}

install_uv() {
  echo "==> Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
}

ensure_uv() {
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  if command_exists uv; then
    return 0
  fi

  if [[ "$INSTALL_UV" == "1" ]]; then
    install_uv
  fi

  if ! command_exists uv; then
    cat >&2 <<'EOF'
error: required command not found: uv

Install uv first, or let this script install it:
  bash scripts/setup.sh --install-uv

Manual install:
  curl -LsSf https://astral.sh/uv/install.sh | sh
EOF
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

http_ok() {
  local url="$1"
  curl --fail --silent --show-error --max-time 3 "$url" >/dev/null 2>&1
}

check_http() {
  local label="$1"
  local url="$2"
  if http_ok "$url"; then
    echo "ok: $label is reachable at $url"
  else
    echo "warning: $label is not reachable at $url"
  fi
}

wait_http() {
  local label="$1"
  local url="$2"
  local attempts="${3:-15}"
  local delay_seconds="${4:-2}"
  local count=1

  while [[ "$count" -le "$attempts" ]]; do
    if http_ok "$url"; then
      echo "ok: $label is reachable at $url"
      return 0
    fi
    sleep "$delay_seconds"
    count=$((count + 1))
  done

  echo "warning: $label is not reachable at $url"
  return 1
}

start_ollama() {
  if http_ok "$OLLAMA_TAGS_URL"; then
    echo "ok: Ollama is already running"
    return 0
  fi

  echo "==> Trying to start Ollama"
  if command_exists open; then
    open -a Ollama >/dev/null 2>&1 || true
    wait_http "Ollama" "$OLLAMA_TAGS_URL" 10 2 && return 0
  fi

  if command_exists ollama; then
    nohup ollama serve >/tmp/ai-signal-radio-ollama.log 2>&1 &
    wait_http "Ollama" "$OLLAMA_TAGS_URL" 15 2 && return 0
    echo "warning: Ollama did not become reachable; see /tmp/ai-signal-radio-ollama.log"
    return 1
  fi

  echo "warning: Ollama app or ollama command was not found"
  return 1
}

ollama_model_available() {
  if ! command_exists ollama; then
    return 1
  fi
  ollama list | awk 'NR > 1 {print $1}' | grep -Fxq "$OLLAMA_MODEL"
}

pull_ollama_model() {
  ensure_command ollama
  if ! http_ok "$OLLAMA_TAGS_URL"; then
    echo "error: Ollama is not reachable at $OLLAMA_TAGS_URL" >&2
    echo "hint: run with --start-ollama, or start Ollama manually." >&2
    return 1
  fi

  if ollama_model_available; then
    echo "ok: Ollama model is already available: $OLLAMA_MODEL"
    return 0
  fi

  echo "==> Pulling Ollama model: $OLLAMA_MODEL"
  ollama pull "$OLLAMA_MODEL"
}

check_ollama_model() {
  if ollama_model_available; then
    echo "ok: Ollama model is available: $OLLAMA_MODEL"
  else
    echo "warning: Ollama model is not listed locally: $OLLAMA_MODEL"
    echo "hint: bash scripts/setup.sh --pull-ollama-model --ollama-model $OLLAMA_MODEL"
  fi
}

start_voicevox() {
  if http_ok "$VOICEVOX_VERSION_URL"; then
    echo "ok: VOICEVOX is already running"
    return 0
  fi

  echo "==> Trying to start VOICEVOX"
  if command_exists open; then
    open -a "$VOICEVOX_APP_NAME" >/dev/null 2>&1 || true
    wait_http "VOICEVOX" "$VOICEVOX_VERSION_URL" 20 2 && return 0
  fi

  echo "warning: VOICEVOX did not become reachable"
  echo "hint: start VOICEVOX engine manually, then rerun --check-voicevox."
  return 1
}

echo "==> Checking required commands"
ensure_command curl
ensure_uv

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

if [[ "$START_OLLAMA" == "1" ]]; then
  start_ollama || true
fi

if [[ "$PULL_OLLAMA_MODEL" == "1" ]]; then
  pull_ollama_model
fi

if [[ "$START_VOICEVOX" == "1" ]]; then
  start_voicevox || true
fi

if [[ "$CHECK_OLLAMA" == "1" ]]; then
  echo "==> Checking Ollama"
  check_http "Ollama" "$OLLAMA_TAGS_URL"
  check_ollama_model
fi

if [[ "$CHECK_VOICEVOX" == "1" ]]; then
  echo "==> Checking VOICEVOX"
  check_http "VOICEVOX" "$VOICEVOX_VERSION_URL"
fi

echo "==> Setup complete"
echo "Next: bash scripts/best-current-run.sh"

#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Run the current recommended ai-signal-radio daily pipeline.

Usage:
  bash scripts/best-current-run.sh

Environment variables:
  CONFIG=config/sources.live.example.yml
  LIMIT=8
  SUMMARIZER=ollama
  OLLAMA_MODEL=gemma4:latest
  OLLAMA_URL=http://127.0.0.1:11434
  PROJECT_VENV=.venv     Virtual environment to activate before running uv.
  DEEP_DIVE=1          Generate deep-dive dialogue script and TTS text.
  DOCS=1               Generate MkDocs preview pages.
  VOICEVOX=1           Synthesize wav files when VOICEVOX is available.
  PLAY_AUDIO=1         Play generated audio at the end when available.
  PLAY_TARGET=daily    Audio to play: daily or deep-dive.
  AUDIO_PLAYER=afplay  Audio player command.
  SPEAKER=3
  HOST_SPEAKER=3
  ANALYST_SPEAKER=8
  SPEED=1.18
  PITCH=0.0
  INTONATION=1.0

Examples:
  bash scripts/best-current-run.sh
  PLAY_AUDIO=0 bash scripts/best-current-run.sh
  PLAY_TARGET=deep-dive bash scripts/best-current-run.sh
  VOICEVOX=0 bash scripts/best-current-run.sh
  LIMIT=12 OLLAMA_MODEL=gemma4:latest bash scripts/best-current-run.sh
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

cd "$(dirname "$0")/.."

PROJECT_VENV="${PROJECT_VENV:-.venv}"
if [[ -f "$PROJECT_VENV/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$PROJECT_VENV/bin/activate"
else
  echo "warning: project virtualenv not found: $PROJECT_VENV; continuing with uv run." >&2
fi

CONFIG="${CONFIG:-config/sources.live.example.yml}"
LIMIT="${LIMIT:-8}"
SUMMARIZER="${SUMMARIZER:-ollama}"
OLLAMA_MODEL="${OLLAMA_MODEL:-gemma4:latest}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
DEEP_DIVE="${DEEP_DIVE:-1}"
DOCS="${DOCS:-1}"
VOICEVOX="${VOICEVOX:-1}"
PLAY_AUDIO="${PLAY_AUDIO:-1}"
PLAY_TARGET="${PLAY_TARGET:-daily}"
AUDIO_PLAYER="${AUDIO_PLAYER:-afplay}"
SPEAKER="${SPEAKER:-3}"
HOST_SPEAKER="${HOST_SPEAKER:-3}"
ANALYST_SPEAKER="${ANALYST_SPEAKER:-8}"
SPEED="${SPEED:-1.18}"
PITCH="${PITCH:-0.0}"
INTONATION="${INTONATION:-1.0}"
DAILY_AUDIO_WRITTEN="0"
DEEP_AUDIO_WRITTEN="0"

run_voicevox_tts() {
  local label="$1"
  local input="$2"
  local output="$3"
  shift 3

  if [[ "$VOICEVOX" != "1" ]]; then
    echo "==> Skipping $label audio because VOICEVOX=0."
    return 1
  fi

  echo "==> Synthesizing $label audio with VOICEVOX"
  if uv run ai-signal tts \
    --input "$input" \
    --output "$output" \
    --speed "$SPEED" \
    --pitch "$PITCH" \
    --intonation "$INTONATION" \
    "$@"
  then
    return 0
  fi

  echo "warning: VOICEVOX $label audio synthesis failed. Continuing without wav output." >&2
  return 1
}

print_outputs() {
  echo "==> Done"
  echo "Daily script: data/scripts/daily.md"
  echo "Daily TTS:    data/scripts/daily.tts.txt"
  if [[ "$DEEP_DIVE" == "1" ]]; then
    echo "Deep dive:    data/scripts/deep-dive.md"
    echo "Deep TTS:     data/scripts/deep-dive.tts.txt"
  fi
  if [[ "$DAILY_AUDIO_WRITTEN" == "1" ]]; then
    echo "Audio:        data/audio/daily.wav"
  fi
  if [[ "$DEEP_AUDIO_WRITTEN" == "1" ]]; then
    echo "Deep audio:   data/audio/deep-dive.wav"
  fi
  if [[ "$DOCS" == "1" ]]; then
    echo "Preview:      uv run mkdocs serve"
  fi
}

play_audio() {
  local target_path=""

  if [[ "$PLAY_AUDIO" != "1" ]]; then
    echo "==> Skipping audio playback because PLAY_AUDIO=0."
    return 0
  fi

  case "$PLAY_TARGET" in
    daily)
      if [[ "$DAILY_AUDIO_WRITTEN" == "1" ]]; then
        target_path="data/audio/daily.wav"
      fi
      ;;
    deep-dive)
      if [[ "$DEEP_AUDIO_WRITTEN" == "1" ]]; then
        target_path="data/audio/deep-dive.wav"
      fi
      ;;
    *)
      echo "warning: unknown PLAY_TARGET=$PLAY_TARGET; expected daily or deep-dive." >&2
      return 0
      ;;
  esac

  if [[ -z "$target_path" ]]; then
    echo "==> Skipping audio playback because $PLAY_TARGET audio was not generated."
    return 0
  fi

  if ! command -v "$AUDIO_PLAYER" >/dev/null 2>&1; then
    echo "warning: audio player not found: $AUDIO_PLAYER; skipping playback." >&2
    return 0
  fi

  echo "==> Playing $PLAY_TARGET audio"
  "$AUDIO_PLAYER" "$target_path"
}

echo "==> Running daily AI news pipeline"
run_cmd=(
  uv run ai-signal run
  --config "$CONFIG"
  --limit "$LIMIT"
  --script-style briefing
  --summarizer "$SUMMARIZER"
)
if [[ "$SUMMARIZER" == "ollama" ]]; then
  run_cmd+=(--ollama-model "$OLLAMA_MODEL" --ollama-url "$OLLAMA_URL")
fi
"${run_cmd[@]}"

echo "==> Writing daily TTS script"
uv run ai-signal tts-script \
  --input data/scripts/daily.md \
  --output data/scripts/daily.tts.txt \
  --speaker "$SPEAKER"

if run_voicevox_tts \
  "daily" \
  data/scripts/daily.tts.txt \
  data/audio/daily.wav \
  --speaker "$SPEAKER"
then
  DAILY_AUDIO_WRITTEN="1"
fi

if [[ "$DEEP_DIVE" == "1" ]]; then
  echo "==> Writing deep-dive dialogue script"
  uv run ai-signal script \
    --input data/wiki \
    --output data/scripts/deep-dive.md \
    --style dialogue

  echo "==> Writing deep-dive TTS script"
  uv run ai-signal tts-script \
    --input data/scripts/deep-dive.md \
    --output data/scripts/deep-dive.tts.txt \
    --speaker "$SPEAKER" \
    --host-speaker "$HOST_SPEAKER" \
    --analyst-speaker "$ANALYST_SPEAKER"

  if run_voicevox_tts \
    "deep-dive" \
    data/scripts/deep-dive.tts.txt \
    data/audio/deep-dive.wav
  then
    DEEP_AUDIO_WRITTEN="1"
  fi
fi

if [[ "$DOCS" == "1" ]]; then
  echo "==> Generating MkDocs preview pages"
  uv run ai-signal docs
fi

play_audio
print_outputs

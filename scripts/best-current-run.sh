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
  DEEP_DIVE=1          Generate deep-dive dialogue script and TTS text.
  DOCS=1               Generate MkDocs preview pages.
  VOICEVOX=1           Synthesize wav files when VOICEVOX is available.
  SPEAKER=3
  HOST_SPEAKER=3
  ANALYST_SPEAKER=8
  SPEED=1.18
  PITCH=0.0
  INTONATION=1.0

Examples:
  bash scripts/best-current-run.sh
  VOICEVOX=0 bash scripts/best-current-run.sh
  LIMIT=12 OLLAMA_MODEL=gemma4:latest bash scripts/best-current-run.sh
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

cd "$(dirname "$0")/.."

CONFIG="${CONFIG:-config/sources.live.example.yml}"
LIMIT="${LIMIT:-8}"
SUMMARIZER="${SUMMARIZER:-ollama}"
OLLAMA_MODEL="${OLLAMA_MODEL:-gemma4:latest}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
DEEP_DIVE="${DEEP_DIVE:-1}"
DOCS="${DOCS:-1}"
VOICEVOX="${VOICEVOX:-1}"
SPEAKER="${SPEAKER:-3}"
HOST_SPEAKER="${HOST_SPEAKER:-3}"
ANALYST_SPEAKER="${ANALYST_SPEAKER:-8}"
SPEED="${SPEED:-1.18}"
PITCH="${PITCH:-0.0}"
INTONATION="${INTONATION:-1.0}"
DAILY_AUDIO_WRITTEN="0"
DEEP_AUDIO_WRITTEN="0"

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

if [[ "$VOICEVOX" == "1" ]]; then
  echo "==> Synthesizing daily audio with VOICEVOX"
  if uv run ai-signal tts \
    --input data/scripts/daily.tts.txt \
    --output data/audio/daily.wav \
    --speaker "$SPEAKER" \
    --speed "$SPEED" \
    --pitch "$PITCH" \
    --intonation "$INTONATION"
  then
    DAILY_AUDIO_WRITTEN="1"
  else
    echo "warning: VOICEVOX daily audio synthesis failed. Continuing without wav output." >&2
  fi
else
  echo "==> Skipping VOICEVOX audio because VOICEVOX=0."
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

  if [[ "$VOICEVOX" == "1" ]]; then
    echo "==> Synthesizing deep-dive audio with VOICEVOX"
    if uv run ai-signal tts \
      --input data/scripts/deep-dive.tts.txt \
      --output data/audio/deep-dive.wav \
      --speed "$SPEED" \
      --pitch "$PITCH" \
      --intonation "$INTONATION"
    then
      DEEP_AUDIO_WRITTEN="1"
    else
      echo "warning: VOICEVOX deep-dive audio synthesis failed. Continuing without wav output." >&2
    fi
  fi
fi

if [[ "$DOCS" == "1" ]]; then
  echo "==> Generating MkDocs preview pages"
  uv run ai-signal docs
fi

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

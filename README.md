# ai-signal-radio

Local-first AI news pipeline MVP.

`ai-signal-radio` collects AI-related news items, normalizes and deduplicates
them, writes an LLM-friendly Markdown wiki note, and generates a short
radio-style briefing script. The first version stores everything as JSON and
Markdown files under `data/`.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management

## Setup

```bash
uv sync
```

## Run The MVP Pipeline

The example config uses a local demo source, so the first run does not need the
network:

```bash
uv run ai-signal-radio run
```

Outputs are written to:

- `data/raw/` for collected JSON
- `data/wiki/` for Markdown wiki notes
- `data/scripts/` for radio scripts
- `data/audio/` for optional VOICEVOX audio

To enable live sources, copy and edit `config/sources.example.yml`, then pass it
to the CLI:

```bash
uv run ai-signal-radio run --config config/sources.example.yml
```

## VOICEVOX

VOICEVOX synthesis is disabled in the example config. To use it, run a local
VOICEVOX engine and set:

```yaml
tts:
  enabled: true
  endpoint: "http://127.0.0.1:50021"
  speaker: 1
```

## Tests

```bash
uv run pytest
```

# ai-signal-radio

AI 関連ニュースを集め、LLM が読みやすい Markdown wiki に整理し、短いラジオ風スクリプトを作るためのローカルファーストな CLI プロジェクトです。

最初の MVP では、Web UI、データベース、ベクトルDB、OpenAI API キーは不要です。データは JSON と Markdown として `data/` 配下に保存します。

## MVP の範囲

- RSS / Atom、arXiv、Hacker News Algolia からニュースを収集するための小さな collector
- URL とタイトルによる簡易 dedupe と、判定理由の JSON 保存
- 設定ファイルで調整できる透明なヒューリスティック score と source diversity による最終選抜
- `data/wiki/YYYY-MM-DD/RUN_ID/` への Markdown wiki note 生成
- wiki note から TTS で読みやすい日本語ラジオ風スクリプト生成
- 完全ローカルの `demo` コマンド
- pytest による基本テスト

## セットアップ

必要なもの:

- Python 3.11+
- uv

```bash
uv sync
```

## デモ実行

`demo` はネットワークアクセスなしで動きます。ハードコードされたサンプルニュースを使って、raw JSON、processed JSON、wiki、script まで生成します。

```bash
uv run ai-signal demo
```

## 収集

```bash
uv run ai-signal collect --config config/sources.example.yml --limit 20
```

デフォルトの `config/sources.example.yml` は demo source のみ有効です。RSS、arXiv、Hacker News を使う場合は、設定ファイルをコピーして編集してください。

```bash
cp config/sources.example.yml config/sources.yml
uv run ai-signal collect --config config/sources.yml --limit 20
```

`config/sources.yml` はローカル設定用として git 管理から除外されています。

実ニュースをすぐ試す場合は、arXiv と Hacker News を有効にした example を使えます。

```bash
uv run ai-signal run \
  --config config/sources.live.example.yml \
  --limit 8 \
  --summarizer ollama \
  --ollama-model gemma4:latest
```

このコマンドは `collect -> processed -> wiki -> script` をまとめて実行します。実行ごとの成果物は run id 付きで残し、最新 script は `data/scripts/daily.md` にもコピーします。

`collect` は取得したままの raw JSON だけを保存します。`run` は raw JSON に加えて、重複排除とスコアリング後の selected items を `data/processed/latest.json` と `data/processed/YYYY-MM-DD/RUN_ID.json` に保存します。日次確認や wiki 生成には processed JSON を使うと、選抜理由を追いやすくなります。

`ranker` の重みは設定ファイルで調整できます。

```yaml
ranker:
  keyword_bonus: 2.0
  official_source_bonus: 4.0
  research_bonus: 2.0
  hn_points_divisor: 100.0
  hn_points_cap: 3.0
```

各 source の `params` には `timeout_seconds` と `rate_limit_seconds` を指定できます。公開APIに連続アクセスしすぎないため、実ニュース用設定では小さな待機時間を入れています。

## Wiki 生成

```bash
uv run ai-signal wiki --input data/processed/latest.json --output data/wiki
```

`wiki` は raw JSON と processed JSON のどちらも受け取れます。processed JSON の場合は保存済みのランキング順と score breakdown をそのまま使います。出力先は `data/wiki/YYYY-MM-DD/RUN_ID/` です。各ニュースごとに frontmatter 付き Markdown を生成します。タグ別の topic page は `data/wiki/topics/` に生成します。
通常は決定的なプレースホルダー要約を使うため、LLM は呼びません。

ローカル Ollama を明示的に使う場合:

```bash
uv run ai-signal wiki \
  --input data/raw/latest.json \
  --output data/wiki \
  --summarizer ollama \
  --ollama-model gemma4:latest
```

手元にあるモデルでは、まず `gemma4:latest` を推奨します。重めの深掘りには `huihui_ai/Qwen3.6-abliterated:27b`、画像入力が必要になったら `llama3.2-vision:latest` を候補にします。

## Script 生成

```bash
uv run ai-signal script --input data/wiki --output data/scripts/daily.md --style standard
```

生成される script は VOICEVOX などの TTS で読みやすいよう、短い日本語文を中心にしています。`--style short|standard|detailed` で読み上げの長さを変えられます。

## Rebuild

過去の raw JSON をネットワークなしで再処理できます。ranker や wiki/script の実装を変えたあと、同じ収集結果から再生成したいときに使います。

```bash
uv run ai-signal rebuild \
  --input data/raw/latest.json \
  --data-dir data \
  --limit 8 \
  --script-style standard
```

## ディレクトリ構成

```text
config/
  sources.example.yml
  pronunciations.example.yml
data/
  raw/
    YYYYMMDDTHHMMSSffffffZ-items.json
    YYYYMMDDTHHMMSSffffffZ-dedupe.json
    latest.json
    latest-dedupe.json
  processed/
    YYYY-MM-DD/
      RUN_ID.json
    latest.json
  wiki/
    YYYY-MM-DD/
      RUN_ID/
        01-title.md
    topics/
      ai.md
  scripts/
    YYYY-MM-DD-RUN_ID-daily.md
    daily.md
  audio/
src/
  ai_signal_radio/
    collectors/
    processors/
    tts/
tests/
docs/
```

生成データは `.gitignore` されています。`.gitkeep` 以外の `data/` 配下の成果物はコミットしません。

## VOICEVOX

VOICEVOX 対応は任意です。`demo` や通常の wiki/script 生成には VOICEVOX は不要です。

ローカルの VOICEVOX engine が起動している場合、ずんだもん speaker 3 で script から wav を生成できます。

```bash
uv run ai-signal tts \
  --input data/scripts/daily.md \
  --output data/audio/daily.wav \
  --speaker 3 \
  --speed 1.18 \
  --pitch 0.0 \
  --intonation 1.0
```

`speaker`、`speed_scale`、`pitch_scale`、`intonation_scale` は `config/sources.yml` の `tts` セクションにも書けます。CLI 引数を指定した場合は、CLI 側が優先されます。

```yaml
tts:
  endpoint: "http://127.0.0.1:50021"
  speaker: 3
  speed_scale: 1.18
  pitch_scale: 0.0
  intonation_scale: 1.0
  pronunciation_profile: "config/pronunciations.example.yml"
```

固有名詞の読み替えは文脈や分野で揺れやすいため、グローバルな読み方辞書は持ちません。必要なときだけ、番組・分野ごとの任意 pronunciation profile を指定します。

読み替えを試す場合は、任意の YAML profile を指定できます。

```bash
uv run ai-signal tts \
  --config config/sources.example.yml \
  --input data/scripts/daily.md \
  --output data/audio/daily.wav \
  --pronunciation-profile config/pronunciations.example.yml
```

VOICEVOX engine が起動していない場合は、CLI が接続先 URL と起動確認のメッセージを出します。

## テスト

```bash
uv run pytest
```

GitHub Actions でも push / pull request 時に pytest だけを実行します。

## MkDocs Preview

生成済みの wiki / script をブラウザで読むために、MkDocs 用のローカルプレビューを作れます。

```bash
uv run ai-signal demo
uv run ai-signal docs
uv run mkdocs serve
```

`ai-signal docs` は `data/wiki`、`data/scripts/daily.md`、`data/processed/latest.json` から `docs/generated/` を作ります。`docs/generated/` と `site/` は git 管理しません。

静的ビルドを確認する場合:

```bash
uv run mkdocs build --strict
```

## ローカル日次実行

`launchd` や `cron` で日次実行する例は [Local Scheduling](docs/SCHEDULING.md) に置いています。

## 今後のロードマップ

- topic page を日次の差分ではなく長期の知識ページとして育てる
- source ごとの rate limit / timeout をより細かく制御する
- Ollama summarizer の実ニュース向け評価を増やす

## Project Planning

- [Next Actions](docs/NEXT_ACTIONS.md)

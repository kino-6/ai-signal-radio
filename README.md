# ai-signal-radio

AI 関連ニュースを集め、LLM が読みやすい Markdown wiki に整理し、短いラジオ風スクリプトを作るためのローカルファーストな CLI プロジェクトです。

最初の MVP では、Web UI、データベース、ベクトルDB、OpenAI API キーは不要です。データは JSON と Markdown として `data/` 配下に保存します。

## MVP の範囲

- RSS / Atom、arXiv、Hacker News Algolia からニュースを収集するための小さな collector
- URL とタイトルによる簡易 dedupe
- 透明なヒューリスティックによる score 付けと source diversity による最終選抜
- `data/wiki/YYYY-MM-DD/` への Markdown wiki note 生成
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

`demo` はネットワークアクセスなしで動きます。ハードコードされたサンプルニュースを使って、raw JSON、wiki、script まで生成します。

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

このコマンドは `collect -> wiki -> script` をまとめて実行し、`data/scripts/daily.md` まで生成します。

## Wiki 生成

```bash
uv run ai-signal wiki --input data/raw/latest.json --output data/wiki
```

出力先は `data/wiki/YYYY-MM-DD/` です。各ニュースごとに frontmatter 付き Markdown を生成します。
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
uv run ai-signal script --input data/wiki --output data/scripts/daily.md
```

生成される script は VOICEVOX などの TTS で読みやすいよう、短い日本語文を中心にしています。

## ディレクトリ構成

```text
config/
  sources.example.yml
data/
  raw/
    latest.json
  wiki/
    YYYY-MM-DD/
      01-title.md
  scripts/
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

固有名詞の読み替えは文脈や分野で揺れやすいため、MVP ではグローバルな読み方辞書を持ちません。必要になったら、番組・分野ごとの任意 pronunciation profile として追加する方針です。

## テスト

```bash
uv run pytest
```

## 今後のロードマップ

- collector の parse テストを増やす
- dedupe の理由を記録する
- score の内訳を説明できるようにする
- wiki note の品質を上げる
- VOICEVOX で wav を生成する CLI を追加する
- ローカルスケジューラで日次実行できる例を追加する
- Ollama summarizer のプロンプトと出力品質を改善する

## Project Planning

- [Next Actions](docs/NEXT_ACTIONS.md)

# AI Signal Radio

AI 関連ニュースを収集し、LLM が読みやすい wiki note とラジオ風スクリプトに変換するローカルファーストな CLI です。

## Quick Links

- [Next Actions](NEXT_ACTIONS.md)
- [Local Scheduling](SCHEDULING.md)
- [MkDocs Visualization Plan](MKDOCS_PLAN.md)
- [Radio Quality Improvement Plan](RADIO_QUALITY_PLAN.md)

## Local Preview

生成済みの wiki / script を MkDocs で見る場合は、先にプレビュー用 Markdown を作ります。

```bash
uv run ai-signal docs
uv run mkdocs serve
```

`docs/generated/` はローカル閲覧用の生成物です。git には含めません。

## Typical Flow

```bash
uv run ai-signal demo
uv run ai-signal docs
uv run mkdocs serve
```

実ニュースで試す場合:

```bash
uv run ai-signal run --config config/sources.live.example.yml --limit 8
uv run ai-signal docs
uv run mkdocs serve
```

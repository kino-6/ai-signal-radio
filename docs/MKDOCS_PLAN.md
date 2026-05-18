# MkDocs Visualization Plan

ai-signal-radio の wiki / script / processed JSON を、ローカルで眺めやすくするための MkDocs 試作計画。

## Goal

- 収集した AI ニュースの Daily wiki をブラウザで読む
- topic page を一覧し、LLM 向け知識ベースとして育てる入口を作る
- radio script と source / score / dedupe trace を人間が確認しやすくする
- Web UI ではなく、静的ドキュメントとしてローカルプレビューする

## Design Principles

- `data/` の生成物は引き続き git 管理しない
- MkDocs 用の生成プレビューも git 管理しない
- 手動で見たいときに `uv run ai-signal docs ...` のようなコマンドで `docs/generated/` を作る
- まずは標準 MkDocs theme で始め、必要になったら `mkdocs-material` を検討する
- TTS や LLM の実行は MkDocs build に混ぜない

## Proposed Structure

```text
mkdocs.yml
docs/
  index.md
  NEXT_ACTIONS.md
  SCHEDULING.md
  MKDOCS_PLAN.md
  generated/              # ignored
    daily.md
    radio.md
    topics/
      ai.md
    runs/
      YYYY-MM-DD/
        RUN_ID/
          01-title.md
```

## Implementation Checklist

- [x] `mkdocs` を dev dependency に追加する
- [x] `mkdocs.yml` を追加する
- [x] `docs/index.md` を追加し、README より短い入口ページにする
- [x] `.gitignore` に `docs/generated/` と `site/` を追加する
- [x] `ai-signal docs` サブコマンドを追加する
- [x] `ai-signal docs --wiki data/wiki --script data/scripts/daily.md --output docs/generated` で静的プレビュー用 Markdown を生成する
- [x] generated daily index に最新 run、topic links、radio script link を載せる
- [x] MkDocs build がネットワークなしで通るようにする
- [x] `uv run mkdocs build --strict` をテストする
- [x] README に `uv run mkdocs serve` の手順を追加する

## First Slice

最初の実装では、次だけを狙う。

- `mkdocs.yml`
- `docs/index.md`
- `docs/generated/` を作る `ai-signal docs`
- 最新 wiki run と `data/scripts/daily.md` を MkDocs で読める形にコピー
- `uv run pytest`
- `uv run ai-signal demo`
- `uv run ai-signal docs`
- `uv run mkdocs build --strict`

## Open Questions

- topic page は `data/wiki/topics/` をそのまま見せるか、MkDocs 用に再構成するか
- `processed/latest.json` の score breakdown を Markdown table として出すか
- audio file へのリンクを MkDocs に置くか
- 将来 GitHub Pages に載せるか、ローカル閲覧専用にするか

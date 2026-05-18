# Next Actions

ai-signal-radio の次の実装アクションを `[x]` / `[ ]` で管理するためのメモ。

## Current State

- [x] Python 3.11+ / uv のプロジェクト骨格を作る
- [x] ローカルデモソースで end-to-end に動く CLI を作る
- [x] raw JSON、wiki Markdown、radio script を `data/` 配下へ保存する
- [x] processed JSON に deduped/ranked selected items と score/dedupe trace を保存する
- [x] RSS、arXiv、Hacker News、VOICEVOX の初期インターフェースを置く
- [x] pytest でモデル、重複排除、wiki writer をテストする

## Next Milestone: Useful Local Daily Run

目標: ネットワーク取得を有効化しても壊れにくく、毎日ローカルで実行できる状態にする。

- [x] `README.md` に「初回セットアップ」「デモ実行」「ライブソース実行」の流れをもう少し具体化する
- [x] `config/sources.example.yml` とは別に、自分用設定を置ける `config/sources.yml` を `.gitignore` に追加する
- [x] CLI に `--dry-run` を追加して、ファイル保存前に収集件数とタイトル一覧を確認できるようにする
- [x] CLI に `--source` フィルタを追加して、特定ソースだけ実行できるようにする
- [x] live collector の例外表示を改善し、1ソース失敗しても他ソースの成果物が残ることを明示する
- [x] RSS / Atom パーサーのテストフィクスチャを追加し、ネットワークなしで parse 挙動を固定する
- [x] Hacker News collector の JSON parse テストを追加する
- [x] arXiv collector の URL 組み立てテストを追加する
- [x] 実ニュース用の `config/sources.live.example.yml` を追加する

## Next Milestone: Better Signal Quality

目標: ただ集めるだけでなく、AIニュースとして読みやすく、後でLLMに渡しやすい形にする。

- [x] `NewsItem` に `content_hash` または `canonical_key` を追加し、保存後も重複判定を追跡しやすくする
- [x] dedupe の判定理由をログまたは JSON に残す
- [x] processed JSON metadata に score breakdown と dedupe trace を残す
- [x] ranker の重みを設定ファイルから調整できるようにする
- [x] Daily が Hacker News だけで埋まらないよう source diversity を入れる
- [x] wiki Markdown に「source coverage」「dedupe notes」「open questions」を追加する
- [x] script writer に短め / 標準 / 詳しめの出力モードを追加する
- [x] 生成物のファイル名を `YYYY-MM-DD` と run id で衝突しないよう整理する

## Next Milestone: VOICEVOX MVP

目標: ローカル VOICEVOX engine が起動している環境で、script から wav まで生成する。

- [x] `voicevox.healthcheck()` を追加して、engine 接続可否を CLI で事前確認する
- [x] `ai-signal-radio tts` サブコマンドを追加し、既存 script から wav を生成できるようにする
- [x] VOICEVOX が無効または未起動のときのエラー文を親切にする
- [x] speaker、speed、pitch、intonation を config で調整できるようにする
- [x] 固有名詞の読み替えは、グローバル辞書ではなく番組・分野ごとの任意 profile として検討する
- [x] TTS はネットワークテストを避け、HTTP 呼び出し部分をモック可能にする

## Later

- [x] 過去 raw JSON を読み込んで再処理する `rebuild` サブコマンドを追加する
- [x] source ごとの rate limit / timeout を設定可能にする
- [x] Markdown wiki を日次だけでなく topic ページへ分割する
- [x] LLM summarizer の差し込み口を作る。ただし hidden network call はしない
- [x] Ollama summarizer のプロンプトと日本語出力品質を改善する
- [x] ローカルスケジューラ利用例を docs に追加する
- [x] GitHub Actions でテストだけ走らせる

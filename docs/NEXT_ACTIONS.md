# Next Actions

ai-signal-radio の次の実装アクションを `[x]` / `[ ]` で管理するためのメモ。

## Current State

- [x] Python 3.11+ / uv のプロジェクト骨格を作る
- [x] ローカルデモソースで end-to-end に動く CLI を作る
- [x] raw JSON、wiki Markdown、radio script を `data/` 配下へ保存する
- [x] processed JSON に deduped/ranked selected items と score/dedupe trace を保存する
- [x] RSS、arXiv、Hacker News、VOICEVOX の初期インターフェースを置く
- [x] pytest でモデル、重複排除、wiki writer をテストする
- [x] canonical URL / title normalization を共有 module に集約する
- [x] wiki note builder / Markdown writer / topic page writer の責務を分ける
- [x] daily listening では `briefing` style を推奨する
- [x] deterministic foundation と LLM editorial skill の責務分担を docs に整理する

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
- [x] Daily では topic cluster が離れた項目を優先して選抜する
- [x] 収集候補数 `--collect-limit` と最終選抜数 `--limit` を分離する
- [x] AI 固定の語彙・番組文言を `config/topics/ai.yml` に切り出す
- [x] `security` / `developer-tools` の topic profile sample を追加する
- [x] 別 topic を試す README 導線と source example を追加する
- [x] AI を用いたプロセス改善 topic profile と source example を追加する
- [x] 初回セットアップを `scripts/setup.sh` にまとめる
- [x] `scripts/setup.sh` で uv / Ollama model / VOICEVOX 起動確認まで案内する
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

## Next Milestone: Radio Quality

目標: 実ニュースを「聞いて理解できる」短い daily briefing にする。

詳細な改善計画は [Radio Quality Improvement Plan](RADIO_QUALITY_PLAN.md) にまとめる。

- [x] `script_writer` に `briefing` style を追加する
- [x] 上位 3 件を深めに、残りを一言ニュースにする
- [x] source line を読み上げ向きに自然な日本語へ整える
- [x] TTS 用に英語タイトル、記号、略語を正規化する
- [x] 近い話題を heuristic topic cluster としてまとめる
- [x] deep dive 用に Host / Analyst の掛け合い format を試す

## Next Milestone: LLM Editorial Skill

目標: 収集・重複排除・スコアリング・保存の土台は deterministic に残し、topic ごとの編集判断を明示的な LLM skill として追加する。

詳細な方針は [Foundation And Editorial Skill Plan](FOUNDATION_AND_EDITORIAL_SKILL.md) にまとめる。

### Phase 1: Config And Data Contract

まずは LLM を呼ばず、設定と保存形式だけを固定する。

- [x] `EditorialSkill` config model を追加する
- [x] `EditorialReview` model を追加し、JSON 保存できる形を固定する
- [x] `config/editorial/ai-process-improvement.yml` を topic sample として追加する
- [x] `read_in_daily` / `wiki_only` / `reject_reason` / `spoken_title` / `one_line_takeaway` の意味を docs に残す
- [x] config parse と default 値のテストを追加する

### Phase 2: Local LLM Reviewer

次に Ollama を使った editorial pass を opt-in で追加する。

- [x] `OllamaEditorialReviewer` を追加する
- [x] reviewer prompt は item の title / source / summary / score_breakdown / topic metadata だけを入力にする
- [x] LLM 出力は JSON parse し、壊れた出力は deterministic fallback にする
- [x] fake transport で JSON parse / fallback のテストを追加する
- [x] hidden network call が tests に入らないことを確認する

### Phase 3: Pipeline Integration

review 結果を processed JSON に残し、daily 選抜へ少しだけ反映する。

- [x] `run` / `rebuild` で `--editorial-skill` を受け取れるようにする
- [x] item ごとに `editorial_review` metadata を保存する
- [x] `relevance_score` / `read_in_daily` / `wiki_only` を final selection に反映する
- [x] LLM が落とした item も processed JSON から消さず、理由を追えるようにする
- [x] `best-current-run.sh` から `EDITORIAL_SKILL` / `EDITORIAL_MODEL` を渡せるようにする

### Phase 4: Radio Output Quality

最後に「聞いてよくなる」部分へ接続する。

- [x] `spoken_title` を briefing / deep dive の見出しに使う
- [x] `one_line_takeaway` を daily briefing の本文に使う
- [x] `listen_action` を締めの確認観点に反映する
- [ ] 実ニュースで deterministic only と editorial pass の daily を比較する
- [ ] 生成された `daily.md` / `daily.tts.txt` / wav を人間目線で確認する

## Architecture Notes

- [x] topic clustering は product term と keyword overlap による軽量 heuristic として扱う
- [x] ニュース処理の土台と番組編集の責務分担を明文化する
- [ ] topic clustering の誤結合 / 見逃しを、実ニュースのサンプルで定期的に確認する
- [ ] `standard` / `briefing` / `dialogue` の使い分けを CLI help にもう少し反映する

## Product Ideas

- [x] Run profile の Export / Import を追加する

  業務利用では、収集設定・topic・editorial skill・出力 style などを毎回手で合わせるより、用途別 profile として保存して再利用できる方が便利。

  例:

  ```json
  {
    "version": 1,
    "name": "Company Daily",
    "config": "config/sources.ai-process-improvement.example.yml",
    "topic": "config/topics/ai-process-improvement.yml",
    "editorialSkill": "config/editorial/ai-process-improvement.yml",
    "collectLimit": 40,
    "limit": 8,
    "summarizer": "ollama",
    "scriptStyle": "briefing"
  }
  ```

  実装メモ:

  - `uv run ai-signal profile export ...` で JSON を作る
  - `uv run ai-signal run --profile ...` で import して実行する
  - profile schema には `version` を持たせ、将来の設定項目追加に備える
  - import 時の unknown key は警告しつつ無視し、`--strict` では失敗させる

- [ ] PDF / document export profile を検討する

  ページ形式・見た目・安全設定・索引生成などをまとめる profile は、PDF / document export 機能が入った時点で別 schema として検討する。

  例:

  ```json
  {
    "version": 1,
    "name": "Company Spec A4",
    "pageFormat": "A4",
    "stylePreset": "github",
    "securityMode": "block-all",
    "includeBookmarks": true,
    "includePdfIndex": true
  }
  ```

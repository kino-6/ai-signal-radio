# Radio Quality Improvement Plan

実ニュース demo を聞いた結果をもとに、AI Signal Radio を「毎日聞けるラジオ」に近づけるための改善計画。

## Current Demo Findings

- [x] 実ニュースを収集し、Ollama で日本語 wiki / radio script へ変換できた
- [x] VOICEVOX で `data/audio/daily-live.wav` まで生成できた
- [x] MkDocs で daily / graph / radio script を確認できた
- [ ] arXiv が 429 のときに Hacker News だけへ偏る問題がある
- [x] Sova AI のような近い話題が別ニュースとして重複する
- [x] 英語タイトルがそのまま読み上げられ、TTS では聞き取りにくい
- [x] 「取得元は hacker-news-ai です」が機械的で番組らしくない
- [x] 詳細版 6 件は約 4 分 45 秒で、日常的に聞くには少し長い

## Product Direction

このプロジェクトの主目的は「速すぎる AI の動きを、あとで LLM に渡せる知識と、人間が聞ける短い音声に変換すること」。

そのため、単に記事を読むのではなく、次の 3 層に分けて品質を上げる。

- 事実: 何が起きたか、どのソースから来たか
- 意味: なぜ AI / LLM 開発者に関係するか
- 次の行動: 読む、試す、監視する、保留する

## Improvement Roadmap

### Priority Backlog: Speaking Quality

- [x] P0: wiki 要約と番組用の言葉を分けるため、`spoken_title` / `one_line_takeaway` / `why_it_matters` / `listen_action` を持つ
- [x] P1: Daily 冒頭に「今日はこれだけ覚える」を 1 文で入れる
- [x] P1: Deep Dive を質問主導にし、Host が事実、Analyst が疑問と論点を挟む
- [x] P2: score / source / cluster の理由を、内部語ではなく人間の判断理由に翻訳する
- [ ] P2: TTS 用に 1 文 40-60 字を目安に分割し、括弧を減らす
- [ ] P3: 締めの「今日の実装観点」をニュース内容から毎回少し変える
- [ ] P3: 話速、間、イントネーション preset を用途別に docs 化する

### Phase 1: Radio Script Editing

- [x] `script_writer` に `briefing` style を追加する
- [x] 上位 3 件は深めに、残りは一言ニュースにする
- [x] 冒頭で「今日の流れ」を 1 文で伝える
- [x] 各ニュースの source line を「Hacker News より」「arXiv より」のように自然にする
- [x] score / source_type / points をもとに、読み上げる情報量を調整する
- [x] 締めに「今日の実装観点」を 1 つだけ入れる

### Phase 2: TTS Readability

- [x] Markdown 見出しをそのまま読ませず、TTS 用本文を生成する
- [x] 英語タイトルを読み上げ用に短く言い換える
- [x] `AI`, `LLM`, `API`, `SDK`, `Vercel`, `LangGraph` などを文脈内で読みやすく整形する
- [x] カンマ抜け、括弧、記号、URL 由来のノイズを TTS 前に正規化する
- [x] `script` と `tts_script` を分け、Markdown と音声用テキストを別管理する
- [ ] 話速、間、イントネーションの推奨 preset を docs に残す

### Phase 3: Semantic Dedupe And Topic Clustering

- [x] URL / title dedupe の後に、近いタイトルを topic cluster としてまとめる
- [x] 同一 topic 内では代表記事を 1 本選び、補足ソースを metadata に残す
- [x] Sova AI のような `Show HN` / follow-up 記事を 1 セグメントに統合する
- [x] cluster reason を processed JSON に保存する
- [x] wiki note に related sources を出す

### Phase 4: Source Balance And Reliability

- [ ] arXiv 429 時の retry / backoff / cache を追加する
- [x] ソースごとの最低 / 最大採用数を設定できるようにする
- [x] HN に偏った日は、冒頭で「今日は HN 中心」と明示する
- [x] RSS / official source / research / community の coverage を daily metadata に出す
- [x] 取得失敗ソースを daily script の末尾ではなく metadata に残す

### Phase 5: Deep Dive Format

- [x] daily の最後に「今日の深掘り候補」を 1 件選ぶ
- [x] 深掘り候補の選定理由を score breakdown と cluster 情報から説明する
- [x] deep dive 用 wiki note に「背景」「技術的論点」「試す価値」「未確認事項」を追加する
- [x] deep dive script は 3-5 分版として daily とは別ファイルにする
- [x] 深掘りでは、事実と推測を明確に分ける

## Dialogue Format Idea

掛け合いは有効。特に深掘りでは、聞き手の頭の中に出る疑問をもう一人の声が代弁できる。

最初は二役にする。

- Host: ニュースを短く整理する。事実、出典、今日の流れを担当する
- Analyst: 「なぜ重要か」「何を試すべきか」「どこが未確認か」を質問形式で掘る

例:

```text
Host: 今日の注目は、モバイル AI エージェントが Google Play の審査で止まった話です。
Analyst: これは単なるストア審査の話ではなく、AI がスマホをどこまで操作してよいか、という境界の話ですね。
Host: 取得元は Hacker News。関連投稿が複数あり、今回は Sova AI という Android エージェントをひとつの話題として扱います。
Analyst: 開発者目線では、アクセシビリティ API に依存する設計がどこまで持続可能かを見たいです。
```

## Dialogue Guardrails

- [x] 掛け合いは deep dive から導入し、daily 全体には入れすぎない
- [x] Host は事実、Analyst は解釈と問いを担当する
- [x] 未確認の推測は「まだ確認が必要」と言う
- [x] キャラクター性より、聞きやすさと理解を優先する
- [ ] 1 セグメントは 45-90 秒を目安にする

## First Implementation Slice

まずは小さく、次を実装する。

- [x] `script_writer` に `briefing` style を追加する
- [x] `briefing` は上位 3 件を通常紹介し、4 件目以降を一言ニュースにする
- [x] source line を読み上げ向きに整える
- [x] TTS 用に英語タイトルを短くする helper を追加する
- [x] 既存 tests に `briefing` style の期待値を追加する
- [x] 実ニュースで `uv run ai-signal run ... --script-style briefing` を試す

## Later Questions

- [x] Host / Analyst を VOICEVOX の別 speaker に割り当てるか
- [ ] deep dive を daily 実行時に必ず作るか、手動コマンドにするか
- [ ] Ollama model ごとに script 品質差を比較するか
- [ ] audio metadata と MkDocs への音声リンクをどう扱うか

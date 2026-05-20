# Foundation And Editorial Skill Plan

ai-signal-radio は、ローカルでニュースを集め、重複を整理し、wiki とラジオ音声まで出す土台がかなり固まってきた。

次の品質向上は、コマンドやヒューリスティックを細かく増やすより、編集判断を LLM に渡す方が効果が大きそう。

## Current Foundation

すでにコード側で安定させたい土台はかなり揃っている。

- [x] RSS / Atom、arXiv、Hacker News から収集できる
- [x] collector ごとの timeout / retry / rate limit を設定できる
- [x] 1 ソースが失敗しても他ソースで続行できる
- [x] raw JSON、processed JSON、dedupe report、run metadata を保存できる
- [x] canonical URL / title normalization / content hash を共有化している
- [x] URL / title dedupe と dedupe trace を残せる
- [x] score breakdown を processed JSON に残せる
- [x] source diversity と topic diversity で daily selection を制御できる
- [x] `--collect-limit` と `--limit` を分離し、広く集めて少なく読む運用ができる
- [x] topic profile で番組名、対象読者、スコア語彙、解釈観点を切り替えられる
- [x] wiki note、topic page、daily script、deep dive script を生成できる
- [x] VOICEVOX 用 TTS text と wav を生成できる
- [x] `best-current-run.sh` で日次実行をまとめられる
- [x] MkDocs preview で wiki / radio / graph / audio を確認できる

この部分は deterministic な土台として残す。ここを LLM に任せすぎると、再現性とデバッグ性が落ちる。

## What Should Stay Deterministic

コード側で持ち続けるべき責務:

- 収集 source の実行
- canonical key と dedupe
- scoring の内訳保存
- source / topic diversity の制御
- run id、timestamp、metadata 保存
- wiki / script / audio のファイル出力
- VOICEVOX 接続、speaker、speed、読み替え
- fallback summary と fallback script
- テストで固定すべき入出力

これは「素材と証跡を安定して作る層」。

## What Should Move Toward LLM Editorial Skill

LLM に渡した方が品質が上がりそうな責務:

- topic に本当に関係あるニュースかの判定
- daily で読むべきか、wiki に残すだけでよいかの判断
- topic ごとの重要性の見立て
- 「なぜ重要か」を対象読者向けに翻訳すること
- 似ているが別物の話題、別物に見えるが同じ話題の判断
- 聞きやすい spoken title / one-line takeaway の作成
- deep dive の問いの設計
- 締めの「今日の確認観点」をニュース内容から作ること
- topic sample demo として見せるときの編集方針

これは「素材を番組にする編集層」。

## Why Topic Profiles Alone Are Not Enough

Topic profile は便利だが、YAML の keyword だけでは限界がある。

例: `ai-process-improvement`

- `AI`, `agent`, `automation` は広すぎる
- 研究として面白いが、業務プロセス改善とは遠いものも拾う
- 逆に、タイトルに `workflow` がなくてもプロセス改善に効く話がある
- 「この topic sample として聞かせる価値があるか」は文脈判断が必要

したがって topic profile は粗い方向づけとして残し、その後に LLM editorial pass を入れるのがよい。

## Proposed Pipeline

次の形を目指す。

```text
collect
  -> dedupe
  -> deterministic score
  -> source/topic diversity candidate set
  -> LLM editorial pass
  -> wiki notes
  -> radio script
  -> TTS text
  -> VOICEVOX audio
```

重要なのは、LLM に全部を渡すのではなく、証跡付きの候補を渡すこと。

## Editorial Skill Concept

`topic profile` より一段上に、編集方針としての skill を置く。

候補:

```text
config/editorial/ai-process-improvement.yml
```

例:

```yaml
name: ai-process-improvement
audience: 業務改善担当者・開発リーダー
purpose: AIを使って業務、開発、運用プロセスをどう改善するかを短く聞ける形にする
accept:
  - AIで業務フロー、開発プロセス、レビュー、仕様化、運用を改善する話
  - 導入判断、ROI、組織知、責任分界に関係する話
  - 現場で小さく試せる自動化やナレッジ共有の話
reject:
  - AIモデル性能だけの話
  - プロセス改善に直接つながらない画像認識や医療AIの研究
  - 単なるエージェント実装ライブラリ紹介
radio_style:
  framing: 自分の業務にどう小さく適用できるかを必ず言う
```

## Editorial Pass Output

LLM には JSON を返させる。

```json
{
  "relevance_score": 4,
  "read_in_daily": true,
  "wiki_only": false,
  "why_relevant": "一人チームの開発プロセス設計に直接関係するため。",
  "process_improvement_angle": "仕様定義と既存知識の形式知化をAIに渡す設計が重要。",
  "spoken_title": "AI支援による一人チームの成果事例",
  "one_line_takeaway": "AIはチームを置き換えるより、経験者の生産性を高める道具として効きます。",
  "listen_action": "自分の業務で、仕様化が詰まっている箇所を1つ選びます。",
  "reject_reason": ""
}
```

この出力は processed JSON metadata に保存する。

## CLI Direction

最初は明示的 opt-in にする。

```bash
uv run ai-signal run \
  --config config/sources.ai-process-improvement.example.yml \
  --topic config/topics/ai-process-improvement.yml \
  --editorial-skill config/editorial/ai-process-improvement.yml \
  --editorial-model gemma4:latest \
  --collect-limit 40 \
  --limit 8 \
  --script-style briefing
```

`best-current-run.sh` では環境変数で切り替える。

```bash
EDITORIAL_SKILL=config/editorial/ai-process-improvement.yml \
EDITORIAL_MODEL=gemma4:latest \
bash scripts/best-current-run.sh
```

## Guardrails

- [x] editorial pass は明示的に有効化したときだけ動く
- [x] tests では hidden network call をしない
- [x] LLM failure 時は deterministic selection に fallback する
- [x] LLM 出力は JSON parse し、壊れた出力は採用しない
- [x] LLM が落とした item も processed JSON に `wiki_only` または `reject_reason` として残す
- [ ] fact summary は入力情報だけを根拠にする
- [ ] 推測は `open_questions` に逃がす

## Next Implementation Slice

小さく始める。まずは LLM を呼ばずに contract を固定し、その後に opt-in で Ollama reviewer を挿す。

### Phase 1: Config And Data Contract

- [x] `EditorialSkill` config model を追加する
- [x] `EditorialReview` model を追加し、JSON 保存できる形を固定する
- [x] `config/editorial/ai-process-improvement.yml` を topic sample として追加する
- [x] config parse と default 値のテストを追加する

### Phase 2: Local LLM Reviewer

- [x] `OllamaEditorialReviewer` を追加する
- [x] reviewer prompt は item の title / source / summary / score_breakdown / topic metadata だけを入力にする
- [x] LLM 出力は JSON parse し、壊れた出力は deterministic fallback にする
- [x] fake transport で JSON parse / fallback のテストを追加する

### Phase 3: Pipeline Integration

- [x] `run` / `rebuild` で `--editorial-skill` を受け取れるようにする
- [x] item ごとに `editorial_review` metadata を保存する
- [x] `relevance_score` と `read_in_daily` を final selection に反映する
- [x] LLM が落とした item も processed JSON から消さず、理由を追えるようにする
- [x] `best-current-run.sh` から `EDITORIAL_SKILL` / `EDITORIAL_MODEL` を渡せるようにする

### Phase 4: Radio Output Quality

- [x] `spoken_title` を briefing / deep dive の見出しに使う
- [x] `one_line_takeaway` を daily briefing の本文に使う
- [x] `listen_action` を締めの確認観点に反映する
- [ ] 実ニュースで deterministic only と editorial pass の daily を比較する

## Current Judgment

土台はかなり完成に近い。

今後は、土台をさらにコマンドで細かく調整するより、LLM に渡す編集 skill を整えた方が、topic sample demo の品質が上がる。

特に `ai-process-improvement` のような抽象度の高い話題は、keyword だけではなく「この番組で読む価値があるか」という編集判断が必要。

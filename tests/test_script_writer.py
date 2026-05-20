from datetime import datetime, timezone

from ai_signal_radio.models import WikiNote
from ai_signal_radio.config import TopicProfile
from ai_signal_radio.processors.script_writer import render_script


def test_render_script_is_japanese_tts_friendly() -> None:
    note = WikiNote(
        title="LLM agent update",
        source="example-rss",
        source_url="https://example.com",
        source_type="rss",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
        fact_summary="新しいエージェント機能が公開されました。",
        interpretation="開発者のワークフローに影響する可能性があります。",
        action_items=("元記事を確認する",),
        score=5.0,
    )

    script = render_script([note])

    assert script.startswith("# Daily AI Signal Radio")
    assert "こんにちは。今日のAIニュースです。" in script
    assert "今日の注目トピックは 1 件です。" in script
    assert "取得元は example-rss です。" in script
    assert "それでは、今日もよい開発を。" in script


def test_render_script_uses_topic_profile_program_text() -> None:
    note = WikiNote(
        title="CVE advisory",
        source="CISA",
        source_url="https://example.com",
        source_type="rss",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("security",),
        fact_summary="CISA が脆弱性情報を公開しました。",
        interpretation="運用リスクの確認が必要です。",
        action_items=("元情報を確認する",),
    )
    profile = TopicProfile(
        name="security",
        program_title="Security Signal Radio",
        briefing_intro="今日のセキュリティニュースです。",
        audience="セキュリティ担当者",
        focus_action_line="今日の確認観点は、影響範囲を小さく切り分けることです。",
        closing_line="それでは、今日も安全に運用しましょう。",
    )

    script = render_script([note], style="briefing", topic_profile=profile)

    assert script.startswith("# Security Signal Radio")
    assert "こんにちは。今日のセキュリティニュースです。" in script
    assert "今日の確認観点は、影響範囲を小さく切り分けることです。" in script
    assert "それでは、今日も安全に運用しましょう。" in script


def test_render_script_supports_length_styles() -> None:
    note = WikiNote(
        title="LLM agent update",
        source="example-rss",
        source_url="https://example.com",
        source_type="rss",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
        fact_summary="新しいエージェント機能が公開されました。",
        interpretation="開発者のワークフローに影響する可能性があります。",
        action_items=("元記事を確認する",),
        score=5.0,
    )

    short = render_script([note], style="short")
    detailed = render_script([note], style="detailed")

    assert "開発者のワークフロー" not in short
    assert "次のアクションは、元記事を確認する" in detailed


def test_render_script_supports_briefing_style() -> None:
    notes = [
        WikiNote(
            title="Show HN: Android AI agent-assistant operating your apps (no adb,PC,root,etc.)",
            source="hacker-news-ai",
            source_url="https://example.com/hn-1",
            source_type="hackernews",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            tags=("ai",),
            fact_summary="Androidアプリを操作するAIエージェントが公開されました。",
            interpretation="モバイルAIの実用化に関わる動きです。",
            action_items=("デモを確認する",),
            score=9.0,
        ),
        WikiNote(
            title="Show HN: Torrix, self hosted, LLM Observability,(no Postgres, no Redis)",
            source="hacker-news-ai",
            source_url="https://example.com/hn-2",
            source_type="hackernews",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            tags=("llm",),
            fact_summary="LLMの監視ツールが公開されました。",
            interpretation="小さなチームでも導入しやすい点が重要です。",
            action_items=("SQLiteの制約を確認する",),
            score=8.0,
        ),
        WikiNote(
            title="$38k AWS Bedrock bill caused by a simple prompt caching miss",
            source="hacker-news-ai",
            source_url="https://example.com/hn-3",
            source_type="hackernews",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            tags=("ai", "cost"),
            fact_summary="プロンプトキャッシュの不備で高額請求が発生しました。",
            interpretation="AIエージェント運用には支出制御が必要です。",
            action_items=("予算アラートを確認する",),
            score=7.0,
        ),
        WikiNote(
            title="Show HN: OpenHarness Open-source terminal coding agent for any LLM",
            source="hacker-news-ai",
            source_url="https://example.com/hn-4",
            source_type="hackernews",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            tags=("llm", "coding"),
            fact_summary="任意のLLMを使えるコーディングエージェントです。",
            interpretation="ローカル開発環境との接続が見どころです。",
            action_items=("READMEを読む",),
            score=6.0,
        ),
    ]

    script = render_script(notes, style="briefing")

    assert "今日はこれだけ覚えてください。" in script
    assert "まずは上位 2 件だけを押さえて、そのあと 2 件を一言で拾います。" in script
    assert "## 一言ニュース" in script
    assert "Show HN:" not in script
    assert "Android AI agent-assistant operating your apps" not in script
    assert "取得元は" not in script
    assert "Hacker News より。" in script
    assert "見るポイントは、デモを確認する。" in script
    assert "プロンプトキャッシュの不備で高額請求が発生しました。" in script
    assert "ローカル開発環境との接続が見どころです。" not in script
    assert "## 今日の深掘り候補" in script
    assert "詳細は深掘り版で扱います。" in script
    assert "score breakdown" not in script
    assert "source type" not in script
    assert "今日の実装観点" in script


def test_briefing_style_collapses_topic_clusters() -> None:
    representative = WikiNote(
        title="Google banned our mobile AI agent app",
        source="hacker-news-ai",
        source_url="https://example.com/hn-1",
        source_type="hackernews",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
        fact_summary="Sova AIがGoogle Playで却下されました。",
        interpretation="モバイルAIエージェントの境界に関わる話です。",
        action_items=("デモを確認する",),
        topic_cluster_id="topic-sova",
        topic_cluster_label="Sova",
        topic_cluster_size=2,
        topic_cluster_representative=True,
        related_titles=("Android AI agent-assistant operating your apps",),
    )
    duplicate_topic = WikiNote(
        title="Android AI agent-assistant operating your apps",
        source="hacker-news-ai",
        source_url="https://example.com/hn-2",
        source_type="hackernews",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
        fact_summary="Sova AIがAndroidアプリを操作します。",
        interpretation="同じ話題です。",
        action_items=("APKを確認する",),
        topic_cluster_id="topic-sova",
        topic_cluster_label="Sova",
        topic_cluster_size=2,
        topic_cluster_representative=False,
    )

    script = render_script([representative, duplicate_topic], style="briefing")

    assert "収集した 2 件を、重複する話題をまとめて 1 トピックに整理しました。" in script
    assert "関連投稿 2 件をまとめています。" in script
    assert "Android AI agent-assistant operating your apps" not in script
    assert "## 1. Sova AIのモバイルエージェントがGoogle Playで却下" in script


def test_briefing_keeps_selected_non_representative_notes_from_different_clusters() -> None:
    notes = [
        WikiNote(
            title="Code as Agent Harness",
            source="arxiv-ai",
            source_url="https://example.com/arxiv-1",
            source_type="arxiv",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            tags=("ai",),
            fact_summary="コードをエージェント実行基盤として扱う研究です。",
            interpretation="エージェント実装の設計に関係します。",
            action_items=("論文を確認する",),
            topic_cluster_id="topic-agent",
            topic_cluster_label="Agent",
            topic_cluster_size=5,
            topic_cluster_representative=False,
        ),
        WikiNote(
            title="Vision-OPD",
            source="arxiv-ai",
            source_url="https://example.com/arxiv-2",
            source_type="arxiv",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            tags=("ai",),
            fact_summary="マルチモーダルLLMの細部認識を扱う研究です。",
            interpretation="評価と視覚モデル改善に関係します。",
            action_items=("実験設定を確認する",),
            topic_cluster_id="topic-vision",
            topic_cluster_label="Vision",
            topic_cluster_size=4,
            topic_cluster_representative=False,
        ),
    ]

    script = render_script(notes, style="briefing")

    assert "今日の注目トピックは 2 件です。" in script
    assert "収集した 2 件を、重複する話題をまとめて 2 トピックに整理しました。" not in script
    assert "コードをエージェント実行基盤として扱う研究です。" in script
    assert "マルチモーダルLLMの細部認識を扱う研究です。" in script


def test_dialogue_style_renders_deep_dive() -> None:
    note = WikiNote(
        title="Google banned our mobile AI agent app",
        source="hacker-news-ai",
        source_url="https://example.com/hn-1",
        source_type="hackernews",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
        fact_summary="Sova AIがGoogle Playで却下されました。",
        interpretation="モバイルAIエージェントの境界に関わる話です。",
        action_items=("デモを確認する",),
        open_questions=("Google Playの審査基準を確認する",),
        topic_cluster_id="topic-sova",
        topic_cluster_label="Sova",
        topic_cluster_size=2,
        topic_cluster_representative=True,
        related_titles=("Android AI agent-assistant operating your apps",),
    )

    script = render_script([note], style="dialogue")

    assert script.startswith("# AI Signal Radio Deep Dive")
    assert "今日のテーマは「Sova AIのモバイルエージェントがGoogle Playで却下」です。" in script
    assert "Host:" in script
    assert "Analyst:" in script
    assert "Analyst: まず、これは何が起きた話ですか？" in script
    assert "Analyst: それは、AI開発者にとってなぜ重要なんでしょう？" in script
    assert "Analyst: では、次にどこを見るとよさそうですか？" in script
    assert "## 事実" in script
    assert "## 解釈" in script
    assert "## 試す価値" in script
    assert "## 未確認事項" in script
    assert "Host: モバイルAIエージェントの境界に関わる話です。" in script
    assert "Host: Google Playの審査基準を確認する。" in script
    assert "関連投稿 2 件をまとめて見ています。" in script


def test_dialogue_style_keeps_japanese_question_punctuation() -> None:
    note = WikiNote(
        title="AI agent policy update",
        source="example",
        source_url="https://example.com",
        source_type="rss",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
        fact_summary="新しいポリシーが出ました。",
        interpretation="開発者に影響します。",
        action_items=("内容を確認する",),
        open_questions=("実装への影響は？",),
    )

    script = render_script([note], style="dialogue")

    assert "実装への影響は？。" not in script
    assert "実装への影響は？" in script


def test_briefing_uses_japanese_spoken_headline_for_english_title() -> None:
    note = WikiNote(
        title="$38k AWS Bedrock bill caused by a simple prompt caching miss",
        source="hacker-news-ai",
        source_url="https://example.com/hn-1",
        source_type="hackernews",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
        fact_summary="プロンプトキャッシュの不備で高額請求が発生しました。",
        interpretation="AIエージェント運用には支出制御が必要です。",
        action_items=("予算アラートを確認する",),
    )

    script = render_script([note], style="briefing")

    assert "$38k AWS Bedrock bill caused by a simple prompt caching miss" not in script
    assert "## 1. AWS Bedrockのプロンプトキャッシュ不備で高額請求" in script


def test_briefing_prefers_radio_note_fields() -> None:
    note = WikiNote(
        title="Long internal title that should not be spoken",
        source="example-rss",
        source_url="https://example.com/radio-fields",
        source_type="rss",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
        fact_summary="長い事実要約です。",
        interpretation="長い解釈です。",
        action_items=("長いアクションです",),
        spoken_title="耳で聞く短い見出し",
        one_line_takeaway="今日覚えることは、番組用の要点を別に持つことです。",
        why_it_matters="なぜ重要かというと、要約文をそのまま読まずに済むからです。",
        listen_action="次に見るポイントは、生成された台本の聞きやすさです。",
    )

    script = render_script([note], style="briefing")

    assert "## 1. 耳で聞く短い見出し" in script
    assert "今日覚えることは、番組用の要点を別に持つことです。" in script
    assert "なぜ重要かというと、要約文をそのまま読まずに済むからです。" in script
    assert "次に見るポイントは、生成された台本の聞きやすさです。" in script
    assert "今日の確認観点です。次に見るポイントは、生成された台本の聞きやすさです。" in script
    assert "長い事実要約です。" not in script
    assert "長い解釈です。" not in script


def test_briefing_opens_with_single_focus_takeaway() -> None:
    note = WikiNote(
        title="Focus topic",
        source="example-rss",
        source_url="https://example.com/focus",
        source_type="rss",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
        fact_summary="重要な更新です。",
        interpretation="重要です。",
        action_items=("確認する",),
        spoken_title="今日の本命ニュース",
        one_line_takeaway="AIエージェントの権限管理を見る回です。",
        score=10.0,
    )

    script = render_script([note], style="briefing")

    assert "今日はこれだけ覚えてください。今日の本命ニュース。AIエージェントの権限管理を見る回です。" in script


def test_briefing_mentions_when_source_mix_is_biased() -> None:
    notes = [
        WikiNote(
            title=f"AI topic {index}",
            source="hacker-news-ai",
            source_url=f"https://example.com/{index}",
            source_type="hackernews",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            tags=("ai",),
            fact_summary="AI関連のニュースです。",
            interpretation="開発者に関係します。",
            action_items=("元記事を確認する",),
        )
        for index in range(4)
    ]

    script = render_script(notes, style="briefing")

    assert "今日は Hacker News で見えている開発者向けトピックが中心です。" in script
    assert "実行メタデータ" in script
    assert "取得ログ" not in script


def test_briefing_selects_deep_dive_candidate_by_score_and_cluster() -> None:
    notes = [
        WikiNote(
            title="Small topic",
            source="rss",
            source_url="https://example.com/a",
            source_type="rss",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            tags=("ai",),
            fact_summary="小さな話題です。",
            interpretation="影響は限定的です。",
            action_items=("読む",),
            score=2.0,
        ),
        WikiNote(
            title="Important clustered topic",
            source="hacker-news-ai",
            source_url="https://example.com/b",
            source_type="hackernews",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            tags=("ai",),
            fact_summary="重要な話題です。",
            interpretation="影響が大きいです。",
            action_items=("試す",),
            score=8.0,
            score_reasons=("keyword_score=4.0", "hn_points_bonus=2.0"),
            topic_cluster_id="topic-important",
            topic_cluster_label="Important",
            topic_cluster_size=3,
            topic_cluster_representative=True,
        ),
    ]

    script = render_script(notes, style="briefing")

    assert "重要な話題ですを深掘り候補にします。" in script
    assert "関連投稿が複数あります" in script
    assert "詳細は深掘り版で扱います。" in script
    assert "score breakdown" not in script
    assert "source type" not in script


def test_dialogue_deep_dive_reason_uses_human_language() -> None:
    note = WikiNote(
        title="Important clustered topic",
        source="hacker-news-ai",
        source_url="https://example.com/b",
        source_type="hackernews",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
        fact_summary="重要な話題です。",
        interpretation="影響が大きいです。",
        action_items=("試す",),
        score=8.0,
        score_reasons=("keyword_score=4.0", "hn_points_bonus=2.0"),
        topic_cluster_id="topic-important",
        topic_cluster_label="Important",
        topic_cluster_size=3,
        topic_cluster_representative=True,
    )

    script = render_script([note], style="dialogue")

    assert "関連投稿が 3 件あり、単発ではない動きに見える" in script
    assert "Hacker News で実装者の反応を追いやすい" in script
    assert "開発ツールやモデル運用の話題として試しやすいこと" in script
    assert "AI関連キーワードの重み" not in script
    assert "score breakdown" not in script
    assert "keyword_score" not in script
    assert "source type" not in script


def test_dialogue_uses_radio_takeaway_when_fact_summary_is_not_japanese() -> None:
    note = WikiNote(
        title="English fact topic",
        source="demo",
        source_url="https://example.com/english",
        source_type="demo",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        tags=("ai",),
        fact_summary="A project added benchmark support.",
        interpretation="開発者に関係します。",
        action_items=("確認する",),
        one_line_takeaway="AI評価ベンチマークの更新です。",
    )

    script = render_script([note], style="dialogue")

    assert "Host: AI評価ベンチマークの更新です。" in script
    assert "Host: A project added benchmark support." not in script

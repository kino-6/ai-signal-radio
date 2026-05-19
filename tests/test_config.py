from ai_signal_radio.config import load_config, load_topic_profile


def test_load_config_reads_tts_voice_controls(tmp_path) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(
        """
tts:
  enabled: true
  endpoint: "http://127.0.0.1:50021"
  speaker: 3
  speed_scale: 1.25
  pitch_scale: 0.02
  intonation_scale: 1.1
  pronunciation_profile: "config/pronunciations.yml"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.tts.enabled is True
    assert config.tts.speaker == 3
    assert config.tts.speed_scale == 1.25
    assert config.tts.pitch_scale == 0.02
    assert config.tts.intonation_scale == 1.1
    assert config.tts.pronunciation_profile == "config/pronunciations.yml"


def test_load_config_reads_ranker_source_diversity(tmp_path) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(
        """
ranker:
  max_topic_cluster_items: 2
  min_source_types:
    arxiv: 2
    rss: 1
  max_source_types:
    hackernews: 2
""".strip(),
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.ranker.max_topic_cluster_items == 2
    assert config.ranker.min_source_types == {"arxiv": 2, "rss": 1}
    assert config.ranker.max_source_types == {"hackernews": 2}


def test_load_topic_profile_reads_program_and_scoring_terms(tmp_path) -> None:
    path = tmp_path / "security.yml"
    path.write_text(
        """
name: security
program_title: "Security Signal Radio"
briefing_intro: "今日のセキュリティニュースです。"
audience: "セキュリティ担当者"
interpretation_lens: "脆弱性対応、検知、運用リスク"
default_tags:
  - security
score_keywords:
  - cve
  - exploit
official_sources:
  - cisa
""".strip(),
        encoding="utf-8",
    )

    profile = load_topic_profile(path)

    assert profile.name == "security"
    assert profile.program_title == "Security Signal Radio"
    assert profile.briefing_intro == "今日のセキュリティニュースです。"
    assert profile.audience == "セキュリティ担当者"
    assert profile.default_tags == ("security",)
    assert profile.score_keywords == ("cve", "exploit")
    assert profile.official_sources == ("cisa",)

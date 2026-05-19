from ai_signal_radio.config import load_config


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

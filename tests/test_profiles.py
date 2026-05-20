import json

import pytest

from ai_signal_radio.profiles import RunProfile, load_run_profile, write_run_profile


def test_write_and_load_run_profile_round_trip(tmp_path) -> None:
    path = tmp_path / "company-a4.json"

    write_run_profile(
        path,
        RunProfile(
            name="Company Daily",
            config="config/sources.live.example.yml",
            topic="config/topics/ai.yml",
            editorial_skill="config/editorial/ai-process-improvement.yml",
            limit=8,
            collect_limit=40,
            source=("arxiv", "hackernews"),
            summarizer="ollama",
            ollama_model="gemma4:latest",
            script_style="briefing",
        ),
    )

    raw = json.loads(path.read_text(encoding="utf-8"))
    loaded = load_run_profile(path).profile

    assert raw["version"] == 1
    assert raw["collectLimit"] == 40
    assert raw["editorialSkill"] == "config/editorial/ai-process-improvement.yml"
    assert loaded.name == "Company Daily"
    assert loaded.source == ("arxiv", "hackernews")
    assert loaded.script_style == "briefing"


def test_load_run_profile_warns_on_unknown_keys_by_default(tmp_path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "name": "Company Spec A4",
                "config": "config/sources.example.yml",
                "pageFormat": "A4",
            }
        ),
        encoding="utf-8",
    )

    profile_doc = load_run_profile(path)

    assert profile_doc.profile.name == "Company Spec A4"
    assert profile_doc.warnings == ("unknown profile key ignored: pageFormat",)


def test_load_run_profile_strict_rejects_unknown_keys(tmp_path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(
        json.dumps({"version": 1, "name": "Company Spec A4", "pageFormat": "A4"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown keys"):
        load_run_profile(path, strict=True)

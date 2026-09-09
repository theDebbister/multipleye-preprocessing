"""Tests for the consolidated wide psychometric results output."""

import logging

import pandas as pd
import yaml

from preprocessing.config import settings
from preprocessing.psychometric_tests.preprocess_psychometric_tests import (
    _ordered_psychometric_columns,
    preprocess_all_sessions,
)


def _write_ran_csv(session_dir) -> None:
    ran_dir = session_dir / "RAN"
    ran_dir.mkdir(parents=True)
    (ran_dir / "ran.csv").write_text("Trial,Reading_Time\n1,1.5\n2,1.9\n")


def test_ordered_psychometric_columns():
    cols = [
        "notes",
        "WikiVocab_accuracy",
        "PLAB_accuracy",
        "LWMC_SS_score",
        "Stroop_accuracy",
        "session_id",
        "RAN_experimental_rt_sec",
        "Flanker_num_items",
        "PLAB_Done",
    ]
    id_cols = ["session_id", "participant_id", "session", "postfix", "notes"]
    flag_cols = [
        "LWMC_Done",
        "RAN_Done",
        "Stroop_Done",
        "Flanker_Done",
        "WikiVocab_Done",
        "PLAB_Done",
    ]
    ordered = _ordered_psychometric_columns(cols, id_cols, flag_cols)
    assert ordered == [
        "session_id",
        "notes",
        "PLAB_Done",
        "LWMC_SS_score",
        "RAN_experimental_rt_sec",
        "Stroop_accuracy",
        "Flanker_num_items",
        "WikiVocab_accuracy",
        "PLAB_accuracy",
    ]


def test_consolidated_output_single_wide_csv(tmp_path, monkeypatch):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()

    # Session 001: has a RAN test.
    s1 = sessions_dir / "001_DE_DE_1_PT1"
    s1.mkdir()
    _write_ran_csv(s1)

    # Session 002: no test data at all.
    s2 = sessions_dir / "002_DE_DE_1_PT1"
    s2.mkdir()

    output_dir = tmp_path / "output" / "dcn"
    monkeypatch.setattr(settings, "PSYCHOMETRIC_TESTS_DIR", sessions_dir)
    monkeypatch.setattr(settings, "OUTPUT_DIR", output_dir)
    settings.__dict__["DATA_COLLECTION_NAME"] = "dcn"

    results_path = preprocess_all_sessions(sessions_dir)

    assert (
        results_path
        == output_dir / "psychometric_tests" / "psychometric_results_dcn.csv"
    )

    df = pd.read_csv(results_path)

    # One row per session, wide with all columns.
    assert len(df) == 2
    assert {"session_id", "participant_id", "RAN_Done"}.issubset(df.columns)

    # Detailed-only columns are present alongside _Done flags.
    assert "RAN_practice_rt_sec" in df.columns
    assert "RAN_experimental_rt_sec" in df.columns

    # Session 001 has a done flag and values; session 002 is empty for RAN.
    row001 = df[df["session_id"] == "001_DE_DE_1_PT1"].iloc[0]
    row002 = df[df["session_id"] == "002_DE_DE_1_PT1"].iloc[0]
    assert row001["RAN_Done"] == 1
    assert row001["RAN_practice_rt_sec"] == 1.5
    assert row002["RAN_Done"] == 0
    assert pd.isna(row002["RAN_practice_rt_sec"])

    # No per-session detail subfolders are created.
    assert not (output_dir / "psychometric_tests" / "001_DE_DE_1_PT1").exists()

    # Merged per-participant file is also produced.
    merged_path = (
        output_dir / "psychometric_tests" / "psychometric_results_dcn_merged.csv"
    )
    assert merged_path.exists()
    merged = pd.read_csv(merged_path)
    assert len(merged) == 2


def test_preprocess_warns_missing_tests_from_session_configs(
    tmp_path, monkeypatch, caplog
):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()

    # Session 001: has RAN data, config additionally expects WikiVocab (no data).
    s1 = sessions_dir / "001_DE_DE_1_PT1"
    s1.mkdir()
    _write_ran_csv(s1)
    with open(s1 / "001_DE_DE_1_PT1.yaml", "w") as f:
        yaml.dump(
            {
                "plab": False,
                "ran": True,
                "stroop_flanker": False,
                "wmc": False,
                "wiki_vocab": True,
            },
            f,
        )

    output_dir = tmp_path / "output" / "dcn"
    monkeypatch.setattr(settings, "PSYCHOMETRIC_TESTS_DIR", sessions_dir)
    monkeypatch.setattr(settings, "OUTPUT_DIR", output_dir)
    settings.__dict__["DATA_COLLECTION_NAME"] = "dcn"

    with caplog.at_level(logging.WARNING):
        preprocess_all_sessions(sessions_dir)

    # Session-folder configs are discovered (no stale 'No configuration files' warning).
    assert "No configuration files" not in caplog.text
    # WikiVocab is expected per config but was not preprocessed -> consolidated warning.
    assert "Participants missing expected psychometric tests" in caplog.text
    assert "WikiVocab" in caplog.text
    assert "001_DE_DE_1" in caplog.text


def test_preprocess_processes_session_without_config(tmp_path, monkeypatch, caplog):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()

    # Session 001 has data (RAN) but no participant config YAML.
    s1 = sessions_dir / "001_DE_DE_1_PT1"
    s1.mkdir()
    _write_ran_csv(s1)

    output_dir = tmp_path / "output" / "dcn"
    monkeypatch.setattr(settings, "PSYCHOMETRIC_TESTS_DIR", sessions_dir)
    monkeypatch.setattr(settings, "OUTPUT_DIR", output_dir)
    settings.__dict__["DATA_COLLECTION_NAME"] = "dcn"

    with caplog.at_level(logging.WARNING):
        preprocess_all_sessions(sessions_dir)

    results_path = output_dir / "psychometric_tests" / "psychometric_results_dcn.csv"
    df = pd.read_csv(results_path, dtype={"participant_id": str})

    # The data-only session is processed with metadata derived from the folder name.
    assert len(df) == 1
    row = df.iloc[0]
    assert row["session_id"] == "001_DE_DE_1_PT1"
    assert row["participant_id"] == "001"
    assert row["RAN_Done"] == 1
    # No config present -> no consolidated missing-test warning.
    assert "Participants missing expected psychometric tests" not in caplog.text

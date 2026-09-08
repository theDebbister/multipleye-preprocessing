import pandas as pd

from preprocessing.config import settings
from preprocessing.psychometric_tests.preprocess_psychometric_tests import (
    create_merged_psychometric_overview,
    preprocess_all_sessions,
)


def test_non_compliant_sid_in_preprocess(tmp_path, monkeypatch):
    # Setup: Create a non-compliant session folder
    # Based on issue: 010_DE_Lueneburg_1_PT1.yaml (not SID compliant)
    # A compliant SID is like 001_en_UK_1_PT1 (3 digits, 2 chars lang, 2 chars country, lab, session)
    # 010_DE_Lueneburg_1_PT1: 010 (3), DE (2), Lueneburg (9! > 2), 1, PT1

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()

    non_compliant_folder = sessions_dir / "010_DE_Lueneburg_1_PT1"
    non_compliant_folder.mkdir()

    # Create a dummy yaml file inside
    (non_compliant_folder / "010_DE_Lueneburg_1_PT1.yaml").touch()

    output_dir = tmp_path / "output" / "dcn" / "psychometric_tests"
    monkeypatch.setattr(settings, "PSYCHOMETRIC_TESTS_DIR", sessions_dir)
    monkeypatch.setattr(settings, "OUTPUT_DIR", tmp_path / "output" / "dcn")
    settings.__dict__["DATA_COLLECTION_NAME"] = "dcn"

    overview_path = preprocess_all_sessions(sessions_dir)
    df = pd.read_csv(overview_path)

    assert overview_path == output_dir / "psychometric_results_dcn.csv"

    # Check session_id for non-compliant folder
    # The participant_id might also be extracted incorrectly if not compliant
    # 010_DE_Lueneburg_1_PT1 fallback pid was session.name[:3]
    row = df[df["participant_id"].astype(str).isin(["10", "010"])].iloc[0]
    assert row["session_id"] == "010_DE_Lueneburg_1_PT1"

    # The consolidated table also produces a merged per-participant file.
    assert (output_dir / "psychometric_results_dcn_merged.csv").exists()


def test_non_compliant_sid_in_merged_overview(tmp_path):
    # Setup: Create an overview CSV with non-compliant session_id
    data = [
        {
            "session_id": "010_DE_Lueneburg_1_PT1",
            "participant_id": "010",
            "LWMC_Done": 1,
            "RAN_Done": 0,
            "notes": "",
        }
    ]
    df = pd.DataFrame(data)
    overview_path = tmp_path / "psychometric_overview.csv"
    df.to_csv(overview_path, index=False)

    merged_path = create_merged_psychometric_overview(overview_path)
    merged_df = pd.read_csv(merged_path)

    row = merged_df.iloc[0]
    # The current fallback in get_base_sid: re.sub(r"_(S|PT|ET)\d+$", "", str(sid_str))
    # For "010_DE_Lueneburg_1_PT1", it should return "010_DE_Lueneburg_1"
    assert row["session_id"] == "010_DE_Lueneburg_1"
    assert row["original_sessions"] == "010_DE_Lueneburg_1_PT1"

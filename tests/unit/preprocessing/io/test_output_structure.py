import polars as pl
import pymovements as pm
import pytest

from preprocessing.config import settings
from preprocessing.io.load import (
    load_reading_measures,
    load_scanpaths,
    load_trial_level_events_data,
    load_trial_level_raw_data,
)
from preprocessing.io.save import (
    save_events_data,
    save_raw_data,
    save_reading_measures,
    save_scanpaths,
    save_session_metadata,
)
from preprocessing.models.sid import Sid

SID_STRINGS = ["001_EN_UK_1_S1", "017_DA_DK_1_ET1_start_after_trial_3"]


@pytest.fixture(autouse=True)
def _set_output_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(type(settings), "OUTPUT_DIR", tmp_path)


@pytest.fixture
def dummy_gaze():
    df = pl.DataFrame(
        {
            "time": [0.0, 1.0, 2.0],
            "pixel_x": [100.0, 101.0, 102.0],
            "pixel_y": [200.0, 201.0, 202.0],
            "pupil": [10.0, 11.0, 12.0],
            "trial": ["trial_1", "trial_1", "trial_1"],
            "stimulus": ["Enc_WikiMoon_1", "Enc_WikiMoon_1", "Enc_WikiMoon_1"],
            "page": ["page_1", "page_1", "page_1"],
            "position_x": [100.0, 101.0, 102.0],
            "position_y": [200.0, 201.0, 202.0],
            "velocity_x": [100.0, 101.0, 102.0],
            "velocity_y": [200.0, 201.0, 202.0],
        }
    )
    gaze = pm.Gaze(
        df,
        trial_columns=["trial", "stimulus", "page"],
        pixel_columns=["pixel_x", "pixel_y"],
        position_columns=["position_x", "position_y"],
        velocity_columns=["velocity_x", "velocity_y"],
    )

    gaze.events = pm.Events(
        pl.DataFrame(
            {
                "name": ["fixation", "saccade"],
                "start": [0, 1],
                "end": [1, 2],
                "trial": ["trial_1", "trial_1"],
                "stimulus": ["Enc_WikiMoon_1", "Enc_WikiMoon_1"],
                "page": ["page_1", "page_1"],
                "char_idx": [1, 1],
                "char": ["a", "b"],
                "onset": [0, 1],
                "duration": [1, 1],
                "location_x": [100.0, 101.0],
                "location_y": [200.0, 201.0],
                "top_left_x": [0.0, 0.0],
                "top_left_y": [0.0, 0.0],
                "width": [10.0, 10.0],
                "height": [10.0, 10.0],
                "char_idx_in_line": [1, 1],
                "line_idx": [1, 1],
                "word_idx": [1, 1],
                "word_idx_in_line": [1, 1],
                "word": ["a", "b"],
            }
        )
    )
    gaze.validations = pl.DataFrame({"v": [1]})
    gaze.calibrations = pl.DataFrame({"c": [1]})
    gaze._metadata = {"datetime": "2023-01-01 12:00:00", "some": "metadata"}
    gaze.experiment = pm.Experiment(30, 40, 50, 60, 100, 100)
    return gaze


@pytest.mark.parametrize("sid_str", SID_STRINGS)
def test_save_load_raw_data_structure(tmp_path, dummy_gaze, sid_str):
    sid = Sid(sid_str)
    save_raw_data(sid, dummy_gaze)
    assert sid.raw_data_dir.exists()
    assert (sid.raw_data_dir / f"{sid!s}_trial_1_Enc_WikiMoon_1_raw_data.csv").exists()

    loaded_gaze = load_trial_level_raw_data(
        sid, trial_columns=["trial", "stimulus", "page"]
    )
    assert len(loaded_gaze.samples) == 3


@pytest.mark.parametrize("event_type", ["fixation", "saccade"])
@pytest.mark.parametrize("sid_str", SID_STRINGS)
def test_save_load_events_structure(tmp_path, dummy_gaze, event_type, sid_str):
    sid = Sid(sid_str)
    save_events_data(
        event_type,
        sid,
        "trial",
        ["stimulus"],
        ["name", "start", "end", "trial", "stimulus", "page"],
        dummy_gaze,
    )
    expected_dir = sid.fixations_dir if event_type == "fixation" else sid.saccades_dir
    assert expected_dir.exists()
    assert (expected_dir / f"{sid!s}_Enc_WikiMoon_1_{event_type}.csv").exists()

    loaded_gaze = load_trial_level_events_data(dummy_gaze, sid, event_type)
    assert len(loaded_gaze.events.frame.filter(pl.col("name") == event_type)) >= 1


@pytest.mark.parametrize("sid_str", SID_STRINGS)
def test_save_load_scanpaths_structure(tmp_path, dummy_gaze, sid_str):
    sid = Sid(sid_str)
    save_scanpaths(sid, dummy_gaze)
    assert sid.scanpaths_dir.exists()
    assert (sid.scanpaths_dir / f"{sid!s}_trial_1_Enc_WikiMoon_1_scanpath.csv").exists()

    loaded_gaze = load_scanpaths(gaze=dummy_gaze, sid=sid)
    aoi_cols = [
        "char_idx",
        "char",
        "top_left_x",
        "top_left_y",
        "width",
        "height",
        "char_idx_in_line",
        "line_idx",
        "word_idx",
        "word_idx_in_line",
        "word",
    ]

    assert all(col in loaded_gaze.events.frame.columns for col in aoi_cols)
    assert not any(
        "_right" in col_name for col_name in loaded_gaze.events.frame.columns
    )


@pytest.mark.parametrize("sid_str", SID_STRINGS)
def test_save_load_reading_measures_structure(tmp_path, sid_str):
    sid = Sid(sid_str)
    df_rm = pl.DataFrame(
        {"trial": ["trial_1"], "stimulus": ["Enc_WikiMoon_1"], "val": [1.0]}
    )
    save_reading_measures(sid, df_rm)
    assert sid.reading_measures_dir.exists()
    assert (
        sid.reading_measures_dir
        / f"{sid!s}_trial_1_Enc_WikiMoon_1_reading_measures.csv"
    ).exists()

    loaded_rm = load_reading_measures(sid)
    assert len(loaded_rm) == 1


@pytest.mark.parametrize("sid_str", SID_STRINGS)
def test_save_load_metadata_structure(tmp_path, dummy_gaze, sid_str):
    sid = Sid(sid_str)
    save_raw_data(sid, dummy_gaze)
    save_session_metadata(sid, dummy_gaze)
    assert sid.metadata_dir.exists()
    assert (sid.metadata_dir / "gaze_metadata.json").exists()
    assert (sid.metadata_dir / "calibrations.feather").exists()
    assert (sid.metadata_dir / "validations.feather").exists()
    assert (sid.metadata_dir / "calibrations.tsv").exists()
    assert (sid.metadata_dir / "validations.tsv").exists()

    # Ensure experiment.yaml exists (usually saved by gaze.save)
    if not (sid.metadata_dir / "experiment.yaml").exists():
        with open(sid.metadata_dir / "experiment.yaml", "w") as f:
            f.write("sampling_rate: 100")

    loaded_gaze = load_trial_level_raw_data(
        sid,
        trial_columns=["trial", "stimulus", "page"],
        load_metadata=True,
    )
    assert loaded_gaze._metadata["some"] == "metadata"
    assert len(loaded_gaze.calibrations) > 0
    assert len(loaded_gaze.validations) > 0


@pytest.mark.parametrize("invalid_type", ["", "blinks", "INVALID"])
def test_save_events_data_invalid_event_type(tmp_path, dummy_gaze, invalid_type):
    sid = Sid("001_EN_UK_1_S1")
    with pytest.raises(
        ValueError, match="Only fixations and saccades are currently supported"
    ):
        save_events_data(
            invalid_type,
            sid,
            "trial",
            ["stimulus"],
            ["name"],
            dummy_gaze,
        )


@pytest.mark.parametrize("invalid_type", ["", "blinks", "INVALID"])
def test_load_trial_level_events_data_invalid_event_type(
    tmp_path, dummy_gaze, invalid_type
):
    sid = Sid("001_EN_UK_1_S1")
    with pytest.raises(ValueError, match="event_type must be "):
        load_trial_level_events_data(dummy_gaze, sid, invalid_type)


def test_load_reading_measures_with_actual_filenames(tmp_path):
    sid = Sid("017_DA_DK_1_ET1")
    sid.reading_measures_dir.mkdir(parents=True)

    # Files as reported in the issue
    filenames = [
        f"{sid.id_no_postfix}_PRACTICE_trial_1_Enc_WikiMoon_reading_measures.csv",
        f"{sid.id_no_postfix}_trial_1_Lit_MagicMountain_reading_measures.csv",
        f"{sid.id_no_postfix}_trial_5_PopSci_MultiplEYE_reading_measures.csv",
    ]

    for filename in filenames:
        df = pl.DataFrame({"measure": [1.0], "trial": ["dummy"], "stimulus": ["dummy"]})
        df.write_csv(sid.reading_measures_dir / filename)

    # Test loading
    df_loaded = load_reading_measures(sid)

    assert len(df_loaded) == 3
    assert set(df_loaded["trial"].unique()) == {
        "PRACTICE_trial_1",
        "trial_1",
        "trial_5",
    }
    assert set(df_loaded["stimulus"].unique()) == {
        "Enc_WikiMoon",
        "Lit_MagicMountain",
        "PopSci_MultiplEYE",
    }

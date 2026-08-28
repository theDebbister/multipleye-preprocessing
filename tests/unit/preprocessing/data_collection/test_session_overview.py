import contextlib
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from preprocessing.data_collection.session import Session
from preprocessing.data_collection.stimulus import LabConfig


def _make_session(overrides: dict | None = None) -> Session:
    fields = {
        "participant_id": 1,
        "session_identifier": "001_EN_UK_1_ET1",
        "is_pilot": False,
        "session_folder_path": Path("/tmp"),
        "session_file_path": Path("/tmp/test.log"),
        "session_file_name": "test.log",
        **(overrides or {}),
    }
    return Session(**fields)


def _mock_lab_config() -> LabConfig:
    return LabConfig(
        screen_resolution=(1920, 1080),
        screen_size_cm=(52.0, 32.0),
        screen_distance_cm=60.0,
        image_resolution=(1322, 980),
        image_size_cm=(38.0, 28.3),
        name_eye_tracker="test",
        sampling_frequency_hz=1000.0,
        psychometric_tests=[],
    )


def _seed_metadata(sess: Session) -> None:
    sess.pm_gaze_metadata = {
        "tracked_eye": "R",
        "data_loss_ratio": 0.02,
        "mount_configuration": {
            "mount_type": "Desktop",
            "head_stabilization": "stabilized",
            "eyes_recorded": "binocular / monocular",
        },
        "pupil_data_type": "AREA",
    }
    sess.lab_config = _mock_lab_config()


def _validations(accuracy: list[float | None] | None = None) -> pl.DataFrame:
    accuracy = accuracy if accuracy is not None else [0.2, 0.35, 0.5]
    return pl.DataFrame(
        {
            "time": list(range(100, 100 + len(accuracy))),
            "accuracy_avg": accuracy,
            "accuracy_max": [0.3] * len(accuracy),
            "eye": ["right"] * len(accuracy),
        }
    )


def _calibrations() -> pl.DataFrame:
    return pl.DataFrame({"time": [50.0, 150.0]})


def _sess_with_validation_data() -> Session:
    sess = _make_session()
    _seed_metadata(sess)
    sess.validations = _validations()
    sess.calibrations = _calibrations()
    return sess


def test_create_overview_includes_new_fields() -> None:
    sess = _sess_with_validation_data()

    overview = sess.create_overview()

    tracking = overview["tracking"]
    assert tracking["tracked_eye"] == "R"
    assert tracking["tracked_eye_consistent"] is True
    cal = overview["calibration_validation"]
    assert cal["num_good_validations"] == 1
    assert cal["num_moderate_validations"] == 1
    assert cal["num_bad_validations"] == 1
    dq = overview["data_quality"]
    assert "session_total_data_loss_ratio" in dq
    assert dq["session_total_data_loss_ratio"] is None
    assert "session_blink_loss_ratio" in dq
    assert dq["session_blink_loss_ratio"] is None


def test_create_overview_includes_measure_based_data_loss() -> None:
    sess = _sess_with_validation_data()
    sess._measure_total_data_loss_ratio = 0.015
    sess._measure_blink_loss_ratio = 0.008

    overview = sess.create_overview()

    dq = overview["data_quality"]
    assert dq["session_total_data_loss_ratio"] == 0.015
    assert dq["session_blink_loss_ratio"] == 0.008


def test_tracked_eye_inconsistent_when_eye_changes() -> None:
    validations = _validations()
    validations = validations.with_columns(pl.lit("left").alias("eye"))
    sess = _make_session()
    sess.validations = validations
    sess.calibrations = _calibrations()
    _seed_metadata(sess)

    overview = sess.create_overview()

    tracking = overview["tracking"]
    assert tracking["tracked_eye"] == "R"
    assert tracking["tracked_eye_consistent"] is False


def test_sections_are_present() -> None:
    sess = _sess_with_validation_data()

    overview = sess.create_overview()

    assert list(overview.keys()) == [
        "administrative",
        "technical_setup",
        "tracking",
        "calibration_validation",
        "data_quality",
        "experiment_procedure",
        "trials",
        "comprehension",
        "data_formats",
    ]


def test_technical_setup_from_lab_config() -> None:
    sess = _sess_with_validation_data()

    overview = sess.create_overview()
    tech = overview["technical_setup"]

    assert tech["eye_tracker_name"] == "test"
    assert tech["sampling_frequency_hz"] == 1000.0
    assert tech["mount_type"] == "Desktop"
    assert tech["head_stabilization"] == "stabilized"
    assert tech["eyes_recorded"] == "binocular / monocular"
    assert tech["pupil_data_type"] == "AREA"
    assert tech["screen_resolution_width_px"] == 1920
    assert tech["screen_resolution_height_px"] == 1080
    assert tech["screen_distance_cm"] == 60.0
    assert tech["image_size_width_cm"] == 38.0


def test_avg_validation_error_computed_from_validations() -> None:
    sess = _make_session()
    _seed_metadata(sess)
    sess.calibrations = pl.DataFrame({"time": [50.0]})
    sess.validations = _validations([0.2, 0.3, 0.4])

    overview = sess.create_overview()
    cal = overview["calibration_validation"]

    assert cal["avg_validation_error_dva"] == 0.3
    assert cal["num_calibrations"] == 1
    assert cal["num_validations"] == 3


def test_comprehension_scores_read_from_answers_csv(tmp_path: Path) -> None:
    sess = _sess_with_validation_data()

    answers = pl.DataFrame(
        {
            "trial": ["trial_1"] * 6,
            "condition_number": [1, 1, 2, 2, 3, 3],
            "is_correct": [True, False, True, True, False, True],
        }
    )
    answers_dir = tmp_path / "comp_answers" / "001_EN_UK_1_ET1"
    answers_dir.mkdir(parents=True)
    answers.write_csv(answers_dir / "001_EN_UK_1_ET1_answers.csv")

    with patch.object(
        Session,
        "sid",
        property(lambda self: _FakeSid(answers_dir)),
    ):
        overview = sess.create_overview()
        comp = overview["comprehension"]

    assert comp["avg_comprehension_score"] == 0.667
    assert comp["avg_comprehension_score_local"] == 0.5
    assert comp["avg_comprehension_score_bridging"] == 1.0
    assert comp["avg_comprehension_score_global"] == 0.5


class _FakeSid:
    def __init__(self, answers_dir: Path):
        self._answers_dir = answers_dir

    @property
    def answers_dir(self) -> Path:
        return self._answers_dir

    def __str__(self) -> str:
        return "001_EN_UK_1_ET1"


def test_session_duration_from_messages() -> None:
    sess = _sess_with_validation_data()
    sess.messages = pl.DataFrame(
        {"time": [1000.0, 2000.0, 60000.0], "content": ["a", "b", "c"]}
    )

    overview = sess.create_overview()
    proc = overview["experiment_procedure"]

    assert proc["total_session_duration_s"] == 59.0


def test_reading_time_from_stimulus_start_end_ts() -> None:
    sess = _sess_with_validation_data()
    sess.stimulus_start_end_ts = [
        {"stimulus": "a", "trial": "trial_1", "start_ts": 1000.0, "stop_ts": 4000.0},
        {"stimulus": "b", "trial": "trial_2", "start_ts": 5000.0, "stop_ts": 7000.0},
    ]

    overview = sess.create_overview()
    proc = overview["experiment_procedure"]

    assert proc["total_reading_time_s"] == 5.0


def test_stimulus_order_ids_with_names() -> None:
    from types import SimpleNamespace

    sess = _sess_with_validation_data()
    sess.stimuli = [
        SimpleNamespace(id=1, name="Lit_MagicMountain", trial_id="trial_1"),
        SimpleNamespace(id=2, name="Lit_Alchemist", trial_id="trial_2"),
        SimpleNamespace(id=3, name="Enc_WikiMoon", trial_id="trial_3"),
    ]
    sess.stimulus_order_ids = [3, 1, 2]

    overview = sess.create_overview()
    proc = overview["experiment_procedure"]

    assert proc["stimulus_order_ids_with_names"] == [
        {"stimulus_id": 3, "stimulus_name": "Enc_WikiMoon", "trial": "trial_3"},
        {"stimulus_id": 1, "stimulus_name": "Lit_MagicMountain", "trial": "trial_1"},
        {"stimulus_id": 2, "stimulus_name": "Lit_Alchemist", "trial": "trial_2"},
    ]


def test_stimulus_order_ids_with_names_unknown_without_stimuli() -> None:
    sess = _sess_with_validation_data()
    sess.stimulus_order_ids = [1, 2, 3]

    overview = sess.create_overview()
    proc = overview["experiment_procedure"]

    assert proc["stimulus_order_ids_with_names"] == "unknown"


def test_data_formats_section() -> None:
    sess = _sess_with_validation_data()

    overview = sess.create_overview()
    formats = overview["data_formats"]

    assert formats["raw_data"] is True
    assert formats["fixations"] is True
    assert formats["saccades"] is True
    assert formats["reading_measures"] is True
    assert formats["answers"] is True


def test_data_formats_can_be_disabled_for_other_pipelines() -> None:
    sess = _sess_with_validation_data()
    sess.fixations = False
    sess.saccades = False

    overview = sess.create_overview()
    formats = overview["data_formats"]

    assert formats["fixations"] is False
    assert formats["saccades"] is False
    assert formats["raw_data"] is True


# --- Branch coverage: unprocessed / edge-case sessions ---


def test_unprocessed_session_defaults() -> None:
    """A session with no data populated should not crash and report defaults."""
    sess = _make_session()

    overview = sess.create_overview()

    assert overview["tracking"]["tracked_eye"] == "unknown"
    assert overview["technical_setup"]["eye_tracker_name"] is None
    assert overview["calibration_validation"]["avg_validation_error_dva"] == "unknown"
    assert overview["calibration_validation"]["num_calibrations"] == 7
    assert overview["comprehension"]["avg_comprehension_score"] == "unknown"
    assert overview["experiment_procedure"]["total_session_duration_s"] == "unknown"
    assert overview["experiment_procedure"]["total_reading_time_s"] == "unknown"


def test_metadata_not_a_dict() -> None:
    sess = _make_session()
    sess.pm_gaze_metadata = "unknown"

    overview = sess.create_overview()

    assert overview["administrative"]["year_of_data_collection"] == "unknown"
    assert overview["technical_setup"]["mount_type"] is None


def test_mount_configuration_not_a_dict() -> None:
    sess = _make_session()
    sess.pm_gaze_metadata = {
        "tracked_eye": "R",
        "mount_configuration": "unknown",
        "pupil_data_type": "AREA",
    }

    overview = sess.create_overview()
    tech = overview["technical_setup"]

    assert tech["mount_type"] is None
    assert tech["eyes_recorded"] is None


def test_technical_setup_without_lab_config() -> None:
    sess = _make_session()
    _seed_metadata(sess)
    sess.lab_config = "unknown"

    overview = sess.create_overview()
    tech = overview["technical_setup"]

    assert tech["eye_tracker_name"] is None
    assert tech["sampling_frequency_hz"] is None
    assert tech["screen_resolution_width_px"] is None


def test_validations_without_accuracy_column() -> None:
    sess = _make_session()
    _seed_metadata(sess)
    sess.calibrations = _calibrations()
    sess.validations = pl.DataFrame({"time": [100.0, 200.0]})

    overview = sess.create_overview()
    cal = overview["calibration_validation"]

    assert cal["avg_validation_error_dva"] == "unknown"
    assert cal["num_validations"] == 2


def test_validations_with_null_accuracy() -> None:
    sess = _make_session()
    _seed_metadata(sess)
    sess.calibrations = _calibrations()
    sess.validations = _validations([None, None])

    overview = sess.create_overview()
    cal = overview["calibration_validation"]

    assert cal["avg_validation_error_dva"] == "unknown"


def test_calibrations_with_accuracy_column() -> None:
    sess = _make_session()
    _seed_metadata(sess)
    sess.validations = _validations()
    sess.calibrations = pl.DataFrame(
        {
            "time": [50.0, 150.0],
            "num_points": [9, 9],
            "eye": ["right", "right"],
            "tracking_mode": ["CR", "CR"],
            "accuracy_avg": [0.1, 0.3],
        }
    )

    overview = sess.create_overview()
    cal = overview["calibration_validation"]

    assert cal["avg_calibration_error_dva"] == 0.2


def test_calibrations_with_null_accuracy() -> None:
    sess = _make_session()
    _seed_metadata(sess)
    sess.validations = _validations()
    sess.calibrations = pl.DataFrame(
        {
            "time": [50.0, 150.0],
            "num_points": [9, 9],
            "eye": ["right", "right"],
            "tracking_mode": ["CR", "CR"],
            "accuracy_avg": [None, None],
        }
    )

    overview = sess.create_overview()
    cal = overview["calibration_validation"]

    assert cal["avg_calibration_error_dva"] == "unknown"


def test_answers_csv_unreadable(tmp_path: Path, monkeypatch) -> None:
    sess = _sess_with_validation_data()
    answers_dir = tmp_path / "comp_answers" / "001_EN_UK_1_ET1"
    answers_dir.mkdir(parents=True)
    (answers_dir / "001_EN_UK_1_ET1_answers.csv").write_text("garbage")

    def _raise(*args, **kwargs):
        from polars.exceptions import ComputeError

        raise ComputeError("cannot parse")

    monkeypatch.setattr("preprocessing.data_collection.session.pl.read_csv", _raise)

    with patch.object(
        Session,
        "sid",
        property(lambda self: _FakeSid(answers_dir)),
    ):
        overview = sess.create_overview()
        comp = overview["comprehension"]

    assert comp["avg_comprehension_score"] == "unknown"


def test_answers_csv_all_null_is_correct(tmp_path: Path) -> None:
    sess = _sess_with_validation_data()
    answers_dir = tmp_path / "comp_answers" / "001_EN_UK_1_ET1"
    answers_dir.mkdir(parents=True)
    answers = pl.DataFrame(
        {
            "trial": ["trial_1", "trial_2"],
            "condition_number": [1, 2],
            "is_correct": [None, None],
        }
    )
    answers.write_csv(answers_dir / "001_EN_UK_1_ET1_answers.csv")

    with patch.object(
        Session,
        "sid",
        property(lambda self: _FakeSid(answers_dir)),
    ):
        overview = sess.create_overview()
        comp = overview["comprehension"]

    assert comp["avg_comprehension_score"] == "unknown"
    assert comp["avg_comprehension_score_local"] == "unknown"


def test_answers_csv_without_one_condition(tmp_path: Path) -> None:
    sess = _sess_with_validation_data()
    answers_dir = tmp_path / "comp_answers" / "001_EN_UK_1_ET1"
    answers_dir.mkdir(parents=True)
    answers = pl.DataFrame(
        {
            "trial": ["trial_1", "trial_2"],
            "condition_number": [1, 1],
            "is_correct": [True, False],
        }
    )
    answers.write_csv(answers_dir / "001_EN_UK_1_ET1_answers.csv")

    with patch.object(
        Session,
        "sid",
        property(lambda self: _FakeSid(answers_dir)),
    ):
        overview = sess.create_overview()
        comp = overview["comprehension"]

    assert comp["avg_comprehension_score"] == 0.5
    assert comp["avg_comprehension_score_local"] == 0.5
    assert comp["avg_comprehension_score_bridging"] == "unknown"
    assert comp["avg_comprehension_score_global"] == "unknown"


def test_answers_csv_missing_is_correct(tmp_path: Path) -> None:
    sess = _sess_with_validation_data()
    answers_dir = tmp_path / "comp_answers" / "001_EN_UK_1_ET1"
    answers_dir.mkdir(parents=True)
    answers = pl.DataFrame({"trial": ["trial_1"], "condition_number": [1]})
    answers.write_csv(answers_dir / "001_EN_UK_1_ET1_answers.csv")

    with patch.object(
        Session,
        "sid",
        property(lambda self: _FakeSid(answers_dir)),
    ):
        overview = sess.create_overview()
        comp = overview["comprehension"]

    assert comp["avg_comprehension_score"] == "unknown"


def test_answers_csv_practice_only(tmp_path: Path) -> None:
    sess = _sess_with_validation_data()
    answers_dir = tmp_path / "comp_answers" / "001_EN_UK_1_ET1"
    answers_dir.mkdir(parents=True)
    answers = pl.DataFrame(
        {
            "trial": ["PRACTICE_trial_1"],
            "condition_number": [1],
            "is_correct": [True],
        }
    )
    answers.write_csv(answers_dir / "001_EN_UK_1_ET1_answers.csv")

    with patch.object(
        Session,
        "sid",
        property(lambda self: _FakeSid(answers_dir)),
    ):
        overview = sess.create_overview()
        comp = overview["comprehension"]

    assert comp["avg_comprehension_score"] == "unknown"


def test_answers_csv_without_condition_number(tmp_path: Path) -> None:
    sess = _sess_with_validation_data()
    answers_dir = tmp_path / "comp_answers" / "001_EN_UK_1_ET1"
    answers_dir.mkdir(parents=True)
    answers = pl.DataFrame(
        {
            "trial": ["trial_1", "trial_2"],
            "is_correct": [True, False],
        }
    )
    answers.write_csv(answers_dir / "001_EN_UK_1_ET1_answers.csv")

    with patch.object(
        Session,
        "sid",
        property(lambda self: _FakeSid(answers_dir)),
    ):
        overview = sess.create_overview()
        comp = overview["comprehension"]

    assert comp["avg_comprehension_score"] == 0.5
    assert comp["avg_comprehension_score_local"] == "unknown"


def test_session_duration_without_time_column() -> None:
    sess = _sess_with_validation_data()
    sess.messages = pl.DataFrame({"content": ["a", "b"]})

    overview = sess.create_overview()
    proc = overview["experiment_procedure"]

    assert proc["total_session_duration_s"] == "unknown"


def test_session_duration_with_null_timestamps() -> None:
    sess = _sess_with_validation_data()
    sess.messages = pl.DataFrame({"time": [None, None], "content": ["a", "b"]})

    overview = sess.create_overview()
    proc = overview["experiment_procedure"]

    assert proc["total_session_duration_s"] == "unknown"


def test_reading_time_malformed_entries() -> None:
    sess = _sess_with_validation_data()
    sess.stimulus_start_end_ts = [
        {"stimulus": "a", "trial": "trial_1", "start_ts": 1000.0, "stop_ts": 4000.0},
        {"stimulus": "b", "trial": "trial_2"},
        "garbage",
    ]

    overview = sess.create_overview()
    proc = overview["experiment_procedure"]

    assert proc["total_reading_time_s"] == 3.0


def test_reading_time_non_positive_total() -> None:
    sess = _sess_with_validation_data()
    sess.stimulus_start_end_ts = [
        {"stimulus": "a", "trial": "trial_1", "start_ts": 4000.0, "stop_ts": 1000.0},
    ]

    overview = sess.create_overview()
    proc = overview["experiment_procedure"]

    assert proc["total_reading_time_s"] == "unknown"


def test_reading_time_already_set() -> None:
    sess = _sess_with_validation_data()
    sess.total_reading_time = 42.0
    sess.stimulus_start_end_ts = [
        {"stimulus": "a", "trial": "trial_1", "start_ts": 1000.0, "stop_ts": 4000.0},
    ]

    overview = sess.create_overview()
    proc = overview["experiment_procedure"]

    assert proc["total_reading_time_s"] == 42.0


# --- Trial building ---


def _write_answers(
    tmp_path: Path,
    rows: list[dict],
) -> Path:
    """Write an answers CSV and return the comp_answers dir for the fake sid."""
    answers_dir = tmp_path / "comp_answers" / "001_EN_UK_1_ET1"
    answers_dir.mkdir(parents=True)
    pl.DataFrame(rows).write_csv(answers_dir / "001_EN_UK_1_ET1_answers.csv")
    return answers_dir


def _trial_sess(answers_dir: Path) -> Session:
    sess = _sess_with_validation_data()
    sess.stimulus_start_end_ts = [
        {
            "stimulus": "Lit_MagicMountain",
            "trial": "trial_1",
            "start_ts": 1000.0,
            "stop_ts": 4000.0,
        },
        {
            "stimulus": "Lit_Alchemist",
            "trial": "trial_2",
            "start_ts": 5000.0,
            "stop_ts": 8000.0,
        },
        {
            "stimulus": "Enc_WikiMoon",
            "trial": "PRACTICE_trial_1",
            "start_ts": 100.0,
            "stop_ts": 500.0,
        },
    ]
    return sess


_ANSWERS_ROWS = [
    {
        "trial": "trial_1",
        "stimulus": "Lit_MagicMountain",
        "stimulus_id": 3,
        "is_correct": True,
        "confirmation_rt_ms": 1000.0,
    },
    {
        "trial": "trial_1",
        "stimulus": "Lit_MagicMountain",
        "stimulus_id": 3,
        "is_correct": False,
        "confirmation_rt_ms": 2000.0,
    },
    {
        "trial": "trial_2",
        "stimulus": "Lit_Alchemist",
        "stimulus_id": 4,
        "is_correct": True,
        "confirmation_rt_ms": 1500.0,
    },
    {
        "trial": "PRACTICE_trial_1",
        "stimulus": "Enc_WikiMoon",
        "stimulus_id": 13,
        "is_correct": True,
        "confirmation_rt_ms": 500.0,
    },
]


@pytest.mark.parametrize(
    (
        "trial_number",
        "is_practice",
        "stimulus_name",
        "num_questions",
        "comprehension_score",
        "question_time_ms",
        "reading_time_ms",
    ),
    [
        (1, False, "Lit_MagicMountain", 2, 0.5, 3000.0, 3000.0),
        (2, False, "Lit_Alchemist", 1, 1.0, 1500.0, 3000.0),
        (1, True, "Enc_WikiMoon", 1, 1.0, 500.0, 400.0),
    ],
)
def test_trials_computed_from_answers_and_reading_times(
    tmp_path: Path,
    trial_number: int,
    is_practice: bool,
    stimulus_name: str,
    num_questions: int,
    comprehension_score: float,
    question_time_ms: float,
    reading_time_ms: float,
) -> None:
    answers_dir = _write_answers(tmp_path, _ANSWERS_ROWS)
    sess = _trial_sess(answers_dir)

    with patch.object(
        Session,
        "sid",
        property(lambda self: _FakeSid(answers_dir)),
    ):
        trials = sess.create_overview()["trials"]

    trial = next(
        t
        for t in trials
        if t["trial_number"] == trial_number and t["is_practice"] == is_practice
    )
    assert trial["stimulus_name"] == stimulus_name
    assert trial["num_questions"] == num_questions
    assert trial["comprehension_score"] == comprehension_score
    assert trial["comprehension_question_time_ms"] == question_time_ms
    assert trial["reading_time_ms"] == reading_time_ms


@pytest.mark.parametrize(
    ("answers_setup",),
    [
        ("missing",),
        ("unreadable",),
    ],
)
def test_trials_unknown_without_usable_answers(
    tmp_path: Path,
    answers_setup: str,
) -> None:
    sess = _sess_with_validation_data()

    def _patched_sid(path: Path):
        return _FakeSid(path)

    if answers_setup == "missing":
        answers_dir = tmp_path / "nonexistent"
    else:
        answers_dir = tmp_path / "comp_answers" / "001_EN_UK_1_ET1"
        answers_dir.mkdir(parents=True)
        (answers_dir / "001_EN_UK_1_ET1_answers.csv").write_text("garbage")

    def _raise(*args, **kwargs):
        from polars.exceptions import ComputeError

        raise ComputeError("cannot parse")

    patches = [
        patch.object(
            Session,
            "sid",
            property(lambda self: _patched_sid(answers_dir)),
        )
    ]
    if answers_setup == "unreadable":
        patches.insert(
            0, patch("preprocessing.data_collection.session.pl.read_csv", _raise)
        )

    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        trials = sess.create_overview()["trials"]

    assert trials == "unknown"

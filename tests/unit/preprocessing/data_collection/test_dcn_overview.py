import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
import yaml

from preprocessing.data_collection.multipleye_data_collection import (
    MultipleyeDataCollection,
)
from preprocessing.data_collection.session import Session


def _mock_lab_config():
    cfg = MagicMock()
    cfg.screen_resolution = (1920, 1080)
    cfg.screen_size_cm = (52.0, 32.0)
    cfg.screen_distance_cm = 60.0
    cfg.image_resolution = (1322, 980)
    cfg.image_size_cm = (38.0, 28.3)
    cfg.name_eye_tracker = "EyeLink 1000 Plus"
    cfg.sampling_frequency_hz = 1000.0
    cfg.psychometric_tests = ["TestA", "TestB"]
    return cfg


@pytest.fixture
def dummy_dcn_dir(tmp_path: Path) -> Path:
    """Create a dummy data collection folder structure with sessions."""
    collection_name = "MultiplEYE_EN_UK_London_1_2025"
    data_dir = tmp_path / collection_name
    data_dir.mkdir()

    et_sessions_dir = data_dir / "eye-tracking-sessions"
    et_sessions_dir.mkdir()
    (data_dir / "psychometric-tests").mkdir()
    stimuli_dir = data_dir / f"stimuli_{collection_name}"
    stimuli_dir.mkdir()
    config_dir = stimuli_dir / "config"
    config_dir.mkdir()

    df = pd.DataFrame({"participant_id": [1, 2, 3], "version_number": [1, 1, 1]})
    df.to_csv(config_dir / "stimulus_order_versions_EN_UK_1.csv", index=False)

    for s_id in ["001_EN_UK_1_ET1", "002_EN_UK_1_ET1", "003_EN_UK_1_ET1"]:
        s_path = et_sessions_dir / s_id
        s_path.mkdir()
        (s_path / "data.edf").touch()

    return data_dir


@pytest.fixture
def mock_load_lab_config(monkeypatch):
    """Mock load_lab_config to return a mock config."""

    class MockLabConfig:
        def __init__(self):
            self.name_eye_tracker = "EyeLink 1000 Plus"
            self.psychometric_tests = ["TestA", "TestB"]
            self.screen_resolution = (1920, 1080)
            self.sampling_frequency_hz = 1000.0
            self.screen_size_cm = (52.0, 32.0)
            self.screen_distance_cm = 60.0
            self.image_resolution = (1322, 980)
            self.image_size_cm = (38.0, 28.3)

    monkeypatch.setattr(
        MultipleyeDataCollection,
        "load_lab_config",
        lambda *args, **kwargs: MockLabConfig(),
    )


@pytest.fixture
def mock_pipeline_version(monkeypatch):
    monkeypatch.setattr(
        MultipleyeDataCollection,
        "_get_pipeline_version",
        lambda self: "2026.08.11",
    )


def _create_dc(dummy_dcn_dir: Path, **kwargs) -> MultipleyeDataCollection:
    """Factory to create a MultipleyeDataCollection with dummy data."""
    return MultipleyeDataCollection.create_from_data_folder(dummy_dcn_dir, **kwargs)


def _setup_session_with_data(
    session: Session,
    avg_calibration_error: float = 0.5,
    avg_validation_error: float = 0.3,
    total_data_loss: float = 0.02,
    blink_loss: float = 0.01,
    total_reading_time: float = 25000.0,
    total_session_duration: float = 1800.0,
    avg_comprehension: float = 0.8,
    avg_comprehension_local: float = 0.7,
    avg_comprehension_global: float = 0.9,
    avg_comprehension_bridging: float = 0.6,
    num_completed_trials: int = 10,
) -> None:
    session.avg_calibration_error = avg_calibration_error
    session.avg_validation_error = avg_validation_error
    session._measure_total_data_loss_ratio = total_data_loss
    session._measure_blink_loss_ratio = blink_loss
    session.total_reading_time = total_reading_time
    session.total_session_duration = total_session_duration
    session.avg_comprehension_score = avg_comprehension
    session.avg_comprehension_score_local = avg_comprehension_local
    session.avg_comprehension_score_global = avg_comprehension_global
    session.avg_comprehension_score_bridging = avg_comprehension_bridging
    session.num_completed_trials = num_completed_trials


def _admin(overview: dict) -> dict:
    return overview["administrative"]


def _lang(overview: dict) -> dict:
    return overview["language_details"]


def _avail(overview: dict) -> dict:
    return overview["data_availability"]


def _psych(overview: dict) -> dict:
    return overview["psychometric_tests"]


def _tech(overview: dict) -> dict:
    return overview["technical_setup"]


def _proc(overview: dict) -> dict:
    return overview["processing"]


def _qual(overview: dict) -> dict:
    return overview["data_quality"]


class TestAdministrative:
    def test_legacy_fields_preserved(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        a = _admin(overview)

        assert a["title"] == "MultiplEYE_EN_UK_London_1_2025"
        assert a["dataset_type"] == "MultiplEYE"
        assert a["tested_language"] == "EN"
        assert a["country"] == "UK"
        assert a["city"] == "London"
        assert a["lab_number"] == 1

    def test_dataset_description(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        a = _admin(overview)

        assert "London" in a["dataset_description"]
        assert "EN" in a["dataset_description"]

    def test_session_counts(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        a = _admin(overview)

        assert a["number_of_sessions"] == 3
        assert a["number_of_pilots"] == 0
        assert "number_of_et_sessions_per_participant" in a


class TestProcessing:
    def test_processing_metadata(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        p = _proc(overview)

        assert p["pipeline_version"] == "2026.08.11"
        assert p["preprocessing_date"] == datetime.now(tz=UTC).strftime("%Y-%m-%d")


class TestTechnicalSetup:
    def test_technical_setup(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        t = _tech(overview)

        assert t["eye_tracker_name"] == "EyeLink 1000 Plus"
        assert t["sampling_frequency_hz"] == 1000.0
        assert t["screen_resolution_width_px"] == 1920
        assert t["screen_resolution_height_px"] == 1080

    def test_psychometric_tests(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        p = _psych(overview)

        assert p["tests_available"] == ["TestA", "TestB"]


class TestYAMLOutput:
    def test_yaml_output_is_valid(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        dc.create_dataset_overview(path=dummy_dcn_dir)
        yaml_path = dummy_dcn_dir / "MultiplEYE_EN_UK_London_1_2025_overview.yaml"
        assert yaml_path.exists()

        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        assert data["administrative"]["title"] == "MultiplEYE_EN_UK_London_1_2025"

    def test_sections_ordered(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)

        keys = list(overview.keys())
        assert keys[0] == "administrative"
        assert keys[1] == "language_details"
        assert keys[2] == "data_availability"
        assert keys[3] == "psychometric_tests"
        assert keys[4] == "technical_setup"
        assert keys[5] == "processing"
        assert keys[6] == "processing_config"
        assert keys[7] == "data_quality"


class TestProcessingConfig:
    def test_processing_config_reflects_settings(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        pc = overview["processing_config"]

        assert pc["fixation_method"] == "ivt"
        assert pc["fixation_minimum_duration_ms"] == 100
        assert pc["fixation_velocity_threshold"] == 20.0
        assert pc["saccade_method"] == "microsaccades"
        assert pc["saccade_minimum_duration"] == 6
        assert pc["saccade_threshold_factor"] == 6.0
        assert pc["velocity_estimation_method"] == "savitzky_golay"
        assert pc["velocity_smoothing_window_ms"] == 50
        assert pc["velocity_polynomial_degree"] == 2

    def test_processing_config_records_fixed_design_decisions(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        pc = overview["processing_config"]

        assert pc["aoi_enlargement"] == "half_line_spacing"
        assert pc["reading_measures_null_fill"] == 0
        assert pc["scanpath_drop_unmapped"] is True
        assert pc["data_loss_missingness_column"] == "pixel"
        assert pc["per_trial_loss_weighting"] == "equal"

    def test_processing_config_records_psychometric_thresholds(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        from preprocessing import settings

        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        pc = overview["processing_config"]

        assert pc["psym_wikivocab_min_rt"] == settings.PSYM_WIKIVOCAB_MIN_RT
        assert pc["psym_wikivocab_max_rt"] == settings.PSYM_WIKIVOCAB_MAX_RT
        assert pc["psym_stroop_min_rt"] == settings.PSYM_STROOP_MIN_RT
        assert pc["psym_stroop_max_rt"] == settings.PSYM_STROOP_MAX_RT
        assert pc["psym_flanker_min_rt"] == settings.PSYM_FLANKER_MIN_RT
        assert pc["psym_flanker_max_rt"] == settings.PSYM_FLANKER_MAX_RT

    def test_processing_config_records_eye_and_column_mappings(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        from preprocessing import settings

        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        pc = overview["processing_config"]

        assert pc["tracked_eye"] == settings.TRACKED_EYE
        assert pc["trial_cols"] == settings.TRIAL_COLS
        assert pc["trial_col"] == settings.TRIAL_COL
        assert pc["page_col"] == settings.PAGE_COL
        assert pc["stimulus_col"] == settings.STIMULUS_COL
        assert pc["word_idx_col"] == settings.WORD_IDX_COL
        assert pc["char_idx_col"] == settings.CHAR_IDX_COL

    def test_processing_config_inf_round_trips_through_yaml(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        dc.create_dataset_overview(path=dummy_dcn_dir)
        yaml_path = dummy_dcn_dir / "MultiplEYE_EN_UK_London_1_2025_overview.yaml"

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        pc = data["processing_config"]
        assert pc["psym_wikivocab_max_rt"] == float("inf")
        assert pc["psym_stroop_max_rt"] == float("inf")
        assert pc["psym_flanker_max_rt"] == float("inf")
        assert pc["tracked_eye"] == ["L", "R", "RIGHT", "LEFT"]


class TestDataAvailability:
    def test_all_formats_hardcoded_true(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        a = _avail(overview)

        assert a["raw_data_available"] is True
        assert a["fixations_available"] is True
        assert a["saccades_available"] is True
        assert a["reading_measures_available"] is True


class TestComputedAverages:
    def test_none_with_unprocessed_sessions(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        q = _qual(overview)

        assert q["mean_calibration_error_dva"] is None
        assert q["mean_validation_error_dva"] is None
        assert q["mean_data_loss_ratio"] is None
        assert q["mean_blink_ratio"] is None
        assert q["mean_total_reading_time_ms"] is None
        assert q["mean_comprehension_score"] is None
        assert q["mean_comprehension_score_local"] is None
        assert q["mean_comprehension_score_global"] is None
        assert q["mean_comprehension_score_bridging"] is None

    def test_comprehension_by_type_averages(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        _setup_session_with_data(
            dc.sessions["001_EN_UK_1_ET1"],
            avg_comprehension=0.8,
            avg_comprehension_local=0.7,
            avg_comprehension_global=0.9,
            avg_comprehension_bridging=0.6,
        )
        _setup_session_with_data(
            dc.sessions["002_EN_UK_1_ET1"],
            avg_comprehension=0.6,
            avg_comprehension_local=0.5,
            avg_comprehension_global=0.7,
            avg_comprehension_bridging=0.4,
        )

        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        q = _qual(overview)

        assert q["mean_comprehension_score"] == 0.7
        assert q["mean_comprehension_score_local"] == 0.6
        assert q["mean_comprehension_score_global"] == 0.8
        assert q["mean_comprehension_score_bridging"] == 0.5

    def test_averages_with_multiple_sessions(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        _setup_session_with_data(
            dc.sessions["001_EN_UK_1_ET1"],
            avg_calibration_error=0.5,
            avg_validation_error=0.3,
            total_data_loss=0.02,
            blink_loss=0.01,
        )
        _setup_session_with_data(
            dc.sessions["002_EN_UK_1_ET1"],
            avg_calibration_error=0.7,
            avg_validation_error=0.4,
            total_data_loss=0.03,
            blink_loss=0.02,
        )
        _setup_session_with_data(
            dc.sessions["003_EN_UK_1_ET1"],
            avg_calibration_error=0.6,
            avg_validation_error=0.5,
            total_data_loss=0.01,
            blink_loss=0.03,
        )

        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        q = _qual(overview)

        assert q["mean_calibration_error_dva"] == 0.6
        assert q["mean_validation_error_dva"] == 0.4
        assert q["mean_data_loss_ratio"] == 0.02
        assert q["mean_blink_ratio"] == 0.02


class TestAttritionRate:
    def test_attrition_rate(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        for s in dc.sessions.values():
            _setup_session_with_data(s)
        dc.crashed_session_ids = ["1"]

        overview = dc.create_dataset_overview(path=dummy_dcn_dir)

        assert _qual(overview)["attrition_rate"] == pytest.approx(1.0 / 3.0, abs=0.01)

    def test_attrition_rate_zero_with_no_crashes(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        for s in dc.sessions.values():
            _setup_session_with_data(s)

        overview = dc.create_dataset_overview(path=dummy_dcn_dir)

        assert _qual(overview)["attrition_rate"] == 0.0


class TestMetadataForm:
    def test_missing_metadata_form(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        ld = _lang(overview)

        assert ld["metadata_form_exists"] is False
        assert ld["language_script"] is None
        assert ld["language_family"] is None

    def test_metadata_form_fields_loaded(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        collection_name = "MultiplEYE_EN_UK_London_1_2025"
        stimuli_dir = dummy_dcn_dir / f"stimuli_{collection_name}"
        doc_dir = stimuli_dir.parent / "documentation"
        doc_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = doc_dir / "MultiplEYE_en_uk_London_1_2025_metadata_form.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "Script": "Latin",
                    "Language_family": "Indo-European",
                    "Start_date_of_data_collection": "2025-01-15",
                    "End_date_of_data_collection": "2025-03-20",
                    "Required_pq_fixing": "yes",
                    "Monitor_name": "Dell U2412M",
                    "Custom_units_of_analysis": False,
                },
                f,
            )

        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        ld = _lang(overview)
        t = _tech(overview)
        p = _proc(overview)

        assert ld["metadata_form_exists"] is True
        assert ld["language_script"] == "Latin"
        assert ld["language_family"] == "Indo-European"
        assert ld["start_date_of_data_collection"] == "2025-01-15"
        assert ld["end_date_of_data_collection"] == "2025-03-20"
        assert t["monitor_name"] == "Dell U2412M"
        assert p["required_pq_fixing"] == "yes"
        assert "2025-01-15" in _admin(overview)["dataset_description"]


class TestWPM:
    def test_wpm_none_when_no_stimuli(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        dc = _create_dc(dummy_dcn_dir)
        s1 = dc.sessions["001_EN_UK_1_ET1"]
        _setup_session_with_data(s1, total_reading_time=30000.0)
        s1.stimuli = "unknown"

        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        q = _qual(overview)

        assert q["mean_total_reading_time_ms"] == 30000.0
        assert q["mean_wpm"] is None

    def test_wpm_computed_from_page_texts(
        self, dummy_dcn_dir, mock_load_lab_config, mock_pipeline_version
    ) -> None:
        page = MagicMock()
        page.text = "This is a test sentence with eight words here."
        stim = MagicMock()
        stim.pages = [page, page]

        dc = _create_dc(dummy_dcn_dir)
        s1 = dc.sessions["001_EN_UK_1_ET1"]
        _setup_session_with_data(s1, total_reading_time=60000.0)
        s1.stimuli = [stim]

        overview = dc.create_dataset_overview(path=dummy_dcn_dir)

        assert _qual(overview)["mean_wpm"] == pytest.approx(18.0, abs=0.5)


class TestLabConfigAttributeSafety:
    def test_missing_lab_config_attrs_handled(
        self, dummy_dcn_dir, mock_pipeline_version, monkeypatch
    ) -> None:
        class SparseLabConfig:
            def __init__(self):
                self.name_eye_tracker = "EyeLink 1000 Plus"
                self.psychometric_tests = None

        monkeypatch.setattr(
            MultipleyeDataCollection,
            "load_lab_config",
            lambda *args, **kwargs: SparseLabConfig(),
        )
        dc = _create_dc(dummy_dcn_dir)
        overview = dc.create_dataset_overview(path=dummy_dcn_dir)
        t = _tech(overview)
        p = _psych(overview)

        assert t["eye_tracker_name"] is not None
        assert t["sampling_frequency_hz"] is None
        assert t["screen_resolution_width_px"] is None
        assert t["screen_resolution_height_px"] is None
        assert p["tests_available"] is None

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TypeVar

import polars as pl

from ..config import settings
from ..data_collection.stimulus import LabConfig, Stimulus
from ..data_collection.trial import Trial
from ..models import Sid
from ..utils.logging import get_logger

logger = get_logger()

T = TypeVar("T")


@dataclass
class Session:
    # general info
    participant_id: int

    session_identifier: str
    is_pilot: bool

    # paths and files
    session_folder_path: Path
    session_file_path: Path
    session_file_name: str
    asc_path: Path | str = field(default="unknown", init=False)

    # stimuli
    # TODO: move stimuli, completed stimuli, stimuli trial mapping to one thing
    stimuli: list[Stimulus] | str = field(default="unknown", init=False)
    randomization_version: int | str = field(default="unknown", init=False)
    stimulus_folder_name: str = field(default="unknown", init=False)
    completed_stimuli_ids: list[int] | str = field(default="unknown", init=False)
    completed_stimuli_names: list[str] | str = field(default="unknown", init=False)
    question_order: dict[str, list[str]] | str = field(default="unknown", init=False)
    stimulus_order_ids: list[int] | str = field(default="unknown", init=False)
    stimulus_order_ids_with_names: list[dict[str, object]] | str = field(
        default="unknown", init=False
    )
    messages: pl.DataFrame | list[dict[str, str]] | str = field(
        default="unknown", init=False
    )
    uncategorized_messages: list[dict[str, str]] | str = field(
        default="unknown", init=False
    )
    stimuli_trial_mapping: dict[str, str] | str = field(default="unknown", init=False)
    stimulus_start_end_ts: list[dict[str, str | float]] | str = field(
        default="unknown", init=False
    )

    logfile: str = field(default="unknown", init=False)
    interrupted: bool | str = field(default="unknown", init=False)
    lab_config: LabConfig | str = field(default="unknown", init=False)

    # stats
    total_reading_time: float | str = field(default="unknown", init=False)
    total_session_duration: float | str = field(default="unknown", init=False)
    obligatory_break_made: bool | str = field(default="unknown", init=False)
    num_optional_breaks_made: int | str = field(default="unknown", init=False)
    total_break_time: float | str = field(default="unknown", init=False)

    # calibrations & validations
    calibrations: pl.DataFrame | str = field(default="unknown", init=False)
    validations: pl.DataFrame | str = field(default="unknown", init=False)
    avg_comprehension_score: float | str = field(default="unknown", init=False)
    avg_comprehension_score_local: float | str = field(default="unknown", init=False)
    avg_comprehension_score_global: float | str = field(default="unknown", init=False)
    avg_comprehension_score_bridging: float | str = field(default="unknown", init=False)
    avg_calibration_error: float | str = field(default="unknown", init=False)
    num_calibrations: int | str = field(default="unknown", init=False)
    num_validations: int | str = field(default="unknown", init=False)
    avg_validation_error: float | str = field(default="unknown", init=False)

    # eye tracking metadata
    tracked_eye: str = field(default="unknown", init=False)
    tracked_eye_consistent: bool = field(default=True, init=False)
    num_good_validations: int = field(default=0, init=False)
    num_moderate_validations: int = field(default=0, init=False)
    num_bad_validations: int = field(default=0, init=False)

    # completed trials
    num_completed_trials: int = field(default=0, init=False)

    # sanity report
    sanity_report_path: Path | str = field(default="unknown", init=False)

    # preprocessing pm
    pm_gaze_path: Path | str = field(default="unknown", init=False)
    pm_gaze_metadata: dict | str = field(default="unknown", init=False)

    # psychometric tests
    psychometric_tests_session: str = field(default="unknown", init=False)

    # data formats
    # True by default: our pipeline produces all formats. Other pipelines may
    # set these to False when a format is not generated.
    raw_data: bool = field(default=True, init=False)
    fixations: bool = field(default=True, init=False)
    saccades: bool = field(default=True, init=False)
    reading_measures: bool = field(default=True, init=False)
    answers: bool = field(default=True, init=False)

    # per-trial metrics
    trials: list[Trial] | str = field(default="unknown", init=False)

    @property
    def sid(self) -> "Sid":
        return Sid(self.session_identifier)

    def create_overview(self) -> dict:
        """
        Create a topic-grouped overview of the session.

        Returns
        -------
        dict
            Overview with sections: administrative, technical_setup, tracking,
            calibration_validation, data_quality, experiment_procedure,
            comprehension, and data_formats.
        """
        self._create_stats()

        return {
            "administrative": {
                "participant_id": self.participant_id,
                "session_identifier": self.session_identifier,
                "is_pilot": self.is_pilot,
                "year_of_data_collection": self._get_metadata("year", "unknown"),
                "month_of_data_collection": self._get_metadata("month", "unknown"),
            },
            "technical_setup": self._technical_setup(),
            "tracking": {
                "tracked_eye": self.tracked_eye,
                "tracked_eye_consistent": self.tracked_eye_consistent,
            },
            "calibration_validation": {
                "num_calibrations": self.num_calibrations,
                "num_validations": self.num_validations,
                "avg_calibration_error_dva": self.avg_calibration_error,
                "avg_validation_error_dva": self.avg_validation_error,
                "num_good_validations": self.num_good_validations,
                "num_moderate_validations": self.num_moderate_validations,
                "num_bad_validations": self.num_bad_validations,
            },
            "data_quality": {
                "session_total_data_loss_ratio": getattr(
                    self,
                    "_measure_total_data_loss_ratio",
                    None,
                ),
                "session_blink_loss_ratio": getattr(
                    self,
                    "_measure_blink_loss_ratio",
                    None,
                ),
            },
            "experiment_procedure": {
                "question_order": self.question_order,
                "stimulus_order_ids": self.stimulus_order_ids,
                "stimulus_order_ids_with_names": self.stimulus_order_ids_with_names,
                "num_completed_trials": len(self.stimulus_order_ids)
                if isinstance(self.stimulus_order_ids, list)
                else None,
                "was_session_interrupted": self.interrupted,
                "obligatory_break_made": self.obligatory_break_made,
                "num_optional_breaks_made": self.num_optional_breaks_made,
                "total_break_time_s": self.total_break_time,
                "total_reading_time_s": self.total_reading_time,
                "total_session_duration_s": self.total_session_duration,
            },
            "trials": (
                [asdict(t) for t in self.trials]
                if isinstance(self.trials, list)
                else self.trials
            ),
            "comprehension": {
                "avg_comprehension_score": self.avg_comprehension_score,
                "avg_comprehension_score_local": self.avg_comprehension_score_local,
                "avg_comprehension_score_global": self.avg_comprehension_score_global,
                "avg_comprehension_score_bridging": self.avg_comprehension_score_bridging,
            },
            "data_formats": {
                "raw_data": self.raw_data,
                "fixations": self.fixations,
                "saccades": self.saccades,
                "reading_measures": self.reading_measures,
                "answers": self.answers,
            },
        }

    def _get_metadata(self, key: str, default: T = "unknown") -> str | T:
        """Return a value from pm_gaze_metadata without raising on missing keys."""
        if isinstance(self.pm_gaze_metadata, dict):
            return self.pm_gaze_metadata.get(key, default)
        return default

    def _technical_setup(self) -> dict:
        """Assemble the technical setup section from lab config and gaze metadata."""
        cfg = self.lab_config if isinstance(self.lab_config, LabConfig) else None
        mount = self._get_metadata("mount_configuration", {})
        if not isinstance(mount, dict):
            mount = {}

        def _resolve(attr: str, fallback: object = None) -> object:
            if cfg is not None:
                return getattr(cfg, attr, fallback)
            return fallback

        def _pair(tup: object) -> tuple[object, object]:
            if isinstance(tup, (tuple, list)) and len(tup) == 2:
                return tup[0], tup[1]
            return None, None

        screen_res_w, screen_res_h = _pair(_resolve("screen_resolution"))
        screen_size_w, screen_size_h = _pair(_resolve("screen_size_cm"))
        image_res_w, image_res_h = _pair(_resolve("image_resolution"))
        image_size_w, image_size_h = _pair(_resolve("image_size_cm"))

        return {
            "eye_tracker_name": _resolve("name_eye_tracker", None),
            "sampling_frequency_hz": _resolve("sampling_frequency_hz", None),
            "mount_type": mount.get("mount_type"),
            "head_stabilization": mount.get("head_stabilization"),
            "eyes_recorded": mount.get("eyes_recorded"),
            "pupil_data_type": self._get_metadata("pupil_data_type"),
            "screen_resolution_width_px": screen_res_w,
            "screen_resolution_height_px": screen_res_h,
            "screen_size_width_cm": screen_size_w,
            "screen_size_height_cm": screen_size_h,
            "screen_distance_cm": _resolve("screen_distance_cm", None),
            "image_resolution_width_px": image_res_w,
            "image_resolution_height_px": image_res_h,
            "image_size_width_cm": image_size_w,
            "image_size_height_cm": image_size_h,
        }

    def _compute_comprehension_scores(self) -> None:
        """Load the session answers CSV and compute mean comprehension scores.

        Scores are computed over experiment trials only (practice trials are
        excluded). Type-specific scores use the condition_number column where
        1=local, 2=bridging, 3=global.
        """
        default = "unknown"
        self.avg_comprehension_score = default
        self.avg_comprehension_score_local = default
        self.avg_comprehension_score_global = default
        self.avg_comprehension_score_bridging = default

        answers_csv = self.sid.answers_dir / f"{self.sid}_answers.csv"
        if not answers_csv.exists():
            return

        try:
            answers = pl.read_csv(answers_csv)
        except Exception as exc:
            logger.warning(f"Could not read answers CSV {answers_csv}: {exc}")
            return

        if answers.is_empty() or "is_correct" not in answers.columns:
            return

        experiment = answers.filter(~pl.col("trial").str.starts_with("PRACTICE_"))
        if experiment.is_empty():
            return

        correct = [c for c in experiment["is_correct"].to_list() if c is not None]
        if correct:
            self.avg_comprehension_score = round(
                sum(1 for c in correct if c) / len(correct), 3
            )

        type_map = {1: "local", 2: "bridging", 3: "global"}
        if "condition_number" in experiment.columns:
            for condition, name in type_map.items():
                subset = [
                    c
                    for c in experiment.filter(pl.col("condition_number") == condition)[
                        "is_correct"
                    ].to_list()
                    if c is not None
                ]
                if subset:
                    setattr(
                        self,
                        f"avg_comprehension_score_{name}",
                        round(sum(1 for c in subset if c) / len(subset), 3),
                    )

    def _compute_session_duration(self) -> float | None:
        """Return session duration in seconds from message timestamps, if available."""
        if not isinstance(self.messages, pl.DataFrame) or self.messages.is_empty():
            return None
        if "time" not in self.messages.columns:
            return None
        times = self.messages["time"].cast(pl.Float64).drop_nulls().to_list()
        if not times:
            return None
        min_t = min(times)
        max_t = max(times)
        return round((max_t - min_t) / 1000, 3)

    def _create_stats(self):
        self.num_calibrations = len(self.calibrations)
        self.num_validations = len(self.validations)

        self.tracked_eye = self._get_metadata("tracked_eye", "unknown")

        # Mean calibration and validation error (accuracy_avg column), if present.
        if (
            isinstance(self.validations, pl.DataFrame)
            and not self.validations.is_empty()
            and "accuracy_avg" in self.validations.columns
        ):
            vals = self.validations["accuracy_avg"].drop_nulls().to_list()
            if vals:
                self.avg_validation_error = round(sum(vals) / len(vals), 3)

        if (
            isinstance(self.calibrations, pl.DataFrame)
            and not self.calibrations.is_empty()
            and "accuracy_avg" in self.calibrations.columns
        ):
            vals = self.calibrations["accuracy_avg"].drop_nulls().to_list()
            if vals:
                self.avg_calibration_error = round(sum(vals) / len(vals), 3)

        if (
            not isinstance(self.validations, str)
            and not self.validations.is_empty()
            and {"accuracy_avg", "eye"}.issubset(self.validations.columns)
        ):
            scores = self.validations["accuracy_avg"].drop_nulls().to_list()
            eyes = self.validations["eye"].drop_nulls().to_list()
            self.num_good_validations = sum(
                1 for s in scores if s < settings.SINGLE_VALIDATION_GOOD_MAX
            )
            self.num_moderate_validations = sum(
                1
                for s in scores
                if settings.SINGLE_VALIDATION_GOOD_MAX
                <= s
                < settings.SINGLE_VALIDATION_MODERATE_MAX
            )
            self.num_bad_validations = sum(
                1 for s in scores if s >= settings.SINGLE_VALIDATION_MODERATE_MAX
            )

            non_standard = [
                e for e in eyes if e and e[0].lower() != self.tracked_eye.lower()
            ]
            self.tracked_eye_consistent = len(non_standard) == 0

        self._compute_comprehension_scores()

        self.trials = self._compute_trials()

        duration = self._compute_session_duration()
        if duration is not None:
            self.total_session_duration = duration

        if self.total_reading_time == "unknown":
            reading = self._compute_total_reading_time()
            if reading is not None:
                self.total_reading_time = reading

        order_with_names = self._compute_stimulus_order_with_names()
        if isinstance(order_with_names, list):
            self.stimulus_order_ids_with_names = order_with_names

    def _compute_total_reading_time(self) -> float | None:
        """Return total reading time in seconds from stimulus start/end timestamps.

        The timestamps are stored on the session when reading times are
        documented (sanity checks). Falls back to None when unavailable.
        """
        if (
            not isinstance(self.stimulus_start_end_ts, list)
            or not self.stimulus_start_end_ts
        ):
            return None
        total_ms = 0.0
        for entry in self.stimulus_start_end_ts:
            try:
                start = float(entry["start_ts"])
                stop = float(entry["stop_ts"])
            except (KeyError, TypeError, ValueError):
                continue
            total_ms += stop - start
        if total_ms <= 0:
            return None
        return round(total_ms / 1000, 3)

    def _compute_stimulus_order_with_names(
        self,
    ) -> list[dict[str, object]] | str:
        """Return the stimulus order as a list of trial/stim-id/stim-name mappings.

        Each entry maps the presented order to its trial, stimulus id, and
        stimulus name. Returns ``"unknown"`` when the stimulus order or stimulus
        metadata is not available.
        """
        if not isinstance(self.stimulus_order_ids, list) or not self.stimulus_order_ids:
            return "unknown"
        if not isinstance(self.stimuli, list):
            return "unknown"

        id_to_stim = {
            getattr(s, "id", None): s for s in self.stimuli if hasattr(s, "id")
        }
        id_to_stim = {sid: s for sid, s in id_to_stim.items() if sid is not None}

        result: list[dict[str, object]] = []
        for stim_id in self.stimulus_order_ids:
            entry: dict[str, object] = {"stimulus_id": stim_id}
            stim = id_to_stim.get(stim_id)
            if stim is not None:
                entry["stimulus_name"] = getattr(stim, "name", None)
                entry["trial"] = getattr(stim, "trial_id", None)
            result.append(entry)
        return result

    def _reading_time_by_trial(self) -> dict[str, float]:
        """Return total reading time in ms per trial from stimulus timestamps."""
        by_trial: dict[str, float] = {}
        if not isinstance(self.stimulus_start_end_ts, list):
            return by_trial
        for entry in self.stimulus_start_end_ts:
            try:
                start = float(entry["start_ts"])
                stop = float(entry["stop_ts"])
                trial = str(entry["trial"])
            except (KeyError, TypeError, ValueError):
                continue
            by_trial[trial] = by_trial.get(trial, 0.0) + (stop - start)
        return by_trial

    def _compute_trials(self) -> list[Trial] | str:
        """Assemble per-trial metrics from the answers CSV and reading times.

        Returns
        -------
        list[Trial] | str
            Per-trial metrics, or "unknown" when the answers CSV is missing.
        """
        answers_csv = self.sid.answers_dir / f"{self.sid}_answers.csv"
        if not answers_csv.exists():
            return "unknown"

        try:
            answers = pl.read_csv(answers_csv)
        except Exception as exc:
            logger.warning(f"Could not read answers CSV {answers_csv}: {exc}")
            return "unknown"

        required = {"trial", "stimulus", "stimulus_id", "is_correct"}
        if answers.is_empty() or not required.issubset(answers.columns):
            return "unknown"

        reading_by_trial = self._reading_time_by_trial()

        trials: list[Trial] = []
        for trial_id, group in answers.group_by("trial", maintain_order=True):
            trial_id = trial_id[0] if isinstance(trial_id, tuple) else trial_id
            correct = [c for c in group["is_correct"].to_list() if c is not None]
            if not correct:
                score = 0.0
            else:
                score = round(sum(1 for c in correct if c) / len(correct), 3)

            question_time = 0.0
            if "confirmation_rt_ms" in group.columns:
                q_times = [
                    float(t) for t in group["confirmation_rt_ms"].drop_nulls().to_list()
                ]
                question_time = round(sum(q_times), 3) if q_times else 0.0

            first = group.row(0, named=True)
            try:
                trial_number = int(str(trial_id).rsplit("_", 1)[-1])
            except ValueError:
                trial_number = 0

            trials.append(
                Trial(
                    trial_number=trial_number,
                    stimulus_id=int(first["stimulus_id"]),
                    stimulus_name=str(first["stimulus"]),
                    is_practice=str(trial_id).startswith("PRACTICE_"),
                    num_questions=group.height,
                    comprehension_score=score,
                    comprehension_question_time_ms=question_time,
                    reading_time_ms=round(reading_by_trial.get(str(trial_id), 0.0), 3),
                )
            )

        trials.sort(key=lambda t: (t.is_practice, t.trial_number))
        return trials

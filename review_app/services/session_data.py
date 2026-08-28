"""Read session overview YAML and compute check results with threshold comparison."""

from pathlib import Path

import yaml

from ..models import CheckResult, ReviewAnnotation, SessionDetail
from .thresholds import check_value

# Mapping from overview YAML field names to check metadata.
# Ordered by category for display grouping.
CHECK_REGISTRY: list[dict] = [
    # Eye-tracker metadata
    {"field": "tracked_eye", "label": "Tracked eye", "category": "Hardware"},
    {
        "field": "tracked_eye_consistent",
        "label": "Tracked eye consistent",
        "category": "Hardware",
    },
    {"field": "eye_tracker_name", "label": "Eye tracker", "category": "Hardware"},
    {
        "field": "sampling_frequency_hz",
        "label": "Sampling frequency (Hz)",
        "category": "Hardware",
    },
    {"field": "mount_type", "label": "Mount type", "category": "Hardware"},
    {
        "field": "head_stabilization",
        "label": "Head stabilization",
        "category": "Hardware",
    },
    {"field": "eyes_recorded", "label": "Eyes recorded", "category": "Hardware"},
    {"field": "pupil_data_type", "label": "Pupil data type", "category": "Hardware"},
    {
        "field": "screen_resolution_width_px",
        "label": "Screen resolution width (px)",
        "category": "Hardware",
    },
    {
        "field": "screen_resolution_height_px",
        "label": "Screen resolution height (px)",
        "category": "Hardware",
    },
    {
        "field": "screen_size_width_cm",
        "label": "Screen size width (cm)",
        "category": "Hardware",
    },
    {
        "field": "screen_size_height_cm",
        "label": "Screen size height (cm)",
        "category": "Hardware",
    },
    {
        "field": "screen_distance_cm",
        "label": "Screen distance (cm)",
        "category": "Hardware",
    },
    {
        "field": "image_resolution_width_px",
        "label": "Image resolution width (px)",
        "category": "Hardware",
    },
    {
        "field": "image_resolution_height_px",
        "label": "Image resolution height (px)",
        "category": "Hardware",
    },
    {
        "field": "image_size_width_cm",
        "label": "Image size width (cm)",
        "category": "Hardware",
    },
    {
        "field": "image_size_height_cm",
        "label": "Image size height (cm)",
        "category": "Hardware",
    },
    # Calibration & validation
    {
        "field": "num_calibrations",
        "label": "Number of calibrations",
        "category": "Calibration",
    },
    {
        "field": "num_validations",
        "label": "Number of validations",
        "category": "Calibration",
    },
    {
        "field": "avg_calibration_error_dva",
        "label": "Avg calibration error",
        "category": "Calibration",
    },
    {
        "field": "avg_validation_error_dva",
        "label": "Avg validation error",
        "category": "Calibration",
    },
    {
        "field": "num_good_validations",
        "label": "Good validations",
        "category": "Calibration",
    },
    {
        "field": "num_moderate_validations",
        "label": "Moderate validations",
        "category": "Calibration",
    },
    {
        "field": "num_bad_validations",
        "label": "Bad validations",
        "category": "Calibration",
    },
    # Data quality
    {
        "field": "session_total_data_loss_ratio",
        "label": "Total data loss ratio",
        "category": "Data Quality",
    },
    {
        "field": "session_blink_loss_ratio",
        "label": "Blink loss ratio",
        "category": "Data Quality",
    },
    # Recording
    {
        "field": "total_session_duration_s",
        "label": "Session duration (s)",
        "category": "Recording",
    },
    {
        "field": "total_reading_time_s",
        "label": "Total reading time (s)",
        "category": "Recording",
    },
    {
        "field": "total_break_time_s",
        "label": "Total break time (s)",
        "category": "Recording",
    },
    {
        "field": "mean_rt_per_stim_ms",
        "label": "Mean reading time per stimulus (ms)",
        "category": "Recording",
    },
    {
        "field": "sd_rt_per_stim_ms",
        "label": "SD reading time per stimulus (ms)",
        "category": "Recording",
    },
    {
        "field": "obligatory_break_made",
        "label": "Obligatory break taken",
        "category": "Recording",
    },
    {
        "field": "num_optional_breaks_made",
        "label": "Optional breaks taken",
        "category": "Recording",
    },
    # Experiment
    {
        "field": "num_completed_trials",
        "label": "Completed trials",
        "category": "Experiment",
    },
    {
        "field": "num_experiment_trials",
        "label": "Experiment trials completed",
        "category": "Experiment",
    },
    {
        "field": "num_practice_trials",
        "label": "Practice trials completed",
        "category": "Experiment",
    },
    {
        "field": "was_session_interrupted",
        "label": "Session interrupted",
        "category": "Experiment",
    },
    # Comprehension
    {
        "field": "avg_comprehension_score",
        "label": "Avg comprehension score",
        "category": "Comprehension",
    },
    {
        "field": "avg_comprehension_score_local",
        "label": "Avg local comprehension score",
        "category": "Comprehension",
    },
    {
        "field": "avg_comprehension_score_global",
        "label": "Avg global comprehension score",
        "category": "Comprehension",
    },
    {
        "field": "avg_comprehension_score_bridging",
        "label": "Avg bridging comprehension score",
        "category": "Comprehension",
    },
    # Data presence
    {"field": "raw_data", "label": "Raw data present", "category": "Data Files"},
    {"field": "fixations", "label": "Fixations present", "category": "Data Files"},
    {"field": "saccades", "label": "Saccades present", "category": "Data Files"},
    {
        "field": "reading_measures",
        "label": "Reading measures present",
        "category": "Data Files",
    },
    {"field": "answers", "label": "Answers present", "category": "Data Files"},
]


def read_overview(path: Path) -> dict | None:
    """Read a session or dataset overview YAML.

    :param path: Path to the YAML file.
    :returns: Dict of values, or None if file not found.
    """
    if not path.exists():
        return None
    with open(path) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def get_field(overview: dict, field: str) -> object | None:
    """Resolve a field from a session overview, searching nested sections.

    Session overviews are grouped into topic sections (e.g. ``Data_quality``).
    This helper finds a field either at the top level (legacy flat overviews)
    or inside any section dict.

    :param overview: Dict from a session overview YAML.
    :param field: Field name to look up.
    :returns: The value, or None if not found.
    """
    if field in overview:
        return overview[field]
    for section in overview.values():
        if isinstance(section, dict) and field in section:
            return section[field]
    return None


def compute_checks(overview: dict, thresholds: dict | None) -> list[CheckResult]:
    """Compute CheckResult list from overview values and thresholds.

    :param overview: Dict from session overview YAML.
    :param thresholds: Thresholds dict or None.
    :returns: List of CheckResult with pass/warn/fail status.
    """
    checks: list[CheckResult] = []
    for entry in CHECK_REGISTRY:
        field = entry["field"]
        value = get_field(overview, field)
        if value is None:
            continue
        if not _is_checkable(value):
            continue
        threshold_spec, status = check_value(field, value, thresholds)
        checks.append(
            CheckResult(
                check_id=field,
                label=entry["label"],
                value=_serialize(value),
                threshold=_serialize_threshold(threshold_spec),
                status=status,
            )
        )
    return checks


def _is_checkable(value: object) -> bool:
    """Returns True if the value type can be compared against thresholds."""
    return isinstance(value, (int, float, bool, str))


def _serialize(value: object) -> str | float | int | bool | None:
    """Serialize a value for the API response (passthrough for primitive types)."""
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, (int, bool, str)):
        return value
    if value is None:
        return None
    return str(value)


def _serialize_threshold(value: object) -> str | list[float | int] | None:
    """Serialize a threshold spec — bare int/float becomes str.

    ``CheckResult.threshold`` accepts ``str | list[float | int] | None`` but
    NOT bare ``int``/``float``. This converter ensures scalar numeric thresholds
    (e.g. ``num_completed_trials: 6`` in a legacy ``quality_thresholds.yaml``)
    are rendered as strings instead of crashing pydantic validation.
    """
    if isinstance(value, list):
        return [float(v) if isinstance(v, (int, float)) else v for v in value]
    if value is None:
        return None
    return str(value)


def build_session_detail(
    overview: dict,
    review: ReviewAnnotation,
    thresholds: dict | None,
    dcn_name: str,
    sid: str,
) -> SessionDetail:
    """Build a SessionDetail from overview YAML, review, and thresholds.

    :param overview: Dict from session overview YAML.
    :param review: ReviewAnnotation (may be empty for unreviewed).
    :param thresholds: Thresholds dict or None.
    :param dcn_name: Data collection name (for plot path resolution).
    :param sid: Session identifier.
    :returns: SessionDetail model.
    """
    pid = get_field(overview, "participant_id") or 0
    is_pilot = get_field(overview, "is_pilot") or False
    checks = compute_checks(overview, thresholds)

    from ..config import sanity_checks_path

    plots_dir = sanity_checks_path(dcn_name, sid) / f"{sid}_plots"
    plots_available = plots_dir.exists()

    return SessionDetail(
        sid=sid,
        pid=pid,
        is_pilot=is_pilot,
        overview=overview,
        checks=checks,
        review=review,
        plots_available=plots_available,
    )

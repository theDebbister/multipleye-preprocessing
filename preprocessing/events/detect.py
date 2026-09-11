"""Event detection functions."""

from ..config import settings
from ..events.properties import compute_event_properties


def detect_fixations(
    gaze,
    method: str | None = None,
    minimum_duration: int | None = None,
    velocity_threshold: float | None = None,
) -> None:
    """
    This function applies a fixation detection method and then computes
    descriptive properties (such as fixation location).

    Parameters
    ----------
    gaze : pm.Gaze
        The gaze object containing gaze samples and trial metadata.

    method : {"ivt", "idt"} | None, optional
        Event detection method:
        - ``"ivt"`` (Velocity-Threshold Identification):
          Samples are classified as fixations when their velocity is below
          ``velocity_threshold`` degrees/second. Consecutive samples are
          merged into fixation events. This is the default method.
        - ``"idt"`` (Dispersion-Threshold Identification):
          Groups points that remain within a spatial dispersion window for
          at least ``minimum_duration`` ms.
        Defaults to ``settings.FIXATION_METHOD``.

    minimum_duration : int | None, optional
        Minimum duration (in milliseconds) for a group of samples to be
        classified as a fixation. Defaults to ``settings.FIXATION_MINIMUM_DURATION_MS``.

    velocity_threshold : float | None, optional
        Velocity threshold used by the IVT method (in degrees/second).
        Defaults to ``settings.FIXATION_VELOCITY_THRESHOLD``.

    Notes
    -----
    After detection, fixation properties (e.g., fixation location) are
    computed and added to ``gaze.events``.
    """
    if method is None:
        method = settings.FIXATION_METHOD
    if minimum_duration is None:
        minimum_duration = settings.FIXATION_MINIMUM_DURATION_MS
    if velocity_threshold is None:
        velocity_threshold = settings.FIXATION_VELOCITY_THRESHOLD

    gaze.detect(
        method, minimum_duration=minimum_duration, velocity_threshold=velocity_threshold
    )

    compute_event_properties(
        gaze, settings.FIXATION, settings.EVENT_PROPERTIES[settings.FIXATION]
    )


def detect_saccades(
    gaze,
    minimum_duration: int | None = None,
    threshold_factor: float | None = None,
) -> None:
    """
    This function detects saccades (or micro-saccades) using a
    noise-adaptive velocity threshold and then computes properties such as
    saccade amplitude and peak velocity.

    Parameters
    ----------
    gaze : pm.Gaze
        The gaze object.

    minimum_duration : int | None, optional
        Minimum duration (in samples) required for a velocity peak to be
        considered a saccade. Shorter events are ignored as noise.
        Defaults to ``settings.SACCADE_MINIMUM_DURATION``.

    threshold_factor : float | None, optional
        Multiplier that determines the velocity threshold relative to the
        noise level in the signal. Increasing this value makes detection
        more conservative (fewer saccades). Defaults to
        ``settings.SACCADE_THRESHOLD_FACTOR``.

    Notes
    -----
    After detection, saccade properties (e.g., amplitude and peak velocity)
    are computed and added to ``gaze.events``.
    """
    if minimum_duration is None:
        minimum_duration = settings.SACCADE_MINIMUM_DURATION
    if threshold_factor is None:
        threshold_factor = settings.SACCADE_THRESHOLD_FACTOR

    gaze.detect(
        settings.SACCADE_METHOD,
        minimum_duration=minimum_duration,
        threshold_factor=threshold_factor,
    )

    compute_event_properties(
        gaze, settings.SACCADE, settings.EVENT_PROPERTIES[settings.SACCADE]
    )

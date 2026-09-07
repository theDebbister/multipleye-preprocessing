"""Functions for loading and processing gaze data from various formats."""

import json
import logging
import re
from pathlib import Path

import polars as pl
import pymovements as pm
import yaml
from pymovements import transforms
from pymovements.events import Events

from ..config import settings
from ..data_collection.stimulus import LabConfig
from ..models.sid import Sid


def _blink_loss_table(
    per_group_blink: pl.DataFrame,
    per_group_sample_count: pl.DataFrame,
    group_cols: list[str],
    duration_col: str,
    sr: float,
) -> pl.DataFrame:
    """Build a blink-loss table grouped by a given set of columns.

    Joins summed blink durations per group with the sample count per group and
    derives the blink-loss ratio and recording duration.

    Parameters
    ----------
    per_group_blink : pl.DataFrame
        Blink events grouped by ``group_cols`` with a ``blink_duration_ms`` column.
    per_group_sample_count : pl.DataFrame
        Sample counts grouped by ``group_cols`` with a ``sample_count`` column.
    group_cols : list of str
        Columns used for grouping (e.g. per-page or per-trial columns).
    duration_col : str
        Name of the output recording-duration column.
    sr : float
        Sampling rate in Hz.

    Returns
    -------
    pl.DataFrame
        A table with ``group_cols``, ``blink_loss_ratio``, ``blink_duration_ms`` and
        ``duration_col`` columns.
    """
    return (
        per_group_blink.join(
            per_group_sample_count,
            on=group_cols,
            how="right",
        )
        .with_columns(
            (
                pl.col("blink_duration_ms").fill_null(0)
                / (pl.col("sample_count") * 1000.0 / sr)
            ).alias("blink_loss_ratio")
        )
        .with_columns((pl.col("sample_count") * 1000.0 / sr).alias(duration_col))
        .select(
            [
                *group_cols,
                "blink_loss_ratio",
                "blink_duration_ms",
                duration_col,
            ]
        )
    )


def load_gaze_data(
    asc_file: Path,
    lab_config: LabConfig,
    sid: Sid,
    trial_cols: list[str] | None = None,
    messages: bool | list[str] = False,
) -> pm.Gaze:
    """Load sample gaze data from an ASC file.

    This function extracts and processes gaze data: Identify trials, stimulus details, activities,
    and practice sessions by pattern matching.
    Non-trial data is filtered out from the results before returning the processed gaze object.

    Parameters
    ----------
    asc_file : Path
        Path to the ASC file containing gaze data.
    lab_config : LabConfig
        Configuration object containing details about the lab environment,
        including screen resolution, screen size (in cm),
        and the eye-tracking device's sampling rate.
    sid : Sid
        The session identifier.
    trial_cols : list of str, optional
        List of columns to be associated with trial-level metadata. Default is None.
    messages : bool or list of str, optional
        Whether to extract messages from the ASC file. If True, all messages are extracted.
        If a list of strings is provided, only messages matching the patterns are extracted.
        Default is False.

    Returns
    -------
    pm.Gaze
        A gaze object that encapsulates the processed and structured gaze data,
        along with associated metadata, such as sampling rate, screen configuration,
        and experimental details.
    """

    # Initialize experiment config from lab config. Although sampling rate and resolution are automatically inferred
    # in from_asc(), the function will emit a warning in case the parsed values do not match the experiment specification.
    # This way we perform a sanity check for the experiment configuration.
    experiment = pm.Experiment(
        screen_width_px=lab_config.image_resolution[0],
        screen_height_px=lab_config.image_resolution[1],
        screen_width_cm=lab_config.image_size_cm[0],
        screen_height_cm=lab_config.image_size_cm[1],
        distance_cm=lab_config.screen_distance_cm,
        sampling_rate=lab_config.sampling_frequency_hz,
    )

    if messages is None:
        messages = False

    gaze = pm.gaze.from_asc(
        asc_file,
        patterns=settings.GAZE_PATTERNS,
        trial_columns=trial_cols,
        add_columns={"session": str(sid)},
        experiment=experiment,
        messages=messages,
        events=True,
    )

    # Compute measure-based blink loss via measure_events_ratio.
    # Session-level (duration-weighted), not per-trial mean.
    # Parsed events (including blinks) are available here but must be cleared
    # before returning -- they crash save_raw_data's unnest of the pixel column.
    sr = gaze.experiment.sampling_rate or float(
        gaze._metadata.get("sampling_rate", 1000.0),
    )
    trial_cols = gaze.trial_columns or ["trial", "stimulus", "page"]

    if gaze.events is not None and not gaze.events.frame.is_empty():
        # Use transforms.events2timeratio directly with trial_columns=None
        # for session-level blink loss. gaze.measure_events_ratio() always
        # passes self.trial_columns, which produces a per-row expression
        # that crashes .item() on multi-sample DataFrames.
        # TODO: switch back to gaze.measure_events_ratio(trial_columns=None)
        # once https://github.com/pymovements/pymovements/issues/1673 ships.
        blink_expr = transforms.events2timeratio(
            events=gaze.events.frame,
            samples=gaze.samples,
            name="blink_eyelink",
            time_column="time",
            trial_columns=None,
            sampling_rate=sr,
        )
        gaze._measure_blink_loss_ratio = gaze.samples.select(blink_expr).item()

        blink_events = gaze.events.frame.filter(pl.col("name").str.contains("blink"))
        if not blink_events.is_empty():
            # Per-page blink loss: one row per page, time-weighted within the page.
            per_page_blink = blink_events.group_by(trial_cols).agg(
                pl.col("duration").sum().alias("blink_duration_ms")
            )
            per_page_sample_count = gaze.samples.group_by(trial_cols).agg(
                pl.len().alias("sample_count")
            )
            gaze._per_page_blink_loss = _blink_loss_table(
                per_page_blink,
                per_page_sample_count,
                group_cols=trial_cols,
                duration_col="page_duration_ms",
                sr=sr,
            )

            # Per-trial blink loss: one row per trial (time-weighted within the
            # trial). Trials are not weighted by length against each other; the
            # sanity report takes a plain, equal-weighted mean over trial rows.
            per_trial_cols = ["trial", "stimulus"]
            per_trial_blink = blink_events.group_by(per_trial_cols).agg(
                pl.col("duration").sum().alias("blink_duration_ms")
            )
            per_trial_sample_count = gaze.samples.group_by(per_trial_cols).agg(
                pl.len().alias("sample_count")
            )
            gaze._per_trial_blink_loss = _blink_loss_table(
                per_trial_blink,
                per_trial_sample_count,
                group_cols=per_trial_cols,
                duration_col="trial_duration_ms",
                sr=sr,
            )
        else:
            gaze._per_page_blink_loss = None
            gaze._per_trial_blink_loss = None

    # Clear parsed events to avoid save_raw_data crash.
    gaze.events = Events(
        data=pl.DataFrame(
            schema={col: pl.Utf8 for col in trial_cols},
        ),
        trial_columns=trial_cols,
    )

    # Filter out data outside of trials
    # TODO: Also report time spent outside of trials
    gaze.samples = gaze.samples.filter(
        pl.col("trial").is_not_null() & pl.col("page").is_not_null()
    )

    return gaze


def load_trial_level_raw_data(
    sid: Sid,
    trial_columns: list[str],
    file_pattern: str | None = None,
    load_metadata: bool = False,
) -> pm.Gaze:
    """Load trial-level raw data from multiple CSV files and construct a gaze object.

    This function aggregates raw data files containing gaze data with position and velocity information for one or more trials.

    Parameters
    ----------
    sid : Sid
        The session identifier.
    trial_columns : list of str
        Column names that uniquely identify a trial within the data.
    file_pattern : str, optional
        The file search pattern for raw data CSV files. Defaults to None, which uses settings.RAW_DATA_FILE_GLOB.
    load_metadata : bool, optional
        Whether to load metadata files (`gaze_metadata.json`, `experiment.yaml`,
        `validations.tsv`, `calibrations.tsv`) to enrich the gaze object.

    Returns
    -------
    pm.Gaze
        A gaze object containing the trial-level aggregated gaze data along with
        any associated metadata, validations, calibrations, and experiment settings, if provided.
    """
    data_folder = sid.raw_data_dir
    if file_pattern is None:
        file_pattern = settings.RAW_DATA_FILE_GLOB

    regex_name = settings.RAW_DATA_FILENAME_REGEX

    initial_df = pl.DataFrame()

    for file in data_folder.glob(file_pattern):
        trial_df = pl.read_csv(
            file,
            schema_overrides={
                "time": pl.Float64,
                "pupil": pl.Float64,
                "pixel_x": pl.Float64,
                "pixel_y": pl.Float64,
                "position_x": pl.Float64,
                "position_y": pl.Float64,
                "velocity_x": pl.Float64,
                "velocity_y": pl.Float64,
                "page": pl.Utf8,
            },
        )
        match = re.match(regex_name, file.stem)
        trial_df = trial_df.with_columns(
            pl.lit(match.group("trial")).alias("trial"),
            pl.lit(match.group("stimulus")).alias("stimulus"),
        )

        initial_df = initial_df.vstack(trial_df)

    if initial_df.is_empty():
        raise ValueError(
            f"No raw data files found in {data_folder} with pattern {file_pattern}"
        )

    gaze = pm.Gaze(
        initial_df,
        trial_columns=trial_columns,
        pixel_columns=["pixel_x", "pixel_y"],
        position_columns=["position_x", "position_y"],
        velocity_columns=["velocity_x", "velocity_y"],
    )

    if load_metadata:
        metadata_path = sid.metadata_dir

        with open(metadata_path / "gaze_metadata.json", encoding="utf8") as f:
            metadata = json.load(f)

        gaze._metadata = metadata

        with open(metadata_path / "experiment.yaml") as f:
            exp = yaml.safe_load(f)

        with open(metadata_path / "validations.tsv", encoding="utf8") as f:
            validations_df = pl.read_csv(f, separator="\t")

        gaze.validations = validations_df

        with open(metadata_path / "calibrations.tsv", encoding="utf8") as f:
            calibrations_df = pl.read_csv(f, separator="\t")

        gaze.calibrations = calibrations_df

        exp = pm.Experiment.from_dict(exp)

        gaze.experiment = exp

        messages_path = metadata_path / "messages.csv"
        if messages_path.exists():
            gaze.messages = pl.read_csv(messages_path)

    return gaze


def load_trial_level_events_data(
    gaze: pm.Gaze,
    sid: Sid,
    event_type: str,
    file_pattern: str | None = None,
) -> pm.Gaze:
    """Load and processes trial-level event data for a given type.

    The function reads CSV files within a specified folder,
    applies a file pattern to match and extract relevant groups,
    and integrates the data into the provided `gaze` object.
    Combine with existing event data if present.

    Parameters
    ----------
    gaze : pm.Gaze
        An object containing gaze data and associated event information.
    sid : Sid
        The session identifier.
    event_type : str
        The type of event to load, must be one of the keys in `DEFAULT_EVENT_PROPERTIES`.
    file_pattern : str, optional
        A pattern for matching CSV file names to extract relevant groups.
        If None, defaults to settings.EVENT_DATA_FILE_GLOB formatted with event_type.

    Returns
    -------
    pm.Gaze
        The updated gaze object with the loaded and integrated event data.
    """
    if event_type == "fixation":
        data_folder = sid.fixations_dir
    elif event_type == "saccade":
        data_folder = sid.saccades_dir
    else:
        raise ValueError(
            f"event_type must be {list(settings.EVENT_PROPERTIES.keys())}, got {event_type}"
        )

    if file_pattern is None:
        file_pattern = settings.EVENT_DATA_FILENAME_REGEX.format(event_type=event_type)

    all_events = pl.DataFrame()
    for file in data_folder.glob(
        settings.EVENT_DATA_FILE_GLOB.format(event_type=event_type)
    ):
        trial_df = pl.read_csv(file)

        match = re.match(file_pattern, file.name)
        # go over groups in the name regex and add them as columns
        if match is None:
            logging.info(f"Skipping file {file} for event loading")
        else:
            for group_name in match.groupdict():
                if group_name not in trial_df.columns:
                    trial_df = trial_df.with_columns(
                        pl.lit(match.group(group_name)).alias(group_name)
                    )

        all_events = all_events.vstack(trial_df)

    all_events = all_events.with_columns(pl.lit(event_type).alias("name"))

    # if there have already been events detected, keep them
    if not gaze.events.frame.is_empty():
        original_events = gaze.events.frame

        new_events = pm.Events(
            all_events,
            trial_columns=gaze.trial_columns,
        )

        new_events = new_events.frame.with_columns(pl.lit(event_type).alias("name"))

        # if one df has more columns than the other, add the missing columns with same column type!
        for col in original_events.columns:
            if col not in new_events.columns:
                dtype = original_events[col].dtype
                new_events = new_events.with_columns(
                    pl.lit(None).cast(dtype).alias(col)
                )
        for col in new_events.columns:
            if col not in original_events.columns:
                dtype = new_events[col].dtype
                original_events = original_events.with_columns(
                    pl.lit(None).cast(dtype).alias(col)
                )
        # sort columns to be in the same order
        new_events = new_events.select(original_events.columns)

        all_events = original_events.vstack(new_events)

    gaze.events = pm.Events(
        all_events,
        trial_columns=gaze.trial_columns,
    )

    return gaze


def load_scanpaths(
    gaze: pm.Gaze,
    sid: Sid,
    file_pattern: str | None = None,
) -> pm.Gaze:
    """Load scanpaths for a session from CSV files and return a gaze object with expanded events frame.

    The function reads CSV files within a specified folder,
    applies a file pattern to match and extract relevant groups,
    and integrates the data into the provided `gaze` object's events frame.

    Parameters
    ----------
    gaze : pm.Gaze
        An object containing gaze data and associated event information.
    sid : Sid
        The session identifier.
    file_pattern : str, optional
        A pattern for matching CSV file names to extract relevant groups.
        If None, defaults to settings.SCANPATH_FILENAME_REGEX.

    Returns
    -------
    pm.Gaze
        The updated gaze object with the loaded and integrated scanpaths.
    """

    if file_pattern is None:
        file_pattern = settings.SCANPATH_FILENAME_REGEX

    all_scanpaths = pl.DataFrame()
    data_folder = sid.scanpaths_dir

    for file in data_folder.glob(settings.SCANPATH_FILE_GLOB):
        trial_df = pl.read_csv(file)

        match = re.match(file_pattern, file.name)
        # go over groups in the name regex and add them as columns
        if match is None:
            logging.info(f"Skipping file {file} for scanpath loading")
            continue
        else:
            for group_name in match.groupdict():
                if group_name not in trial_df.columns:
                    trial_df = trial_df.with_columns(
                        pl.lit(match.group(group_name)).alias(group_name)
                    )

        all_scanpaths = all_scanpaths.vstack(trial_df)

    if len(all_scanpaths) == 0:
        # return gaze untouched if no scanpaths files were found
        return gaze

    # join loaded scanpaths into existing events frame
    key_cols = ["onset", "trial", "stimulus", "page", "name"]
    imported_cols = [
        col
        for col in all_scanpaths.columns
        if col not in gaze.events.frame.columns or col in key_cols
    ]

    matched_events = gaze.events.frame.join(
        all_scanpaths.select(imported_cols), on=key_cols, how="left"
    )

    gaze.events.frame = matched_events

    return gaze


def load_reading_measures(
    sid: Sid,
    file_pattern: str | None = None,
) -> pl.DataFrame:
    """Load reading measures from CSV files.

    Parameters
    ----------
    sid : Sid
        The session identifier.
    file_pattern : str, optional
        Regex pattern to extract trial and stimulus from filenames.
        Defaults to ``settings.READING_MEASURES_FILENAME_REGEX``.

    Returns
    -------
    pl.DataFrame
        A DataFrame containing the concatenated reading measures data.
    """
    data_folder = sid.reading_measures_dir
    glob_pattern = settings.READING_MEASURES_GLOB
    regex = file_pattern or settings.READING_MEASURES_FILENAME_REGEX

    all_trials = []

    for file in data_folder.glob(glob_pattern):
        match = re.match(regex, file.name)
        if not match:
            continue

        df = pl.read_csv(file)
        trial_df = df.with_columns(
            pl.lit(match.group("trial")).alias("trial"),
            pl.lit(match.group("stimulus")).alias("stimulus"),
        )
        all_trials.append(trial_df)

    if not all_trials:
        raise ValueError(f"No reading measures files found in {data_folder}")

    return pl.concat(all_trials)

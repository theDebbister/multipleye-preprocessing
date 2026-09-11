"""Functions for saving data."""

import contextlib
import json

import polars as pl
import pymovements as pm

from ..models.sid import Sid


def save_raw_data(sid: Sid, data: pm.Gaze) -> None:
    """
    Saves raw gaze data with calculated position and velocity in separate csv files per trial.

    Parameters
    ----------
    sid : Sid
        The session identifier.
    data : pm.Gaze
        The gaze data as a pymovements Gaze object.
    """
    directory = sid.raw_data_dir
    directory.mkdir(parents=True, exist_ok=True)

    new_data = data.clone()

    trials = new_data.split(by="trial", as_dict=False)

    for trial in trials:
        with contextlib.suppress(Warning):
            trial.unnest()
        df = trial.samples
        trial = df["trial"][0]
        stimulus = df["stimulus"][0]
        name = f"{sid!s}_{trial}_{stimulus}_raw_data.csv"
        df = df[
            "time",
            "pixel_x",
            "pixel_y",
            "position_x",
            "position_y",
            "velocity_x",
            "velocity_y",
            "pupil",
            "page",
        ]
        df.write_csv(directory / name)


def save_events_data(
    event_type: str,
    sid: Sid,
    split_column: str,
    name_columns: list[str],
    file_columns: list[str],
    data: pm.Gaze,
) -> None:
    """
    Saves events data (fixations or saccades) in separate csv files. The input is expected to be
    produced with pymovements.

    Parameters
    ----------
    event_type : str
        What type of event should be stored. Either "fixation" or "saccade".
    sid : Sid
        The session identifier.
    split_column : str
        What column to split the events data by. The function will create a separate file for each
        unique value in this column.
    name_columns : list of str
        Column values per split that should be included in the file name.
    file_columns : list of str
        Columns that should be included in the saved csv file.
    data : pm.Gaze
        The events data as a pymovements Gaze object.
    """

    if event_type not in ["fixation", "saccade"]:
        raise ValueError(
            "Only fixations and saccades are currently supported as events."
        )

    directory = sid.fixations_dir if event_type == "fixation" else sid.saccades_dir
    directory.mkdir(parents=True, exist_ok=True)

    data_copy = data.clone()
    data_copy.events.unnest()

    events = data_copy.events.frame.filter(pl.col("name") == event_type)

    for group in events.partition_by(split_column):
        name = f"{sid!s}"
        for col in name_columns:
            if col not in group.columns:
                raise ValueError(f"Column {col} not found in events data.")
            name += f"_{group[col][0]}"

        name += f"_{event_type}.csv"

        df = group.select(file_columns)
        df.write_csv(directory / name)


def save_scanpaths(sid: Sid, data: pm.Gaze) -> None:
    """
    Saves scanpaths in separate csv files per trial.

    Parameters
    ----------
    sid : Sid
        The session identifier.
    data : pm.Gaze
        The gaze data as a pymovements Gaze object.
    """
    directory = sid.scanpaths_dir
    directory.mkdir(parents=True, exist_ok=True)

    new_data = data.clone()

    try:
        new_data.unnest()
        new_data.events.unnest()
    except Warning:
        # if the columns are already unnested there is a Warning (which interrupts)
        pass

    trials = new_data.events.split(by="trial", as_dict=False)

    for trial in trials:
        df = trial.frame
        # drop all rows where there has been no aoi mapped
        # TODO: what to do about fixations were no aoi is mapped?
        df = df.filter(pl.col("char_idx").is_not_null())
        if df.is_empty():
            continue
        trial = df["trial"][0]
        stimulus = df["stimulus"][0]
        name = f"{sid!s}_{trial}_{stimulus}_scanpath.csv"

        df = df[
            "onset",
            "duration",
            "name",
            "location_x",
            "location_y",
            "char_idx",
            "char",
            "top_left_x",
            "top_left_y",
            "width",
            "height",
            "char_idx_in_line",
            "line_idx",
            "page",
            "unit_of_analysis_idx",
            "unit_of_analysis_idx_in_line",
            "unit_of_analysis",
        ]
        df.write_csv(directory / name)


def save_reading_measures(sid: Sid, data: pl.DataFrame) -> None:
    """
    Saves reading measures in separate csv files per trial.

    Parameters
    ----------
    sid : Sid
        The session identifier.
    data : pl.DataFrame
        The reading measures as a polars DataFrame.
    """
    directory = sid.reading_measures_dir
    directory.mkdir(parents=True, exist_ok=True)

    trials = data.partition_by(by="trial", as_dict=False)

    for trial in trials:
        trial_id = trial["trial"][0]
        stimulus = trial["stimulus"][0]
        name = f"{sid!s}_{trial_id}_{stimulus}_reading_measures.csv"
        trial = trial.drop("stimulus", "trial")
        trial.write_csv(directory / name)


def save_session_metadata(sid: Sid, gaze: pm.Gaze) -> None:
    """
    Saves session metadata in a json file and also saves the gaze object's metadata.

    Parameters
    ----------
    sid : Sid
        The session identifier.
    gaze : pm.Gaze
        The gaze data as a pymovements Gaze object.
    """
    metadata_directory = sid.metadata_dir
    metadata_directory.mkdir(parents=True, exist_ok=True)

    metadata = gaze._metadata
    metadata["datetime"] = str(metadata["datetime"])

    # remove validations and calibrations because they are already saved in separate files
    metadata.pop("calibrations", None)
    metadata.pop("validations", None)

    with open(metadata_directory / "gaze_metadata.json", "w", encoding="utf8") as f:
        json.dump(metadata, f)

    gaze.save(
        metadata_directory,
        save_events=False,
        save_samples=False,
        save_calibrations=False,
        save_validations=False,
    )

    # both are dfs
    validations = gaze.validations
    calibrations = gaze.calibrations

    validations.write_csv(metadata_directory / "validations.tsv", separator="\t")
    gaze.save_validations(metadata_directory / "validations.feather")

    calibrations.write_csv(metadata_directory / "calibrations.tsv", separator="\t")
    gaze.save_calibrations(metadata_directory / "calibrations.feather")

    if gaze.messages is not None and not gaze.messages.is_empty():
        gaze.messages.write_csv(
            metadata_directory / "messages.csv",
            include_header=True,
        )

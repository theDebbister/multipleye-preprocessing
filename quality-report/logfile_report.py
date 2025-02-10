import argparse
import logging
import math
from functools import partial
from pathlib import Path
from typing import Any, Callable, TextIO, Union

import PIL
import matplotlib.pyplot as plt
import pandas as pd
import polars as pl
import pymovements as pm
from matplotlib.patches import Circle

import config


def load_data(logfile: Path) -> pd.DataFrame:
    logfile_frame = pd.read_csv(logfile, encoding='utf-8', sep='\t')
    print(logfile_frame.head())
    return logfile_frame


ReportFunction = Callable[[str, Any, Union[list, tuple]], None]


def check_metadata(metadata: dict[str, Any], report: ReportFunction) -> None:
    num_calibrations = len(metadata["calibrations"])
    report(
        "Number of calibrations", num_calibrations, config.ACCEPTABLE_NUM_CALIBRATIONS
    )
    validation_scores_avg = [
        float(validation["validation_score_avg"])
        for validation in metadata["validations"]
    ]
    report(
        "AVG validation scores",
        validation_scores_avg,
        config.ACCEPTABLE_AVG_VALIDATION_SCORES,
    )
    validation_scores_max = [
        float(validation["validation_score_max"])
        for validation in metadata["validations"]
    ]
    report(
        "MAX validation scores",
        validation_scores_max,
        config.ACCEPTABLE_MAX_VALIDATION_SCORES,
    )
    validation_errors = [
        validation["error"].removesuffix(" ERROR")
        for validation in metadata["validations"]
    ]
    report("Validation errors", validation_errors, config.ACCEPTABLE_VALIDATION_ERRORS)

    data_loss_ratio = metadata["data_loss_ratio"]
    report(
        "Data loss ratio",
        data_loss_ratio,
        config.ACCEPTABLE_DATA_LOSS_RATIOS,
        percentage=True,
    )
    data_loss_ratio_blinks = metadata["data_loss_ratio_blinks"]
    report(
        "Data loss ratio due to blinks",
        data_loss_ratio_blinks,
        config.ACCEPTABLE_DATA_LOSS_RATIOS,
        percentage=True,
    )
    total_recording_duration = metadata["total_recording_duration_ms"] / 1000
    report(
        "Total recording duration",
        total_recording_duration,
        config.ACCEPTABLE_RECORDING_DURATIONS,
    )


def check_gaze(gaze: pm.GazeDataFrame, report: ReportFunction) -> None:
    num_practice_trials = (
        gaze.frame.filter(pl.col("practice") == True).select(pl.col("trial")).n_unique()
    )
    report(
        "Number of practice trials",
        num_practice_trials,
        config.ACCEPTABLE_NUM_PRACTICE_TRIALS,
    )
    num_trials = (
        gaze.frame.filter(pl.col("practice") == False)
        .select(pl.col("trial"))
        .n_unique()
    )
    report("Number of trials", num_trials, config.ACCEPTABLE_NUM_TRIALS)
    # TODO: All trials present, all pages, questions and ratings present, plausible reading times etc.


def preprocess(gaze: pm.GazeDataFrame) -> None:
    # Savitzky-Golay filter as in https://doi.org/10.3758/BRM.42.1.188
    window_length = round(
        gaze.experiment.sampling_rate / 1000 * config.SG_WINDOW_LENGTH
    )
    if window_length % 2 == 0:  # Must be odd
        window_length += 1
    gaze.pix2deg()
    gaze.pos2vel("savitzky_golay", window_length=window_length, degree=config.SG_DEGREE)
    gaze.detect("ivt")
    gaze.detect("microsaccades")
    for property, kwargs, event_name in [
        ("location", dict(position_column="pixel"), "fixation"),
        ("amplitude", dict(), "saccade"),
        ("peak_velocity", dict(), "saccade"),
    ]:
        processor = pm.EventGazeProcessor((property, kwargs))
        new_properties = processor.process(
            gaze.events,
            gaze,
            identifiers=gaze.trial_columns,
            name=event_name,
        )
        join_on = gaze.trial_columns + ["name", "onset", "offset"]
        gaze.events.add_event_properties(new_properties, join_on=join_on)
    # TODO: AOI mapping


def check_events(events: pm.EventDataFrame, report: ReportFunction) -> None:
    pass  # TODO: Fixations on/off stimulus etc.


def plot_gaze(gaze: pm.GazeDataFrame, stimulus_dir: Path, plots_dir: Path) -> None:
    for trial, stimulus, screen in (
            gaze.frame.select(pl.col("trial"), pl.col("stimulus"), pl.col("screen"))
                    .unique()
                    .iter_rows()
    ):
        stimulus_genre, stimulus_name, stimulus_id = stimulus.split("_")

        screen_gaze = gaze.frame.filter(
            (pl.col("trial") == trial) & (pl.col("screen") == screen)
        ).select(
            pl.col("pixel").list.get(0).alias("pixel_x"),
            pl.col("pixel").list.get(1).alias("pixel_y"),
        )
        screen_events = gaze.events.frame.filter(
            (pl.col("trial") == trial)
            & (pl.col("screen") == screen)
            & (pl.col("name") == "fixation")
        ).select(
            pl.col("duration"),
            pl.col("location").list.get(0).alias("pixel_x"),
            pl.col("location").list.get(1).alias("pixel_y"),
        )

        fig, ax = plt.subplots()
        if screen.startswith("page_"):
            stimulus_image_path = (
                    stimulus_dir
                    / "stimuli_images_zh_ch_1"
                    / f"{stimulus_genre.lower()}_{stimulus_name.lower()}_id{stimulus_id}_{screen}_zh.png"
            )
        elif screen.startswith("question_"):
            question_id = int(screen.split("_")[1])
            version = 1  # TODO: Use the correct version (question/answer order) for this subject
            stimulus_image_path = (
                    stimulus_dir
                    / "question_images_zh_ch_1"
                    / f"question_images_version_{version}"
                    / f"{stimulus_genre}_{stimulus_name}_id{stimulus_id}_question_{question_id:05.0f}_zh.png"
            )
        else:
            stimulus_image_path = (
                    stimulus_dir
                    / f"participant_instructions_images_zh_ch_1"
                    / f"{screen}_zh.png"
            )
        stimulus_image = PIL.Image.open(stimulus_image_path)
        ax.imshow(stimulus_image)
        plt.plot(
            screen_gaze["pixel_x"],
            screen_gaze["pixel_y"],
            color="black",
            linewidth=0.5,
            alpha=0.3,
        )
        for row in screen_events.iter_rows(named=True):
            fixation = Circle(
                (row["pixel_x"], row["pixel_y"]),
                math.sqrt(row["duration"]),
                color="blue",
                fill=True,
                alpha=0.5,
                zorder=10,
            )
            ax.add_patch(fixation)
        ax.set_xlim((0, gaze.experiment.screen.width_px))
        ax.set_ylim((gaze.experiment.screen.height_px, 0))
        fig.savefig(plots_dir / f"stimulus_{stimulus}_{screen}.png")
        plt.close(fig)


def report_to_file(
        name: str,
        values: Any,
        acceptable_values: Any,
        *,
        report_file: TextIO,
        percentage: bool = False,
) -> None:
    if not isinstance(values, (list, tuple)):
        values = [values]
    result = "❌"

    if isinstance(acceptable_values, list):  # List of acceptable values
        if all(value in acceptable_values for value in values):
            result = "✅"
    elif isinstance(acceptable_values, tuple):  # Range of acceptable values
        lower, upper = acceptable_values
        if all((lower <= value) and (upper >= value) for value in values):
            result = "✅"
    else:  # Single acceptable value
        if all(value == acceptable_values for value in values):
            result = "✅"

    if percentage:
        values = [f"{value:.2%}" for value in values]
    report_file.write(f"{result} {name}: {', '.join(map(str, values))}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a quality report for a MultiplEYE session"
    )
    parser.add_argument("EXPERIMENT_LOGFILE", type=Path, help="Path to EXPERIMENT_LOGFILE file")
    parser.add_argument(
        "--stimulus_dir", type=Path, help="Path to the stimulus directory"
    )
    parser.add_argument(
        "--report-to",
        type=Path,
        help="Path to save the report",
    )
    parser.add_argument("--plots-dir", type=Path, help="Path to save the plots")
    args = parser.parse_args()
    if args.report_to is None:
        args.report_to = Path(args.EXPERIMENT_LOGFILE.stem + "_logfile_report.txt")

    report_file = open(args.report_to, "w", encoding="utf-8")
    report = partial(report_to_file, report_file=report_file)

    logging.basicConfig(level=logging.INFO)

    logging.info("Loading data...")

    logging.info("Checking metadata...")

    logging.info("Checking gaze data...")

    logging.info("Preprocessing...")

    load_data(args.EXPERIMENT_LOGFILE)


if __name__ == "__main__":
    main()

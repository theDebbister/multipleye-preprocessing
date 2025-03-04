import argparse
import importlib
import logging
import math
from functools import partial
from pathlib import Path
from typing import Any, Callable, TextIO, Union

import PIL
import matplotlib.pyplot as plt
import polars as pl
import pymovements as pm
from matplotlib.patches import Circle

import config


def load_data(asc_file: Path, stimulus_dir: Path, config: Path) -> pm.GazeDataFrame:
    gaze = pm.gaze.from_asc(
        asc_file,
        patterns=[
            r"start_recording_(?P<trial>(?:PRACTICE_)?trial_\d+)_stimulus_(?P<stimulus>[^_]+_[^_]+_\d+)_(?P<screen>.+)",
            r"start_recording_(?P<trial>(?:PRACTICE_)?trial_\d+)_(?P<screen>familiarity_rating_screen_\d+|subject_difficulty_screen)",
            {"pattern": r"stop_recording_", "column": "trial", "value": None},
            {"pattern": r"stop_recording_", "column": "screen", "value": None},
            {
                "pattern": r"start_recording_(?:PRACTICE_)?trial_\d+_stimulus_[^_]+_[^_]+_\d+_page_\d+",
                "column": "activity",
                "value": "reading",
            },
            {
                "pattern": r"start_recording_(?:PRACTICE_)?trial_\d+_stimulus_[^_]+_[^_]+_\d+_question_\d+",
                "column": "activity",
                "value": "question",
            },
            {
                "pattern": r"start_recording_(?:PRACTICE_)?trial_\d+_(familiarity_rating_screen_\d+|subject_difficulty_screen)",
                "column": "activity",
                "value": "rating",
            },
            {"pattern": r"stop_recording_", "column": "activity", "value": None},
            {
                "pattern": r"start_recording_PRACTICE_trial_",
                "column": "practice",
                "value": True,
            },
            {
                "pattern": r"start_recording_trial_",
                "column": "practice",
                "value": False,
            },
            {"pattern": r"stop_recording_", "column": "practice", "value": None},
        ],
        trial_columns=["trial", "stimulus", "screen"],
    )

    # Filter out data outside of trials
    # TODO: Also report time spent outside of trials
    gaze.frame = gaze.frame.filter(
        pl.col("trial").is_not_null() & pl.col("screen").is_not_null()
    )

    # Extract metadata from stimulus config and ASC file
    if config:
        stimulus_config_path = config
    else:
        print("couldn't find config")
        stimulus_config_path = stimulus_dir / "config" / "config_zh_ch_Zurich_1_2025.py"
    assert (
        stimulus_config_path.exists()
    ), f"Stimulus config not found at {stimulus_config_path}"
    stimulus_config_spec = importlib.util.spec_from_file_location(
        "stimulus_config", stimulus_config_path
    )
    print(stimulus_config_spec)
    stimulus_config = importlib.util.module_from_spec(stimulus_config_spec)
    stimulus_config_spec.loader.exec_module(stimulus_config)
    # TODO: Uncomment assertions when experiment implementation is fixed (https://www.sr-research.com/support/thread-9129.html)
    # assert metadata["resolution"][0] == stimulus_config.IMAGE_WIDTH_PX, f"Image width mismatch: {metadata['resolution'][0]} != {stimulus_config.IMAGE_WIDTH_PX}"
    # assert metadata["resolution"][1] == stimulus_config.IMAGE_HEIGHT_PX, f"Image height mismatch: {metadata['resolution'][1]} != {stimulus_config.IMAGE_HEIGHT_PX}"
    gaze.experiment = pm.Experiment(
        sampling_rate=gaze._metadata["sampling_rate"],
        screen_width_px=stimulus_config.IMAGE_WIDTH_PX,
        screen_height_px=stimulus_config.IMAGE_HEIGHT_PX,
        screen_width_cm=stimulus_config.IMAGE_SIZE_CM[0],
        screen_height_cm=stimulus_config.IMAGE_SIZE_CM[1],
        distance_cm=stimulus_config.DISTANCE_CM,
    )
    return gaze


ReportFunction = Callable[[str, Any, Union[list, tuple]], None]


def check_metadata(metadata: dict[str, Any], report: ReportFunction) -> None:
    date = f"{metadata['time']};     {metadata['day']}.{metadata['month']}.{metadata['year']}"
    report(
        "Date", date, None
    )
    num_calibrations = len(metadata["calibrations"])
    report(
        "Number of calibrations", num_calibrations, config.ACCEPTABLE_NUM_CALIBRATIONS
    )
    validation_scores_avg = [
        float(validation["validation_score_avg"])
        for validation in metadata["validations"]
    ]
    num_validations = len(metadata["validations"])
    report(
        "Number of validations", num_validations, config.ACCEPTABLE_NUM_CALIBRATIONS
    )
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
        config.TRACKED_EYE,
    )
    validation_errors = [
        validation["error"].removesuffix(" ERROR")
        for validation in metadata["validations"]
    ]
    report("Validation errors", validation_errors, config.ACCEPTABLE_VALIDATION_ERRORS)

    tracked_eye = metadata["tracked_eye"]
    report("tracked_eye",
           tracked_eye,
           config.TRACKED_EYE
           )

    validation_eye = [
        (validation["tracked_eye"][0])
        for validation in metadata["validations"]
    ]
    report(
        "Validation tracked Eyes",
        validation_eye,
        tracked_eye,
    )
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
    total_recording_duration = metadata["total_recording_duration_ms"] / 60000
    report(
        "Total recording duration",
        total_recording_duration,
        config.ACCEPTABLE_RECORDING_DURATIONS,
    )
    sampling_rate = metadata["sampling_rate"]
    report("Sampling rate",
           sampling_rate,
           config.EXPECTED_SAMPLING_RATE,
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


def plot_gaze(gaze: pm.GazeDataFrame, stimulus_dir: Path, plots_dir: Path, ) -> None:
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


def plot_main_sequence(events: pm.EventDataFrame, plots_dir: Path) -> None:
    pm.plotting.main_sequence_plot(
        events, show=False, savepath=plots_dir / "main_sequence.png"
    )

    # Filter out data outside of trials


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
    result = ""

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
        values = [f"{value:.6%}" for value in values]
    report_file.write(f"{result} {name}: {', '.join(map(str, values))}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a quality report for a MultiplEYE session"
    )
    parser.add_argument("asc_file", type=Path, help="Path to the ASC file")
    parser.add_argument(
        "stimulus_dir", type=Path, help="Path to the stimulus directory"
    )
    parser.add_argument(
        "--report-to",
        type=Path,
        help="Path to save the report",
    )
    parser.add_argument("--plots-dir", type=Path, help="Path to save the plots")
    args = parser.parse_args()
    if args.report_to is None:
        args.report_to = Path(args.asc_file.stem + "_report.txt")
    if args.plots_dir is None:
        args.plots_dir = Path(args.asc_file.stem + "_plots")

    report_file = open(args.report_to, "w", encoding="utf-8")
    args.plots_dir.mkdir(exist_ok=True)
    report = partial(report_to_file, report_file=report_file)

    logging.basicConfig(level=logging.INFO)

    logging.info("Loading data...")
    gaze = load_data(args.asc_file, args.stimulus_dir, config=None)
    logging.info("Checking gaze data...")
    check_gaze(gaze, report)
    logging.info("Preprocessing...")
    preprocess(gaze)

    # import pickle

    # with open("tmp.pkl", "wb") as f:
    #     pickle.dump(gaze, f)
    # exit()

    # with open("tmp.pkl", "rb") as f:
    #     gaze = pickle.load(f)

    logging.info("Checking event data...")
    check_events(gaze.events, report)
    logging.info("Generating gaze plots...")
    plot_gaze(gaze, args.stimulus_dir, args.plots_dir)
    logging.info("Generating main sequence plot...")
    plot_main_sequence(gaze.events, args.plots_dir)


if __name__ == "__main__":
    main()

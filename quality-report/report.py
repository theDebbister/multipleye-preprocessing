import argparse
import importlib
import logging
import math
from glob import glob
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import PIL
import polars as pl
import pymovements as pm
from matplotlib.patches import Circle

import config


def load_data(asc_file: Path, stimulus_dir: Path) -> tuple[pm.GazeDataFrame, dict[str, Any]]:
    gaze, metadata = pm.gaze.from_asc(
        asc_file,
        patterns=[
            # TODO: Update patterns (https://github.com/theDebbister/multipleye-preprocessing/issues/5#issuecomment-2230701372)
            r"start_recording_(?P<trial>(?:PRACTICE_)?trial_\d+)_(?P<screen>.+)",
            {"pattern": r"stop_recording_", "column": "trial", "value": None},
            {"pattern": r"stop_recording_", "column": "screen", "value": None},
            {
                "pattern": r"start_recording_(?:PRACTICE_)?trial_\d+_page_\d+",
                "column": "activity",
                "value": "reading",
            },
            {
                "pattern": r"start_recording_(?:PRACTICE_)?trial_\d+_question_\d+",
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
        trial_columns=["trial", "screen"],
    )

    # Map trial numbers to stimulus IDs
    # TODO: Read stimulus IDs from ASC file (https://github.com/theDebbister/multipleye-preprocessing/issues/5#issuecomment-2230701372)
    stimulus_ids = {
        "PRACTICE_trial_1": 13,
        "PRACTICE_trial_2": 7,
        "trial_1": 9,
        "trial_2": 10,
        "trial_3": 11,
        "trial_4": 6,
        "trial_5": 1,
        "trial_6": 2,
        "trial_7": 3,
        "trial_8": 4,
        "trial_9": 12,
        "trial_10": 8,
    }
    gaze.frame = gaze.frame.with_columns(
        pl.col("trial").replace(stimulus_ids).alias("stimulus")
    )

    # Filter out data outside of trials
    # TODO: Also report time spent outside of trials
    gaze.frame = gaze.frame.filter(
        pl.col("trial").is_not_null() & pl.col("screen").is_not_null()
    )

    gaze.frame = gaze.frame.with_columns(
        pl.col("trial").replace(stimulus_ids).alias("stimulus_id")
    )

    # Extract metadata from stimulus config and ASC file
    stimulus_config_spec = importlib.util.spec_from_file_location("stimulus_config", stimulus_dir / "config" / "config_hr_ch_Zurich_1_2025.py")
    stimulus_config = importlib.util.module_from_spec(stimulus_config_spec)
    stimulus_config_spec.loader.exec_module(stimulus_config)
    assert metadata["resolution"][0] == stimulus_config.IMAGE_WIDTH_PX, f"Image width mismatch: {metadata['resolution'][0]} != {stimulus_config.IMAGE_WIDTH_PX}"
    assert metadata["resolution"][1] == stimulus_config.IMAGE_HEIGHT_PX, f"Image height mismatch: {metadata['resolution'][1]} != {stimulus_config.IMAGE_HEIGHT_PX}"
    gaze.experiment = pm.Experiment(
        sampling_rate=metadata["sampling_rate"],
        screen_width_px=stimulus_config.IMAGE_WIDTH_PX,
        screen_height_px=stimulus_config.IMAGE_HEIGHT_PX,
        screen_width_cm=stimulus_config.IMAGE_SIZE_CM[0],
        screen_height_cm=stimulus_config.IMAGE_SIZE_CM[1],
        distance_cm=stimulus_config.DISTANCE_CM,
    )
    return gaze, metadata


def check_metadata(metadata: dict[str, Any]) -> None:
    pass  # TODO: Calibration/validation quality, data loss etc.


def check_gaze(gaze: pm.GazeDataFrame) -> None:
    pass  # TODO: All trials present, all pages, questions and ratings present, plausible reading times etc.


def preprocess(gaze: pm.GazeDataFrame) -> None:
    # Savitzky-Golay filter as in https://doi.org/10.3758/BRM.42.1.188
    window_length = round(gaze.experiment.sampling_rate / 1000 * 50)  # 50 ms
    if window_length % 2 == 0:  # Must be odd
        window_length += 1
    gaze.pix2deg()
    gaze.pos2vel("savitzky_golay", window_length=window_length, degree=2)
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


def check_events(events: pm.EventDataFrame) -> None:
    pass  # TODO: Fixations on/off stimulus etc.


def plot_main_sequence(events: pm.EventDataFrame, plots_dir: Path) -> None:
    pass  # TODO


def plot_gaze(gaze: pm.GazeDataFrame, stimulus_dir: Path, plots_dir: Path) -> None:
    for trial, stimulus, screen in (
        gaze.frame.select(pl.col("trial"), pl.col("stimulus"), pl.col("screen")).unique().iter_rows()
    ):
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
            stimulus_image_path, = glob(str(stimulus_dir / "stimuli_images_hr_ch_1" / f"*_id{stimulus}_{screen}_hr.png"))
        elif screen.startswith("question_"):
            question_number = int(screen.split("_")[1])
            version = 1  # TODO: Use the correct version (question/answer order) for this subject
            stimulus_image_path = sorted(glob(str(stimulus_dir / "question_images_hr_ch_1" / f"question_images_version_{version}" / f"*_id{stimulus}_question_*.png")))[question_number - 1]
        else:
            stimulus_image_path, = glob(str(stimulus_dir / f"participant_instructions_images_hr_ch_1" / f"{screen}_hr.png"))
        stimulus_image = PIL.Image.open(stimulus_image_path[0])
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


def plot_main_sequence(events: pm.EventDataFrame, plots_dir: Path) -> None:
    pm.plotting.main_sequence_plot(events, show=False, savepath=plots_dir / "main_sequence.png")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a quality report for a MultiplEYE session"
    )
    parser.add_argument("asc_file", type=Path, help="Path to the ASC file")
    parser.add_argument(
        "stimulus_dir", type=Path, help="Path to the stimulus directory"
    )
    parser.add_argument("--report-to", type=Path, help="Path to save the report")
    parser.add_argument("--plots-dir", type=Path, help="Path to save the plots")
    args = parser.parse_args()
    if args.report_to is None:
        args.report_to = Path(args.asc_file.stem + "_report.txt")
    if args.plots_dir is None:
        args.plots_dir = Path(args.asc_file.stem + "_plots")
        args.plots_dir.mkdir(exist_ok=True)

    logging.basicConfig(level=logging.INFO)

    logging.info("Loading data...")
    gaze, metadata = load_data(args.asc_file, args.stimulus_dir)
    logging.info("Checking metadata...")
    check_metadata(metadata)
    logging.info("Checking gaze data...")
    check_gaze(gaze)
    logging.info("Preprocessing...")
    preprocess(gaze)
    logging.info("Checking event data...")
    check_events(gaze.events)
    logging.info("Generating gaze plots...")
    plot_gaze(gaze, args.stimulus_dir, args.plots_dir)
    logging.info("Generating main sequence plots...")
    plot_main_sequence(gaze.events, args.plots_dir)


if __name__ == "__main__":
    main()

import argparse
import logging
from pathlib import Path
from typing import Any

import pymovements as pm

import config


def load_data(asc_file: Path) -> tuple[pm.GazeDataFrame, dict[str, Any]]:
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
    )
    # TODO: Extract sampling rate, screen size etc. from metadata and stimulus folder
    gaze.experiment = pm.Experiment(
        sampling_rate=2000,
        screen_width_px=1275,
        screen_height_px=916,
        screen_width_cm=37,
        screen_height_cm=28,
        distance_cm=60,
    )
    return gaze, metadata


def check_metadata(metadata: dict[str, Any]) -> None:
    pass  # TODO: Calibration/validation quality, data loss etc.


def check_gaze(gaze: pm.GazeDataFrame) -> None:
    pass  # TODO: All trials present, plausible reading times etc.


def preprocess(gaze: pm.GazeDataFrame) -> None:
    pass  # TODO: Fixation detection, AOI mapping etc.


def check_events(events: pm.EventDataFrame) -> None:
    pass  # TODO: Fixations on/off stimulus etc.


def main_sequence_plot(events: pm.EventDataFrame) -> None:
    pass  # TODO


def gaze_plot(events: pm.EventDataFrame) -> None:
    pass  # TODO


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a quality report for a MultiplEYE session"
    )
    parser.add_argument("asc_file", type=Path, help="Path to the ASC file")
    parser.add_argument(
        "stimulus_dir", type=Path, help="Path to the stimulus directory"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logging.info("Loading data...")
    gaze, metadata = load_data(args.asc_file)
    logging.info("Checking metadata...")
    check_metadata(metadata)
    logging.info("Checking gaze data...")
    check_gaze(gaze)
    logging.info("Preprocessing...")
    preprocess(gaze)
    logging.info("Checking event data...")
    check_events(gaze.events)


if __name__ == "__main__":
    main()

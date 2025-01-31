import argparse
import importlib
import math
from pathlib import Path

import matplotlib.pyplot as plt
import PIL
import polars as pl
import pymovements as pm
from matplotlib.patches import Circle
from stimulus import LabConfig, Stimulus, load_stimuli


def load_data(asc_file: Path, lab_config: LabConfig) -> pm.GazeDataFrame:
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
    # TODO: Uncomment assertions when experiment implementation is fixed (https://www.sr-research.com/support/thread-9129.html)
    # assert metadata["resolution"][0] == stimulus_config.IMAGE_WIDTH_PX, f"Image width mismatch: {metadata['resolution'][0]} != {stimulus_config.IMAGE_WIDTH_PX}"
    # assert metadata["resolution"][1] == stimulus_config.IMAGE_HEIGHT_PX, f"Image height mismatch: {metadata['resolution'][1]} != {stimulus_config.IMAGE_HEIGHT_PX}"
    # print(lab_config) #ersten drei sollte es aus asc herauslesen, andere aus lab config
    # gaze.experiment = pm.Experiment(
    #    sampling_rate=gaze._metadata["sampling_rate"],
    #    screen_width_px=lab_config.screen_resolution[0],
    #    screen_height_px=lab_config.screen_resolution[1],
    #    screen_width_cm=lab_config.screen_size_cm[0],
    #    screen_height_cm=lab_config.screen_size_cm[1],
    #    distance_cm=lab_config.screen_distance_cm,
    # )
    gaze.experiment.screen.width_cm = 37
    gaze.experiment.screen.height_cm = 28
    gaze.experiment.screen.distance_cm = lab_config.screen_distance_cm
    print(gaze.experiment)
    return gaze


def preprocess(
        gaze: pm.GazeDataFrame, sg_window_length: int = 50, sg_degree: int = 2
) -> None:
    # Savitzky-Golay filter as in https://doi.org/10.3758/BRM.42.1.188
    window_length = round(gaze.experiment.sampling_rate / 1000 * sg_window_length)
    if window_length % 2 == 0:  # Must be odd
        window_length += 1
    gaze.pix2deg()
    gaze.pos2vel("savitzky_golay", window_length=window_length, degree=sg_degree)
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


def plot_gaze(gaze: pm.GazeDataFrame, stimulus: Stimulus, plots_dir: Path) -> None:
    for page in stimulus.pages:
        screen_gaze = gaze.frame.filter(
            (pl.col("stimulus") == f"{stimulus.name}_{stimulus.id}")
            & (pl.col("screen") == f"page_{page.number}")
        ).select(
            pl.col("pixel").list.get(0).alias("pixel_x"),
            pl.col("pixel").list.get(1).alias("pixel_y"),
        )
        page_events = gaze.events.frame.filter(
            (pl.col("stimulus") == f"{stimulus.name}_{stimulus.id}")
            & (pl.col("screen") == f"page_{page.number}")
            & (pl.col("name") == "fixation")
        ).select(
            pl.col("duration"),
            pl.col("location").list.get(0).alias("pixel_x"),
            pl.col("location").list.get(1).alias("pixel_y"),
        )

        fig, ax = plt.subplots()
        stimulus_image = PIL.Image.open(page.image_path)
        ax.imshow(stimulus_image)

        # Plot raw gaze data
        plt.plot(
            screen_gaze["pixel_x"],
            screen_gaze["pixel_y"],
            color="black",
            linewidth=0.5,
            alpha=0.3,
        )

        # Plot fixations
        for row in page_events.iter_rows(named=True):
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
        fig.savefig(plots_dir / f"{stimulus.name}_{page.number}.png")
        plt.close(fig)

    for question in stimulus.questions:
        screen_name = (
            f"question_{int(question.id)}"  # Screen names don't have leading zeros
        )
        screen_gaze = gaze.frame.filter(
            (pl.col("stimulus") == f"{stimulus.name}_{stimulus.id}")
            & (pl.col("screen") == screen_name)
        ).select(
            pl.col("pixel").list.get(0).alias("pixel_x"),
            pl.col("pixel").list.get(1).alias("pixel_y"),
        )
        page_events = gaze.events.frame.filter(
            (pl.col("stimulus") == f"{stimulus.name}_{stimulus.id}")
            & (pl.col("screen") == screen_name)
            & (pl.col("name") == "fixation")
        ).select(
            pl.col("duration"),
            pl.col("location").list.get(0).alias("pixel_x"),
            pl.col("location").list.get(1).alias("pixel_y"),
        )

        fig, ax = plt.subplots()
        question_image = PIL.Image.open(question.image_path)
        ax.imshow(question_image)

        # Plot raw gaze data
        plt.plot(
            screen_gaze["pixel_x"],
            screen_gaze["pixel_y"],
            color="black",
            linewidth=0.5,
            alpha=0.3,
        )

        # Plot fixations
        for row in page_events.iter_rows(named=True):
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
        fig.savefig(plots_dir / f"{stimulus.name}_q{question.id}.png")
        plt.close(fig)

    for rating in stimulus.ratings:
        screen_name = (
            f"{rating.name}"  # Screen names don't have leading zeros
        )
        screen_gaze = gaze.frame.filter(
            (pl.col("trial") == f"trial_{stimulus.id}")
            & (pl.col("screen") == screen_name)
        ).select(
            pl.col("pixel").list.get(0).alias("pixel_x"),

            pl.col("pixel").list.get(1).alias("pixel_y"),
        )
        page_events = gaze.events.frame.filter(
            (pl.col("stimulus") == f"trial_{stimulus.id}")
            & (pl.col("screen") == screen_name)
            & (pl.col("name") == "fixation")
        ).select(
            pl.col("duration"),
            pl.col("location").list.get(0).alias("pixel_x"),
            pl.col("location").list.get(1).alias("pixel_y"),
        )

        fig, ax = plt.subplots()
        rating_image = PIL.Image.open(rating.image_path)
        ax.imshow(rating_image)

        # Plot raw gaze data
        plt.plot(
            screen_gaze["pixel_x"],
            screen_gaze["pixel_y"],
            color="black",
            linewidth=0.5,
            alpha=0.3,
        )

        # Plot fixations
        for row in page_events.iter_rows(named=True):
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
        fig.savefig(plots_dir / f"{stimulus.name}_{stimulus.id}_{rating.name}.png")
        plt.close(fig)


def plot_main_sequence(events: pm.EventDataFrame, plots_dir: Path) -> None:
    pm.plotting.main_sequence_plot(
        events, show=False, savepath=plots_dir / "main_sequence.png"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate plots for a MultiplEYE session"
    )
    parser.add_argument("asc_file", type=Path, help="Path to the ASC file")
    parser.add_argument(
        "stimulus_dir", type=Path, help="Path to the stimulus directory"
    )

    parser.add_argument("--plots-dir", type=Path, required=True, help="Path to save the plots")
    args = parser.parse_args()

    print("Loading data...")
    stimuli, lab_config = load_stimuli(
        args.stimulus_dir,
        "nl",
        "nl",
        1,
    )
    gaze = load_data(
        args.asc_file,
        lab_config,
    )
    print("Preprocessing...")
    preprocess(gaze)
    for stimulus in stimuli:
        print(f"Plotting {stimulus.name}...")
        plot_gaze(gaze, stimulus, args.plots_dir)

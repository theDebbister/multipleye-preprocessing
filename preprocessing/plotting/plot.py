import math
from pathlib import Path

import matplotlib.pyplot as plt
import PIL
import polars as pl
import pymovements as pm
from matplotlib.patches import Circle

from ..config import settings
from ..data_collection.stimulus import Stimulus


def plot_gaze(
    gaze: pm.Gaze,
    stimulus: Stimulus,
    plots_dir: Path,
    duration_ms_in_cm: float = 0.03,
    aoi_image: bool = False,
) -> None:
    data = gaze.clone()
    data.unnest(["pixel", "position", "velocity"])

    # pixels per centimeter on this screen
    px_per_cm = data.experiment.screen.width_px / data.experiment.screen.width_cm

    for page in stimulus.pages:
        page_samples = data.samples.filter(
            (pl.col(settings.STIMULUS_COL) == f"{stimulus.name}_{stimulus.id}")
            & (pl.col(settings.PAGE_COL) == f"{settings.PAGE_PREFIX}{page.number}")
        ).select(pl.col("pixel_x"), pl.col("pixel_y"))

        page_events = data.events.frame.filter(
            (pl.col(settings.STIMULUS_COL) == f"{stimulus.name}_{stimulus.id}")
            & (pl.col(settings.PAGE_COL) == f"{settings.PAGE_PREFIX}{page.number}")
            & (pl.col("name") == settings.FIXATION)
        ).select(
            pl.col("duration"),
            pl.col("location_x"),
            pl.col("location_y"),
        )

        fig, ax = plt.subplots()
        use_aoi = aoi_image or settings.PLOT_AOI_OVERLAY
        aoi_path = None
        if use_aoi:
            if page.aoi_image_path.exists():
                aoi_path = page.aoi_image_path
            else:
                # Fallback: try original data folder if it is not the same as output dir
                relative_aoi_path = page.aoi_image_path.relative_to(settings.OUTPUT_DIR)
                original_aoi_path = settings.DATASET_DIR / relative_aoi_path
                if original_aoi_path.exists():
                    aoi_path = original_aoi_path

        if aoi_path:
            stimulus_image = PIL.Image.open(aoi_path)
        else:
            stimulus_image = PIL.Image.open(page.image_path)
        ax.imshow(stimulus_image)

        # Plot raw gaze data
        plt.plot(
            page_samples["pixel_x"],
            page_samples["pixel_y"],
            color="black",
            linewidth=0.5,
            alpha=0.3,
        )

        # Plot fixations, make the rad scaled by the resolution
        for row in page_events.iter_rows(named=True):
            radius = math.sqrt(row["duration"]) * px_per_cm * duration_ms_in_cm

            fixation = Circle(
                (row["location_x"], row["location_y"]),
                radius,
                color="blue",
                fill=True,
                alpha=0.5,
                zorder=10,
            )
            ax.add_patch(fixation)
        ax.set_xlim((0, data.experiment.screen.width_px))
        ax.set_ylim((data.experiment.screen.height_px, 0))
        fig.savefig(plots_dir / f"{stimulus.name}_{page.number}.png")
        plt.close(fig)

    for question in stimulus.questions:
        screen_name = f"{settings.QUESTION_PREFIX}{int(question.id)}"  # Screen names don't have leading zeros
        page_samples = data.samples.filter(
            (pl.col(settings.STIMULUS_COL) == f"{stimulus.name}_{stimulus.id}")
            & (pl.col(settings.PAGE_COL) == screen_name)
        ).select(
            pl.col("pixel_x"),
            pl.col("pixel_y"),
        )
        page_events = data.events.frame.filter(
            (pl.col(settings.STIMULUS_COL) == f"{stimulus.name}_{stimulus.id}")
            & (pl.col(settings.PAGE_COL) == screen_name)
            & (pl.col("name") == settings.FIXATION)
        ).select(
            pl.col("duration"),
            pl.col("location_x"),
            pl.col("location_y"),
        )

        fig, ax = plt.subplots()
        use_aoi = aoi_image or settings.PLOT_AOI_OVERLAY
        aoi_path = None
        if use_aoi:
            if question.aoi_image_path.exists():
                aoi_path = question.aoi_image_path
            else:
                # Fallback: try original data folder if it is not the same as output dir
                relative_aoi_path = question.aoi_image_path.relative_to(
                    settings.OUTPUT_DIR
                )
                original_aoi_path = settings.DATASET_DIR / relative_aoi_path
                if original_aoi_path.exists():
                    aoi_path = original_aoi_path

        if aoi_path:
            question_image = PIL.Image.open(aoi_path)
        else:
            question_image = PIL.Image.open(question.image_path)
        ax.imshow(question_image)

        # Plot raw gaze data
        plt.plot(
            page_samples["pixel_x"],
            page_samples["pixel_y"],
            color="black",
            linewidth=0.5,
            alpha=0.3,
        )

        # Plot fixations
        for row in page_events.iter_rows(named=True):
            radius = math.sqrt(row["duration"]) * px_per_cm * duration_ms_in_cm

            fixation = Circle(
                (row["location_x"], row["location_y"]),
                radius,
                color="blue",
                fill=True,
                alpha=0.5,
                zorder=10,
            )
            ax.add_patch(fixation)
        ax.set_xlim((0, data.experiment.screen.width_px))
        ax.set_ylim((data.experiment.screen.height_px, 0))
        fig.savefig(plots_dir / f"{stimulus.name}_q{question.id}.png")
        plt.close(fig)

    for rating in stimulus.ratings:
        screen_name = f"{rating.name}"  # Screen names don't have leading zeros
        page_samples = data.samples.filter(
            (pl.col(settings.TRIAL_COL) == f"trial_{stimulus.id}")
            & (pl.col(settings.PAGE_COL) == screen_name)
        ).select(
            pl.col("pixel_x"),
            pl.col("pixel_y"),
        )
        page_events = data.events.frame.filter(
            (pl.col(settings.STIMULUS_COL) == f"trial_{stimulus.id}")
            & (pl.col(settings.PAGE_COL) == screen_name)
            & (pl.col("name") == settings.FIXATION)
        ).select(
            pl.col("duration"),
            pl.col("location_x"),
            pl.col("location_y"),
        )

        fig, ax = plt.subplots()
        rating_image = PIL.Image.open(rating.image_path)
        ax.imshow(rating_image)

        # Plot raw gaze data
        plt.plot(
            page_samples["pixel_x"],
            page_samples["pixel_y"],
            color="black",
            linewidth=0.5,
            alpha=0.3,
        )

        # Plot fixations
        for row in page_events.iter_rows(named=True):
            radius = math.sqrt(row["duration"]) * px_per_cm * duration_ms_in_cm

            fixation = Circle(
                (row["location_x"], row["location_y"]),
                radius,
                color="blue",
                fill=True,
                alpha=0.5,
                zorder=10,
            )
            ax.add_patch(fixation)
        ax.set_xlim((0, data.experiment.screen.width_px))
        ax.set_ylim((data.experiment.screen.height_px, 0))
        fig.savefig(plots_dir / f"{stimulus.name}_{stimulus.id}_{rating.name}.png")
        plt.close(fig)


def plot_main_sequence(events: pm.Events, plots_dir: Path) -> None:
    pm.plotting.main_sequence_plot(
        events,
        savepath=plots_dir / "main_sequence.png",
    )

def check_validations(gaze, messages):
    for num, validation in enumerate(gaze._metadata["validations"]):
        if validation["validation_score_avg"] < "0.305":
            continue
        else:
            print(validation["validation_score_avg"], validation["timestamp"])
            bad_val_timestamp = float(validation["timestamp"])
            found_val = False

        for cal in gaze._metadata["calibrations"]:
            cal_timestamp = float(cal["timestamp"])
            if cal_timestamp > bad_val_timestamp and cal_timestamp < bad_val_timestamp + 200000:
                # print(f"Calibration after validation at timestamp {cal['timestamp']}")
                # sanity.report_to_file(f"Calibration after validation at timestamp {cal['timestamp']}", sanity.report_file)
                index_bad_val = gaze._metadata["validations"].index(validation)
                next_validation = gaze._metadata['validations'][index_bad_val + 1]
                time_between = round((float(next_validation["timestamp"]) - bad_val_timestamp) / 1000, 3)
                print(
                    f"next validation, {time_between} seconds later with score {next_validation['validation_score_avg']}")
                sanity.report_to_file(
                    f"Calibration after validation at timestamp {cal['timestamp']}.   Next validation, {time_between} seconds later with score {next_validation['validation_score_avg']}",
                    sanity.report_file)
                found_val = True
        if not found_val:
            print(f"No calibration after validation  score {validation['validation_score_avg']}")
            sanity.report_to_file(
                f"No calibration after validation {num + 1}/{len(gaze._metadata['validations'])} at {bad_val_timestamp} with validation score {validation['validation_score_avg']}",
                sanity.report_file)


check_validations(gaze, messages)



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
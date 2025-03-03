import argparse
import math
from pathlib import Path
import pandas as pd
import PIL
import matplotlib.pyplot as plt
import polars as pl
import pymovements as pm
from matplotlib.patches import Circle
import re
from stimulus import LabConfig, Stimulus, load_stimuli
import os

def _report_to_file(message: str, report_file: Path):
    assert isinstance(report_file, Path)
    with open(report_file, "a", encoding="utf-8") as report_file:
        report_file.write(f"{message}\n")


def check_validations(gaze, messages, report_file):
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
                _report_to_file(
                    f"Calibration after validation at timestamp {cal['timestamp']}.   Next validation, {time_between} seconds later with score {next_validation['validation_score_avg']}",
                    report_file)
                found_val = True
        if not found_val:
            print(f"No calibration after validation  score {validation['validation_score_avg']}")
            _report_to_file(
                f"No calibration after validation {num + 1}/{len(gaze._metadata['validations'])} at {bad_val_timestamp} with validation score {validation['validation_score_avg']}",
                report_file)



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



def analyse_asc(asc_file: str,
                session: str ,
                initial_ts: int | None,
                lab: str,
                stimuli_trial_mapping: dict):
    start_ts = []
    stop_ts = []
    start_msg = []
    stop_msg = []
    duration_ms = []
    duration_str = []
    trials = []
    pages = []
    status = []
    stimulus_name = []

    parent_folder = Path(__file__).parent.parent
    asc_file = parent_folder / asc_file
    output_dir = asc_file.parent/ 'reading_times'
    output_dir.mkdir(exist_ok=True)
    with open(asc_file, 'r', encoding='utf8') as f:

        start_regex = re.compile(
            r'MSG\s+(?P<timestamp>\d+)\s+(?P<type>start_recording)_(?P<trial>(PRACTICE_)?trial_\d\d?)_(?P<page>.*)')
        stop_regex = re.compile(
            r'MSG\s+(?P<timestamp>\d+)\s+(?P<type>stop_recording)_(?P<trial>(PRACTICE_)?trial_\d\d?)_(?P<page>.*)')

        for l in f.readlines():
            if match := start_regex.match(l):
                start_ts.append(match.groupdict()['timestamp'])
                start_msg.append(match.groupdict()['type'])
                trials.append(match.groupdict()['trial'])

                if match.groupdict()['trial'] in stimuli_trial_mapping:
                    stimulus_name.append(stimuli_trial_mapping[match.groupdict()['trial']])

                pages.append(match.groupdict()['page'])
                status.append('reading time')
            elif match := stop_regex.match(l):
                stop_ts.append(match.groupdict()['timestamp'])
                stop_msg.append(match.groupdict()['type'])

    total_reading_duration_ms = 0
    for start, stop in zip(start_ts, stop_ts):
        time_ms = int(stop) - int(start)
        time_str = convert_to_time_str(time_ms)
        duration_ms.append(time_ms)
        duration_str.append(time_str)
        total_reading_duration_ms += time_ms

    print('Total reading duration:', convert_to_time_str(total_reading_duration_ms))

    # calcualte duration between pages
    temp_stop_ts = stop_ts.copy()
    temp_stop_ts.insert(0, initial_ts)
    temp_stop_ts = temp_stop_ts[:-1]

    total_set_up_time_ms = 0
    for stop, start, page, trial in zip(temp_stop_ts, start_ts, pages, trials):
        time_ms = int(start) - int(stop)
        time_str = convert_to_time_str(time_ms)
        duration_ms.append(time_ms)
        duration_str.append(time_str)
        start_msg.append('time inbetween')
        stop_msg.append('time inbetween')
        start_ts.append(stop)
        stop_ts.append(start)
        trials.append(trial)
        total_set_up_time_ms += time_ms

        if trial in stimuli_trial_mapping:
            stimulus_name.append(stimuli_trial_mapping[trial])

        pages.append(page)
        status.append('time before pages and breaks')

    print('Total set up and break time:', convert_to_time_str(total_set_up_time_ms))

    df = pd.DataFrame({
        'start_ts': start_ts,
        'stop_ts': stop_ts,
        'trial': trials,
        'stimulus': stimulus_name,
        'page': pages,
        'type': status,
        'duration_ms': duration_ms,
        'duration-hh:mm:ss': duration_str
    })

    df.to_csv(output_dir/ f'times_per_page_pilot_{session}.tsv', sep='\t', index=False,)

    sum_df = df[['stimulus', 'trial', 'type', 'duration_ms']].dropna()
    sum_df['duration_ms'] = sum_df['duration_ms'].astype(float)
    sum_df = sum_df.groupby(by=['stimulus', 'trial', 'type']).sum().reset_index()
    duration = sum_df['duration_ms'].apply(lambda x: convert_to_time_str(x))
    sum_df['duration-hh:mm:ss'] = duration
    sum_df.to_csv(output_dir/ f'times_per_page_pilot_{session}.tsv', index=False, sep='\t')

    print('Total exp time: ', convert_to_time_str(total_reading_duration_ms + total_set_up_time_ms))
    print('\n')

    # write total times to csv
    total_times = pd.DataFrame({
        'pilot': session,
        'lab': lab,
        'language': 'en',
        'total_trials': [len(sum_df) / 2],
        'total_pages': [len(df) / 2],
        'total_reading_time': [convert_to_time_str(total_reading_duration_ms)],
        'total_non-reading_time': [convert_to_time_str(total_set_up_time_ms)],
        'total_exp_time': [convert_to_time_str(total_reading_duration_ms + total_set_up_time_ms)]
    })
    if os.path.exists(output_dir/ f'total_times.tsv'):
        temp_total_times = pd.read_csv('reading_times/total_times.tsv', sep='\t')
        total_times = pd.concat([temp_total_times, total_times], ignore_index=True)

    total_times.to_csv('reading_times/total_times.tsv', sep='\t', index=False)

    total_times.to_excel('reading_times/total_times.xlsx', index=False)
    sum_df.to_excel(f'reading_times/times_per_trial_pilot_{session}.xlsx', index=False)
    df.to_excel(f'reading_times/times_per_page_pilot_{session}.xlsx', index=False)


def convert_to_time_str(duration_ms: float) -> str:
    seconds = int(duration_ms / 1000) % 60
    minutes = int(duration_ms / (1000 * 60)) % 60
    hours = int(duration_ms / (1000 * 60 * 60)) % 24

    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


if __name__ == '__main__':

    analyse_asc(
        "C:\\Users\saphi\PycharmProjects\multipleye-preprocessing\data\MultiplEYE_ET_EE_Tartu_1_2025\eye-tracking-sessions\core_dataset\\006_ET_EE_1_ET1\\006etee1.asc",
        session="006",
        lab='et',
        initial_ts=14556585,
        stimuli_trial_mapping={
            'PRACTICE_trial_1': 'Enc_WikiMoon',
            'PRACTICE_trial_2': 'Lit_NorthWind',
            'trial_1': 'Lit_Solaris',
            'trial_2': 'Lit_MagicMountain',
            'trial_3': 'Arg_PISACowsMilk',
            'trial_4': 'Lit_BrokenApril',
            'trial_5': 'PopSci_Caveman',
            'trial_6': 'Arg_PISARapaNui',
            'trial_7': 'Ins_HumanRights',
            'trial_8': 'PopSci_MultiplEYE',
            'trial_9': 'Lit_Alchemist',
            'trial_10': 'Ins_LearningMobility',
        }
    )

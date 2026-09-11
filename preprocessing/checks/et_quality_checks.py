from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

import polars as pl

from ..config import settings
from ..data_collection.stimulus import Stimulus
from ..utils import _report_to_file

ReportFunction = Callable[[str, Any, Any], None]


def report_to_file_metadata(
    name: str,
    values: Any,
    acceptable_values: Any,
    report_file: TextIO,
    percentage: bool = False,
) -> None:
    """
    Check if the metadata values are in the acceptable values or within the acceptable range and write a report to file.
    :param name: Name of the metadata value
    :param values: Values of the metadata to check
    :param acceptable_values: Acceptable values or range of acceptable values for the metadata value
    :param report_file: Opened file to write the report to
    :param percentage: If True, the values are converted to percentage
    :return:
    """
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
        values = [f"{value:.3%}" for value in values]
    report_file.write(f"- {result} **{name}**: {', '.join(map(str, values))}\n")


def check_comprehension_question_answers(
    logfile: pl.DataFrame,
    stimuli: Stimulus | list[Stimulus],
    report_file: Path | None = None,
):
    """compute the number of correct answers for each participant
    params: logfile as polars
    returns nothing"""
    overall_correct_answers = 0
    overall_answers = 0
    for stimulus in stimuli:
        # get the trial number for the stimulus as rating screens don't have an entry in the stimulus_number column
        trial_id = logfile.filter(pl.col("stimulus_number") == f"{stimulus.id}").item(
            0, "trial_number"
        )
        stimulus_frame = logfile.filter(
            (pl.col("trial_number") == f"{trial_id}")
            & (pl.col("stimulus_number") == f"{stimulus.id}")
        )
        answers = stimulus_frame.filter(pl.col("message").str.contains("FINAL ANSWER"))
        correct_answers = stimulus_frame.filter(pl.col("message").str.contains("True"))
        overall_correct_answers += len(correct_answers)
        overall_answers += len(answers)
        _report_to_file(
            f"- Correct answers for **{stimulus.name}**: {len(correct_answers)} out of {len(answers)} answers",
            report_file,
        )

    if overall_answers != 0:
        _report_to_file(
            f"\n**Overall correct answers**: {overall_correct_answers} out of {overall_answers} answers ({overall_correct_answers / overall_answers:.2f})",
            report_file,
        )
    else:
        _report_to_file(
            f"\n**Overall correct answers**: {overall_correct_answers} out of {overall_answers} answers",
            report_file,
        )


def check_validation_requirements(
    validations: pl.DataFrame, calibrations: pl.DataFrame, report_file, stimulus_times
):
    # sort validations and calibrations by timestamp, merge into one list
    vals = validations.sort("time").to_dicts()
    cals = calibrations.sort("time").to_dicts()

    # prepare lists

    mes = {
        "val_cal_during_stimulus": [],
        "good_vals": [],
        "no_cal_after_bad_val": [],
        "moderate_vals": [],
        "bad_vals": [],
        "others": [],
        "start_after_bad_val": [],
        "no_val_before_stimulus": [],
        "start_after_moderate_val": [],
        "necessary_cals": [],
        "final_vals": [],
        "final_cals": [],
        "no_val": [],
    }

    merged = sorted(vals + cals + stimulus_times, key=lambda x: float(x["time"]))
    bad_tstamp = None
    bad_val = False
    val = False
    cal = False
    moderate_val = False
    mod_tstamp = None
    in_stimulus = False
    val_count = 0
    good_vals = 0
    moderate_vls = 0
    cal_count = 0
    val_performed = False
    score = -1
    num_stimuli = len(stimulus_times)
    real_num_stimuli = 0

    for m in merged:
        val = False
        if "accuracy_avg" in m:
            val_count += 1
            val = True
            cal = False

            if bad_val:
                time_since_last_val = round((float(m["time"]) - bad_tstamp) / 1000, 3)
                # if there are more than 2 minutes between bad val and next val, we consider that a calibration should have happened
                if time_since_last_val > 120:
                    mes["no_cal_after_bad_val"].append(
                        f"⚠️ No calibration at {m['time']} after BAD validation at timestamp {bad_tstamp}"
                    )
                    bad_val = False
            score = float(m["accuracy_avg"])

            if real_num_stimuli == num_stimuli:
                mes["final_vals"].append(
                    f"Validation after last stimulus: {m['time']}, score: {score}"
                )
                _report_to_file(
                    f"- ⚠️ Validation after last stimulus: {m['time']}, score: {score}",
                    report_file,
                )

            elif score < settings.SINGLE_VALIDATION_GOOD_MAX:
                _report_to_file(
                    f"- ✅ Good validation at {m['time']} with score {m['accuracy_avg']}",
                    report_file,
                )
                bad_val = False
                moderate_val = False
                val_performed = True
                good_vals += 1
            elif (
                settings.SINGLE_VALIDATION_MODERATE_MAX
                > score
                >= settings.SINGLE_VALIDATION_GOOD_MAX
            ):
                mes["moderate_vals"].append(
                    f"⚠️ Moderate validation at {m['time']} with score {m['accuracy_avg']}"
                )
                moderate_val = True
                bad_val = False
                moderate_vls += 1
                mod_tstamp = int(m["time"])
            elif score >= settings.SINGLE_VALIDATION_MODERATE_MAX:
                mes["bad_vals"].append(
                    f"❌ BAD Validation at {m['time']} with score {m['accuracy_avg']}"
                )
                bad_val = True
                moderate_val = False
                bad_tstamp = int(m["time"])
            if in_stimulus:
                mes["val_cal_during_stimulus"].append(
                    f"⚠️ Validation during stimulus at {m['time']} with score {m['accuracy_avg']}"
                )

        elif "message" in m:
            if "start" in m["message"]:
                real_num_stimuli += 1
                in_stimulus = True
                _report_to_file(f"- {m['message']} at {m['time']}", report_file)
                if cal:
                    mes["no_val_before_stimulus"].append(
                        f"⚠️ {m['message']} without prior validation at {m['time']}. Only calibration at {m['time']}"
                    )
                    cal = False
                elif bad_val:
                    mes["start_after_bad_val"].append(
                        f"❌ {m['message']} directly after bad validation at {bad_tstamp} with score {score}!"
                    )
                    bad_val = False
                elif moderate_val:
                    mes["start_after_moderate_val"].append(
                        f"⚠️ {m['message']} directly after moderate validation at {mod_tstamp}  with score {score}!"
                    )
                    moderate_val = False
                elif val_performed:
                    val_performed = False
                elif not val_performed:
                    mes["no_val_before_stimulus"].append(
                        f"⚠️ {m['message']} without prior validation at {m['time']}"
                    )

            if "end" in m["message"]:
                real_num_stimuli += 1
                in_stimulus = False
                _report_to_file(f"- {m['message']} at {m['time']}", report_file)

        else:
            cal_count += 1
            cal = True
            if bad_val:
                bad_val = False
                time_between = round((float(m["time"]) - bad_tstamp) / 1000, 3)
                mes["necessary_cals"].append(
                    f"✅ Calibration at {m['time']} {time_between} seconds after BAD validation"
                )
            if in_stimulus:
                mes["val_cal_during_stimulus"].append(
                    f"⚠️ Calibration during stimulus at {m['time']}"
                )

            if real_num_stimuli == num_stimuli:
                mes["final_cals"].append(
                    f"Calibration after last stimulus: {m['time']}"
                )
                _report_to_file(
                    f"- ❌ Calibration after last stimulus: {m['time']}", report_file
                )

            score = -1

    _report_to_file(
        "\n## Validation/Calibration Summary",
        report_file,
    )
    _report_to_file(f"- Good validations: {good_vals}/{val_count}", report_file)
    _report_to_file(f"- Moderate validations: {moderate_vls}/{val_count}", report_file)
    _report_to_file(
        f"- Bad validations: {len(mes['bad_vals'])}/{val_count}", report_file
    )

    _report_to_file("\n**Stimulus start after bad/moderate validation**", report_file)
    for start in mes["start_after_bad_val"]:
        _report_to_file(f"- {start}", report_file)
    for start in mes["start_after_moderate_val"]:
        _report_to_file(f"- {start}", report_file)

    _report_to_file(
        "\n**Missing calibrations after bad/moderate validations**", report_file
    )
    for start in mes["no_cal_after_bad_val"]:
        _report_to_file(f"- {start}", report_file)

    _report_to_file("\n**Necessary calibrations after bad validations**", report_file)
    for cal in mes["necessary_cals"]:
        _report_to_file(f"- {cal}", report_file)

    _report_to_file("\n**No validation before stimulus start**", report_file)
    for start in mes["no_val_before_stimulus"]:
        _report_to_file(f"- {start}", report_file)

    _report_to_file(
        "\n**Validation/calibration during stimulus presentation**", report_file
    )
    for vc in mes["val_cal_during_stimulus"]:
        _report_to_file(f"- {vc}", report_file)

    _report_to_file("\n**Bad validations**", report_file)
    for bad in mes["bad_vals"]:
        _report_to_file(f"- {bad}", report_file)

    _report_to_file("\n**Moderate validations**", report_file)
    for moderate in mes["moderate_vals"]:
        _report_to_file(f"- {moderate}", report_file)

    _report_to_file(
        "\n" + ("- ✅ Final validation" if val else "- ❌ No final validation!"),
        report_file,
    )


def check_metadata(
    metadata: dict[str, Any],
    calibrations: pl.DataFrame,
    validations: pl.DataFrame,
    report: ReportFunction,
    total_data_loss_ratio: float | None = None,
    blink_loss_ratio: float | None = None,
) -> None:
    """
    Check the metadata of the gaze data and write a report to file.
    :param metadata: Metadata report.
    :param calibrations: Session calibrations as DataFrame from the pymovements metadata.
    :param validations: Session validations as DataFrame from the pymovements metadata.
    :param report: Function to write the report to file.
    :return:
    """
    date = f"{metadata['time']};     {metadata['day']}.{metadata['month']}.{metadata['year']}"
    report("Date", date, None)

    num_calibrations = len(calibrations)
    report(
        "Number of calibrations",
        num_calibrations,
        settings.ACCEPTABLE_NUM_CALIBRATIONS,
    )

    validation_scores_avg = validations["accuracy_avg"].cast(pl.Float32).to_list()

    num_validations = len(validations)
    report("Number of validations", num_validations, settings.ACCEPTABLE_NUM_VALIDATION)
    report(
        "AVG validation scores",
        [round(score, 4) for score in validation_scores_avg],
        settings.ACCEPTABLE_AVG_VALIDATION_SCORES,
    )
    validation_scores_max = validations["accuracy_max"].cast(pl.Float32).to_list()
    report(
        "MAX validation scores",
        [round(score, 4) for score in validation_scores_max],
        settings.TRACKED_EYE,
    )

    # this has been excluded in pm, but as we have the accuracy values this is enough...
    # validation_errors = validations["error"].to_list()
    # report("Validation errors", validation_errors, config.ACCEPTABLE_VALIDATION_ERRORS)

    tracked_eye = metadata["tracked_eye"]
    report("tracked_eye", tracked_eye, settings.TRACKED_EYE)

    validation_eye = validations["eye"].to_list()

    report(
        "Validation tracked Eyes",
        validation_eye,
        tracked_eye,
    )
    data_loss = (
        total_data_loss_ratio
        if total_data_loss_ratio is not None
        else metadata.get("data_loss_ratio")
    )
    if data_loss is not None:
        report(
            "Total data loss ratio",
            round(data_loss, 3),
            settings.ACCEPTABLE_DATA_LOSS_RATIOS,
            percentage=True,
        )
    blink_loss = (
        blink_loss_ratio
        if blink_loss_ratio is not None
        else metadata.get("data_loss_ratio_blinks")
    )
    if blink_loss is not None:
        report(
            "Blink loss ratio",
            round(blink_loss, 3),
            settings.ACCEPTABLE_DATA_LOSS_RATIOS,
            percentage=True,
        )
    total_recording_duration = metadata["total_recording_duration_ms"] / 60000
    report(
        "Total recording duration",
        round(total_recording_duration, 2),
        settings.ACCEPTABLE_RECORDING_DURATIONS,
    )
    sampling_rate = metadata["sampling_rate"]
    report(
        "Sampling rate",
        sampling_rate,
        settings.EXPECTED_SAMPLING_RATE_HZ,
    )

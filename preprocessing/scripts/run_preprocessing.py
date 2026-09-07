import contextlib
import os
from argparse import ArgumentParser

import polars as pl
import pymovements as pm
from tqdm import tqdm

import preprocessing
from preprocessing import settings
from preprocessing.checks.quality_thresholds import write_quality_thresholds
from preprocessing.scripts.prepare_language_folder import prepare_language_folder

from ..utils.logging import get_logger


def run_preprocessing(config_path: str | None = None):
    settings.load(config_path)
    logger = get_logger()

    # Check for configuration issues after loading
    status_msg = settings.get_config_status_message()
    if status_msg:
        from ..config import package_logger

        package_logger.error(status_msg)
        return

    data_collection_name = settings.DATA_COLLECTION_NAME

    logger.info(
        f"Running MultiplEYE preprocessing for data collection: {data_collection_name}"
    )

    prepare_language_folder(data_collection_name)

    data_folder_path = settings.DATASET_DIR

    if not os.path.exists(data_folder_path):
        raise FileNotFoundError(
            f"Data folder {data_folder_path} does not exist. Please make sure to download the data and place it in the correct folder. "
            f"And check if you have filled in the correct data collection name in the settings."
        )

    if settings.EXPERIMENT_TYPE == "MultiplEYE":
        data_collection = preprocessing.data_collection.MultipleyeDataCollection.create_from_data_folder(
            data_folder_path,
            include_pilots=settings.INCLUDE_PILOTS,
            excluded_sessions=settings.EXCLUDE_SESSIONS,
            included_sessions=settings.INCLUDE_SESSIONS,
            output_dir=settings.OUTPUT_DIR,
        )

    elif settings.EXPERIMENT_TYPE == "MeRID":
        data_collection = (
            preprocessing.data_collection.MeridDataCollection.create_from_data_folder(
                data_folder_path,
                include_pilots=settings.INCLUDE_PILOTS,
                excluded_sessions=settings.EXCLUDE_SESSIONS,
                included_sessions=settings.INCLUDE_SESSIONS,
                output_dir=settings.OUTPUT_DIR,
            )
        )

    else:
        raise ValueError(
            f"Invalid experiment type: {settings.EXPERIMENT_TYPE}. Supported types: [MultiplEYE, MeRID]"
        )

    write_quality_thresholds(settings.OUTPUT_DIR)

    if settings.RUN_PREFLIGHT_CHECK:
        from ..checks.preflight import run_preflight_check

        run_preflight_check(data_collection)

    data_collection.convert_edf_to_asc()
    data_collection.prepare_session_level_information()

    # for sess in multipleye:
    #     if sess.stimuli == 'unknown':
    #         print(sess.session_identifier)

    sessions = [s for s in data_collection]

    for sess in (pbar := tqdm(sessions)):
        pbar.set_description(f"Preprocessing session {sess.sid}:")

        asc = sess.asc_path

        # Flag to be changed, when recalculation was forced for a session previously, e.g. because of incomplete files
        # Forces recalculation for all subsequent stages
        recalculated_upstream = False

        # check whether the raw data was calculated before and whether it is complete
        raw_data_folder = sess.sid.raw_data_dir
        num_expected_files = len(sess.completed_stimuli_ids)
        metadata_exists = (sess.sid.metadata_dir / "gaze_metadata.json").exists()
        files = list(raw_data_folder.glob("*.csv"))
        num_files = len(files)

        if num_files > 0:
            # Check if a previous version of this pipeline saved the raw data without velocity and position information
            test_file = files[0]
            preprocessed = "position_x" in pl.read_csv(test_file, n_rows=0).columns
        else:
            preprocessed = False

        if (
            num_expected_files == num_files
            and raw_data_folder.exists()
            and preprocessed
            and metadata_exists
            and not settings.RECALCULATE
        ):
            # Loading previously extracted raw data
            pbar.set_description(f"Loading samples {sess.sid}:")
            gaze = preprocessing.load_trial_level_raw_data(
                sess.sid,
                trial_columns=settings.TRIAL_COLS,
                load_metadata=True,
            )

            if gaze is not None and gaze.messages is None and asc.exists():
                tmp = pm.gaze.from_asc(
                    asc, patterns=[], messages=settings.EXPERIMENT_MSG_PATTERNS
                )
                gaze.messages = tmp.messages

        else:
            # Extract raw data from asc file
            recalculated_upstream = True
            pbar.set_description(f"Extracting samples {sess.sid}:")
            gaze = preprocessing.load_gaze_data(
                asc_file=asc,
                lab_config=sess.lab_config,
                sid=sess.sid,
                trial_cols=settings.TRIAL_COLS,
                messages=settings.EXPERIMENT_MSG_PATTERNS,
            )

            # filter gaze to only contain data of completed stimuli
            gaze.samples = gaze.samples.filter(
                pl.col("stimulus").is_in(sess.completed_stimuli_names)
            )

            # Compute total data loss via pymovements.measure.data_loss().
            # Session-level (duration-weighted), not per-trial mean.
            sr = gaze.experiment.sampling_rate or float(gaze._metadata["sampling_rate"])
            gaze._measure_total_data_loss_ratio = gaze.samples.select(
                pm.measure.data_loss("pixel", sampling_rate=sr, unit="ratio")
            ).item()

            # Per-page data loss: group by trial_columns (which include "page"),
            # so each row is one page. The ratio is time-weighted *within* the page
            # (lost samples / expected samples over the page's time span).
            gaze._per_page_data_loss = gaze.samples.group_by(gaze.trial_columns).agg(
                pm.measure.data_loss("pixel", sampling_rate=sr, unit="ratio")
            )
            # Per-trial data loss: group by trial only (not page). Each trial gets one
            # independent ratio (time-weighted within the trial). Trials are NOT
            # weighted by their length against each other -- that is handled by the
            # plain, equal-weighted mean across trial rows in the sanity report.
            gaze._per_trial_data_loss = gaze.samples.group_by(
                ["trial", "stimulus"]
            ).agg(pm.measure.data_loss("pixel", sampling_rate=sr, unit="ratio"))

            preprocessing.save_session_metadata(sess.sid, gaze)

            # preprocess gaze data
            pbar.set_description(f"Preprocessing samples {sess.sid}:")
            preprocessing.preprocess_gaze(
                gaze,
            )

            # save raw data
            preprocessing.save_raw_data(sess.sid, gaze)

        sess.pm_gaze_metadata = gaze._metadata
        sess.calibrations = gaze.calibrations
        sess.validations = gaze.validations
        sess.messages = gaze.messages

        # Store measure-based data loss values (computed above and in load_gaze_data).
        sess._measure_total_data_loss_ratio = getattr(
            gaze,
            "_measure_total_data_loss_ratio",
            None,
        )
        sess._measure_blink_loss_ratio = getattr(
            gaze,
            "_measure_blink_loss_ratio",
            None,
        )
        sess._per_page_data_loss = getattr(gaze, "_per_page_data_loss", None)
        sess._per_page_blink_loss = getattr(gaze, "_per_page_blink_loss", None)
        sess._per_trial_data_loss = getattr(gaze, "_per_trial_data_loss", None)
        sess._per_trial_blink_loss = getattr(gaze, "_per_trial_blink_loss", None)

        # create or load fixation data
        fixation_data_folder = sess.sid.fixations_dir
        saccade_data_folder = sess.sid.saccades_dir

        if gaze is None:
            logger.warning(
                f"Gaze data missing for {sess.sid}. Skipping event detection."
            )
        else:
            # Count previously outputted fixation files
            num_expected_files = len(sess.completed_stimuli_ids)
            num_files = len(list(fixation_data_folder.glob("*.csv")))

            if settings.RUN_FIXATION_DETECTION:
                if (
                    num_expected_files == num_files
                    and fixation_data_folder.exists()
                    and not settings.RECALCULATE
                    and not recalculated_upstream
                ):
                    # Loading events if all fixation files exist and the recalculate flag is not active
                    pbar.set_description(f"Loading fixations {sess.sid}:")
                    gaze = preprocessing.load_trial_level_events_data(
                        gaze,
                        sess.sid,
                        event_type=settings.FIXATION,
                        file_pattern=None,
                    )

                else:
                    recalculated_upstream = True
                    # If files were not complete or recalculation is active we run fixation detection
                    pbar.set_description(f"Detecting fixations {sess.sid}:")

                    preprocessing.detect_fixations(gaze)
                    preprocessing.save_events_data(
                        settings.FIXATION,
                        sess.sid,
                        "trial",
                        ["trial", "stimulus"],
                        ["onset", "duration", "location_x", "location_y", "page"],
                        gaze,
                    )

                    # Unnest event columns (e.g. location struct -> location_x/location_y)
                    # so downstream code doesn't need to handle struct columns.
                    if gaze is not None and gaze.events is not None:
                        with contextlib.suppress(Warning):
                            gaze.events.unnest()

            else:
                # Fixation detection is disabled
                if num_expected_files == num_files:
                    logger.info(f"Using existing fixation data for {sess.sid}")
                    gaze = preprocessing.load_trial_level_events_data(
                        gaze,
                        sess.sid,
                        event_type=settings.FIXATION,
                        file_pattern=None,
                    )
                else:
                    # Fixation detection is disabled, but previous outputs are also not available
                    logger.info(f"Skipping fixation detection for {sess.sid}")

            # Count previously outputted saccade files
            num_files = len(list(saccade_data_folder.glob("*.csv")))

            if settings.RUN_SACCADE_DETECTION:
                if (
                    num_expected_files == num_files
                    and saccade_data_folder.exists()
                    and not settings.RECALCULATE
                    and not recalculated_upstream
                ):
                    # Loading events if all saccade files exist and the recalculate flag is not active
                    pbar.set_description(f"Loading saccades {sess.sid}:")

                    gaze = preprocessing.load_trial_level_events_data(
                        gaze,
                        sess.sid,
                        event_type=settings.SACCADE,
                        file_pattern=None,
                    )

                else:
                    recalculated_upstream = True
                    # If files were not complete or recalculation is active we run saccade detection
                    pbar.set_description(f"Detecting saccades {sess.sid}:")

                    if settings.RUN_SACCADE_DETECTION:
                        preprocessing.detect_saccades(gaze)

                        preprocessing.save_events_data(
                            settings.SACCADE,
                            sess.sid,
                            "trial",
                            ["trial", "stimulus"],
                            [
                                "onset",
                                "duration",
                                "amplitude",
                                "peak_velocity",
                                "dispersion",
                                "page",
                            ],
                            gaze,
                        )

                    # Unnest event columns (e.g. location struct -> location_x/location_y)
                    # so downstream code doesn't need to handle struct columns.
                    if gaze is not None and gaze.events is not None:
                        with contextlib.suppress(Warning):
                            gaze.events.unnest()

            else:
                # Saccade detection is disabled
                if num_expected_files == num_files:
                    logger.info(f"Using existing saccade data for {sess.sid}")
                    gaze = preprocessing.load_trial_level_events_data(
                        gaze,
                        sess.sid,
                        event_type=settings.SACCADE,
                        file_pattern=None,
                    )
                else:
                    # Saccade detection is disabled, but previous outputs are also not available
                    logger.info(f"Skipping saccade detection for {sess.sid}")

        # map to AOIs and create scanpaths
        if (
            gaze is None
            or gaze.events is None
            or gaze.events.frame.filter(pl.col("name") == settings.FIXATION).is_empty()
        ):
            # Fixation data is not availablec, either due to skipping or other reasons
            logger.warning(
                f"Fixations missing for {sess.sid}. Skipping AOI mapping/scanpaths."
            )
        else:
            # Check whether scanpaths have been saved before for this session
            num_expected_files = len(sess.completed_stimuli_ids)

            scanpaths_data_folder = sess.sid.scanpaths_dir
            num_files = len(list(scanpaths_data_folder.glob("*.csv")))

            if (
                num_files == num_expected_files
                and scanpaths_data_folder.exists()
                and not settings.RECALCULATE
                and not recalculated_upstream
            ):
                gaze = preprocessing.load_scanpaths(gaze, sess.sid)

            else:
                recalculated_upstream = True
                preprocessing.map_fixations_to_aois(
                    gaze,
                    sess.stimuli,
                )
                preprocessing.save_scanpaths(sess.sid, gaze)

                preprocessing.save_session_metadata(sess.sid, gaze)

        rm_folder = sess.sid.reading_measures_dir

        if settings.RUN_READING_MEASURES:
            if (
                gaze is None
                or gaze.events is None
                or gaze.events.frame.filter(
                    pl.col("name") == settings.FIXATION
                ).is_empty()
                or settings.WORD_IDX_COL not in gaze.events.columns
            ):
                logger.warning(
                    f"Gaze/Event data missing or not mapped for {sess.sid}. Skipping reading measures."
                )

            num_expected_files = len(sess.completed_stimuli_ids)
            num_files = len(list(rm_folder.glob("*.csv")))

            if (
                num_files == num_expected_files
                and rm_folder.exists()
                and not settings.RECALCULATE
                and not recalculated_upstream
            ):
                # check if the folder contains the expected number of files, if not, we will recalculate

                pbar.set_description(f"Loading reading measures {sess.sid}:")
                reading_measures = preprocessing.load_reading_measures(sess.sid)

                data_collection[sess.session_identifier].reading_measures = True

            else:
                recalculated_upstream = True
                pbar.set_description(f"Calculating reading measures {sess.sid}:")
                reading_measures = preprocessing.calculate_reading_measures(
                    gaze,
                    sess.stimuli,
                )

                preprocessing.save_reading_measures(sess.sid, reading_measures)
                data_collection[sess.session_identifier].reading_measures = True
        else:
            pbar.set_description(f"Skipping reading measures {sess.sid}:")

        # === COMPREHENSION QUESTION ANSWERS ===
        if settings.RUN_COMPREHENSION_ANSWERS:
            answers_csv = sess.sid.answers_dir / f"{sess.sid}_answers.csv"

            if (
                answers_csv.exists()
                and not settings.RECALCULATE
                and not recalculated_upstream
            ):
                pbar.set_description(f"Loading comprehension answers {sess.sid}")
                sess.answers = True
            else:
                recalculated_upstream = True
                pbar.set_description(f"Collecting comprehension answers {sess.sid}")
                question_order_csv = (
                    sess.session_folder_path
                    / "logfiles"
                    / "question_order_versions.csv"
                )
                if question_order_csv.exists():
                    parsed_answers = None
                    source = "unknown"

                    # 1. Primary source: ASC messages (prefer if gaze exists)
                    if (
                        gaze is not None
                        and gaze.messages is not None
                        and not gaze.messages.is_empty()
                    ):
                        parsed_answers = preprocessing.parse_answers_from_messages(
                            gaze.messages
                        )
                        if parsed_answers is not None and not parsed_answers.is_empty():
                            source = "asc"

                    # 2. Fallback source: experiment logfile
                    if parsed_answers is None or parsed_answers.is_empty():
                        # We only fallback if we really didn't find anything in ASC
                        # OR if extraction was disabled and raw data was missing (gaze is None)
                        parsed_answers = preprocessing.parse_answers_from_logfile(
                            sess.logfile, sess.stimuli_trial_mapping
                        )
                        if not parsed_answers.is_empty():
                            source = "logfile"

                    preprocessing.collect_session_answers(
                        question_order_csv=question_order_csv,
                        stimuli_trial_map=sess.stimuli_trial_mapping,
                        stimuli=sess.stimuli,
                        parsed_answers=parsed_answers,
                        out_path=answers_csv,
                        source=source,
                        completed_stimuli_ids=sess.completed_stimuli_ids,
                    )
                    sess.answers = True
        else:
            pbar.set_description(f"Skipping comprehension answers {sess.sid}:")

        if settings.RUN_SANITY_CHECKS:
            if gaze is None:
                logger.warning(
                    f"Gaze data missing for {sess.sid}. Skipping sanity report."
                )
            else:
                pbar.set_description(f"Creating sanity check report {sess.sid}")
                data_collection.create_sanity_check_report(
                    gaze,
                    sess.session_identifier,
                    plotting=True,
                    recalculate=(settings.RECALCULATE or recalculated_upstream),
                    output_dir=settings.OUTPUT_DIR,
                )
        else:
            pbar.set_description(f"Skipping sanity checks {sess.sid}:")

        data_collection.create_session_overview(
            sess.session_identifier, path=settings.OUTPUT_DIR
        )

    data_collection.create_dataset_overview(path=settings.OUTPUT_DIR)
    data_collection.parse_participant_data(settings.OUTPUT_DIR / "participant_data.csv")

    if settings.RUN_PSYCHOMETRIC_TESTS:
        logger.info("Processing psychometric tests...")
        from ..psychometric_tests.preprocess_psychometric_tests import (
            preprocess_all_sessions,
        )

        preprocess_all_sessions(settings.PSYCHOMETRIC_TESTS_DIR)


def main():
    """Run MultiplEYE preprocessing with the config file as argument."""
    parser = ArgumentParser(description="Run MultiplEYE preprocessing.")

    parser.add_argument(
        "--config_path",
        type=str,
        default=None,
        help="Path to the preprocessing configuration YAML file.",
    )
    args = parser.parse_args()
    run_preprocessing(args.config_path)


if __name__ == "__main__":
    main()

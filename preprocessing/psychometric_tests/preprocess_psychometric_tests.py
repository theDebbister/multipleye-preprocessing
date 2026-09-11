"""Utilities to preprocess psychometric test outputs into simple summary metrics.

This module provides small helpers to load raw CSV exports for several common
psychometric tasks and compute concise summaries such as mean reaction time and
accuracy, optionally grouped by condition where applicable.

Covered tasks:
- Lewandowsky WMC battery
- Rapid Automatised Naming (RAN)
- Stroop
- Flanker
- PLAB (Pimsleur Language Aptitude Battery)
- WikiVocab (LexTALE)

Background and task descriptions:
https://github.com/MultiplEYE-COST/MultiplEYE-psychometric-tests#readme
"""

from logging import Logger
from math import nan
from pathlib import Path

import pandas as pd
import yaml
from pandas import DataFrame, read_csv

from ..config import settings
from ..models.sid import Sid
from ..utils import validate_psychometric_data
from ..utils.data_path_utils import find_psychometric_config_files
from ..utils.logging import get_logger


def preprocess_all_sessions(test_session_folder: Path | None = None) -> Path:
    """
    Preprocess all psychometric test sessions and write a consolidated results table.

    This function performs the following steps:
    1. Validates the psychometric data structure.
    2. Iterates through each session folder.
    3. Extracts session information (PID, session part, postfix).
    4. Preprocesses each individual test (LWMC, RAN, Stroop, Flanker, WikiVocab, PLAB).
    5. Aggregates all results (summary and detailed metrics) into a wide row per session.
    6. Writes a consolidated per-session results CSV and a per-participant merged CSV.

    Two output files are generated in ``OUTPUT_DIR / PSYCHOMETRIC_TESTS_FOLDER``:

    - ``psychometric_results_{DCN}.csv``: one row per session with all available
      metrics (per-condition RT/accuracy/item counts, LWMC scores and timings,
      WikiVocab item breakdowns, PLAB set splits), prefixed per test. Sessions
      without a given test have empty cells for that test's columns.
    - ``psychometric_results_{DCN}_merged.csv``: sessions merged per participant
      (e.g. PT1 + PT2) when their tests are disjoint.

    Parameters
    ----------
    test_session_folder : Path | None
        Path to the folder containing restructured psychometric test sessions.
        If None, it uses the default directory from settings.

    Returns
    -------
    Path
        The path to the generated per-session results CSV file.

    Notes
    -----
    - All computations are performed once per session and collected into a single
      wide per-session row; tests without data produce empty cells.
    """
    if test_session_folder is None:
        test_session_folder = settings.PSYCHOMETRIC_TESTS_DIR

    output_dir = settings.OUTPUT_DIR / settings.PSYCHOMETRIC_TESTS_FOLDER

    if not test_session_folder.exists() or not any(
        _is_valid_folder(p) for p in test_session_folder.iterdir()
    ):
        get_logger(__name__).info(
            "No psychometric test session folders found. Skipping."
        )
        return output_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    # Run sanity check before processing
    validate_psychometric_data(
        settings.PSYM_PARTICIPANT_CONFIGS, test_session_folder, is_restructured=True
    )

    # Collect session folders
    session_folders = test_session_folder.iterdir()
    session_folders = [p for p in session_folders if _is_valid_folder(p)]
    session_folders = sorted(session_folders, key=lambda p: p.name)

    overview_rows: list[dict] = []
    detailed_rows: list[dict] = []

    for session in session_folders:
        try:
            folder_sid = Sid(session.name)
            pid = folder_sid.pid
            session_part = folder_sid.session
            session_id_extended = str(folder_sid)
            postfix = folder_sid.postfix
            notes = folder_sid.notes
        except (ValueError, TypeError):
            # Fallback for non-standard folders if absolutely necessary
            folder_sid = None
            pid = session.name[:3] if len(session.name) >= 3 else session.name
            session_part = ""
            session_id_extended = session.name
            postfix = ""
            notes = ""

        # Find the original config file inside the session folder to ensure correct metadata.
        # In restructured folders, there should be exactly one .yaml file.
        config_files = list(session.glob("*.yaml"))
        if config_files and folder_sid:
            try:
                config_sid = Sid(config_files[0].stem)
                if folder_sid.equals_soft(config_sid):
                    # Prefer metadata from the original config if they soft-match
                    pid = config_sid.pid
                    session_part = config_sid.session
                    session_id_extended = str(config_sid)
                    postfix = config_sid.postfix
                    notes = config_sid.notes
            except (ValueError, TypeError):
                pass

        # Initialise an overview row with participant and per-test Done flags (0/1)
        overview_row: dict = {
            "session_id": session_id_extended,
            "participant_id": pid,
            "LWMC_Done": 0,
            "RAN_Done": 0,
            "Stroop_Done": 0,
            "Flanker_Done": 0,
            "WikiVocab_Done": 0,
            "PLAB_Done": 0,
            "notes": notes,
        }

        # Detailed row: single CSV per participant with namespaced, readable columns
        detailed_row: dict = {
            "participant_id": pid,
            "session": session_part,
            "session_id": session_id_extended,
            "postfix": postfix,
            "notes": notes,
        }

        # LWMC
        lwmc_dir = session / settings.PSYM_LWMC_DIR
        if lwmc_dir.exists():
            try:
                res_lwmc = preprocess_lwmc(lwmc_dir)  # dict
                # detailed: all LWMC metrics (the _Done flags live only in the overview)
                detailed_row.update(
                    {k: v for k, v in res_lwmc.items() if not k.endswith("_Done")}
                )
                # overview: selected scores and processing tasks
                for k in [
                    "LWMC_MU_score",
                    "LWMC_OS_score",
                    "LWMC_SS_score",
                    "LWMC_SSTM_score",
                    "LWMC_Total_score_mean",
                    "LWMC_OS_processingTask_score",
                    "LWMC_SentS_processingTask_score",
                    "LWMC_MU_Done",
                    "LWMC_OS_Done",
                    "LWMC_SS_Done",
                    "LWMC_SSTM_Done",
                ]:
                    if k in res_lwmc:
                        overview_row[k] = res_lwmc[k]
                overview_row["LWMC_Done"] = 1
            except ValueError as err:
                get_logger(__name__).debug(
                    f"[{session.name}] LWMC test skipped: {err!s}"
                )

        # RAN
        ran_dir = session / settings.PSYM_RAN_DIR
        if ran_dir.exists():
            try:
                res_ran = preprocess_ran(ran_dir)
                # both detailed and overview get all RAN metrics
                detailed_row.update(res_ran)
                overview_row.update(res_ran)
                # Mark Done on successful preprocessing regardless of emptiness
                overview_row["RAN_Done"] = 1
            except ValueError as err:
                get_logger(__name__).debug(
                    f"[{session.name}] RAN test skipped: {err!s}"
                )

        # Stroop & Flanker
        sf_dir = session / settings.PSYM_STROOP_FLANKER_DIR
        if sf_dir.exists():
            try:
                res_stroop = preprocess_stroop(sf_dir)  # DataFrame
                stroop_effects = {
                    "StroopAccuracyEffect": res_stroop["Stroop_incongruent_accuracy"]
                    - res_stroop["Stroop_congruent_accuracy"],
                    "StroopRTEffect_sec": res_stroop["Stroop_incongruent_rt_mean_sec"]
                    - res_stroop["Stroop_congruent_rt_mean_sec"],
                    "Stroop_incongruent_correct_rt_mean_sec": res_stroop[
                        "Stroop_incongruent_correct_rt_mean_sec"
                    ],
                    "Stroop_congruent_correct_rt_mean_sec": res_stroop[
                        "Stroop_congruent_correct_rt_mean_sec"
                    ],
                }
                # overview: only effects
                overview_row.update(stroop_effects)
                # detailed: effects + grouped metrics per condition
                detailed_row.update(stroop_effects)
                detailed_row.update(res_stroop)
                overview_row["Stroop_Done"] = 1
            except ValueError as err:
                get_logger(__name__).debug(
                    f"[{session.name}] Stroop test skipped: {err!s}"
                )
            try:
                res_flanker = preprocess_flanker(sf_dir)  # DataFrame
                flanker_effects = {
                    "FlankerAccuracyEffect": res_flanker["Flanker_incongruent_accuracy"]
                    - res_flanker["Flanker_congruent_accuracy"],
                    "FlankerRTEffect_sec": res_flanker[
                        "Flanker_incongruent_rt_mean_sec"
                    ]
                    - res_flanker["Flanker_congruent_rt_mean_sec"],
                    "Flanker_incongruent_correct_rt_mean_sec": res_flanker[
                        "Flanker_incongruent_correct_rt_mean_sec"
                    ],
                    "Flanker_congruent_correct_rt_mean_sec": res_flanker[
                        "Flanker_congruent_correct_rt_mean_sec"
                    ],
                }
                # overview: only effects
                overview_row.update(flanker_effects)
                # detailed: effects + grouped metrics per condition
                detailed_row.update(flanker_effects)
                detailed_row.update(res_flanker)
                overview_row["Flanker_Done"] = 1
            except ValueError as err:
                get_logger(__name__).debug(
                    f"[{session.name}] Flanker test skipped: {err!s}"
                )

        # WikiVocab (tuple[rt_mean, accuracy])
        wv_dir = session / settings.PSYM_WIKIVOCAB_DIR
        if wv_dir.exists():
            try:
                res_wv = preprocess_wikivocab(wv_dir)
                # detailed: all computed fields
                # detailed_row.update({f"WikiVocab_{k}": v for k, v in wv.items()})
                detailed_row.update(res_wv)
                # overview: only selected
                for key in [
                    "WikiVocab_rt_mean_sec",
                    "WikiVocab_accuracy",
                    "WikiVocab_incorrect_correct_score",
                    "WikiVocab_correct_words_rt_mean_sec",
                    "WikiVocab_correct_pseudowords_rt_mean_sec",
                ]:
                    overview_row[key] = res_wv[key]
                overview_row["WikiVocab_Done"] = 1
            except ValueError as err:
                get_logger(__name__).debug(
                    f"[{session.name}] WikiVocab test skipped: {err!s}"
                )

        # PLAB (tuple[rt_mean, accuracy])
        plab_dir = session / settings.PSYM_PLAB_DIR
        if plab_dir.exists():
            try:
                res_plab = preprocess_plab(plab_dir)
                detailed_row.update(res_plab)
                overview_row["PLAB_rt_mean_sec"] = res_plab["PLAB_rt_mean_sec"]
                overview_row["PLAB_accuracy"] = res_plab["PLAB_accuracy"]
                overview_row["PLAB_set1_accuracy"] = res_plab["PLAB_set1_accuracy"]
                overview_row["PLAB_set2_accuracy"] = res_plab["PLAB_set2_accuracy"]
                overview_row["PLAB_set1_rt_mean_sec"] = res_plab[
                    "PLAB_set1_rt_mean_sec"
                ]
                overview_row["PLAB_set2_rt_mean_sec"] = res_plab[
                    "PLAB_set2_rt_mean_sec"
                ]
                overview_row["PLAB_Done"] = 1
            except ValueError as err:
                get_logger(__name__).debug(
                    f"[{session.name}] PLAB test skipped: {err!s}"
                )

        # Collect the wide per-session row containing all summary and detailed metrics.
        detailed_rows.append(detailed_row)
        overview_rows.append(overview_row)

    # Write overview CSV (wide format) to the output directory
    out_path = output_dir / f"psychometric_results_{settings.DATA_COLLECTION_NAME}.csv"

    # Consolidated wide table: all detailed metrics per session plus _Done flags.
    df = pd.DataFrame(detailed_rows)
    flag_cols = [
        "LWMC_Done",
        "LWMC_MU_Done",
        "LWMC_OS_Done",
        "LWMC_SS_Done",
        "LWMC_SSTM_Done",
        "RAN_Done",
        "Stroop_Done",
        "Flanker_Done",
        "WikiVocab_Done",
        "PLAB_Done",
    ]
    # Merge the _Done flags (present on overview rows) into the detailed rows.
    overview_df = pd.DataFrame(overview_rows)
    flag_cols_present = [c for c in flag_cols if c in overview_df.columns]
    flag_df = overview_df[flag_cols_present].fillna(0).astype(int)
    df = pd.concat([df, flag_df], axis=1)

    # Order columns: identifiers, then flags, then metrics grouped by test.
    id_cols = ["session_id", "participant_id", "session", "postfix", "notes"]
    ordered_cols = _ordered_psychometric_columns(df.columns, id_cols, flag_cols)
    df = df[ordered_cols]
    df.to_csv(out_path, index=False)

    get_logger(__name__).info(f"Wrote results: {out_path}")

    merged_path = create_merged_psychometric_overview(out_path)
    get_logger(__name__).info(f"Wrote merged results: {merged_path}")

    _warn_missing_tests_in_merged_overview(merged_path, test_session_folder)

    return out_path


def create_merged_psychometric_overview(overview_path: Path) -> Path:
    """
    Create a merged version of a wide psychometric results table.

    Rows for the same participant are merged if their tests are disjoint
    (e.g., PT1 has RAN and PT2 has LWMC). If tests overlap, they are not
    merged and a warning is issued.

    Parameters
    ----------
    overview_path : Path
        Path to the wide per-session results CSV (e.g. ``psychometric_results_*``).

    Returns
    -------
    Path
        Path to the generated merged overview CSV.
    """
    df = read_csv(overview_path, dtype={"participant_id": str})
    if df.empty:
        return overview_path

    # Extract base session ID (without the S/PT/ET suffix)
    def get_base_sid(sid_str):
        try:
            # Reconstruct SID without the session part
            return Sid(sid_str).base_id
        except Exception:
            # Fallback: remove trailing _PTn or _Sn or _ETn
            return re.sub(r"_(S|PT|ET)\d+$", "", str(sid_str))

    import re

    df["base_session_id"] = df["session_id"].apply(get_base_sid)

    done_cols = [c for c in df.columns if c.endswith("_Done")]

    merged_rows = []
    # Group by base_session_id and participant_id
    for (base_sid, pid), group in df.groupby(["base_session_id", "participant_id"]):
        if len(group) == 1:
            row = group.iloc[0].to_dict()
            row["original_sessions"] = row["session_id"]
            row["session_id"] = base_sid
            merged_rows.append(row)
            continue

        # Check for overlapping tests
        can_merge = True
        for col in done_cols:
            if group[col].sum() > 1:
                can_merge = False
                get_logger(__name__).warning(
                    f"Cannot merge sessions for participant {pid} ({base_sid}): "
                    f"overlapping results for {col}."
                )
                break

        if can_merge:
            # Merge disjoint rows
            merged_row = group.iloc[0].copy()
            merged_row["session_id"] = base_sid
            merged_row["original_sessions"] = ", ".join(
                group["session_id"].astype(str).tolist()
            )

            # For all columns that are not IDs or Done flags, take the non-null/non-zero value
            # Actually, most result columns should be disjoint if _Done flags are disjoint.
            for col in df.columns:
                if col in [
                    "session_id",
                    "participant_id",
                    "base_session_id",
                    "notes",
                    "original_sessions",
                ]:
                    continue

                # If it's a _Done col, sum it.
                if col in done_cols:
                    merged_row[col] = group[col].sum()
                else:
                    # Find non-NA values in the group for this column
                    valid_values = group[col].dropna()
                    if not valid_values.empty:
                        merged_row[col] = valid_values.iloc[0]
                    else:
                        merged_row[col] = nan

            # Merge notes
            all_notes = [
                str(n).strip() for n in group["notes"].dropna() if str(n).strip()
            ]
            merged_row["notes"] = "; ".join(dict.fromkeys(all_notes))

            merged_rows.append(merged_row.to_dict())
        else:
            # Keep separate
            for _, row in group.iterrows():
                r = row.to_dict()
                r["original_sessions"] = r["session_id"]
                r["session_id"] = (
                    base_sid  # Or keep original? User said '015_HR_hr_1' in first column
                )
                merged_rows.append(r)

    merged_df = DataFrame(merged_rows)

    # Reorder columns
    session_cols = ["session_id", "participant_id", "original_sessions"]
    flag_cols = done_cols
    fixed = session_cols + flag_cols + ["notes"]
    remaining = [
        c for c in merged_df.columns if c not in fixed and c != "base_session_id"
    ]

    # Filter out columns that might not exist in df
    final_cols = [c for c in fixed if c in merged_df.columns] + remaining
    merged_df = merged_df[final_cols]

    out_path = overview_path.parent / overview_path.name.replace(".csv", "_merged.csv")
    merged_df.to_csv(out_path, index=False)
    return out_path


def _is_valid_folder(folder: Path) -> bool:
    return folder.is_dir() and folder.stem[:3].isdigit() and folder.stem[3] == "_"


_TEST_ORDER = ["LWMC", "RAN", "Stroop", "Flanker", "WikiVocab", "PLAB"]


def _ordered_psychometric_columns(
    columns: list[str],
    id_cols: list[str],
    flag_cols: list[str],
) -> list[str]:
    """
    Order the wide results columns: identifiers, then flags, then metrics per test.

    Metric columns are grouped by their test name prefix (``_TEST_ORDER``) and
    sorted alphabetically within each group. Any unrecognized metric columns are
    appended at the end in sorted order.

    Parameters
    ----------
    columns : list[str]
        All columns present in the results table.
    id_cols : list[str]
        Identifier columns to place first.
    flag_cols : list[str]
        ``_Done`` flag columns to place after the identifiers.

    Returns
    -------
    list[str]
        The ordered column list (only columns present in ``columns``).
    """
    ids = [c for c in id_cols if c in columns]
    flags = [c for c in flag_cols if c in columns]
    metrics = [c for c in columns if c not in id_cols and c not in flag_cols]

    remaining = list(metrics)
    metrics_ordered: list[str] = []
    for prefix in _TEST_ORDER:
        group = sorted(c for c in remaining if c.startswith(prefix))
        metrics_ordered.extend(group)
        remaining = [c for c in remaining if c not in group]
    metrics_ordered.extend(sorted(remaining))

    return ids + flags + metrics_ordered


def _warn_missing_tests_in_merged_overview(
    merged_path: Path, test_session_folder: Path
) -> None:
    """
    Emit consolidated warnings for missing or unexpected psychometric tests.

    Compares the expected psychometric tests (from the participant config YAMLs)
    against the ``_Done`` flags in the merged overview and emits at most one
    warning per category, listing all affected participants together:

    - config says a test is expected, but it was not preprocessed (``_Done`` = 0)
    - config says a test is absent, but data was preprocessed (``_Done`` > 0)

    The config YAMLs are looked up in the session folders of ``test_session_folder``
    (restructured layout), falling back to the legacy config folder.

    Parameters
    ----------
    merged_path : Path
        Path to the merged psychometric overview CSV.
    test_session_folder : Path
        The folder containing the per-session psychometric test folders.
    """
    merged_df = read_csv(merged_path, dtype={"participant_id": str})
    if merged_df.empty:
        return

    done_cols = [c for c in merged_df.columns if c.endswith("_Done")]

    # Folder name -> _Done columns produced when the test is processed.
    # A test counts as fully done only when all its flags are set. for LWMC this
    # includes the per-subtask flags so that a partial run (some subtasks missing) is
    # still reported as missing expected data.
    folder_to_done = {
        "PLAB": ["PLAB_Done"],
        "RAN": ["RAN_Done"],
        "Stroop_Flanker": ["Stroop_Done", "Flanker_Done"],
        "WMC": [
            "LWMC_Done",
            "LWMC_MU_Done",
            "LWMC_OS_Done",
            "LWMC_SS_Done",
            "LWMC_SSTM_Done",
        ],
        "WikiVocab": ["WikiVocab_Done"],
    }

    # Aggregate expected flags across all session-level config files per base SID.
    config_files = find_psychometric_config_files(
        settings.PSYM_PARTICIPANT_CONFIGS, test_session_folder, is_restructured=True
    )
    expected_by_base: dict[str, dict[str, bool]] = {}
    for config_file in config_files:
        try:
            base_id = Sid(config_file.stem).base_id
        except (ValueError, TypeError):
            continue
        with open(config_file) as f:
            config_data = yaml.safe_load(f) or {}
        agg = expected_by_base.setdefault(base_id, {})
        for yaml_flag in settings.PSYCHOMETRIC_TEST_MAPPING:
            agg[yaml_flag] = agg.get(yaml_flag, False) or (
                config_data.get(yaml_flag, False) is True
            )

    missing_for_expected: dict[str, list[str]] = {}
    present_but_unexpected: dict[str, list[str]] = {}

    for _, row in merged_df.iterrows():
        base_id = str(row["session_id"])
        if base_id not in expected_by_base:
            continue
        expected = expected_by_base[base_id]
        for yaml_flag, folder_name in settings.PSYCHOMETRIC_TEST_MAPPING.items():
            done_names = [
                c for c in folder_to_done.get(folder_name, []) if c in done_cols
            ]
            if not done_names:
                continue
            any_done = any(int(row[c]) > 0 for c in done_names)
            all_done = all(int(row[c]) > 0 for c in done_names)
            if expected.get(yaml_flag, False):
                if not all_done:
                    missing_for_expected.setdefault(folder_name, []).append(base_id)
            else:
                if any_done:
                    present_but_unexpected.setdefault(folder_name, []).append(base_id)

    _log_test_report(
        get_logger(__name__),
        "Participants missing expected psychometric tests (marked as expected in "
        "config, but no results were preprocessed)",
        missing_for_expected,
    )
    _log_test_report(
        get_logger(__name__),
        "Participants with psychometric test data but marked as absent (or missing) "
        "in config",
        present_but_unexpected,
    )


def _log_test_report(
    logger: Logger,
    description: str,
    by_test: dict[str, list[str]],
    max_sids: int = 5,
) -> None:
    """
    Log a per-test summary of affected participants as a single warning.

    Groups the affected participant SIDs by test and prints a count plus a short
    list per test, truncating long lists to ``max_sids`` entries.

    Parameters
    ----------
    logger : Logger
        The logger to emit the warning on.
    description : str
        Human-readable description of the category being reported.
    by_test : dict[str, list[str]]
        Mapping from test folder name to a list of affected participant SIDs.
    max_sids : int
        Maximum number of participant SIDs to list per test before truncating.
    """
    if not by_test:
        return

    unique_sids = sorted({sid for sids in by_test.values() for sid in sids})
    lines = [
        f"{description}:",
        f"  Affected: {len(unique_sids)} participant(s)",
    ]
    for folder_name in sorted(by_test):
        sids = sorted(dict.fromkeys(by_test[folder_name]))
        shown = ", ".join(sids[:max_sids])
        if len(sids) > max_sids:
            shown += f", ... (+{len(sids) - max_sids} more)"
        lines.append(f"  {folder_name}: {len(sids)} participant(s): {shown}")

    logger.warning("\n".join(lines))


def preprocess_stroop(stroop_flanker_dir: Path) -> dict:
    """Preprocess Stroop test CSV data.

    Computes reaction time and accuracy grouped by stimulus type
    (congruent, incongruent, neutral).

    **Stroop**: The Stroop test is a test of cognitive control that measures the ability to inhibit
    automatic responses. The test consists of three parts:
    a color naming task, a word reading task, and a color-word naming task.

    **Reference**: J. R. Stroop. Studies of interference in serial verbal reactions.
    Journal of Experimental Psychology, 18(6):643–662, December 1935. doi:10.1037/h0054651.

    **Effect Calculations**:
    - StroopAccuracyEffect = incongruent_accuracy - congruent_accuracy
    - StroopRTEffect_sec = incongruent_rt_mean_sec - congruent_rt_mean_sec

    Parameters
    ----------
    stroop_flanker_dir : Path
        Path to the folder containing Stroop and Flanker data.

    Returns
    -------
    dict
        A dictionary containing reaction times, accuracies, and item counts
        for each condition, prefixed with 'Stroop_'.

    Raises
    ------
    ValueError
        If no valid results file with required columns is found.
    """
    try:
        df = _find_one_filetype_with_columns(
            stroop_flanker_dir,
            ["stim_type", "stroop_key.rt", "stroop_key.corr"],
            allow_nan=True,
        )
    except ValueError as err:
        # Determine display path for the outer error message
        try:
            psym_dir = settings.PSYCHOMETRIC_TESTS_DIR
            if (
                stroop_flanker_dir.is_absolute()
                and psym_dir.is_absolute()
                and stroop_flanker_dir.is_relative_to(psym_dir)
            ):
                display_path = str(stroop_flanker_dir.relative_to(psym_dir))
            else:
                display_path = stroop_flanker_dir.name
        except (ValueError, AttributeError):
            display_path = stroop_flanker_dir.name

        import re

        see_also = ""
        files_checked = re.findall(r"'([^']+)'", str(err))
        # Filter out common non-file strings
        if files_checked:
            # Only include names that look like CSVs
            csv_files = [f for f in files_checked if f.endswith(".csv")]
            if csv_files:
                see_also = f" See '{display_path}/" + "', '".join(csv_files) + "'."

        raise ValueError(
            f"Stroop results missing or incomplete in '{display_path}'. "
            f"The script couldn't find a valid results file with stimulus and response data. "
            f"Please check if the experiment was interrupted or if the data was recorded correctly.{see_also} "
            f"\nDetail: {err}"
        ) from err
    result_df = _reaction_time_accuracy(
        df,
        reaction_time_col="stroop_key.rt",
        correctness_col="stroop_key.corr",
        group_by_col="stim_type",
        min_rt=settings.PSYM_STROOP_MIN_RT,
        max_rt=settings.PSYM_STROOP_MAX_RT,
    )
    # RT for correct responses only
    result_df_acc = _reaction_time_accuracy(
        df,
        reaction_time_col="stroop_key.rt",
        correctness_col="stroop_key.corr",
        group_by_col="stim_type",
        correct_only=True,
        min_rt=settings.PSYM_STROOP_MIN_RT,
        max_rt=settings.PSYM_STROOP_MAX_RT,
    )

    result_df.rename(columns={"rt_mean": "rt_mean_sec"}, inplace=True)
    result_df_acc.rename(columns={"rt_mean": "correct_rt_mean_sec"}, inplace=True)

    result_dict = {}
    for cond in ["incongruent", "congruent", "neutral"]:
        for metric in ("rt_mean_sec", "accuracy", "num_items"):
            result_dict[f"Stroop_{cond}_{metric}"] = float(result_df.loc[cond, metric])
        # Add correct RT mean
        result_dict[f"Stroop_{cond}_correct_rt_mean_sec"] = float(
            result_df_acc.loc[cond, "correct_rt_mean_sec"]
        )

    return result_dict


def preprocess_flanker(stroop_flanker_dir: Path) -> dict:
    """Preprocess Flanker test CSV data.

    Computes reaction time and accuracy grouped by stimulus type
    (congruent, incongruent, neutral).

    **Flanker**: The Flanker test is a test of cognitive control that measures the ability to
    inhibit irrelevant information.
    The test consists of a series of trials in which participants must respond to a central target
    while ignoring flanking distractors.

    **Reference**: Barbara A. Eriksen and Charles W. Eriksen. Effects of noise letters upon the
    identification of a target letter in a nonsearch task.
    Perception & Psychophysics, 16(1):143–149, January 1974. doi:10.3758/BF03203267.

    **Effect Calculations**:
    - FlankerAccuracyEffect = incongruent_accuracy - congruent_accuracy
    - FlankerRTEffect_sec = incongruent_rt_mean - congruent_rt_mean

    Parameters
    ----------
    stroop_flanker_dir : Path
        Path to the folder containing Stroop and Flanker data.

    Returns
    -------
    dict
        A dictionary containing reaction times, accuracies, and item counts
        for each condition, prefixed with 'Flanker_'.

    Raises
    ------
    ValueError
        If no valid results file with required columns is found.
    """
    try:
        df = _find_one_filetype_with_columns(
            stroop_flanker_dir,
            ["stim_type", "Flanker_key.rt", "Flanker_key.corr"],
            allow_nan=True,
        )
    except ValueError as err:
        # Determine display path for the outer error message
        try:
            psym_dir = settings.PSYCHOMETRIC_TESTS_DIR
            if (
                stroop_flanker_dir.is_absolute()
                and psym_dir.is_absolute()
                and stroop_flanker_dir.is_relative_to(psym_dir)
            ):
                display_path = str(stroop_flanker_dir.relative_to(psym_dir))
            else:
                display_path = stroop_flanker_dir.name
        except (ValueError, AttributeError):
            display_path = stroop_flanker_dir.name

        import re

        see_also = ""
        files_checked = re.findall(r"'([^']+)'", str(err))
        if files_checked:
            csv_files = [f for f in files_checked if f.endswith(".csv")]
            if csv_files:
                see_also = f" See '{display_path}/" + "', '".join(csv_files) + "'."

        raise ValueError(
            f"Flanker results missing or incomplete in '{display_path}'. "
            f"The script couldn't find a valid results file with stimulus and response data. "
            f"Please check if the experiment was interrupted or if the data was recorded correctly.{see_also} "
            f"\nDetail: {err}"
        ) from err
    result_df = _reaction_time_accuracy(
        df,
        reaction_time_col="Flanker_key.rt",
        correctness_col="Flanker_key.corr",
        group_by_col="stim_type",
        min_rt=settings.PSYM_FLANKER_MIN_RT,
        max_rt=settings.PSYM_FLANKER_MAX_RT,
    )
    # RT for correct responses only
    result_df_acc = _reaction_time_accuracy(
        df,
        reaction_time_col="Flanker_key.rt",
        correctness_col="Flanker_key.corr",
        group_by_col="stim_type",
        correct_only=True,
        min_rt=settings.PSYM_FLANKER_MIN_RT,
        max_rt=settings.PSYM_FLANKER_MAX_RT,
    )

    result_df.rename(columns={"rt_mean": "rt_mean_sec"}, inplace=True)
    result_df_acc.rename(columns={"rt_mean": "correct_rt_mean_sec"}, inplace=True)

    result_dict = {}
    for cond in ["incongruent", "congruent"]:
        for metric in ("rt_mean_sec", "accuracy", "num_items"):
            result_dict[f"Flanker_{cond}_{metric}"] = float(result_df.loc[cond, metric])
        # Add correct RT mean
        result_dict[f"Flanker_{cond}_correct_rt_mean_sec"] = float(
            result_df_acc.loc[cond, "correct_rt_mean_sec"]
        )

    return result_dict


def preprocess_lwmc(lwmc_dir: Path) -> dict:
    """Preprocess Lewandowsky WMC battery.

    **Tasks**:

    - MU (Memory Update): proportion of items recalled correctly (per-trial mean, then mean over trials).
    - OS (Operation Span): mean of per-trial recall correctness (unweighted by list length).
    - SS (Sentence Span): mean of per-trial recall correctness (unweighted by list length).
    - SSTM (Spatial Short-Term Memory): overall score normalised by 240 from ``SSTM-<id>.dat``.

    **Implementation notes**:

    - MU/OS/SS data are taken from the CSV export (not the .dat files).
      We compute a trial index from ``base_text_intertrial.started`` and then, for each task,
      compute the mean of the per-trial mean correctness values. This avoids overweighting
      trials with more items.
    - SSTM continues to be read from the original ``.dat`` file.
    - A partial run (a CSV missing entire task columns, or a missing SSTM ``.dat``) is not
      an error: the tasks that do have data are scored and the missing ones are reported via
      ``LWMC_<Task>_Done`` flags set to 0 with NaN scores. ``LWMC_Total_score_mean`` is only
      computed when all four subtasks are present.

    Attribution: Scoring concept adapted from Laura Stahlhut's Python implementation (2022)
    of the Lewandowsky WMC battery (wmc-analysis).

    **Reference**: Stephan Lewandowsky, Klaus Oberauer, Lee-Xieng Yang, and Ullrich K. H. Ecker.
    A working memory test battery for MATLAB. Behavior Research Methods, 42(2):571–585, May 2010.
    doi:10.3758/BRM.42.2.571.

    **Exact Mathematical Formulas**:
    - Trial_Score_MU = sum(correct_items_in_trial) / num_items_in_trial
    - MU_score = mean(Trial_Score_MU) across all trials
    - Trial_Score_OS = sum(correct_items_in_trial) / num_items_in_trial
    - OS_score = mean(Trial_Score_OS) across all trials
    - Trial_Score_SS = sum(correct_items_in_trial) / num_items_in_trial
    - SS_score = mean(Trial_Score_SS) across all trials
    - SSTM_score = SSTM_raw_score / 240.0
    - LWMC_Total_score_mean = (MU_score + OS_score + SS_score + SSTM_score) / 4,
      computed only when all four subtasks are available.

    Parameters
    ----------
    lwmc_dir : Path
        Path to the folder containing the WMC test data.

    Returns
    -------
    dict
        A dictionary with scores and response times for each task, prefixed with 'LWMC_'.
        Each task also has a ``LWMC_<Task>_Done`` flag (0/1) indicating whether usable data
        was found for it.

    Raises
    ------
    ValueError
        If no usable WMC data at all is available, or the SSTM ``.dat`` file is malformed.
    """

    # 1) Load the single WMC CSV that contains the relevant columns.
    #    The file may be partial: a run that aborted partway can be missing the
    #    columns for tasks that never started (e.g. no MU). read_all_columns=False
    #    lets us still extract the tasks that were recorded.
    required_cols = [
        "is_practice",  # Filter out practice trials
        "base_text_intertrial.started",  # Marker to separate trials
        "mu_key_resp_recall.is_correct",
        "mu_key_resp_recall.rt",  # MU columns
        "os_key_resp_recall.corr",
        "os_key_resp_recall.rt",  # OS columns
        "os_key_resp_equation.corr",  # OS processing task
        "ss_key_resp_recall.corr",
        "ss_key_resp_recall.rt",  # SS columns
        "ss_key_resp_sentence.corr",  # SS processing task
    ]
    try:
        df = _find_one_filetype_with_columns(
            lwmc_dir, required_cols, allow_nan=True, read_all_columns=False
        )
    except ValueError as err:
        # Determine display path for the outer error message
        try:
            psym_dir = settings.PSYCHOMETRIC_TESTS_DIR
            if (
                lwmc_dir.is_absolute()
                and psym_dir.is_absolute()
                and lwmc_dir.is_relative_to(psym_dir)
            ):
                display_path = str(lwmc_dir.relative_to(psym_dir))
            else:
                display_path = lwmc_dir.name
        except (ValueError, AttributeError):
            display_path = lwmc_dir.name

        import re

        see_also = ""
        files_checked = re.findall(r"'([^']+)'", str(err))
        if files_checked:
            csv_files = [f for f in files_checked if f.endswith(".csv")]
            if csv_files:
                see_also = f" See '{display_path}/" + "', '".join(csv_files) + "'."

        raise ValueError(
            f"LWMC (Working Memory Capacity) results missing or incomplete in '{display_path}'. "
            f"The script couldn't find a valid results file with recall and timing data. "
            f"Please check if the experiment was interrupted or if the data was recorded correctly.{see_also} "
            f"\nDetail: {err}"
        ) from err

    anchors = ["is_practice", "base_text_intertrial.started"]
    if not all(a in df.columns for a in anchors):
        raise ValueError(
            "LWMC (Working Memory Capacity) results missing or incomplete: the WMC CSV "
            "does not contain the trial markers required to compute scores."
        )

    # Create a trial identifier using the inter-trial text onset markers
    # Each non-NaN in base_text_intertrial.started indicates a new trial boundary.
    df["trial_id"] = df["base_text_intertrial.started"].notna().cumsum()

    mask = df["is_practice"].fillna(False)
    if mask.dtype != bool:
        mask = mask.astype(bool)
    df = df[~mask].copy()
    if df.empty:
        raise ValueError("No non-practice trials found in WMC CSV")

    def _per_trial_mean_then_mean(
        correctness_col: str, time_col: str, label: str
    ) -> tuple[float, float, bool]:
        """Return (mean score, mean time, done) for one WMC subtask.

        A missing or empty subtask is not an error: it yields (nan, nan, False) so the
        other (partial) data can still be used.
        """
        if correctness_col not in df.columns:
            return nan, nan, False
        # Select only rows with a value for the specific task's correctness column
        mask_vals = df[correctness_col].notna()
        if not mask_vals.any():
            return nan, nan, False
        # Use the in-frame 'trial_id' column to avoid index alignment issues
        sub = df.loc[mask_vals, [correctness_col, time_col, "trial_id"]].copy()
        # Ensure correctness is numeric (0/1 or NaN)
        sub[correctness_col] = pd.to_numeric(sub[correctness_col], errors="coerce")
        # Compute mean correctness per trial_id, then mean of these per-trial means
        corr_per_trial = sub.groupby("trial_id", dropna=True)[correctness_col].mean()
        time_per_trial = sub.groupby("trial_id", dropna=True)[time_col].mean()
        if corr_per_trial.empty:
            return nan, nan, False
        return float(corr_per_trial.mean()), float(time_per_trial.mean()), True

    # 2) Compute MU/OS/SS from CSV columns (each may be missing in a partial run)
    mu_score, mu_time, mu_done = _per_trial_mean_then_mean(
        "mu_key_resp_recall.is_correct", "mu_key_resp_recall.rt", "MU"
    )
    os_score, os_time, os_done = _per_trial_mean_then_mean(
        "os_key_resp_recall.corr", "os_key_resp_recall.rt", "OS"
    )
    ss_score, ss_time, ss_done = _per_trial_mean_then_mean(
        "ss_key_resp_recall.corr", "ss_key_resp_recall.rt", "SS"
    )

    # 2b) Compute processing task scores for OS and SS
    def _compute_processing_score(col: str) -> float:
        if col not in df.columns:
            return nan
        return float(df[col].mean())

    os_proc_score = _compute_processing_score("os_key_resp_equation.corr")
    ss_proc_score = _compute_processing_score("ss_key_resp_sentence.corr")

    # 3) SSTM from legacy .dat
    def _participant_id_from_dir(d: Path) -> str:
        stem = d.parent.stem
        if len(stem) < 3 or not stem[:3].isdigit():
            raise ValueError(f"Cannot infer participant id from folder name: {stem}")
        return str(int(stem[:3]))

    pid = _participant_id_from_dir(lwmc_dir)
    sstm_file = lwmc_dir / f"SSTM-{pid}.dat"
    sstm_done = False
    if sstm_file.exists() and sstm_file.is_file():

        def _read_lines(p: Path) -> list[str]:
            try:
                with p.open("r", encoding="utf-8") as fh:
                    return fh.readlines()
            except Exception as exc:
                raise ValueError(f"Failed to read WMC file {p}: {exc}") from exc

        sstm_lines = _read_lines(sstm_file)
        if len(sstm_lines) < 2:
            raise ValueError(f"Malformed SSTM file (too few lines): {sstm_file}")
        sstm_tokens = [t for t in sstm_lines[1].rstrip("\n").split(" ") if t != ""]
        if len(sstm_tokens) < 2:
            raise ValueError(f"Malformed SSTM line (too few tokens): {sstm_lines[1]}")
        try:
            sstm_raw = int(sstm_tokens[1])
        except ValueError as exc:
            raise ValueError(f"Invalid SSTM score token: {sstm_tokens[1]}") from exc
        sstm_score = sstm_raw / 240.0
        sstm_done = True
    else:
        # Missing SSTM file: keep the other subtask scores, SSTM stays NaN.
        sstm_score = nan

    if not any([mu_done, os_done, ss_done, sstm_done]):
        raise ValueError(
            "LWMC (Working Memory Capacity) results missing or incomplete: "
            "no usable WMC subtask data was found in the available files."
        )

    # 4) Total mean: only computed when all four subtasks are complete.
    if all([mu_done, os_done, ss_done, sstm_done]):
        total = (mu_score + os_score + ss_score + sstm_score) / 4.0
    else:
        total = nan

    missing_tasks = [
        label
        for label, done in [
            ("MU", mu_done),
            ("OS", os_done),
            ("SS", ss_done),
            ("SSTM", sstm_done),
        ]
        if not done
    ]
    if missing_tasks:
        get_logger(__name__).warning(
            "LWMC partially preprocessed for '%s': missing %s.",
            lwmc_dir.parent.name,
            ", ".join(missing_tasks),
        )

    return {
        "LWMC_MU_score": mu_score,
        "LWMC_MU_Done": 1 if mu_done else 0,
        "LWMC_MU_time_sec": mu_time,
        "LWMC_OS_score": os_score,
        "LWMC_OS_Done": 1 if os_done else 0,
        "LWMC_OS_time_sec": os_time,
        "LWMC_OS_processingTask_score": os_proc_score,
        "LWMC_SS_score": ss_score,
        "LWMC_SS_Done": 1 if ss_done else 0,
        "LWMC_SS_time_sec": ss_time,
        "LWMC_SentS_processingTask_score": ss_proc_score,
        "LWMC_SSTM_score": sstm_score,
        "LWMC_SSTM_Done": 1 if sstm_done else 0,
        "LWMC_Total_score_mean": total,
    }


def preprocess_ran(ran_dir: Path) -> dict:
    """Preprocess RAN (Rapid Automatised Naming) test CSV data.

    Extracts reaction times for practice and experimental trials.

    **RAN task**:
    The Rapid Automatised Naming (RAN) task is a standard test of the speed and efficiency of naming digits.
    It is used to assess the speed of processing and the ability to quickly retrieve information
    from memory. This is a well-established cognitive assessment tool.

    **Calculation**: Direct extraction of Reading_Time for practice (Trial=1) and experimental (Trial=2) trials.

    Parameters
    ----------
    ran_dir : Path
        Path to the folder containing RAN test data.

    Returns
    -------
    dict
        A dictionary with keys 'RAN_practice_rt_sec' and 'RAN_experimental_rt_sec'.

    Raises
    ------
    ValueError
        If required results file is missing or malformed.
    """
    try:
        df = _find_one_filetype_with_columns(
            ran_dir, ["Trial", "Reading_Time"], allow_nan=False
        )
    except ValueError as err:
        # Determine display path for the outer error message
        try:
            psym_dir = settings.PSYCHOMETRIC_TESTS_DIR
            if (
                ran_dir.is_absolute()
                and psym_dir.is_absolute()
                and ran_dir.is_relative_to(psym_dir)
            ):
                display_path = str(ran_dir.relative_to(psym_dir))
            else:
                display_path = ran_dir.name
        except (ValueError, AttributeError):
            display_path = ran_dir.name

        import re

        see_also = ""
        files_checked = re.findall(r"'([^']+)'", str(err))
        if files_checked:
            csv_files = [f for f in files_checked if f.endswith(".csv")]
            if csv_files:
                see_also = f" See '{display_path}/" + "', '".join(csv_files) + "'."

        raise ValueError(
            f"RAN (Rapid Naming) results missing or incomplete in '{display_path}'. "
            f"Please check if the experiment was interrupted or if the data was recorded correctly.{see_also} "
            f"\nDetail: {err}"
        ) from err

    # Extract practice and experimental trial reaction times
    practice_rt = df[df["Trial"] == 1]["Reading_Time"]
    experimental_rt = df[df["Trial"] == 2]["Reading_Time"]

    return {
        "RAN_practice_rt_sec": float(practice_rt.iloc[0]),
        "RAN_experimental_rt_sec": float(experimental_rt.iloc[0]),
    }


def preprocess_wikivocab(wv_dir: Path) -> dict:
    """Preprocess WikiVocab test CSV data.

    Computes mean reaction time, overall accuracy, and balanced accuracy
    score based on LexTALE scoring.

    **WikiVocab**:
    The WikiVocab test is a generative vocabulary test for online research based on the Wikipedia corpus.
    It is designed to measure the breadth of an individual's vocabulary knowledge.

    **Reference**: Pol van Rijn, Yue Sun, Harin Lee, Raja Marjieh, Ilia Sucholutsky, Francesca
    Lanzarini, Elisabeth André, and Nori Jacoby.
    Around the world in 60 words: A generative vocabulary test for online research.
    February 2023. arXiv:2302.01614.

    **Calculation**:
    - Overall accuracy = sum(correct_trials) / total_trials
    - Real word accuracy = correct_real_words / num_real_words
    - Pseudo word accuracy = correct_pseudo_words / num_pseudo_words
    - Balanced score = (real_word_accuracy + pseudo_word_accuracy) / 2
      (Equivalent to LexTALE scoring: https://www.lextale.com/scoring.html)
    - Reaction times are filtered by a minimum threshold (default 200ms).

    Parameters
    ----------
    wv_dir : Path
        Path to the folder containing WikiVocab test data.

    Returns
    -------
    dict
        A dictionary with reaction times, accuracies, and balanced scores,
        prefixed with 'WikiVocab_'.

    Raises
    ------
    ValueError
        If required results file is missing or malformed.
    """
    try:
        df = _find_one_filetype_with_columns(
            wv_dir, ["correct_answer", "real_answer", "RT"], allow_nan=False
        )
    except ValueError as err:
        # Determine display path for the outer error message
        try:
            psym_dir = settings.PSYCHOMETRIC_TESTS_DIR
            if (
                wv_dir.is_absolute()
                and psym_dir.is_absolute()
                and wv_dir.is_relative_to(psym_dir)
            ):
                display_path = str(wv_dir.relative_to(psym_dir))
            else:
                display_path = wv_dir.name
        except (ValueError, AttributeError):
            display_path = wv_dir.name

        import re

        see_also = ""
        files_checked = re.findall(r"'([^']+)'", str(err))
        if files_checked:
            csv_files = [f for f in files_checked if f.endswith(".csv")]
            if csv_files:
                see_also = f" See '{display_path}/" + "', '".join(csv_files) + "'."

        raise ValueError(
            f"WikiVocab results missing or incomplete in '{display_path}'. "
            f"Please check if the experiment was interrupted or if the data was recorded correctly.{see_also} "
            f"\nDetail: {err}"
        ) from err

    try:
        # Validate correct_answer values
        if not df["correct_answer"].isin([0, 1]).all():
            invalid_vals = df.loc[
                ~df["correct_answer"].isin([0, 1]), "correct_answer"
            ].unique()
            raise ValueError(
                f"WikiVocab 'correct_answer' contains invalid values: {invalid_vals}. "
                "Expected 0 (pseudoword) or 1 (real word)."
            )

        # Validate RT values are numeric before filtering
        if not pd.api.types.is_numeric_dtype(df["RT"]):
            raise ValueError("Reaction time column contains non-numeric values.")

        # Filter by RT thresholds if provided
        df = df.copy()
        df = df[
            (df["RT"] >= settings.PSYM_WIKIVOCAB_MIN_RT)
            & (df["RT"] <= settings.PSYM_WIKIVOCAB_MAX_RT)
        ]
    except ValueError as err:
        # Re-use the same error wrapping logic for consistent reporting
        try:
            psym_dir = settings.PSYCHOMETRIC_TESTS_DIR
            if (
                wv_dir.is_absolute()
                and psym_dir.is_absolute()
                and wv_dir.is_relative_to(psym_dir)
            ):
                display_path = str(wv_dir.relative_to(psym_dir))
            else:
                display_path = wv_dir.name
        except (ValueError, AttributeError):
            display_path = wv_dir.name

        raise ValueError(
            f"WikiVocab results missing or incomplete in '{display_path}'. "
            f"Please check if the experiment was interrupted or if the data was recorded correctly. "
            f"\nDetail: {err}"
        ) from err

    df["correctness"] = df["correct_answer"] == df["real_answer"]

    # Calculate additional metrics
    num_pseudo = len(df[df["correct_answer"] == 0])
    num_real = len(df[df["correct_answer"] == 1])

    # Calculate correct fractions
    pseudo_correct = (
        df[(df["correct_answer"] == 0) & (df["correctness"])].shape[0] / num_pseudo
        if num_pseudo > 0
        else float("nan")
    )
    real_correct = (
        df[(df["correct_answer"] == 1) & (df["correctness"])].shape[0] / num_real
        if num_real > 0
        else float("nan")
    )

    # Calculate incorrect_correct score
    incorrect_correct = (real_correct + pseudo_correct) / 2

    # Ratio of items
    ratio_items = num_real / num_pseudo if num_pseudo > 0 else nan

    try:
        # Overall RT and accuracy
        rt_acc = _reaction_time_accuracy(
            df,
            reaction_time_col="RT",
            correctness_col="correctness",
            min_rt=settings.PSYM_WIKIVOCAB_MIN_RT,
            max_rt=settings.PSYM_WIKIVOCAB_MAX_RT,
        )

        # Correct RT for all items
        rt_acc_all = _reaction_time_accuracy(
            df,
            reaction_time_col="RT",
            correctness_col="correctness",
            correct_only=True,
            min_rt=settings.PSYM_WIKIVOCAB_MIN_RT,
            max_rt=settings.PSYM_WIKIVOCAB_MAX_RT,
        )

        # Correct RT for real words
        df_words = df[df["correct_answer"] == 1]
        if not df_words.empty:
            rt_acc_words = _reaction_time_accuracy(
                df_words,
                reaction_time_col="RT",
                correctness_col="correctness",
                correct_only=True,
                min_rt=settings.PSYM_WIKIVOCAB_MIN_RT,
                max_rt=settings.PSYM_WIKIVOCAB_MAX_RT,
            )
        else:
            rt_acc_words = (nan, nan, 0)

        # Correct RT for pseudowords
        df_pseudo = df[df["correct_answer"] == 0]
        if not df_pseudo.empty:
            rt_acc_pseudo = _reaction_time_accuracy(
                df_pseudo,
                reaction_time_col="RT",
                correctness_col="correctness",
                correct_only=True,
                min_rt=settings.PSYM_WIKIVOCAB_MIN_RT,
                max_rt=settings.PSYM_WIKIVOCAB_MAX_RT,
            )
        else:
            rt_acc_pseudo = (nan, nan, 0)
    except ValueError as err:
        # Determine display path for the outer error message
        try:
            psym_dir = settings.PSYCHOMETRIC_TESTS_DIR
            if (
                wv_dir.is_absolute()
                and psym_dir.is_absolute()
                and wv_dir.is_relative_to(psym_dir)
            ):
                display_path = str(wv_dir.relative_to(psym_dir))
            else:
                display_path = wv_dir.name
        except (ValueError, AttributeError):
            display_path = wv_dir.name

        import re

        see_also = ""
        files_checked = re.findall(r"'([^']+)'", str(err))
        if files_checked:
            csv_files = [f for f in files_checked if f.endswith(".csv")]
            if csv_files:
                see_also = f" See '{display_path}/" + "', '".join(csv_files) + "'."

        raise ValueError(
            f"WikiVocab results missing or incomplete in '{display_path}'. "
            f"Please check if the experiment was interrupted or if the data was recorded correctly.{see_also} "
            f"\nDetail: {err}"
        ) from err

    return {
        "WikiVocab_rt_mean_sec": rt_acc[0],
        "WikiVocab_accuracy": rt_acc[1],
        "WikiVocab_num_items": rt_acc[2],
        "WikiVocab_num_pseudo_words": num_pseudo,
        "WikiVocab_num_real_words": num_real,
        "WikiVocab_ratio_items": ratio_items,
        "WikiVocab_incorrect_correct_score": incorrect_correct,
        "WikiVocab_pseudo_correct": pseudo_correct,
        "WikiVocab_real_correct": real_correct,
        "WikiVocab_correct_all_rt_mean_sec": rt_acc_all[0],
        "WikiVocab_correct_words_rt_mean_sec": rt_acc_words[0],
        "WikiVocab_correct_pseudowords_rt_mean_sec": rt_acc_pseudo[0],
    }


def preprocess_plab(plab_dir: Path) -> dict:
    """Preprocess PLAB (Pimsleur Language Aptitude Battery) test CSV data.

    Computes mean reaction time and overall accuracy, as well as split accuracy
    and reaction time for items 1-4 and 5-15.

    **PLAB test**: The PLAB test is Pimsleur Language Aptitude Battery test.
    It is a test of language aptitude that is designed to measure an individual's ability to learn
    a foreign language.

    **Reference**: Paul Pimsleur, D. J. Reed, and C. W. Standfield.
    Pimsleur Language Aptitude Battery: PLAB : Manual.
    Second Language Testing Foundation, North Bethesda, 2004 edition, 2004.

    **Calculation**: Mean RT and overall accuracy across all PLAB trials, and
    for two specific sets of items (1-4 and 5-15).

    Parameters
    ----------
    plab_dir : Path
        Path to the folder containing PLAB test data.

    Returns
    -------
    dict
        A dictionary with 'PLAB_rt_mean_sec', 'PLAB_accuracy', 'PLAB_num_items',
        and split metrics for sets 1 and 2.

    Raises
    ------
    ValueError
        If required results file is missing or malformed.
    """
    try:
        df = _find_one_filetype_with_columns(
            plab_dir, ["rt", "correctness", "question_id"], allow_nan=True
        )
    except ValueError as err:
        # Determine display path for the outer error message
        try:
            psym_dir = settings.PSYCHOMETRIC_TESTS_DIR
            if (
                plab_dir.is_absolute()
                and psym_dir.is_absolute()
                and plab_dir.is_relative_to(psym_dir)
            ):
                display_path = str(plab_dir.relative_to(psym_dir))
            else:
                display_path = plab_dir.name
        except (ValueError, AttributeError):
            display_path = plab_dir.name

        import re

        see_also = ""
        files_checked = re.findall(r"'([^']+)'", str(err))
        if files_checked:
            csv_files = [f for f in files_checked if f.endswith(".csv")]
            if csv_files:
                see_also = f" See '{display_path}/" + "', '".join(csv_files) + "'."

        raise ValueError(
            f"PLAB results missing or incomplete in '{display_path}'. "
            f"Please check if the experiment was interrupted or if the data was recorded correctly.{see_also} "
            f"\nDetail: {err}"
        ) from err

    rt_mean, accuracy, num_items = _reaction_time_accuracy(
        df,
        reaction_time_col="rt",
        correctness_col="correctness",
        min_rt=0.0,
        max_rt=float("inf"),
    )

    # Split accuracy and RT for set 1 (items 1-4) and set 2 (items 5-15)
    df_set1 = df[df["question_id"].isin([1, 2, 3, 4])]
    df_set2 = df[df["question_id"].isin(range(5, 16))]

    rt_set1, acc_set1, _num_set1 = (nan, nan, 0)
    if not df_set1.empty:
        rt_set1, acc_set1, _num_set1 = _reaction_time_accuracy(
            df_set1,
            reaction_time_col="rt",
            correctness_col="correctness",
            min_rt=0.0,
            max_rt=float("inf"),
        )

    rt_set2, acc_set2, _num_set2 = (nan, nan, 0)
    if not df_set2.empty:
        rt_set2, acc_set2, _num_set2 = _reaction_time_accuracy(
            df_set2,
            reaction_time_col="rt",
            correctness_col="correctness",
            min_rt=0.0,
            max_rt=float("inf"),
        )

    return {
        "PLAB_rt_mean_sec": rt_mean,
        "PLAB_accuracy": accuracy,
        "PLAB_num_items": num_items,
        "PLAB_set1_accuracy": acc_set1,
        "PLAB_set2_accuracy": acc_set2,
        "PLAB_set1_rt_mean_sec": rt_set1,
        "PLAB_set2_rt_mean_sec": rt_set2,
    }


def _reaction_time_accuracy(
    df: DataFrame,
    reaction_time_col: str,
    correctness_col: str,
    group_by_col: str | None = None,
    correct_only: bool = False,
    min_rt: float | None = None,
    max_rt: float | None = None,
) -> DataFrame | tuple[float, float, int]:
    """
    Calculate reaction time mean and accuracy, optionally grouped.

    Parameters
    ----------
    df : DataFrame
        DataFrame containing the reaction time and correctness columns.
    reaction_time_col : str
        Column name for reaction time.
    correctness_col : str
        Column name for correctness/accuracy (values must be 0/1 or booleans; NaN allowed).
    group_by_col : str, optional
        Column name to group by for calculating reaction time and accuracy.
        If this is given, the output is a DataFrame with mean reaction time and accuracy
        grouped by the specified column.
    correct_only : bool, optional
        If True, compute reaction time on correct trials only. For grouped outputs,
        reaction time is averaged over correct trials per group, while accuracy is
        still computed as the mean of the correctness column per group. Default False.
    min_rt : float, optional
        Minimum reaction time to include. Trials with RT below this threshold
        are excluded from all calculations (RT mean, accuracy, and num_items).
    max_rt : float, optional
        Maximum reaction time to include. Trials with RT above this threshold
        are excluded from all calculations (RT mean, accuracy, and num_items).

    Returns
    -------
    DataFrame | tuple[float, float, int]
        If ``group_by_col`` is None, returns a tuple of (mean reaction time, accuracy, num_items).
        If ``group_by_col`` is provided, returns a DataFrame indexed by the group values
        with three columns: ``rt_mean``, ``accuracy``, and ``num_items``, where
        num_items shows the number of non-NaN reaction time values per group.

    Raises
    ------
    ValueError
        If required columns are missing, DataFrame is empty, reaction time column
        is not numeric, correctness contains values outside {0,1,True,False,NaN},
        or NaN positions between reaction time and correctness columns do not match.

    Notes
    -----
    - NaN handling: rows with NaN in either reaction time or correctness are
      allowed, but their NaN positions must match to ensure paired calculations.
    - Filtering (min_rt, max_rt): Trials outside the specified range are
      completely removed from the dataset before any calculations.
    """
    if not all(col in df.columns for col in [reaction_time_col, correctness_col]):
        raise ValueError(
            f"DataFrame must contain '{reaction_time_col}' and '{correctness_col}' columns."
        )
    # Validate inputs once
    __validate_rt_acc_inputs(df, reaction_time_col, correctness_col)

    # Filter by RT thresholds if provided
    filtered_df = df.copy()
    if min_rt is not None:
        filtered_df = filtered_df[filtered_df[reaction_time_col] >= min_rt]
    if max_rt is not None:
        filtered_df = filtered_df[filtered_df[reaction_time_col] <= max_rt]

    # Grouped case: vectorised aggregations
    if group_by_col is not None:
        if group_by_col not in filtered_df.columns:
            raise ValueError(
                f"DataFrame must contain group_by column '{group_by_col}'."
            )

        # Get the grouped data
        grouped = filtered_df.groupby(group_by_col, dropna=True)

        # Accuracy per group
        acc = grouped[correctness_col].mean().rename("accuracy")

        # Reaction time per group (optionally only on correct trials)
        if correct_only:
            rt_series = filtered_df[filtered_df[correctness_col] == 1]
            rt = rt_series.groupby(group_by_col, dropna=True)[reaction_time_col].mean()
        else:
            rt = filtered_df.groupby(group_by_col, dropna=True)[
                reaction_time_col
            ].mean()
        rt = rt.rename("rt_mean")

        # Number of items per group
        num_items = grouped[reaction_time_col].count().rename("num_items")

        return rt.to_frame().join([acc, num_items], how="outer")

    # Ungrouped case
    if correct_only:
        rt_mean = filtered_df[filtered_df[correctness_col] == 1][
            reaction_time_col
        ].mean()
    else:
        rt_mean = filtered_df[reaction_time_col].mean()
    accuracy = filtered_df[correctness_col].mean()
    num_items = filtered_df[reaction_time_col].notna().sum()

    return rt_mean, accuracy, num_items


def __validate_rt_acc_inputs(
    df: DataFrame,
    reaction_time_col: str,
    correctness_col: str,
) -> None:
    """Validate inputs for reaction time and accuracy computations.

    Ensures DataFrame is non-empty, NaN positions match between columns,
    reaction time is numeric (allowing NaNs), and correctness contains only
    0/1/True/False/NaN values.
    """
    if df.empty:
        raise ValueError("DataFrame is empty")
    # NaN positions must match between correctness and reaction time
    if df[correctness_col].isna().ne(df[reaction_time_col].isna()).any():
        raise ValueError(
            "NaN positions in correctness and reaction time columns do not match"
        )
    # Reaction time must be numeric dtype (NaNs allowed)
    if df[reaction_time_col].dtype not in ["float64", "float32", "int64", "int32"]:
        raise ValueError("Reaction time column contains non-numeric values")
    # Correctness must be boolean-like (0/1/True/False/NaN)
    if not df[correctness_col].isin([0, 1, True, False, nan]).all():
        raise ValueError("Correctness column contains non-boolean values")


def _find_one_filetype_with_columns(
    folder: Path,
    columns: list[str],
    allow_nan=False,
    base_path: Path | None = None,
    read_all_columns: bool = True,
) -> DataFrame:
    """Find a single CSV file containing specific columns and return it as DataFrame.

    This function searches a specified folder for CSV files and ensures that exactly one file
    contains the specified columns. It returns the file as DataFrame with only the
    specified columns.

    By default it requires all ``columns`` to be present in exactly one CSV file. When
    ``read_all_columns`` is False, a CSV qualifies if it contains at least one of the
    ``columns``. Among the qualifying files the most recently dated one is chosen (files
    are named ``<experiment>_<participant>_<date>_<time>.csv``, so the lexically largest
    name is the most recent run); the number of present columns only breaks ties. Since
    several CSV files in one folder make it ambiguous which run is the actual measurement,
    a warning is logged telling the user to check the lab documentation or ask the
    experimenter.

    Parameters
    ----------
    folder : Path
        Directory to search for the file.
    columns : list[str]
        List of column names that should be present in the CSV.
    allow_nan : bool, optional
        If True, allows NaN values in the ``columns`` asked for. Default is False.
    base_path : Path, optional
        If provided, the folder path in error messages will be relative to this path.
    read_all_columns : bool, optional
        If True (default), the CSV must contain all ``columns``. If False, a CSV qualifies
        when it contains at least one of ``columns`` and only the present subset is returned.

    Returns
    -------
    DataFrame
        DataFrame containing only the specified (and present) columns.

    Raises
    ------
    ValueError
        If no CSV files with the required columns are found.
    ValueError
        If NaN values are found in required columns and ``allow_nan`` is False.
    """
    csvs = list(folder.glob("*.csv"))

    # Determine the folder path to show in error messages
    try:
        if base_path and folder.is_absolute() and base_path.is_absolute():
            display_path = str(folder.relative_to(base_path))
        else:
            # Fallback: if folder is inside settings.PSYCHOMETRIC_TESTS_DIR, use that
            psym_dir = settings.PSYCHOMETRIC_TESTS_DIR
            if (
                folder.is_absolute()
                and psym_dir.is_absolute()
                and folder.is_relative_to(psym_dir)
            ):
                display_path = str(folder.relative_to(psym_dir))
            else:
                display_path = folder.name
    except (ValueError, AttributeError, RuntimeError):
        display_path = folder.name

    if not csvs:
        raise ValueError(f"No CSV files were found in '{display_path}'.")

    valid_csvs = []
    missing_cols_info = {}
    match_count = {}  # csv name -> number of requested columns present (partial mode)
    for csv in csvs:
        # Only read the header to check columns
        try:
            cols_found = read_csv(csv, nrows=0).columns
        except Exception:
            continue
        present = [col for col in columns if col in cols_found]
        missing = [col for col in columns if col not in cols_found]
        if read_all_columns:
            if not missing:
                valid_csvs.append(csv)
            else:
                missing_cols_info[csv.name] = missing
        elif present:
            match_count[csv.name] = len(present)
            valid_csvs.append(csv)

    if not valid_csvs:
        details = ""
        if missing_cols_info:
            details = "\nChecked: " + ", ".join(f"'{f}'" for f in missing_cols_info)
        raise ValueError(
            f"No CSV files with the required columns {columns} were found in '{display_path}'.{details}"
        )

    # With multiple candidate runs it is ambiguous which one reflects the actual
    # measurement, so prefer the most recently dated run. Files are named
    # ``<experiment>_<participant>_<date>_<time>.csv``, so the lexically largest
    # name is the most recent run. In partial mode the number of present columns
    # only breaks ties.
    if read_all_columns:
        chosen = max(valid_csvs, key=lambda c: c.name)
        selected_cols = columns
    else:
        chosen = max(
            valid_csvs,
            key=lambda c: (c.name, match_count.get(c.name, 0)),
        )
        selected_cols = [
            col for col in columns if col in read_csv(chosen, nrows=0).columns
        ]

    if len(valid_csvs) > 1:
        matched_names = sorted(c.name for c in valid_csvs)
        get_logger(__name__).warning(
            "Multiple CSV files with data were found in '%s': %s. "
            "It is ambiguous which one reflects the actual run. Using the "
            "most recent one: '%s'. Please check the lab session documentation "
            "or ask the experimenter which file is correct.",
            display_path,
            ", ".join(matched_names),
            chosen.name,
        )

    df = read_csv(chosen, usecols=selected_cols)
    if df.empty:
        raise ValueError(
            f"The data file '{chosen.name}' was found but contains no data rows."
        )

    if not allow_nan and df.isna().any().any():
        nan_cols = df.columns[df.isna().any()].tolist()
        raise ValueError(
            f"Required columns {nan_cols} in '{chosen.name}' contain missing values (NaN)."
        )
    return df

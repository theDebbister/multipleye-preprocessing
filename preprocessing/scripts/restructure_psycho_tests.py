"""Utility script to restructure psychometric tests data folders."""

import argparse
import shutil
from pathlib import Path

import yaml

from preprocessing import settings
from preprocessing.models.sid import Sid
from preprocessing.utils import get_logger, validate_psychometric_data

logger = get_logger()


def fix_psycho_tests_structure(
    config_folder: Path | None = None,
    data_folder: Path | None = None,
    out_folder: Path | None = None,
):
    if config_folder is None:
        config_folder = settings.PSYM_PARTICIPANT_CONFIGS
    if data_folder is None:
        data_folder = settings.PSYM_CORE_DATA
    if out_folder is None:
        out_folder = settings.PSYCHOMETRIC_TESTS_DIR
    """
    Restructures psychometric tests data into per-participant folders.

    This function processes configuration files in the `config_folder` and data directories within
    `data_folder`.
    It identifies tests, organises each participant's test data based on the configuration,
    and relocates data to a per-participant directory format in the `out_folder`.

    The test data and config files are *moved* (not copied) into the session folders.
    After the restructuring succeeds, the now-empty task-first source folders are removed
    so the original structure does not remain as a duplicate.

    Parameters
    ----------
    config_folder : Path
        The folder containing configuration files (.yaml) for the psychometric tests.
        (default: config.PSYM_PARTICIPANT_CONFIGS)
    data_folder : Path
        The folder containing raw test data for participants.
        The data is assumed to be structured with subfolders for each test type.
        (default: config.PSYM_CORE_DATA)
    out_folder : Path
        Session folder where the restructured data / user folders will be saved.
        If not provided, defaults to the folder specified in the config.
        (default: config.PSYCHOMETRIC_TESTS_DIR)

    Notes
    -----
    1. The function identifies participants and their corresponding session data based on the file
       naming convention in the `config_folder`.
    2. Configurations ending with specific session markers ('S1', 'S2')
       are transformed into specific folder names ('PT1', 'PT2') to create session directories.
    3. Any missing tests for a participant are logged to the console.
    4. Session data that has no matching participant config is still moved into a session-first
       folder (no config YAML is generated), and a warning lists every such session.
    5. Data in test roots that are not part of the psychometric test mapping (e.g. 'WCST')
       is left in place in the source and logged as a warning. The source folder is only
       removed once it is fully empty.

    Raises
    ------
    TypeError:
        If `config_folder`, `data_folder`, or `out_folder` are not of type `Path`.
    FileNotFoundError:
        If `config_folder` or `data_folder` do not exist.
    """

    # Check that the folders are of type Path
    if not isinstance(config_folder, Path):
        raise TypeError("config_folder must be of type Path.")
    if not isinstance(data_folder, Path):
        raise TypeError("data_folder must be of type Path.")
    if not isinstance(out_folder, Path):
        raise TypeError("out_folder must be of type Path.")

    # Check that the folders exist
    if not config_folder.exists():
        msg = f"config_folder does not exist: {config_folder}"
        # try to look for zip files in the parent directory
        # (psychometric-tests-sessions/ instead of psychometric-tests-sessions/core_data/...)
        zip_search_path = config_folder.parent.parent
        if zip_search_path.exists():
            zip_files = list(zip_search_path.glob("*.zip"))
            if zip_files:
                zip_names = [f.name for f in zip_files]
                msg += f"\nFound zip files in {zip_search_path}: {zip_names}. Find out if these zips include the desired data and unzip them."
        raise FileNotFoundError(msg)
    if not data_folder.exists():
        raise FileNotFoundError(f"data_folder does not exist: {data_folder}")

    # Create out folder if it does not exist
    if not out_folder.exists():
        out_folder.mkdir(parents=True)

    # Find config files
    config_files = list(config_folder.glob("*.yaml"))
    # Without any config files there is nothing to restructure unless there is
    # session data present that can be adopted regardless of a config.
    if not config_files and not _has_adoptable_data(data_folder):
        raise ValueError(f"No configuration files ('*.yaml') found in {config_folder}.")

    for config_file in config_files:
        # Check if there is a corresponding data file
        name = config_file.stem

        with open(config_file) as f:
            try:
                yaml.safe_load(f)
            except yaml.YAMLError as exc:
                logger.error(f"Error reading configuration file {config_file}: {exc}")
                continue

        target_name = _normalize_session_name(name)

        session_folder = out_folder / target_name
        session_folder.mkdir(parents=True, exist_ok=True)

        # Use Sid for robust matching of source data
        try:
            config_sid = Sid(name)
        except (ValueError, TypeError):
            config_sid = None

        _move_session_data(session_folder, data_folder, name, config_sid)

        # move the config file to the new session folder
        new_config_path = session_folder / config_file.name
        shutil.move(str(config_file), str(new_config_path))

    # Adopt any remaining session data that has no participant config.
    _adopt_orphan_data(data_folder, out_folder)

    # Run validation after restructuring
    validate_psychometric_data(config_folder, out_folder, is_restructured=True)

    # Clean up the now-empty task-first source structure.
    _cleanup_source_after_restructure(config_folder, data_folder)


def _normalize_session_name(name: str) -> str:
    """Return the session-first folder name for *name*, normalizing S to PT.

    Non-SID-compliant names are returned unchanged so the source folder name is
    preserved verbatim.
    """
    try:
        config_sid = Sid(name)
        target_sid = Sid(
            pid=config_sid.pid,
            lang=config_sid.lang,
            country=config_sid.country,
            lab=config_sid.lab,
            session=config_sid.session.replace("S", "PT")
            if config_sid.session.startswith("S")
            else config_sid.session,
            postfix=config_sid.postfix,
        )
        return str(target_sid)
    except (ValueError, TypeError):
        return name


def _move_session_data(
    session_folder: Path, data_folder: Path, name: str, config_sid: Sid | None
) -> None:
    """Move all of a session's test data into its session-first folder."""
    for folder_name in settings.PSYCHOMETRIC_TEST_MAPPING.values():
        # Try exact match first
        old_path = data_folder / folder_name / name

        # If not found and it's a valid SID, try soft matching
        if not old_path.exists() and config_sid:
            test_type_dir = data_folder / folder_name
            if test_type_dir.exists():
                for potential_dir in test_type_dir.iterdir():
                    if potential_dir.is_dir():
                        try:
                            folder_sid = Sid(potential_dir.name)
                            if config_sid.equals_soft(folder_sid):
                                old_path = potential_dir
                                break
                        except (ValueError, TypeError):
                            continue

        # We move the data if it actually exists
        if old_path.exists():
            new_test_path = session_folder / folder_name
            new_test_path.mkdir(parents=True, exist_ok=True)
            _move_merge(old_path, new_test_path)


def _adopt_orphan_data(data_folder: Path, out_folder: Path) -> None:
    """Move session data that has no participant config into session-first folders.

    Collects the per-test subfolders still present in the task-first source after the
    config-driven restructure, groups them by soft-equal session SID, and moves each
    group into a session-first folder. No participant config YAML is generated; the
    session is processed later based on whatever data is available.

    A single warning is emitted listing every session whose config is missing.
    """
    test_folders = list(settings.PSYCHOMETRIC_TEST_MAPPING.values())
    if not data_folder.exists():
        return

    # Normalized session name -> {test folder name: source path}
    orphans: dict[str, dict[str, Path]] = {}

    for test_name in test_folders:
        test_root = data_folder / test_name
        if not test_root.is_dir():
            continue
        for potential_dir in test_root.iterdir():
            if not potential_dir.is_dir():
                continue
            target = _normalize_session_name(potential_dir.name)
            orphans.setdefault(target, {}).setdefault(test_name, potential_dir)

    if not orphans:
        return

    for target_name, test_sources in sorted(orphans.items()):
        session_folder = out_folder / target_name
        session_folder.mkdir(parents=True, exist_ok=True)
        for test_name, src in test_sources.items():
            dst = session_folder / test_name
            dst.mkdir(parents=True, exist_ok=True)
            _move_merge(src, dst)

    missing = sorted(orphans)
    logger.warning(
        f"No participant config for {len(missing)} session(s); "
        f"restructured data anyway (no config generated): {missing}"
    )


def _has_adoptable_data(data_folder: Path) -> bool:
    """Return True if any mapped test root still contains session data to adopt."""
    if not data_folder.exists():
        return False
    for test_name in settings.PSYCHOMETRIC_TEST_MAPPING.values():
        test_root = data_folder / test_name
        if test_root.is_dir() and any(test_root.iterdir()):
            return True
    return False


def _move_merge(src: Path, dst: Path) -> None:
    """Move *src* into *dst*, merging when *dst* already exists."""
    if not dst.exists():
        shutil.move(str(src), str(dst))
        return
    for item in src.iterdir():
        shutil.move(str(item), str(dst))
    shutil.rmtree(src)


def _cleanup_source_after_restructure(config_folder: Path, data_folder: Path) -> None:
    """Remove the source task-first folders after a successful restructure.

    Participant configs and mapped test data are moved (not copied) during the restructure,
    so the original task-first folders only remain where data could not be moved (for example
    test roots that are not part of the psychometric test mapping, or non-SID-compliant
    folders). Empty folders are removed so the legacy source structure does not stay around
    as a duplicate; anything left over is logged as a warning.
    """
    removed: list[Path] = []

    if config_folder.exists():
        leftovers = list(config_folder.iterdir())
        if not leftovers:
            shutil.rmtree(config_folder)
            removed.append(config_folder)
        else:
            logger.warning(
                f"Leftover files (not matched to a session config) kept in {config_folder}: "
                f"{[p.name for p in leftovers]}"
            )

    if data_folder.exists():
        for test_root in sorted(
            data_folder.iterdir(), key=lambda p: p.name, reverse=True
        ):
            if not test_root.is_dir():
                continue
            entries = list(test_root.iterdir())
            if not entries:
                shutil.rmtree(test_root)
                removed.append(test_root)
            else:
                leftover_names = sorted(p.name for p in entries)
                logger.warning(
                    f"Unmoved data (not part of the psychometric test mapping) kept in "
                    f"{test_root}: {leftover_names}"
                )
        if not any(data_folder.iterdir()):
            shutil.rmtree(data_folder)
            removed.append(data_folder)

    if removed:
        logger.info(
            "Removed from source after restructure: "
            + ", ".join(str(p) for p in removed)
        )


def main():
    parser = argparse.ArgumentParser(
        description="Fix the structure of psychometric tests in a data collection folder."
    )
    parser.add_argument(
        "--config_folder",
        type=str,
        help="Path to the folder containing the psychometric tests configuration files.",
        default=None,
    )
    parser.add_argument(
        "--data_folder",
        type=str,
        help="Path to the folder containing the data collection.",
        default=None,
    )
    parser.add_argument(
        "--out_folder",
        type=str,
        help="Path to the session folder where the restructured data / user folders will be saved.",
        default=None,
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only run sanity checks without restructuring data.",
    )
    parser.add_argument(
        "--restructured",
        action="store_true",
        help="Run sanity checks assuming data is already restructured.",
    )
    args = parser.parse_args()

    config_p = Path(args.config_folder) if args.config_folder else None
    data_p = Path(args.data_folder) if args.data_folder else None
    out_p = Path(args.out_folder) if args.out_folder else None

    from preprocessing import settings

    if config_p is None:
        config_p = settings.PSYM_PARTICIPANT_CONFIGS
    if data_p is None:
        data_p = settings.PSYM_CORE_DATA
    if out_p is None:
        out_p = settings.PSYCHOMETRIC_TESTS_DIR

    if args.check_only:
        print(f"Running sanity check on data: {data_p} with configs: {config_p}")
        validate_psychometric_data(config_p, data_p, is_restructured=args.restructured)
        return

    print(
        f"Restructuring psychometric tests data from \ndata_folder: {data_p}\n"
        f"to out_folder: {out_p}\nwith config_folder: {config_p}"
    )

    fix_psycho_tests_structure(config_p, data_p, out_p)

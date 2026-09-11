from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

from .models.dcn import Dcn

TEMPLATE_DOCS_URL = (
    "https://multipleye-cost.github.io/multipleye-preprocessing/guide/configuration/"
)
TEMPLATE_RELATIVE_PATH = Path(
    "templates_and_notes/multipleye_settings_preprocessing.template.yaml"
)

logger = logging.getLogger(__name__)
package_logger = logging.getLogger("preprocessing")


class Settings:
    """Settings for MultiplEYE preprocessing pipeline."""

    def __init__(self) -> None:
        # These settings can be overridden by a YAML file.

        self._init_defaults()
        self._repo_root = Path(__file__).parent.parent
        self._initialized = True
        self._is_template_loaded = False
        self._is_auto_filled = False
        self._config_found = False
        self._config_source: Path | None = None

    @property
    def DATA_COLLECTION_NAME(self) -> str | None:
        self._ensure_loaded()
        return self.__dict__.get("DATA_COLLECTION_NAME")

    @DATA_COLLECTION_NAME.setter
    def DATA_COLLECTION_NAME(self, value: str | None) -> None:
        self.__dict__["DATA_COLLECTION_NAME"] = value

    @property
    def DATASET_DIR(self) -> Path:
        """The directory where raw data is stored."""
        if "DATASET_DIR" in self.__dict__:
            return self.__dict__["DATASET_DIR"]
        self._ensure_loaded()
        return self._repo_root / "data" / (self.DATA_COLLECTION_NAME or "")

    @DATASET_DIR.setter
    def DATASET_DIR(self, value: Path | str) -> None:
        self.__dict__["DATASET_DIR"] = Path(value)

    @property
    def OUTPUT_DIR(self) -> Path:
        """The directory where preprocessed data is stored."""
        if "OUTPUT_DIR" in self.__dict__:
            return self.__dict__["OUTPUT_DIR"]
        self._ensure_loaded()
        return self._repo_root / "preprocessed_data" / (self.DATA_COLLECTION_NAME or "")

    @OUTPUT_DIR.setter
    def OUTPUT_DIR(self, value: Path | str) -> None:
        self.__dict__["OUTPUT_DIR"] = Path(value)

    @property
    def _dcn(self) -> Dcn | None:
        """Get the Dcn model instance."""
        name = self.DATA_COLLECTION_NAME
        if name and Dcn.is_valid(name):
            return Dcn(name)
        return None

    @property
    def LANGUAGE(self) -> str:
        """The language code from the data collection name."""
        if "LANGUAGE" in self.__dict__:
            return self.__dict__["LANGUAGE"]
        return self._dcn.lang if self._dcn else ""

    @LANGUAGE.setter
    def LANGUAGE(self, value: str) -> None:
        self.__dict__["LANGUAGE"] = value

    @property
    def COUNTRY(self) -> str:
        """The country code from the data collection name."""
        if "COUNTRY" in self.__dict__:
            return self.__dict__["COUNTRY"]
        return self._dcn.country if self._dcn else ""

    @COUNTRY.setter
    def COUNTRY(self, value: str) -> None:
        self.__dict__["COUNTRY"] = value

    @property
    def CITY(self) -> str:
        """The city name from the data collection name."""
        if "CITY" in self.__dict__:
            return self.__dict__["CITY"]
        return self._dcn.city if self._dcn else ""

    @CITY.setter
    def CITY(self, value: str) -> None:
        self.__dict__["CITY"] = value

    @property
    def LAB(self) -> str:
        """The lab identifier from the data collection name."""
        if "LAB" in self.__dict__:
            return self.__dict__["LAB"]
        return self._dcn.lab if self._dcn else ""

    @LAB.setter
    def LAB(self, value: str) -> None:
        self.__dict__["LAB"] = value

    @property
    def YEAR(self) -> str:
        """The year from the data collection name."""
        if "YEAR" in self.__dict__:
            return self.__dict__["YEAR"]
        return self._dcn.year if self._dcn else ""

    @YEAR.setter
    def YEAR(self, value: str) -> None:
        self.__dict__["YEAR"] = value

    @property
    def COPY_AOI_IMAGES_OVERLAY(self) -> bool:
        """Whether to copy AOI images overlay to the output directory."""
        self._ensure_loaded()
        return self.__dict__.get("COPY_AOI_IMAGES_OVERLAY", False)

    @COPY_AOI_IMAGES_OVERLAY.setter
    def COPY_AOI_IMAGES_OVERLAY(self, value: bool) -> None:
        self.__dict__["COPY_AOI_IMAGES_OVERLAY"] = value

    @property
    def PLOT_AOI_OVERLAY(self) -> bool:
        """Whether to use AOI overlay or only stimulus images for plotting."""
        self._ensure_loaded()
        return self.__dict__.get("PLOT_AOI_OVERLAY", False)

    @PLOT_AOI_OVERLAY.setter
    def PLOT_AOI_OVERLAY(self, value: bool) -> None:
        self.__dict__["PLOT_AOI_OVERLAY"] = value

    @property
    def PSYCHOMETRIC_TESTS_DIR(self) -> Path:
        """The directory for psychometric test sessions (input, session-first)."""
        if "PSYCHOMETRIC_TESTS_DIR" in self.__dict__:
            return self.__dict__["PSYCHOMETRIC_TESTS_DIR"]
        return self.DATASET_DIR / "psychometric-tests-sessions"

    @PSYCHOMETRIC_TESTS_DIR.setter
    def PSYCHOMETRIC_TESTS_DIR(self, value: Path | str) -> None:
        self.__dict__["PSYCHOMETRIC_TESTS_DIR"] = Path(value)

    @property
    def PSYM_CORE_DATA(self) -> Path:
        """The directory for raw psychometric data (task-first, input)."""
        if "PSYM_CORE_DATA" in self.__dict__:
            return self.__dict__["PSYM_CORE_DATA"]
        return self.PSYCHOMETRIC_TESTS_DIR / "core_data"

    @PSYM_CORE_DATA.setter
    def PSYM_CORE_DATA(self, value: Path | str) -> None:
        self.__dict__["PSYM_CORE_DATA"] = Path(value)

    @property
    def PSYM_PARTICIPANT_CONFIGS(self) -> Path:
        """The directory for participant configurations."""
        if "PSYM_PARTICIPANT_CONFIGS" in self.__dict__:
            return self.__dict__["PSYM_PARTICIPANT_CONFIGS"]
        return (
            self.PSYM_CORE_DATA
            / f"participant_configs_{self.LANGUAGE}_{self.COUNTRY}_{self.LAB}"
        )

    @PSYM_PARTICIPANT_CONFIGS.setter
    def PSYM_PARTICIPANT_CONFIGS(self, value: Path | str) -> None:
        self.__dict__["PSYM_PARTICIPANT_CONFIGS"] = Path(value)

    @property
    def START_RECORDING_REGEX(self) -> re.Pattern:
        """Regex to identify the start of a recording."""
        if "START_RECORDING_REGEX" in self.__dict__:
            return self.__dict__["START_RECORDING_REGEX"]
        # Use placeholders for trial and page column names to satisfy static analysis
        pattern = (
            r"(?P<type>start_recording)_"
            rf"(?P<{self.TRIAL_COL}>(PRACTICE_)?trial_\d\d?)_"
            rf"stimulus_(?P<stimulus_name>\S+?)_(?P<stimulus_id>\d+)_(?P<{self.PAGE_COL}>\S+)"
        )
        return re.compile(pattern)

    @START_RECORDING_REGEX.setter
    def START_RECORDING_REGEX(self, value: re.Pattern | str) -> None:
        if isinstance(value, str):
            self.__dict__["START_RECORDING_REGEX"] = re.compile(value)
        else:
            self.__dict__["START_RECORDING_REGEX"] = value

    @property
    def STOP_RECORDING_REGEX(self) -> re.Pattern:
        """Regex to identify the stop of a recording."""
        if "STOP_RECORDING_REGEX" in self.__dict__:
            return self.__dict__["STOP_RECORDING_REGEX"]
        pattern = (
            r"(?P<type>stop_recording)_"
            rf"(?P<{self.TRIAL_COL}>(PRACTICE_)?trial_\d\d?)_"
            r"stimulus_(?P<stimulus_name>\S+?)_"
            rf"(?P<stimulus_id>\d+)_(?P<{self.PAGE_COL}>\S+)"
        )
        return re.compile(pattern)

    @STOP_RECORDING_REGEX.setter
    def STOP_RECORDING_REGEX(self, value: re.Pattern | str) -> None:
        if isinstance(value, str):
            self.__dict__["STOP_RECORDING_REGEX"] = re.compile(value)
        else:
            self.__dict__["STOP_RECORDING_REGEX"] = value

    @property
    def RAW_DATA_FILENAME_REGEX(self) -> str:
        """Regex to extract info from raw data filenames."""
        if "RAW_DATA_FILENAME_REGEX" in self.__dict__:
            return self.__dict__["RAW_DATA_FILENAME_REGEX"]
        trial_col = self.TRIAL_COL
        stimulus_col = self.STIMULUS_COL
        return rf".*?(?P<{trial_col}>(?:PRACTICE_)?trial_\d+)_(?P<{stimulus_col}>[^_]+_[^_]+_\d+(?:\.0)?)_raw_data"

    @RAW_DATA_FILENAME_REGEX.setter
    def RAW_DATA_FILENAME_REGEX(self, value: str) -> None:
        self.__dict__["RAW_DATA_FILENAME_REGEX"] = value

    @property
    def EVENT_DATA_FILENAME_REGEX(self) -> str:
        """Regex to extract info from event data filenames."""
        if "EVENT_DATA_FILENAME_REGEX" in self.__dict__:
            return self.__dict__["EVENT_DATA_FILENAME_REGEX"]
        trial_col = self.TRIAL_COL
        stimulus_col = self.STIMULUS_COL
        return rf".*?(?P<{trial_col}>(?:PRACTICE_)?trial_\d+)_(?P<{stimulus_col}>[^_]+_[^_]+_\d+(?:\.0)?)_{{event_type}}.csv"

    @EVENT_DATA_FILENAME_REGEX.setter
    def EVENT_DATA_FILENAME_REGEX(self, value: str) -> None:
        self.__dict__["EVENT_DATA_FILENAME_REGEX"] = value

    @property
    def SCANPATH_FILENAME_REGEX(self) -> str:
        """Regex to extract info from scanpath data filenames."""
        if "SCANPATH_FILENAME_REGEX" in self.__dict__:
            return self.__dict__["SCANPATH_FILENAME_REGEX"]
        trial_col = self.TRIAL_COL
        stimulus_col = self.STIMULUS_COL
        return rf".+?(?P<{trial_col}>(?:PRACTICE_)?trial_\d+)_(?P<{stimulus_col}>[^_]+_[^_]+_\d+(\.0)?)_scanpath.csv"

    @SCANPATH_FILENAME_REGEX.setter
    def SCANPATH_FILENAME_REGEX(self, value: str) -> None:
        self.__dict__["SCANPATH_FILENAME_REGEX"] = value

    @property
    def READING_MEASURES_FILENAME_REGEX(self) -> str:
        """Regex to extract trial and stimulus info from reading measures filenames."""
        if "READING_MEASURES_FILENAME_REGEX" in self.__dict__:
            return self.__dict__["READING_MEASURES_FILENAME_REGEX"]
        return r".*?(?P<trial>(?:PRACTICE_)?trial_\d+)_(?P<stimulus>.+)_reading_measures\.csv"

    @READING_MEASURES_FILENAME_REGEX.setter
    def READING_MEASURES_FILENAME_REGEX(self, value: str) -> None:
        self.__dict__["READING_MEASURES_FILENAME_REGEX"] = value

    @property
    def GAZE_PATTERNS(self) -> list[Any]:
        """Patterns used by pymovements to parse ASC files."""
        if "GAZE_PATTERNS" in self.__dict__:
            return self.__dict__["GAZE_PATTERNS"]
        trial_col = self.TRIAL_COL
        stimulus_col = self.STIMULUS_COL
        page_col = self.PAGE_COL
        return [
            rf"start_recording_(?P<{trial_col}>(?:PRACTICE_)?trial_\d+)_stimulus_(?P<{stimulus_col}>[^_]+_[^_]+_\d+(\.0)?)_(?P<{page_col}>.+)",
            rf"start_recording_(?P<{trial_col}>(?:PRACTICE_)?trial_\d+)_(?P<{page_col}>familiarity_rating_screen_\d+|subject_difficulty_screen)",
            {"pattern": r"stop_recording_", "column": trial_col, "value": None},
            {"pattern": r"stop_recording_", "column": page_col, "value": None},
            {
                "pattern": self.READING_ACTIVITY_PATTERN,
                "column": self.ACTIVITY_COL,
                "value": "reading",
            },
            {
                "pattern": self.QUESTION_ACTIVITY_PATTERN,
                "column": self.ACTIVITY_COL,
                "value": "question",
            },
            {
                "pattern": self.RATING_ACTIVITY_PATTERN,
                "column": self.ACTIVITY_COL,
                "value": "rating",
            },
            {"pattern": r"stop_recording_", "column": self.ACTIVITY_COL, "value": None},
            {
                "pattern": r"start_recording_PRACTICE_trial_",
                "column": self.PRACTICE_COL,
                "value": True,
            },
            {
                "pattern": r"start_recording_trial_",
                "column": self.PRACTICE_COL,
                "value": False,
            },
            {"pattern": r"stop_recording_", "column": self.PRACTICE_COL, "value": None},
        ]

    @GAZE_PATTERNS.setter
    def GAZE_PATTERNS(self, value: list[Any]) -> None:
        self.__dict__["GAZE_PATTERNS"] = value

    def _init_defaults(self) -> None:
        #: Name of the data collection (e.g., 'ME_EN_UK_LON_LAB1_2025').
        self.DATA_COLLECTION_NAME: str | None = None

        #: Whether to enable development mode.
        self.DEVELOPMENT: bool = False

        #: Whether to include sessions from the pilot folder.
        self.INCLUDE_PILOTS: bool = False

        #: Whether to copy AOI images overlay to the output directory.
        self.COPY_AOI_IMAGES_OVERLAY: bool = False

        #: Whether to use AOI overlay or only stimulus images for plotting.
        self.PLOT_AOI_OVERLAY: bool = False

        #:
        self.EXPERIMENT_TYPE: str = ""

        # Defines whether written files will be recalculated, if they already exist.
        # If False, preprocessed sessions will be skipped and not reprocessed.
        # If only some files for a session exist, the user has to select recalculate once
        # to avoid having files stemming from different versions.
        self.RECALCULATE = False

        #: List of session identifiers to explicitly exclude from processing.
        self.EXCLUDE_SESSIONS: list[str] = []

        #: List of session identifiers to explicitly include. If not empty, only these are processed.
        self.INCLUDE_SESSIONS: list[str] = []

        #: Default log level for the package/Python.
        self.LOG_LEVEL: str = "INFO"

        #: Log level for the console output.
        self.CONSOLE_LOG_LEVEL: str = "INFO"

        #: Log level for the file output.
        self.FILE_LOG_LEVEL: str = "DEBUG"

        #: Log level for warnings capture.
        self.WARNINGS_CAPTURE_LEVEL = logging.WARNING

        #: List of regex patterns to ignore in log messages.
        self.IGNORED_LOG_REGEXES: list[str] = [
            r"Could not determine dtype for column \d+, falling back to string",
        ]

        #: List of folder names to ignore when scanning for session folders.
        self.IGNORED_SESSION_FOLDERS: list[str] = [
            "test_sessions",
            "core_sessions",
            "pilot_sessions",
        ]

        #: Append to existing log files instead of overwriting.
        self.APPEND_LOGS: bool = False

        #: Force recalculation of ASC files even if they already exist in the output folder.
        self.FORCE_RECONVERT_ASC: bool = False

        #: The expected sampling rate of the eye tracker in Hertz.
        self.EXPECTED_SAMPLING_RATE_HZ: int = 1000

        # --- CONSTANTS FOR EXPERIMENT ---

        #: Expected number of practice trials.
        self.NUM_PRACTICE_TRIALS = 2

        #: Expected minimum number of experimental trials.
        self.NUM_TRIALS = 12

        #: Expected number of questions for experimental stimuli.
        self.NUM_QUESTIONS_EXPERIMENT = 6

        #: Expected number of questions for practice stimuli.
        self.NUM_QUESTIONS_PRACTICE = 2

        #: Number of versions of stimuli orders and question versions
        self.NUM_STIMULUS_ORDER_VERSIONS = 250

        # --- FOLDER AND FILE NAMES ---

        #: Columns that uniquely identify a trial.
        self.TRIAL_COLS = ["trial", "stimulus", "page"]

        #: Subfolder name for raw data.
        self.RAW_DATA_FOLDER = Path("raw_data/")

        #: Subfolder name for ASC files.
        self.ASC_FOLDER = Path("asc/")

        #: Subfolder name for fixation data.
        self.FIXATIONS_FOLDER = Path("fixations/")

        #: Subfolder name for saccade data.
        self.SACCADES_FOLDER = Path("saccades/")

        #: Subfolder name for scanpath data.
        self.SCANPATHS_FOLDER = Path("scanpaths/")

        #: Subfolder name for reading measures data
        self.READING_MEASURES_FOLDER = Path("reading_measures/")

        #: Subfolder name for sanity checks data.
        self.SANITY_CHECKS_FOLDER = Path("sanity_checks/")

        #: Subfolder name for metadata files.
        self.METADATA_FOLDER = Path("metadata/")

        #: Subfolder name for comprehension question answers.
        self.ANSWERS_FOLDER = Path("comp_answers/")

        #: Subfolder name for psychometric tests output (overview + detailed CSVs).
        self.PSYCHOMETRIC_TESTS_FOLDER = Path("psychometric_tests/")

        #: Regex patterns for ASC messages used during the experiment
        #: (recording start/stop, breaks, screens, comprehension answers).
        self.EXPERIMENT_MSG_PATTERNS = [
            r"start_recording_.*",
            r"stop_recording_.*",
            r"(optional|obligatory)_break.*",
            r"welcome_screen",
            r"informed_consent_screen",
            r"start_experiment",
            r"stimulus_order_version",
            r"showing_instruction_screen",
            r"showing_subject_difficulty_screen",
            r"showing_familiarity_rating_screen_\d+",
            r"camera_setup_screen",
            r"practice_text_starting_screen",
            r"transition_screen",
            r"final_validation",
            r"validation_before_stimulus",
            r"show_final_screen",
            r"optional_break_screen",
            r"fixation_trigger:.*",
            r"recalibration",
            r"empty_screen",
            r"screen_image_onset",
            r"screen_image_offset",
            r".*_preliminary_answer_.*",
            r"question_screen_image_offset",
            r".*_final_answer_given_is_.*",
            r".*_answer_given_is_correct:.*",
        ]

        # --- PIPELINE STAGES ---
        #: Whether to run the preflight input file check before processing.
        self.RUN_PREFLIGHT_CHECK = True
        #: Whether to perform fixation detection.
        self.RUN_FIXATION_DETECTION = True
        #: Whether to perform saccade detection.
        self.RUN_SACCADE_DETECTION = True
        #: Whether to perform reading measures calculation.
        self.RUN_READING_MEASURES = True
        #: Whether to collect comprehension question answers.
        self.RUN_COMPREHENSION_ANSWERS = True
        #: Whether to create sanity check reports.
        self.RUN_SANITY_CHECKS = True
        #: Whether to process psychometric tests.
        self.RUN_PSYCHOMETRIC_TESTS = True

        #: Column name for the trial identifier.
        self.TRIAL_COL = "trial"

        #: Column name for the page identifier.
        self.PAGE_COL = "page"

        #: Column name for the stimulus identifier.
        self.STIMULUS_COL = "stimulus"

        #: Column name for the word index.
        self.WORD_IDX_COL = "word_idx"

        #: Column name for the character index.
        self.CHAR_IDX_COL = "char_idx"

        # --- SANITY CHECK THRESHOLDS ---

        #: Acceptable range [min, max] for the number of calibrations in a session.
        self.ACCEPTABLE_NUM_CALIBRATIONS = [3, 30]

        #: Acceptable range (min, max) for the number of validations in a session.
        self.ACCEPTABLE_NUM_VALIDATION = (12, 30)

        #: Acceptable range (min, max) for average validation accuracy scores.
        self.ACCEPTABLE_AVG_VALIDATION_SCORES = (0.0, 0.8)

        #: Acceptable range (min, max) for maximum validation accuracy scores.
        self.ACCEPTABLE_MAX_VALIDATION_SCORES = (0.0, 1.5)

        #: Single validation classification — scores below this are GOOD.
        self.SINGLE_VALIDATION_GOOD_MAX = 0.305

        #: Single validation classification — scores below this are MODERATE (≥ GOOD_MAX, < this is MODERATE).
        self.SINGLE_VALIDATION_MODERATE_MAX = 0.45

        #: Mapping from YAML config flags to folder names for psychometric tests.
        self.PSYCHOMETRIC_TEST_MAPPING = {
            "plab": "PLAB",
            "ran": "RAN",
            "stroop_flanker": "Stroop_Flanker",
            "wmc": "WMC",
            "wiki_vocab": "WikiVocab",
        }

        #: List of acceptable validation error strings.
        self.ACCEPTABLE_VALIDATION_ERRORS = ["GOOD"]

        #: Acceptable range (min, max) for data loss ratio (0.0 to 1.0).
        self.ACCEPTABLE_DATA_LOSS_RATIOS = (0.0, 0.10)

        #: Acceptable range (min, max) for recording duration in seconds.
        self.ACCEPTABLE_RECORDING_DURATIONS = (600, 7200)

        #: Expected number of practice trials.
        self.ACCEPTABLE_NUM_PRACTICE_TRIALS = 2

        #: Expected minimum number of experimental trials.
        self.ACCEPTABLE_NUM_TRIALS = 10

        #: Minimum number of completed trials before a session is considered complete.
        #: MultiplEYE full session = 12, MeRID split = 6, crash = <6.
        self.ACCEPTABLE_NUM_COMPLETED_TRIALS = 6

        #: Column name for the activity identifier.
        self.ACTIVITY_COL = "activity"

        #: Column name for the practice flag.
        self.PRACTICE_COL = "practice"

        #: Prefix for page names.
        self.PAGE_PREFIX = "page_"

        #: Prefix for question names.
        self.QUESTION_PREFIX = "question_"

        #: Pattern for reading activity.
        self.READING_ACTIVITY_PATTERN = r"start_recording_(?:PRACTICE_)?trial_\d+_stimulus_[^_]+_[^_]+_\d+(\.0)?_page_\d+"

        #: Pattern for question activity.
        self.QUESTION_ACTIVITY_PATTERN = r"start_recording_(?:PRACTICE_)?trial_\d+_stimulus_[^_]+_[^_]+_\d+(\.0)?_question_\d+"

        #: Pattern for rating activity.
        self.RATING_ACTIVITY_PATTERN = r"start_recording_(?:PRACTICE_)?trial_\d+_(familiarity_rating_screen_\d+|subject_difficulty_screen)"

        # --- DATA CHARACTERISTICS ---

        #: Labels used for eye tracking.
        self.TRACKED_EYE = ["L", "R", "RIGHT", "LEFT"]

        #: Event name for fixations.
        self.FIXATION = "fixation"

        #: Event name for saccades.
        self.SACCADE = "saccade"

        # --- PSYCHOMETRIC TEST THRESHOLDS ---

        #: Minimum reaction time for WikiVocab in seconds.
        self.PSYM_WIKIVOCAB_MIN_RT = 0.2

        #: Maximum reaction time for WikiVocab in seconds.
        self.PSYM_WIKIVOCAB_MAX_RT = float("inf")

        #: Minimum reaction time for Stroop in seconds.
        self.PSYM_STROOP_MIN_RT = 0.2

        #: Maximum reaction time for Stroop in seconds.
        self.PSYM_STROOP_MAX_RT = float("inf")

        #: Minimum reaction time for Flanker in seconds.
        self.PSYM_FLANKER_MIN_RT = 0.0

        #: Maximum reaction time for Flanker in seconds.
        self.PSYM_FLANKER_MAX_RT = float("inf")

        # --- REGULAR EXPRESSIONS ---

        #: Regex to parse generic messages from eye tracker logs.
        self.MESSAGE_REGEX = re.compile(
            r"MSG\s+(?P<timestamp>\d+[.]?\d*)\s+(?P<message>.*)"
        )

        #: Glob pattern for raw data files.
        self.RAW_DATA_FILE_GLOB = "*_raw_data.csv"

        #: Glob pattern for event data files.
        self.EVENT_DATA_FILE_GLOB = "*_{event_type}.csv"

        #: Glob pattern for scanpath files.
        self.SCANPATH_FILE_GLOB = "*_scanpath.csv"

        #: Glob pattern for reading measures files.
        self.READING_MEASURES_GLOB = "*_reading_measures.csv"

        #: Regex to extract the stimulus order version from ASC files.
        self.STIMULUS_ORDER_VERSION_REGEX = re.compile(
            r"MSG\s+\d+\s+stimulus_order_version:\s+(?P<version_num>\d\d?\d?)\n"
        )

        #: Regex to extract stimulus order version from logfiles.
        self.LOGFILE_ORDER_VERSION_REGEX = re.compile(
            r"(STIMULUS_ORDER_VERSION_)(?P<order_version>\d+)"
        )

        multipleye_messages = {
            "other_screens": [
                "welcome_screen",
                "informed_consent_screen",
                "start_experiment",
                "stimulus_order_version",
                "showing_instruction_screen",
                "camera_setup_screen",
                "practice_text_starting_screen",
                "transition_screen",
                "final_validation",
                "show_final_screen",
                "optional_break_screen",
                "fixation_trigger:skipped_by_experimenter",
                "fixation_trigger:experimenter_calibration_triggered",
                "recalibration",
                "empty_screen",
                "obligatory_break",
                "optional_break",
            ],
            "break_msgs": [
                "optional_break_duration",
                "optional_break_end",
                "optional_break",
                "obligatory_break_duration",
                "obligatory_break_end",
                "obligatory_break",
            ],
        }

        self.BREAK_REGEX = re.compile(
            "|".join(map(re.escape, multipleye_messages["break_msgs"]))
        )
        self.OTHER_SCREENS_REGEX = re.compile(
            "|".join(map(re.escape, multipleye_messages["other_screens"]))
        )

        # --- HARDWARE AND STIMULI MAPPINGS ---

        #: Mapping of eye tracker brands to known model names.
        self.EYETRACKER_NAMES = {
            "eyelink": [  # TODO: Update list to mapping between same eyetrackers - use dict
                "EyeLink 1000 Plus",
                "EyeLink 1000+",
                "EyeLink 1000-Plus",
                "EyeLink II",
                "EyeLink 1000",
                "EyeLink Portable Duo",
                "EyeLink Portable Duo 2000Hz Remote",
                "Eyelink Duo",
                "EyeLink Duo",
                "Eyelink Portable Duo",
            ],
        }

        #: Mapping of stimulus names to internal numeric IDs.
        self.STIMULUS_NAME_MAPPING = {
            "PopSci_MultiplEYE": 1,
            "Ins_HumanRights": 2,
            "Ins_LearningMobility": 3,
            "Lit_Alchemist": 4,
            "Lit_MagicMountain": 6,
            "Lit_Solaris": 8,
            "Lit_BrokenApril": 9,
            "Arg_PISACowsMilk": 10,
            "Arg_PISARapaNui": 11,
            "PopSci_Caveman": 12,
            "Enc_WikiMoon": 13,
            "Lit_NorthWind": 7,
        }

        # --- PSYCHOMETRIC TEST DIRECTORIES ---

        #: Subfolder name for Working Memory Capacity tests.
        self.PSYM_LWMC_DIR = Path("WMC/")

        #: Subfolder name for Rapid Automatized Naming tests.
        self.PSYM_RAN_DIR = Path("RAN/")

        #: Subfolder name for Stroop and Flanker tests.
        self.PSYM_STROOP_FLANKER_DIR = Path("Stroop_Flanker/")

        #: Subfolder name for PLAB tests.
        self.PSYM_PLAB_DIR = Path("PLAB/")

        #: Subfolder name for WikiVocab tests.
        self.PSYM_WIKIVOCAB_DIR = Path("WikiVocab/")

        # --- GAZE PATTERNS AND EVENT PROPERTIES ---

        #: Properties to compute for each event type.
        self.EVENT_PROPERTIES = {
            self.FIXATION: [
                ("location", {"position_column": "pixel"}),
                ("dispersion", {}),
            ],
            self.SACCADE: [
                ("amplitude", {}),
                ("peak_velocity", {}),
                ("dispersion", {}),
            ],
        }

        self._loaded = False
        self._loading = False

    @property
    def THIS_REPO(self) -> Path:
        return self._repo_root

    def _ensure_loaded(self) -> None:
        if not self._loaded and not self._loading:
            self.load()

    def _is_valid_data_collection_name(self, name: str) -> bool:
        """Check if the name follows the MultiplEYE data collection format."""
        return Dcn.is_valid(name)

    def load(self, path: str | Path | None = None) -> None:
        """Load settings from various sources with defined precedence."""
        self._loading = True
        try:
            if path:
                self.load_from_yaml(path)
                self._config_found = True
                self._apply_logging_settings()
                return

            env_path = os.getenv("MULTIPLEYE_CONFIG")
            if env_path:
                self.load_from_yaml(env_path)
                self._config_found = True
                self._apply_logging_settings()
                return

            cwd_default = Path.cwd() / "multipleye_settings_preprocessing.yaml"
            if cwd_default.exists():
                self.load_from_yaml(cwd_default)
                self._config_found = True
                self._apply_logging_settings()
                return

            # No config found, try to create from template
            cwd_name = Path.cwd().name
            if self._is_valid_data_collection_name(cwd_name):
                self.create_config_template(cwd_default, collection_name=cwd_name)
                self._is_auto_filled = True
            else:
                self.create_config_template(cwd_default)

            self._is_template_loaded = True
            if cwd_default.exists():
                self.load_from_yaml(cwd_default)
                self._apply_logging_settings()

            return

        finally:
            self._loading = False

    def _apply_logging_settings(self) -> None:
        """Apply logging settings from configuration to the active logger."""
        # Use the package-level setup_logging to ensure consistent behaviour
        from .utils.logging import clear_log_file, setup_logging

        log_file = self.DATASET_DIR / "preprocessing_logs.txt"
        if not self.DATASET_DIR.exists():
            log_file = None
        elif not self.APPEND_LOGS:
            clear_log_file(log_file)

        setup_logging(
            log_file=log_file,
            console_level=self.CONSOLE_LOG_LEVEL,
            file_level=self.FILE_LOG_LEVEL,
        )

    def create_config_template(
        self, target_path: Path, collection_name: str | None = None
    ) -> None:
        """Create a configuration template at the target path."""
        template_path = self._repo_root / TEMPLATE_RELATIVE_PATH
        if not template_path.exists():
            return

        try:
            content = template_path.read_text(encoding="utf-8")
            if collection_name:
                content = content.replace(
                    'data_collection_name: "REPLACE_WITH_YOUR_COLLECTION_NAME"',
                    f'data_collection_name: "{collection_name}"',
                )
            target_path.write_text(content)
        except OSError:
            # We don't log here to keep load() silent,
            # but we can check if it exists in get_config_status_message
            pass

    def get_config_status_message(self) -> str | None:
        """Return a status message if configuration is missing or invalid."""
        cwd_default = Path.cwd() / "multipleye_settings_preprocessing.yaml"

        if self._is_template_loaded:
            if cwd_default.exists():
                if self._is_auto_filled:
                    return (
                        "\n" + "=" * 80 + "\n"
                        " CONFIGURATION REQUIRED\n" + "=" * 80 + "\n"
                        "No configuration file was found.\n\n"
                        f"The data collection name has been detected as '{Path.cwd().name}'\n"
                        "and the configuration template has been updated for you at:\n"
                        f"  {cwd_default}\n\n"
                        "Please open this file, review the settings,\n"
                        "and then run the pipeline again.\n\n"
                        f"For more help, see: {TEMPLATE_DOCS_URL}\n" + "=" * 80 + "\n"
                    )

                return (
                    "\n" + "=" * 80 + "\n"
                    " CONFIGURATION REQUIRED\n" + "=" * 80 + "\n"
                    "No configuration file was found.\n\n"
                    "A template has been created for you at:\n"
                    f"  {cwd_default}\n\n"
                    "Please open this file, set your 'data_collection_name',\n"
                    "and then run the pipeline again.\n\n"
                    f"For more help, see: {TEMPLATE_DOCS_URL}\n" + "=" * 80 + "\n"
                )
            else:
                return (
                    f"No configuration file found and failed to create template at {cwd_default}. "
                    f"See: {TEMPLATE_DOCS_URL}"
                )

        if not self._config_found and not self._loaded:
            return (
                "No configuration file found. Expected one of: explicit path, "
                f"MULTIPLEYE_CONFIG env var, or {cwd_default}. See: {TEMPLATE_DOCS_URL}"
            )

        # Check for placeholders
        val = self.__dict__.get("DATA_COLLECTION_NAME")
        if val == "REPLACE_WITH_YOUR_COLLECTION_NAME":
            return (
                "\n" + "=" * 80 + "\n"
                " INVALID CONFIGURATION\n" + "=" * 80 + "\n"
                f"Invalid DATA_COLLECTION_NAME: '{val}'.\n"
                "It looks like you are still using a placeholder value.\n\n"
                "Please edit your configuration file and set 'data_collection_name' to your "
                "actual collection identifier (e.g., 'MultiplEYE_EN_UK_London_1_2026').\n\n"
                "The collection name must follow the format: MultiplEYE_LANG_COUNTRY_CITY_LAB_YEAR\n"
                f"For more details on naming and configuration, see: {TEMPLATE_DOCS_URL}\n"
                + "=" * 80
                + "\n"
            )

        return None

    def load_from_yaml(self, path: str | Path) -> None:
        """Load settings from a YAML file."""
        path = Path(path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        logger.debug(f"Loading config from: {path}")

        with open(path) as f:
            user_configs = yaml.safe_load(f)

        if user_configs:
            self.update(user_configs)

        self._config_source = path
        self._validate()
        self._loaded = True

    def update(self, config_dict: dict[str, Any]) -> None:
        """Update settings from a dictionary."""
        for key, value in config_dict.items():
            upper_key = key.upper()
            if upper_key in self.__dict__:
                setattr(self, upper_key, value)
            else:
                # Allow setting new attributes or lowercase if they exist
                setattr(self, key, value)

    def _validate(self) -> None:
        """Validate required settings."""
        if self._loading:  # Skip validation during initial loading of parts
            return

        # Use __dict__ to avoid _ensure_loaded() recursion via property
        val = self.__dict__.get("DATA_COLLECTION_NAME")
        if not val:
            # We don't raise here if we are just loading, as we might be loading the template
            return

    def setup_logging(self, log_file: str | Path | None = None) -> None:
        """Configure logging with separate levels for console and file.

        To be replaced by https://github.com/MultiplEYE-COST/multipleye-preprocessing/pull/64
        """
        # Root logger or specific package logger
        root_logger = logging.getLogger("preprocessing")

        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        root_logger.setLevel(logging.DEBUG)  # Capture everything, filter in handlers

        # Console handler
        console_handler = logging.StreamHandler()
        console_level = getattr(logging, self.CONSOLE_LOG_LEVEL.upper(), logging.INFO)
        console_handler.setLevel(console_level)
        console_formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler
        if log_file:
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_level = getattr(logging, self.FILE_LOG_LEVEL.upper(), logging.DEBUG)
            file_handler.setLevel(file_level)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

        # Also set the level for the root logger if needed
        # (if we want to affect non-preprocessing loggers)
        # logging.getLogger().setLevel(getattr(logging, self.LOG_LEVEL.upper(), logging.WARNING))

    def __setattr__(self, name: str, value: Any) -> None:
        if not name.startswith("_"):
            # Check if this is an initial set (in __init__) or a later change
            if hasattr(self, name):
                old_value = getattr(self, name)
                if old_value != value:
                    logger.debug(f"Changing setting {name}: {old_value} -> {value}")
            else:
                # If we are not in _loading and not in __init__, it's a new attribute, using a flag
                if hasattr(self, "_initialized") and self._initialized:
                    logger.debug(f"Setting new attribute {name}: {value}")

        super().__setattr__(name, value)

    def __getattr__(self, name: str) -> Any:
        # Avoid recursion for private attributes or property-backed attributes
        if name.startswith("_") or name == "DATA_COLLECTION_NAME":
            raise AttributeError(name)

        self._ensure_loaded()

        # uppercase for case-insensitivity, check in __dict__
        upper_name = name.upper()
        if upper_name in self.__dict__:
            return self.__dict__[upper_name]

        if name in self.__dict__:
            return self.__dict__[name]

        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def copy_config_to(self, output_dir: str | Path | None = None) -> Path | None:
        """Copy the last-used config file into the output metadata folder.

        The copy preserves the original filename and overwrites any existing file so
        the output folder always reflects the most recent pipeline run.

        Parameters
        ----------
        output_dir : str | Path | None, optional
            Target output directory. Defaults to ``self.OUTPUT_DIR``.

        Returns
        -------
        Path | None
            The destination path of the copy, or ``None`` if no config source was recorded.
        """
        import shutil

        if self._config_source is None:
            logger.warning(
                "No config source path recorded; skipping config copy to output folder."
            )
            return None

        dest_dir = Path(output_dir or self.OUTPUT_DIR) / self.METADATA_FOLDER
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / self._config_source.name
        shutil.copy2(str(self._config_source), str(dest))
        logger.info(f"Config copy written to {dest}")
        return dest


settings = Settings()

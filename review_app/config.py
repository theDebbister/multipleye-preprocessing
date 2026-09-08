"""Review app configuration — resolve paths to preprocessed data.

The base directory is configurable via the ``PREPROCESSED_DATA_DIR``
environment variable. Folder name constants mirror those in
``preprocessing.config.Settings`` but are duplicated here to
avoid triggering the settings auto-load mechanism.
"""

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

PREPROCESSED_DATA_DIR = Path(
    os.environ.get("PREPROCESSED_DATA_DIR", _REPO_ROOT / "preprocessed_data")
)

RAW_DATA_DIR = Path(os.environ.get("RAW_DATA_DIR", _REPO_ROOT / "data"))

REVIEW_DATA_DIR = Path(os.environ.get("REVIEW_DATA_DIR", _REPO_ROOT / "review_data"))

# Folder name constants (mirrors preprocessing.config.Settings defaults).
_METADATA_FOLDER = "metadata/"
_SANITY_CHECKS_FOLDER = "sanity_checks/"
_PSYCHOMETRIC_TESTS_FOLDER = "psychometric_tests/"


def dcn_path(dcn_name: str) -> Path:
    return PREPROCESSED_DATA_DIR / dcn_name


def metadata_path(dcn_name: str, sid: str) -> Path:
    return dcn_path(dcn_name) / _METADATA_FOLDER / sid


def sanity_checks_path(dcn_name: str, sid: str) -> Path:
    return dcn_path(dcn_name) / _SANITY_CHECKS_FOLDER / sid


def quality_thresholds_path(dcn_name: str) -> Path:
    return dcn_path(dcn_name) / "quality_thresholds.yaml"


def dataset_overview_path(dcn_name: str) -> Path:
    return dcn_path(dcn_name) / f"{dcn_name}_overview.yaml"


def session_overview_path(dcn_name: str, sid: str) -> Path:
    return metadata_path(dcn_name, sid) / f"{sid}_overview.yaml"


def review_path(dcn_name: str) -> Path:
    return REVIEW_DATA_DIR / dcn_name


def reviews_file_path(dcn_name: str) -> Path:
    return review_path(dcn_name) / "reviews.yaml"


def swipe_judgments_path(dcn_name: str) -> Path:
    return review_path(dcn_name) / "swipe_judgments.yaml"


def psychometric_path(dcn_name: str) -> Path:
    return (
        dcn_path(dcn_name)
        / _PSYCHOMETRIC_TESTS_FOLDER
        / f"psychometric_results_{dcn_name}.csv"
    )

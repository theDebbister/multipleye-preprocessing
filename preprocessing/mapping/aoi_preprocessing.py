"""
In order to make the MultiplEYE eye-tracking data more meaningful to use for different languages, there is the option
of adding custom units-of-analysis (UOAs) to the areas of interest (AOIs) defined in the stimulus. By default, the
aois are defined as words deliemited by white space and in additional as characters. However, characters are rarely used
for analyses and too small, and in some cases words are not the most meaningful unit of analysis (e.g., in agglutinative
languages). In order to make the naming consistent all word aois will be called "unit-of-analysis" aois, regardless of the
custom definition.
This script:
- loads all MultiplEYE aoi files and renames the columns for publication
- adds custom uoa aois from a provided from custom files for each language
"""

import difflib
from pathlib import Path

import pandas as pd

from preprocessing import settings


def rename_aoi_columns(aoi_file: Path) -> None:
    """
    Refactor the aoi files for a given data collection to have consistent naming conventions.
    If necessary, add the custom uoa aois for the given language.
    :param aoi_file: Path to the AOI file
    """

    aoi_data = pd.read_csv(aoi_file)

    # rename columns
    aoi_data = aoi_data.rename(
        {
            "word_idx": "unit_of_analysis_idx",
            "word": "unit_of_analysis",
            "word_idx_in_line": "unit_of_analysis_idx_in_line",
        },
        axis="columns",
    )

    # save the refactored aoi files
    aoi_data.sort_values(by=["page", "char_idx"], inplace=True)
    aoi_data.to_csv(aoi_file, index=False)


def add_custom_aois(aoi_file: Path, language: str) -> None:
    """
    Will call a language specific function which adds the custom aois for this language, if they are available and
    supported.
    :param aoi_file: Path to the AOI file
    :param language: The language of the data collection.
    :return:
    """

    if language == "ZH":
        _add_custom_uoa(aoi_file, "segment", "segment_idx")
    elif language == "KL":
        # for KL currently, the questions are not supported
        if not "question" in aoi_file.name:
            custom_name = aoi_file.stem + "_morph.csv"
            _add_custom_uoa(aoi_file, "morph_token", "morph_idx", custom_name)
    else:
        raise Warning(
            f"You requested adding custom units of analysis to the aoi files. Currently, your language {language} "
            "is not supported. Please contact the maintainers to add your language."
        )


def _add_custom_uoa(
    aoi_file: Path, uoa_column_name, uoa_idx_colum_name, custom_file_name: str = ""
) -> None:
    """
    The custom units of analysis can be added as follows for ZH:
    - They are in a directory called "custom_units_of_analysis" in the data folder
    - The aoi files for the questions are named and structured the same as the original question aoi files.
        - They contain an additional segment and segment_idx column
        - As the text on all pages is for all question versions is the same, only question_images_version_1 is annotated
    - The stimuli text aoi files are name like this: Lit_Alchemist_zh_seg_pages.csv. The first part can be replaced
    by the respective stimulus name
        - They contain an additional word and word_idx column

    How to add it:
    - Merge the custom and the original aoi files on the char and char index as well as the page column!
    - check that all chars listed in both files exactly align. Index and char should be exactly the same.
    - ensure the segment contains the actual characters that it annotates, and that the running segment index is correct
    - for the questions add the segments to all question images versions and make sure the characters match. Only the coordinates should be different for the options

    Output:
    The original aoi files should be exactly the same as before also the file name, but they should contain two additional columns:
        - unit_of_analysis
        - unit_of_analysis_idx

    If there is a word column already in there: rename to secondary_unit_of_analysis and word_idx to secondary_unit_of_analysis_idx.
    The characters and character indices should stay exactly the same.

    If any of the characters and segment characters do not match, it will be reported.

    """

    if custom_file_name:
        uoa_file = settings.DATASET_DIR / "custom_units_of_analysis" / custom_file_name
    else:
        uoa_file = settings.DATASET_DIR / "custom_units_of_analysis" / aoi_file.name

    if not uoa_file.exists():
        raise FileNotFoundError(
            f"We could not find a matching uoa file for {aoi_file.name}. Please make "
            f"sure that the uoa file is named exactly as the corresponding aoi file and "
            f"that it is in your data folder in a folder called 'custom_units_of_analysis'."
        )

    if "questions" in uoa_file.name:
        uoa_data = pd.read_csv(uoa_file, dtype={uoa_column_name: str})[
            [
                uoa_column_name,
                uoa_idx_colum_name,
                "char",
                "char_idx",
                "page",
                "question_image_version",
            ]
        ]
        uoa_data = uoa_data[
            uoa_data["question_image_version"] == "question_images_version_1"
        ]

        uoa_data = uoa_data[
            [uoa_column_name, uoa_idx_colum_name, "char", "char_idx", "page"]
        ]

    else:
        uoa_data = pd.read_csv(uoa_file, dtype={uoa_column_name: str})[
            [uoa_column_name, uoa_idx_colum_name, "char", "char_idx", "page"]
        ]

    aoi_data = pd.read_csv(aoi_file, dtype={uoa_column_name: str})

    uoa_data = uoa_data.sort_values(by=["page"], ascending=False).reset_index()
    aoi_data = aoi_data.sort_values(by=["page"], ascending=False).reset_index()

    uoa_chars = uoa_data["char"].tolist()

    if "questions" in uoa_file.name:
        aoi_chars = aoi_data[
            aoi_data["question_image_version"] == "question_images_version_1"
        ]["char"].tolist()
    else:
        aoi_chars = aoi_data["char"].tolist()

    if len(uoa_data) != len(aoi_data):
        for line in difflib.unified_diff(aoi_chars, uoa_chars, lineterm=""):
            print(line)

    # check that the char and char_idx column match
    try:
        assert aoi_chars == uoa_chars
    except AssertionError:
        raise AssertionError(
            f"There is a mismatch in the character columns of {uoa_file.name} and it original aoi file. "
            f"They do not contain the same characters."
        )

    # join the segment and segment idx on page and char idx
    new_aois = aoi_data.merge(uoa_data, on=["page", "char_idx", "char"])

    # rename columns
    new_aois = new_aois.rename(
        {
            "unit_of_analysis_idx": "secondary_unit_of_analysis_idx",
            "unit_of_analysis": "secondary_unit_of_analysis",
            "unit_of_analysis_idx_in_line": "secondary_unit_of_analysis_idx_in_line",
            uoa_column_name: "unit_of_analysis",
            uoa_idx_colum_name: "unit_of_analysis_idx",
        },
        axis="columns",
    )

    # get the line index of the segments
    new_aois["unit_of_analysis_idx_in_line"] = (
        new_aois.groupby(["page", "line_idx"])["unit_of_analysis_idx"]
        .rank(method="dense")
        .astype(pd.Int64Dtype())
    )

    col_order = [
        "char_idx",
        "char",
        "top_left_x",
        "top_left_y",
        "width",
        "height",
        "char_idx_in_line",
        "line_idx",
        "page",
        "unit_of_analysis",
        "unit_of_analysis_idx",
        "unit_of_analysis_idx_in_line",
        "secondary_unit_of_analysis_idx",
        "secondary_unit_of_analysis_idx_in_line",
        "secondary_unit_of_analysis",
    ]

    new_aois = new_aois[col_order]
    new_aois.sort_values(by=["page", "line_idx", "char_idx"], inplace=True)
    new_aois.to_csv(aoi_file, index=False)

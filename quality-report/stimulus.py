from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import polars as pl
import pymovements as pm

NAMES = [
    "PopSci_MultiplEYE",
    "Ins_HumanRights",
    "Ins_LearningMobility",
    "Lit_Alchemist",
    "Lit_MagicMountain",
    "Lit_Solaris",
    "Lit_BrokenApril",
    "Arg_PISACowsMilk",
    "Arg_PISARapaNui",
    "PopSci_Caveman",
    "Enc_WikiMoon",
    "Lit_NorthWind",
]


@dataclass
class StimulusPage:
    number: int
    text: str
    image_path: Path


@dataclass
class Stimulus:
    id: int
    name: str
    type: Literal["experiment", "practice"]
    pages: list[StimulusPage]
    text_stimulus: pm.stimulus.TextStimulus
    # TODO: questions

    @classmethod
    def load(
        cls,
        stimulus_dir: Path,
        lang: str,
        country: str,
        labnum: int,
        stimulus_name: str,
    ):
        assert stimulus_name in NAMES, f"{stimulus_name!r} is not a valid stimulus name"
        stimulus_df_path = stimulus_dir / f"multipleye_stimuli_experiment_{lang}.xlsx"
        stimulus_df = pl.read_excel(stimulus_df_path)
        stimulus_row = stimulus_df.row(
            by_predicate=pl.col("stimulus_name") == stimulus_name, named=True
        )

        stimulus_id = stimulus_row["stimulus_id"]
        stimulus_type = stimulus_row["stimulus_type"]

        pages = []
        for column, value in stimulus_row.items():
            if column.startswith("page_") and value is not None:
                page_number = int(column.split("_")[1])
                image_filename = f"{stimulus_name.lower()}_id{stimulus_id}_page_{page_number}_{lang}.png"
                image_path = (
                    stimulus_dir
                    / f"stimuli_images_{lang}_{country}_{labnum}"
                    / image_filename
                )

                page = StimulusPage(
                    number=page_number,
                    text=value,
                    image_path=image_path,
                )
                assert (
                    page.image_path.exists()
                ), f"File {page.image_path} does not exist"
                pages.append(page)

        aoi_path = (
            stimulus_dir
            / f"aoi_stimuli_{lang}_{country}_{labnum}"
            / f"{stimulus_name.lower()}_{stimulus_id}_aoi.csv"
        )
        text_stimulus = pm.stimulus.text.from_file(
            aoi_path,
            aoi_column="char",
            start_x_column="top_left_x",
            start_y_column="top_left_y",
            width_column="width",
            height_column="height",
            page_column="page",
        )

        stimulus = cls(
            id=stimulus_id,
            name=stimulus_name,
            type=stimulus_type,
            pages=pages,
            text_stimulus=text_stimulus,
        )
        return stimulus


if __name__ == "__main__":
    stimulus_dir = Path("C:\\Users\saphi\PycharmProjects\multipleye-preprocessing\data\stimuli_MultiplEYE_zh_ch_Zurich_1_2025")
    lang = "zh"
    country = "ch"
    labnum = 1
    stimulus_name = "PopSci_MultiplEYE"

    stimulus = Stimulus.load(stimulus_dir, lang, country, labnum, stimulus_name)
    for page in stimulus.pages:
        print(page.number, page.image_path)

    print(stimulus)

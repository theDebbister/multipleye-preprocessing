from dataclasses import dataclass
from pathlib import Path
from typing import Literal
import pandas as pd

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
    # TODO: questions
    # TODO: aois

    @classmethod
    def load(
        cls, stimulus_dir: Path, lang: str, country: str, labnum: int, stimulus_name: str
    ):
        assert stimulus_name in NAMES, f"{stimulus_name!r} is not a valid stimulus name"
        stimulus_df_path = stimulus_dir / f"multipleye_stimuli_experiment_{lang}.xlsx"
        stimulus_df = pd.read_excel(stimulus_df_path)
        stimulus_rows = stimulus_df[stimulus_df["stimulus_name"] == stimulus_name]
        assert len(stimulus_rows) == 1, f"{len(stimulus_rows)} rows found for stimulus {stimulus_name} in {stimulus_df_path}"

        stimulus_row = stimulus_rows.iloc[0]
        stimulus_id = int(stimulus_row["stimulus_id"])
        stimulus_type = stimulus_row["stimulus_type"]

        pages = []
        for column, value in stimulus_row.items():
            if column.startswith("page_"):
                page_number = int(column.split("_")[1])
                if pd.notna(value):
                    image_filename = f"{stimulus_name.lower()}_id{stimulus_id}_page_{page_number}_{lang}.png"
                    image_path=stimulus_dir / f"stimuli_images_{lang}_{country}_{labnum}" / image_filename
                    page = StimulusPage(
                        number=page_number,
                        text=value,
                        image_path=image_path,
                    )
                    assert page.image_path.exists(), f"File {page.image_path} does not exist"
                    pages.append(page)

        stimulus = cls(
            id=stimulus_id,
            name=stimulus_name,
            type=stimulus_type,
            pages=pages,
        )
        return stimulus


if __name__ == "__main__":
    stimulus_dir = Path("010_ZH_CH_1_ET1/stimuli_MultiplEYE_zh_ch_Zurich_1_2025")
    lang = "zh"
    country = "ch"
    labnum = 1
    stimulus_name = "PopSci_MultiplEYE"

    stimulus = Stimulus.load(stimulus_dir, lang, country, labnum, stimulus_name)

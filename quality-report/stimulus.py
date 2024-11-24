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
        cls, stim_dir: Path, lang: str, country: str, labnum: int, stimulus_name: str
    ):
        stimulus_df = pd.read_excel(
            stim_dir / f"multipleye_stimuli_experiment_{lang}.xlsx"
        )
        stimulus_rows = stimulus_df[stimulus_df["stimulus_name"] == stimulus_name]
        assert len(stimulus_rows) == 1
        stimulus_row = stimulus_rows.iloc[0]
        stimulus_id = int(stimulus_row["stimulus_id"])
        stimulus_type = stimulus_row["stimulus_type"]
        pages = []
        for column, value in stimulus_row.items():
            if column.startswith("page_"):
                page_number = int(column.split("_")[1])
                if pd.notna(value):
                    page = StimulusPage(
                        number=page_number,
                        text=value,
                        image_path=stim_dir
                        / f"stimuli_images_{lang}_{country}_{labnum}",
                    )
                    pages.append(page)
        return cls(
            id=stimulus_id,
            name=stimulus_name,
            type=stimulus_type,
            pages=pages,
        )


if __name__ == "__main__":
    stim_dir = Path("010_ZH_CH_1_ET1/stimuli_MultiplEYE_zh_ch_Zurich_1_2025")

    lang = "zh"
    country = "ch"
    labnum = 1
    stimulus_name = "PopSci_MultiplEYE"

    stimulus = Stimulus.load(stim_dir, lang, country, labnum, stimulus_name)
    print(stimulus)

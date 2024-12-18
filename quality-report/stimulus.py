import ast
import json
from dataclasses import dataclass
from glob import glob
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
class Instruction:
    id: int
    name: str
    text: str
    image_path: Path

@dataclass
class StimulusPage:
    number: int
    text: str
    image_path: Path


@dataclass
class ComprehensionQuestion:
    name: str
    id: str
    question: str
    target: str
    distractor_a: str
    distractor_b: str
    distractor_c: str
    image_path: Path


@dataclass
class Stimulus:
    id: int
    name: str
    type: Literal["experiment", "practice"]
    pages: list[StimulusPage]
    text_stimulus: pm.stimulus.TextStimulus
    questions: list[ComprehensionQuestion]
    instructions: list[Instruction]

    @classmethod
    def load(
        cls,
        stimulus_dir: Path,
        lang: str,
        country: str,
        labnum: int,
        stimulus_name: str,
    ) -> "Stimulus":
        assert stimulus_name in NAMES, f"{stimulus_name!r} is not a valid stimulus name"
        stimulus_df_path = stimulus_dir / f"multipleye_stimuli_experiment_{lang}.xlsx"
        stimulus_df = pl.read_excel(stimulus_df_path)
        stimulus_row = stimulus_df.row(
            by_predicate=pl.col("stimulus_name") == stimulus_name, named=True
        )

        stimulus_id = stimulus_row["stimulus_id"]
        stimulus_type = stimulus_row["stimulus_type"]
        assert stimulus_type in [
            "experiment",
            "practice",
        ], f"{stimulus_type!r} is not a valid stimulus type"

        pages = []
        for column, value in stimulus_row.items():
            if column.startswith("page_") and value is not None:
                page_number = int(column.split("_")[1])
                image_path = (
                    stimulus_dir
                    / f"stimuli_images_{lang}_{country}_{labnum}"
                    / f"{stimulus_name.lower()}_id{stimulus_id}_page_{page_number}_{lang}.png"
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

        questions_df_path = (
            stimulus_dir / f"multipleye_comprehension_questions_{lang}.xlsx"
        )
        questions_df = pl.read_excel(questions_df_path)
        question_rows = questions_df.filter(
            pl.col("stimulus_name") == stimulus_name
        ).rows(named=True)
        questions = []
        for question_row in question_rows:
            question_name = question_row["item_id"]
            question_id = question_row["item_id"].split("_")[-1]
            question = question_row["question"]
            target = question_row["target"]
            distractor_a = question_row["distractor_a"]
            distractor_b = question_row["distractor_b"]
            distractor_c = question_row["distractor_c"]
            question_image_path = (
                stimulus_dir
                / f"question_images_{lang}_{country}_{labnum}"
                / "question_images_version_1"  # NOTE: We always use version 1 here (but different participants have different versions)
                / f"{stimulus_name}_id{stimulus_id}_question_{question_id}_{lang}.png"
            )
            question = ComprehensionQuestion(
                name=question_name,
                id=question_id,
                question=question,
                target=target,
                distractor_a=distractor_a,
                distractor_b=distractor_b,
                distractor_c=distractor_c,
                image_path=question_image_path,
            )
            questions.append(question)

        # TODO: Instructions are the same for all stimuli, so this is not the best place to put them
        instruction_df_path = (
            stimulus_dir
            / f"multipleye_participant_instructions_{lang}_with_img_paths.csv"
        )
        instruction_df = pl.read_csv(instruction_df_path)
        instructions = []
        for instruction_row in instruction_df.iter_rows(named=True):

            instruction_id = instruction_row["instruction_screen_id"]
            instruction_name = instruction_row["instruction_screen_name"]
            instruction_text = instruction_row["instruction_screen_text"]
            instruction_image_path = (
                stimulus_dir
                / f"participant_instructions_images_{lang}_{country}_{labnum}"
                / instruction_row["instruction_screen_img_name"]
            )
            instruction_image_path = stimulus_dir/ f"participant_instructions_images_{lang}_{country}_1/{instruction_row['instruction_screen_img_name']}"

            instruction = Instruction(
                id=instruction_id,
                name=instruction_name,
                text=instruction_text,
                image_path=Path(instruction_image_path),
            )

            assert (
                instruction.image_path.exists()
            ), f"File {instruction.image_path} does not exist."
            instructions.append(instruction)

        if stimulus_type == "experiment":
            assert (
                len(questions) == 6
            ), f"{stimulus_id} has {len(questions)} questions instead of 6"
        else:
            assert (
                len(questions) == 2
            ), f"{stimulus_id} has {len(questions)} questions instead of 2"

        stimulus = cls(
            id=stimulus_id,
            name=stimulus_name,
            type=stimulus_type,
            pages=pages,
            text_stimulus=text_stimulus,
            questions=questions,
            instructions=instructions,
        )
        return stimulus


@dataclass
class LabConfig:
    screen_resolution: tuple[int, int]
    screen_size_cm: tuple[float, float]
    screen_distance_cm: float

    @classmethod
    def load(cls, stimulus_dir: Path, lang: str, country: str, labnum: int):
        config_path = glob(
            f"MultiplEYE_{lang.upper()}_{country.upper()}_*_{labnum}_*_lab_configuration.json",
            root_dir=stimulus_dir / "config",
        )
        assert (
            len(config_path) == 1
        ), f"Found {len(config_path)} config files: {config_path}"
        config_path = stimulus_dir / "config" / config_path[0]
        with open(config_path) as f:
            config = json.load(f)

        screen_resolution = ast.literal_eval(config["Monitor_resolution_in_px"])
        screen_size_cm = ast.literal_eval(config["Screen_size_in_cm"])
        screen_distance_cm = float(config["Distance_in_cm"])

        return cls(
            screen_resolution=screen_resolution,
            screen_size_cm=screen_size_cm,
            screen_distance_cm=screen_distance_cm,
        )


def load_stimuli(
    stimulus_dir: Path, lang: str, country: str, labnum: int
) -> tuple[list[Stimulus], LabConfig]:
    stimuli = []
    for stimulus_name in NAMES:
        stimulus = Stimulus.load(stimulus_dir, lang, country, labnum, stimulus_name)
        stimuli.append(stimulus)
    config = LabConfig.load(stimulus_dir, lang, country, labnum)
    return stimuli, config


if __name__ == "__main__":
    stimulus_dir = Path("C:\\Users\saphi\PycharmProjects\multipleye-preprocessing\data\stimuli_MultiplEYE_zh_ch_Zurich_1_2025")
    lang = "zh"
    country = "ch"
    labnum = 1
    stimulus_name = "PopSci_MultiplEYE"
    print(stimulus_dir.exists())
    stimulus = Stimulus.load(stimulus_dir, lang, country, labnum, stimulus_name)
    for page in stimulus.pages:
        print(page.number, page.image_path)

    print(stimulus)

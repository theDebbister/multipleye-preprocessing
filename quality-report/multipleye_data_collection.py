import json
import pickle
from pathlib import Path
from pprint import pprint
import polars as pl

import pandas as pd
from pymovements import GazeDataFrame
from tqdm import tqdm
from report import check_gaze, check_metadata, check_events, report_to_file as report_meta
from functools import partial

from data_collection import DataCollection
from plot import load_data, preprocess
from stimulus import load_stimuli, LabConfig, Stimulus


class MultipleyeDataCollection(DataCollection):

    def __init__(self,
                 config_file: Path,
                 stimulus_dir: Path,
                 lab_number: int,
                 city: str,
                 data_root: Path,
                 lab_configuration: LabConfig,
                 session_folder_regex: str,
                 stimuli: list[Stimulus],
                 **kwargs):
        super().__init__(**kwargs)
        self.config_file = config_file
        self.stimulus_dir = stimulus_dir
        self.lab_number = lab_number
        self.city = city
        self.lab_configuration = lab_configuration
        self.data_root = data_root
        self.session_folder_regex = session_folder_regex
        self.stimuli = stimuli

        if not self.output_dir:
            self.output_dir = self.data_root.parent / 'quality_reports'
            self.output_dir.mkdir(exist_ok=True)

        self.add_recorded_sessions(self.data_root, self.session_folder_regex, convert_to_asc=True)

    @classmethod
    def create_from_data_folder(cls, data_dir: str):
        data_dir = Path(data_dir)

        data_folder_name = data_dir.name
        _, stimulus_language, country, city, lab_number, year = data_folder_name.split('_')

        session_folder_regex = r"\d\d\d" + f"_{stimulus_language}_{country}_{lab_number}_ET1"

        stimulus_folder_path = data_dir / f'stimuli_{data_folder_name}'
        config_file = (stimulus_folder_path /
                       'config' /
                       f'config_{stimulus_language.lower()}_{country.lower()}_{city}_{lab_number}.py')

        stimuli, lab_configuration_data = load_stimuli(stimulus_folder_path, stimulus_language,
                                                       country, lab_number, city, year)

        eye_tracker = lab_configuration_data.name_eye_tracker

        et_data_path = data_dir / 'eye-tracking-sessions'

        return cls(
            data_collection_name=data_folder_name,
            stimulus_language=stimulus_language,
            country=country,
            year=int(year),
            eye_tracker=eye_tracker,
            session_folder_regex=session_folder_regex,
            config_file=config_file,
            stimulus_dir=stimulus_folder_path,
            lab_number=int(lab_number),
            city=city,
            data_root=et_data_path,
            lab_configuration=lab_configuration_data,
            stimuli=stimuli
        )

    def create_gaze_frame(self, session: str | list[str] = '', overwrite: bool = False) -> None:
        """
        Creates, preprocesses and saves the gaze data for the specified session or all sessions.
        :param session: If a session identifier is specified only the gaze data for this session is loaded.
        :param overwrite: If True the gaze data is overwritten if it already exists.
        :return:
        """

        if session:
            if isinstance(session, str):
                session_keys = [session]

            elif isinstance(session, list):
                session_keys = session

        else:
            session_keys = self.sessions.keys()

        for session_name in tqdm(session_keys, desc="Creating gaze data"):
            gaze_path = self.output_dir / session
            print(gaze_path)
            # / f"{session_name}_gaze.pkl"
            gaze_path.mkdir(parents=True, exist_ok=True)

            gaze_path = gaze_path / f"{session_name}_gaze.pkl"

            if gaze_path.exists() and not overwrite:
                # make sure gaze path is added if the pkl was created in a previous run
                self.sessions[session_name]['gaze_path'] = gaze_path
                return

            try:
                gaze = load_data(Path(self.sessions[session_name]['asc_path']), self.lab_configuration,
                                 session_idf=session_name)
            except KeyError:
                raise KeyError(
                    f"Session {session_name} not found in {self.data_root}.")
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"No asc file found for session {session_name}. Please create first.")

            preprocess(gaze)
            # save and load the gaze dataframe to pickle for later usage
            self.sessions[session_name]['gaze_path'] = gaze_path

            # make sure all dirs haven been created

            with open(gaze_path, "wb") as f:
                pickle.dump(gaze, f)

    def create_sanity_check_report(self):

        for session_name, session in self.sessions.items():
            report_file = open(self.output_dir / session_name / f"{session_name}_report.txt", "w", encoding="utf-8")
            gaze = self.get_gaze_frame(session_name)
            report = partial(report_meta, report_file=report_file)
            check_gaze(gaze, report)
            check_metadata(gaze._metadata, report)

            # TODO: implement the following functions in this class
            # check_all_screens_logfile(sanity.logfile, stimuli)
            # check_validations(gaze, messages)
            # check_instructions(messages, stimuli, sanity)

            report_file.close()


if __name__ == '__main__':
    data_collection_folder = 'MultiplEYE_ET_EE_Tartu_1_2025'

    this_repo = Path().resolve().parent

    data_folder_path = this_repo / "data" / data_collection_folder

    multipleye = MultipleyeDataCollection.create_from_data_folder(str(data_folder_path))

    multipleye.get_gaze_frame()

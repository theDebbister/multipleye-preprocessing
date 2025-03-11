import json
import pickle
from pathlib import Path
from pprint import pprint
import polars as pl
import re
import pandas as pd
import logging
from pymovements import GazeDataFrame
from tqdm import tqdm
from report import check_gaze, check_metadata,report_to_file as report_meta
from functools import partial

from data_collection import DataCollection
from plot import load_data, preprocess
from stimulus import load_stimuli, LabConfig, Stimulus
import os
from formal_experiment_checks import check_all_screens_logfile, check_all_screens, check_instructions
from et_quality_checks import check_validations, plot_gaze, plot_main_sequence


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
        logging.basicConfig()

    @classmethod
    def create_from_data_folder(cls, data_dir: str, additional_folder: str = 'core_dataset') -> "MultipleyeDataCollection":
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

        et_data_path = data_dir / 'eye-tracking-sessions' / additional_folder #ToDo: implement it more general to adhere to multipleye folder structure

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
            gaze_path = self.output_dir / session_name

            # / f"{session_name}_gaze.pkl"
            gaze_path.mkdir(parents=True, exist_ok=True)

            gaze_path = gaze_path / f"{session_name}_gaze.pkl"

            if gaze_path.exists() and not overwrite:
                # make sure gaze path is added if the pkl was created in a previous run
                self.sessions[session_name]['gaze_path'] = gaze_path
                logging.debug(f"Gaze data already exists for {session_name}.")

                return

            self.sessions[session_name]['gaze_path'] = gaze_path

            try:
                gaze = load_data(Path(self.sessions[session_name]['asc_path']), self.lab_configuration,
                                 session_idf=session_name)
            except KeyError:
                raise KeyError(
                    f"Session {session_name} not found in {self.data_root}.")
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"No asc file found for session {session_name}. Please create first.")

            logging.warning(f"Preprocessing gaze data for {session_name}. This might take a while.")

            preprocess(gaze)
            # save and load the gaze dataframe to pickle for later usage
            self.sessions[session_name]['gaze_path'] = gaze_path

            # make sure all dirs haven been created

            with open(gaze_path, "wb") as f:
                pickle.dump(gaze, f)

    def get_gaze_frame(self, session_identifier: str,
                       create_if_not_exists: bool = False,
                       ) -> GazeDataFrame:
        """
        Loads and possibly creates the gaze data for the specified session(s).
        :param create_if_not_exists: The gaze data will be created and stored if True.
        :param session_identifier: If (a) session identifier(s) is/are specified only the gaze data for this session is
        loaded. Otherwise, the gaze data for all sessions is loaded.
        :return:
        """

        if session_identifier not in self.sessions:
            raise KeyError(f'Session {session_identifier} not found in {self.data_root}.')

        try:
            # check if pkl files are already available
            gaze_path = Path(self.output_dir/ session_identifier).glob('*.pkl')

            if len(list(gaze_path)) == 1:
                gaze_path = Path(self.output_dir / session_identifier).glob('*.pkl')
                gaze_path = list(gaze_path)[0]
                self.sessions[session_identifier]['gaze_path'] = gaze_path
                logging.debug(f'Found pkl file for {session_identifier}.')
            else:
                raise FileNotFoundError

        except FileNotFoundError:
            if create_if_not_exists:
                self.create_gaze_frame(session=session_identifier)
                gaze_path = self.sessions[session_identifier]['gaze_path']
            else:
                raise KeyError(f'Gaze frame not created for session {session_identifier}. Please create first.')

        with open(gaze_path, "rb") as f:
            gaze = pickle.load(f)

        return gaze

    def create_sanity_check_report(self, sessions: str | list[str] | None = None, plotting: bool = True):

        if not sessions:
            sessions = (session_name for session_name, session in self.sessions.items())
        elif isinstance(sessions, str):
            sessions = [sessions]
        elif isinstance(sessions, list):
            sessions = sessions

        for session_name in tqdm(sessions, desc=f"performing sanity checks"):

            gaze = self.get_gaze_frame(session_name, create_if_not_exists=True)
            report_file = open(self.output_dir / session_name / f"{session_name}_report.txt", "a+", encoding="utf-8")

            report = partial(report_meta, report_file=report_file)
            self.sessions[session_name]['report_file'] = report_file
            self.load_logfiles(session_name)
            #check_gaze(gaze, report)
            check_metadata(gaze._metadata, report)
            report_file.close()


            self.check_logfiles(session_name)
            self.check_asc_all_screens(session_name, gaze)
            self.check_asc_instructions(session_name)
            self.check_asc_validation(session_name, gaze)
            if plotting:
                self.create_plots(session_name, gaze)



    def check_logfiles(self, session_identifier):
        """
        Check the logfile for the specified session.
        :param session_identifier: The session identifier.
        :return:
        """

        report_file = self.output_dir / session_identifier / f"{session_identifier}_report.txt"
        check_all_screens_logfile(self.sessions[session_identifier]["logfile"], self.stimuli, report_file)


    def create_plots(self, session_identifier, gaze=None):

        logging.info(f" creating plots for {session_identifier}.")

        if not gaze:
            logging.debug(f"Loading gaze data for {session_identifier}.")
            gaze = self.get_gaze_frame(session_identifier, create_if_not_exists=True)

        plot_dir = self.output_dir / session_identifier / f"{session_identifier}_plots"
        plot_dir.mkdir(exist_ok=True)

        plot_main_sequence(gaze.events, plot_dir)

        for stimulus in self.stimuli:
            logging.debug(f"Creating plots for {stimulus.name}.")
            plot_gaze(gaze, stimulus, plot_dir)



    def check_asc_instructions(self, session_identifier):
        """
        Check the instructions for the specified session.
        :param messages: The messages for the session.
        :param stimuli: The stimuli for the session.
        :param report_file: The report file.
        :return:
        """
        logging.debug(f"Checking asc file for {session_identifier} instructions.")
        messages = self._load_messages_for_experimenter_checks(session_identifier)
        report_file = self.output_dir / session_identifier / f"{session_identifier}_report.txt"
        check_instructions(messages, self.stimuli, report_file, self.sessions[session_identifier]["stimuli_order"])


    def load_logfiles(self, session_identifier):
        """
        Load the logfile for the specified session.
        :param session_identifier: The session identifier.
        :return: The logfile as a polars DataFrame, the completed stimuli and the stimuli order.
        """
        logfilepath = Path(f'{self.data_root}/{session_identifier}/logfiles')

        assert logfilepath.exists(), f"Logfile path {logfilepath} does not exist."
        logfile = logfilepath.glob("EXPERIMENT_*.txt")
        stim_path = logfilepath / 'completed_stimuli.csv'

        for log in logfile:
            logfile = pl.read_csv(log, separator="\t")
        completed_stimuli = pl.read_csv(stim_path, separator=","),
        stimuli_order = pl.read_csv(stim_path, separator=",")[
            "stimulus_id"].to_list()

        self.sessions[session_identifier]['logfile'] = logfile
        self.sessions[session_identifier]['completed_stimuli'] = completed_stimuli
        self.sessions[session_identifier]['stimuli_order'] = stimuli_order
        #return logfile, completed_stimuli, stimuli_order


    def _report_to_file(message: str, report_file: Path):
        assert isinstance(report_file, Path)
        with open(report_file, "a", encoding="utf-8") as report_file:
            report_file.write(f"{message}\n")
        # logging.info(message)

    def _load_messages_for_experimenter_checks(self, session_identifier: str):
        """
       qick fix for now, should be replaced by the summary experiment frame later on
        """
        REGEX = r'MSG\s+(?P<timestamp>\d+[.]?\d*)\s+(?P<message>.*)'
        asc_file = self.sessions[session_identifier]['asc_path']
        with open(asc_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        messages = []
        for line in lines:
            match = re.match(REGEX, line)
            if match:
                messages.append(match.groupdict())
        return messages


    def check_asc_validation(self, session_identifier, gaze=None):
        """
        Check the asc file for the specified session.
        :param session_identifier: The session identifier.
        :return:
        """
        logging.debug(f"Checking Validation for {session_identifier}.")
        messages = self._load_messages_for_experimenter_checks(session_identifier)
        if not messages:
            logging.error(f"No messages found in {session_identifier}.")
        if not gaze:
            logging.debug(f"Loading gaze data for {session_identifier}.")
            gaze = self.get_gaze_frame(session_identifier, create_if_not_exists=True)

        report_file = self.output_dir / session_identifier / f"{session_identifier}_report.txt"
        check_validations(gaze, messages, report_file)

    def check_asc_all_screens(self, session_identifier, gaze=None):
        """
        """
        logging.debug(f"Checking asc file all screens for {session_identifier} all screens.")

        if not gaze:
            logging.debug(f"Loading gaze data for {session_identifier}.")
            gaze = self.get_gaze_frame(session_identifier, create_if_not_exists=True)

        report_file = self.output_dir / session_identifier / f"{session_identifier}_report.txt"
        check_all_screens(gaze, self.stimuli, report_file)



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    data_collection_folder = 'MultiplEYE_ET_EE_Tartu_1_2025'

    this_repo = Path().resolve().parent

    data_folder_path = this_repo / "data" / data_collection_folder

    multipleye = MultipleyeDataCollection.create_from_data_folder(str(data_folder_path))
    #multipleye.add_recorded_sessions(data_root= data_folder_path / 'eye-tracking-sessions' / 'core_dataset', convert_to_asc=False, session_folder_regex=r"005_ET_EE_1_ET1")
    #multipleye.create_gaze_frame("005_ET_EE_1_ET1")
    multipleye.create_sanity_check_report(["005_ET_EE_1_ET1", "006_ET_EE_1_ET1"])

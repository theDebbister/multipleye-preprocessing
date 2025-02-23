import os
import pickle
import re
import subprocess
from pathlib import Path

import numpy as np
from pymovements import GazeDataFrame
from tqdm import tqdm

from plot import load_data, preprocess
from stimulus import load_stimuli

EYETRACKER_NAMES = {
    'eyelink': [
        'EyeLink 1000 Plus',
        'EyeLink II',
        'EyeLink 1000',
        'EyeLink Portable Duo',
    ],
}


def eyelink(method):
    def wrapper(self):
        if self.eye_tracker == 'eyelink':
            return method(self)
        else:
            raise ValueError(f'Function {method.__name__} is only supported for EyeLink data. '
                             f'You are using {self.eye_tracker}')

    return wrapper


class DataCollection:

    def __init__(self,
                 data_collection_name: str,
                 stimulus_language: str,
                 country: str,
                 year: int,
                 eye_tracker: str,
                 **kwargs,
                 ):
        """
        
        :param stimulus_language:
        :param country: 
        :param year:
        :param eye_tracker: 
        """
        self.session_folder_regex = ''
        self.data_root = ''
        self.output_dir = ''
        self.sessions = {}
        # TODO: in theory this can be multiple languages for the stimuli..
        self.language = stimulus_language
        self.country = country
        self.year = year
        self.data_collection_name = data_collection_name

        for short_name, long_name in EYETRACKER_NAMES.items():
            if eye_tracker in long_name:
                self.eye_tracker = short_name
                self.eye_tracker_name = long_name
                break

        else:
            raise ValueError(f'Eye tracker {eye_tracker} not yet supported. '
                             f'Supported eye trackers are: '
                             f'{np.array([val for k, val in EYETRACKER_NAMES.items()]).flatten()}')



    def add_recorded_sessions(self,
                              data_root: Path,
                              session_folder_regex: str = '',
                              session_file_suffix: str = '',
                              convert_to_asc: bool = False) -> None:
        """
        
        :param data_root: Specifies the root folder where the data is stored
        :param session_folder_regex: The pattern for the session folder names. It is possible to include infomration in
        regex groups. Those will be parsed directly and stored in the session object.
        Those folders should be in the root folder. If '' then the root folder is assumed to contain all files
        from the sessions.
        :param session_file_suffix: The pattern for the session file names. If no pattern is given, all files in the
        session folder are assumed to be the data files depending on the eye tracker.
        :return: 
        """

        self.data_root = data_root
        self.session_folder_regex = session_folder_regex

        if not session_file_suffix:
            # TODO: add configs for each eye tracker such that we don't always have to loop through all eye trackers
            #  but can write generic code. E.g. self.eye_tracker.session_file_regex
            if self.eye_tracker == 'eyelink':
                session_file_suffix = r'.edf'

        # get a list of all folders in the data folder
        if session_folder_regex:

            for item in os.scandir(self.data_root):
                if item.is_dir():
                    if re.match(session_folder_regex, item.name):

                        session_file = list(Path(item.path).glob('*' + session_file_suffix))

                        if len(session_file) == 0:
                            raise ValueError(f'No files found in folder {item.name} that match the pattern '
                                             f'{session_file_suffix}')
                        elif len(session_file) > 1:
                            raise ValueError(f'More than one file found in folder {item.name} that match the pattern '
                                             f'{session_file_suffix}. Please specify a more specific pattern and check '
                                             f'your data.')
                        else:
                            session_file = session_file[0]

                        # TODO: introduce a session object?
                        self.sessions[item.name] = {
                            'session_folder_path': item.path,
                            'session_file_path': session_file,
                            'session_file_name': session_file.name,
                            'session_folder_name': item.name,
                            'session_stimuli': ''
                        }

                        # check if asc files are already available
                        if not convert_to_asc and self.eye_tracker == 'eyelink':
                            asc_file = Path(item.path).glob('*.asc')
                            if len(list(asc_file)) == 1:
                                asc_file = list(asc_file)[0]
                                self.sessions[item.name]['asc_path'] = asc_file
                                print(f'Found asc file for {item.name}.')

                    else:
                        print(f'Folder {item.name} does not match the regex pattern {session_folder_regex}. '
                              f'Not considered as session.')
                elif item.is_file() and item.name.endswith('.edf'):
                    self.sessions[item.name] = {
                        'session_file_path': item.path,
                        'session_file_name': item.name,
                    }

        # TODO: somehow manage the case that the asc files are already available
        if convert_to_asc:
            self.convert_edf_to_asc()

    @eyelink
    def convert_edf_to_asc(self) -> None:

        if self.sessions is None:
            raise ValueError('No sessions added. Please add sessions first.')

        # TODO: make sure that edf2asc is installed on the computer
        for session in tqdm(self.sessions, desc='Converting EDF to ASC'):
            path = self.sessions[session]['session_file_path']

            if not path.with_suffix('.asc').exists():

                subprocess.run(['edf2asc', path])

                asc_path = path.with_suffix('.asc')
                self.sessions[session]['asc_path'] = asc_path
            else:
                asc_path = path.with_suffix('.asc')
                self.sessions[session]['asc_path'] = asc_path
                print(f'ASC file already exists for {session}.')

    def create_gaze_frame(self, session: str | list[str] = '', overwrite: bool = False) -> None:

        raise NotImplementedError

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
            gaze_path = self.sessions[session_identifier]['gaze_path']
        except KeyError:
            if create_if_not_exists:
                self.create_gaze_frame(session=session_identifier)
                gaze_path = self.sessions[session_identifier]['gaze_path']
            else:
                raise KeyError(f'Gaze frame not created for session {session_identifier}. Please create first.')

        with open(gaze_path, "rb") as f:
            gaze = pickle.load(f)

        return gaze

    # TODO: add method to check whether stimuli are completed

    # TODO: for future: think about how to handle stimuli in the general case


if __name__ == '__main__':
    pass

from pathlib import Path


class DataCollection:

    def __init__(self,
                 language: str,
                 country: str,
                 year: int,
                 eye_tracker: str,
                 kwargs: dict = None,
                 ):
        """
        
        :param language: 
        :param country: 
        :param year:
        :param eye_tracker: 
        """
        self.session_folder_regex = None
        self.data_root = None
        self.sessions = None
        self.language = language
        self.country = country
        self.year = year

        self.kwargs = kwargs

        supported_eye_trackers = ['eyelink']
        if eye_tracker == 'eyelink':
            self.eye_tracker = eye_tracker
        else:
            raise ValueError(f'Eye tracker {eye_tracker} not yet supported. '
                             f'Supported eye trackers are: {supported_eye_trackers}')

    def add_recorded_sessions(self,
                              data_root: str,
                              session_folder_regex: str = '',
                              session_file_regex: str = '',
                              convert_to_asc: bool = False):
        """
        
        :param data_root: Specifies the root folder where the data is stored
        :param session_folder_regex: The pattern for the session folder names. 
        Those folders should be in the root folder. If '' then the root folder is assumed to contain all the sessions.
        :param session_file_regex: The pattern for the session file names. If no pattern is given, all files in the
        session folder are assumed to be the data files depending on the eye tracker.
        :return: 
        """

        self.data_root = data_root
        self.session_folder_regex = session_folder_regex

        self.sessions = {}

        if not session_file_regex:
            if self.eye_tracker == 'eyelink':
                session_file_regex = '.*\.edf'

        full_regex = Path(session_folder_regex) / Path(session_file_regex)

        session_file_paths = Path(data_root).rglob(str(full_regex))
        print(session_file_paths)

        if convert_to_asc:
            self.convert_edf_to_asc()

        pass

    def convert_edf_to_asc(self):

        if not self.eye_tracker == 'eyelink':
            raise ValueError(f'Converting to asc is only supported for EyeLink data. '
                             f'You are using {self.eye_tracker}')

        if self.sessions is None:
            raise ValueError('No sessions added. Please add sessions first.')

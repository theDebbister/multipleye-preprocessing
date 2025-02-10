import os
import pickle
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import polars as pl

from plot import load_data, preprocess
from stimulus import load_stimuli


@dataclass
class Sanity:
    """Class for perfomring Sanity checks"""
    local_file_path: Path
    asc_file: Path
    stimulus_file_path: Path
    logfile_path: Path
    city: str
    year: str
    lang: str
    country: str
    labnum: str
    participant_abbr: str
    output_dir: Path
    json: Path
    experiment_config: Path
    report_file: Path
    plot_dir: Path
    logfile: pd.DataFrame
    completed_stimuli: pd.DataFrame
    stimuli_order: list
    gaze: pd.DataFrame = None

    def __post_init__(self):
        self.output_dir.mkdir(exist_ok=True)
        self.plot_dir.mkdir(exist_ok=True)
        self.stimuli_order = self.completed_stimuli["stimulus_id"].to_list()

    @classmethod
    def load(cls,
             path_asc_file: str,
             local_file_path: str,
             stimulus_file_path: str,
             logfile_path: str,
             ) -> "Sanity":
        regex = r"(?P<participant_number>\d{3})_(?P<lang>\w{2})_(?P<country>\w{2})_(?P<labnum>\d)_(?P<ET>ET\d)(?P<extra>_\w+)?\\(?P<participant_abbr>\w+).asc"
        stim_regex = r"stimuli_MultiplEYE_(?P<data_coll_abr>\w{2}_\w{2}_[a-zA-Z]+_\d_\d{4})"
        # TODO fix path  parsing problems, copatibility with windows and linux and then the regex parsing
        matches = re.search(regex, path_asc_file)
        vars_dict = matches.groupdict()
        stim_matches = re.search(stim_regex, stimulus_file_path)
        stim_dict = stim_matches.groupdict()
        vars_dict.update(stim_dict)

        if matches:
            print("Match was found at {start}-{end}: {match}".format(start=matches.start(), end=matches.end(),
                                                                     match=matches.group()))

            for groupNum in range(0, len(matches.groups())):
                groupNum = groupNum + 1

                print("Group {groupNum} found at {start}-{end}: {group}".format(groupNum=groupNum,
                                                                                start=matches.start(groupNum),
                                                                                end=matches.end(groupNum),
                                                                                group=matches.group(groupNum)))
            os.chdir(local_file_path)
            print(local_file_path)
            output_dir = Path(
                f"{local_file_path}\quality-report\output\{vars_dict['data_coll_abr']}")
            print(len(str(output_dir)))
            output_dir.mkdir(exist_ok=True)
            output_dir = output_dir / vars_dict['participant_abbr']
            output_dir.mkdir(exist_ok=True)
            plot_dir = Path(f"{output_dir}\{vars_dict['participant_abbr']}_plots")
            plot_dir.mkdir(exist_ok=True)

        else:
            raise ValueError("No match found")

        return cls(
            lang=vars_dict["lang"],
            city=vars_dict["data_coll_abr"].split("_")[2],
            country=vars_dict["country"],
            labnum=vars_dict["labnum"],
            year=vars_dict["data_coll_abr"].split("_")[4],
            local_file_path=Path(local_file_path),
            asc_file=Path(local_file_path) / Path(path_asc_file),
            stimulus_file_path=Path(stimulus_file_path),
            # output_dir=Path(f"{local_file_path}\quality-report\output\{vars_dict['data_coll_abr']}\{vars_dict['participant_abbr']}"),
            output_dir=output_dir,
            json=Path(f"{stimulus_file_path}\config\MultiplEYE_{vars_dict['data_coll_abr']}_lab_configuration.json"),
            participant_abbr=vars_dict["participant_abbr"],
            logfile_path=Path(logfile_path),
            experiment_config=Path(
                f"{stimulus_file_path}\config\config_{vars_dict['lang'].lower()}_{vars_dict['country'].lower()}_{vars_dict['data_coll_abr'].split('_')[2]}_{vars_dict['labnum']}_{vars_dict['data_coll_abr'].split('_')[4]}.py"),
            # report_file=Path(
            #    f"{local_file_path}\quality-report\output\{vars_dict['data_coll_abr']}\{vars_dict['participant_abbr']}_report.txt"),
            report_file=Path(f"{output_dir}\{vars_dict['participant_abbr']}_report.txt"),
            plot_dir=Path(f"{output_dir}\{vars_dict['participant_abbr']}_plots"),
            # plot_dir=Path(
            #    f"{local_file_path}\quality-report\output\{vars_dict['data_coll_abr']}\{vars_dict['participant_abbr']}_plots"),
            logfile=pl.read_csv(logfile_path, separator="\t"),
            completed_stimuli=pl.read_csv(Path(logfile_path).parent / "completed_stimuli.csv", separator=","),
            stimuli_order=pl.read_csv(Path(logfile_path).parent / "completed_stimuli.csv", separator=",")[
                "stimulus_id"].to_list()
        )

    @staticmethod
    def report_to_file(message: str, report_file: Path):
        assert isinstance(report_file, Path)
        with open(report_file, "a", encoding="utf-8") as report_file:
            report_file.write(f"{message}\n")

    def get_frame(self):

        ### Create or load gaze dataframe from ASC file, with the provided lab configuration
        ### Only execute if no gaze dataframe is available
        try:
            with open(self.output_dir / Path(f"{self.participant_abbr}_gaze.pkl"), "rb") as f:
                gaze = pickle.load(f)
        except FileNotFoundError:
            stimuli, lab_config = load_stimuli(self.stimulus_file_path, self.lang, self.country, self.labnum)
            gaze = load_data(self.asc_file, lab_config)
            preprocess(gaze)
            ### save and load the gaze dataframe to pickle for later usage
            with open(self.output_dir / f"{self.participant_abbr}_gaze.pkl", "wb") as f:
                pickle.dump(gaze, f)
            with open(self.output_dir / f"{self.participant_abbr}_gaze.pkl", "rb") as f:
                gaze = pickle.load(f)

        self.gaze = gaze
        return gaze


def main():
    path_asc_file = "data\\017_NL_NL_1_ET1_testrun_1733144369\\017nlnl1.asc"
    # path_asc_file ="data\\016_NL_NL_1_ET1\\016nlnl1.asc"
    path_asc_file = "data\\010_ZH_CH_1_ET1\\010zhch1.asc"
    # path_asc_file = "data\\003_HR_HR_1_ET1\\003hrhr1.asc"
    local_file_part = "C:\\Users\saphi\PycharmProjects\multipleye-preprocessing"
    stimulus_file_path = "C:\\Users\saphi\PycharmProjects\multipleye-preprocessing\data\stimuli_MultiplEYE_NL_NL_Nijmegen_1_2024"
    stimulus_file_path = "C:\\Users\saphi\PycharmProjects\multipleye-preprocessing\data\stimuli_MultiplEYE_ZH_CH_Zurich_1_2025"

    logfile_path = f"C:\\Users\saphi\PycharmProjects\multipleye-preprocessing\data\\017_NL_NL_1_ET1_testrun_1733144369\logfiles\EXPERIMENT_LOGFILE_1_017_2024-12-02_1733144369.txt"
    logfile_path = f"C:\\Users\saphi\PycharmProjects\multipleye-preprocessing\data\\010_ZH_CH_1_ET1\logfiles\EXPERIMENT_LOGFILE_1_010_2024-11-15_1731682963.txt"

    sanity = Sanity.load(path_asc_file, local_file_part, stimulus_file_path, logfile_path)
    print(sanity.output_dir)
    print(sanity.asc_file)
    gaze = sanity.get_frame()
    print(gaze)


if __name__ == "__main__":
    main()

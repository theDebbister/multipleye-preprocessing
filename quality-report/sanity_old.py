from pathlib import Path
import polars as pl
import pandas as pd
import re




def extract_information_file_path(path_asc_file, local_file_path, stimulus_file_path, logfile_path):
    regex = r"(?P<participant_number>\d{3})_(?P<lang>\w{2})_(?P<country>\w{2})_(?P<labnum>\d)_(?P<ET>ET\d)(?P<extra>_\w+)?\\(?P<participant_abbr>\w+).asc"
    stim_regex = r"stimuli_MultiplEYE_(?P<data_coll_abr>\w{2}_\w{2}_[a-zA-Z]+_\d_\d{4})"
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
    vars_dict["local_file_path"] = Path(local_file_path)
    vars_dict["asc_file"] = Path(local_file_path) / Path(path_asc_file)
    vars_dict["stimulus_file_path"] = Path(stimulus_file_path)
    vars_dict["city"] = vars_dict["data_coll_abr"].split("_")[2]
    vars_dict["year"] = vars_dict["data_coll_abr"].split("_")[4]
    output_dir = f"{vars_dict['local_file_path']}\quality-report\output\{vars_dict['data_coll_abr']}"
    output_dir = Path(output_dir)
    print(output_dir)
    output_dir.mkdir(exist_ok=True)
    vars_dict["output_dir"] = output_dir
    vars_dict["json"] = Path(
        f"{stimulus_file_path}\config\MultiplEYE_{vars_dict['data_coll_abr']}_lab_configuration.json")

    print(vars_dict['asc_file'].exists())
    vars_dict["experiment_config"] = Path(
        f"{stimulus_file_path}\config\config_{vars_dict['lang'].lower()}_{vars_dict['country'].lower()}_{vars_dict['city']}_{vars_dict['labnum']}_{vars_dict['year']}.py")
    vars_dict["report_file"] = output_dir / f"{vars_dict['participant_abbr']}_report.txt"
    plot_dir = vars_dict["output_dir"] / f"{vars_dict['participant_abbr']}_plots"
    plot_dir.mkdir(exist_ok=True)
    vars_dict["plot_dir"] = plot_dir
    logfile = pl.read_csv(logfile_path, separator="\t")
    vars_dict["logfile"] = logfile
    vars_dict["completed_stimuli"] = pl.read_csv(Path(logfile_path).parent / "completed_stimuli.csv", separator=",")
    # stimulus_order = pl.read_csv(vars_dict["completed_stimuli"], separator=",")
    vars_dict["stimuli_order"] = vars_dict["completed_stimuli"]["stimulus_id"].to_list()

    return vars_dict


def report_to_file(message: str, report_file: Path):
    assert isinstance(report_file, Path)
    with open(report_file, "a", encoding="utf-8") as report_file:
        report_file.write(f"{message}\n")


def main():
    path_asc_file = "data\\017_NL_NL_1_ET1_testrun_1733144369\\017nlnl1.asc"
    # path_asc_file ="data\\016_NL_NL_1_ET1\\016nlnl1.asc"
    # path_asc_file= "data\\010_ZH_CH_1_ET1\\010zhch1.asc"
    # path_asc_file = "data\\003_HR_HR_1_ET1\\003hrhr1.asc"
    local_file_part = "C:\\Users\saphi\PycharmProjects\multipleye-preprocessing"
    stimulus_file_path = "C:\\Users\saphi\PycharmProjects\multipleye-preprocessing\data\stimuli_MultiplEYE_NL_NL_Nijmegen_1_2024"
    # stimulus_file_path = "C:\\Users\saphi\PycharmProjects\multipleye-preprocessing\data\stimuli_MultiplEYE_ZH_CH_Zurich_1_2025"

    logfile_path = f"C:\\Users\saphi\PycharmProjects\multipleye-preprocessing\data\\017_NL_NL_1_ET1_testrun_1733144369\logfiles\EXPERIMENT_LOGFILE_1_017_2024-12-02_1733144369.txt"
    # logfile_path = f"C:\\Users\saphi\PycharmProjects\multipleye-preprocessing\data\\010_ZH_CH_1_ET1\logfiles\EXPERIMENT_LOGFILE_1_010_2024-11-15_1731682963.txt"

    vars_dict = extract_information_file_path(path_asc_file, local_file_part, stimulus_file_path, logfile_path)
    print(vars_dict["completed_stimuli"])


if __name__ == "__main__":
    main()

from pathlib import Path
import polars as pl
import pandas as pd
import re
import json
import PIL
import math
from report import check_gaze, check_metadata, preprocess, check_events, plot_gaze, report_to_file as report_meta, plot_main_sequence
from functools import partial
from stimulus import Stimulus

def extract_informatio_file_path(path_asc_file, local_file_path, stimulus_file_path, logfile_path):
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
    vars_dict["completed_stimuli"] = Path(logfile_path).parent / "completed_stimuli.csv"
    stimulus_order = pl.read_csv(vars_dict["completed_stimuli"], separator=",")
    vars_dict["stimuli_order"] = stimulus_order["stimulus_id"].to_list()

    return vars_dict




def report_to_file(message: str, report_file: Path):
    with open(report_file, "a", encoding="utf-8") as report_file:
        report_file.write(f"{message}\n")


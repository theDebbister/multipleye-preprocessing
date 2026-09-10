(technical_architecture)=

# Technical Architecture

This page covers the data layout, pEYEpline philosophy, and output structure.
For a detailed stage-by-stage breakdown, see {ref}`pipeline_stages`.

(multiplEYE_data_structure)=

## Data Structure

**A MultiplEYE dataset lives in one folder named by language, country, lab, and year.**
Inside you find the raw eye-tracking sessions, stimulus materials, psychometric test exports,
and participant questionnaires. The naming follows the pattern
`MultiplEYE_{LANG}_{COUNTRY}_{CITY}_{LAB}_{YEAR}` (e.g. `MultiplEYE_HR_HR_Zagreb_1_2025`).

The top-level folder looks like this:

```text
MultiplEYE_HR_HR_Zagreb_1_2025/
├── eye-tracking-sessions/          # one subfolder per participant
│   ├── 015_HR_hr_Zagreb_1_S1/     # session = participant + recording
│   │   ├── 015_HR_hr_Zagreb_1.edf
│   │   ├── 015_HR_hr_Zagreb_1.asc
│   │   └── logfiles/              # PsychoPy output
│   ├── 016_HR_hr_Zagreb_1_S1/
│   ├── pilot_sessions/            # optional
│   └── test_sessions/             # optional
├── psychometric-tests-sessions/   # raw PT exports per session
│   ├── 015_HR_hr_Zagreb_1_PT1/
│   │   ├── WMC/
│   │   ├── RAN/
│   │   ├── Stroop_Flanker/
│   │   ├── WikiVocab/
│   │   └── PLAB/
│   └── participant_configs_HR_hr_1/
├── stimuli_MultiplEYE_HR_HR_Zagreb_1_2025/
│   ├── aoi_HR_hr_1/
│   ├── stimuli_images_HR_hr_1/
│   ├── question_images_HR_hr_1/
│   ├── config/                    # lab config, stimulus order, metadata
│   ├── multipleye_stimuli_experiment_HR.xlsx
│   └── multipleye_comprehension_questions_HR.xlsx
├── participant_questionnaire_HR_hr_1_2025/
└── documentation/
```

**A session identifier carries the participant ID, language, country, lab, and session type.**
The format is `{PID}_{LANG}_{country}_{lab}_{session}`. For example `015_HR_hr_Zagreb_1_S1`
means participant 015, Croatian, lab Zagreb 1, eye-tracking session 1.
Session types are `S` / `ET` for eye-tracking and `PT` for psychometric tests.
The participant ID is always three digits and unique only within a dataset.

**The pEYEpline works session-by-session and assumes a fixed set of logfiles per session.**
Each session folder must contain an EDF (or ASC) file and a `logfiles/` subfolder with:

- `completed_stimuli.csv` — which stimuli the participant actually read
- `question_order_versions.csv` — which randomisation version was used
- `EXPERIMENT_{...}.txt` — trial-level log from PsychoPy
- `GENERAL_LOGFILE_{...}.txt` — contains the stimulus order version number

**Stimulus definitions live in the stimulus folder, shared across all sessions.**
The AOI files (`{stimulus}_aoi.csv` and `{stimulus}_aoi_questions.csv`) define word- and
character-level interest areas per stimulus. The config folder contains the lab hardware
settings, the stimulus order randomisation table, and the experiment metadata form.

## pEYEpline Philosophy

**Every stage reads the output of the previous stage and can be toggled on or off.**
The configuration YAML controls which stages run. Output files are cached on disk; when
`recalculate: false` the pEYEpline skips recomputation and validates file counts against the
expected number of completed stimuli.

**Two experiment types are supported through the same interface.** `MultiplEYE` uses one
session per participant. `MeRID` splits the stimulus order across two sessions — the
`MeridDataCollection` overrides the stimulus loading logic while keeping everything else
identical.

**The pEYEpline is batch-oriented.** It discovers all sessions in a data collection, runs a
preflight check on all of them, converts EDFs to ASC, loads session-level metadata, and
then loops over each session for the heavy computation (gaze processing, event detection,
reading measures, answers, sanity checks). Psychometric tests run once at the end over all
sessions.

**For a full stage-by-stage description, head over to {ref}`pipeline_stages`.**

(output_folder_structure)=

## Output Structure

**Everything lands in `preprocessed_data/{data_collection_name}/`, organised by stage.**
Each stage has its own folder with subfolders per session. This keeps the data tidy and
makes it easy to see what's been processed.

```text
preprocessed_data/{dcn}/
├── asc/                    # converted ASC files
├── raw_data/               # per-trial gaze samples
├── metadata/               # session metadata, calibrations, validations
├── fixations/              # detected fixations
├── saccades/               # detected saccades
├── scanpaths/              # AOI-mapped fixations
├── reading_measures/       # word-level reading measures
├── comp_answers/           # comprehension question answers
├── sanity_checks/          # quality reports and plots
├── psychometric_tests/     # PT overview + per-session details
├── participant_data.csv
├── {dcn}_overview.yaml
└── stimuli_{dcn}/          # copy of stimulus assets used
```

**Filenames follow a consistent pattern.** Per-trial files are named
`{sid}_{trial}_{stimulus}_{stage}.csv`. Psychometric test outputs use
`psychometric_overview_{dcn}.csv` (one row per session) and
`psychometric_overview_{dcn}_merged.csv` (sessions merged per participant when tests are
disjoint). The merged overview combines PT1 and PT2 data for the same subject.

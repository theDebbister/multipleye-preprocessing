(pipeline_stages)=

# pEYEpline Stages

This page documents each preprocessing stage in detail — what goes in, what comes out,
and what happens along the way. For the broader picture (data layout, output structure),
see {ref}`technical_architecture`.

```{mermaid}
graph TB
    subgraph Setup[Setup]
        direction LR
        A1[Prepare Data] --> A2[Preflight] --> A3[EDF → ASC]
    end
    subgraph Load[Session Loading]
        direction LR
        B1[Session Info] --> B2[Load Gaze] --> B3[Preprocess]
    end
    subgraph Events[Event Detection]
        direction LR
        C1[Fixation Detection]
        C2[Saccade Detection]
    end
    subgraph Analysis[Analysis]
        direction LR
        D1[AOI Mapping] --> D2[Reading Measures]
        D1 --> D3[Parse Answers]
    end
    subgraph Report[Quality & Summary]
        direction LR
        E1[Sanity Checks] --> E2[Participant CSV]
    end
    A3 --> B1
    B3 --> C1 & C2
    C1 & C2 --> D1
    C1 --> E1
    D3 --> E1
    A1 -.-> F[Psychometric Tests]
```

Stages 0–2 are preparation for all sessions. Stages 3–12 run per session in a loop.
Stage 13 is independent and runs once at the end, after all sessions are done.

(preprocessing_step_0)=

## Stage 0: Data Preparation

**Prepare the raw folder: extract archives, copy stimulus files, fix AOIs, and get
psychometric test data into shape.** This runs once before anything else. It handles the
messy reality of real data collections: tar archives that need unpacking, zip files per
participant, AOI CSV files that need splitting into text and question variants, and
old-format psychometric test data that needs restructuring from task-first to session-first.

The function is `prepare_language_folder()` in `scripts.prepare_language_folder`. It also
copies stimulus images, question images, and configuration files into the output folder so
the pEYEpline has everything it needs in one place. If the stimulus folder has changed since
the last run (e.g. after a team upload), the pEYEpline detects this automatically and
re-copies everything on the next run.

(preprocessing_step_1)=

## Stage 1: Preflight Check

**Validate every input file before the pEYEpline touches any data.** This catches missing
files early rather than failing midway. It checks that the stimulus XLSX files exist, every
session has its EDF and logfiles, all participant IDs appear in the stimulus order table,
and psychometric test folders are present if expected.

The check lives in `checks.preflight.run_preflight_check()`. It does not fail on the first
problem — it collects everything wrong and reports it all at once, so you can fix multiple
issues in one go. File matching is case-insensitive because operating systems differ.

(preprocessing_step_2)=

## Stage 2: EDF to ASC

**Convert EyeLink binary files to readable ASCII.** EyeTrackers record in `.edf` format,
which is proprietary. The pEYEpline calls the `edf2asc` binary from the EyeLink SDK to
produce `.asc` files that contain both the gaze samples and the timestamped messages that
encode trial structure.

The method is `MultipleyeDataCollection.convert_edf_to_asc()`. It runs the binary with
flags `-input -ftime -p <output_dir> -y` and copies the result to `asc/<sid>/<sid>.asc`.
If the ASC already exists and `FORCE_RECONVERT_ASC` is off, it skips. The `edf2asc` binary
cannot be distributed with the pEYEpline due to licensing.
See the {ref}`installation instructions <eyelink_dev_kit>` for how to obtain it from SR Research.

(preprocessing_step_3)=

## Stage 3: Session-Level Information

**Load everything about a session: what stimuli were read, what the logfiles say, and
which randomisation version was used.** This is where the raw session folder gets turned
into a rich `Session` object with all its metadata. The pEYEpline reads `completed_stimuli.csv`
to know which trials count, parses the ASC messages to get timestamps and reading times,
loads the experiment logfile for trial details, extracts the stimulus order version from
the general logfile, and builds a full list of `Stimulus` objects with their AOIs and
questions.

This is all done by `prepare_session_level_information()` in
`data_collection.multipleye_data_collection`. It also handles crashed sessions where a
participant had to restart — it detects the restart flag and adjusts the stimulus order
accordingly.

(preprocessing_step_4)=

## Stage 4: Gaze Data Loading

**Turn the ASC file into a structured gaze object with trials, pages, and activities.**
The pEYEpline uses `pymovements.gaze.from_asc()` with a set of regex patterns that decode
the experiment's message format. Each `start_recording_...` message marks a new recording
segment: reading a page, answering a question, or rating a stimulus. The patterns pull out
the trial number, stimulus name, page number, and activity type.

Two code paths exist. On first run, the ASC is parsed fresh and the per-trial raw CSVs are
saved. On subsequent runs, the cached CSVs are loaded back and stitched into a `Gaze`
object — this is faster and avoids re-parsing. Only data for completed stimuli (from
`completed_stimuli.csv`) is kept; aborted trials are discarded.

The entry points are `load_gaze_data()` and `load_trial_level_raw_data()` in `io.load`.

(preprocessing_step_5)=

## Stage 5: Signal Preprocessing

**Convert raw pixels to visual degrees and compute gaze velocity.** Raw eye-tracker
coordinates are in pixels, which means nothing without knowing the screen size and viewing
distance. The pEYEpline converts them to degrees of visual angle using the lab's hardware
settings (`LabConfig`). Then it computes velocity with a Savitzky-Golay filter — two passes,
50 ms window, polynomial degree 2. This cleaned signal is what the event detectors need.

All of this happens in `signals.preprocess.preprocess_gaze()`.

(preprocessing_step_6)=

## Stage 6: Fixation Detection

**Find fixations using a velocity threshold.** The I-VT algorithm marks samples below
20 deg/s as fixation and groups consecutive ones. The minimum fixation duration is 100 ms.
For each fixation found, the pEYEpline computes its centroid location and spatial dispersion.

The function is `events.detect.detect_fixations()`. Results are saved as per-trial CSVs
in `fixations/<sid>/`.

(preprocessing_step_7)=

## Stage 7: Saccade Detection

**Detect saccades with a noise-adaptive threshold.** Unlike fixations, saccades are fast
eye movements. The algorithm adapts the velocity threshold to the noise level of each
recording. Minimum duration is 6 samples (roughly 12 ms at 500 Hz). Properties computed
include amplitude in degrees, peak velocity, and dispersion.

The function is `events.detect.detect_saccades()`. Results go to `saccades/<sid>/`.

(preprocessing_step_8)=

## Stage 8: AOI Mapping and Scanpaths

**Map every fixation to the word and character the participant was looking at.** Using
the AOI files from the stimulus folder, each fixation gets annotated with a character
index, word index, line number, and page. This turns a list of coordinates into a reading
scanpath.

The function `mapping.aoi.map_fixations_to_aois()` collects all AOIs from the stimulus
definitions and calls `pymovements`'s built-in mapping. The annotated fixations are saved
as scanpath CSVs in `scanpaths/<sid>/`.

(preprocessing_step_9)=

## Stage 9: Reading Measures

**Calculate word-level eye-movement measures from the scanpath.** This is where the
pEYEpline produces the numbers that most reading researchers care about: how long did
someone look at a word, did they regress, did they refixate. The pEYEpline first annotates
fixations with run IDs and pass flags (first-pass vs regression), then computes measures
for each word.

Measures include total fixation count (TFC), first-fixation duration (FFD), first-pass
reading time (FPRT), regression-path duration (RPD), and about a dozen more. The full list
is documented in the {ref}`reading_measures` section.

The entry point is `metrics.calculate.calculate_reading_measures()`.

(preprocessing_step_10)=

## Stage 10: Comprehension Answers

**Extract what answers participants gave to comprehension questions and whether they
were correct.** The primary source is the ASC file itself — the experiment software logs
`preliminary_answer`, `final_answer_given_is_...`, and `answer_given_is_correct:...`
messages with millisecond timestamps. These give you both response times and accuracy.

If ASC messages are unavailable (some data collections have this gap), the pEYEpline falls
back to the EXPERIMENT logfile, which has the final answer and correctness but no response
times. A warning is logged in that case.

The parsed answers are then combined with the participant's question order version and the
stimulus definitions to produce a full answer table with trial, stimulus, question ID,
condition (local/bridging/global), response, correctness, and RTs. Saved to
`comp_answers/<sid>/<sid>_answers.csv`.

The relevant modules are in `answers/`: `msg_parser.py`, `experiment_log_parser.py`,
`collect.py`.

(preprocessing_step_11)=

## Stage 11: Sanity Checks and Reports

**Generate quality reports at the session and dataset level.** This stage produces text
reports on calibration quality, validation scores, data loss, fixation statistics per page,
per-trial data loss, and logfile consistency. It also creates plots (gaze-over-stimulus, main sequence) that
help spot problematic sessions visually.

Session overviews and a dataset overview YAML are written to the metadata folder. The
checks live in `checks/et_quality_checks.py` and `checks/formal_experiment_checks.py`.
See {ref}`sanity_check_report` for a complete description of every field in the report output.

(preprocessing_step_12)=

## Stage 12: Participant Data

**Aggregate questionnaire data into a single CSV.** Participant questionnaires are stored
as individual JSON files. This step reads them all, fixes a known key-naming bug from
earlier experiment versions, and writes a tidy `participant_data.csv`.

(preprocessing_step_13)=

## Stage 13: Psychometric Tests

**Process psychometric test exports into summary metrics.** Six tests are supported:
working memory (LWMC), rapid automatised naming (RAN), Stroop, Flanker, vocabulary
(WikiVocab/LexTALE), and language aptitude (PLAB). Each has its own preprocessing function
in `psychometric_tests.preprocess_psychometric_tests`.

The output is an overview CSV with one row per session (key metrics only, like accuracy
effects and mean RTs) and a detailed CSV per session with all computed values. An
additional merged overview combines PT1 and PT2 sessions for the same participant when
their tests don't overlap.

## Configuration

**Everything is controlled by a single YAML file and a global `Settings` object.**
The config sets the data collection name, which stages to run, quality thresholds, and
logging verbosity. The pEYEpline looks for it in this order:

1. `--config_path` argument
2. `MULTIPLEYE_CONFIG` environment variable
3. `multipleye_settings_preprocessing.yaml` in the current directory
4. Auto-detected from the folder name (creates a template)

See the {ref}`configuration_guide` for all available settings.

## Package Architecture

**The `preprocessing` package is organised by function, with a flat public API.**
Internal modules live in subpackages (`io/`, `events/`, `signals/`, `mapping/`,
`metrics/`, `answers/`, `checks/`, `psychometric_tests/`, `data_collection/`, `models/`,
`utils/`, `scripts/`). The `api.py` facade re-exports all key functions so users can
call `preprocessing.load_gaze_data(...)` instead of digging into submodules.

The main data classes form a hierarchy: `MultipleyeDataCollection` owns a dict of
`Session` objects, each of which owns lists of `Stimulus` and `Trial` objects. For
two-session experiments, `MeridDataCollection` extends the base class and overrides only
the stimulus order logic.

**The pEYEpline caches aggressively.** Every stage checks whether its output already
exists on disk. If it does and `recalculate` is false, the stage loads the cached result
instead of recomputing. The number of cached files is validated against the list of
completed stimuli to catch partial or corrupted runs.

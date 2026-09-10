(psychometric_tests)=

# Psychometric Tests

To obtain results for the psychometric tests, the recorded data has to be processed. This page
explains the steps involved in the processing. Furthermore, some background information about the
psychometric tests is provided.

## Table of Contents

- [Data Collection](#data_collection)
- [Theoretical Background](#theoretical_background)
    - [Lewandowsky WMC Battery](#lewandowsky_wmc_battery_test)
    - [Rapid Automatized Naming (RAN)](#rapid_automatized_naming_test)
    - [Stroop Test](#stroop_test)
    - [Flanker Task](#flanker_test)
    - [PLAB (Pimsleur Language Aptitude Battery)](#plab_test)
    - [WikiVocab](#wikivocab_test)
- [Calculating the Psychometric Tests](#calculating_psychometric_tests)
    - [Preparing the Data](#preparing_data)
    - [Running the Calculations](#running_calculations_psychometric)

(data_collection)=

## Data Collection

Data for the psychometric tests have been collected using the [
`MultiplEYE-psychometric-tests`](https://github.com/MultiplEYE-COST/MultiplEYE-psychometric-tests)
repository. Find details about it in the project's `README.md`.

(theoretical_background)=

## Theoretical Background

The psychometric tests in the MultiplEYE battery are carefully selected to provide a comprehensive
assessment of cognitive abilities relevant to language processing and eye-tracking research. Each
test targets specific cognitive domains while maintaining cross-linguistic validity and experimental
efficiency.

(lewandowsky_wmc_battery_test)=

### Lewandowsky WMC Battery

Working Memory Capacity (WMC) is a fundamental cognitive construct that represents the amount of
information that can be temporarily stored and manipulated to support higher-level cognitive
processes (such as text comprehension). WMC is correlated with general intelligence (g-factor),
language comprehension, and reading ability {cite:p}`Daneman1980`. The Lewandowsky WMC battery
assesses two working memory domains (verbal/numerical and spatial)
through four complementary tasks:

- **Memory Update (MU)**: Participants continuously update a running memory store with new
  information while discarding old items. This task measures the ability to dynamically manipulate
  information in working memory.
- **Operation Span (OS)**: Participants must remember items while performing simple mathematical
  operations, capturing the dual-processing demands of working memory.
- **Sentence Span (SS)**: Similar to OS but with sentence verification tasks instead of mathematical
  operations, tapping verbal working memory specifically relevant to language processing.
- **Spatial Short-Term Memory (SSTM)**: Assesses visuospatial memory through recall of spatial
  sequences, providing a non-verbal complement to the verbal tasks.

Our implementation follows the methodology described in {cite:t}`Lewandowsky2010`, specifically the
data format and scoring details outlined in the appendix. The scoring approach calculates the
proportion of items recalled correctly for each trial, then computes the mean of these trial-level
proportions to obtain the final task score. This method ensures that each task contributes equally
to the overall WMC construct, regardless of differences in the number of trials or set sizes across
tasks.

For each trial, the score is calculated as the proportion of correctly recalled items:

$$\mathrm{Trial\_Score}_{\mathrm{task}} = \frac{\sum \mathrm{correct\_items\_in\_trial}}{\mathrm{num\_items\_in\_trial}}$$

The final task score is the mean of all trial scores:

$$\mathrm{Task\_Score} = \mathrm{mean} (\mathrm{Trial\_Score}_{\mathrm{task}})$$

For the spatial task is scored on pattern similarity, computed as the sum of the dot-to-dot
similarities. This dot-to-dot similarity is understood by "awarding 2 points for no distance between
a recalled dot and a presented dot, 1 point for a deviation of one cell in any direction, and 0
points if the deviation exceeded one cell". Finally, this score is normalized:

$$\mathrm{SSTM\_Score} = \frac{\mathrm{SSTM\_raw\_score}}{240.0}$$

The total WMC score is the average across all tasks:

$$\mathrm{Total\_Score} = \frac{\mathrm{MU\_Score} + \mathrm{OS\_Score} + \mathrm{SS\_Score} + \mathrm{SSTM\_Score}}{4.0}$$

This implementation processes data from CSV files rather than the original .dat format described in
the paper, but maintains the same scoring logic and produces equivalent results. For the spatial
task, we extract the raw score from the .dat file and normalize it by dividing by 240.0, consistent
with the maximum attainable score in the current version.

**Returned Results**:

- `LWMC_MU_score`: Memory Update task score
- `LWMC_OS_score`: Operation Span task score
- `LWMC_OS_processingTask_score`: Equation accuracy for Operation Span
- `LWMC_SS_score`: Sentence Span task score
- `LWMC_SentS_processingTask_score`: Sentence truth-value accuracy for Sentence Span
- `LWMC_SSTM_score`: Spatial Short-Term Memory task score
- `LWMC_Total_score_mean`: Average score across all four tasks

*Note: The processing task scores (OS and SentS) are included in the overview to validate
participant engagement.*

*Detailed outputs*:

- `LWMC_MU_time_sec`: Mean response time for Memory Update
- `LWMC_OS_time_sec`: Mean response time for Operation Span
- `LWMC_SS_time_sec`: Mean response time for Sentence Span

(rapid_automatized_naming_test)=

### Rapid Automatized Naming (RAN)

Rapid Automatized Naming is a classic measure of processing speed and automaticity in cognitive
retrieval. Originally developed to predict reading ability, RAN assesses the efficiency with which
participants can access and articulate phonological word forms corresponding to visually presented
stimuli. The task is described as a "microcosm" of reading as it involves sequential shifts of
visual attention, lexical access, and articulatory planning {cite:p}`WolfBowers1999`. The task
requires participants to name a series of familiar items (typically digits or letters) as quickly as
possible. RAN performance is strongly predictive of reading fluency across languages and is
considered a marker of the automaticity of cognitive processes {cite:p}`Denckla1976`.

For our data, there are two trials per session. Both trials consist of a $5 \times 10$ digit matrix.
The results are the times each of the two trials took to complete.

**Returned Results**:

- `RAN_practice_rt_sec`: Reaction time for practice trial
- `RAN_experimental_rt_sec`: Reaction time for experimental trial

(stroop_test)=

### Stroop Test

The Stroop test is one of the most widely used measures of cognitive control and inhibitory
functioning. It demonstrates the phenomenon of interference---when automatic processing (reading)
conflicts with task demands (color naming). In the color-word Stroop, participants must inhibit the
automatic tendency to read words while naming the font color. The difference in performance between
congruent (word matches color) and incongruent (word conflicts with color) trials provides a
sensitive measure of inhibitory control {cite:p}`Stroop1935`.

To ensure data quality, reaction times below a minimum threshold (default 200ms) or above a maximum
threshold (default infinity) are excluded from all calculations (reaction time means, accuracy, and
trial counts) as they likely represent accidental key presses or lapses in attention.

**Mathematical Formulas**:

For each condition (incongruent, congruent, neutral), basic metrics are calculated as:

$$\mathrm{Accuracy}_{\mathrm{condition}} = \frac{\sum \mathrm{correct\_trials}_{\mathrm{condition}}}{\mathrm{total\_trials}_{\mathrm{condition}}}$$

$$\mathrm{RT}_{\mathrm{condition}} = \mathrm{mean} (\mathrm{rt}_{\mathrm{condition}})$$

Interference effects (focused on congruent vs incongruent comparison):

$$\mathrm{AccuracyEffect} = \mathrm{Accuracy}_{\mathrm{incongruent}} - \mathrm{Accuracy}_{\mathrm{congruent}}$$

$$\mathrm{RTEffect}_{\mathrm{sec}} = \mathrm{RT}_{\mathrm{incongruent}} - \mathrm{RT}_{\mathrm{congruent}}$$

**Returned Results**:

- `StroopAccuracyEffect`: Accuracy interference effect
- `StroopRTEffect_sec`: Reaction time interference effect
- `Stroop_incongruent_correct_rt_mean_sec`: Mean RT for correct incongruent trials
- `Stroop_congruent_correct_rt_mean_sec`: Mean RT for correct congruent trials

*Detailed outputs*:

- `Stroop_incongruent_rt_mean_sec`: Mean RT for incongruent trials (filtered by minimum RT)
- `Stroop_incongruent_correct_rt_mean_sec`: Mean RT for correct incongruent trials (filtered by
  minimum RT)
- `Stroop_incongruent_accuracy`: Accuracy for incongruent trials
- `Stroop_incongruent_num_items`: Number of incongruent trials
- `Stroop_congruent_rt_mean_sec`: Mean RT for congruent trials (filtered by minimum RT)
- `Stroop_congruent_correct_rt_mean_sec`: Mean RT for correct congruent trials (filtered by minimum
  RT)
- `Stroop_congruent_accuracy`: Accuracy for congruent trials
- `Stroop_congruent_num_items`: Number of congruent trials
- `Stroop_neutral_rt_mean_sec`: Mean RT for neutral trials (filtered by minimum RT)
- `Stroop_neutral_correct_rt_mean_sec`: Mean RT for correct neutral trials (filtered by minimum RT)
- `Stroop_neutral_accuracy`: Accuracy for neutral trials
- `Stroop_neutral_num_items`: Number of neutral trials

(flanker_test)=

### Flanker Task

The Flanker task complements the Stroop by measuring inhibitory control in a spatial attention
domain. Participants must respond to a central target while ignoring surrounding "flanker"
distractors. The task creates conflict between automatic attentional capture by the flankers and the
goal-directed focus on the target. Like the Stroop, the difference between incongruent and congruent
conditions provides a measure of cognitive control, but through spatial rather than semantic
interference {cite:p}`Eriksen1974`.

By default, no minimum reaction time filter is applied to the Flanker task, as processing of purely
visual stimuli is faster and simpler than semantic processing.

**Mathematical Formulas**:

For each condition (incongruent, congruent), basic metrics are calculated as:

$$\mathrm{Accuracy}_{\mathrm{condition}} = \frac{\sum \mathrm{correct\_trials}_{\mathrm{condition}}}{\mathrm{total\_trials}_{\mathrm{condition}}}$$

$$\mathrm{RT}_{\mathrm{condition}} = \mathrm{mean} (\mathrm{rt}_{\mathrm{condition}})$$

Spatial interference effects:

$$\mathrm{AccuracyEffect} = \mathrm{Accuracy}_{\mathrm{incongruent}} - \mathrm{Accuracy}_{\mathrm{congruent}}$$

$$\mathrm{RTEffect}_{\mathrm{sec}} = \mathrm{RT}_{\mathrm{incongruent}} - \mathrm{RT}_{\mathrm{congruent}}$$

**Returned Results**:

- `FlankerAccuracyEffect`: Accuracy interference effect
- `FlankerRTEffect_sec`: Reaction time interference effect
- `Flanker_incongruent_correct_rt_mean_sec`: Mean RT for correct incongruent trials
- `Flanker_congruent_correct_rt_mean_sec`: Mean RT for correct congruent trials

*Detailed outputs*:

- `Flanker_incongruent_rt_mean_sec`: Mean RT for incongruent trials
- `Flanker_incongruent_correct_rt_mean_sec`: Mean RT for correct incongruent trials
- `Flanker_incongruent_accuracy`: Accuracy for incongruent trials
- `Flanker_incongruent_num_items`: Number of incongruent trials
- `Flanker_congruent_rt_mean_sec`: Mean RT for congruent trials
- `Flanker_congruent_correct_rt_mean_sec`: Mean RT for correct congruent trials
- `Flanker_congruent_accuracy`: Accuracy for congruent trials
- `Flanker_congruent_num_items`: Number of congruent trials

(plab_test)=

### PLAB (Pimsleur Language Aptitude Battery)

The PLAB test assesses language learning aptitude through a battery of tasks that measure different
components of language ability. Unlike the other cognitive tests, PLAB specifically targets
metalinguistic awareness and the ability to consciously infer and apply grammatical rules and
generalizations. This makes it particularly valuable for research on multilingualism and language
learning {cite:p}`Pimsleur2004`.

**Returned Results**:

- `PLAB_rt_mean_sec`: Mean reaction time across all PLAB trials
- `PLAB_accuracy`: Overall accuracy across all PLAB trials
- `PLAB_set1_accuracy`: Accuracy for items 1-4
- `PLAB_set2_accuracy`: Accuracy for items 5-15
- `PLAB_set1_rt_mean_sec`: Mean RT for items 1-4
- `PLAB_set2_rt_mean_sec`: Mean RT for items 5-15

*Detailed outputs*:

- `PLAB_num_items`: Total number of PLAB trials

(wikivocab_test)=

### WikiVocab

WikiVocab is a modern vocabulary assessment that uses items drawn from Wikipedia corpora across
multiple languages. It provides a cross-linguistically valid measure of vocabulary breadth by
including both real words and carefully constructed pseudo-words. Vocabulary breadth is
operationalized as the number of words for which a person has at least partial knowledge. The
balanced scoring approach (averaging performance on real and pseudo-words) helps control for
individual response tendencies, such as a bias towards accepting or rejecting items, and makes it
comparable across languages with different writing systems and vocabulary structures {cite:p}
`vanRijn2023`.

Reaction times are filtered by a minimum threshold (default 200ms) and a maximum threshold (default
infinity) to exclude extreme responses (e.g., accidental key presses or attention lapses). Trials
outside this range are excluded from all metrics, including the balanced LexTALE score.

- Large, representative item pools from Wikipedia
- Balanced scoring controls for response biases
- Cross-linguistic comparability through pseudo-word calibration
- For some languages, equivalent to LexTALE (Lextale.com scoring)

**Mathematical Formulas**:

Accuracy calculations for real and pseudo words:

$$\mathrm{Real\_Correct} = \frac{\mathrm{correct\_real\_words}}{\mathrm{total\_real\_words}}$$

$$\mathrm{Pseudo\_Correct} = \frac{\mathrm{correct\_pseudo\_words}}{\mathrm{total\_pseudo\_words}}$$

Balanced LexTALE-style scoring:

$$\mathrm{Incorrect\_Correct\_Score} = \frac{\mathrm{Real\_Correct} + \mathrm{Pseudo\_Correct}}{2}$$

**Returned Results**:

- `WikiVocab_rt_mean_sec`: Mean reaction time across all trials (filtered by minimum RT)
- `WikiVocab_accuracy`: Overall accuracy across all trials
- `WikiVocab_incorrect_correct_score`: Balanced LexTALE-style score
- `WikiVocab_correct_words_rt_mean_sec`: Mean RT for correct real word responses
- `WikiVocab_correct_pseudowords_rt_mean_sec`: Mean RT for correct pseudoword responses
- `WikiVocab_ratio_items`: Ratio of real words to pseudowords (detailed only)

*Detailed outputs*:

- `WikiVocab_num_items`: Total number of items
- `WikiVocab_num_pseudo_words`: Number of pseudo-word items
- `WikiVocab_num_real_words`: Number of real word items
- `WikiVocab_pseudo_correct`: Fraction correct for pseudo words
- `WikiVocab_real_correct`: Fraction correct for real words
- `WikiVocab_overall_correct`: Overall fraction correct

(calculating_psychometric_tests)=

## Calculating the Psychometric Tests

As hinted in the {ref}`running_pipelines` section, there are project scripts for the psychometric
tests. But before calculation, the input data must be structured correctly.

(preparing_data)=

### Preparing the Data

For each session, there should be a folder containing one subfolder for each test with its data. The
data should be structured as follows, i.e. for the session identifier (sid)
`008_SQ_CH_1_PT2` and data collection identifier `MultiplEYE_SQ_CH_Zurich_1_2025`:

```text
data/MultiplEYE_SQ_CH_Zurich_1_2025/psychometric-tests-sessions/
├── ...
├── 008_SQ_CH_1_PT2
│   ├── 008_SQ_CH_1_PT2.yaml
│   ├── PLAB
│   │   ├── SQCH1_008_PT2_2025-09-13_15-18-01.csv
│   │   ├── SQCH1_008_PT2_2025-09-13_15-18-01.log
│   │   └── SQCH1_008_PT2_2025-09-13_15-18-01.psydat
│   ├── RAN
│   │   ├── SQCH1_008_PT2_2025-09-13_15-12-11.log
│   │   ├── SQCH1_8_S2_2025-09-13_15-12-11.csv
│   │   └── audio_SQCH1_008_PT2_2025-09-13_15-12-11
│   │       ├── SQCH1_8_S2_trial1.wav
│   │       └── SQCH1_8_S2_trial2.wav
│   ├── Stroop_Flanker
│   │   ├── SQCH1_008_PT2_2025-09-13_15-13-23.csv
│   │   ├── SQCH1_008_PT2_2025-09-13_15-13-23.log
│   │   └── SQCH1_008_PT2_2025-09-13_15-13-23.psydat
│   ├── WMC
│   │   ├── MU-8.dat
│   │   ├── OS-8.dat
│   │   ├── SQCH1_008_PT2_2025-09-13_14-31-31.csv
│   │   ├── SQCH1_008_PT2_2025-09-13_14-31-31.log
│   │   ├── SQCH1_008_PT2_2025-09-13_14-31-31.psydat
│   │   ├── SS-8.dat
│   │   ├── SSTM-8.dat
│   │   └── sstm_detailed
│   │       └── SSTM-8.dat
│   ├── WikiVocab
│   │   ├── SQCH1_008_PT2_2025-09-13_15-26-53.csv
│   │   └── images
│   └── psychometric_details_008_SQ_CH_1_PT2.csv
```

If it happens that the data is structured first by the test folder and then by session folder,
`prepare_language_folder` and the preflight check will detect this and restructure the data
automatically. The `restructure_psycho_tests` CLI tool can still be used as a fallback. This can be
invoked like this:

```bash
restructure_psycho_tests
```

In short, if your data structure looks like below, `restructure_psycho_tests` can format it into the
desired structure as shown above.

```text
data/MultiplEYE_SQ_CH_Zurich_1_2025/psychometric-tests-sessions/core_data/
├── PLAB
│   ├── 001_SQ_CH_1_PT2
│   ├── ...
│   └── 026_SQ_CH_1_PT1
├── RAN
│   ├── 001_SQ_CH_1_PT2
│   ├── ...
│   └── 026_SQ_CH_1_PT1
├── Stroop_Flanker
│   ├── 001_SQ_CH_1_PT2
│   ├── ...
│   └── 026_SQ_CH_1_PT1
├── WMC
│   ├── 001_SQ_CH_1_PT2
│   ├── ...
│   └── 026_SQ_CH_1_PT1
├── WikiVocab
│   ├── 001_SQ_CH_1_PT2
│   ├── ...
│   └── 026_SQ_CH_1_PT1
└── participant_configs_SQ_CH_1
    ├── 001_SQ_CH_1_PT2.yaml
    ├── ...
    └── 026_SQ_CH_1_PT1.yaml
```

Usually, the command needs no arguments, if the {ref}`configuration_guide` was correctly set up.
Otherwise, you can find out how to overwrite the global settings by invoking
`restructure_psycho_tests --help`. If one session did not finish all tests, this is no problem. For
the sessions where this is the case, the tests that do not have data will be logged to the console.
The following calculation has been constructed to handle this case, only calculating the results of
tests with existing data.

(running_calculations_psychometric)=

### Running the Calculations

The psychometric test calculations are performed as part of the main pEYEpline (via
`run_preprocessing`, gated by `RUN_PSYCHOMETRIC_TESTS`), or standalone via the
`preprocess_psychometric_tests()` function. Both process each test separately and combine the
results into overview and detailed output files.

#### Output Location

All psychometric test results are written to
`preprocessed_data/{data_collection_id}/psychometric_tests/`.

#### Overview vs. Detailed Output

The pEYEpline generates two types of output:

- **Overview file** (`psychometric_overview_{data_collection_id}.csv`): Contains one row per session
  with primary metrics as per the original paper outputs.
- **Merged overview file** (`psychometric_overview_{data_collection_id}_merged.csv`): Contains one
  row per participant, merging disjoint PT sessions (e.g. PT1 with PT2).
- **Detailed file** (`psychometric_details_{session_id}.csv`): Per-session CSV with all detailed
  values, written to a subfolder named after the session.

#### Command Line Usage

The tests can be calculated as part of the full pEYEpline:

```bash
run_preprocessing --config_path path/to/your_config.yaml
```

Or standalone:

```bash
preprocess_psychometric_tests
```

For details on how to overwrite the global settings, run `preprocess_psychometric_tests --help`.

#### Data Handling

The calculations automatically handle missing data. If a participant didn't complete certain tests,
those values will be omitted from the output files and logged to the console. This ensures robust
processing even with incomplete datasets.

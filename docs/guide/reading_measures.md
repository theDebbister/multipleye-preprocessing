(reading_measures)=

# Reading Measures

**Reading measures are word-level eye-movement metrics calculated from AOI-mapped
fixations.** The pEYEpline computes them per trial by first annotating fixations with run
and pass information, then deriving a set of standard measures for each word. The
implementation lives in `metrics.reading.reading_measures`.

## Fixation Annotation

**Every fixation gets tagged with a run ID, first-pass status, regression flags, and
neighbouring word indices.** This annotation is the foundation for all measures. The
pEYEpline groups fixations by trial, stimulus, and page, then computes:

- `run_id` — contiguous fixations on the same word form a run. Each time the reader moves
  to a different word and comes back, a new run starts.
- `is_first_pass` — a run is first-pass if the word is entered from the left, no higher
  word index has been fixated before, and the word has not been entered before. All
  later revisits (regressions-in) are marked as non-first-pass.
- `is_reg_in` / `is_reg_out` — a regression occurs when the next fixation lands on a
  lower (regression-out) or the previous fixation came from a higher (regression-in) word
  index.
- `is_first_fix` — the very first fixation on the word in the entire trial.
- `prev_word_idx` / `next_word_idx` — word indices of the preceding and following
  fixation, used for saccade length calculation.

## Fixation-based Measures

| Abbreviation | Description |
|---|---|
| **FFD** | Duration of the first fixation on a word during first-pass reading, 0 if skipped in first-pass |
| **FD** | Duration of the first fixation on the word, regardless of pass |
| **FPF** | 1 if the word was fixated in first-pass, 0 otherwise |
| **FPFC** | Number of first-pass fixations on the word |
| **FPRT** | Sum of all first-pass fixation durations (0 if skipped) |
| **FRT** | Sum of fixations from first entering the word until first leaving it (same as FPRT when the first run was first-pass) |
| **TFC** | Total number of fixations on the word |
| **TFT** | Sum of all fixations (FPRT + RRT) |
| **RR** | 1 if the word had re-reading after first-pass, 0 otherwise |
| **RRT** | Sum of fixations that are not part of first-pass (TFT - FPRT) |
| **SFD** | Duration of the only first-pass fixation; 0 if skipped or multiple first-pass fixations |

## Transition-based Measures

| Abbreviation | Description |
|---|---|
| **LP** | Character index of the first fixation on the word (landing position) |
| **RBRT** | Sum of fixation durations on the word until a word to its right is fixated (RPD_inc - RPD_exc) |
| **RPD_exc** | Sum of regressive fixation durations after a first-pass regression until fixating a word to the right, excluding fixations on the word itself |
| **RPD_inc** | Sum of all fixations from first first-pass fixation on the word until fixating a word to its right (includes regressive fixations); 0 if not fixated in first-pass |
| **SL_in** | Saccade length leading to the first fixation on the word (in words); positive = progressive, negative = regressive |
| **SL_out** | Saccade length of the first saccade leaving the word (in words) |
| **TRC_in** | Number of regressive saccades landing on this word |
| **TRC_out** | Number of regressive saccades initiated from this word |

## Output Format

**Reading measures are saved as one CSV per trial in `reading_measures/<sid>/`.**
The filename follows the pattern `{sid}_{trial}_{stimulus}_reading_measures.csv`.
Each row is a word, with columns for the trial identifier, page number, word index, word
text, and all measures above. Words that were never fixated have zeros in all measure
columns and are marked as `skipped = 1`.

## AOI Enlargement

**AOIs are enlarged vertically before mapping to cover the space between lines.**
The original AOIs from the stimulus files only cover the exact character bounding box.
A fixation slightly above or below the line would miss the word. The `enlarge_aois()`
function in `mapping.aoi` extends each AOI upward and downward by half the inter-line
spacing, so fixations between lines still map to the correct character.

import polars as pl


def test_space_fixation_counts_toward_word(run_pipeline, simple_aois):
    gaze_events = pl.DataFrame(
        {
            "name": ["fixation"],
            "stimulus": ["stim_1"],
            "trial": ["trial_1"],
            "page": ["page_1"],
            "onset": [100],
            "duration": [200],
            "unit_of_analysis_idx": [0],  # fixation on space belonging to Mali
            "char_idx": [4],  # space after the first word which has 4 chars
            "char": [" "],
            "unit_of_analysis": [" "],
        }
    )

    word_level_table = run_pipeline(simple_aois, gaze_events)

    # 3 words total (Mali, Dy, maybe trailing space word_idx=2)
    assert word_level_table.height == 2

    mali = word_level_table.filter(pl.col("unit_of_analysis_idx") == 0)
    dy = word_level_table.filter(pl.col("unit_of_analysis_idx") == 1)

    assert mali.select("skipped").item() == 0
    assert dy.select("skipped").item() == 1


def test_skipped_word(run_pipeline, simple_aois):
    gaze = pl.DataFrame(
        {
            "name": ["fixation"],
            "stimulus": ["stim_1"],
            "trial": ["trial_1"],
            "page": ["page_1"],
            "onset": [100],
            "duration": [200],
            "unit_of_analysis_idx": [0],
            "char_idx": [1],
            "char": ["a"],
            "unit_of_analysis": ["Mali"],
        }
    )

    wlt = run_pipeline(simple_aois, gaze)

    skipped = wlt.filter(pl.col("unit_of_analysis_idx") == 1)

    assert skipped.select("TFC").item() == 0
    assert skipped.select("TFT").item() == 0
    assert skipped.select("FPRT").item() == 0
    assert skipped.select("FPFC").item() == 0
    assert skipped.select("FPF").item() == 0
    assert skipped.select("SFD").item() == 0
    assert skipped.select("RRT").item() == 0
    assert skipped.select("RR").item() == 0


def test_two_first_pass_fixations(run_pipeline, simple_aois):
    gaze = pl.DataFrame(
        {
            "name": ["fixation", "fixation"],
            "stimulus": ["stim_1"] * 2,
            "trial": ["trial_1"] * 2,
            "page": ["page_1"] * 2,
            "onset": [100, 400],
            "duration": [200, 150],
            "unit_of_analysis_idx": [0, 0],
            "char_idx": [1, 2],
            "char": ["a", "l"],
            "unit_of_analysis": ["Mali", "Mali"],
        }
    )

    wlt = run_pipeline(simple_aois, gaze)

    mali = wlt.filter(pl.col("unit_of_analysis_idx") == 0)

    assert mali.select("TFC").item() == 2
    assert mali.select("TFT").item() == 350
    assert mali.select("FFD").item() == 200
    assert mali.select("FD").item() == 200
    assert mali.select("FPRT").item() == 350
    assert mali.select("FRT").item() == 350
    assert mali.select("FPFC").item() == 2
    assert mali.select("FPF").item() == 1
    assert mali.select("SFD").item() == 0
    assert mali.select("RRT").item() == 0
    assert mali.select("RR").item() == 0


def test_regression_multiple_rereading(run_pipeline, simple_aois):
    gaze = pl.DataFrame(
        {
            "name": ["fixation"] * 4,
            "stimulus": ["stim_1"] * 4,
            "trial": ["trial_1"] * 4,
            "page": ["page_1"] * 4,
            "onset": [100, 300, 600, 900],
            "duration": [115, 327, 261, 260],
            "unit_of_analysis_idx": [0, 1, 0, 0],
            "char_idx": [2, 6, 1, 2],
            "char": ["l", "a", "a", "l"],
            "unit_of_analysis": ["Mali", "Magjik", "Mali", "Mali"],
        }
    )

    wlt = run_pipeline(simple_aois, gaze)
    word = wlt.filter(pl.col("unit_of_analysis_idx") == 0)

    assert word.select("TFC").item() == 3

    # First-pass only first fixation
    assert word.select("FPRT").item() == 115

    # Total time includes rereading
    assert word.select("TFT").item() == 115 + 261 + 260

    # Rereading only the two later fixations
    assert word.select("RRT").item() == 261 + 260
    assert word.select("RR").item() == 1

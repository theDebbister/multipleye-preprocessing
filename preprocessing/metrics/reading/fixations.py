import polars as pl


def annotate_fixations(
    gaze_events: pl.DataFrame,
    group_columns: list[str] | None = None,
) -> pl.DataFrame:
    """
    Annotate fixations with run- and pass-level information.

    Definitions:
    - run_id: contiguous fixations on the same word
    - first-pass: a new run (visit) to a word that starts from the left and
      the word has not been exited before

      :param gaze_events: DataFrame containing pymovements' fixation events. Needs to be mapped to aois.
      :param group_columns: list of column names to group the fixations by. E.g., trial, stimulus, page.
      If None, defaults to ["trial", "stimulus", "page"].
    """
    if group_columns is None:
        from ...config import settings

        group_columns = [settings.TRIAL_COL, settings.STIMULUS_COL, settings.PAGE_COL]

    fix = (
        gaze_events.filter(
            (pl.col("name") == settings.FIXATION)
            & (pl.col(settings.WORD_IDX_COL).is_not_null())
        )
        .with_row_count("fixation_id")
        .sort(group_columns + ["onset"])
    )

    # -------------------------------------------------
    # Reading runs (contiguous fixations on the same word)
    # -------------------------------------------------
    fix = fix.with_columns(
        (
            pl.col(settings.WORD_IDX_COL)
            != pl.col(settings.WORD_IDX_COL).shift().over(group_columns)
        )
        .fill_null(True)
        .alias("new_run")
    )

    fix = fix.with_columns(
        pl.col("new_run").cast(pl.Int8).cum_sum().over(group_columns).alias("run_id")
    )

    # -----------------------------------------------------
    # Neighbouring fixated words (for regression detection)
    # -----------------------------------------------------
    fix = fix.with_columns(
        [
            pl.col(settings.WORD_IDX_COL)
            .shift()
            .over(group_columns)
            .alias("prev_word_idx"),
            pl.col(settings.WORD_IDX_COL)
            .shift(-1)
            .over(group_columns)
            .alias("next_word_idx"),
        ]
    )

    fix = fix.with_columns(
        [
            (pl.col(settings.WORD_IDX_COL) - pl.col("prev_word_idx")).alias("delta_in"),
            (pl.col("next_word_idx") - pl.col(settings.WORD_IDX_COL)).alias(
                "delta_out"
            ),
        ]
    )

    fix = fix.with_columns(
        [
            (pl.col("delta_in") < 0).alias("is_reg_in"),
            (pl.col("delta_out") < 0).alias("is_reg_out"),
        ]
    )

    # -------------------------------------------------
    # First fix on word
    # -------------------------------------------------
    fix = fix.with_columns(
        pl.col(settings.WORD_IDX_COL)
        .cum_count()
        .over(group_columns + [settings.WORD_IDX_COL])
        .eq(1)
        .alias("is_first_fix")
    )

    # -------------------------------------------------
    # First-pass flag (word-level first reading episode)
    # -------------------------------------------------

    def mark_first_pass(df: pl.DataFrame) -> pl.DataFrame:
        """
        Mark fixations that belong to the first-pass reading of a word.

        First-pass is defined at the *run* level.
        A run is first-pass if:
            1. It is the first time the reader enters the word
            (not necessarily the first fixation, but the first run)
            2. The word is entered from the left (forward reading direction)
            3. No words with a higher index have been fixated before
            (i.e. the word has not been exited or skipped)

        All fixations within such a run are labeled `is_first_pass = True`.
        Any later revisit to the word, or entries from the right (regressions),
        are not part of first-pass.

        :param df: DataFrame containing pymovements fixation events. Needs to be mapped to aois, and annotated with
        run_id and prev_word_idx. See annotate_fixations() for details.
        """
        df = df.sort("onset")

        first_pass_flags: list[bool] = []

        prev_run = None
        rightmost_word_seen = None
        current_run_is_first_pass = False

        # set of words that have been entered at the start of any prior run
        words_ever_entered: set[int] = set()

        for row in df.iter_rows(named=True):
            from ...config import settings

            w = row[settings.WORD_IDX_COL]
            run = row["run_id"]
            prev_w = row["prev_word_idx"]

            new_run = run != prev_run

            if new_run:
                entered_from_left = (prev_w is None) or (w > prev_w)

                no_higher_word_seen = (rightmost_word_seen is None) or (
                    w >= rightmost_word_seen
                )

                first_time_entering_word = w not in words_ever_entered

                current_run_is_first_pass = (
                    entered_from_left
                    and no_higher_word_seen
                    and first_time_entering_word
                )

                words_ever_entered.add(w)

            first_pass_flags.append(current_run_is_first_pass)

            if rightmost_word_seen is None or w > rightmost_word_seen:
                rightmost_word_seen = w

            prev_run = run

        return df.with_columns(pl.Series("is_first_pass", first_pass_flags))

    fix = fix.group_by(*group_columns, maintain_order=True).map_groups(mark_first_pass)

    return fix.select(
        [
            settings.TRIAL_COL,
            settings.PAGE_COL,
            "fixation_id",
            "onset",
            settings.WORD_IDX_COL,
            settings.CHAR_IDX_COL,
            "char",
            "run_id",
            "is_first_pass",
            "duration",
            "unit_of_analysis",
            "prev_word_idx",
            "next_word_idx",
            "is_reg_in",
            "is_reg_out",
            "is_first_fix",
        ]
    )

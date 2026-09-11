import polars as pl

from ...config import settings


def all_tokens_from_aois(
    aois: pl.DataFrame,
    trial: str | None = None,
) -> pl.DataFrame:
    """
    Returns every AOI token on the page:
    words, spaces, punctuation — everything that has a word_idx.
    """
    aois = (
        aois.with_columns([pl.lit(trial).cast(pl.Utf8).alias(settings.TRIAL_COL)])
        if settings.TRIAL_COL not in aois.columns
        else aois
    )

    return (
        aois.select(
            [
                settings.TRIAL_COL,
                settings.PAGE_COL,
                settings.WORD_IDX_COL,
                "unit_of_analysis",
            ]
        )
        .unique()
        .sort(settings.WORD_IDX_COL)
    )


def mark_skipped_tokens(
    all_tokens: pl.DataFrame, fixations: pl.DataFrame
) -> pl.DataFrame:
    fixated_tokens = (
        fixations.select([settings.TRIAL_COL, settings.PAGE_COL, settings.WORD_IDX_COL])
        .drop_nulls()
        .unique()
        .with_columns(pl.lit(1).alias("fixated"))
    )

    out = all_tokens.join(
        fixated_tokens,
        on=[settings.TRIAL_COL, settings.PAGE_COL, settings.WORD_IDX_COL],
        how="left",
    )

    return out.with_columns(
        pl.when(pl.col("fixated").is_null())
        .then(1)  # not fixated → skipped
        .otherwise(0)  # fixated → not skipped
        .cast(pl.Int8)
        .alias("skipped")
    ).drop("fixated")

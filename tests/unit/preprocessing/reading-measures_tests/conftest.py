import polars as pl
import pytest

from preprocessing.metrics.reading.fixations import annotate_fixations
from preprocessing.metrics.reading.reading_measures import build_word_level_table
from preprocessing.metrics.reading.words import (
    all_tokens_from_aois,
    mark_skipped_tokens,
)


@pytest.fixture
def run_pipeline():
    def _run(aois, gaze_events):
        word_lookup = all_tokens_from_aois(aois, trial="trial_1")
        fixation_table = annotate_fixations(gaze_events)
        words_with_skip = mark_skipped_tokens(word_lookup, fixation_table)

        return build_word_level_table(
            words=words_with_skip,
            fix=fixation_table,
        )

    return _run


@pytest.fixture
def simple_aois():
    """Create a sample aois table"""
    return pl.DataFrame(
        {
            "page": ["page_1"] * 8,
            "unit_of_analysis_idx": [0, 0, 0, 0, 0, 1, 1, 1],
            "char": ["M", "a", "l", "i", " ", "D", "y", " "],
            "char_idx": [0, 1, 2, 3, 4, 5, 6, 7],
            "char_idx_in_line": list(range(8)),
            "unit_of_analysis": ["Mali", "Mali", "Mali", "Mali", " ", "Dy", "Dy", " "],
        }
    )

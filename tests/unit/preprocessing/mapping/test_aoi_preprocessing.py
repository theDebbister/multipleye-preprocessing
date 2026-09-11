import pandas as pd

from preprocessing.mapping import aoi_preprocessing


def test_add_custom_aois_adds_expected_columns(tmp_path, monkeypatch):
    aoi_file = tmp_path / "dummy.csv"
    custom_dir = tmp_path / "custom_units_of_analysis"
    custom_dir.mkdir()

    aoi_df = pd.DataFrame(
        [
            {
                "char_idx": 1,
                "char": "a",
                "top_left_x": 0,
                "top_left_y": 0,
                "width": 10,
                "height": 10,
                "char_idx_in_line": 1,
                "line_idx": 1,
                "page": 1,
                "unit_of_analysis": "w1",
                "unit_of_analysis_idx": 1,
                "unit_of_analysis_idx_in_line": 1,
            },
            {
                "char_idx": 2,
                "char": "b",
                "top_left_x": 10,
                "top_left_y": 0,
                "width": 10,
                "height": 10,
                "char_idx_in_line": 2,
                "line_idx": 1,
                "page": 1,
                "unit_of_analysis": "w1",
                "unit_of_analysis_idx": 1,
                "unit_of_analysis_idx_in_line": 1,
            },
            {
                "char_idx": 3,
                "char": "c",
                "top_left_x": 20,
                "top_left_y": 0,
                "width": 10,
                "height": 10,
                "char_idx_in_line": 1,
                "line_idx": 2,
                "page": 1,
                "unit_of_analysis": "w2",
                "unit_of_analysis_idx": 2,
                "unit_of_analysis_idx_in_line": 1,
            },
        ]
    )
    aoi_df.to_csv(aoi_file, index=False)

    custom_df = pd.DataFrame(
        [
            {"segment": "s1", "segment_idx": 1, "char": "a", "char_idx": 1, "page": 1},
            {"segment": "s1", "segment_idx": 1, "char": "b", "char_idx": 2, "page": 1},
            {"segment": "s2", "segment_idx": 2, "char": "c", "char_idx": 3, "page": 1},
        ]
    )
    custom_df.to_csv(custom_dir / "dummy.csv", index=False)

    monkeypatch.setattr(aoi_preprocessing.settings, "DATASET_DIR", tmp_path)

    aoi_preprocessing.add_custom_aois(aoi_file, "ZH")

    result = pd.read_csv(aoi_file)

    assert list(result.columns) == [
        "char_idx",
        "char",
        "top_left_x",
        "top_left_y",
        "width",
        "height",
        "char_idx_in_line",
        "line_idx",
        "page",
        "unit_of_analysis",
        "unit_of_analysis_idx",
        "unit_of_analysis_idx_in_line",
        "secondary_unit_of_analysis_idx",
        "secondary_unit_of_analysis_idx_in_line",
        "secondary_unit_of_analysis",
    ]
    assert result["unit_of_analysis"].tolist() == ["s1", "s1", "s2"]
    assert result["unit_of_analysis_idx"].tolist() == [1, 1, 2]
    assert result["secondary_unit_of_analysis"].tolist() == ["w1", "w1", "w2"]

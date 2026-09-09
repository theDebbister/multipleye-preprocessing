import logging

import pytest
import yaml

from preprocessing.scripts.restructure_psycho_tests import fix_psycho_tests_structure


@pytest.fixture
def psycho_structure(tmp_path):
    """Creates a temporary structure for psychometric tests."""
    config_folder = tmp_path / "core_data" / "participant_configs_ZH_CH_1"
    data_folder = tmp_path / "core_data"
    out_folder = tmp_path / "output"

    config_folder.mkdir(parents=True)
    out_folder.mkdir()

    return config_folder, data_folder, out_folder


@pytest.mark.parametrize(
    "yaml_flag, folder_name",
    [
        ("plab", "PLAB"),
        ("ran", "RAN"),
        ("stroop_flanker", "Stroop_Flanker"),
        ("wmc", "WMC"),
        ("wiki_vocab", "WikiVocab"),
    ],
)
def test_restructure_individual_tests(psycho_structure, yaml_flag, folder_name):
    config_folder, data_folder, out_folder = psycho_structure
    sid = "001_ZH_CH_1_PT1"

    # Create config with only one test enabled
    config_data = {
        flag: False for flag in ["plab", "ran", "stroop_flanker", "wmc", "wiki_vocab"]
    }
    config_data[yaml_flag] = True
    with open(config_folder / f"{sid}.yaml", "w") as f:
        yaml.dump(config_data, f)

    # Create data for that test
    (data_folder / folder_name / sid).mkdir(parents=True)
    (data_folder / folder_name / sid / "data.csv").touch()

    fix_psycho_tests_structure(config_folder, data_folder, out_folder)

    assert (out_folder / sid / folder_name / "data.csv").exists()
    assert (out_folder / sid / f"{sid}.yaml").exists()


def test_restructure_multiple_tests(psycho_structure):
    config_folder, data_folder, out_folder = psycho_structure
    sid = "001_ZH_CH_1_PT1"

    # Create config with multiple tests
    config_data = {
        "plab": True,
        "ran": False,
        "stroop_flanker": True,
        "wmc": False,
        "wiki_vocab": False,
    }
    with open(config_folder / f"{sid}.yaml", "w") as f:
        yaml.dump(config_data, f)

    # Create data
    (data_folder / "PLAB" / sid).mkdir(parents=True)
    (data_folder / "PLAB" / sid / "data.csv").touch()
    (data_folder / "Stroop_Flanker" / sid).mkdir(parents=True)
    (data_folder / "Stroop_Flanker" / sid / "data.csv").touch()

    fix_psycho_tests_structure(config_folder, data_folder, out_folder)

    assert (out_folder / sid / "PLAB" / "data.csv").exists()
    assert (out_folder / sid / "Stroop_Flanker" / "data.csv").exists()
    assert (out_folder / sid / f"{sid}.yaml").exists()


def test_restructure_missing_data_warning(psycho_structure, caplog):
    config_folder, data_folder, out_folder = psycho_structure
    sid = "002_ZH_CH_1_PT1"

    # Marked as True in config but data is missing
    config_data = {"plab": True}
    with open(config_folder / f"{sid}.yaml", "w") as f:
        yaml.dump(config_data, f)

    with caplog.at_level(logging.WARNING):
        fix_psycho_tests_structure(config_folder, data_folder, out_folder)

    assert "!!! MISSING DATA !!!" in caplog.text
    assert (
        f"Participant {sid} is marked for PLAB in participant configuration ({sid}.yaml)"
        in caplog.text
    )
    assert "but the data folder does not exist at" in caplog.text


def test_restructure_false_but_data_exists_warning(psycho_structure, caplog):
    config_folder, data_folder, out_folder = psycho_structure
    sid = "003_ZH_CH_1_PT1"

    # Marked as False in config but data exists
    config_data = {"plab": False}
    with open(config_folder / f"{sid}.yaml", "w") as f:
        yaml.dump(config_data, f)

    (data_folder / "PLAB" / sid).mkdir(parents=True)
    (data_folder / "PLAB" / sid / "data.csv").touch()

    with caplog.at_level(logging.WARNING):
        fix_psycho_tests_structure(config_folder, data_folder, out_folder)

    assert (
        f"Participant {sid} has data for PLAB, but it is marked as False (or missing) in participant config ({sid}.yaml)"
        in caplog.text
    )
    assert (out_folder / sid / "PLAB" / "data.csv").exists()


def test_restructure_non_sid_compliant_warning(psycho_structure, caplog):
    config_folder, data_folder, out_folder = psycho_structure
    invalid_sid = "99_INVALID"

    config_data = {"plab": True}
    with open(config_folder / f"{invalid_sid}.yaml", "w") as f:
        yaml.dump(config_data, f)

    (data_folder / "PLAB" / invalid_sid).mkdir(parents=True)

    with caplog.at_level(logging.WARNING):
        fix_psycho_tests_structure(config_folder, data_folder, out_folder)

    assert (
        f"Configuration file name is not SID-compliant: {invalid_sid}.yaml"
        in caplog.text
    )
    # Should still process
    assert (out_folder / invalid_sid / "PLAB").exists()


def test_restructure_normalization_s1_to_pt1(psycho_structure):
    config_folder, data_folder, out_folder = psycho_structure
    sid_s1 = "004_ZH_CH_1_S1"

    config_data = {"plab": True}
    with open(config_folder / f"{sid_s1}.yaml", "w") as f:
        yaml.dump(config_data, f)

    (data_folder / "PLAB" / sid_s1).mkdir(parents=True)

    fix_psycho_tests_structure(config_folder, data_folder, out_folder)

    expected_folder = "004_ZH_CH_1_PT1"
    assert (out_folder / expected_folder).exists()
    assert (out_folder / expected_folder / "PLAB").exists()
    assert (out_folder / expected_folder / f"{sid_s1}.yaml").exists()


def test_restructure_soft_matching_pt1_data_for_s1_config(psycho_structure):
    """Test that it finds _PT1 data even if config is _S1."""
    config_folder, data_folder, out_folder = psycho_structure
    sid_config = "005_ZH_CH_1_S1"
    sid_data = "005_ZH_CH_1_PT1"

    config_data = {"plab": True}
    with open(config_folder / f"{sid_config}.yaml", "w") as f:
        yaml.dump(config_data, f)

    (data_folder / "PLAB" / sid_data).mkdir(parents=True)
    (data_folder / "PLAB" / sid_data / "data.csv").touch()

    fix_psycho_tests_structure(config_folder, data_folder, out_folder)

    expected_folder = "005_ZH_CH_1_PT1"
    assert (out_folder / expected_folder).exists()
    assert (out_folder / expected_folder / "PLAB" / "data.csv").exists()
    assert (out_folder / expected_folder / f"{sid_config}.yaml").exists()


def test_restructure_moves_and_cleans_up_source(psycho_structure):
    config_folder, data_folder, out_folder = psycho_structure
    sid = "007_ZH_CH_1_PT1"

    config_data = {"plab": True, "ran": True}
    with open(config_folder / f"{sid}.yaml", "w") as f:
        yaml.dump(config_data, f)

    (data_folder / "PLAB" / sid).mkdir(parents=True)
    (data_folder / "PLAB" / sid / "data.csv").touch()
    (data_folder / "RAN" / sid).mkdir(parents=True)
    (data_folder / "RAN" / sid / "data.csv").touch()

    fix_psycho_tests_structure(config_folder, data_folder, out_folder)

    # Data is moved (not copied): present in the session folder, gone from the source.
    assert (out_folder / sid / "PLAB" / "data.csv").exists()
    assert (out_folder / sid / "RAN" / "data.csv").exists()
    assert (out_folder / sid / f"{sid}.yaml").exists()
    assert not (data_folder / "PLAB").exists()
    assert not (data_folder / "RAN").exists()
    assert not config_folder.exists()


def test_restructure_keeps_unmapped_data_with_warning(psycho_structure, caplog):
    config_folder, data_folder, out_folder = psycho_structure
    sid = "008_ZH_CH_1_PT1"

    config_data = {"plab": True}
    with open(config_folder / f"{sid}.yaml", "w") as f:
        yaml.dump(config_data, f)

    (data_folder / "PLAB" / sid).mkdir(parents=True)
    (data_folder / "PLAB" / sid / "data.csv").touch()
    # Data in a non-mapped test root (WCST) must be preserved, not moved.
    (data_folder / "WCST" / "999_ZH_CH_1_PT1").mkdir(parents=True)
    (data_folder / "WCST" / "999_ZH_CH_1_PT1" / "x.csv").touch()

    with caplog.at_level(logging.WARNING):
        fix_psycho_tests_structure(config_folder, data_folder, out_folder)

    assert (out_folder / sid / "PLAB" / "data.csv").exists()
    assert not (data_folder / "PLAB").exists()
    assert (data_folder / "WCST").exists()
    assert "Unmoved data" in caplog.text
    assert not config_folder.exists()


def test_restructure_no_configs_raises_value_error(tmp_path):
    config_folder = tmp_path / "empty_configs"
    config_folder.mkdir()
    data_folder = tmp_path / "data"
    data_folder.mkdir()
    out_folder = tmp_path / "out"

    with pytest.raises(ValueError, match="No configuration files"):
        fix_psycho_tests_structure(config_folder, data_folder, out_folder)


def test_restructure_adopts_data_without_config(psycho_structure, caplog):
    config_folder, data_folder, out_folder = psycho_structure
    sid = "037_ZH_CH_1_PT1"

    # No config file for this session; data is split across multiple test roots.
    for test_name in ["PLAB", "RAN", "Stroop_Flanker", "WikiVocab"]:
        (data_folder / test_name / sid).mkdir(parents=True)
        (data_folder / test_name / sid / "data.csv").touch()

    with caplog.at_level(logging.WARNING):
        fix_psycho_tests_structure(config_folder, data_folder, out_folder)

    # Data is moved into a single session-first folder.
    for test_name in ["PLAB", "RAN", "Stroop_Flanker", "WikiVocab"]:
        assert (out_folder / sid / test_name / "data.csv").exists()
        assert not (data_folder / test_name).exists()
    # No config YAML is generated.
    assert not (out_folder / sid / f"{sid}.yaml").exists()
    # A warning lists the missing config session.
    assert "No participant config" in caplog.text
    assert sid in caplog.text
    # Source is fully empty and removed.
    assert not data_folder.exists()


def test_restructure_adopts_multiple_orphans_in_one_warning(psycho_structure, caplog):
    config_folder, data_folder, out_folder = psycho_structure

    for sid in ["037_ZH_CH_1_PT1", "049_ZH_CH_1_PT1", "092_ZH_CH_1_PT1"]:
        (data_folder / "RAN" / sid).mkdir(parents=True)
        (data_folder / "RAN" / sid / "data.csv").touch()

    with caplog.at_level(logging.WARNING):
        fix_psycho_tests_structure(config_folder, data_folder, out_folder)

    # All orphans adopted with a single aggregate warning listing each.
    for sid in ["037_ZH_CH_1_PT1", "049_ZH_CH_1_PT1", "092_ZH_CH_1_PT1"]:
        assert (out_folder / sid / "RAN" / "data.csv").exists()
    assert "No participant config for 3 session(s)" in caplog.text
    assert "037_ZH_CH_1_PT1" in caplog.text
    assert "049_ZH_CH_1_PT1" in caplog.text
    assert "092_ZH_CH_1_PT1" in caplog.text


def test_restructure_adopts_orphan_normalizes_s_to_pt(psycho_structure, caplog):
    config_folder, data_folder, out_folder = psycho_structure

    # Data folder uses an S-suffix; output should be normalized to PT.
    (data_folder / "PLAB" / "037_ZH_CH_1_S1").mkdir(parents=True)
    (data_folder / "PLAB" / "037_ZH_CH_1_S1" / "data.csv").touch()

    with caplog.at_level(logging.WARNING):
        fix_psycho_tests_structure(config_folder, data_folder, out_folder)

    assert (out_folder / "037_ZH_CH_1_PT1" / "PLAB" / "data.csv").exists()
    assert not (data_folder / "PLAB").exists()
    assert not data_folder.exists()

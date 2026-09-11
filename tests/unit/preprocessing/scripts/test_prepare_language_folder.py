import pandas as pd
import pytest

from preprocessing import settings
from preprocessing.data_collection.multipleye_data_collection import (
    MultipleyeDataCollection,
)
from preprocessing.models.dcn import Dcn
from preprocessing.scripts.prepare_language_folder import (
    _compute_stimulus_checksum,
    prepare_language_folder,
)


@pytest.fixture
def mock_data_collection_factory(tmp_path, monkeypatch):
    def _create_mock(data_collection_name):
        dcn = Dcn(data_collection_name)
        lang, country, lab_no = dcn.lang, dcn.country, dcn.lab

        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        collection_dir = data_dir / data_collection_name
        collection_dir.mkdir(parents=True, exist_ok=True)

        # Create required folders
        (collection_dir / "eye-tracking-sessions").mkdir(exist_ok=True)
        (collection_dir / "psychometric-tests-sessions").mkdir(exist_ok=True)

        stimuli_dir = collection_dir / f"stimuli_{data_collection_name}"
        stimuli_dir.mkdir(exist_ok=True)
        (stimuli_dir / "config").mkdir(exist_ok=True)

        aoi_dir = stimuli_dir / f"aoi_stimuli_{lang.lower()}_{country.lower()}_{lab_no}"
        aoi_dir.mkdir(exist_ok=True)

        # Create 12 dummy AOI files to satisfy current validation
        for i in range(1, 13):
            aoi_file = aoi_dir / f"test_{i}_aoi.csv"
            df = pd.DataFrame(
                {
                    "page": ["page_1", "page_1", "question_1"],
                    "word": ["word1", " ", "qword1"],
                    "char": ["w", " ", "q"],
                    "char_idx": [0, 1, 2],
                    "word_idx": [0, 0, 0],
                    "word_idx_in_line": [0, 0, 0],
                    "line_idx": [0, 0, 0],
                    "char_idx_in_line": [0, 1, 0],
                    "top_left_x": [0, 10, 0],
                    "top_left_y": [0, 0, 100],
                    "width": [10, 5, 10],
                    "height": [20, 20, 20],
                }
            )
            df.to_csv(aoi_file, index=False)

        # Mock settings
        monkeypatch.setattr(settings, "_repo_root", tmp_path)
        settings.DATA_COLLECTION_NAME = data_collection_name
        settings.DATASET_DIR = collection_dir
        settings.OUTPUT_DIR = tmp_path / "preprocessed_data" / data_collection_name

        return tmp_path, data_collection_name, aoi_dir

    return _create_mock


def setup_stimulus_assets(tmp_path, data_collection_name, aoi_dir):
    dcn = Dcn(data_collection_name)
    lang, country, city, lab_no = dcn.lang, dcn.country, dcn.city, dcn.lab
    suffix = f"{lang.lower()}_{country.lower()}_{lab_no}"
    stimuli_dir = aoi_dir.parent

    img_dir = stimuli_dir / f"stimuli_images_{suffix}"
    img_dir.mkdir(exist_ok=True)
    (img_dir / "test_img.png").touch()

    q_dir = stimuli_dir / f"question_images_{suffix}"
    q_dir.mkdir(exist_ok=True)
    v1_dir = q_dir / "question_images_version_1"
    v1_dir.mkdir(exist_ok=True)
    (v1_dir / "q1.png").touch()
    v2_dir = q_dir / "question_images_version_2"
    v2_dir.mkdir(exist_ok=True)
    (v2_dir / "q2.png").touch()

    xlsx_file = stimuli_dir / f"multipleye_stimuli_experiment_{lang}.xlsx"
    xlsx_file.touch()

    # Create a dummy config file
    config_dir = stimuli_dir / "config"
    config_dir.mkdir(exist_ok=True)
    config_file = (
        config_dir
        / f"config_{lang.lower()}_{country.lower()}_{city.lower()}_{lab_no}_dummy.py"
    )
    with open(config_file, "w") as f:
        f.write("RESOLUTION = (1920, 1080)\n")
        f.write("SCREEN_SIZE_CM = (50, 30)\n")
        f.write("DISTANCE_CM = 60\n")
        f.write("IMAGE_WIDTH_PX = 1000\n")
        f.write("IMAGE_HEIGHT_PX = 800\n")
        f.write("IMAGE_SIZE_CM = (20, 15)\n")

    json_config = (
        config_dir
        / f"MultiplEYE_{lang}_{country}_{city}_{lab_no}_{dcn.year}_lab_configuration.json"
    )
    with open(json_config, "w") as f:
        f.write(
            '{"Name_eye-tracker": "EyeLink 1000 Plus", "Psychometric_tests": {"Are_tests_conducted": true}}'
        )

    # Create a session with an ASC file indicating version 1
    session_name = f"001_{lang}_{country}_{lab_no}_ET1"
    eye_tracking_dir = (
        tmp_path / "data" / data_collection_name / "eye-tracking-sessions"
    )
    session_dir = eye_tracking_dir / session_name
    session_dir.mkdir(exist_ok=True)
    asc_file = session_dir / f"{session_name}.asc"
    with open(asc_file, "w") as f:
        f.write("MSG 123456 stimulus_order_version: 1\n")
    # Add dummy EDF file
    (session_dir / f"{session_name}.edf").touch()

    # Create stimulus order versions CSV
    stim_order_file = (
        config_dir / f"stimulus_order_versions_{lang}_{country}_{lab_no}.csv"
    )
    with open(stim_order_file, "w") as f:
        f.write("participant_id,version_number\n")
        f.write("001,1\n")

    return suffix, lang


@pytest.mark.parametrize(
    "data_collection_name",
    ["MultiplEYE_DA_DK_Aalborg_1_2026", "MultiplEYE_EN_UK_London_2_2025"],
)
def test_prepare_language_folder_copies_and_modifies_in_preprocessed(
    mock_data_collection_factory, data_collection_name
):
    tmp_path, data_collection_name, aoi_dir = mock_data_collection_factory(
        data_collection_name
    )
    suffix, lang = setup_stimulus_assets(tmp_path, data_collection_name, aoi_dir)
    dcn = Dcn(data_collection_name)

    # Run preparation
    prepare_language_folder(data_collection_name)

    # Verify that the file in data/ was NOT modified (should still be 12 files)
    files_data = list(aoi_dir.glob("*.csv"))
    assert len(files_data) == 12

    # Verify preprocessed_data exists and contains 24 files + marker
    preprocessed_stim_dir = (
        tmp_path
        / "preprocessed_data"
        / data_collection_name
        / f"stimuli_{data_collection_name}"
    )
    preprocessed_aoi_dir = (
        preprocessed_stim_dir
        / f"aoi_stimuli_{dcn.lang.lower()}_{dcn.country.lower()}_{dcn.lab}"
    )
    assert preprocessed_aoi_dir.exists()

    files_preprocessed = list(preprocessed_aoi_dir.glob("*.csv"))
    assert len(files_preprocessed) == 24
    assert (preprocessed_aoi_dir / ".fixed").exists()

    # Verify other assets were copied
    assert (
        preprocessed_stim_dir / f"stimuli_images_{suffix}" / "test_img.png"
    ).exists()
    assert (
        preprocessed_stim_dir / f"multipleye_stimuli_experiment_{lang}.xlsx"
    ).exists()
    assert (preprocessed_stim_dir / "config").exists()

    # Verify ONLY used question version was copied
    assert (
        preprocessed_stim_dir
        / f"question_images_{suffix}"
        / "question_images_version_1"
    ).exists()
    assert not (
        preprocessed_stim_dir
        / f"question_images_{suffix}"
        / "question_images_version_2"
    ).exists()


@pytest.mark.parametrize("data_collection_name", ["MultiplEYE_DA_DK_Aalborg_1_2026"])
def test_multipleye_data_collection_uses_preprocessed_stimuli(
    mock_data_collection_factory, data_collection_name
):
    tmp_path, data_collection_name, aoi_dir = mock_data_collection_factory(
        data_collection_name
    )
    setup_stimulus_assets(tmp_path, data_collection_name, aoi_dir)

    # Run preparation first to create preprocessed stimuli
    prepare_language_folder(data_collection_name)

    # Create the data collection
    mdc = MultipleyeDataCollection.create_from_data_folder(settings.DATASET_DIR)

    # Verify that stimulus_dir points to preprocessed_data
    expected_stim_dir = (
        tmp_path
        / "preprocessed_data"
        / data_collection_name
        / f"stimuli_{data_collection_name}"
    )
    assert mdc.stimulus_dir == expected_stim_dir


@pytest.mark.parametrize("data_collection_name", ["MultiplEYE_DA_DK_Aalborg_1_2026"])
def test_prepare_language_folder_optional_aoi_images(
    mock_data_collection_factory, data_collection_name
):
    tmp_path, data_collection_name, aoi_dir = mock_data_collection_factory(
        data_collection_name
    )
    suffix, _lang = setup_stimulus_assets(tmp_path, data_collection_name, aoi_dir)

    # Create AOI stimuli images folder
    stimuli_dir = aoi_dir.parent
    aoi_img_dir = stimuli_dir / f"aoi_stimuli_images_{suffix}"
    aoi_img_dir.mkdir()
    (aoi_img_dir / "overlay.png").touch()

    # Set config to True
    settings.COPY_AOI_IMAGES_OVERLAY = True

    # Run preparation
    prepare_language_folder(data_collection_name)

    # Verify it was copied
    preprocessed_stim_dir = (
        tmp_path
        / "preprocessed_data"
        / data_collection_name
        / f"stimuli_{data_collection_name}"
    )
    assert (
        preprocessed_stim_dir / f"aoi_stimuli_images_{suffix}" / "overlay.png"
    ).exists()


@pytest.mark.parametrize("data_collection_name", ["MultiplEYE_DA_DK_Aalborg_1_2026"])
def test_prepare_language_folder_no_pt_data(
    mock_data_collection_factory, data_collection_name
):
    """Pipeline should warn, not raise, when psychometric-tests-sessions is missing."""
    tmp_path, data_collection_name, aoi_dir = mock_data_collection_factory(
        data_collection_name
    )
    setup_stimulus_assets(tmp_path, data_collection_name, aoi_dir)

    # Remove the psychometric-tests-sessions folder
    import shutil

    shutil.rmtree(
        tmp_path / "data" / data_collection_name / "psychometric-tests-sessions"
    )

    # Should not raise
    prepare_language_folder(data_collection_name)


def test_checksum_deterministic(tmp_path):
    source = tmp_path / "stimuli"
    source.mkdir()
    (source / "config").mkdir()
    (source / "config" / "a.py").write_text("x=1")
    (source / "data.csv").write_text("col\n1\n")

    assert _compute_stimulus_checksum(source) == _compute_stimulus_checksum(source)


def test_checksum_different_content_changes_hash(tmp_path):
    source = tmp_path / "stimuli"
    source.mkdir()
    f = source / "data.csv"
    f.write_text("col\n1\n")

    h1 = _compute_stimulus_checksum(source)
    f.write_text("col\n1\n2\n")
    h2 = _compute_stimulus_checksum(source)

    assert h1 != h2


def test_checksum_added_file_changes_hash(tmp_path):
    source = tmp_path / "stimuli"
    source.mkdir()
    (source / "a.csv").write_text("x")

    h1 = _compute_stimulus_checksum(source)
    (source / "b.csv").write_text("y")
    h2 = _compute_stimulus_checksum(source)

    assert h1 != h2


def test_checksum_removed_file_changes_hash(tmp_path):
    source = tmp_path / "stimuli"
    source.mkdir()
    (source / "a.csv").write_text("x")
    (source / "b.csv").write_text("y")

    h1 = _compute_stimulus_checksum(source)
    (source / "b.csv").unlink()
    h2 = _compute_stimulus_checksum(source)

    assert h1 != h2


@pytest.mark.parametrize(
    "subdirs",
    [
        [],
        ["subdir"],
    ],
)
def test_checksum_no_files_returns_64_char_hex(tmp_path, subdirs):
    source = tmp_path / "stimuli"
    source.mkdir()
    for sub in subdirs:
        (source / sub).mkdir()

    h = _compute_stimulus_checksum(source)

    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_checksum_mtime_independent(tmp_path):
    source = tmp_path / "stimuli"
    source.mkdir()
    f = source / "f.txt"
    f.write_text("hello")

    h1 = _compute_stimulus_checksum(source)
    f.touch()
    h2 = _compute_stimulus_checksum(source)

    assert h1 == h2


@pytest.fixture
def first_run(mock_data_collection_factory):
    def _run(data_collection_name):
        tmp_path, data_collection_name, aoi_dir = mock_data_collection_factory(
            data_collection_name
        )
        setup_stimulus_assets(tmp_path, data_collection_name, aoi_dir)
        prepare_language_folder(data_collection_name)
        preprocessed_stim_dir = (
            tmp_path
            / "preprocessed_data"
            / data_collection_name
            / f"stimuli_{data_collection_name}"
        )
        checksum_path = preprocessed_stim_dir / ".copy_checksum"
        return tmp_path, data_collection_name, preprocessed_stim_dir, checksum_path

    return _run


@pytest.mark.parametrize("data_collection_name", ["MultiplEYE_DA_DK_Aalborg_1_2026"])
def test_second_run_skips_copy_when_unchanged(first_run, data_collection_name):
    _, _, _, checksum_path = first_run(data_collection_name)
    first_hash = checksum_path.read_text().strip()

    prepare_language_folder(data_collection_name)

    assert checksum_path.read_text().strip() == first_hash


@pytest.mark.parametrize("data_collection_name", ["MultiplEYE_DA_DK_Aalborg_1_2026"])
def test_stimulus_change_triggers_recopy(first_run, data_collection_name):
    tmp_path, _, stim_dir, checksum_path = first_run(data_collection_name)
    first_hash = checksum_path.read_text().strip()

    stimuli_dir = (
        tmp_path / "data" / data_collection_name / f"stimuli_{data_collection_name}"
    )
    (stimuli_dir / "config" / "new_version.csv").write_text("version,2")
    prepare_language_folder(data_collection_name)

    assert checksum_path.read_text().strip() != first_hash
    assert (stim_dir / "config" / "new_version.csv").exists()

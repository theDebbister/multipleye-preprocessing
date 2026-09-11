(configuration_guide)=

# Configuration

The MultiplEYE pEYEpline uses a central configuration system to manage all parameters,
ensuring reproducible and consistent data processing.

## Loading Precedence

The pEYEpline searches for configuration in the following order:

1. **CLI Argument**: `--config_path your_config.yaml` when running the preprocessing script.
2. **Environment Variable**: `MULTIPLEYE_CONFIG` pointing to a YAML file.
3. **Local Default**: `multipleye_settings_preprocessing.yaml` in your current working directory.

**If no configuration is found**, the pEYEpline will:

1. Copy a template to `multipleye_settings_preprocessing.yaml` in your current directory.
2. Display a message with instructions.
3. **Stop execution**.

You must then edit the file (at least set `data_collection_name`) and rerun the command.

## Initial Setup

When you run the pEYEpline for the first time in a new directory, it will create a template for you.

```bash
uv run run_preprocessing
```

After it stops, open `multipleye_settings_preprocessing.yaml` and configure your session.

## Configuration Settings

Settings are divided into user-configurable parameters and internal constants.

### User Settings (Required & Common)

- `DATA_COLLECTION_NAME`: **(Required)** A unique identifier for your collection.
    - Format: `MultiplEYE_[LANG]_[COUNTRY]_[CITY]_[LAB_NO]_[YEAR]`
    - Example: `MultiplEYE_EN_UK_London_1_2026`
    - **Note**: This name has been given to you by the MultiplEYE project.
      It is used to determine data and output paths. If it doesn't match the
      required 6-part format, the pEYEpline might fail to resolve certain paths.
- `OVERWRITE`: `true` to reprocess existing data, `false` (default) to skip already processed
  sessions.
- `EXPERIMENT_TYPE`: `MultiplEYE` (default) or `MeRID`.
- `INCLUDE_SESSIONS` / `EXCLUDE_SESSIONS`: Optional lists to filter which sessions are processed.
- `INCLUDE_PILOTS`: `true` to include data from pilot folders (default: `false`).
- `EXPECTED_SAMPLING_RATE_HZ`: The sampling rate of your eye tracker (default: `1000`).

#### Less commonly changed user settings

- `DATASET_DIR`: The path where your raw data is located. By default, this is
  `data/[DATA_COLLECTION_NAME]`.
- `OUTPUT_DIR`: The path where preprocessed data will be saved. By default, this is
  `preprocessed_data/[DATA_COLLECTION_NAME]`.

### Quality Check Thresholds

These settings define the criteria for "GOOD" data quality. **Do not change these** unless you are a
core developer, as they ensure consistency across the MultiplEYE project.

- `ACCEPTABLE_NUM_CALIBRATIONS`: [min, max] range for calibrations.
- `ACCEPTABLE_NUM_VALIDATION`: [min, max] range for validations.
- `ACCEPTABLE_AVG_VALIDATION_SCORES`: Acceptable average accuracy.
- `ACCEPTABLE_DATA_LOSS_RATIOS`: Max allowed data loss.
- `ACCEPTABLE_RECORDING_DURATIONS`: Acceptable session duration range.
- `ACCEPTABLE_NUM_PRACTICE_TRIALS`: Expected number of practice trials.
- `ACCEPTABLE_NUM_TRIALS`: Expected minimum number of trials.

### Logging Settings

- `LOG_LEVEL`: General log level (default: `INFO`).
- `CONSOLE_LOG_LEVEL`: What you see in the terminal.
- `FILE_LOG_LEVEL`: What is saved to `preprocessing_logs.txt` (usually `DEBUG`).

## Programmatic Usage (Notebooks)

If you are using the package in a Python script or Jupyter notebook:

```python
from preprocessing import settings

# Load a specific config file
settings.load("path/to/your_config.yaml")

# Access settings
print(settings.DATA_COLLECTION_NAME)
```

## Internal Constants

The `settings` object also contains technical parameters like folder names (`RAW_DATA_FOLDER`, etc.)
and regex patterns. These are marked as internal in the template and should not be modified.

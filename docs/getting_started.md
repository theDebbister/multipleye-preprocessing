(getting_started)=

# Getting Started

For the pEYEpline to function, there are some requirements that need to be met.
This page explains the setup of the {ref}`pEYEpline`, how to install the {ref}`eyelink_dev_kit`,
and {ref}`running_pipelines`.
More details on how to use the pEYEpline can be found in the {ref}`reference_guide`.

(pipeline_structure)=

## pEYEpline

The pEYEpline is written in Python and uses a few dependencies,
including [`pymovements`](https://pymovements.readthedocs.io/), `polars`, `matplotlib`,
among others.
The pEYEpline is not distributed on PyPI and should be used directly from the source code.
To download the source code,
you can clone the [
`MultiplEYE-COST/multipleye-preprocessing`](https://github.com/MultiplEYE-COST/multipleye-preprocessing)
repository to your local machine.

```bash
git clone https://github.com/MultiplEYE-COST/multipleye-preprocessing.git
```

Once cloned, navigate into the cloned repository.

```bash
cd multipleye-preprocessing/
```

### Installation

To use the pEYEpline, we expect you to have python set up on your machine.
Make sure to use an up-to-date python version.
The pEYEpline has been developed with `3.13` and up in mind.

We recommend using `uv` to set up your environment, as it will automatically install the
dependencies
as specified in `pyproject.toml`.

1. Install `uv` by following the instructions on
   their [website](https://docs.astral.sh/uv/getting-started/installation/).
2. Clone the repository and navigate into it (see above).
3. Now, you can set the environment up using [`uv`](https://docs.astral.sh/uv/):

    ```bash
    uv sync
    ```
4. And activate it, with Unix (Mac/Linux):
   ```
   source .venv/bin/activate
   ```

   Or for Windows:
   ```
   .venv\Scripts\activate
   ```

```{note}
If you do not want to use `uv`, you can install the pEYEpline in editable mode:
```bash
pip install -e .
```

## Eye-tracker specific requirements

In order to use the pEYEpline, there are eye-tracker specific libraries required.
At the moment, only EyeLink eye-trackers are supported.

(eyelink_dev_kit)=

### EyeLink Developers Kit

Before we can {ref}`run the pEYEpline <running_pipelines>`,
we need to install the EyeLink Developers Kit.
This is needed to convert files from the proprietary `.edf` format to the parsable `.asc` format,
the binary `edf2asc` needs to be installed.

The `edf2asc` utility is being delivered with the EyeLink Developers Kit and is owned by
SR Research Ltd., being distributed through their forum website.
To access the download, an account must be created first.
If you do not own an account on the SR Support Forum yet,
[register in their support forum](https://www.sr-research.com/support/member.php?action=register):

1. Fill in the *Account Details* and *Preferences*.
2. In the *Required Information* section, select the EyeLink system you use
   (e.g., EyeLink Portable Duo) and your institution and role information.
3. Fill in *Image Verification* and *Security Question*.
4. Confirm your mail address through the mail you should receive from `support@sr-research.com`.
5. Wait, as each registration needs to be approved manually. This may take a day.

When you have an account:
Navigate to [the download page](https://www.sr-research.com/support/thread-13.html)
and login, unless you are already logged in.
If you need some context on the EyeLink Developers Kit,
you can read through this page.
Select the download fitting your operating system and install it.
An installation guide is available for Windows and macOS at the bottom of the page.

After installation, you should have access to the `edf2asc` program.
To confirm that it is available, open a terminal or command prompt and run:

```bash
edf2asc
```

This should show the program's version and usage information.

(running_pipelines)=

## Running the pEYEpline

### Download your MultiplEYE data

```{attention}
The steps below require that you have access to a protected folder where the MultiplEYE data for one data collection is stored.
You have only been granted access to this folder if you are part of the data collection for this language.
```

1. Download the data folder from the online repository. Download the content of the entire folder.
   When you download it from SwitchDrive, it will automatically create a .tar file.
2. Add the folder to the `data/` folder in this repo. Its name should be the name of the data
   collection, e.g. `MultiplEYE_ZH_CH_Zurich_1_2025`.
3. Extract the .tar file in the `data/` folder.
4. Please make sure that the extracted folder has the same structure as the folder online.

### Configuration

The MultiplEYE pEYEpline uses a central configuration system to manage all parameters,
ensuring reproducible and consistent data processing. Before you start processing your data, you need to set up this configuration.

When you run the pEYEpline for the first time in a new directory, it will create a template called `multipleye_settings_preprocessing.yaml` for you.

```bash
uv run run_preprocessing
```

After it stops, open this file and configure the following parameters:

- `DATA_COLLECTION_NAME`: **(Required)** A unique identifier for your collection.
    - Format: `MultiplEYE_[LANG]_[COUNTRY]_[CITY]_[LAB_NO]_[YEAR]`
    - Example: `MultiplEYE_EN_UK_London_1_2026`
    - **Note**: This name has been given to you by the MultiplEYE project.
      It is used to determine data and output paths. If it doesn't match the
      required 6-part format, the pEYEpline might fail to resolve certain paths.
- `OVERWRITE`: `true` to reprocess existing data, `false` (default) to only load the output of previously processed sessions instead of recalculation.
- `EXPERIMENT_TYPE`: `MultiplEYE` (default) or `MeRID`.
- `INCLUDE_SESSIONS` / `EXCLUDE_SESSIONS`: Optional lists to filter which sessions are processed.
- `INCLUDE_PILOTS`: `true` to include data from pilot folders (default: `false`).
- `EXPECTED_SAMPLING_RATE_HZ`: The sampling rate of your eye tracker (default: `1000`).

**Do not change** any of the parameters marked for internal usage, as they ensure consistency across the MultiplEYE project.

Please find additional information on the configuration here: {ref}`configuration_guide`

### Preprocess your data

If it is your first time with the pEYEpline, you can explore it step-by-step by processing one session with the [step-by-step Jupyter notebook](https://github.com/MultiplEYE-COST/multipleye-preprocessing/blob/main/preprocessing.ipynb). You can also open the same file locally at `preprocessing.ipynb` in the repo root.


To process several sessions at once, the pEYEpline can be executed directly from the command line.
For more detailed information on required data and formats and all the steps of the pEYEpline please read into the more detailed {ref}`reference_guide` chapter.

To run the pEYEpline (if you used `uv` for installation and activated the
environment):

```bash
run_preprocessing
```

You can always check the available options for each script by using the `--help` flag:

```bash
run_preprocessing --help
```

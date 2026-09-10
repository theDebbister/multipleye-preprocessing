<p style="text-align:center;">
<img width="110%" height="110%" alt="pEYEpline"
 src="https://raw.githubusercontent.com/MultiplEYE-COST/multipleye-preprocessing/main/docs/_static/logo.svg"
 onerror="this.onerror=null;this.src='./docs/_static/logo.svg';"/>
</p>

---

[![Documentation](https://img.shields.io/badge/Documentation-Visit-blue)](https://multipleye-cost.github.io/multipleye-preprocessing/)
[![GitHub Repository](https://img.shields.io/badge/Source-Code-green)](https://github.com/MultiplEYE-COST/multipleye-preprocessing)
[![Python Version](https://img.shields.io/badge/Python-3.13+-yellow)](https://www.python.org/)

# MultiplEYE Preprocessing pEYEpline

> [!TIP]
> Version
> [v2026.07.01](https://github.com/MultiplEYE-COST/multipleye-preprocessing/releases/tag/v2026.07.01)
> (July 2026) marks the first stable release.
> From this version onward, the output format and core API are
> considered stable. Future updates will focus on maintenance,
> bug fixes, and feature additions without breaking changes.

> [!IMPORTANT]
> This repository is **stable and actively maintained**. Please:
> - Keep the repository up-to-date to receive the latest changes, fixes, and improvements
> - Report issues if you encounter unexpected behavior
> - Refer to the documentation for the latest information on how to use the pEYEpline
> - Check the
> - [troubleshooting guide](https://multipleye-cost.github.io/multipleye-preprocessing/troubleshooting/)
    if you encounter any issues

This repository contains the pEYEpline for eye-tracking data and psychometric test
scoring from the MultiplEYE project.

If you are running the pEYEpline and encounter any issues, please check
the [troubleshooting guide](https://multipleye-cost.github.io/multipleye-preprocessing/troubleshooting/).

> [!NOTE]
> This repository processes data recorded with
> [MultiplEYE-psychometric-tests](https://github.com/MultiplEYE-COST/MultiplEYE-psychometric-tests).

## What You Can Do With This Repository

### 1. Run the Preprocessing Pipeline

Process raw eye-tracking data (EyeLink `.edf` files) and score psychometric tests in one
workflow:

```bash
# Configure your settings in multipleye_settings_preprocessing.yaml
run_preprocessing
```

This handles:

- Converting `.edf` to `.asc` format
- Parsing and validating eye-tracking data
- Applying filters and detecting events
- Generating preprocessed output files
- Scoring psychometric tests

> [!TIP]
> A step-by-step notebook is available in `preprocessing.ipynb` to walk through the pEYEpline in
> detail.

> [!IMPORTANT]
> Psychometric tests require data to be structured correctly. See the
> [Psychometric Tests documentation](https://multipleye-cost.github.io/multipleye-preprocessing/guide/psychometric_tests/)
> for details on the expected data format.

### 2. Score Psychometric Tests (Standalone)

If you only need to re-score psychometric tests without re-running the pEYEpline, use the
standalone command:

```bash
preprocess_psychometric_tests
```

This uses the same data already prepared by `run_preprocessing` and produces the same output.

---

## Installation

For full installation instructions, see
the [Getting Started guide](https://multipleye-cost.github.io/multipleye-preprocessing/getting_started/).

Quick setup:

```bash
git clone https://github.com/MultiplEYE-COST/multipleye-preprocessing.git
cd multipleye-preprocessing/
uv sync
source .venv/bin/activate  # Unix/Mac
# or
.venv\Scripts\activate  # Windows
```

---

## Documentation Overview

| Topic                                                                                                              | Description                                          |
|--------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|
| [Getting Started](https://multipleye-cost.github.io/multipleye-preprocessing/getting_started/)                     | Installation, requirements, and running the pEYEpline |
| [Preprocessing](https://multipleye-cost.github.io/multipleye-preprocessing/guide/preprocessing/)                   | Detailed pEYEpline documentation        |
| [Reading Measures](https://multipleye-cost.github.io/multipleye-preprocessing/guide/reading_measures/)             | Reading measures from preprocessed eye-tracking data |
| [Psychometric Tests](https://multipleye-cost.github.io/multipleye-preprocessing/guide/psychometric_tests/)         | Test descriptions and scoring details                |
| [Configuration](https://multipleye-cost.github.io/multipleye-preprocessing/guide/configuration/)                   | Configuration file options                           |
| [Technical Architecture](https://multipleye-cost.github.io/multipleye-preprocessing/guide/technical_architecture/) | Code structure and design                            |

---

## Quick Start

1. Update settings in `multipleye_settings_preprocessing.yaml`
2. Run the full pEYEpline (eye-tracking + psychometric tests): `run_preprocessing`
3. Re-score psychometric tests standalone (optional): `preprocess_psychometric_tests`

> [!CAUTION]
> EyeLink-specific: You must install the EyeLink Developers Kit to convert `.edf` files. See the
> [installation guide](https://multipleye-cost.github.io/multipleye-preprocessing/getting_started/)
> for details.

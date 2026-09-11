(preprocessing_pipeline_index)=

<p style="text-align:center;">
<img width="110%" height="110%" alt="pEYEpline"
 src="_static/logo.svg"
 onerror="this.onerror=null;this.src='../_static/logo.svg';"/>
</p>

::::{grid} 1 2 2 2
:gutter: 1 1 1 2

:::{grid-item-card} {material-regular}`rocket;2em` Getting Started
:link: getting_started
:link-type: ref

How to prepare before running your first preprocessing.\
Start your endeavor here!

+++ {ref}`Learn more » <getting_started>`
:::

:::{grid-item-card} {material-regular}`menu_book;2em` Reference Guide
:link: reference_guide
:link-type: ref

If you are interested in the details of the pEYEpline, this section is for you.

+++ {ref}`Learn more »<reference_guide>`
:::

:::{grid-item-card} {material-regular}`help_outline;2em` FAQ
:link: faq
:link-type: ref

Answers to frequently asked questions.

+++ {ref}`Learn more »<faq>`
:::

:::{grid-item-card} {material-regular}`warning;2em` Troubleshooting
:link: troubleshooting
:link-type: ref

Solutions to common warnings and errors.

+++ {ref}`Learn more »<troubleshooting>`
:::

::::

The pEYEpline for the MultiplEYE corpus by {cite:t}`JakobiDingEtAl2025MultipleyeCorpus`. The
pEYEpline is designed to process the raw eye-tracking data and psychometric test data collected in
the MultiplEYE project, transforming it into a standardized format suitable for analysis and sharing
with the research community.

The pEYEpline is built in Python and its core functionalities rely on the `pymovements` library,
which provides tools for processing eye-tracking data.
See [pymovements website](https://pymovements.readthedocs.io/en/stable/).

## What you can do

- **Run the pEYEpline:** Process raw eye-tracking data (EyeLink `.edf` files) and score psychometric
  tests in one workflow.
- **Score psychometric tests standalone:** Re-score tests without re-running the full pEYEpline.

```bash
run_preprocessing                    # run the full pEYEpline
preprocess_psychometric_tests        # score psychometric tests only
```

## Quick start

```bash
git clone https://github.com/MultiplEYE-COST/multipleye-preprocessing.git
cd multipleye-preprocessing/
uv sync
source .venv/bin/activate
```

1. Run the pEYEpline: `run_preprocessing`
2. Update settings in `multipleye_settings_preprocessing.yaml`
3. Rerun the pEYEpline: `run_preprocessing`

## Setup and use

To use the pEYEpline, please follow the instructions in the {ref}`getting_started` section. This
section will guide you through the setup, including how to install dependencies and run the
pEYEpline on your data collection.

## How to cite

If you use the pEYEpline, or parts of it in your research, please cite it as specified in {cite:t}
`Jakobi2026MultiplEYEPreprocessing`. You can also find citation information for this project in the
`CITATION.cff`
file in the repository and cite it accordingly.

## Acknowledgments

This project has been partially funded by:

- MultiplEYE COST Action, CA21131
- Swiss National Science Foundation (SNSF), 212276 (MeRID)
- swissuniversities, OpenEye

```{eval-rst}
.. toctree::
   :hidden:
   :name: table_of_contents
   :caption: Table of Contents
   :maxdepth: 2
   :glob:

   getting_started
   guide/index
   faq
   troubleshooting
   bibliography
```

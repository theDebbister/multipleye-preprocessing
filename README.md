# multipleye-preprocessing

## Goals

- Preprocess data on session level
- Keep intermediate results between steps
- Keep preprocessing steps modular, allow manual intervention between steps
- Make pipeline self-contained and reproducible
- Support only EyeLink (for now)

## Data flow

![](preprocessing.drawio.png)

## Roadmap

- [ ] Basic pipeline skeleton
  - [ ] Pipeline config
  - [ ] CLI
- [ ] Preprocessing steps
  - [ ] edf2asc
  - [ ] Raw sample extraction
    - [ ] Coordinate normalization
    - [ ] AOI mapping
  - [ ] Fixation detection
  - [ ] Reading measure calculation
- [ ] Quality checks
- [ ] Plots
- [ ] Documentation

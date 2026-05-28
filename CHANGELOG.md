# Changelog

## v1.9.2

- Performed a public-release readiness pass for the GitHub package.
- Updated package metadata and citation version to `1.9.2`.
- Corrected the 100-instance mixed benchmark manifest so complexity fields are populated with the current metadata schema.
- Re-tested unit tests, CLI generation, planted-schedule feasibility checking, and mixed 100-instance generation.

## v1.9.1

- Restored and emphasized the main mixed benchmark profile workflow for small, medium, large, sparse, tight, low-availability, and hard instances.
- Added `scripts/generate_100_mixed_benchmark_instances.py` for generating a 100-instance general benchmark set from the original profile families.
- Updated README and benchmark generation documentation to distinguish the general mixed benchmark set from Pareto-template datasets.
- Added manifest and design CSV outputs for the 100-instance mixed benchmark workflow.

## v1.9.0

- Prepared a clean GitHub-ready package layout.
- Removed generated sample outputs and cache folders from the repository package.
- Rewrote the main README for public repository use.
- Added detailed benchmark generation methodology documentation.
- Added reviewer-response and manuscript data-availability text templates.
- Moved 100-instance helper scripts to `scripts/`.
- Kept installation-free `PYTHONPATH=src` usage as the primary workflow.


## v1.8.2

- Added `generate-pareto-template-ultralight` command.
- Added `pareto_template_ultralight.py`.
- Added `generate_100_pareto_template_ultralight_instances.py`.
- Ultra-light template fixes `D=2`, `W=3`, `H=1..2`, `I=3..4` to reduce active `i,d,w,h` combinations for exact GAMS/AUGMECON runs.
- 100-instance helper was optimized to import the generator directly instead of launching 100 subprocesses.



## v1.8.1

- Added `generate-pareto-template-light` for small, sparse Pareto-oriented instances.
- Added `generate_100_pareto_template_light_instances.py` helper.
- Light template limits dimensions to `I=3..5`, `D=2..3`, `W=3..4`, `H=1..2`.
- Uses sparse `B(w,h)` and exactly two ward choices for flexible courses to reduce active `IDWH` combinations for exact GAMS/AUGMECON runs.

## v1.6.0

- Added GAMS-friendly XLSX sheets: `GAMS_Index`, `set_*`, `par_*`, and `tab_*`.
- Added per-instance `txt/` folder with one tab-delimited TXT file for every set, parameter, binary table, and planted schedule.
- Added per-instance `M/` folder with MATLAB loaders that read the TXT files into a structured MATLAB `snap` struct.
- Added per-instance `gams/` folder with GDXXRW helper files for converting `instance.xlsx` to `instance.gdx`.

## v1.4.6

- Fixed `generate-grid` default behavior to generate all official benchmark profiles, not only `vvs` and `vs`.
- Added explicit `DEFAULT_GRID_PROFILES` list: `vvs`, `vs`, `snap_s`, `snap_m`, `snap_l`, `snap_tight`, `snap_sparse`, `snap_lowavail`, `snap_hard`.
- Updated bundled sample outputs to include one generated instance from every default profile.
- Kept `tiny` excluded from the default grid because it is only for developer smoke tests.


## 1.4.6

- Added two exact-test size profiles: `vvs` (I=3, D=1, W=1, H=1) and `vs` (I=4, D=2, W=2, H=1).
- Updated README and documentation for the new very small profiles.
- Added tests confirming requested dimensions and feasibility for `vvs` and `vs`.

## 1.4.4

- Removed all Windows `.bat` helper files.
- Made the no-install `PYTHONPATH=src` workflow the primary usage path.
- Updated README and beginner documentation to avoid `pip install -e .` for normal users.
- Kept editable installation only as an optional developer workflow.


## v1.4.3
- Fixed Cap(d,w,h) generation for valid course-ward-hospital combinations.
- All eligible hospitals that contain a ward now receive independent demand-aware capacities.
- Capacities may differ across hospitals and may also coincide naturally, but non-selected hospitals no longer receive a misleading default capacity of 1.
- Added tests to ensure valid capacities are at least large enough to host a required student group.

## v1.4.2

- Added no-install Windows batch files for offline/non-Python users.
- Added offline usage documentation.
- Updated README to avoid `pip install -e .` as the default path for beginners.
- Relaxed build-system requirement from `setuptools>=68` to `setuptools>=61`.

## v1.4.1

- Verified schema and model-aligned generation.
- Fixed capacities for invalid `Eb(d,w,h)=0` combinations to zero.

## v1.8.0

- Added `generate-pareto-template`, a dedicated template-based Pareto-friendly instance generator.
- Allowed hospital count for template Pareto generation in the range `1..3`.
- Template generator uses a fixed baseline course plus flexible ward-choice courses to encourage Pareto trade-offs.
- Added `generate_100_pareto_template_instances.py` helper script.
- Added documentation in `docs/11_pareto_template_generator.md`.

# Output files

Each generated instance folder contains the following files.

## `instance.json`

The canonical machine-readable problem data. Use this file in optimization models and algorithms.

## `instance.xlsx`

A review-friendly Excel workbook that mirrors `instance.json`. It contains separate sheets for sets, groups, courses, semester plan, wards, hospitals, model parameters, the planted solution, and metadata.

## `load_<instance_id>.m`

A per-instance MATLAB loader. It reads `instance.json`, `metadata.json`, and `planted_solution.csv` from the same folder and returns a MATLAB struct named `snap`.

## `planted_solution.csv`

A known feasible schedule generated together with the instance. It is intended for validation and sanity checks, not as an optimized solution.

## `metadata.json`

Generation metadata, including profile, seed, complexity indicators, and the planted-solution feasibility report.

## `bundle_manifest.json`

A small manifest listing all files included in the instance bundle.

## Schema clarity note

The set `I` is represented as student groups. Generated files use `group_id` only. Fields such as `student_id`, duplicate `group`, `level`, `allowed_levels`, `allowed_groups`, and legacy compatibility views are intentionally omitted to avoid misleading readers.


## v1.4.5 very small profiles

Two exact-test size profiles were added: `vvs` with I=3, D=1, W=1, H=1 and `vs` with I=4, D=2, W=2, H=1. They are intended for very small mathematical-model tests and early solver validation.

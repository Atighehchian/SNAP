# SNAP Benchmark Instance Generator

A clean Python package for generating reproducible benchmark instances for the **Student Nurse Allocation Problem (SNAP)** during clinical training.

The generator is designed for research experiments involving exact mathematical programming, GAMS, MATLAB, and metaheuristic algorithms such as NSGA-II. It creates model-aligned instances with controlled feasibility, structural difficulty, sparsity, tightness, and Pareto-front potential.

> This is a **SNAP-specific, Taillard-inspired** benchmark generator. It follows the reproducibility and controlled-randomness philosophy of scheduling benchmark generators, but it is **not** the original Taillard flow-shop/job-shop/open-shop generator.

---

## What this repository provides

This repository includes:

```text
src/snapbench/                      Python package
scripts/                            Batch generation helper scripts
docs/                               Methodological documentation
tests/                              Basic regression tests
matlab/                             MATLAB loading utilities
examples/                           Small command examples
```

For each generated instance, the package can write:

```text
instance.json                       Canonical machine-readable instance data
instance.xlsx                       Human-readable and GAMS-friendly workbook
txt/                                One TXT file per set, parameter, and table
M/                                  MATLAB loaders that read txt/ files
gams/                               GAMS/GDXXRW helper files
load_<instance_id>.m                Backward-compatible MATLAB loader
planted_solution.csv                Constructed reference schedule when available
metadata.json                       Seed, profile, complexity, feasibility metadata
bundle_manifest.json                File list and export metadata
```

The canonical source of truth is always:

```text
instance.json
```

---

## Core model structure

Generated instances follow the mathematical model structure with the following main sets:

| Symbol | Meaning |
|---|---|
| `I` | student groups |
| `D` | courses |
| `W` | clinical wards |
| `H` | hospitals |
| `S` | shifts |
| `T` | days in a week |
| `K` | weeks in the academic term |

The academic time structure is fixed:

```text
S = 2 shifts
T = 6 days per week
K = 16 weeks
```

Important generated parameters include:

```text
B(w,h)          ward-hospital existence
Mea(d,w)        course-ward eligibility
Eb(d,w,h)       valid course-ward-hospital combination
Comm(i,d)       group-course requirement
Com(i,d,w)      group-course-ward requirement
Du(d)           course duration in training days
O(d)            required consecutive training days
PW(d)           ward-choice logic
Dur(d,w)        duration assigned to course-ward relation
weeks(d,w)      required weeks for course-ward relation
Cap(d,w,h)      capacity of course-ward-hospital combination
Av(i,t,k)       student-group availability
Avb(w,h,t,k)    ward-hospital availability
ne(d,w)         long-shift flag
nt(w)           overlap/interference permission
nee(d,w)        minimum long-shift requirement
```

---

## Feasibility-by-construction logic

The generator is not an unconstrained random sampler. It applies feasibility safeguards during construction:

1. Every course has at least one eligible ward.
2. Every ward exists in at least one hospital.
3. Every hospital contains at least one ward.
4. Valid resource combinations are derived as:

   ```text
   Eb(d,w,h) = Mea(d,w) * B(w,h)
   ```

5. Student-course-ward demand is derived as:

   ```text
   Com(i,d,w) = 1 if Comm(i,d)=1 and Mea(d,w)=1
   ```

6. Invalid `d,w,h` combinations receive zero capacity.
7. Valid `d,w,h` combinations receive meaningful positive capacity.
8. Capacity is checked against group size.
9. Student availability is generated with consecutive-day blocks compatible with `O(d)`.
10. Excessive `PW=0` multi-ward courses are avoided because they multiply the required workload.
11. A planted/reference schedule is generated and can be checked.

This does not mean every arbitrary custom input is guaranteed to be easy. It means the built-in profiles and template generators are designed to avoid accidental infeasibility caused by inconsistent random data.

---

## Installation-free usage

The recommended workflow is to run the package directly from source. This avoids `pip install -e .`, which can be inconvenient on machines without internet access.

### Windows Command Prompt

```bat
set PYTHONPATH=src
python -m snapbench.cli profiles
```

### Windows PowerShell

```powershell
$env:PYTHONPATH="src"
python -m snapbench.cli profiles
```

### Linux / macOS

```bash
PYTHONPATH=src python -m snapbench.cli profiles
```

Optional editable install for developers:

```bash
python -m pip install -e . --no-build-isolation --no-deps
```

---

## Quick start

Generate a small benchmark grid:

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-grid --output instances --instances-per-profile 2 --seed 20260508
```

Generate without Excel output for faster benchmark creation:

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-grid --output instances --instances-per-profile 2 --seed 20260508 --no-xlsx
```

Generate the main 100-instance mixed benchmark set across the original profile families:

```bat
set PYTHONPATH=src
python scripts\generate_100_mixed_benchmark_instances.py --output instances_mixed_100 --seed 20260508
```

This script generates a balanced benchmark set from the main instance families: `vvs`, `vs`, `snap_s`, `snap_m`, `snap_l`, `snap_tight`, `snap_sparse`, `snap_lowavail`, and `snap_hard`. By default, it skips XLSX export for speed; add `--with-xlsx` if Excel files are required.

Check the planted schedule of one instance:

```bat
set PYTHONPATH=src
python -m snapbench.cli check --instance instances/snap_s_001/instance.json --schedule instances/snap_s_001/planted_solution.csv
```

Describe instance complexity:

```bat
set PYTHONPATH=src
python -m snapbench.cli describe --instance instances/snap_s_001/instance.json
```

---

## Available generation commands

### List profiles

```bat
set PYTHONPATH=src
python -m snapbench.cli profiles
```

### Generate one profile

```bat
set PYTHONPATH=src
python -m snapbench.cli generate --output instances --profile snap_s --instances 5 --seed 20260508
```

### Generate a grid across default profiles

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-grid --output instances --instances-per-profile 2 --seed 20260508
```

### Generate custom dimensions

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-custom --output instances_custom --name custom_4_2_3_1 --groups 4 --courses 2 --wards 3 --hospitals 1 --instances 3 --seed 20260508
```

### Generate Pareto-friendly custom dimensions

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-custom --output instances_pareto --name pareto_8_4_5_2 --groups 8 --courses 4 --wards 5 --hospitals 2 --instances 3 --seed 20260508 --pareto-friendly
```

### Generate template-based Pareto instances

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-pareto-template --output instances_template --name tpl_4_3_4_2 --groups 4 --courses 3 --wards 4 --hospitals 2 --instances 5 --seed 20260508 --no-xlsx
```

### Generate light Pareto-template instances

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-pareto-template-light --output instances_light --name light_4_2_3_2 --groups 4 --courses 2 --wards 3 --hospitals 2 --instances 5 --seed 20260508 --no-xlsx
```

### Generate ultra-light Pareto-template instances

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-pareto-template-ultralight --output instances_ultra --name ultra_3_2 --groups 3 --hospitals 2 --instances 5 --seed 20260508 --no-xlsx
```

---

## Instance families

| Family | Purpose |
|---|---|
| `vvs` | Very very small exact-solver tests |
| `vs` | Very small exact-solver tests |
| `snap_s` | Small MIP-oriented instances |
| `snap_m` | Medium instances |
| `snap_l` | Larger benchmark instances |
| `snap_sparse` | Fewer valid course-ward-hospital combinations |
| `snap_tight` | Reduced capacity slack and stronger resource competition |
| `snap_lowavail` | Controlled availability pressure |
| `snap_hard` | Larger and more structurally difficult benchmark cases |
| `pareto-friendly` | Data-level conflict between resource concentration and completion time |
| `pareto-template` | Small structured instances for Pareto-front testing |
| `pareto-template-light` | Sparse exact-solver-friendly Pareto instances |
| `pareto-template-ultralight` | Ultra-sparse instances inspired by a manually validated Pareto case |

### Tight instances

Tight instances are not intended to be randomly infeasible. They reduce capacity slack and increase resource competition while preserving construction safeguards. They are useful for testing robustness and runtime behavior under constrained but meaningful conditions.

### Sparse instances

Sparse instances reduce the number of valid assignment combinations. This is important because the computational burden depends strongly on active combinations, not only on the raw product `I*D*W*H`.

### Main mixed benchmark set

The main mixed benchmark set is not limited to Pareto-template instances. It contains the original profile families used for general computational testing:

| Profile | Role in the benchmark | Typical use |
|---|---|---|
| `vvs` | Very very small instances | Smoke tests and exact-solver debugging |
| `vs` | Very small instances | Basic model validation |
| `snap_s` | Small MIP-oriented instances | Exact and heuristic comparison on small cases |
| `snap_m` | Medium benchmark instances | General NSGA-II and heuristic evaluation |
| `snap_l` | Large benchmark instances | Metaheuristic scalability testing |
| `snap_tight` | Tight-capacity instances | Robustness under resource competition |
| `snap_sparse` | Sparse eligibility instances | Effect of limited course-ward-hospital alternatives |
| `snap_lowavail` | Availability-pressure instances | Effect of limited student/resource availability |
| `snap_hard` | Larger mixed-difficulty instances | Stress testing and metaheuristic evaluation |

The helper script `scripts/generate_100_mixed_benchmark_instances.py` generates exactly 100 instances across these families. This is the recommended dataset for broad computational analysis. The Pareto-template scripts are complementary and should be used when the specific goal is to test Pareto-front formation on small exact-solver-friendly cases.

### Pareto-template instances

Pareto-template instances are designed to create a controlled trade-off:

```text
using fewer wards/resources  -> longer completion time
using more wards/resources   -> shorter completion time
```

This structure is useful for testing AUGMECON, NSGA-II, Hypervolume, and Pareto-front quality metrics.

---

## Active assignment size

The raw size

```text
I * D * W * H
```

does not fully describe the difficulty of a SNAP instance. A more informative measure is:

```text
Active_IDWH = number of valid (i,d,w,h) combinations
```

where:

```text
Com(i,d,w)=1 and Eb(d,w,h)=1
```

The package stores complexity metadata in `metadata.json` and can recompute it using:

```bat
set PYTHONPATH=src
python -m snapbench.cli describe --instance path\to\instance.json
```

---

## Batch helper scripts

The `scripts/` folder includes helper scripts for generating larger experimental sets. The most important general benchmark script is:

```text
scripts/generate_100_mixed_benchmark_instances.py
```

It generates a 100-instance mixed benchmark set from the original benchmark families:

```text
vvs=5
vs=5
snap_s=15
snap_m=15
snap_l=10
snap_tight=15
snap_sparse=15
snap_lowavail=10
snap_hard=10
```

Run it with:

```bat
set PYTHONPATH=src
python scripts\generate_100_mixed_benchmark_instances.py --output instances_mixed_100 --seed 20260508
```

Use `--with-xlsx` if full Excel workbooks are required:

```bat
set PYTHONPATH=src
python scripts\generate_100_mixed_benchmark_instances.py --output instances_mixed_100 --seed 20260508 --with-xlsx
```

Pareto-template helper scripts are also included:

```text
scripts/generate_100_pareto_template_instances.py
scripts/generate_100_pareto_template_light_instances.py
scripts/generate_100_pareto_template_ultralight_instances.py
```

Example:

```bat
set PYTHONPATH=src
python scripts\generate_100_pareto_template_ultralight_instances.py --output instances_ultralight_100 --seed 20260508 --no-xlsx
```

---

## GAMS and MATLAB support

For GAMS, each instance can include:

```text
gams/gdxxrw_symbols.txt
gams/import_to_gdx.gms
gams/declarations_and_load.inc
```

For MATLAB, each instance can include:

```text
load_<instance_id>.m
M/load_instance.m
```

The `txt/` folder contains tab-delimited files for all sets, parameters, tables, and schedules, allowing external solvers to load the same instance data without relying on `instance.xlsx`.

---

## Reproducibility

Every instance is generated from:

```text
base_seed + instance-specific deterministic seed logic
```

Metadata files store the base seed, instance seed, generation mode, profile, size, complexity, and feasibility diagnostics. Reusing the same command and seed regenerates the same benchmark set.

---

## Suggested experimental use

For exact mathematical programming:

```text
vvs, vs, snap_sparse, pareto-template-light, pareto-template-ultralight
```

For NSGA-II and metaheuristics:

```text
snap_s, snap_m, snap_tight, snap_lowavail, snap_hard, pareto-friendly
```

For Pareto-front quality analysis:

```text
pareto-template, pareto-template-light, pareto-template-ultralight
```

Recommended reporting metrics:

```text
number of Pareto points
Hypervolume
normalized Hypervolume
spacing
runtime
feasibility ratio
active assignment size
```

---

## Development tests

```bash
PYTHONPATH=src pytest
```

---

## Citation and data availability

If used in a manuscript, cite the repository and specify the exact release tag, seed, and generation command. A `CITATION.cff` file is included and should be updated with the final authors, title, DOI, and repository URL before publication.

---

## License

MIT License. See `LICENSE`.

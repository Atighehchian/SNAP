# Benchmark Instance Generation Methodology

This document explains how SNAP benchmark instances are generated, how feasibility is controlled, and how the different instance families should be used in computational experiments.

## 1. Design philosophy

The generator creates model-aligned benchmark instances for the Student Nurse Allocation Problem. It is not an unconstrained random generator. It uses controlled randomization, deterministic seeds, construction rules, and feasibility checks.

The goals are:

1. to follow the mathematical model structure;
2. to reduce accidental infeasibility;
3. to generate diverse benchmark families;
4. to support exact and metaheuristic experiments;
5. to support reproducible public experiments.

The generator is Taillard-inspired in the sense that it provides controlled benchmark profiles and seed-based reproducibility. It is not the original Taillard scheduling generator.

## 2. Feasibility-oriented construction

The generator applies feasibility safeguards during construction.

### 2.1 Course, ward, and hospital consistency

The course-ward matrix is defined as:

```text
Mea(d,w) = 1 if course d can be delivered in ward w
```

The ward-hospital matrix is:

```text
B(w,h) = 1 if ward w exists in hospital h
```

The valid course-ward-hospital matrix is derived as:

```text
Eb(d,w,h) = Mea(d,w) * B(w,h)
```

This prevents invalid combinations from entering the model.

### 2.2 Student-course consistency

The group-course requirement is:

```text
Comm(i,d) = 1 if group i must take course d
```

The group-course-ward requirement is derived as:

```text
Com(i,d,w) = 1 if Comm(i,d)=1 and Mea(d,w)=1
```

This prevents requirements that cannot be served by any eligible ward.

### 2.3 Time consistency

The time structure is fixed:

```text
S = 2
T = 6
K = 16
```

The generator ensures that course duration, required consecutive days, and required weeks are mutually compatible. Student availability is generated with compatible consecutive-day blocks. This is important because an instance can be infeasible even if it has enough available days in total, when those days do not form the required consecutive block.

### 2.4 Capacity consistency

If `Eb(d,w,h)=0`, then `Cap(d,w,h)=0`. If `Eb(d,w,h)=1`, then a positive meaningful capacity is generated. Valid hospitals are not silently assigned arbitrary default capacities.

Capacity is checked against group size to avoid trivial infeasibility.

### 2.5 Workload consistency

The generator controls the number of required courses per group and avoids excessive `PW=0` courses with multiple wards. A `PW=0` course with multiple wards multiplies the required workload and can easily exceed the 16-week horizon.

## 3. Instance families

### 3.1 Standard instances

Standard instances provide general benchmark data for testing file formats, feasibility checks, and baseline algorithms.

### 3.2 Sparse instances

Sparse instances reduce `Mea`, `B`, and therefore `Eb` density. They reduce active assignment combinations and are useful for exact solvers or early debugging.

### 3.3 Tight instances

Tight instances reduce capacity slack and increase competition for resources. They are generated with feasibility safeguards; they are not intended to be accidentally infeasible. They are useful for studying runtime and robustness under constrained resources.

### 3.4 Low-availability instances

Low-availability instances introduce controlled availability pressure. Availability restrictions are generated carefully so that required consecutive-day blocks are not accidentally destroyed.

### 3.5 Hard instances

Hard instances combine larger size, tighter resource structures, and more complex eligibility relations. They are primarily intended for metaheuristic and large-scale testing.

### 3.6 Pareto-friendly instances

Pareto-friendly instances are designed to create objective conflict:

```text
fewer selected wards/resources -> longer completion time
more selected wards/resources  -> shorter completion time
```

This is done by combining fixed courses and flexible courses. Fixed courses typically have one ward. Flexible courses have several eligible wards and `PW(d)=1`.

### 3.7 Pareto-template instances

Template instances are smaller, structured cases intended for exact multi-objective tests. They are inspired by a manually validated instance that produced multiple Pareto points.

### 3.8 Pareto-template-light and ultra-light

These are sparse and small enough for exact solvers. Ultra-light instances typically use:

```text
I = 3 or 4
D = 2
W = 3
H = 1 or 2
O(d) = 3
mem(i) = 1
one fixed course
one flexible course
capacity = 1
```

They are useful for fast AUGMECON/GAMS testing and Pareto-front validation.

## 4. Active assignment size

Raw size is not enough:

```text
I * D * W * H
```

The more meaningful size indicator is:

```text
Active_IDWH = |{(i,d,w,h): Com(i,d,w)=1 and Eb(d,w,h)=1}|
```

This quantity better reflects the number of active binary assignment possibilities.

## 5. Reproducibility

All generation commands accept a base seed. Each instance receives an instance-specific seed. Metadata files store seed, profile, size, generation mode, complexity, and feasibility information.

## 6. Recommended reporting

When reporting experiments, include:

```text
profile or generation command
base seed
number of instances
size indicators
Active_IDWH
feasibility ratio
runtime
number of Pareto points
Hypervolume
spacing
```

## 7. Main 100-instance mixed benchmark set

The primary benchmark dataset for broad computational analysis is the 100-instance mixed profile set. This dataset is intentionally different from the Pareto-template datasets. It is designed to cover the original range of problem sizes and structural difficulty levels: very small, small, medium, large, tight, sparse, low-availability, and hard instances.

The default mix is:

```text
vvs            5 instances
vs             5 instances
snap_s        15 instances
snap_m        15 instances
snap_l        10 instances
snap_tight    15 instances
snap_sparse   15 instances
snap_lowavail 10 instances
snap_hard     10 instances
```

This gives exactly 100 instances. The dataset can be generated with:

```bat
set PYTHONPATH=src
python scripts\generate_100_mixed_benchmark_instances.py --output instances_mixed_100 --seed 20260508
```

By default, the script writes JSON, TXT, MATLAB, and GAMS-compatible files but does not write XLSX files, because 100 full Excel workbooks can be large. Excel output can be enabled with:

```bat
set PYTHONPATH=src
python scripts\generate_100_mixed_benchmark_instances.py --output instances_mixed_100 --seed 20260508 --with-xlsx
```

The script writes the following summary files:

```text
design_100_mixed_benchmark.csv
manifest_100_mixed_benchmark.csv
mix_summary.json
```

The design file records the intended profile mix and nominal dimensions. The manifest records generated instance identifiers, seeds, folders, feasibility status, and complexity indicators.

The profile mix can be changed explicitly. For example:

```bat
set PYTHONPATH=src
python scripts\generate_100_mixed_benchmark_instances.py --output instances_mixed_100 --seed 20260508 --mix vvs=5,vs=5,snap_s=20,snap_m=20,snap_l=10,snap_tight=15,snap_sparse=10,snap_lowavail=10,snap_hard=5
```

The custom mix must sum to 100.

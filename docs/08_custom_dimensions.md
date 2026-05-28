# Custom-size instance generation

The generator can create an instance with user-specified main model dimensions:

- `I`: number of student groups
- `D`: number of courses
- `W`: number of distinct wards
- `H`: number of hospitals

The model time structure remains fixed according to the paper model:

```text
S = 2 shifts
T = 6 days per week
K = 16 weeks
```

## Command

Windows Command Prompt:

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-custom --output instances_custom --name custom_4_2_2_1 --groups 4 --courses 2 --wards 2 --hospitals 1 --instances 5 --seed 20260508
```

PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m snapbench.cli generate-custom --output instances_custom --name custom_4_2_2_1 --groups 4 --courses 2 --wards 2 --hospitals 1 --instances 5 --seed 20260508
```

## Optional distribution controls

The dimensions are explicit, but other generation rules must still be defined. By default, custom instances inherit distribution settings from `snap_s`.

You can change the base distribution:

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-custom --output instances_custom --name custom_medium_style --groups 12 --courses 6 --wards 8 --hospitals 3 --base-profile snap_m --instances 3 --seed 20260508
```

Useful optional arguments:

```text
--min-group-size
--max-group-size
--min-du-days
--max-du-days
--min-consecutive-days
--max-consecutive-days
--target-mea-density
--pw-probability
--senior-ratio
--allow-long-shift-probability
--nt-probability
```

To see all options:

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-custom --help
```

## Output

The custom command creates the same output structure as built-in profiles:

```text
instance.json
instance.xlsx
planted_solution.csv
metadata.json
txt/
M/
gams/
```

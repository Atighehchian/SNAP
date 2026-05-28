# Simple usage guide for non-Python users

This guide avoids `pip install -e .`. The package is run directly from the source folder using `PYTHONPATH=src`.

## Step 1: Install Visual Studio Code

Install Visual Studio Code, then open the project folder with:

```text
File > Open Folder
```

Choose the folder that contains:

```text
README.md
pyproject.toml
src
```

## Step 2: Install Python

Install Python 3.10 or newer from python.org.

On the first installer page, check:

```text
[✓] Add python.exe to PATH
```

Then click:

```text
Install Now
```

After installation, close and reopen Visual Studio Code.

## Step 3: Open the terminal

In Visual Studio Code:

```text
Terminal > New Terminal
```

Check Python:

```bat
python --version
```

If this does not work, try:

```bat
py --version
```

## Step 4: Generate instances without installing the package

In Windows Command Prompt or the VS Code terminal, run:

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-grid --output instances --instances-per-profile 2 --seed 20260508
```

If `python` is not recognized, run:

```bat
set PYTHONPATH=src
py -m snapbench.cli generate-grid --output instances --instances-per-profile 2 --seed 20260508
```

In PowerShell, use:

```powershell
$env:PYTHONPATH="src"
python -m snapbench.cli generate-grid --output instances --instances-per-profile 2 --seed 20260508
```

## Step 5: Use the generated files

Open the `instances` folder. Each generated problem has its own folder containing:

```text
instance.json
instance.xlsx
load_<instance_id>.m
planted_solution.csv
metadata.json
bundle_manifest.json
```

The JSON file is the official data file. The XLSX file is for checking the data in Excel. The `.m` file loads the generated data in MATLAB.

## Check the first instance

```bat
set PYTHONPATH=src
python -m snapbench.cli check --instance instances/snap_s_001/instance.json --schedule instances/snap_s_001/planted_solution.csv
```

The output should contain:

```text
feasible: true
```

## Optional flags

Skip XLSX output:

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-grid --output instances --instances-per-profile 2 --seed 20260508 --no-xlsx
```

Skip MATLAB loader output:

```bat
set PYTHONPATH=src
python -m snapbench.cli generate-grid --output instances --instances-per-profile 2 --seed 20260508 --no-matlab
```

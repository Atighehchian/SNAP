# MATLAB Loader Output

Starting from v1.3.0, every generated instance folder includes a MATLAB loader file.

Example folder:

```text
instances/snap_s_001/
  instance.json
  instance.xlsx
  load_snap_s_001.m
  planted_solution.csv
  metadata.json
  bundle_manifest.json
```

## MATLAB usage

```matlab
addpath("instances/snap_s_001")
snap = load_snap_s_001();
```

The loader returns a struct named `snap` with these important fields:

| Field | Meaning |
|---|---|
| `snap.instance` | Raw decoded `instance.json` |
| `snap.metadata` | Raw decoded `metadata.json` |
| `snap.schedule` | Table loaded from `planted_solution.csv` |
| `snap.sets` | Sets `I, D, W, H, S, T, K` |
| `snap.groups` | Table for set `I`, interpreted as student groups |
| `snap.courses` | Table for set `D` |
| `snap.wards` | Table for set `W` |
| `snap.hospitals` | Table for set `H` |
| `snap.params` | Raw model parameter structure |
| `snap.B`, `snap.Mea`, `snap.Cap`, etc. | Convenience tables for mathematical-model parameters |

## Why generate a per-instance loader?

The JSON file remains the canonical source, but a MATLAB user can load the instance without writing any JSON parsing code. The generated `.m` file is intentionally lightweight and reads files from its own folder, so it stays consistent with the JSON and CSV outputs.

## Disable MATLAB loader generation

```bash
set PYTHONPATH=src
python -m snapbench.cli generate-grid --output instances --instances-per-profile 2 --seed 20260508 --no-matlab
```

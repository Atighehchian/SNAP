# XLSX output

Starting from version 1.2.0, each generated SNAP instance is written in two complementary formats:

- `instance.json`: canonical machine-readable instance data
- `instance.xlsx`: Excel workbook for human inspection

The workbook is generated automatically by `python -m snapbench.cli generate` and `python -m snapbench.cli generate-grid`. No additional command is required.

## Workbook sheets

The Excel workbook includes sheets such as:

- `README`
- `Sets`
- `Groups_I`
- `Courses_D`
- `Wards_W`
- `Hospitals_H`
- `B_wh`
- `Course_Params`
- `Mea_dw`
- `Dur_weeks_dw`
- `Comm_id`
- `Com_idw`
- `Eb_dwh`
- `Cap_dwh`
- `Av_itk`
- `Avb_whtk`
- `ne_nee_dw`
- `nt_w`
- `Planted_Solution`
- `Metadata`

## Disabling XLSX generation

Use `--no-xlsx` if only JSON/CSV outputs are desired:

```bash
set PYTHONPATH=src
python -m snapbench.cli generate-grid --output instances --instances-per-profile 2 --seed 20260508 --no-xlsx
```

## Important note

The Excel workbook is intended for review and communication. The JSON file remains the authoritative representation for algorithms, reproducibility, and Git-based data processing.


Version 1.4.1 adds a `Semester_Plan` sheet that summarizes semester-level groups, courses, shared available days, and maximum O(d).

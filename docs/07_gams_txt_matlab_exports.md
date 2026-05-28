# GAMS, TXT, and MATLAB export structure

Version 1.6.0 adds solver-facing side exports to every generated instance.

## Excel workbook for GAMS/GDX

`instance.xlsx` keeps the human-readable review sheets and additionally includes GAMS-friendly long-form sheets:

- `GAMS_Index`: symbol name, type, domain, sheet name, range, rDim, cDim, and row count
- `set_I`, `set_D`, `set_W`, `set_H`, `set_S`, `set_T`, `set_K`
- `par_mem`, `par_semester`, `par_Du`, `par_O`, `par_PW`, `par_Dur`, `par_weeks`, `par_Cap`, `par_ne`, `par_nee`, `par_nt`
- `tab_B`, `tab_Mea`, `tab_Comm`, `tab_Com`, `tab_Eb`, `tab_Av`, `tab_Avb`

Each parameter/table sheet is written in long form: one domain column per index followed by a numeric `value` column. This is intended for GDXXRW import with `rDim=<domain column count>` and `cDim=0`.

## GAMS helper files

Each instance contains a `gams/` folder:

```text
gams/
  gdxxrw_symbols.txt
  import_to_gdx.gms
  declarations_and_load.inc
  README_gams.txt
```

From the `gams` folder, run:

```text
gams import_to_gdx.gms
```

This reads `../instance.xlsx` and creates `../instance.gdx`.

## TXT export

Each instance contains a `txt/` folder:

```text
txt/
  sets/
  parameters/
  tables/
  schedule/
```

All TXT files are UTF-8, tab-delimited, and contain a header row.

## MATLAB TXT loader

Each instance contains an `M/` folder:

```text
M/
  load_instance.m
  load_<instance_id>.m
  README_MATLAB.txt
```

MATLAB usage:

```matlab
addpath("instances/snap_s_001/M")
snap = load_instance();
```

The returned struct includes:

```matlab
snap.sets.I
snap.params.Cap
snap.tables.Eb
snap.schedule
```

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from .xlsx_export import write_instance_xlsx
from .matlab_export import matlab_safe_function_name, write_instance_matlab_loader
from .symbol_export import write_symbol_txt_files
from .matlab_txt_export import write_matlab_txt_loader
from .gams_export import write_gams_import_files


SCHEDULE_FIELDS = [
    "assignment_id",
    "group_id",
    "course_id",
    "ward_id",
    "hospital_id",
    "week",
    "start_week",
    "start_day",
    "O_consecutive_days",
    "segment_Dur_days",
    "segment_weeks",
    "days",
    "shift",
    "mem",
    "PW",
]


def write_json(path: str | Path, obj: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def read_json(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_schedule_csv(path: str | Path, schedule: List[Dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SCHEDULE_FIELDS)
        writer.writeheader()
        for row in schedule:
            out = dict(row)
            if isinstance(out.get("days"), list):
                out["days"] = ";".join(str(x) for x in out["days"])
            writer.writerow({k: out.get(k, "") for k in SCHEDULE_FIELDS})


def read_schedule_csv(path: str | Path) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if "days" in row and isinstance(row["days"], str):
                row["days"] = [int(x) for x in row["days"].split(";") if x]
            for key in ["week", "start_week", "start_day", "O_consecutive_days", "segment_Dur_days", "segment_weeks", "shift", "mem", "PW"]:
                if key in row and row[key] != "":
                    row[key] = int(row[key])
            rows.append(row)
    return rows


def save_instance_bundle(output_dir: str | Path, instance: Dict[str, Any], schedule: List[Dict[str, Any]], metadata: Dict[str, Any], *, write_xlsx: bool = True, write_matlab: bool = True, write_txt: bool = True, write_gams: bool = True) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "instance.json", instance)
    write_schedule_csv(output_dir / "planted_solution.csv", schedule)
    write_json(output_dir / "metadata.json", metadata)

    # Machine-readable side exports for GAMS/MATLAB workflows.
    if write_txt:
        write_symbol_txt_files(output_dir / "txt", instance, schedule, metadata)
    if write_gams:
        write_gams_import_files(output_dir / "gams", instance)

    matlab_loader = matlab_safe_function_name(instance["metadata"]["instance_id"]) + ".m"
    files = [
        "instance.json",
        "instance.xlsx",
        matlab_loader,
        "M/load_instance.m",
        f"M/{matlab_loader}",
        "txt/",
        "gams/",
        "import_to_gdx.gms",
        "gdxxrw_symbols.txt",
        "declarations_and_load.inc",
        "README_gams.txt",
        "planted_solution.csv",
        "metadata.json",
    ]
    if write_xlsx:
        write_instance_xlsx(output_dir / "instance.xlsx", instance, schedule, metadata)
    else:
        files.remove("instance.xlsx")
    if write_matlab:
        # Keep the legacy root loader for backward compatibility and add the requested M folder.
        write_instance_matlab_loader(output_dir / matlab_loader, instance, schedule, metadata)
        write_matlab_txt_loader(output_dir / "M", instance)
    else:
        files.remove(matlab_loader)
        files.remove("M/load_instance.m")
        files.remove(f"M/{matlab_loader}")
    if not write_txt:
        files.remove("txt/")
    if not write_gams:
        files.remove("gams/")
        files.remove("import_to_gdx.gms")
        files.remove("gdxxrw_symbols.txt")
        files.remove("declarations_and_load.inc")
        files.remove("README_gams.txt")
    write_json(output_dir / "bundle_manifest.json", {
        "files": files,
        "format_version": instance["metadata"]["format_version"],
        "matlab_loader": matlab_loader if write_matlab else None,
        "matlab_folder": "M" if write_matlab else None,
        "txt_folder": "txt",
        "gams_folder": "gams",
        "gams_root_import": "import_to_gdx.gms",
    })

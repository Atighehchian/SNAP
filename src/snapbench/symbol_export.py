from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple
import csv


@dataclass(frozen=True)
class SymbolTable:
    name: str
    kind: str  # set, parameter, table, schedule
    domain: Tuple[str, ...]
    headers: Tuple[str, ...]
    rows: Tuple[Tuple[Any, ...], ...]
    sheet_name: str
    txt_subdir: str


def _b(value: Any) -> int:
    return 1 if bool(value) else 0


def _course_map(instance: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {c["course_id"]: c for c in instance.get("courses", [])}


def _group_map(instance: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {g["group_id"]: g for g in instance.get("groups", [])}


def set_symbols(instance: Dict[str, Any]) -> List[SymbolTable]:
    sets = instance.get("sets", {})
    data = {
        "I": [(g["group_id"],) for g in instance.get("groups", [])],
        "D": [(c["course_id"],) for c in instance.get("courses", [])],
        "W": [(w["ward_id"],) for w in instance.get("wards", [])],
        "H": [(h["hospital_id"],) for h in instance.get("hospitals", [])],
        "S": [(s,) for s in range(1, int(sets.get("S", 0)) + 1)],
        "T": [(t,) for t in range(1, int(sets.get("T", 0)) + 1)],
        "K": [(k,) for k in range(1, int(sets.get("K", 0)) + 1)],
    }
    out: List[SymbolTable] = []
    for name in ["I", "D", "W", "H", "S", "T", "K"]:
        out.append(SymbolTable(
            name=name,
            kind="set",
            domain=(name,),
            headers=(name,),
            rows=tuple(data[name]),
            sheet_name=f"set_{name}",
            txt_subdir="sets",
        ))
    return out


def parameter_symbols(instance: Dict[str, Any]) -> List[SymbolTable]:
    params = instance.get("model_parameters", {})
    groups = _group_map(instance)
    tables: List[SymbolTable] = []

    def add(name: str, kind: str, domain: Sequence[str], headers: Sequence[str], rows: Iterable[Sequence[Any]], prefix: str = "par") -> None:
        tables.append(SymbolTable(
            name=name,
            kind=kind,
            domain=tuple(domain),
            headers=tuple(headers),
            rows=tuple(tuple(r) for r in rows),
            sheet_name=f"{prefix}_{name}",
            txt_subdir="tables" if kind == "table" else "parameters",
        ))

    add("mem", "parameter", ("I",), ("i", "value"), ((gid, int(g.get("mem", 0))) for gid, g in groups.items()))
    add("semester", "parameter", ("I",), ("i", "value"), ((gid, int(g.get("semester", 0))) for gid, g in groups.items()))

    add("Du", "parameter", ("D",), ("d", "value"), ((r["course_id"], int(r.get("Du_days", 0))) for r in params.get("Du", [])))
    add("O", "parameter", ("D",), ("d", "value"), ((r["course_id"], int(r.get("O_consecutive_days", 0))) for r in params.get("O", [])))
    add("PW", "parameter", ("D",), ("d", "value"), ((r["course_id"], int(r.get("PW", 0))) for r in params.get("PW", [])))
    add("Dur", "parameter", ("D", "W"), ("d", "w", "value"), ((r["course_id"], r["ward_id"], int(r.get("Dur_days", 0))) for r in params.get("Dur", [])))
    add("weeks", "parameter", ("D", "W"), ("d", "w", "value"), ((r["course_id"], r["ward_id"], int(r.get("weeks", 0))) for r in params.get("weeks", [])))
    add("Cap", "parameter", ("D", "W", "H"), ("d", "w", "h", "value"), ((r["course_id"], r["ward_id"], r["hospital_id"], int(r.get("capacity", 0))) for r in params.get("Cap", [])))
    add("ne", "parameter", ("D", "W"), ("d", "w", "value"), ((r["course_id"], r["ward_id"], _b(r.get("allowed", False))) for r in params.get("ne", [])))
    add("nee", "parameter", ("D", "W"), ("d", "w", "value"), ((r["course_id"], r["ward_id"], int(r.get("minimum_long_shifts", 0))) for r in params.get("nee", [])))
    add("nt", "parameter", ("W",), ("w", "value"), ((r["ward_id"], _b(r.get("interference_allowed", False))) for r in params.get("nt", [])))

    add("B", "table", ("W", "H"), ("w", "h", "value"), ((r["ward_id"], r["hospital_id"], _b(r.get("exists", False))) for r in params.get("B", [])), prefix="tab")
    add("Mea", "table", ("D", "W"), ("d", "w", "value"), ((r["course_id"], r["ward_id"], _b(r.get("defined", False))) for r in params.get("Mea", [])), prefix="tab")
    add("Comm", "table", ("I", "D"), ("i", "d", "value"), ((r["group_id"], r["course_id"], _b(r.get("required", False))) for r in params.get("Comm", [])), prefix="tab")
    add("Com", "table", ("I", "D", "W"), ("i", "d", "w", "value"), ((r["group_id"], r["course_id"], r["ward_id"], _b(r.get("required", False))) for r in params.get("Com", [])), prefix="tab")
    add("Eb", "table", ("D", "W", "H"), ("d", "w", "h", "value"), ((r["course_id"], r["ward_id"], r["hospital_id"], _b(r.get("eligible", False))) for r in params.get("Eb", [])), prefix="tab")
    add("Av", "table", ("I", "T", "K"), ("i", "t", "k", "value"), ((r["group_id"], int(r["day"]), int(r["week"]), _b(r.get("available", False))) for r in params.get("Av", [])), prefix="tab")
    add("Avb", "table", ("W", "H", "T", "K"), ("w", "h", "t", "k", "value"), ((r["ward_id"], r["hospital_id"], int(r["day"]), int(r["week"]), _b(r.get("available", False))) for r in params.get("Avb", [])), prefix="tab")
    return tables


def schedule_symbol(schedule: Sequence[Dict[str, Any]]) -> SymbolTable:
    headers = ("assignment_id", "i", "d", "w", "h", "week", "start_week", "start_day", "O", "Dur", "weeks", "days", "shift", "mem", "PW")
    rows = []
    for r in schedule:
        days = r.get("days")
        if isinstance(days, list):
            days = ";".join(str(x) for x in days)
        rows.append((
            r.get("assignment_id"), r.get("group_id"), r.get("course_id"), r.get("ward_id"), r.get("hospital_id"),
            r.get("week"), r.get("start_week"), r.get("start_day"), r.get("O_consecutive_days"),
            r.get("segment_Dur_days"), r.get("segment_weeks"), days, r.get("shift"), r.get("mem"), r.get("PW"),
        ))
    return SymbolTable("Planted_Solution", "schedule", tuple(), headers, tuple(rows), "Planted_Solution", "schedule")


def all_symbols(instance: Dict[str, Any], schedule: Sequence[Dict[str, Any]] | None = None) -> List[SymbolTable]:
    out = set_symbols(instance) + parameter_symbols(instance)
    if schedule is not None:
        out.append(schedule_symbol(schedule))
    return out


def write_symbol_txt_files(root: str | Path, instance: Dict[str, Any], schedule: Sequence[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for sub in ["sets", "parameters", "tables", "schedule"]:
        (root / sub).mkdir(parents=True, exist_ok=True)
    for sym in all_symbols(instance, schedule):
        path = root / sym.txt_subdir / f"{sym.name}.txt"
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerow(sym.headers)
            writer.writerows(sym.rows)
    readme = root / "README.txt"
    readme.write_text(
        "SNAP instance text export\n"
        "Encoding: UTF-8\n"
        "Delimiter: TAB\n"
        "Each file has a header row.\n"
        "Sets are in txt/sets, scalar/vector/multidimensional parameters in txt/parameters, binary tables in txt/tables.\n"
        "These TXT files mirror instance.json and are intended for GAMS/MATLAB inspection or custom import scripts.\n",
        encoding="utf-8",
    )


def gams_symbol_ranges(instance: Dict[str, Any]) -> List[Dict[str, Any]]:
    symbols = set_symbols(instance) + parameter_symbols(instance)
    rows: List[Dict[str, Any]] = []
    for sym in symbols:
        if not sym.rows:
            continue
        col_count = len(sym.headers)
        end_col = _excel_col(col_count)
        end_row = len(sym.rows) + 1
        rng = f"{sym.sheet_name}!A2:{end_col}{end_row}"
        rows.append({
            "name": sym.name,
            "kind": sym.kind,
            "domain": ",".join(sym.domain),
            "sheet_name": sym.sheet_name,
            "range": rng,
            "rdim": len(sym.domain) if sym.kind != "set" else 1,
            "cdim": 0,
            "row_count": len(sym.rows),
        })
    return rows


def _excel_col(n: int) -> str:
    letters = ""
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters

#!/usr/bin/env python3
r"""
Generate a 100-instance mixed SNAP benchmark set from the main built-in profiles.

This script is intended for the general benchmark dataset used in the paper,
not only for Pareto-template experiments. It combines very small, small,
medium, large, sparse, tight, low-availability, and hard profiles.

Run from the repository root with PYTHONPATH=src.

Windows CMD:
    set PYTHONPATH=src
    python scripts\generate_100_mixed_benchmark_instances.py --output instances_mixed_100 --seed 20260508

PowerShell:
    $env:PYTHONPATH="src"
    python scripts/generate_100_mixed_benchmark_instances.py --output instances_mixed_100 --seed 20260508

By default, XLSX files are not written because 100 full workbooks can be large.
Use --with-xlsx when human-readable Excel files are required.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

from snapbench.generator import generate_instance
from snapbench.io import save_instance_bundle, write_json
from snapbench.profiles import get_profile, list_profiles


DEFAULT_PROFILE_MIX: "OrderedDict[str, int]" = OrderedDict([
    ("vvs", 5),
    ("vs", 5),
    ("snap_s", 15),
    ("snap_m", 15),
    ("snap_l", 10),
    ("snap_tight", 15),
    ("snap_sparse", 15),
    ("snap_lowavail", 10),
    ("snap_hard", 10),
])

PROFILE_FAMILY_LABELS = {
    "vvs": "very-very-small exact test",
    "vs": "very-small exact test",
    "snap_s": "small MIP-oriented benchmark",
    "snap_m": "medium benchmark",
    "snap_l": "large metaheuristic-oriented benchmark",
    "snap_tight": "capacity-tight benchmark",
    "snap_sparse": "eligibility-sparse benchmark",
    "snap_lowavail": "low-availability benchmark",
    "snap_hard": "hard mixed benchmark",
}


def parse_mix(text: str | None) -> "OrderedDict[str, int]":
    """Parse profile mix like 'vvs=5,vs=5,snap_s=15'."""
    if not text:
        return OrderedDict(DEFAULT_PROFILE_MIX)

    out: "OrderedDict[str, int]" = OrderedDict()
    valid_profiles = set(list_profiles())
    for raw_part in text.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Invalid --mix item {part!r}; expected profile=count")
        name, count_text = [x.strip() for x in part.split("=", 1)]
        if name not in valid_profiles:
            raise ValueError(f"Unknown profile {name!r}; valid profiles: {', '.join(sorted(valid_profiles))}")
        count = int(count_text)
        if count < 0:
            raise ValueError("Profile counts must be non-negative")
        if count:
            out[name] = count

    if not out:
        raise ValueError("Profile mix is empty")
    return out


def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def build_design_rows(profile_mix: Dict[str, int], base_seed: int) -> List[dict]:
    rows: List[dict] = []
    global_no = 1
    for profile_name, count in profile_mix.items():
        profile = get_profile(profile_name)
        for local_index in range(1, count + 1):
            rows.append({
                "global_no": global_no,
                "profile": profile_name,
                "family_label": PROFILE_FAMILY_LABELS.get(profile_name, profile.difficulty_hint),
                "local_index": local_index,
                "groups_I": profile.groups,
                "courses_D": profile.courses,
                "wards_W": profile.wards,
                "hospitals_H": profile.hospitals,
                "I_times_D_times_W_times_H": profile.groups * profile.courses * profile.wards * profile.hospitals,
                "course_load_per_group": profile.course_load_per_group,
                "target_mea_density": profile.target_mea_density,
                "pw_probability": profile.pw_probability,
                "difficulty_hint": profile.difficulty_hint,
                "base_seed": base_seed,
            })
            global_no += 1
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a 100-instance mixed benchmark set from the main SNAP profiles."
    )
    parser.add_argument("--output", default="instances_mixed_100", help="Output directory")
    parser.add_argument("--seed", type=int, default=20260508, help="Base seed for reproducibility")
    parser.add_argument(
        "--mix",
        default=None,
        help=(
            "Optional comma-separated profile mix, e.g. "
            "vvs=5,vs=5,snap_s=15,snap_m=15,snap_l=10,snap_tight=15,snap_sparse=15,snap_lowavail=10,snap_hard=10"
        ),
    )
    parser.add_argument("--series-name", default="snap-mixed-benchmark-v1.9.2")
    parser.add_argument("--with-xlsx", action="store_true", help="Write instance.xlsx for each instance")
    parser.add_argument("--no-matlab", action="store_true", help="Do not write MATLAB loaders")
    parser.add_argument("--no-txt", action="store_true", help="Do not write TXT symbol export")
    parser.add_argument("--no-gams", action="store_true", help="Do not write GAMS helper files")
    parser.add_argument("--dry-run", action="store_true", help="Only write the design table; do not generate instances")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    profile_mix = parse_mix(args.mix)
    total = sum(profile_mix.values())
    if total != 100:
        raise ValueError(f"This script is intended to generate exactly 100 instances; mix sums to {total}")

    design_rows = build_design_rows(profile_mix, args.seed)
    design_fields = [
        "global_no", "profile", "family_label", "local_index",
        "groups_I", "courses_D", "wards_W", "hospitals_H",
        "I_times_D_times_W_times_H", "course_load_per_group",
        "target_mea_density", "pw_probability", "difficulty_hint", "base_seed",
    ]
    design_csv = output / "design_100_mixed_benchmark.csv"
    write_csv(design_csv, design_rows, design_fields)

    write_json(output / "mix_summary.json", {
        "total_instances": total,
        "base_seed": args.seed,
        "series_name": args.series_name,
        "profile_mix": profile_mix,
        "note": "General mixed benchmark set: vvs/vs/small/medium/large/tight/sparse/low-availability/hard.",
        "xlsx_written": bool(args.with_xlsx),
    })

    print(f"Design written to: {design_csv}")
    print(f"Profile mix: {dict(profile_mix)}")

    if args.dry_run:
        print("Dry run only. No instances generated.")
        return 0

    manifest: List[dict] = []
    failure_rows: List[dict] = []

    global_no = 1
    for profile_name, count in profile_mix.items():
        for local_index in range(1, count + 1):
            print(f"[{global_no:03d}/100] generating profile={profile_name}, local_index={local_index}")
            try:
                generated = generate_instance(
                    profile_name,
                    local_index,
                    args.seed,
                    series_name=args.series_name,
                )
                folder = output / generated.metadata["instance_id"]
                save_instance_bundle(
                    folder,
                    generated.instance,
                    generated.planted_schedule,
                    generated.metadata,
                    write_xlsx=bool(args.with_xlsx),
                    write_matlab=not args.no_matlab,
                    write_txt=not args.no_txt,
                    write_gams=not args.no_gams,
                )
                complexity = generated.metadata.get("complexity", {})
                feasibility = generated.metadata.get("planted_solution_feasibility", {})
                manifest.append({
                    "global_no": global_no,
                    "instance_id": generated.metadata.get("instance_id"),
                    "profile": profile_name,
                    "family_label": PROFILE_FAMILY_LABELS.get(profile_name, ""),
                    "local_index": local_index,
                    "instance_seed": generated.metadata.get("instance_seed"),
                    "folder": str(folder.relative_to(output)),
                    "feasible": feasibility.get("feasible"),
                    "violation_count": feasibility.get("violation_count"),
                    "groups_I": complexity.get("groups_I"),
                    "courses_D": complexity.get("courses_D"),
                    "wards_W": complexity.get("wards_W"),
                    "hospitals_H": complexity.get("hospitals_H"),
                    "shifts_S": complexity.get("shifts_S"),
                    "days_T": complexity.get("days_T"),
                    "weeks_K": complexity.get("weeks_K"),
                    "required_group_course_pairs_Comm": complexity.get("required_group_course_pairs_Comm"),
                    "required_group_course_ward_triples_Com": complexity.get("required_group_course_ward_triples_Com"),
                    "training_day_demand": complexity.get("training_day_demand"),
                    "member_day_demand": complexity.get("member_day_demand"),
                    "load_ratio": complexity.get("load_ratio"),
                    "B_density": complexity.get("B_density"),
                    "Mea_density": complexity.get("Mea_density"),
                    "Comm_density": complexity.get("Comm_density"),
                    "Com_density": complexity.get("Com_density"),
                    "Av_ratio": complexity.get("Av_ratio"),
                    "Avb_ratio": complexity.get("Avb_ratio"),
                    "difficulty_score": complexity.get("difficulty_score"),
                    "difficulty_label": complexity.get("difficulty_label"),
                })
            except Exception as exc:  # Keep batch generation diagnosable.
                failure_rows.append({
                    "global_no": global_no,
                    "profile": profile_name,
                    "local_index": local_index,
                    "error": repr(exc),
                })
                print(f"  FAILED: {exc!r}")
            global_no += 1

    manifest_fields = [
        "global_no", "instance_id", "profile", "family_label", "local_index",
        "instance_seed", "folder", "feasible", "violation_count",
        "groups_I", "courses_D", "wards_W", "hospitals_H", "shifts_S", "days_T", "weeks_K",
        "required_group_course_pairs_Comm", "required_group_course_ward_triples_Com",
        "training_day_demand", "member_day_demand", "load_ratio",
        "B_density", "Mea_density", "Comm_density", "Com_density", "Av_ratio", "Avb_ratio",
        "difficulty_score", "difficulty_label",
    ]
    write_csv(output / "manifest_100_mixed_benchmark.csv", manifest, manifest_fields)
    if failure_rows:
        write_csv(output / "failed_generation_log.csv", failure_rows, ["global_no", "profile", "local_index", "error"])

    print(f"Generated: {len(manifest)} / 100")
    if failure_rows:
        print(f"Failures: {len(failure_rows)}; see failed_generation_log.csv")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

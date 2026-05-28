#!/usr/bin/env python3
"""
Generate 100 light Pareto-template SNAP instances.

Place this file in the root folder of the generator package, next to `src/`.
It imports the package directly, so run it with `PYTHONPATH=src`.

Recommended command, Windows CMD:

    set PYTHONPATH=src
    python generate_100_pareto_template_light_instances.py --output instances_template_light_100 --seed 20260508 --no-xlsx

This light set is designed for exact GAMS/AUGMECON experiments, so all instances
use small dimensions:
    I = 3..5, D = 2..3, W = 3..4, H = 1..2
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List

from snapbench.io import save_instance_bundle
from snapbench.pareto_template_light import generate_pareto_template_light_instance


@dataclass(frozen=True)
class LightSize:
    groups: int
    courses: int
    wards: int
    hospitals: int

    @property
    def code(self) -> str:
        return f"L_I{self.groups}_D{self.courses}_W{self.wards}_H{self.hospitals}"


BASE_SIZES: List[LightSize] = [
    LightSize(i, d, w, h)
    for h in (1, 2)
    for d in (2, 3)
    for w in (3, 4)
    for i in (3, 4, 5)
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 100 light Pareto-template instances.")
    parser.add_argument("--output", default="instances_template_light_100")
    parser.add_argument("--seed", type=int, default=20260508)
    parser.add_argument("--no-xlsx", action="store_true")
    parser.add_argument("--no-matlab", action="store_true")
    parser.add_argument("--no-txt", action="store_true")
    parser.add_argument("--no-gams", action="store_true")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    manifest = []
    failures = []
    for idx in range(1, 101):
        size = BASE_SIZES[(idx - 1) % len(BASE_SIZES)]
        run_seed = args.seed + idx * 1009
        name = f"LT{idx:03d}_{size.code}"
        print(f"[{idx:03d}/100] I={size.groups}, D={size.courses}, W={size.wards}, H={size.hospitals}, seed={run_seed}")
        try:
            generated = generate_pareto_template_light_instance(
                name=name,
                groups_n=size.groups,
                courses_n=size.courses,
                wards_n=size.wards,
                hospitals_n=size.hospitals,
                instance_index=1,
                base_seed=run_seed,
            )
            folder = output / generated.metadata["instance_id"]
            save_instance_bundle(
                folder,
                generated.instance,
                generated.planted_schedule,
                generated.metadata,
                write_xlsx=not args.no_xlsx,
                write_matlab=not args.no_matlab,
                write_txt=not args.no_txt,
                write_gams=not args.no_gams,
            )
            potential = generated.metadata.get("pareto_potential", {})
            manifest.append({
                "index": idx,
                "instance_id": generated.metadata["instance_id"],
                "instance_folder": folder.name,
                "groups": size.groups,
                "courses": size.courses,
                "wards": size.wards,
                "hospitals": size.hospitals,
                "seed": generated.metadata["instance_seed"],
                "pareto_potential_accepted": potential.get("accepted"),
                "active_IDWH_estimate": potential.get("active_IDWH_estimate"),
                "latest_completion_time": potential.get("screen_summary", {}).get("latest_completion_time"),
            })
        except Exception as exc:
            failures.append({
                "index": idx,
                "groups": size.groups,
                "courses": size.courses,
                "wards": size.wards,
                "hospitals": size.hospitals,
                "seed": run_seed,
                "error": str(exc)[-800:],
            })
            print(f"  failed: {str(exc)[-220:]}")

    with (output / "manifest_100_pareto_template_light.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["index", "instance_id", "instance_folder", "groups", "courses", "wards", "hospitals", "seed", "pareto_potential_accepted", "active_IDWH_estimate", "latest_completion_time"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest)

    if failures:
        with (output / "failed_generation_log.csv").open("w", newline="", encoding="utf-8") as f:
            fieldnames = ["index", "groups", "courses", "wards", "hospitals", "seed", "error"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(failures)

    print(f"Generated: {len(manifest)} / 100")
    if failures:
        print(f"Failures: {len(failures)}; see failed_generation_log.csv")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

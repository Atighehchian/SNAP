#!/usr/bin/env python3
"""
Generate 100 ultra-light Pareto-template SNAP instances.

Place this file in the root folder of the SNAP generator package, next to src/.
This version imports the generator directly instead of launching 100 subprocesses.

Default size mix:
    I=3,H=1 : 25 instances
    I=3,H=2 : 35 instances
    I=4,H=1 : 15 instances
    I=4,H=2 : 25 instances
Total: 100 instances

Fixed by design:
    D=2, W=3, S=2, T=6, K=16

Usage, Windows CMD:
    set PYTHONPATH=src
    python generate_100_pareto_template_ultralight_instances.py --output instances_ultralight_100 --seed 20260508 --no-xlsx
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from snapbench.io import save_instance_bundle
from snapbench.pareto_template_ultralight import generate_pareto_template_ultralight_instance


@dataclass(frozen=True)
class UltraSpec:
    number: int
    groups: int
    hospitals: int

    @property
    def name(self) -> str:
        return f"UL{self.number:03d}_I{self.groups}_D2_W3_H{self.hospitals}"


def build_specs() -> list[UltraSpec]:
    specs: list[UltraSpec] = []
    n = 1
    for groups, hospitals, count in [(3, 1, 25), (3, 2, 35), (4, 1, 15), (4, 2, 25)]:
        for _ in range(count):
            specs.append(UltraSpec(n, groups, hospitals))
            n += 1
    return specs


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 100 ultra-light Pareto-template SNAP instances.")
    parser.add_argument("--output", default="instances_ultralight_100")
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

    for spec in build_specs():
        print(f"[{spec.number:03d}/100] {spec.name}")
        try:
            generated = generate_pareto_template_ultralight_instance(
                name=spec.name,
                groups_n=spec.groups,
                hospitals_n=spec.hospitals,
                instance_index=1,
                base_seed=args.seed + spec.number * 1009,
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
            manifest.append({
                "number": spec.number,
                "name": spec.name,
                "instance_folder": folder.name,
                "groups_I": spec.groups,
                "courses_D": 2,
                "wards_W": 3,
                "hospitals_H": spec.hospitals,
                "seed": generated.metadata["instance_seed"],
                "active_IDWH_estimate": generated.metadata.get("pareto_potential", {}).get("active_IDWH_estimate"),
                "pareto_potential_accepted": generated.metadata.get("pareto_potential", {}).get("accepted"),
                "status": "generated",
            })
        except Exception as exc:
            failures.append({"number": spec.number, "name": spec.name, "groups_I": spec.groups, "hospitals_H": spec.hospitals, "error": str(exc)})
            print("  failed:", exc)

    with (output / "manifest_ultralight_100.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["number", "name", "instance_folder", "groups_I", "courses_D", "wards_W", "hospitals_H", "seed", "active_IDWH_estimate", "pareto_potential_accepted", "status"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest)

    if failures:
        with (output / "failed_ultralight_100.csv").open("w", newline="", encoding="utf-8") as f:
            fieldnames = ["number", "name", "groups_I", "hospitals_H", "error"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(failures)

    print("Done.")
    print("Generated:", len(manifest))
    print("Failed:", len(failures))
    return 0 if len(manifest) == 100 else 2


if __name__ == "__main__":
    raise SystemExit(main())

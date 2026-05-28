#!/usr/bin/env python3
"""
Generate 100 template-based Pareto-friendly SNAP instances.

Requires generator package v1.8.0 or later. Place this file next to the src/ folder.

Windows CMD:
    set PYTHONPATH=src
    python generate_100_pareto_template_instances.py --output instances_template_100 --seed 20260508

By default XLSX is not generated for speed. Add --with-xlsx if needed.
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

from snapbench.io import save_instance_bundle
from snapbench.pareto_template import generate_pareto_template_instance


def feasible_size_pool(seed: int):
    rng = random.Random(seed)
    pool = []
    for h in [1, 2, 3]:
        for i in range(3, 9):
            for d in range(2, 6):
                for w in range(3, 7):
                    # Conservative structural filters, based on quick feasibility screening.
                    if h == 1:
                        if i * d > 18:
                            continue
                        if w < 4 and d >= 4:
                            continue
                    if h == 2:
                        if i * d > 30 and w <= 3:
                            continue
                    pool.append((i, d, w, h))
    rng.shuffle(pool)
    pool.sort(key=lambda x: (x[3], x[0] * x[1] * x[2] * x[3], x[0], x[1], x[2]))
    return pool


def candidate_sizes_by_h(seed: int):
    pool = feasible_size_pool(seed)
    return {h: [x for x in pool if x[3] == h] for h in [1, 2, 3]}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="instances_template_100")
    ap.add_argument("--seed", type=int, default=20260508)
    ap.add_argument("--with-xlsx", action="store_true")
    ap.add_argument("--no-matlab", action="store_true")
    ap.add_argument("--no-txt", action="store_true")
    ap.add_argument("--no-gams", action="store_true")
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    targets = {1: 45, 2: 35, 3: 20}
    pools = candidate_sizes_by_h(args.seed)

    manifest = []
    failures = []
    n = 1
    for h, target in targets.items():
        success_h = 0
        for (i, d, w, hval) in pools[h]:
            if success_h >= target:
                break
            name = f"T{n:03d}_I{i}_D{d}_W{w}_H{hval}"
            seed = args.seed + n * 1009
            print(f"[{n:03d}/100] I={i}, D={d}, W={w}, H={hval}")
            try:
                generated = generate_pareto_template_instance(
                    name=name,
                    groups_n=i,
                    courses_n=d,
                    wards_n=w,
                    hospitals_n=hval,
                    instance_index=1,
                    base_seed=seed,
                    max_attempts=80,
                )
                folder = out / generated.metadata["instance_id"]
                save_instance_bundle(
                    folder,
                    generated.instance,
                    generated.planted_schedule,
                    generated.metadata,
                    write_xlsx=args.with_xlsx,
                    write_matlab=not args.no_matlab,
                    write_txt=not args.no_txt,
                    write_gams=not args.no_gams,
                )
                pot = generated.metadata.get("pareto_potential", {})
                manifest.append({
                    "n": n,
                    "instance_folder": folder.name,
                    "I": i,
                    "D": d,
                    "W": w,
                    "H": hval,
                    "seed": seed,
                    "pareto_potential_accepted": pot.get("accepted", ""),
                    "pw1_courses": pot.get("pw1_courses", ""),
                    "pw1_multi_option_courses": pot.get("pw1_multi_option_courses", ""),
                    "latest_completion_time": pot.get("screen_summary", {}).get("latest_completion_time", ""),
                    "status": "generated",
                })
                success_h += 1
                n += 1
            except Exception as exc:
                failures.append({"n": n, "I": i, "D": d, "W": w, "H": hval, "seed": seed, "error": str(exc)})
                print(f"  skipped: {exc}")
                continue
        if success_h < target:
            raise RuntimeError(f"Could not generate target for H={h}: {success_h}/{target}")

    with (out / "manifest_100_pareto_template.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["n", "instance_folder", "I", "D", "W", "H", "seed", "pareto_potential_accepted", "pw1_courses", "pw1_multi_option_courses", "latest_completion_time", "status"]
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader(); wr.writerows(manifest)
    if failures:
        with (out / "failed_100_pareto_template.csv").open("w", newline="", encoding="utf-8") as f:
            fields = ["n", "I", "D", "W", "H", "seed", "error"]
            wr = csv.DictWriter(f, fieldnames=fields)
            wr.writeheader(); wr.writerows(failures)
    print(f"Generated: {len(manifest)} / 100")
    return 0 if len(manifest) == 100 else 2


if __name__ == "__main__":
    raise SystemExit(main())

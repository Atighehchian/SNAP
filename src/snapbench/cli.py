from __future__ import annotations

import argparse
import json
from pathlib import Path

from .complexity import compute_complexity
from .feasibility import check_schedule
from .generator import generate_instance, generate_instance_from_profile
from .pareto_template import generate_pareto_template_instance
from .pareto_template_light import generate_pareto_template_light_instance
from .pareto_template_ultralight import generate_pareto_template_ultralight_instance
from .io import read_json, read_schedule_csv, save_instance_bundle, write_json
from .profiles import DEFAULT_GRID_PROFILES, build_custom_profile, list_profiles


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_profiles(args: argparse.Namespace) -> None:
    _print_json({"profiles": list_profiles(), "default_grid_profiles": DEFAULT_GRID_PROFILES})


def cmd_generate(args: argparse.Namespace) -> None:
    output = Path(args.output)
    manifest = []
    for i in range(args.start_index, args.start_index + args.instances):
        generated = generate_instance(args.profile, i, args.seed, series_name=args.series_name)
        folder = output / generated.metadata["instance_id"]
        save_instance_bundle(folder, generated.instance, generated.planted_schedule, generated.metadata, write_xlsx=not args.no_xlsx, write_matlab=not args.no_matlab, write_txt=not args.no_txt, write_gams=not args.no_gams)
        manifest.append({
            "instance_id": generated.metadata["instance_id"],
            "profile": args.profile,
            "seed": generated.metadata["instance_seed"],
            "folder": str(folder),
            **generated.metadata["complexity"],
        })
        print(f"generated {folder}")
    write_json(output / f"manifest_{args.profile}.json", manifest)


def cmd_generate_custom(args: argparse.Namespace) -> None:
    output = Path(args.output)
    profile = build_custom_profile(
        name=args.name,
        groups=args.groups,
        courses=args.courses,
        wards=args.wards,
        hospitals=args.hospitals,
        base_profile=args.base_profile,
        difficulty_hint=args.difficulty_hint,
        min_group_size=args.min_group_size,
        max_group_size=args.max_group_size,
        min_du_days=args.min_du_days,
        max_du_days=args.max_du_days,
        min_consecutive_days=args.min_consecutive_days,
        max_consecutive_days=args.max_consecutive_days,
        target_mea_density=args.target_mea_density,
        pw_probability=args.pw_probability,
        senior_ratio=args.senior_ratio,
        allow_long_shift_probability=args.allow_long_shift_probability,
        nt_probability=args.nt_probability,
        tradeoff_mode=args.tradeoff_mode,
    )
    manifest = []
    for i in range(args.start_index, args.start_index + args.instances):
        generated = generate_instance_from_profile(profile, i, args.seed, series_name=args.series_name)
        folder = output / generated.metadata["instance_id"]
        save_instance_bundle(folder, generated.instance, generated.planted_schedule, generated.metadata, write_xlsx=not args.no_xlsx, write_matlab=not args.no_matlab, write_txt=not args.no_txt, write_gams=not args.no_gams)
        manifest.append({
            "instance_id": generated.metadata["instance_id"],
            "profile": profile.name,
            "seed": generated.metadata["instance_seed"],
            "folder": str(folder),
            **generated.metadata["complexity"],
        })
        print(f"generated {folder}")
    write_json(output / f"manifest_{profile.name}.json", manifest)


def cmd_generate_pareto_template(args: argparse.Namespace) -> None:
    output = Path(args.output)
    manifest = []
    for i in range(args.start_index, args.start_index + args.instances):
        generated = generate_pareto_template_instance(
            name=args.name,
            groups_n=args.groups,
            courses_n=args.courses,
            wards_n=args.wards,
            hospitals_n=args.hospitals,
            instance_index=i,
            base_seed=args.seed,
            series_name=args.series_name,
            max_attempts=args.max_attempts,
        )
        folder = output / generated.metadata["instance_id"]
        save_instance_bundle(folder, generated.instance, generated.planted_schedule, generated.metadata, write_xlsx=not args.no_xlsx, write_matlab=not args.no_matlab, write_txt=not args.no_txt, write_gams=not args.no_gams)
        manifest.append({
            "instance_id": generated.metadata["instance_id"],
            "profile": args.name,
            "seed": generated.metadata["instance_seed"],
            "folder": str(folder),
            "pareto_potential_accepted": generated.metadata.get("pareto_potential", {}).get("accepted"),
            **generated.metadata["complexity"],
        })
        print(f"generated {folder}")
    write_json(output / f"manifest_{args.name}.json", manifest)



def cmd_generate_pareto_template_light(args: argparse.Namespace) -> None:
    output = Path(args.output)
    manifest = []
    for i in range(args.start_index, args.start_index + args.instances):
        generated = generate_pareto_template_light_instance(
            name=args.name,
            groups_n=args.groups,
            courses_n=args.courses,
            wards_n=args.wards,
            hospitals_n=args.hospitals,
            instance_index=i,
            base_seed=args.seed,
            series_name=args.series_name,
            max_attempts=args.max_attempts,
        )
        folder = output / generated.metadata["instance_id"]
        save_instance_bundle(folder, generated.instance, generated.planted_schedule, generated.metadata, write_xlsx=not args.no_xlsx, write_matlab=not args.no_matlab, write_txt=not args.no_txt, write_gams=not args.no_gams)
        manifest.append({
            "instance_id": generated.metadata["instance_id"],
            "profile": args.name,
            "seed": generated.metadata["instance_seed"],
            "folder": str(folder),
            "pareto_potential_accepted": generated.metadata.get("pareto_potential", {}).get("accepted"),
            "active_IDWH_estimate": generated.metadata.get("pareto_potential", {}).get("active_IDWH_estimate"),
            **generated.metadata["complexity"],
        })
        print(f"generated {folder}")
    write_json(output / f"manifest_{args.name}.json", manifest)


def cmd_generate_pareto_template_ultralight(args: argparse.Namespace) -> None:
    output = Path(args.output)
    manifest = []
    for i in range(args.start_index, args.start_index + args.instances):
        generated = generate_pareto_template_ultralight_instance(
            name=args.name,
            groups_n=args.groups,
            hospitals_n=args.hospitals,
            instance_index=i,
            base_seed=args.seed,
            series_name=args.series_name,
            max_attempts=args.max_attempts,
        )
        folder = output / generated.metadata["instance_id"]
        save_instance_bundle(folder, generated.instance, generated.planted_schedule, generated.metadata, write_xlsx=not args.no_xlsx, write_matlab=not args.no_matlab, write_txt=not args.no_txt, write_gams=not args.no_gams)
        manifest.append({
            "instance_id": generated.metadata["instance_id"],
            "profile": args.name,
            "seed": generated.metadata["instance_seed"],
            "folder": str(folder),
            "pareto_potential_accepted": generated.metadata.get("pareto_potential", {}).get("accepted"),
            "active_IDWH_estimate": generated.metadata.get("pareto_potential", {}).get("active_IDWH_estimate"),
            "eligible_DWH": generated.metadata.get("pareto_potential", {}).get("eligible_DWH"),
            **generated.metadata["complexity"],
        })
        print(f"generated {folder}")
    write_json(output / f"manifest_{args.name}.json", manifest)


def cmd_generate_grid(args: argparse.Namespace) -> None:
    output = Path(args.output)
    profiles = args.profiles or DEFAULT_GRID_PROFILES
    full_manifest = []
    for profile in profiles:
        for i in range(1, args.instances_per_profile + 1):
            generated = generate_instance(profile, i, args.seed, series_name=args.series_name)
            folder = output / generated.metadata["instance_id"]
            save_instance_bundle(folder, generated.instance, generated.planted_schedule, generated.metadata, write_xlsx=not args.no_xlsx, write_matlab=not args.no_matlab, write_txt=not args.no_txt, write_gams=not args.no_gams)
            row = {
                "instance_id": generated.metadata["instance_id"],
                "profile": profile,
                "seed": generated.metadata["instance_seed"],
                "folder": str(folder),
                **generated.metadata["complexity"],
            }
            full_manifest.append(row)
            print(f"generated {folder}")
    write_json(output / "manifest_all.json", full_manifest)


def cmd_check(args: argparse.Namespace) -> None:
    instance = read_json(args.instance)
    schedule = read_schedule_csv(args.schedule)
    _print_json(check_schedule(instance, schedule))


def cmd_describe(args: argparse.Namespace) -> None:
    instance = read_json(args.instance)
    _print_json(compute_complexity(instance))



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SNAP MIP-aligned, Taillard-inspired instance generator"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("profiles", help="List available benchmark profiles")
    p.set_defaults(func=cmd_profiles)

    p = sub.add_parser("generate", help="Generate instances for one profile")
    p.add_argument("--output", required=True, help="Output directory")
    p.add_argument("--profile", required=True, choices=list_profiles(), help="Benchmark profile")
    p.add_argument("--instances", type=int, default=1, help="Number of instances to generate")
    p.add_argument("--start-index", type=int, default=1, help="Starting instance index")
    p.add_argument("--seed", type=int, default=20260508, help="Base seed for reproducibility")
    p.add_argument("--series-name", default="snap-math-model-taillard-inspired-v1.8.1")
    p.add_argument("--no-xlsx", action="store_true", help="Do not write instance.xlsx files")
    p.add_argument("--no-matlab", action="store_true", help="Do not write per-instance MATLAB loader .m files")
    p.add_argument("--no-txt", action="store_true", help="Do not write txt/ symbol export")
    p.add_argument("--no-gams", action="store_true", help="Do not write GAMS helper files")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("generate-custom", help="Generate instances from user-specified dimensions |I|, |D|, |W|, |H|")
    p.add_argument("--output", required=True, help="Output directory")
    p.add_argument("--name", default="custom", help="Profile/instance prefix, e.g. custom_3_1_2_1")
    p.add_argument("--groups", type=int, required=True, help="Number of student groups |I|")
    p.add_argument("--courses", type=int, required=True, help="Number of courses |D|")
    p.add_argument("--wards", type=int, required=True, help="Number of distinct wards |W|")
    p.add_argument("--hospitals", type=int, required=True, help="Number of hospitals |H|")
    p.add_argument("--instances", type=int, default=1, help="Number of instances to generate")
    p.add_argument("--start-index", type=int, default=1, help="Starting instance index")
    p.add_argument("--seed", type=int, default=20260508, help="Base seed for reproducibility")
    p.add_argument("--base-profile", choices=list_profiles(), default="snap_s", help="Profile whose distribution settings are inherited")
    p.add_argument("--series-name", default="snap-math-model-taillard-inspired-v1.8.1")
    p.add_argument("--difficulty-hint", default=None, help="Optional label stored in metadata")
    p.add_argument("--min-group-size", type=int, default=None)
    p.add_argument("--max-group-size", type=int, default=None)
    p.add_argument("--min-du-days", type=int, default=None)
    p.add_argument("--max-du-days", type=int, default=None)
    p.add_argument("--min-consecutive-days", type=int, default=None)
    p.add_argument("--max-consecutive-days", type=int, default=None)
    p.add_argument("--target-mea-density", type=float, default=None)
    p.add_argument("--pw-probability", type=float, default=None)
    p.add_argument("--senior-ratio", type=float, default=None)
    p.add_argument("--allow-long-shift-probability", type=float, default=None)
    p.add_argument("--nt-probability", type=float, default=None)
    p.add_argument("--tradeoff-mode", choices=["standard", "pareto"], default="standard", help="Use 'pareto' to create data-level conflict between completion span and ward-use choices")
    p.add_argument("--pareto-friendly", action="store_const", const="pareto", dest="tradeoff_mode", help="Shortcut for --tradeoff-mode pareto")
    p.add_argument("--no-xlsx", action="store_true", help="Do not write instance.xlsx files")
    p.add_argument("--no-matlab", action="store_true", help="Do not write per-instance MATLAB loader .m files")
    p.add_argument("--no-txt", action="store_true", help="Do not write txt/ symbol export")
    p.add_argument("--no-gams", action="store_true", help="Do not write GAMS helper files")
    p.set_defaults(func=cmd_generate_custom)


    p = sub.add_parser("generate-pareto-template", help="Generate template-based Pareto-friendly SNAP instances")
    p.add_argument("--output", required=True, help="Output directory")
    p.add_argument("--name", default="pareto_template", help="Instance/profile prefix")
    p.add_argument("--groups", type=int, required=True, help="Number of student groups |I|; recommended 3..8")
    p.add_argument("--courses", type=int, required=True, help="Number of courses |D|; recommended 2..5")
    p.add_argument("--wards", type=int, required=True, help="Number of wards |W|; recommended 3..6")
    p.add_argument("--hospitals", type=int, required=True, help="Number of hospitals |H|; allowed 1..3")
    p.add_argument("--instances", type=int, default=1)
    p.add_argument("--start-index", type=int, default=1)
    p.add_argument("--seed", type=int, default=20260508)
    p.add_argument("--series-name", default="snap-pareto-template-v1.8.0")
    p.add_argument("--max-attempts", type=int, default=80)
    p.add_argument("--no-xlsx", action="store_true", help="Do not write instance.xlsx files")
    p.add_argument("--no-matlab", action="store_true", help="Do not write per-instance MATLAB loader .m files")
    p.add_argument("--no-txt", action="store_true", help="Do not write txt/ symbol export")
    p.add_argument("--no-gams", action="store_true", help="Do not write GAMS helper files")
    p.set_defaults(func=cmd_generate_pareto_template)



    p = sub.add_parser("generate-pareto-template-light", help="Generate light template-based Pareto-friendly SNAP instances for faster exact/GAMS runs")
    p.add_argument("--output", required=True, help="Output directory")
    p.add_argument("--name", default="pareto_template_light", help="Instance/profile prefix")
    p.add_argument("--groups", type=int, required=True, help="Number of student groups |I|; allowed 3..5")
    p.add_argument("--courses", type=int, required=True, help="Number of courses |D|; allowed 2..3")
    p.add_argument("--wards", type=int, required=True, help="Number of wards |W|; allowed 3..4")
    p.add_argument("--hospitals", type=int, required=True, help="Number of hospitals |H|; allowed 1..2")
    p.add_argument("--instances", type=int, default=1)
    p.add_argument("--start-index", type=int, default=1)
    p.add_argument("--seed", type=int, default=20260508)
    p.add_argument("--series-name", default="snap-pareto-template-light-v1.8.1")
    p.add_argument("--max-attempts", type=int, default=80)
    p.add_argument("--no-xlsx", action="store_true", help="Do not write instance.xlsx files")
    p.add_argument("--no-matlab", action="store_true", help="Do not write per-instance MATLAB loader .m files")
    p.add_argument("--no-txt", action="store_true", help="Do not write txt/ symbol export")
    p.add_argument("--no-gams", action="store_true", help="Do not write GAMS helper files")
    p.set_defaults(func=cmd_generate_pareto_template_light)

    p = sub.add_parser("generate-pareto-template-ultralight", help="Generate ultra-sparse template-based Pareto-friendly SNAP instances for exact/GAMS runs")
    p.add_argument("--output", required=True, help="Output directory")
    p.add_argument("--name", default="pareto_template_ultralight", help="Instance/profile prefix")
    p.add_argument("--groups", type=int, required=True, help="Number of student groups |I|; allowed 3..4")
    p.add_argument("--hospitals", type=int, required=True, help="Number of hospitals |H|; allowed 1..2")
    p.add_argument("--instances", type=int, default=1)
    p.add_argument("--start-index", type=int, default=1)
    p.add_argument("--seed", type=int, default=20260508)
    p.add_argument("--series-name", default="snap-pareto-template-ultralight-v1.8.2")
    p.add_argument("--max-attempts", type=int, default=20)
    p.add_argument("--no-xlsx", action="store_true", help="Do not write instance.xlsx files")
    p.add_argument("--no-matlab", action="store_true", help="Do not write per-instance MATLAB loader .m files")
    p.add_argument("--no-txt", action="store_true", help="Do not write txt/ symbol export")
    p.add_argument("--no-gams", action="store_true", help="Do not write GAMS helper files")
    p.set_defaults(func=cmd_generate_pareto_template_ultralight)

    p = sub.add_parser("generate-grid", help="Generate a benchmark grid across profiles")
    p.add_argument("--output", required=True, help="Output directory")
    p.add_argument("--profiles", nargs="*", choices=list_profiles(), help="Optional profile subset")
    p.add_argument("--instances-per-profile", type=int, default=2, help="Instances per selected profile")
    p.add_argument("--seed", type=int, default=20260508, help="Base seed for reproducibility")
    p.add_argument("--series-name", default="snap-math-model-taillard-inspired-v1.8.1")
    p.add_argument("--no-xlsx", action="store_true", help="Do not write instance.xlsx files")
    p.add_argument("--no-matlab", action="store_true", help="Do not write per-instance MATLAB loader .m files")
    p.add_argument("--no-txt", action="store_true", help="Do not write txt/ symbol export")
    p.add_argument("--no-gams", action="store_true", help="Do not write GAMS helper files")
    p.set_defaults(func=cmd_generate_grid)

    p = sub.add_parser("check", help="Check feasibility of a generated/planted schedule")
    p.add_argument("--instance", required=True, help="Path to instance.json")
    p.add_argument("--schedule", required=True, help="Path to planted_solution.csv or another schedule CSV")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("describe", help="Compute complexity metadata for an instance")
    p.add_argument("--instance", required=True, help="Path to instance.json")
    p.set_defaults(func=cmd_describe)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .complexity import compute_complexity
from .feasibility import check_schedule, summarize_schedule
from .models import GeneratedInstance


def _id(prefix: str, n: int) -> str:
    return f"{prefix}{n:03d}"


@dataclass(frozen=True)
class ParetoTemplateSpec:
    name: str
    groups: int
    courses: int
    wards: int
    hospitals: int
    min_weeks_per_course: int = 2
    max_weeks_per_course: int = 3
    consecutive_days: int = 3
    max_attempts: int = 80


class _PlacementError(RuntimeError):
    pass


def _make_base_sets(spec: ParetoTemplateSpec) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    groups = [
        {
            "group_id": _id("I", i),
            "i_index": i,
            "semester": 7,
            "mem": 1,
        }
        for i in range(1, spec.groups + 1)
    ]
    wards = [{"ward_id": _id("W", w), "w_index": w, "name": f"Ward {w}", "hospital_id": _id("H", 1)} for w in range(1, spec.wards + 1)]
    hospitals = [{"hospital_id": _id("H", h), "h_index": h, "name": f"Hospital {h}"} for h in range(1, spec.hospitals + 1)]
    return groups, wards, hospitals


def _course_weeks(d: int, rng: random.Random, max_courses: int) -> int:
    # Keep total course weeks per group under 16. The fixed first course is 2 weeks;
    # flexible courses alternate 2 and 3 weeks for visible timing trade-offs.
    if d == 1:
        return 2
    if max_courses <= 3:
        return 3 if d == 2 else 2
    return 3 if d in {2, 3} else 2


def _make_courses(spec: ParetoTemplateSpec, rng: random.Random) -> list[dict[str, Any]]:
    courses: list[dict[str, Any]] = []
    O = int(spec.consecutive_days)
    for d in range(1, spec.courses + 1):
        weeks = _course_weeks(d, rng, spec.courses)
        Du = weeks * O
        courses.append({
            "course_id": _id("D", d),
            "d_index": d,
            "semester": 7,
            "Du_days": int(Du),
            "O_consecutive_days": int(O),
            # D1 is a fixed baseline course; all other courses are flexible ward-choice courses.
            "PW": 0 if d == 1 else 1,
            "requires_consecutive_days": True,
            "template_role": "fixed_baseline" if d == 1 else "flexible_choice",
        })
    return courses


def _make_B(wards: list[dict[str, Any]], hospitals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Complete B maximizes hospital alternatives while keeping feasibility transparent.
    return [
        {"ward_id": w["ward_id"], "hospital_id": h["hospital_id"], "exists": True}
        for w in wards
        for h in hospitals
    ]


def _flexible_ward_set(course_index: int, ward_ids: list[str], rng: random.Random) -> list[str]:
    if len(ward_ids) <= 1:
        return list(ward_ids)
    # Course 1 uses W001 only. Flexible courses use 2 or 3 non-W001 wards whenever possible.
    pool = ward_ids[1:] if len(ward_ids) >= 3 else ward_ids
    if len(pool) < 2:
        pool = ward_ids
    k = min(len(pool), 2 + (1 if len(pool) >= 3 and course_index % 3 == 0 else 0))
    start = (course_index - 2) % len(pool)
    selected = []
    for j in range(k):
        selected.append(pool[(start + j) % len(pool)])
    return sorted(set(selected))


def _make_mea(spec: ParetoTemplateSpec, courses: list[dict[str, Any]], wards: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    ward_ids = [w["ward_id"] for w in wards]
    out: list[dict[str, Any]] = []
    for c in courses:
        c_id = c["course_id"]
        d_idx = int(c["d_index"])
        if d_idx == 1:
            selected = {ward_ids[0]}
        else:
            selected = set(_flexible_ward_set(d_idx, ward_ids, rng))
        primary = sorted(selected)[0] if selected else None
        for w in ward_ids:
            defined = w in selected
            role = "none"
            if defined:
                role = "primary" if w == primary else "alternative"
            out.append({"course_id": c_id, "ward_id": w, "defined": bool(defined), "role": role})
    return out


def _make_params(
    spec: ParetoTemplateSpec,
    groups: list[dict[str, Any]],
    courses: list[dict[str, Any]],
    wards: list[dict[str, Any]],
    hospitals: list[dict[str, Any]],
    B: list[dict[str, Any]],
    mea: list[dict[str, Any]],
) -> dict[str, Any]:
    group_ids = [g["group_id"] for g in groups]
    course_ids = [c["course_id"] for c in courses]
    ward_ids = [w["ward_id"] for w in wards]
    hospital_ids = [h["hospital_id"] for h in hospitals]
    course_by_id = {c["course_id"]: c for c in courses}
    mea_defined = {(r["course_id"], r["ward_id"]): r for r in mea if r.get("defined")}

    comm = [{"group_id": i, "course_id": d, "required": True} for i in group_ids for d in course_ids]
    com = [{"group_id": i, "course_id": d, "ward_id": w, "required": (d, w) in mea_defined} for i in group_ids for d in course_ids for w in ward_ids]
    eb = [{"course_id": d, "ward_id": w, "hospital_id": h, "eligible": (d, w) in mea_defined} for d in course_ids for w in ward_ids for h in hospital_ids]

    dur = []
    weeks = []
    for d in course_ids:
        c = course_by_id[d]
        for w in ward_ids:
            if (d, w) in mea_defined:
                dur_days = int(c["Du_days"])
                wk = int(dur_days // int(c["O_consecutive_days"]))
            else:
                dur_days = 0
                wk = 0
            dur.append({"course_id": d, "ward_id": w, "Dur_days": int(dur_days)})
            weeks.append({"course_id": d, "ward_id": w, "weeks": int(wk)})

    cap = []
    for d in course_ids:
        for w in ward_ids:
            role = mea_defined.get((d, w), {}).get("role", "none")
            for h in hospital_ids:
                if (d, w) not in mea_defined:
                    capacity = 0
                else:
                    # Keep capacity limited to create timing pressure. Alternatives are not
                    # made globally dominant; they just provide additional parallel slots.
                    capacity = 1
                    if role == "alternative" and spec.hospitals >= 2:
                        capacity = 1
                cap.append({"course_id": d, "ward_id": w, "hospital_id": h, "capacity": int(capacity), "capacity_role": role})

    av = []
    for i in group_ids:
        for k in range(1, 17):
            for t in range(1, 7):
                av.append({"group_id": i, "week": k, "day": t, "available": t in {1, 2, 3}})

    avb = []
    for w in ward_ids:
        for h in hospital_ids:
            for k in range(1, 17):
                for t in range(1, 7):
                    avb.append({"ward_id": w, "hospital_id": h, "week": k, "day": t, "available": True})

    ne = [{"course_id": d, "ward_id": w, "allowed": False} for d in course_ids for w in ward_ids]
    nee = [{"course_id": d, "ward_id": w, "minimum_long_shifts": 0} for d in course_ids for w in ward_ids]
    nt = [{"ward_id": w, "interference_allowed": False} for w in ward_ids]

    return {
        "B": B,
        "Du": [{"course_id": c["course_id"], "Du_days": int(c["Du_days"])} for c in courses],
        "O": [{"course_id": c["course_id"], "O_consecutive_days": int(c["O_consecutive_days"])} for c in courses],
        "PW": [{"course_id": c["course_id"], "PW": int(c["PW"])} for c in courses],
        "Mea": mea,
        "Comm": comm,
        "Dur": dur,
        "weeks": weeks,
        "Cap": cap,
        "Com": com,
        "Eb": eb,
        "Av": av,
        "Avb": avb,
        "ne": ne,
        "nee": nee,
        "nt": nt,
    }


def _location_options(course_id: str, params: dict[str, Any]) -> list[tuple[str, str]]:
    defined_wards = [r["ward_id"] for r in params["Mea"] if r["course_id"] == course_id and r.get("defined")]
    out = []
    for row in params["Eb"]:
        if row["course_id"] == course_id and row["ward_id"] in defined_wards and row.get("eligible"):
            out.append((row["ward_id"], row["hospital_id"]))
    return sorted(out)


def _plant_schedule(
    spec: ParetoTemplateSpec,
    groups: list[dict[str, Any]],
    courses: list[dict[str, Any]],
    params: dict[str, Any],
    rng: random.Random,
) -> list[dict[str, Any]]:
    O_by_d = {r["course_id"]: int(r["O_consecutive_days"]) for r in params["O"]}
    Du_by_d = {r["course_id"]: int(r["Du_days"]) for r in params["Du"]}
    weeks_by_dw = {(r["course_id"], r["ward_id"]): int(r["weeks"]) for r in params["weeks"]}
    cap_by_dwh = {(r["course_id"], r["ward_id"], r["hospital_id"]): int(r["capacity"]) for r in params["Cap"]}
    group_by_id = {g["group_id"]: g for g in groups}

    group_week_busy: set[tuple[str, int]] = set()
    ward_location_course: dict[tuple[str, str, int], str] = {}
    course_location_load: dict[tuple[str, str, str, int], int] = defaultdict(int)

    schedule: list[dict[str, Any]] = []
    assignment_no = 1

    # Fixed baseline course first, then flexible courses. This mirrors the successful sample.
    for c in courses:
        d = c["course_id"]
        pw = int(c["PW"])
        options_all = _location_options(d, params)
        if not options_all:
            raise _PlacementError(f"No location options for {d}")

        for g in groups:
            gid = g["group_id"]
            mem = int(g.get("mem", 1))
            if pw == 0:
                # In this template PW0 courses have a single ward but may choose among hospitals.
                segment_options = [options_all]
            else:
                segment_options = [options_all]

            for options in segment_options:
                # For diversity, rotate preferred options by group and course.
                options_sorted = sorted(options)
                rot = (int(g["i_index"]) + int(c["d_index"])) % len(options_sorted)
                options_ordered = options_sorted[rot:] + options_sorted[:rot]
                placed = False

                for start_week in range(1, 17):
                    for w, h in options_ordered:
                        segment_weeks = weeks_by_dw.get((d, w), 0)
                        if segment_weeks <= 0:
                            continue
                        if start_week + segment_weeks - 1 > 16:
                            continue
                        weeks_needed = list(range(start_week, start_week + segment_weeks))
                        if any((gid, wk) in group_week_busy for wk in weeks_needed):
                            continue
                        ok = True
                        for wk in weeks_needed:
                            # Ward/hospital cannot host different courses on the same days.
                            existing_course = ward_location_course.get((w, h, wk))
                            if existing_course is not None and existing_course != d:
                                ok = False
                                break
                            load = course_location_load.get((d, w, h, wk), 0)
                            if load + mem > cap_by_dwh.get((d, w, h), 0):
                                ok = False
                                break
                        if not ok:
                            continue

                        for wk in weeks_needed:
                            group_week_busy.add((gid, wk))
                            ward_location_course[(w, h, wk)] = d
                            course_location_load[(d, w, h, wk)] += mem
                            schedule.append({
                                "assignment_id": f"A{assignment_no:05d}",
                                "group_id": gid,
                                "course_id": d,
                                "ward_id": w,
                                "hospital_id": h,
                                "week": wk,
                                "start_week": start_week,
                                "start_day": 1,
                                "O_consecutive_days": O_by_d[d],
                                "segment_Dur_days": Du_by_d[d],
                                "segment_weeks": segment_weeks,
                                "days": [1, 2, 3],
                                "shift": 1,
                                "mem": mem,
                                "PW": pw,
                            })
                            assignment_no += 1
                        placed = True
                        break
                    if placed:
                        break
                if not placed:
                    raise _PlacementError(f"Could not place {gid}-{d}")
    return schedule


def _pareto_template_potential(instance: dict[str, Any], schedule: list[dict[str, Any]]) -> dict[str, Any]:
    mp = instance["model_parameters"]
    pw = {r["course_id"]: int(r["PW"]) for r in mp["PW"]}
    mea_by_d: dict[str, list[str]] = defaultdict(list)
    hospitals_by_ward = defaultdict(set)
    for r in mp["B"]:
        if r.get("exists"):
            hospitals_by_ward[r["ward_id"]].add(r["hospital_id"])
    for r in mp["Mea"]:
        if r.get("defined"):
            mea_by_d[r["course_id"]].append(r["ward_id"])
    pw1_courses = [d for d, val in pw.items() if val == 1]
    multi = [d for d in pw1_courses if len(mea_by_d.get(d, [])) >= 2]
    parallel_units = 0
    for d in multi:
        for w in mea_by_d[d]:
            parallel_units += len(hospitals_by_ward[w])
    summary = summarize_schedule(instance, schedule)
    accepted = len(multi) >= 1 and parallel_units >= 2 and summary.get("latest_completion_time", 999) <= 96
    return {
        "accepted": bool(accepted),
        "template": "fixed-plus-flexible-parallel-capacity",
        "pw1_courses": len(pw1_courses),
        "pw1_multi_option_courses": len(multi),
        "multi_option_ratio": round(len(multi) / max(1, len(pw1_courses)), 4),
        "parallel_location_units_for_flexible_courses": int(parallel_units),
        "intended_tradeoff": "concentrating flexible courses uses fewer wards/locations but increases completion span; distributing them uses more wards/locations but shortens completion span",
        "screen_summary": summary,
    }


def generate_pareto_template_instance(
    *,
    name: str,
    groups_n: int,
    courses_n: int,
    wards_n: int,
    hospitals_n: int,
    instance_index: int,
    base_seed: int,
    series_name: str = "snap-pareto-template-v1.8.0",
    max_attempts: int = 80,
) -> GeneratedInstance:
    if not (1 <= hospitals_n <= 3):
        raise ValueError("pareto-template requires 1 <= hospitals <= 3")
    if not (3 <= groups_n <= 8):
        raise ValueError("pareto-template is intended for 3 <= groups <= 8")
    if not (2 <= courses_n <= 5):
        raise ValueError("pareto-template is intended for 2 <= courses <= 5")
    if not (3 <= wards_n <= 6):
        raise ValueError("pareto-template is intended for 3 <= wards <= 6")

    spec = ParetoTemplateSpec(name=name, groups=groups_n, courses=courses_n, wards=wards_n, hospitals=hospitals_n, max_attempts=max_attempts)
    instance_seed = int(base_seed) + int(instance_index) * 1009
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        rng = random.Random(instance_seed + attempt - 1)
        try:
            groups, wards, hospitals = _make_base_sets(spec)
            courses = _make_courses(spec, rng)
            B = _make_B(wards, hospitals)
            mea = _make_mea(spec, courses, wards, rng)
            params = _make_params(spec, groups, courses, wards, hospitals, B, mea)
            schedule = _plant_schedule(spec, groups, courses, params, rng)
        except Exception as exc:
            last_error = exc
            continue

        instance_id = f"{name}_{instance_index:03d}"
        instance: dict[str, Any] = {
            "metadata": {
                "instance_id": instance_id,
                "series_name": series_name,
                "format_version": "1.8.0",
                "generator": "SNAP template-based Pareto-friendly instance generator",
                "generator_note": "Template based on a fixed baseline course plus flexible ward-choice courses with limited parallel capacity.",
                "profile": name,
                "base_seed": int(base_seed),
                "instance_seed": int(instance_seed + attempt - 1),
                "attempt": attempt,
                "rng": "Python random.Random / Mersenne Twister",
            },
            "time": {
                "shifts": 2,
                "days_per_week": 6,
                "weeks": 16,
                "shift_durations_hours": {"1": 5, "2": 10},
            },
            "sets": {"I": groups_n, "D": courses_n, "W": wards_n, "H": hospitals_n, "S": 2, "T": 6, "K": 16},
            "groups": groups,
            "hospitals": hospitals,
            "wards": wards,
            "courses": courses,
            "model_parameters": params,
            "policy": {
                "capacity_constraint_is_hard": True,
                "group_daily_overlap_is_forbidden": True,
                "course_days_must_be_consecutive": True,
                "avb_default_is_one": True,
                "nee_is_zero_for_current_study": True,
                "template_pareto_policy": "mem=1, O=3, Av days 1-3, Avb all 1, ne=nee=nt=0",
            },
        }
        feasibility = check_schedule(instance, schedule)
        if not feasibility.get("feasible"):
            last_error = RuntimeError(f"Template planted schedule infeasible: {feasibility}")
            continue
        potential = _pareto_template_potential(instance, schedule)
        if not potential.get("accepted"):
            last_error = RuntimeError(f"Template pareto potential rejected: {potential}")
            continue
        complexity = compute_complexity(instance)
        metadata = {
            "instance_id": instance_id,
            "series_name": series_name,
            "profile": name,
            "base_seed": int(base_seed),
            "instance_seed": int(instance_seed + attempt - 1),
            "attempt": attempt,
            "has_planted_feasible_solution": True,
            "generator_mode": "pareto_template",
            "mathematical_model_alignment": {
                "fixed_time": {"s": 2, "t": 6, "k": 16},
                "template_rule": "D1 is fixed baseline with PW=0 and one ward; D2..D are flexible with PW=1 and multiple ward/hospital alternatives.",
                "tradeoff_rule": "ward/location concentration should increase time span, while distribution can reduce time span at the cost of using more wards/locations.",
            },
            "complexity": complexity,
            "planted_solution_feasibility": feasibility,
            "tradeoff_mode": "pareto_template",
            "pareto_potential": potential,
        }
        return GeneratedInstance(instance=instance, planted_schedule=schedule, metadata=metadata)

    raise RuntimeError(f"Failed to generate pareto-template SNAP instance for name={name}, index={instance_index}. Last error: {last_error}")

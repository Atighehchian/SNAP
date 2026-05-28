from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .complexity import compute_complexity
from .feasibility import check_schedule, summarize_schedule
from .models import GeneratedInstance


def _id(prefix: str, n: int) -> str:
    return f"{prefix}{n:03d}"


@dataclass(frozen=True)
class ParetoTemplateLightSpec:
    name: str
    groups: int
    courses: int
    wards: int
    hospitals: int
    consecutive_days: int = 3
    max_attempts: int = 80


class _PlacementError(RuntimeError):
    pass


def _make_base_sets(spec: ParetoTemplateLightSpec) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    groups = [
        {
            "group_id": _id("I", i),
            "i_index": i,
            "semester": 7,
            "mem": 1,
        }
        for i in range(1, spec.groups + 1)
    ]
    wards = [
        {"ward_id": _id("W", w), "w_index": w, "name": f"Ward {w}", "hospital_id": _id("H", 1)}
        for w in range(1, spec.wards + 1)
    ]
    hospitals = [
        {"hospital_id": _id("H", h), "h_index": h, "name": f"Hospital {h}"}
        for h in range(1, spec.hospitals + 1)
    ]
    return groups, wards, hospitals


def _make_courses(spec: ParetoTemplateLightSpec) -> list[dict[str, Any]]:
    courses: list[dict[str, Any]] = []
    O = int(spec.consecutive_days)
    for d in range(1, spec.courses + 1):
        if d == 1:
            weeks = 2
            pw = 0
            role = "fixed_baseline"
        elif d == 2:
            weeks = 3
            pw = 1
            role = "flexible_choice"
        else:
            weeks = 2
            pw = 1
            role = "flexible_choice"
        courses.append(
            {
                "course_id": _id("D", d),
                "d_index": d,
                "semester": 7,
                "Du_days": int(weeks * O),
                "O_consecutive_days": int(O),
                "PW": int(pw),
                "requires_consecutive_days": True,
                "template_role": role,
                "template_weeks": int(weeks),
            }
        )
    return courses


def _make_B(wards: list[dict[str, Any]], hospitals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create a sparse B matrix to reduce active IDWH combinations.

    For one hospital, all wards exist in H001.
    For two hospitals, each ward exists in exactly one hospital, alternating.
    This is intentionally lighter than the full B(w,h)=1 pattern.
    """
    out: list[dict[str, Any]] = []
    hospital_ids = [h["hospital_id"] for h in hospitals]
    for w in wards:
        w_idx = int(w["w_index"])
        for h in hospitals:
            if len(hospital_ids) == 1:
                exists = True
            else:
                # W001 and W002 in H001, W003 and W004 in H002 pattern where possible.
                # This ensures D2 has one option in each hospital when W>=3.
                preferred_h = hospital_ids[0] if w_idx <= 2 else hospital_ids[1]
                exists = h["hospital_id"] == preferred_h
            out.append({"ward_id": w["ward_id"], "hospital_id": h["hospital_id"], "exists": bool(exists)})
    return out


def _flexible_wards(course_index: int, ward_ids: list[str]) -> list[str]:
    # D2: W2 and W3. D3: W3 and W4 if available, otherwise W2 and W3.
    if len(ward_ids) < 3:
        return ward_ids[:]
    if course_index == 2:
        return [ward_ids[1], ward_ids[2]]
    if len(ward_ids) >= 4:
        return [ward_ids[2], ward_ids[3]]
    return [ward_ids[1], ward_ids[2]]


def _make_mea(courses: list[dict[str, Any]], wards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ward_ids = [w["ward_id"] for w in wards]
    out: list[dict[str, Any]] = []
    for c in courses:
        d_idx = int(c["d_index"])
        d_id = c["course_id"]
        if d_idx == 1:
            selected = {ward_ids[0]}
        else:
            selected = set(_flexible_wards(d_idx, ward_ids))
        primary = sorted(selected)[0]
        for w in ward_ids:
            defined = w in selected
            if not defined:
                role = "none"
            elif w == primary:
                role = "primary"
            else:
                role = "alternative"
            out.append({"course_id": d_id, "ward_id": w, "defined": bool(defined), "role": role})
    return out


def _make_params(
    spec: ParetoTemplateLightSpec,
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
    B_exists = {(r["ward_id"], r["hospital_id"]) for r in B if r.get("exists")}

    comm = [{"group_id": i, "course_id": d, "required": True} for i in group_ids for d in course_ids]
    com = [
        {"group_id": i, "course_id": d, "ward_id": w, "required": (d, w) in mea_defined}
        for i in group_ids
        for d in course_ids
        for w in ward_ids
    ]
    eb = [
        {"course_id": d, "ward_id": w, "hospital_id": h, "eligible": (d, w) in mea_defined and (w, h) in B_exists}
        for d in course_ids
        for w in ward_ids
        for h in hospital_ids
    ]

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
                if (d, w) not in mea_defined or (w, h) not in B_exists:
                    capacity = 0
                else:
                    # mem=1 and cap=1 creates parallel-resource pressure without infeasibility.
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
                    available = (w, h) in B_exists
                    avb.append({"ward_id": w, "hospital_id": h, "week": k, "day": t, "available": bool(available)})

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
    out = []
    for row in params["Eb"]:
        if row["course_id"] == course_id and row.get("eligible"):
            out.append((row["ward_id"], row["hospital_id"]))
    return sorted(out)


def _plant_schedule(
    spec: ParetoTemplateLightSpec,
    groups: list[dict[str, Any]],
    courses: list[dict[str, Any]],
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    O_by_d = {r["course_id"]: int(r["O_consecutive_days"]) for r in params["O"]}
    Du_by_d = {r["course_id"]: int(r["Du_days"]) for r in params["Du"]}
    weeks_by_dw = {(r["course_id"], r["ward_id"]): int(r["weeks"]) for r in params["weeks"]}
    cap_by_dwh = {(r["course_id"], r["ward_id"], r["hospital_id"]): int(r["capacity"]) for r in params["Cap"]}

    group_week_busy: set[tuple[str, int]] = set()
    ward_location_course: dict[tuple[str, str, int], str] = {}
    course_location_load: dict[tuple[str, str, str, int], int] = defaultdict(int)
    schedule: list[dict[str, Any]] = []
    assignment_no = 1

    for c in courses:
        d = c["course_id"]
        pw = int(c["PW"])
        options_all = _location_options(d, params)
        if not options_all:
            raise _PlacementError(f"No location options for {d}")
        for g in groups:
            gid = g["group_id"]
            mem = int(g.get("mem", 1))
            options_sorted = sorted(options_all)
            # Rotate groups over available locations to create a feasible planted solution
            # while preserving the trade-off options for the optimizer.
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
                    needed_weeks = list(range(start_week, start_week + segment_weeks))
                    if any((gid, wk) in group_week_busy for wk in needed_weeks):
                        continue
                    ok = True
                    for wk in needed_weeks:
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
                    for wk in needed_weeks:
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


def _pareto_light_potential(instance: dict[str, Any], schedule: list[dict[str, Any]]) -> dict[str, Any]:
    mp = instance["model_parameters"]
    pw = {r["course_id"]: int(r["PW"]) for r in mp["PW"]}
    mea_by_d: dict[str, list[str]] = defaultdict(list)
    eligible_locations_by_d: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for r in mp["Mea"]:
        if r.get("defined"):
            mea_by_d[r["course_id"]].append(r["ward_id"])
    for r in mp["Eb"]:
        if r.get("eligible"):
            eligible_locations_by_d[r["course_id"]].add((r["ward_id"], r["hospital_id"]))
    pw1_courses = [d for d, val in pw.items() if val == 1]
    multi_ward = [d for d in pw1_courses if len(mea_by_d.get(d, [])) >= 2]
    multi_location = [d for d in pw1_courses if len(eligible_locations_by_d.get(d, set())) >= 2]
    summary = summarize_schedule(instance, schedule)
    active_idwh = sum(1 for r in mp["Eb"] if r.get("eligible")) * int(instance["sets"]["I"])
    accepted = len(multi_ward) >= 1 and len(multi_location) >= 1 and active_idwh <= 30 and summary.get("latest_completion_time", 999) <= 96
    return {
        "accepted": bool(accepted),
        "template": "pareto-template-light",
        "pw1_courses": len(pw1_courses),
        "pw1_multi_ward_courses": len(multi_ward),
        "pw1_multi_location_courses": len(multi_location),
        "active_IDWH_estimate": int(active_idwh),
        "intended_tradeoff": "use fewer ward/location choices for concentration and longer span, or distribute flexible courses across more locations for shorter span",
        "screen_summary": summary,
    }


def generate_pareto_template_light_instance(
    *,
    name: str,
    groups_n: int,
    courses_n: int,
    wards_n: int,
    hospitals_n: int,
    instance_index: int,
    base_seed: int,
    series_name: str = "snap-pareto-template-light-v1.8.1",
    max_attempts: int = 80,
) -> GeneratedInstance:
    if not (1 <= hospitals_n <= 2):
        raise ValueError("pareto-template-light requires 1 <= hospitals <= 2")
    if not (3 <= groups_n <= 5):
        raise ValueError("pareto-template-light is intended for 3 <= groups <= 5")
    if not (2 <= courses_n <= 3):
        raise ValueError("pareto-template-light is intended for 2 <= courses <= 3")
    if not (3 <= wards_n <= 4):
        raise ValueError("pareto-template-light is intended for 3 <= wards <= 4")

    spec = ParetoTemplateLightSpec(name=name, groups=groups_n, courses=courses_n, wards=wards_n, hospitals=hospitals_n, max_attempts=max_attempts)
    instance_seed = int(base_seed) + int(instance_index) * 1009
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            groups, wards, hospitals = _make_base_sets(spec)
            courses = _make_courses(spec)
            B = _make_B(wards, hospitals)
            mea = _make_mea(courses, wards)
            params = _make_params(spec, groups, courses, wards, hospitals, B, mea)
            schedule = _plant_schedule(spec, groups, courses, params)
        except Exception as exc:
            last_error = exc
            continue

        instance_id = f"{name}_{instance_index:03d}"
        instance: dict[str, Any] = {
            "metadata": {
                "instance_id": instance_id,
                "series_name": series_name,
                "format_version": "1.8.1",
                "generator": "SNAP light template-based Pareto-friendly instance generator",
                "generator_note": "Light template designed to keep active IDWH small for exact GAMS/AUGMECON runs.",
                "profile": name,
                "base_seed": int(base_seed),
                "instance_seed": int(instance_seed + attempt - 1),
                "attempt": attempt,
                "rng": "deterministic template with seed recorded for reproducibility",
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
                "avb_default_is_one_for_existing_B_only": True,
                "nee_is_zero_for_current_study": True,
                "light_template_policy": "mem=1, D=2..3, W=3..4, H=1..2, sparse B, exactly two ward options for flexible courses",
            },
        }
        feasibility = check_schedule(instance, schedule)
        if not feasibility.get("feasible"):
            last_error = RuntimeError(f"Light template planted schedule infeasible: {feasibility}")
            continue
        potential = _pareto_light_potential(instance, schedule)
        if not potential.get("accepted"):
            last_error = RuntimeError(f"Light template pareto potential rejected: {potential}")
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
            "generator_mode": "pareto_template_light",
            "mathematical_model_alignment": {
                "fixed_time": {"s": 2, "t": 6, "k": 16},
                "template_rule": "D1 is fixed baseline with PW=0 and one ward; D2/D3 are flexible with PW=1 and exactly two ward choices.",
                "speed_rule": "B is sparse and active IDWH is intentionally small to support exact GAMS/AUGMECON runs.",
            },
            "complexity": complexity,
            "planted_solution_feasibility": feasibility,
            "tradeoff_mode": "pareto_template_light",
            "pareto_potential": potential,
        }
        return GeneratedInstance(instance=instance, planted_schedule=schedule, metadata=metadata)

    raise RuntimeError(f"Failed to generate pareto-template-light SNAP instance for name={name}, index={instance_index}. Last error: {last_error}")

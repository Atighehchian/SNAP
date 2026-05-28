from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


def days_from_row(row: Dict[str, Any]) -> list[int]:
    """Return the list of training days used by one schedule row."""
    value = row.get("days")
    if isinstance(value, list):
        return [int(x) for x in value]
    if isinstance(value, str) and value.strip():
        return [int(x) for x in value.replace(",", ";").split(";") if x]
    start = int(row.get("start_day", 1))
    duration = int(row.get("O_consecutive_days", row.get("segment_Dur_days", 1)))
    return list(range(start, start + duration))


def _index_model_parameters(instance: Dict[str, Any]) -> Dict[str, Any]:
    mp = instance["model_parameters"]
    return {
        "B": {(x["ward_id"], x["hospital_id"]) for x in mp.get("B", []) if x.get("exists", True)},
        "Mea": {(x["course_id"], x["ward_id"]) for x in mp.get("Mea", []) if x.get("defined", False)},
        "PW": {x["course_id"]: int(x["PW"]) for x in mp.get("PW", [])},
        "Du": {x["course_id"]: int(x["Du_days"]) for x in mp.get("Du", [])},
        "O": {x["course_id"]: int(x["O_consecutive_days"]) for x in mp.get("O", [])},
        "Dur": {(x["course_id"], x["ward_id"]): int(x["Dur_days"]) for x in mp.get("Dur", [])},
        "weeks": {(x["course_id"], x["ward_id"]): int(x["weeks"]) for x in mp.get("weeks", [])},
        "Cap": {(x["course_id"], x["ward_id"], x["hospital_id"]): int(x["capacity"]) for x in mp.get("Cap", [])},
        "Comm": {(x["group_id"], x["course_id"]) for x in mp.get("Comm", []) if x.get("required", False)},
        "Com": {(x["group_id"], x["course_id"], x["ward_id"]) for x in mp.get("Com", []) if x.get("required", False)},
        "Av": {(x["group_id"], int(x["week"]), int(x["day"])): bool(x.get("available", False)) for x in mp.get("Av", [])},
        "Avb": {(x["ward_id"], x["hospital_id"], int(x["week"]), int(x["day"])): bool(x.get("available", False)) for x in mp.get("Avb", [])},
        "ne": {(x["course_id"], x["ward_id"]): bool(x.get("allowed", False)) for x in mp.get("ne", [])},
        "nee": {(x["course_id"], x["ward_id"]): int(x.get("minimum_long_shifts", 0)) for x in mp.get("nee", [])},
        "nt": {x["ward_id"]: bool(x.get("interference_allowed", False)) for x in mp.get("nt", [])},
    }


def summarize_schedule(instance: Dict[str, Any], schedule: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute model-aligned schedule statistics without judging feasibility."""
    days_per_week = int(instance["time"].get("days_per_week", 6))
    used_ward_hospital_slots: set[tuple[str, str, int, int]] = set()
    used_group_slots: set[tuple[str, int, int]] = set()
    course_wards: dict[str, set[str]] = defaultdict(set)
    completion_times: list[int] = []

    for row in schedule:
        group_id = str(row.get("group_id", ""))
        course_id = str(row.get("course_id", ""))
        ward_id = str(row.get("ward_id", ""))
        hospital_id = str(row.get("hospital_id", ""))
        week = int(row.get("week", 0))
        days = days_from_row(row)
        if days:
            completion_times.append((week - 1) * days_per_week + max(days))
        if course_id and ward_id:
            course_wards[course_id].add(ward_id)
        for day in days:
            if ward_id and hospital_id:
                used_ward_hospital_slots.add((ward_id, hospital_id, week, int(day)))
            if group_id:
                used_group_slots.add((group_id, week, int(day)))

    return {
        "assignments": len(schedule),
        "used_ward_hospital_day_slots": len(used_ward_hospital_slots),
        "used_group_day_slots": len(used_group_slots),
        "scheduled_courses": len(course_wards),
        "course_ward_pairs": sum(len(v) for v in course_wards.values()),
        "latest_completion_time": max(completion_times) if completion_times else 0,
    }


def check_schedule(instance: Dict[str, Any], schedule: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check a candidate schedule against the paper-model aligned SNAP parameters.

    The checker intentionally uses only group-based notation. The set I is treated as
    the set of student groups, so schedule rows must use `group_id`, not `student_id`.
    """
    if "model_parameters" not in instance:
        raise ValueError("This package supports only MIP-aligned SNAP instances with a model_parameters section.")

    violations: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    idx = _index_model_parameters(instance)
    time = instance.get("time", {})
    K = int(time.get("weeks", 16))
    T = int(time.get("days_per_week", 6))
    groups = {g["group_id"]: g for g in instance.get("groups", [])}
    courses = {c["course_id"]: c for c in instance.get("courses", [])}
    wards = {w["ward_id"]: w for w in instance.get("wards", [])}
    hospitals = {h["hospital_id"]: h for h in instance.get("hospitals", [])}

    group_day_occ: dict[tuple[str, int, int], list[str]] = defaultdict(list)
    ward_day_course_occ: dict[tuple[str, str, int, int], list[tuple[str, str]]] = defaultdict(list)
    ward_day_kind_occ: dict[tuple[str, str, int, int, str], list[tuple[str, str]]] = defaultdict(list)
    cap_load: dict[tuple[str, str, str, int, int], int] = defaultdict(int)
    segment_rows: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    group_course_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    long_shift_count: dict[tuple[str, str], int] = defaultdict(int)

    for rno, row in enumerate(schedule, start=1):
        aid = str(row.get("assignment_id", f"row_{rno}"))
        group_id = str(row.get("group_id", ""))
        course_id = str(row.get("course_id", ""))
        ward_id = str(row.get("ward_id", ""))
        hospital_id = str(row.get("hospital_id", ""))

        if not group_id:
            violations.append({"type": "missing_group_id", "assignment_id": aid}); continue
        if group_id not in groups:
            violations.append({"type": "unknown_group", "assignment_id": aid, "group_id": group_id}); continue
        if course_id not in courses:
            violations.append({"type": "unknown_course", "assignment_id": aid, "course_id": course_id}); continue
        if ward_id not in wards:
            violations.append({"type": "unknown_ward", "assignment_id": aid, "ward_id": ward_id}); continue
        if hospital_id not in hospitals:
            violations.append({"type": "unknown_hospital", "assignment_id": aid, "hospital_id": hospital_id}); continue

        if (ward_id, hospital_id) not in idx["B"]:
            violations.append({"type": "invalid_B_ward_hospital", "assignment_id": aid, "ward_id": ward_id, "hospital_id": hospital_id})
        if (course_id, ward_id) not in idx["Mea"]:
            violations.append({"type": "invalid_Mea_course_ward", "assignment_id": aid, "course_id": course_id, "ward_id": ward_id})
        if (group_id, course_id) not in idx["Comm"]:
            violations.append({"type": "unrequired_Comm_group_course", "assignment_id": aid, "group_id": group_id, "course_id": course_id})

        try:
            week = int(row.get("week", 0))
            days = days_from_row(row)
            expected_O = int(row.get("O_consecutive_days", idx["O"].get(course_id, 0)))
            shift = int(row.get("shift", 1))
        except Exception as exc:
            violations.append({"type": "malformed_assignment_row", "assignment_id": aid, "error": str(exc)}); continue

        if week < 1 or week > K:
            violations.append({"type": "week_out_of_range", "assignment_id": aid, "week": week})
        if not days:
            violations.append({"type": "empty_training_days", "assignment_id": aid})
        elif len(days) != expected_O or days != list(range(days[0], days[0] + len(days))):
            violations.append({"type": "non_consecutive_or_wrong_O", "assignment_id": aid, "days": days, "expected_O": expected_O})
        if days and (min(days) < 1 or max(days) > T):
            violations.append({"type": "day_out_of_range", "assignment_id": aid, "days": days})

        if shift == 2 and not idx["ne"].get((course_id, ward_id), False):
            violations.append({"type": "long_shift_not_allowed_ne", "assignment_id": aid, "course_id": course_id, "ward_id": ward_id})
        if shift == 2:
            long_shift_count[(course_id, ward_id)] += len(days)

        mem = int(row.get("mem", groups[group_id].get("mem", 1)))
        course_kind = "senior" if int(courses[course_id].get("semester", groups[group_id].get("semester", 0))) >= 7 else "junior"
        for day in days:
            if not idx["Av"].get((group_id, week, day), False):
                violations.append({"type": "group_unavailable_Av", "assignment_id": aid, "group_id": group_id, "week": week, "day": day})
            if not idx["Avb"].get((ward_id, hospital_id, week, day), False):
                violations.append({"type": "ward_unavailable_Avb", "assignment_id": aid, "ward_id": ward_id, "hospital_id": hospital_id, "week": week, "day": day})
            group_day_occ[(group_id, week, day)].append(aid)
            ward_day_course_occ[(ward_id, hospital_id, week, day)].append((course_id, aid))
            ward_day_kind_occ[(ward_id, hospital_id, week, day, course_kind)].append((course_id, aid))
            cap_load[(course_id, ward_id, hospital_id, week, day)] += mem

        segment_rows[(group_id, course_id, ward_id, hospital_id)].append(row)
        group_course_rows[(group_id, course_id)].append(row)

    # Eq. 3: each group at most one training assignment per day.
    for (group_id, week, day), aids in group_day_occ.items():
        if len(aids) > 1:
            violations.append({"type": "group_daily_overlap", "group_id": group_id, "week": week, "day": day, "assignments": aids})

    # Eqs. 12-14 / nt: ward overlap policy.
    for (ward_id, hospital_id, week, day), course_aids in ward_day_course_occ.items():
        distinct_courses = sorted({course_id for course_id, _aid in course_aids})
        if not idx["nt"].get(ward_id, False):
            if len(distinct_courses) > 1:
                violations.append({"type": "ward_overlap_forbidden_nt0", "ward_id": ward_id, "hospital_id": hospital_id, "week": week, "day": day, "courses": distinct_courses, "assignments": [aid for _course_id, aid in course_aids]})
        else:
            for (ww, hh, kk, tt, kind), kind_course_aids in ward_day_kind_occ.items():
                if (ww, hh, kk, tt) == (ward_id, hospital_id, week, day):
                    kind_courses = sorted({course_id for course_id, _aid in kind_course_aids})
                    if len(kind_courses) > 1:
                        violations.append({"type": "ward_overlap_same_stream_with_nt1", "ward_id": ward_id, "hospital_id": hospital_id, "week": week, "day": day, "stream": kind, "courses": kind_courses, "assignments": [aid for _course_id, aid in kind_course_aids]})

    # Eq. 4: capacity is counted in group members.
    for (course_id, ward_id, hospital_id, week, day), load in cap_load.items():
        cap = idx["Cap"].get((course_id, ward_id, hospital_id), 0)
        if load > cap:
            violations.append({"type": "capacity_exceeded_Cap", "course_id": course_id, "ward_id": ward_id, "hospital_id": hospital_id, "week": week, "day": day, "load": load, "capacity": cap})

    # Assignment requirements and PW logic.
    for (group_id, course_id) in sorted(idx["Comm"]):
        rows = group_course_rows.get((group_id, course_id), [])
        pw = idx["PW"].get(course_id, 1)
        if not rows:
            violations.append({"type": "missing_Comm_requirement", "group_id": group_id, "course_id": course_id})
            continue
        used_wards = sorted({r["ward_id"] for r in rows})
        if pw == 1:
            if len(used_wards) != 1:
                violations.append({"type": "PW1_must_select_exactly_one_ward", "group_id": group_id, "course_id": course_id, "used_wards": used_wards})
            scheduled_days = sum(len(days_from_row(r)) for r in rows)
            if scheduled_days < idx["Du"].get(course_id, 0):
                violations.append({"type": "PW1_insufficient_Du_days", "group_id": group_id, "course_id": course_id, "scheduled_days": scheduled_days, "required_Du": idx["Du"].get(course_id, 0)})
        else:
            required_wards = sorted([ward_id for (g, d, ward_id) in idx["Com"] if g == group_id and d == course_id])
            missing = sorted(set(required_wards) - set(used_wards))
            if missing:
                violations.append({"type": "PW0_missing_required_wards_Com", "group_id": group_id, "course_id": course_id, "missing_wards": missing})
            for ward_id in required_wards:
                ward_days = sum(len(days_from_row(r)) for r in rows if r["ward_id"] == ward_id)
                if ward_days < idx["Dur"].get((course_id, ward_id), 0):
                    violations.append({"type": "PW0_insufficient_Dur_days", "group_id": group_id, "course_id": course_id, "ward_id": ward_id, "scheduled_days": ward_days, "required_Dur": idx["Dur"].get((course_id, ward_id), 0)})

    # Continuity across weeks and tf-style fixed start day after first week.
    for (group_id, course_id, ward_id, hospital_id), rows in segment_rows.items():
        weeks = sorted(int(r["week"]) for r in rows)
        if weeks and weeks != list(range(weeks[0], weeks[-1] + 1)):
            violations.append({"type": "non_continuous_training_weeks", "group_id": group_id, "course_id": course_id, "ward_id": ward_id, "hospital_id": hospital_id, "weeks": weeks})
        expected_weeks = idx["weeks"].get((course_id, ward_id), 0)
        if expected_weeks and len(set(weeks)) < expected_weeks:
            violations.append({"type": "insufficient_weeks_dw", "group_id": group_id, "course_id": course_id, "ward_id": ward_id, "hospital_id": hospital_id, "actual_weeks": len(set(weeks)), "required_weeks": expected_weeks})
        if len(rows) > 2:
            later_starts = {int(r.get("start_day", 0)) for r in rows[1:]}
            if len(later_starts) > 1:
                violations.append({"type": "tf_fixed_start_day_violation", "group_id": group_id, "course_id": course_id, "ward_id": ward_id, "hospital_id": hospital_id, "later_start_days": sorted(later_starts)})

    for (course_id, ward_id), minimum in idx["nee"].items():
        if minimum > 0 and long_shift_count[(course_id, ward_id)] < minimum:
            violations.append({"type": "nee_minimum_long_shift_not_met", "course_id": course_id, "ward_id": ward_id, "actual": long_shift_count[(course_id, ward_id)], "required": minimum})

    by_type: dict[str, int] = defaultdict(int)
    for violation in violations:
        by_type[violation["type"]] += 1
    warnings_by_type: dict[str, int] = defaultdict(int)
    for warning in warnings:
        warnings_by_type[warning["type"]] += 1
    return {
        "feasible": len(violations) == 0,
        "violation_count": len(violations),
        "violations_by_type": dict(sorted(by_type.items())),
        "violations": violations,
        "warning_count": len(warnings),
        "warnings_by_type": dict(sorted(warnings_by_type.items())),
        "warnings": warnings,
        "schedule_summary": summarize_schedule(instance, schedule),
    }

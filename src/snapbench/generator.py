from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from .complexity import compute_complexity
from .feasibility import check_schedule
from .models import BenchmarkProfile, GeneratedInstance
from .profiles import get_profile


def _id(prefix: str, n: int) -> str:
    return f"{prefix}{n:03d}"


def _sample_k(rng: random.Random, items: list[str], k: int) -> list[str]:
    if k >= len(items):
        return list(items)
    return rng.sample(items, k)


REALISTIC_DU_DAYS = [6, 8, 10, 12, 16, 18, 20, 24]


def _is_pareto_mode(profile: BenchmarkProfile) -> bool:
    return getattr(profile, "tradeoff_mode", "standard") == "pareto"


def _divisible_du(rng: random.Random, min_du: int, max_du: int, o: int) -> int:
    """Choose a realistic Du in days.

    The original instance data should not contain very small durations such as 4.
    We therefore sample from a small realistic duration set and prefer values that
    are divisible by O(d), because Dur(d,w) and weeks(d,w) are cleaner when Du/O
    is integral.
    """
    lo = max(6, min_du)
    hi = max(lo, max_du)
    candidates = [x for x in REALISTIC_DU_DAYS if lo <= x <= hi]
    divisible = [x for x in candidates if x % max(1, o) == 0]
    if divisible:
        return rng.choice(divisible)
    if candidates:
        return rng.choice(candidates)
    # Conservative fallback; should rarely be used.
    return max(6, int(math.ceil(lo / max(1, o)) * max(1, o)))


def _weeks_for_course(course: dict[str, Any]) -> int:
    return int(math.ceil(int(course["Du_days"]) / max(1, int(course["O_consecutive_days"]))))


def _lower_du_candidate(current_du: int, O: int) -> int | None:
    candidates = [x for x in REALISTIC_DU_DAYS if x < current_du and x >= 6 and x % max(1, O) == 0]
    return max(candidates) if candidates else None


def _balance_semester_course_loads(courses: list[dict[str, Any]], max_weeks: int = 14) -> None:
    """Keep total clinical weeks for each semester within the 16-week horizon.

    Since all groups of a semester require the same courses and share the same
    availability days, the sum of Du/O over that semester must be controlled.
    """
    by_semester: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for c in courses:
        by_semester[int(c["semester"])].append(c)
    for sem, sem_courses in by_semester.items():
        guard = 0
        while sum(_weeks_for_course(c) for c in sem_courses) > max_weeks and guard < 100:
            guard += 1
            sem_courses.sort(key=lambda c: (_weeks_for_course(c), int(c["Du_days"])), reverse=True)
            changed = False
            for c in sem_courses:
                lower = _lower_du_candidate(int(c["Du_days"]), int(c["O_consecutive_days"]))
                if lower is not None:
                    c["Du_days"] = int(lower)
                    # If the course becomes a single O-block, do not force all Mea wards.
                    if _weeks_for_course(c) < 2:
                        c["PW"] = 1
                    changed = True
                    break
            if not changed:
                break


def _make_hospitals_wards(profile: BenchmarkProfile, rng: random.Random) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    hospitals = [{"hospital_id": _id("H", h), "h_index": h, "name": f"Hospital {h}"} for h in range(1, profile.hospitals + 1)]
    wards = [{"ward_id": _id("W", w), "w_index": w, "name": f"Ward {w}"} for w in range(1, profile.wards + 1)]

    # B(w,h): every hospital has at least one ward and every ward exists in at least one hospital.
    B: set[tuple[str, str]] = set()
    for w_idx, ward in enumerate(wards):
        # Round-robin assignment guarantees every ward has a hospital; later add random duplicate hospitals.
        h = hospitals[w_idx % len(hospitals)]
        B.add((ward["ward_id"], h["hospital_id"]))
    for h_idx, hospital in enumerate(hospitals):
        # Guarantees every hospital has at least one ward.
        w = wards[h_idx % len(wards)]
        B.add((w["ward_id"], hospital["hospital_id"]))
    for ward in wards:
        for hospital in hospitals:
            if (ward["ward_id"], hospital["hospital_id"]) not in B and rng.random() < (0.55 if _is_pareto_mode(profile) else (0.18 if profile.name in {"tiny", "snap_s"} else 0.35)):
                B.add((ward["ward_id"], hospital["hospital_id"]))

    ward_hospital_membership = [
        {"ward_id": w, "hospital_id": h, "exists": True}
        for w, h in sorted(B)
    ]

    # Backward-compatible primary hospital for older algorithms/readers.
    first_hospital_by_ward: dict[str, str] = {}
    for w, h in sorted(B):
        first_hospital_by_ward.setdefault(w, h)
    for ward in wards:
        ward["hospital_id"] = first_hospital_by_ward[ward["ward_id"]]

    return hospitals, wards, ward_hospital_membership


def _semester_stream(semester: int) -> str:
    """Model-level stream used only internally for nt(w) overlap logic."""
    return "senior" if int(semester) >= 7 else "junior"


def _choose_active_semesters(profile: BenchmarkProfile, rng: random.Random) -> list[int]:
    """Select semester cohorts represented in an instance.

    Courses are semester-specific. Therefore all groups in the same semester share
    exactly the same course set and the same weekly availability pattern.
    """
    junior_pool = [2, 3, 4, 5, 6]
    senior_pool = [7, 8]
    max_active = max(1, min(profile.courses, len(junior_pool) + len(senior_pool)))
    senior_slots = 0
    if profile.senior_ratio > 0 and max_active > 1:
        senior_slots = min(len(senior_pool), max(1, round(max_active * profile.senior_ratio)))
    junior_slots = max(1, max_active - senior_slots)
    active = junior_pool[:junior_slots] + senior_pool[:senior_slots]
    # Keep ordering stable for readability, but rotate a little with the seed so profiles vary.
    if len(active) > 2 and rng.random() < 0.35:
        rng.shuffle(active)
        active = sorted(active)
    return active


def _make_groups_courses(profile: BenchmarkProfile, rng: random.Random) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    active_semesters = _choose_active_semesters(profile, rng)

    groups: list[dict[str, Any]] = []
    # Distribute groups across active semesters. Groups in the same semester are equivalent
    # regarding curriculum and availability; they differ only by mem.
    semester_cycle = list(active_semesters)
    for i in range(1, profile.groups + 1):
        semester = semester_cycle[(i - 1) % len(semester_cycle)]
        groups.append({
            "group_id": _id("I", i),
            "i_index": i,
            "semester": int(semester),
            "mem": rng.randint(profile.min_group_size, profile.max_group_size),
        })

    courses: list[dict[str, Any]] = []
    # Distribute courses across semesters. This makes Comm(i,d) semester-driven: all groups
    # of a semester require the same courses, and junior/senior semesters never share a course.
    for d in range(1, profile.courses + 1):
        semester = active_semesters[(d - 1) % len(active_semesters)]
        senior = semester >= 7
        if senior:
            o_min = max(2, profile.min_consecutive_days)
            o_max = min(6, profile.max_consecutive_days)
        else:
            # Lower semesters usually have more theoretical university days, so their
            # clinical consecutive-day windows are not generated at the senior maximum.
            o_min = max(2, profile.min_consecutive_days)
            o_max = min(4, profile.max_consecutive_days)
        O = rng.randint(o_min, max(o_min, o_max))
        Du = _divisible_du(rng, max(6, profile.min_du_days), max(6, profile.max_du_days), O)
        # If Du/O is one block, using PW=0 with multiple wards is conceptually misleading.
        # Such courses are generated as PW=1 so one ward is selected for the whole course.
        max_blocks = max(1, Du // O)
        effective_pw_probability = max(profile.pw_probability, 0.85) if _is_pareto_mode(profile) and profile.wards >= 2 else profile.pw_probability
        PW = 1 if max_blocks < 2 else (1 if rng.random() < effective_pw_probability else 0)
        courses.append({
            "course_id": _id("D", d),
            "d_index": d,
            "semester": int(semester),
            "Du_days": int(Du),
            "O_consecutive_days": int(O),
            "PW": int(PW),
            "requires_consecutive_days": True,
        })
    _balance_semester_course_loads(courses, max_weeks=max(10, profile.weeks - 2))
    return groups, courses


def _make_comm(profile: BenchmarkProfile, rng: random.Random, groups: list[dict[str, Any]], courses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate Comm(i,d) strictly by semester.

    All groups in the same semester have the same required courses. This matches the
    real nursing curriculum logic: groups from one semester attend the same theoretical
    timetable and have the same clinical availability pattern.
    """
    comm: list[dict[str, Any]] = []
    courses_by_semester: dict[int, list[str]] = defaultdict(list)
    for c in courses:
        courses_by_semester[int(c["semester"])].append(c["course_id"])
    for g in groups:
        required_courses = set(courses_by_semester.get(int(g["semester"]), []))
        for c in courses:
            comm.append({
                "group_id": g["group_id"],
                "course_id": c["course_id"],
                "required": c["course_id"] in required_courses,
            })
    return comm


def _make_mea(profile: BenchmarkProfile, rng: random.Random, courses: list[dict[str, Any]], wards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate Mea(d,w), while keeping PW/Du/O consistent.

    In pareto-friendly mode, PW=1 courses receive several realistic alternatives.
    The first selected ward is labeled as ``primary`` and the remaining selected
    wards are labeled as ``alternative``.  The role is metadata only; the GAMS
    model can ignore it.  It is used by the generator to create capacity contrast:
    primary wards are slightly tighter, alternative wards are slightly more
    relieving.  This creates the intended data-level conflict: fewer wards tends
    to increase completion time; more wards tends to reduce completion time.
    """
    mea: list[dict[str, Any]] = []
    ward_ids = [w["ward_id"] for w in wards]
    pareto = _is_pareto_mode(profile)
    target = max(profile.min_wards_per_course, round(profile.target_mea_density * len(wards)))
    for c in courses:
        blocks = max(1, int(c["Du_days"]) // int(c["O_consecutive_days"]))
        if int(c["PW"]) == 0 and blocks < 2:
            c["PW"] = 1

        if int(c["PW"]) == 1:
            max_k = min(profile.max_wards_per_course, len(wards))
            min_k = max(1, profile.min_wards_per_course)
            if pareto and len(wards) >= 2:
                min_k = max(2, min_k)
                max_k = max(min(max_k, len(wards)), min(len(wards), 3))
            mode = min(max_k, max(min_k, target))
        else:
            # At least two wards, but never more than the number of O-day blocks in Du.
            max_k = min(max(2, profile.max_wards_per_course), len(wards), blocks)
            if max_k < 2:
                c["PW"] = 1
                max_k = min(profile.max_wards_per_course, len(wards))
                min_k = max(1, profile.min_wards_per_course)
                if pareto and len(wards) >= 2:
                    min_k = max(2, min_k)
                    max_k = max(min(max_k, len(wards)), min(len(wards), 3))
                mode = min(max_k, max(min_k, target))
            else:
                min_k = 2
                mode = min(max_k, max(2, target))

        k = int(round(rng.triangular(min_k, max_k, mode)))
        k = max(min_k, min(k, len(wards), max_k))
        chosen_list = _sample_k(rng, ward_ids, k)
        # Stable deterministic ordering improves readability of primary/alternative roles.
        chosen_list = sorted(chosen_list)
        chosen = set(chosen_list)
        primary = chosen_list[0] if chosen_list else None
        for ward_id in ward_ids:
            defined = ward_id in chosen
            role = "none"
            if defined:
                role = "primary" if ward_id == primary else "alternative"
            mea.append({"course_id": c["course_id"], "ward_id": ward_id, "defined": defined, "role": role})
    return mea

def _allocate_pw0_durations(total_du: int, O: int, ward_ids: list[str], rng: random.Random) -> dict[str, int]:
    """Split Du across all selected wards for PW=0 courses.

    Dur(d,w) values are multiples of O(d) and sum exactly to Du(d).
    """
    units = max(1, total_du // O)
    n = len(ward_ids)
    if n > units:
        raise ValueError("PW=0 ward count cannot exceed Du/O blocks")
    parts = [1] * n
    remaining = units - n
    for _ in range(remaining):
        parts[rng.randrange(n)] += 1
    rng.shuffle(parts)
    return {w: parts[i] * O for i, w in enumerate(ward_ids)}


def _make_dependent_parameters(
    profile: BenchmarkProfile,
    rng: random.Random,
    groups: list[dict[str, Any]],
    courses: list[dict[str, Any]],
    wards: list[dict[str, Any]],
    hospitals: list[dict[str, Any]],
    B: list[dict[str, Any]],
    comm: list[dict[str, Any]],
    mea: list[dict[str, Any]],
) -> dict[str, Any]:
    B_set = {(x["ward_id"], x["hospital_id"]) for x in B if x.get("exists", True)}
    mea_by_course: dict[str, list[str]] = defaultdict(list)
    course_ward_role: dict[tuple[str, str], str] = {}
    for x in mea:
        if x["defined"]:
            mea_by_course[x["course_id"]].append(x["ward_id"])
            course_ward_role[(x["course_id"], x["ward_id"])] = str(x.get("role", "primary"))
    course_by_id = {c["course_id"]: c for c in courses}
    comm_required = {(x["group_id"], x["course_id"]) for x in comm if x["required"]}
    groups_by_id = {g["group_id"]: g for g in groups}

    dur: list[dict[str, Any]] = []
    weeks_dw: list[dict[str, Any]] = []
    weeks_lookup: dict[tuple[str, str], int] = {}
    com_idw: list[dict[str, Any]] = []
    eb: list[dict[str, Any]] = []
    ne: list[dict[str, Any]] = []
    nee: list[dict[str, Any]] = []

    # Dur and weeks. For PW=0, Dur values across the defined wards sum to Du.
    dur_lookup: dict[tuple[str, str], int] = {}
    for c in courses:
        c_id = c["course_id"]
        O = int(c["O_consecutive_days"])
        Du = int(c["Du_days"])
        wards_for_course = list(mea_by_course[c_id])
        pw0_allocation: dict[str, int] = {}
        if int(c["PW"]) == 0:
            pw0_allocation = _allocate_pw0_durations(Du, O, wards_for_course, rng)
        for w in wards:
            w_id = w["ward_id"]
            defined = w_id in wards_for_course
            if not defined:
                dur_days = 0
            elif int(c["PW"]) == 1:
                dur_days = Du
            else:
                dur_days = pw0_allocation[w_id]
            week_count = int(math.ceil(dur_days / O)) if dur_days > 0 else 0
            dur_lookup[(c_id, w_id)] = int(dur_days)
            weeks_lookup[(c_id, w_id)] = int(week_count)
            dur.append({"course_id": c_id, "ward_id": w_id, "Dur_days": int(dur_days)})
            weeks_dw.append({"course_id": c_id, "ward_id": w_id, "weeks": int(week_count)})

            long_allowed = False
            if defined and int(c.get("semester", 0)) >= 7 and rng.random() < profile.allow_long_shift_probability:
                long_allowed = True
            ne.append({"course_id": c_id, "ward_id": w_id, "allowed": bool(long_allowed)})
            nee.append({"course_id": c_id, "ward_id": w_id, "minimum_long_shifts": 0})

            for h in hospitals:
                eb.append({
                    "course_id": c_id,
                    "ward_id": w_id,
                    "hospital_id": h["hospital_id"],
                    "eligible": bool(defined and (w_id, h["hospital_id"]) in B_set),
                })

        for g in groups:
            for w_id in [w["ward_id"] for w in wards]:
                # com(i,d,w): course d is defined in ward w for group i.
                # It is populated for both PW=0 and PW=1 as Comm(i,d) * Mea(d,w).
                com_idw.append({
                    "group_id": g["group_id"],
                    "course_id": c_id,
                    "ward_id": w_id,
                    "required": bool((g["group_id"], c_id) in comm_required and w_id in wards_for_course),
                })

    # nt(w): zero for small/MIP-oriented profiles; some allowed overlaps for larger/harder profiles.
    nt: list[dict[str, Any]] = []
    unique_need_counter: dict[str, int] = defaultdict(int)
    for c in courses:
        ws = mea_by_course[c["course_id"]]
        if len(ws) == 1:
            unique_need_counter[ws[0]] += 1
    for w in wards:
        allow = False
        if profile.name not in {"tiny", "snap_s"}:
            allow = rng.random() < profile.nt_probability or unique_need_counter[w["ward_id"]] >= 2
        nt.append({"ward_id": w["ward_id"], "interference_allowed": bool(allow)})

    # Av(i,t,k): all groups in the same semester share the same available days.
    max_o_by_semester: dict[int, int] = defaultdict(lambda: 2)
    for c in courses:
        sem = int(c["semester"])
        max_o_by_semester[sem] = max(max_o_by_semester[sem], int(c["O_consecutive_days"]))
    available_days_by_semester: dict[int, set[int]] = {}
    for sem, max_o in max_o_by_semester.items():
        max_o = min(profile.days_per_week, max(2, max_o))
        start = rng.randint(1, profile.days_per_week - max_o + 1)
        available_days_by_semester[sem] = set(range(start, start + max_o))

    av: list[dict[str, Any]] = []
    for g in groups:
        available_days = available_days_by_semester[int(g["semester"])]
        for k in range(1, profile.weeks + 1):
            for t in range(1, profile.days_per_week + 1):
                av.append({"group_id": g["group_id"], "week": k, "day": t, "available": t in available_days})

    # Avb(w,h,t,k): set to one to avoid artificial infeasibility, as requested.
    avb: list[dict[str, Any]] = []
    for w_id, h_id in sorted(B_set):
        for k in range(1, profile.weeks + 1):
            for t in range(1, profile.days_per_week + 1):
                avb.append({"ward_id": w_id, "hospital_id": h_id, "week": k, "day": t, "available": True})

    # Cap(d,w,h): provide a row for every d,w,h combination. Invalid combinations receive zero.
    # For valid combinations, capacity is generated independently for every hospital that
    # owns ward w. The value is demand-aware and never defaults to 1 merely because the
    # planted schedule selected a different hospital. Capacities may be equal across
    # hospitals, but equality is not forced.
    cap: list[dict[str, Any]] = []
    hospitals_by_ward: dict[str, list[str]] = defaultdict(list)
    for w_id, h_id in sorted(B_set):
        hospitals_by_ward[w_id].append(h_id)

    for c in courses:
        c_id = c["course_id"]
        group_mems = [groups_by_id[g_id]["mem"] for (g_id, d_id) in comm_required if d_id == c_id]
        if group_mems:
            max_group_mem = max(group_mems)
            total_members = sum(group_mems)
            group_count = len(group_mems)
        else:
            max_group_mem = int(profile.min_group_size)
            total_members = max_group_mem
            group_count = 1

        for w in wards:
            w_id = w["ward_id"]
            valid_hospitals_for_ward = hospitals_by_ward.get(w_id, [])
            num_valid_hospitals = max(1, len(valid_hospitals_for_ward))
            for h in hospitals:
                h_id = h["hospital_id"]
                eligible = (w_id, h_id) in B_set and dur_lookup.get((c_id, w_id), 0) > 0
                if eligible:
                    week_count = max(1, weeks_lookup[(c_id, w_id)])
                    sequential_slots = max(1, profile.weeks // week_count)
                    total_slot_count = max(1, sequential_slots * num_valid_hospitals)

                    # Minimum feasible capacity for a hospital/ward/course must at least
                    # accommodate one full student group. When demand is high relative
                    # to the number of sequential slots, raise the baseline accordingly.
                    demand_based_cap = int(math.ceil(total_members / total_slot_count))
                    simultaneous_group_pressure = int(math.ceil(group_count / total_slot_count))
                    baseline = max(max_group_mem, demand_based_cap, simultaneous_group_pressure * max_group_mem)

                    if _is_pareto_mode(profile):
                        role = course_ward_role.get((c_id, w_id), "primary")
                        if role == "primary":
                            # Bottleneck/stability option: feasible but tighter.
                            slack_upper = max(1, int(math.ceil(0.12 * baseline)))
                            variation = rng.randint(0, slack_upper)
                            base_cap = baseline + variation
                        else:
                            # Relief/fast option: more capacity, encouraging shorter schedules
                            # at the cost of using more ward alternatives.
                            slack_upper = max(3, int(math.ceil(0.75 * baseline)))
                            variation = rng.randint(max(1, int(math.ceil(0.20 * baseline))), slack_upper)
                            base_cap = baseline + variation
                    else:
                        if profile.name in {"snap_tight", "snap_sparse"}:
                            slack_upper = max(1, int(math.ceil(0.25 * baseline)))
                        elif profile.name in {"snap_hard", "snap_l"}:
                            slack_upper = max(2, int(math.ceil(0.50 * baseline)))
                        else:
                            slack_upper = max(2, int(math.ceil(0.35 * baseline)))
                        # Hospital-specific capacity variation. This is deliberately independent
                        # for each valid (d,w,h), so hospitals sharing the same ward need not
                        # have equal capacities, but they are all meaningful positive capacities.
                        variation = rng.randint(0, slack_upper)
                        base_cap = baseline + variation
                else:
                    base_cap = 0
                cap.append({"course_id": c_id, "ward_id": w_id, "hospital_id": h_id, "capacity": int(base_cap)})

    return {
        "Dur": dur,
        "weeks": weeks_dw,
        "Com": com_idw,
        "Eb": eb,
        "ne": ne,
        "nee": nee,
        "nt": nt,
        "Av": av,
        "Avb": avb,
        "Cap": cap,
    }


def _hospital_options(B: list[dict[str, Any]], ward_id: str) -> list[str]:
    return [x["hospital_id"] for x in B if x["ward_id"] == ward_id and x.get("exists", True)]


def _plant_model_schedule(
    profile: BenchmarkProfile,
    rng: random.Random,
    groups: list[dict[str, Any]],
    courses: list[dict[str, Any]],
    wards: list[dict[str, Any]],
    B: list[dict[str, Any]],
    comm: list[dict[str, Any]],
    mea: list[dict[str, Any]],
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    group_by_id = {g["group_id"]: g for g in groups}
    course_by_id = {c["course_id"]: c for c in courses}
    mea_by_course: dict[str, list[str]] = defaultdict(list)
    for x in mea:
        if x["defined"]:
            mea_by_course[x["course_id"]].append(x["ward_id"])
    dur_lookup = {(x["course_id"], x["ward_id"]): int(x["Dur_days"]) for x in params["Dur"]}
    weeks_lookup = {(x["course_id"], x["ward_id"]): int(x["weeks"]) for x in params["weeks"]}
    av_lookup = {(x["group_id"], int(x["week"]), int(x["day"])): bool(x["available"]) for x in params["Av"]}
    nt_lookup = {x["ward_id"]: bool(x["interference_allowed"]) for x in params["nt"]}

    group_occ: set[tuple[str, int, int]] = set()
    # ward_occ_by_kind: if nt=0 no overlap; if nt=1 one junior and one senior course can coexist.
    ward_occ_total: dict[tuple[str, str, int, int], list[str]] = defaultdict(list)
    ward_occ_kind: dict[tuple[str, str, int, int, str], list[str]] = defaultdict(list)
    # Reuse the same planted segment for the same course-ward across groups when possible.
    # This mirrors cohort scheduling and avoids artificial conflicts created by planting
    # identical course requirements at unrelated random times.
    course_segment_templates: dict[tuple[str, str], tuple[str, int, int, int, int]] = {}
    schedule: list[dict[str, Any]] = []
    assignment_no = 1

    # Hard-first order: courses with PW=0/more weeks and groups with larger mem.
    required_pairs = [(x["group_id"], x["course_id"]) for x in comm if x["required"]]
    # Semester-first ordering is intentional. The first group of a semester creates
    # coherent course templates; subsequent groups in that semester reuse them.
    # Sorting by mem first, as in earlier versions, created incompatible templates.
    required_pairs.sort(key=lambda p: (
        int(group_by_id[p[0]]["semester"]),
        p[0],
        int(course_by_id[p[1]]["d_index"]),
        int(course_by_id[p[1]]["PW"]),
    ))

    for g_id, d_id in required_pairs:
        course = course_by_id[d_id]
        group = group_by_id[g_id]
        if int(course["PW"]) == 1:
            # For PW=1, choose one of the defined wards; prefer one with more hospital options.
            candidates = list(mea_by_course[d_id])
            rng.shuffle(candidates)
            candidates.sort(key=lambda w: -len(_hospital_options(B, w)))
            ward_sequence_options = [[w] for w in candidates]
        else:
            # For PW=0, the group must visit all wards defined in Mea(d,w).
            ward_sequence = list(mea_by_course[d_id])
            rng.shuffle(ward_sequence)
            ward_sequence_options = [ward_sequence]

        placed_whole_requirement = False
        last_error = None
        for ward_sequence in ward_sequence_options:
            temp_rows: list[dict[str, Any]] = []
            temp_group_occ = set(group_occ)
            temp_ward_occ_total = {k: list(v) for k, v in ward_occ_total.items()}
            temp_ward_occ_kind = {k: list(v) for k, v in ward_occ_kind.items()}
            feasible_sequence = True
            for w_id in ward_sequence:
                O = int(course["O_consecutive_days"])
                wk_count = max(1, weeks_lookup[(d_id, w_id)])
                h_options = _hospital_options(B, w_id)
                if not h_options:
                    feasible_sequence = False
                    last_error = f"No hospital for ward {w_id}"
                    break
                placed_segment = False

                # First try an existing template for this course-ward. If a previous group
                # already received this course segment, following groups should normally be
                # able to attend the same course in the same ward/time; capacity is later
                # raised to the planted load.
                tpl = course_segment_templates.get((d_id, w_id))
                if tpl is not None:
                    h_id, start_week, start_day, tpl_wk_count, tpl_O = tpl
                    days = list(range(start_day, start_day + tpl_O))
                    ok = tpl_wk_count == wk_count and tpl_O == O
                    if ok:
                        for offset in range(wk_count):
                            week = start_week + offset
                            for day in days:
                                if not av_lookup.get((g_id, week, day), False):
                                    ok = False; break
                                if (g_id, week, day) in temp_group_occ:
                                    ok = False; break
                                total_key = (w_id, h_id, week, day)
                                kind_key = (w_id, h_id, week, day, _semester_stream(int(course["semester"])))
                                if not nt_lookup.get(w_id, False):
                                    if any(existing_course != d_id for existing_course in temp_ward_occ_total.get(total_key, [])):
                                        ok = False; break
                                else:
                                    if any(existing_course != d_id for existing_course in temp_ward_occ_kind.get(kind_key, [])):
                                        ok = False; break
                            if not ok:
                                break
                    if ok:
                        for offset in range(wk_count):
                            week = start_week + offset
                            row = {
                                "assignment_id": _id("A", assignment_no),
                                "group_id": g_id,
                                "course_id": d_id,
                                "ward_id": w_id,
                                "hospital_id": h_id,
                                "week": week,
                                "start_week": start_week,
                                "start_day": start_day,
                                "O_consecutive_days": O,
                                "segment_Dur_days": int(dur_lookup[(d_id, w_id)]),
                                "segment_weeks": int(wk_count),
                                "days": days,
                                "shift": 1,
                                "mem": int(group["mem"]),
                                "PW": int(course["PW"]),
                            }
                            temp_rows.append(row)
                            assignment_no += 1
                            for day in days:
                                temp_group_occ.add((g_id, week, day))
                                total_key = (w_id, h_id, week, day)
                                kind_key = (w_id, h_id, week, day, _semester_stream(int(course["semester"])))
                                temp_ward_occ_total.setdefault(total_key, []).append(d_id)
                                temp_ward_occ_kind.setdefault(kind_key, []).append(d_id)
                        placed_segment = True

                h_try_order = list(h_options)
                rng.shuffle(h_try_order)

                # Try each valid hospital for this ward, then sequential weeks/start days.
                # The earlier version chose one random hospital and could falsely fail.
                possible_starts = list(range(1, profile.weeks - wk_count + 2))
                rng.shuffle(possible_starts)
                for h_id in h_try_order:
                    if placed_segment:
                        break
                    for start_week in possible_starts:
                        day_starts = list(range(1, profile.days_per_week - O + 2))
                        rng.shuffle(day_starts)
                        for start_day in day_starts:
                            days = list(range(start_day, start_day + O))
                            ok = True
                            for offset in range(wk_count):
                                week = start_week + offset
                                for day in days:
                                    if not av_lookup.get((g_id, week, day), False):
                                        ok = False; break
                                    if (g_id, week, day) in temp_group_occ:
                                        ok = False; break
                                    total_key = (w_id, h_id, week, day)
                                    kind_key = (w_id, h_id, week, day, _semester_stream(int(course["semester"])))
                                    if not nt_lookup.get(w_id, False):
                                        # Ward-use constraints limit distinct courses, not the number of groups
                                        # of the same course sharing a ward within capacity.
                                        if any(existing_course != d_id for existing_course in temp_ward_occ_total.get(total_key, [])):
                                            ok = False; break
                                    else:
                                        # If interference is allowed, junior and senior streams may coexist,
                                        # but within the same stream only one distinct course is allowed.
                                        if any(existing_course != d_id for existing_course in temp_ward_occ_kind.get(kind_key, [])):
                                            ok = False; break
                                if not ok:
                                    break
                            if not ok:
                                continue

                            # Commit segment rows week by week.
                            for offset in range(wk_count):
                                week = start_week + offset
                                row = {
                                    "assignment_id": _id("A", assignment_no),
                                    "group_id": g_id,
                                    "course_id": d_id,
                                    "ward_id": w_id,
                                    "hospital_id": h_id,
                                    "week": week,
                                    "start_week": start_week,
                                    "start_day": start_day,
                                    "O_consecutive_days": O,
                                    "segment_Dur_days": int(dur_lookup[(d_id, w_id)]),
                                    "segment_weeks": int(wk_count),
                                    "days": days,
                                    "shift": 1,
                                    "mem": int(group["mem"]),
                                    "PW": int(course["PW"]),
                                }
                                temp_rows.append(row)
                                assignment_no += 1
                                for day in days:
                                    temp_group_occ.add((g_id, week, day))
                                    total_key = (w_id, h_id, week, day)
                                    kind_key = (w_id, h_id, week, day, _semester_stream(int(course["semester"])))
                                    temp_ward_occ_total.setdefault(total_key, []).append(d_id)
                                    temp_ward_occ_kind.setdefault(kind_key, []).append(d_id)
                            course_segment_templates.setdefault((d_id, w_id), (h_id, start_week, start_day, wk_count, O))
                            placed_segment = True
                            break
                        if placed_segment:
                            break
                if not placed_segment:
                    feasible_sequence = False
                    last_error = f"Could not place segment {g_id}-{d_id}-{w_id}"
                    break

            if feasible_sequence:
                schedule.extend(temp_rows)
                group_occ = temp_group_occ
                ward_occ_total = defaultdict(list, temp_ward_occ_total)
                ward_occ_kind = defaultdict(list, temp_ward_occ_kind)
                placed_whole_requirement = True
                break

        if not placed_whole_requirement:
            raise RuntimeError(last_error or f"Could not plant requirement {g_id}-{d_id}")

    return schedule


def _raise_capacity_to_planted_load(params: dict[str, Any], schedule: list[dict[str, Any]]) -> None:
    # Load is in number of group members, matching Equation (4): sum Y * mem <= Cap.
    # Important: capacity must stay zero for ineligible (d,w,h) combinations.
    # Otherwise the Excel sheet suggests that a course can be taught in a ward/hospital
    # even when Eb(d,w,h)=0. Earlier v1.4.0 incorrectly raised every Cap row to at
    # least one; v1.4.1 keeps Cap consistent with Eb/Mea/B, and v1.4.3 makes all eligible hospital capacities demand-aware instead of leaving non-selected hospitals at a default value of 1.
    load: dict[tuple[str, str, str, int, int], int] = defaultdict(int)
    for row in schedule:
        for day in row["days"]:
            load[(row["course_id"], row["ward_id"], row["hospital_id"], int(row["week"]), int(day))] += int(row.get("mem", 1))
    max_load_by_cwh: dict[tuple[str, str, str], int] = defaultdict(int)
    for (d, w, h, _k, _t), val in load.items():
        max_load_by_cwh[(d, w, h)] = max(max_load_by_cwh[(d, w, h)], val)

    eligible = {
        (row["course_id"], row["ward_id"], row["hospital_id"])
        for row in params.get("Eb", [])
        if bool(row.get("eligible", False))
    }
    for row in params["Cap"]:
        key = (row["course_id"], row["ward_id"], row["hospital_id"])
        if key not in eligible:
            row["capacity"] = 0
        else:
            row["capacity"] = max(int(row["capacity"]), int(max_load_by_cwh.get(key, 0)), 1)



def _compute_pareto_potential(instance: dict[str, Any]) -> dict[str, Any]:
    """Proxy screen for whether an instance has data-level Pareto potential.

    This is not a solver. It checks whether the instance contains enough real
    alternatives and whether those alternatives have capacity contrast. It is a
    practical acceptance test for generated benchmark data.
    """
    mp = instance.get("model_parameters", {})
    mea = mp.get("Mea", [])
    cap = mp.get("Cap", [])
    courses = instance.get("courses", [])

    selected_by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in mea:
        if row.get("defined"):
            selected_by_course[row["course_id"]].append(row)

    pw_by_course = {row["course_id"]: int(row.get("PW", 1)) for row in mp.get("PW", [])}
    candidate_courses = [c for c in courses if pw_by_course.get(c["course_id"], 1) == 1]
    multi_option = [c for c in candidate_courses if len(selected_by_course.get(c["course_id"], [])) >= 2]

    cap_by_cw: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in cap:
        value = int(row.get("capacity", 0))
        if value > 0:
            cap_by_cw[(row["course_id"], row["ward_id"])].append(value)

    contrast_count = 0
    contrast_values: list[float] = []
    for c in multi_option:
        c_id = c["course_id"]
        ward_caps = []
        for m in selected_by_course.get(c_id, []):
            vals = cap_by_cw.get((c_id, m["ward_id"]), [])
            if vals:
                ward_caps.append(sum(vals) / len(vals))
        if len(ward_caps) >= 2:
            mn = min(ward_caps)
            mx = max(ward_caps)
            if mn > 0:
                contrast = mx / mn
                contrast_values.append(contrast)
                if contrast >= 1.15:
                    contrast_count += 1

    eligible_courses = len(candidate_courses)
    multi_option_ratio = len(multi_option) / max(1, eligible_courses)
    contrast_ratio = contrast_count / max(1, len(multi_option))
    accepted = eligible_courses == 0 or (multi_option_ratio >= 0.50 and contrast_ratio >= 0.35)
    return {
        "accepted": bool(accepted),
        "pw1_courses": int(eligible_courses),
        "pw1_multi_option_courses": int(len(multi_option)),
        "multi_option_ratio": round(multi_option_ratio, 4),
        "capacity_contrast_courses": int(contrast_count),
        "capacity_contrast_ratio": round(contrast_ratio, 4),
        "mean_capacity_contrast": round(sum(contrast_values) / len(contrast_values), 4) if contrast_values else 0,
        "interpretation": "proxy screen only; not a mathematical proof of Pareto-front size",
    }

def generate_instance_from_profile(
    profile: BenchmarkProfile,
    instance_index: int,
    base_seed: int,
    series_name: str = "snap-math-model-taillard-inspired-v1.7.0",
    max_attempts: int = 30,
) -> GeneratedInstance:
    """Generate a SNAP benchmark instance from an explicit BenchmarkProfile.

    This function is used both for named built-in profiles and for ad-hoc
    custom profiles supplied through the CLI. Fixed time constants are still
    s=2, t=6, k=16.
    """

    instance_seed = int(base_seed) + int(instance_index) * 1009

    last_error = None
    for attempt in range(1, max_attempts + 1):
        rng = random.Random(instance_seed + attempt - 1)
        try:
            hospitals, wards, B = _make_hospitals_wards(profile, rng)
            groups, courses = _make_groups_courses(profile, rng)
            comm = _make_comm(profile, rng, groups, courses)
            mea = _make_mea(profile, rng, courses, wards)
            params = _make_dependent_parameters(profile, rng, groups, courses, wards, hospitals, B, comm, mea)
            schedule = _plant_model_schedule(profile, rng, groups, courses, wards, B, comm, mea, params)
            _raise_capacity_to_planted_load(params, schedule)
        except RuntimeError as exc:
            last_error = exc
            continue

        instance_id = f"{profile.name}_{instance_index:03d}"
        instance: dict[str, Any] = {
            "metadata": {
                "instance_id": instance_id,
                "series_name": series_name,
                "format_version": "1.7.0",
                "generator": "SNAP MIP-aligned Taillard-inspired benchmark generator",
                "generator_note": (
                    "This generator follows the paper's mathematical-model parameter structure. "
                    "The time horizon is fixed at s=2 shifts, t=6 days/week, k=16 weeks. "
                    "B, Du, O, Mea and Comm are generated as independent data; Dur, weeks, "
                    "Cap, com(i,d,w), Av, Avb, ne, nt and nee are derived according to the SNAP model."
                ),
                "profile": profile.name,
                "base_seed": int(base_seed),
                "instance_seed": int(instance_seed + attempt - 1),
                "attempt": attempt,
                "rng": "Python random.Random / Mersenne Twister",
            },
            "time": {
                "shifts": profile.shifts,
                "days_per_week": profile.days_per_week,
                "weeks": profile.weeks,
                "shift_durations_hours": {"1": profile.standard_shift_hours, "2": profile.long_shift_hours},
            },
            "sets": {"I": profile.groups, "D": profile.courses, "W": profile.wards, "H": profile.hospitals, "S": 2, "T": 6, "K": 16},
            "groups": groups,
            "hospitals": hospitals,
            "wards": wards,
            "courses": courses,
            "model_parameters": {
                "B": B,
                "Du": [{"course_id": c["course_id"], "Du_days": int(c["Du_days"])} for c in courses],
                "O": [{"course_id": c["course_id"], "O_consecutive_days": int(c["O_consecutive_days"])} for c in courses],
                "PW": [{"course_id": c["course_id"], "PW": int(c["PW"])} for c in courses],
                "Mea": mea,
                "Comm": comm,
                **params,
            },
            "policy": {
                "capacity_constraint_is_hard": True,
                "group_daily_overlap_is_forbidden": True,
                "course_days_must_be_consecutive": True,
                "avb_default_is_one": True,
                "nee_is_zero_for_current_study": True,
            },
        }

        complexity = compute_complexity(instance)
        feasibility = check_schedule(instance, schedule)
        if not feasibility["feasible"]:
            last_error = RuntimeError(f"Planted solution failed feasibility check: {feasibility}")
            continue
        pareto_potential = _compute_pareto_potential(instance)
        if _is_pareto_mode(profile) and not pareto_potential.get("accepted", False):
            last_error = RuntimeError(f"Pareto potential screen failed: {pareto_potential}")
            continue

        metadata = {
            "instance_id": instance_id,
            "series_name": series_name,
            "profile": profile.name,
            "base_seed": int(base_seed),
            "instance_seed": int(instance_seed + attempt - 1),
            "attempt": attempt,
            "has_planted_feasible_solution": True,
            "mathematical_model_alignment": {
                "fixed_time": {"s": 2, "t": 6, "k": 16},
                "independent_parameters": ["B", "Du", "O", "Mea", "Comm"],
                "dependent_parameters": ["PW", "Dur", "weeks", "Cap", "Com", "Av", "Avb", "ne", "nt", "nee"],
                "curriculum_policy": "Comm is semester-driven: all groups in the same semester require exactly the same courses; courses are not shared across semesters.",
                "duration_policy": "Du_days is at least 6 and Dur(d,w) for PW=0 is split across defined wards so the sum of Dur over those wards equals Du.",
            },
            "complexity": complexity,
            "planted_solution_feasibility": feasibility,
            "tradeoff_mode": getattr(profile, "tradeoff_mode", "standard"),
            "pareto_potential": pareto_potential,
        }
        return GeneratedInstance(instance=instance, planted_schedule=schedule, metadata=metadata)

    raise RuntimeError(f"Failed to generate feasible MIP-aligned SNAP instance for profile={profile.name}, index={instance_index}. Last error: {last_error}")


def generate_instance(
    profile_name: str,
    instance_index: int,
    base_seed: int,
    series_name: str = "snap-math-model-taillard-inspired-v1.7.0",
    max_attempts: int = 30,
) -> GeneratedInstance:
    """Generate a SNAP benchmark instance for a named built-in profile."""
    return generate_instance_from_profile(
        get_profile(profile_name),
        instance_index,
        base_seed,
        series_name=series_name,
        max_attempts=max_attempts,
    )

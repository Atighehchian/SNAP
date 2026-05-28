from __future__ import annotations

import math
from typing import Any, Dict


def compute_complexity(instance: Dict[str, Any]) -> Dict[str, float | int | str]:
    """Compute model-aligned size and difficulty indicators for one SNAP instance."""
    if "model_parameters" not in instance:
        raise ValueError("This package supports only MIP-aligned SNAP instances with a model_parameters section.")

    mp = instance["model_parameters"]
    groups = instance.get("groups", [])
    courses = instance["courses"]
    wards = instance["wards"]
    hospitals = instance["hospitals"]
    time = instance["time"]
    I, D, W, H = len(groups), len(courses), len(wards), len(hospitals)
    S = int(time.get("shifts", 2))
    T = int(time.get("days_per_week", 6))
    K = int(time.get("weeks", 16))

    B = [x for x in mp.get("B", []) if x.get("exists", True)]
    Mea = [x for x in mp.get("Mea", []) if x.get("defined", False)]
    Comm = [x for x in mp.get("Comm", []) if x.get("required", False)]
    Com = [x for x in mp.get("Com", []) if x.get("required", False)]
    Av = [x for x in mp.get("Av", []) if x.get("available", False)]
    Avb = [x for x in mp.get("Avb", []) if x.get("available", False)]
    Cap = mp.get("Cap", [])
    Dur = {(x["course_id"], x["ward_id"]): int(x["Dur_days"]) for x in mp.get("Dur", [])}
    O = {x["course_id"]: int(x["O_consecutive_days"]) for x in mp.get("O", [])}
    Du = {x["course_id"]: int(x["Du_days"]) for x in mp.get("Du", [])}
    PW = {x["course_id"]: int(x["PW"]) for x in mp.get("PW", [])}

    mem = {g["group_id"]: int(g.get("mem", 1)) for g in groups}
    training_day_demand = 0
    member_day_demand = 0
    for req in Comm:
        group_id, course_id = req["group_id"], req["course_id"]
        if PW.get(course_id, 1) == 1:
            demand = Du.get(course_id, 0)
        else:
            demand = sum(days for (d, _w), days in Dur.items() if d == course_id)
        training_day_demand += demand
        member_day_demand += mem.get(group_id, 1) * demand

    cap_supply = sum(int(x.get("capacity", 0)) * K * T for x in Cap)
    load_ratio = member_day_demand / cap_supply if cap_supply else float("inf")

    mea_density = len(Mea) / (D * W) if D and W else 0.0
    b_density = len(B) / (W * H) if W and H else 0.0
    comm_density = len(Comm) / (I * D) if I and D else 0.0
    com_density = len(Com) / (I * D * W) if I and D and W else 0.0
    av_ratio = len(Av) / (I * T * K) if I else 0.0
    avb_ratio = len(Avb) / (max(1, len(B)) * T * K) if B else 0.0
    avg_O = sum(O.values()) / len(O) if O else 0.0
    avg_Du = sum(Du.values()) / len(Du) if Du else 0.0

    X = I * D * W * H * S * T * K
    Y = X
    Yp = D * W * H * T * K
    tf = I * D * W * H * T * K
    kendp = I * D * W * H * K
    Kend = I * D * W * H
    V1 = I * D * W * H * T * K
    V2 = V1
    Cmax1 = W * H
    Cmaxw = W
    q = D * W * H
    estimated_binary_variables = X + Y + Yp + tf + kendp + V1 + V2 + q
    estimated_integer_continuous_variables = Kend + Cmax1 + Cmaxw

    score = (
        0.25 * min(1.5, load_ratio) / 1.5
        + 0.20 * (1 - min(1, mea_density))
        + 0.15 * (1 - min(1, av_ratio))
        + 0.10 * (1 - min(1, b_density))
        + 0.15 * min(1, avg_O / max(1, T))
        + 0.15 * min(1, math.log10(max(10, estimated_binary_variables)) / 8)
    )
    if score < 0.30:
        label = "easy"
    elif score < 0.50:
        label = "medium"
    elif score < 0.70:
        label = "hard"
    else:
        label = "very_hard"

    return {
        "groups_I": I,
        "courses_D": D,
        "wards_W": W,
        "hospitals_H": H,
        "shifts_S": S,
        "days_T": T,
        "weeks_K": K,
        "B_density": round(b_density, 6),
        "Mea_density": round(mea_density, 6),
        "required_group_course_pairs_Comm": len(Comm),
        "required_group_course_ward_triples_Com": len(Com),
        "Comm_density": round(comm_density, 6),
        "Com_density": round(com_density, 6),
        "Av_ratio": round(av_ratio, 6),
        "Avb_ratio": round(avb_ratio, 6),
        "training_day_demand": int(training_day_demand),
        "member_day_demand": int(member_day_demand),
        "course_specific_capacity_supply": int(cap_supply),
        "load_ratio": round(load_ratio, 6),
        "average_Du_days": round(avg_Du, 6),
        "average_O_consecutive_days": round(avg_O, 6),
        "estimated_binary_variables_full_MIP": int(estimated_binary_variables),
        "estimated_integer_continuous_variables_full_MIP": int(estimated_integer_continuous_variables),
        "difficulty_score": round(score, 6),
        "difficulty_label": label,
    }


from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from collections import defaultdict

from .complexity import compute_complexity
from .feasibility import check_schedule, summarize_schedule
from .models import GeneratedInstance


def _id(prefix: str, n: int) -> str:
    return f"{prefix}{n:03d}"


@dataclass(frozen=True)
class ParetoTemplateMicroSpec:
    name: str
    groups: int
    hospitals: int
    max_attempts: int = 20


class _PlacementError(RuntimeError):
    pass


def _base_sets(spec: ParetoTemplateMicroSpec):
    groups = [{"group_id": _id("I", i), "i_index": i, "semester": 7, "mem": 1} for i in range(1, spec.groups + 1)]
    courses = [
        {"course_id": "D001", "d_index": 1, "semester": 7, "Du_days": 6, "O_consecutive_days": 3, "PW": 0, "requires_consecutive_days": True, "template_role": "fixed_baseline", "template_weeks": 2},
        {"course_id": "D002", "d_index": 2, "semester": 7, "Du_days": 9, "O_consecutive_days": 3, "PW": 1, "requires_consecutive_days": True, "template_role": "flexible_choice", "template_weeks": 3},
    ]
    wards = [{"ward_id": _id("W", w), "w_index": w, "name": f"Ward {w}", "hospital_id": "H001"} for w in range(1, 4)]
    hospitals = [{"hospital_id": _id("H", h), "h_index": h, "name": f"Hospital {h}"} for h in range(1, spec.hospitals + 1)]
    return groups, courses, wards, hospitals


def _make_B(wards, hospitals):
    """Very small B. For H=2, mimic the successful example with all three wards in both hospitals.

    We keep W=3 and H<=2, so even full B remains tiny. This preserves enough alternatives
    for Pareto points without exploding the model.
    """
    out=[]
    for w in wards:
        for h in hospitals:
            out.append({"ward_id": w["ward_id"], "hospital_id": h["hospital_id"], "exists": True})
    return out


def _make_mea(courses, wards):
    out=[]
    for c in courses:
        d=c["course_id"]
        if d == "D001":
            selected={"W001"}
        else:
            selected={"W002", "W003"}
        primary=sorted(selected)[0]
        for w in wards:
            wid=w["ward_id"]
            defined=wid in selected
            role="none" if not defined else ("primary" if wid==primary else "alternative")
            out.append({"course_id": d, "ward_id": wid, "defined": defined, "role": role})
    return out


def _make_params(groups, courses, wards, hospitals, B, mea):
    group_ids=[g["group_id"] for g in groups]
    course_ids=[c["course_id"] for c in courses]
    ward_ids=[w["ward_id"] for w in wards]
    hospital_ids=[h["hospital_id"] for h in hospitals]
    course_by={c["course_id"]: c for c in courses}
    mea_defined={(r["course_id"], r["ward_id"]): r for r in mea if r.get("defined")}
    B_exists={(r["ward_id"], r["hospital_id"]) for r in B if r.get("exists")}
    comm=[{"group_id": i, "course_id": d, "required": True} for i in group_ids for d in course_ids]
    com=[{"group_id": i, "course_id": d, "ward_id": w, "required": (d,w) in mea_defined} for i in group_ids for d in course_ids for w in ward_ids]
    eb=[{"course_id": d, "ward_id": w, "hospital_id": h, "eligible": (d,w) in mea_defined and (w,h) in B_exists} for d in course_ids for w in ward_ids for h in hospital_ids]
    dur=[]; weeks=[]
    for d in course_ids:
        c=course_by[d]
        for w in ward_ids:
            if (d,w) in mea_defined:
                du=int(c["Du_days"]); wk=int(du//int(c["O_consecutive_days"]))
            else:
                du=0; wk=0
            dur.append({"course_id": d, "ward_id": w, "Dur_days": du})
            weeks.append({"course_id": d, "ward_id": w, "weeks": wk})
    cap=[]
    for d in course_ids:
        for w in ward_ids:
            role=mea_defined.get((d,w),{}).get("role","none")
            for h in hospital_ids:
                capacity=1 if ((d,w) in mea_defined and (w,h) in B_exists) else 0
                cap.append({"course_id": d, "ward_id": w, "hospital_id": h, "capacity": capacity, "capacity_role": role})
    av=[]
    for i in group_ids:
        for k in range(1,17):
            for t in range(1,7):
                av.append({"group_id": i, "week": k, "day": t, "available": t in {1,2,3}})
    avb=[]
    for w in ward_ids:
        for h in hospital_ids:
            for k in range(1,17):
                for t in range(1,7):
                    avb.append({"ward_id": w, "hospital_id": h, "week": k, "day": t, "available": (w,h) in B_exists})
    ne=[{"course_id": d, "ward_id": w, "allowed": False} for d in course_ids for w in ward_ids]
    nee=[{"course_id": d, "ward_id": w, "minimum_long_shifts": 0} for d in course_ids for w in ward_ids]
    nt=[{"ward_id": w, "interference_allowed": False} for w in ward_ids]
    return {"B":B,"Du":[{"course_id":c["course_id"],"Du_days":int(c["Du_days"])} for c in courses],"O":[{"course_id":c["course_id"],"O_consecutive_days":int(c["O_consecutive_days"])} for c in courses],"PW":[{"course_id":c["course_id"],"PW":int(c["PW"])} for c in courses],"Mea":mea,"Comm":comm,"Dur":dur,"weeks":weeks,"Cap":cap,"Com":com,"Eb":eb,"Av":av,"Avb":avb,"ne":ne,"nee":nee,"nt":nt}


def _options(d, params):
    return sorted([(r["ward_id"], r["hospital_id"]) for r in params["Eb"] if r["course_id"]==d and r.get("eligible")])


def _plant(groups, courses, params):
    O_by={r["course_id"]: int(r["O_consecutive_days"]) for r in params["O"]}
    Du_by={r["course_id"]: int(r["Du_days"]) for r in params["Du"]}
    weeks_by={(r["course_id"], r["ward_id"]): int(r["weeks"]) for r in params["weeks"]}
    cap_by={(r["course_id"], r["ward_id"], r["hospital_id"]): int(r["capacity"]) for r in params["Cap"]}
    group_week_busy=set()
    course_location_load=defaultdict(int)
    # Allow same course in the same location for several groups up to capacity only.
    # With cap=1, groups are sequentialized, creating time pressure and Pareto potential.
    schedule=[]; a=1
    for c in courses:
        d=c["course_id"]; pw=int(c["PW"])
        opts=_options(d, params)
        if not opts:
            raise _PlacementError(f"No options for {d}")
        for g in groups:
            gid=g["group_id"]; mem=int(g.get("mem",1))
            # For planted feasibility, rotate locations for the flexible course. Optimizer may still concentrate/distribute.
            rot=(int(g["i_index"])-1) % len(opts)
            ordered=opts[rot:]+opts[:rot]
            placed=False
            for sw in range(1,17):
                for w,h in ordered:
                    segw=weeks_by.get((d,w),0)
                    if segw <= 0 or sw+segw-1 > 16:
                        continue
                    weeks=list(range(sw, sw+segw))
                    if any((gid,wk) in group_week_busy for wk in weeks):
                        continue
                    ok=True
                    for wk in weeks:
                        if course_location_load.get((d,w,h,wk),0)+mem > cap_by.get((d,w,h),0):
                            ok=False; break
                    if not ok:
                        continue
                    for wk in weeks:
                        group_week_busy.add((gid,wk))
                        course_location_load[(d,w,h,wk)] += mem
                        schedule.append({"assignment_id":f"A{a:05d}","group_id":gid,"course_id":d,"ward_id":w,"hospital_id":h,"week":wk,"start_week":sw,"start_day":1,"O_consecutive_days":O_by[d],"segment_Dur_days":Du_by[d],"segment_weeks":segw,"days":[1,2,3],"shift":1,"mem":mem,"PW":pw})
                        a += 1
                    placed=True; break
                if placed: break
            if not placed:
                raise _PlacementError(f"Could not place {gid}-{d}")
    return schedule


def _potential(instance, schedule):
    mp=instance["model_parameters"]
    summary=summarize_schedule(instance, schedule)
    eligible=sum(1 for r in mp["Eb"] if r.get("eligible"))
    active=eligible*int(instance["sets"]["I"])
    return {"accepted": active <= 24 and summary.get("latest_completion_time",999) <= 96, "template":"pareto-template-ultralight", "active_IDWH_estimate": int(active), "eligible_DWH": int(eligible), "intended_tradeoff":"D001 fixed baseline; D002 flexible over W002/W003 and H options, cap=1 creates concentration-vs-span tradeoff", "screen_summary": summary}


def generate_pareto_template_ultralight_instance(*, name: str, groups_n: int, hospitals_n: int, instance_index: int, base_seed: int, series_name: str="snap-pareto-template-ultralight-v1.8.2", max_attempts: int=20) -> GeneratedInstance:
    if not (3 <= groups_n <= 4):
        raise ValueError("pareto-template-ultralight requires 3 <= groups <= 4")
    if not (1 <= hospitals_n <= 2):
        raise ValueError("pareto-template-ultralight requires 1 <= hospitals <= 2")
    spec=ParetoTemplateMicroSpec(name=name, groups=groups_n, hospitals=hospitals_n, max_attempts=max_attempts)
    last=None
    for attempt in range(1, max_attempts+1):
        try:
            groups,courses,wards,hospitals=_base_sets(spec)
            B=_make_B(wards,hospitals)
            mea=_make_mea(courses,wards)
            params=_make_params(groups,courses,wards,hospitals,B,mea)
            schedule=_plant(groups,courses,params)
        except Exception as exc:
            last=exc; continue
        iid=f"{name}_{instance_index:03d}"
        instance={"metadata":{"instance_id":iid,"series_name":series_name,"format_version":"1.8.2","generator":"SNAP ultra-light template-based Pareto-friendly instance generator","profile":name,"base_seed":int(base_seed),"instance_seed":int(base_seed)+int(instance_index)*1009+attempt-1,"attempt":attempt},"time":{"shifts":2,"days_per_week":6,"weeks":16,"shift_durations_hours":{"1":5,"2":10}},"sets":{"I":groups_n,"D":2,"W":3,"H":hospitals_n,"S":2,"T":6,"K":16},"groups":groups,"hospitals":hospitals,"wards":wards,"courses":courses,"model_parameters":params,"policy":{"ultralight_template_policy":"D=2, W=3, H=1..2, I=3..4, mem=1, cap=1, D001 fixed one ward, D002 flexible two wards.","capacity_constraint_is_hard":True,"group_daily_overlap_is_forbidden":True,"course_days_must_be_consecutive":True,"nee_is_zero_for_current_study":True}}
        feas=check_schedule(instance,schedule)
        if not feas.get("feasible"):
            last=RuntimeError(f"infeasible planted schedule: {feas}"); continue
        potential=_potential(instance,schedule)
        if not potential.get("accepted"):
            last=RuntimeError(f"potential rejected: {potential}"); continue
        metadata={"instance_id":iid,"series_name":series_name,"profile":name,"base_seed":int(base_seed),"instance_seed":int(base_seed)+int(instance_index)*1009+attempt-1,"attempt":attempt,"has_planted_feasible_solution":True,"generator_mode":"pareto_template_ultralight","mathematical_model_alignment":{"fixed_time":{"s":2,"t":6,"k":16},"template_rule":"D001 fixed baseline with PW=0 and one ward; D002 flexible with PW=1 and W002/W003.","speed_rule":"Only D=2, W=3, H<=2, I<=4; active IDWH intentionally tiny."},"complexity":compute_complexity(instance),"planted_solution_feasibility":feas,"tradeoff_mode":"pareto_template_ultralight","pareto_potential":potential}
        return GeneratedInstance(instance=instance, planted_schedule=schedule, metadata=metadata)
    raise RuntimeError(f"Failed to generate pareto-template-ultralight instance for name={name}, index={instance_index}. Last error: {last}")

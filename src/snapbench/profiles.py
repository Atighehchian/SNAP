from __future__ import annotations

from dataclasses import replace

from .models import BenchmarkProfile


# All profiles use the fixed time structure required by the paper model:
# s=2 shifts, t=6 days/week, k=16 weeks.
PROFILES = {

    "vvs": BenchmarkProfile(
        name="vvs", groups=3, courses=1, wards=1, hospitals=1,
        course_load_per_group=1, min_group_size=3, max_group_size=5,
        min_du_days=6, max_du_days=6, min_consecutive_days=2, max_consecutive_days=3,
        target_mea_density=1.00, pw_probability=1.00,
        min_wards_per_course=1, max_wards_per_course=1,
        senior_ratio=0.0, allow_long_shift_probability=0.0, nt_probability=0.0,
        difficulty_hint="very-very-small-exact-test",
    ),
    "vs": BenchmarkProfile(
        name="vs", groups=4, courses=2, wards=2, hospitals=1,
        course_load_per_group=1, min_group_size=3, max_group_size=6,
        min_du_days=6, max_du_days=8, min_consecutive_days=2, max_consecutive_days=4,
        target_mea_density=0.75, pw_probability=0.85,
        min_wards_per_course=1, max_wards_per_course=2,
        senior_ratio=0.0, allow_long_shift_probability=0.0, nt_probability=0.0,
        difficulty_hint="very-small-exact-test",
    ),
    "tiny": BenchmarkProfile(
        name="tiny", groups=5, courses=4, wards=4, hospitals=1,
        course_load_per_group=2, min_group_size=4, max_group_size=6,
        min_du_days=6, max_du_days=12, min_consecutive_days=2, max_consecutive_days=3,
        target_mea_density=0.60, pw_probability=0.65,
        min_wards_per_course=1, max_wards_per_course=2,
        senior_ratio=0.30, allow_long_shift_probability=0.0, nt_probability=0.0,
        difficulty_hint="debug",
    ),
    "snap_s": BenchmarkProfile(
        name="snap_s", groups=10, courses=7, wards=8, hospitals=2,
        course_load_per_group=3, min_group_size=4, max_group_size=8,
        min_du_days=6, max_du_days=12, min_consecutive_days=2, max_consecutive_days=4,
        target_mea_density=0.45, pw_probability=0.70,
        min_wards_per_course=1, max_wards_per_course=3,
        senior_ratio=0.35, allow_long_shift_probability=0.0, nt_probability=0.0,
        difficulty_hint="small-mip-oriented",
    ),
    "snap_m": BenchmarkProfile(
        name="snap_m", groups=22, courses=14, wards=16, hospitals=3,
        course_load_per_group=5, min_group_size=5, max_group_size=10,
        min_du_days=6, max_du_days=12, min_consecutive_days=2, max_consecutive_days=5,
        target_mea_density=0.35, pw_probability=0.62,
        min_wards_per_course=1, max_wards_per_course=4,
        senior_ratio=0.45, allow_long_shift_probability=0.0, nt_probability=0.05,
        difficulty_hint="medium",
    ),
    "snap_l": BenchmarkProfile(
        name="snap_l", groups=40, courses=24, wards=30, hospitals=4,
        course_load_per_group=7, min_group_size=5, max_group_size=12,
        min_du_days=6, max_du_days=18, min_consecutive_days=2, max_consecutive_days=6,
        target_mea_density=0.28, pw_probability=0.55,
        min_wards_per_course=1, max_wards_per_course=5,
        senior_ratio=0.50, allow_long_shift_probability=0.06, nt_probability=0.10,
        difficulty_hint="large-metaheuristic-oriented",
    ),
    "snap_tight": BenchmarkProfile(
        name="snap_tight", groups=24, courses=14, wards=12, hospitals=3,
        course_load_per_group=6, min_group_size=7, max_group_size=12,
        min_du_days=6, max_du_days=16, min_consecutive_days=2, max_consecutive_days=5,
        target_mea_density=0.30, pw_probability=0.55,
        min_wards_per_course=1, max_wards_per_course=3,
        senior_ratio=0.45, allow_long_shift_probability=0.0, nt_probability=0.08,
        difficulty_hint="capacity-tight",
    ),
    "snap_sparse": BenchmarkProfile(
        name="snap_sparse", groups=24, courses=16, wards=18, hospitals=3,
        course_load_per_group=5, min_group_size=5, max_group_size=10,
        min_du_days=6, max_du_days=12, min_consecutive_days=2, max_consecutive_days=5,
        target_mea_density=0.18, pw_probability=0.55,
        min_wards_per_course=1, max_wards_per_course=2,
        senior_ratio=0.45, allow_long_shift_probability=0.0, nt_probability=0.08,
        difficulty_hint="eligibility-sparse",
    ),
    "snap_lowavail": BenchmarkProfile(
        name="snap_lowavail", groups=24, courses=14, wards=16, hospitals=3,
        course_load_per_group=5, min_group_size=5, max_group_size=10,
        min_du_days=6, max_du_days=12, min_consecutive_days=3, max_consecutive_days=6,
        target_mea_density=0.35, pw_probability=0.60,
        min_wards_per_course=1, max_wards_per_course=4,
        senior_ratio=0.45, allow_long_shift_probability=0.0, nt_probability=0.08,
        difficulty_hint="low-student-availability",
    ),
    "snap_hard": BenchmarkProfile(
        name="snap_hard", groups=38, courses=22, wards=24, hospitals=4,
        course_load_per_group=7, min_group_size=6, max_group_size=12,
        min_du_days=6, max_du_days=18, min_consecutive_days=3, max_consecutive_days=6,
        target_mea_density=0.22, pw_probability=0.50,
        min_wards_per_course=1, max_wards_per_course=4,
        senior_ratio=0.50, allow_long_shift_probability=0.08, nt_probability=0.15,
        difficulty_hint="hard-mixed",
    ),
}

# Profiles generated by default when `generate-grid` is called without --profiles.
# `tiny` is intentionally excluded because it is only a developer smoke-test profile.
# The default grid includes the two micro profiles plus all main benchmark profiles.
DEFAULT_GRID_PROFILES = [
    "vvs",
    "vs",
    "snap_s",
    "snap_m",
    "snap_l",
    "snap_tight",
    "snap_sparse",
    "snap_lowavail",
    "snap_hard",
]


def build_custom_profile(
    *,
    name: str,
    groups: int,
    courses: int,
    wards: int,
    hospitals: int,
    base_profile: str = "snap_s",
    difficulty_hint: str | None = None,
    min_group_size: int | None = None,
    max_group_size: int | None = None,
    min_du_days: int | None = None,
    max_du_days: int | None = None,
    min_consecutive_days: int | None = None,
    max_consecutive_days: int | None = None,
    target_mea_density: float | None = None,
    pw_probability: float | None = None,
    senior_ratio: float | None = None,
    allow_long_shift_probability: float | None = None,
    nt_probability: float | None = None,
    tradeoff_mode: str = "standard",
) -> BenchmarkProfile:
    """Build an ad-hoc benchmark profile from user-supplied dimensions.

    The user controls |I|, |D|, |W| and |H|. Other distribution settings are
    inherited from a named base profile and then clipped so that the generated
    instance remains coherent for the requested size.
    """
    if groups < 1 or courses < 1 or wards < 1 or hospitals < 1:
        raise ValueError("groups, courses, wards and hospitals must all be positive integers")
    base = get_profile(base_profile)
    if tradeoff_mode not in {"standard", "pareto"}:
        raise ValueError("tradeoff_mode must be either 'standard' or 'pareto'")

    min_wpc = min(max(1, base.min_wards_per_course), wards)
    max_wpc = min(max(min_wpc, base.max_wards_per_course), wards)
    # For very small custom instances, avoid forcing all-ward courses too often.
    custom_pw_probability = base.pw_probability if pw_probability is None else float(pw_probability)

    # Pareto-friendly mode deliberately creates more real alternatives.
    # It does not change the mathematical objective, but it shapes the data so
    # using fewer wards tends to create a longer schedule and using more wards
    # tends to reduce completion time.
    if tradeoff_mode == "pareto" and wards >= 2:
        custom_pw_probability = max(custom_pw_probability, 0.85)
        min_wpc = max(2, min_wpc)
        max_wpc = max(max_wpc, min(wards, 4))
        if target_mea_density is None:
            target_mea_density = max(base.target_mea_density, min(0.65, max(0.45, 3 / max(1, wards))))
        if nt_probability is None:
            nt_probability = max(base.nt_probability, 0.10)

    if wards == 1:
        custom_pw_probability = 1.0
        min_wpc = 1
        max_wpc = 1

    return replace(
        base,
        name=name,
        groups=int(groups),
        courses=int(courses),
        wards=int(wards),
        hospitals=int(hospitals),
        course_load_per_group=min(max(1, base.course_load_per_group), int(courses)),
        min_group_size=int(min_group_size if min_group_size is not None else base.min_group_size),
        max_group_size=int(max_group_size if max_group_size is not None else base.max_group_size),
        min_du_days=int(min_du_days if min_du_days is not None else base.min_du_days),
        max_du_days=int(max_du_days if max_du_days is not None else base.max_du_days),
        min_consecutive_days=int(min_consecutive_days if min_consecutive_days is not None else base.min_consecutive_days),
        max_consecutive_days=int(max_consecutive_days if max_consecutive_days is not None else base.max_consecutive_days),
        target_mea_density=float(target_mea_density if target_mea_density is not None else base.target_mea_density),
        pw_probability=custom_pw_probability,
        min_wards_per_course=min_wpc,
        max_wards_per_course=max_wpc,
        senior_ratio=float(senior_ratio if senior_ratio is not None else base.senior_ratio),
        allow_long_shift_probability=float(allow_long_shift_probability if allow_long_shift_probability is not None else base.allow_long_shift_probability),
        nt_probability=float(nt_probability if nt_probability is not None else base.nt_probability),
        difficulty_hint=difficulty_hint or f"custom-I{groups}-D{courses}-W{wards}-H{hospitals}",
        tradeoff_mode=tradeoff_mode,
    )


def list_profiles() -> list[str]:
    return sorted(PROFILES.keys())


def get_profile(name: str) -> BenchmarkProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        valid = ", ".join(list_profiles())
        raise ValueError(f"Unknown profile '{name}'. Valid profiles: {valid}") from exc

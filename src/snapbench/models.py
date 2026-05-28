from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class BenchmarkProfile:
    """Controlled SNAP benchmark class.

    The time horizon is fixed by the paper model: S=2 shifts, T=6 days/week,
    K=16 weeks. The size fields control only |I|, |D|, |W|, |H| and
    difficulty-related distributions.
    """

    name: str
    groups: int
    courses: int
    wards: int
    hospitals: int
    course_load_per_group: int
    min_group_size: int
    max_group_size: int
    min_du_days: int
    max_du_days: int
    min_consecutive_days: int
    max_consecutive_days: int
    target_mea_density: float
    pw_probability: float
    min_wards_per_course: int
    max_wards_per_course: int
    senior_ratio: float
    allow_long_shift_probability: float
    nt_probability: float
    difficulty_hint: str
    tradeoff_mode: str = "standard"

    # Fixed model-time constants from the paper/problem statement.
    shifts: int = 2
    days_per_week: int = 6
    weeks: int = 16
    standard_shift_hours: int = 6
    long_shift_hours: int = 10


@dataclass
class GeneratedInstance:
    """In-memory representation of a generated SNAP instance."""

    instance: Dict[str, Any]
    planted_schedule: List[Dict[str, Any]]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance": self.instance,
            "planted_schedule": self.planted_schedule,
            "metadata": self.metadata,
        }

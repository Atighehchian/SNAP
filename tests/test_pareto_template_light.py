from snapbench.pareto_template_light import generate_pareto_template_light_instance
from snapbench.feasibility import check_schedule


def test_pareto_template_light_basic():
    generated = generate_pareto_template_light_instance(
        name="light_test",
        groups_n=3,
        courses_n=2,
        wards_n=3,
        hospitals_n=1,
        instance_index=1,
        base_seed=20260508,
    )
    report = check_schedule(generated.instance, generated.planted_schedule)
    assert report["feasible"] is True
    assert generated.metadata["pareto_potential"]["accepted"] is True
    assert generated.metadata["pareto_potential"]["active_IDWH_estimate"] <= 30


def test_pareto_template_light_two_hospitals():
    generated = generate_pareto_template_light_instance(
        name="light_test2",
        groups_n=5,
        courses_n=3,
        wards_n=4,
        hospitals_n=2,
        instance_index=1,
        base_seed=20260508,
    )
    report = check_schedule(generated.instance, generated.planted_schedule)
    assert report["feasible"] is True
    assert generated.metadata["pareto_potential"]["accepted"] is True
    assert generated.metadata["pareto_potential"]["active_IDWH_estimate"] <= 30

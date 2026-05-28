from snapbench.pareto_template import generate_pareto_template_instance
from snapbench.feasibility import check_schedule


def test_pareto_template_h1_feasible():
    g = generate_pareto_template_instance(name="tpl_h1", groups_n=3, courses_n=2, wards_n=3, hospitals_n=1, instance_index=1, base_seed=20260508)
    rep = check_schedule(g.instance, g.planted_schedule)
    assert rep["feasible"] is True
    assert g.metadata["pareto_potential"]["accepted"] is True
    assert g.instance["sets"]["H"] == 1


def test_pareto_template_h3_feasible():
    g = generate_pareto_template_instance(name="tpl_h3", groups_n=6, courses_n=4, wards_n=5, hospitals_n=3, instance_index=1, base_seed=20260508)
    rep = check_schedule(g.instance, g.planted_schedule)
    assert rep["feasible"] is True
    assert g.metadata["pareto_potential"]["accepted"] is True
    assert g.instance["sets"]["H"] == 3

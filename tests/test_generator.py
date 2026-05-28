from pathlib import Path

from snapbench.generator import generate_instance
from snapbench.feasibility import check_schedule
from snapbench.io import save_instance_bundle, read_json, read_schedule_csv
from snapbench.complexity import compute_complexity


FORBIDDEN_INSTANCE_KEYS = {"students", "requirements", "student_availability", "ward_capacity"}
FORBIDDEN_GROUP_KEYS = {"student_id", "group", "level"}
FORBIDDEN_SCHEDULE_KEYS = {"student_id", "group", "duration_days"}


def test_generate_snap_s_feasible_and_clean_schema():
    generated = generate_instance("snap_s", 1, 20260508)
    result = check_schedule(generated.instance, generated.planted_schedule)
    assert result["feasible"] is True
    assert result["violation_count"] == 0
    assert generated.instance["sets"]["S"] == 2
    assert generated.instance["sets"]["T"] == 6
    assert generated.instance["sets"]["K"] == 16
    assert generated.instance["metadata"]["format_version"] == "1.7.0"
    assert not (FORBIDDEN_INSTANCE_KEYS & set(generated.instance.keys()))
    for row in generated.instance["groups"]:
        assert not (FORBIDDEN_GROUP_KEYS & set(row.keys()))
    for row in generated.instance["courses"]:
        assert row["Du_days"] >= 6
        assert "allowed_levels" not in row
        assert "allowed_groups" not in row
        assert "duration_days" not in row
    for row in generated.planted_schedule:
        assert not (FORBIDDEN_SCHEDULE_KEYS & set(row.keys()))


def test_bundle_roundtrip(tmp_path: Path):
    generated = generate_instance("tiny", 1, 20260508)
    out = tmp_path / generated.metadata["instance_id"]
    save_instance_bundle(out, generated.instance, generated.planted_schedule, generated.metadata)
    instance = read_json(out / "instance.json")
    schedule = read_schedule_csv(out / "planted_solution.csv")
    assert instance["metadata"]["format_version"] == "1.7.0"
    assert check_schedule(instance, schedule)["feasible"] is True
    assert "student_id" not in (out / "planted_solution.csv").read_text(encoding="utf-8")
    assert (out / "instance.xlsx").exists()
    assert (out / "instance.xlsx").stat().st_size > 0
    loader = out / f"load_{generated.metadata['instance_id']}.m"
    assert loader.exists()
    text = loader.read_text(encoding="utf-8")
    assert f"function snap = load_{generated.metadata['instance_id']}()" in text
    assert "jsondecode" in text
    assert "readtable" in text


def test_complexity_contains_mip_estimates():
    generated = generate_instance("tiny", 1, 20260508)
    complexity = compute_complexity(generated.instance)
    assert complexity["estimated_binary_variables_full_MIP"] > 0
    assert "difficulty_label" in complexity


def test_bundle_can_disable_matlab_loader(tmp_path: Path):
    generated = generate_instance("tiny", 1, 20260508)
    out = tmp_path / generated.metadata["instance_id"]
    save_instance_bundle(out, generated.instance, generated.planted_schedule, generated.metadata, write_matlab=False)
    assert (out / "instance.json").exists()
    assert not (out / f"load_{generated.metadata['instance_id']}.m").exists()
    manifest = read_json(out / "bundle_manifest.json")
    assert manifest["matlab_loader"] is None


def test_capacity_zero_for_ineligible_combinations():
    generated = generate_instance("snap_m", 1, 20260508)
    params = generated.instance["model_parameters"]
    eligible = {
        (row["course_id"], row["ward_id"], row["hospital_id"])
        for row in params["Eb"]
        if row["eligible"]
    }
    for row in params["Cap"]:
        key = (row["course_id"], row["ward_id"], row["hospital_id"])
        if key not in eligible:
            assert row["capacity"] == 0
        else:
            assert row["capacity"] >= 1


def test_capacity_for_all_valid_hospitals_is_demand_aware_not_default_one():
    generated = generate_instance("snap_m", 1, 20260508)
    params = generated.instance["model_parameters"]
    groups_by_id = {g["group_id"]: g for g in generated.instance["groups"]}
    comm_required = {(r["group_id"], r["course_id"]) for r in params["Comm"] if r["required"]}
    max_mem_by_course = {}
    for _g, d in comm_required:
        vals = [groups_by_id[g]["mem"] for (g, dd) in comm_required if dd == d]
        max_mem_by_course[d] = max(vals)
    eligible = {
        (row["course_id"], row["ward_id"], row["hospital_id"])
        for row in params["Eb"]
        if row["eligible"]
    }
    for row in params["Cap"]:
        key = (row["course_id"], row["ward_id"], row["hospital_id"])
        if key in eligible:
            assert row["capacity"] >= max_mem_by_course[row["course_id"]]

    # At least one course-ward with multiple valid hospitals should have meaningful
    # positive capacity in all valid hospitals, not one selected hospital plus default 1.
    caps_by_dw = {}
    for row in params["Cap"]:
        key = (row["course_id"], row["ward_id"], row["hospital_id"])
        if key in eligible:
            caps_by_dw.setdefault((row["course_id"], row["ward_id"]), []).append(row["capacity"])
    multi = [vals for vals in caps_by_dw.values() if len(vals) >= 2]
    assert multi
    assert all(all(v > 1 for v in vals) for vals in multi)


def test_vvs_vs_profiles_have_requested_dimensions():
    expected = {
        "vvs": (3, 1, 1, 1),
        "vs": (4, 2, 2, 1),
    }
    for profile, dims in expected.items():
        generated = generate_instance(profile, 1, 20260508)
        sets = generated.instance["sets"]
        got = (sets["I"], sets["D"], sets["W"], sets["H"])
        assert got == dims
        result = check_schedule(generated.instance, generated.planted_schedule)
        assert result["feasible"] is True
        assert result["violation_count"] == 0


def test_generate_grid_should_include_vvs_and_vs_by_default():
    from snapbench.profiles import list_profiles
    profiles = list_profiles()
    assert "vvs" in profiles
    assert "vs" in profiles


def test_txt_gams_and_m_exports_are_created(tmp_path: Path):
    generated = generate_instance("vs", 1, 20260508)
    out = tmp_path / generated.metadata["instance_id"]
    save_instance_bundle(out, generated.instance, generated.planted_schedule, generated.metadata)

    # TXT export has one file per set/parameter/table category.
    assert (out / "txt" / "sets" / "I.txt").exists()
    assert (out / "txt" / "sets" / "D.txt").exists()
    assert (out / "txt" / "parameters" / "Cap.txt").exists()
    assert (out / "txt" / "tables" / "Eb.txt").exists()
    assert (out / "txt" / "tables" / "Avb.txt").exists()
    assert (out / "txt" / "schedule" / "Planted_Solution.txt").exists()
    assert (out / "txt" / "parameters" / "Cap.txt").read_text(encoding="utf-8").splitlines()[0] == "d\tw\th\tvalue"

    # MATLAB M folder loader reads the TXT export.
    assert (out / "M" / "load_instance.m").exists()
    assert (out / "M" / f"load_{generated.metadata['instance_id']}.m").exists()
    m_text = (out / "M" / "load_instance.m").read_text(encoding="utf-8")
    assert "txtRoot" in m_text
    assert "snap.params.Cap" in m_text
    assert "snap.tables.Avb" in m_text

    # GAMS helper files are present.
    assert (out / "gams" / "gdxxrw_symbols.txt").exists()
    assert (out / "gams" / "import_to_gdx.gms").exists()
    assert (out / "gams" / "declarations_and_load.inc").exists()
    gams_symbols = (out / "gams" / "gdxxrw_symbols.txt").read_text(encoding="utf-8")
    assert "set=I rng=set_I!" in gams_symbols
    assert "par=Cap rng=par_Cap!" in gams_symbols
    assert "par=Avb rng=tab_Avb!" in gams_symbols


def test_xlsx_contains_gams_friendly_sheets(tmp_path: Path):
    from zipfile import ZipFile
    import re

    generated = generate_instance("vvs", 1, 20260508)
    out = tmp_path / generated.metadata["instance_id"]
    save_instance_bundle(out, generated.instance, generated.planted_schedule, generated.metadata)
    workbook_path = out / "instance.xlsx"
    with ZipFile(workbook_path) as zf:
        workbook_xml = zf.read("xl/workbook.xml").decode("utf-8")
    sheet_names = re.findall(r'<sheet name="([^"]+)"', workbook_xml)
    assert "GAMS_Index" in sheet_names
    assert "set_I" in sheet_names
    assert "set_D" in sheet_names
    assert "par_Cap" in sheet_names
    assert "tab_Eb" in sheet_names
    assert "tab_Avb" in sheet_names


def test_generate_custom_profile_dimensions_and_bundle(tmp_path: Path):
    from snapbench.profiles import build_custom_profile
    from snapbench.generator import generate_instance_from_profile

    profile = build_custom_profile(
        name="custom_3_1_2_1",
        groups=3,
        courses=1,
        wards=2,
        hospitals=1,
        base_profile="vvs",
    )
    generated = generate_instance_from_profile(profile, 1, 20260508)
    sets = generated.instance["sets"]
    assert (sets["I"], sets["D"], sets["W"], sets["H"]) == (3, 1, 2, 1)
    assert sets["S"] == 2 and sets["T"] == 6 and sets["K"] == 16
    assert check_schedule(generated.instance, generated.planted_schedule)["feasible"] is True

    out = tmp_path / generated.metadata["instance_id"]
    save_instance_bundle(out, generated.instance, generated.planted_schedule, generated.metadata, write_xlsx=False)
    assert (out / "instance.json").exists()
    assert (out / "txt" / "parameters" / "Cap.txt").exists()
    assert (out / "M" / "load_instance.m").exists()
    assert (out / "import_to_gdx.gms").exists()

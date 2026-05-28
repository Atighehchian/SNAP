from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from .symbol_export import gams_symbol_ranges, parameter_symbols, set_symbols
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


MAX_SHEET_NAME = 31


def _xml_text(value: Any) -> str:
    return escape(str(value), {'"': '&quot;', "'": '&apos;'})


def _col_name(index: int) -> str:
    """Convert a 1-based column index to Excel column letters."""
    letters = ""
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _cell_xml(row_idx: int, col_idx: int, value: Any, style: int = 0) -> str:
    if value is None:
        return ""
    ref = f"{_col_name(col_idx)}{row_idx}"
    style_attr = f' s="{style}"' if style else ""
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"{style_attr}><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"{style_attr}><v>{value}</v></c>'
    text = _xml_text(value)
    return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t>{text}</t></is></c>'


def _worksheet_xml(rows: Sequence[Sequence[Any]], freeze_header: bool = True) -> str:
    max_cols = max((len(r) for r in rows), default=1)
    max_rows = max(len(rows), 1)
    widths: List[int] = []
    for c in range(max_cols):
        max_len = 8
        for row in rows[:5000]:
            if c < len(row) and row[c] is not None:
                max_len = max(max_len, len(str(row[c])))
        widths.append(min(max(max_len + 2, 10), 36))
    cols_xml = "".join(
        f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
        for i, w in enumerate(widths, start=1)
    )
    if freeze_header and rows:
        sheet_views = (
            '<sheetViews><sheetView workbookViewId="0">'
            '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            '<selection pane="bottomLeft"/>'
            '</sheetView></sheetViews>'
        )
    else:
        sheet_views = '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'

    row_xml_parts: List[str] = []
    for r_idx, row in enumerate(rows, start=1):
        cells = []
        for c_idx, value in enumerate(row, start=1):
            style = 1 if r_idx == 1 else 0
            cell = _cell_xml(r_idx, c_idx, value, style)
            if cell:
                cells.append(cell)
        height_attr = ' ht="22" customHeight="1"' if r_idx == 1 else ""
        row_xml_parts.append(f'<row r="{r_idx}"{height_attr}>{"".join(cells)}</row>')
    sheet_data = "".join(row_xml_parts)
    dimension = f'A1:{_col_name(max_cols)}{max_rows}'
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dimension}"/>'
        f'{sheet_views}'
        f'<cols>{cols_xml}</cols>'
        f'<sheetData>{sheet_data}</sheetData>'
        '</worksheet>'
    )


def _styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF0F766E"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left style="thin"><color rgb="FFD9E2EC"/></left><right style="thin"><color rgb="FFD9E2EC"/></right><top style="thin"><color rgb="FFD9E2EC"/></top><bottom style="thin"><color rgb="FFD9E2EC"/></bottom><diagonal/></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''


def _flatten(prefix: str, value: Any, rows: List[List[Any]]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(f"{prefix}.{k}" if prefix else str(k), v, rows)
    elif isinstance(value, list):
        if all(not isinstance(x, (dict, list)) for x in value):
            rows.append([prefix, ";".join(str(x) for x in value)])
        else:
            rows.append([prefix, f"list[{len(value)}]"])
    else:
        rows.append([prefix, value])


def _rows_from_dicts(items: Sequence[Dict[str, Any]], preferred_order: Sequence[str] | None = None) -> List[List[Any]]:
    if not items:
        return [["No data"]]
    keys: List[str] = []
    if preferred_order:
        keys.extend([k for k in preferred_order if any(k in row for row in items)])
    for row in items:
        for key in row.keys():
            if key not in keys:
                keys.append(key)
    rows: List[List[Any]] = [keys]
    for item in items:
        rows.append([_value_for_excel(item.get(k)) for k in keys])
    return rows


def _value_for_excel(value: Any) -> Any:
    if isinstance(value, list):
        return ";".join(str(x) for x in value)
    if isinstance(value, dict):
        return str(value)
    return value


def _course_params(instance: Dict[str, Any]) -> List[List[Any]]:
    params = instance["model_parameters"]
    by_course: Dict[str, Dict[str, Any]] = {}
    for key, field in [("Du", "Du_days"), ("O", "O_consecutive_days"), ("PW", "PW")]:
        for row in params.get(key, []):
            cid = row["course_id"]
            by_course.setdefault(cid, {"course_id": cid})[field] = row.get(field)
    rows = [["course_id", "Du_days", "O_consecutive_days", "PW"]]
    for cid in sorted(by_course):
        row = by_course[cid]
        rows.append([cid, row.get("Du_days"), row.get("O_consecutive_days"), row.get("PW")])
    return rows


def _dur_weeks(instance: Dict[str, Any]) -> List[List[Any]]:
    params = instance["model_parameters"]
    merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in params.get("Dur", []):
        key = (row["course_id"], row["ward_id"])
        merged.setdefault(key, {"course_id": row["course_id"], "ward_id": row["ward_id"]})["Dur_days"] = row.get("Dur_days")
    for row in params.get("weeks", []):
        key = (row["course_id"], row["ward_id"])
        merged.setdefault(key, {"course_id": row["course_id"], "ward_id": row["ward_id"]})["weeks"] = row.get("weeks")
    rows = [["course_id", "ward_id", "Dur_days", "weeks"]]
    for key in sorted(merged):
        row = merged[key]
        rows.append([row["course_id"], row["ward_id"], row.get("Dur_days"), row.get("weeks")])
    return rows


def _ne_nee(instance: Dict[str, Any]) -> List[List[Any]]:
    params = instance["model_parameters"]
    merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in params.get("ne", []):
        key = (row["course_id"], row["ward_id"])
        merged.setdefault(key, {"course_id": row["course_id"], "ward_id": row["ward_id"]})["long_shift_allowed"] = row.get("allowed")
    for row in params.get("nee", []):
        key = (row["course_id"], row["ward_id"])
        merged.setdefault(key, {"course_id": row["course_id"], "ward_id": row["ward_id"]})["minimum_long_shifts"] = row.get("minimum_long_shifts")
    rows = [["course_id", "ward_id", "long_shift_allowed", "minimum_long_shifts"]]
    for key in sorted(merged):
        row = merged[key]
        rows.append([row["course_id"], row["ward_id"], row.get("long_shift_allowed"), row.get("minimum_long_shifts")])
    return rows


def _semester_plan(instance: Dict[str, Any]) -> List[List[Any]]:
    params = instance.get("model_parameters", {})
    groups_by_sem: Dict[int, List[str]] = {}
    for g in instance.get("groups", []):
        groups_by_sem.setdefault(int(g.get("semester", 0)), []).append(g.get("group_id"))
    courses_by_sem: Dict[int, List[str]] = {}
    course_o: Dict[str, int] = {row["course_id"]: int(row.get("O_consecutive_days", 0)) for row in params.get("O", [])}
    for c in instance.get("courses", []):
        courses_by_sem.setdefault(int(c.get("semester", 0)), []).append(c.get("course_id"))
    av_days_by_group: Dict[str, List[int]] = {}
    for row in params.get("Av", []):
        if int(row.get("week", 0)) == 1 and row.get("available"):
            av_days_by_group.setdefault(row["group_id"], []).append(int(row["day"]))
    rows = [["semester", "group_count", "groups", "course_count", "courses", "shared_available_days", "max_O"]]
    for sem in sorted(set(groups_by_sem) | set(courses_by_sem)):
        groups = sorted(groups_by_sem.get(sem, []))
        courses = sorted(courses_by_sem.get(sem, []))
        days = av_days_by_group.get(groups[0], []) if groups else []
        max_o = max([course_o.get(c, 0) for c in courses], default=0)
        rows.append([sem, len(groups), ";".join(groups), len(courses), ";".join(courses), ";".join(str(d) for d in days), max_o])
    return rows


def _gams_workbook_tables(instance: Dict[str, Any]) -> List[Tuple[str, List[List[Any]]]]:
    """Return GDXXRW-friendly flat sheets.

    Each symbol gets one sheet with one header row and long-form rows. Multi-dimensional
    parameters use one column per domain element plus a final `value` column. This layout
    can be read by GAMS/GDXXRW with rDim=<number of domain columns>, cDim=0.
    """
    index_rows: List[List[Any]] = [["symbol", "kind", "domain", "sheet_name", "range", "rDim", "cDim", "row_count"]]
    for row in gams_symbol_ranges(instance):
        index_rows.append([row["name"], row["kind"], row["domain"], row["sheet_name"], row["range"], row["rdim"], row["cdim"], row["row_count"]])
    tables: List[Tuple[str, List[List[Any]]]] = [("GAMS_Index", index_rows)]
    for sym in set_symbols(instance) + parameter_symbols(instance):
        tables.append((sym.sheet_name, [list(sym.headers), *[list(r) for r in sym.rows]]))
    return tables


def build_instance_workbook_tables(instance: Dict[str, Any], schedule: Sequence[Dict[str, Any]], metadata: Dict[str, Any]) -> List[Tuple[str, List[List[Any]]]]:
    params = instance.get("model_parameters", {})
    complexity_rows: List[List[Any]] = [["key", "value"]]
    _flatten("", metadata, complexity_rows)
    workbook_tables: List[Tuple[str, List[List[Any]]]] = [
        ("README", [
            ["Field", "Value"],
            ["instance_id", instance.get("metadata", {}).get("instance_id")],
            ["format_version", instance.get("metadata", {}).get("format_version")],
            ["generator", instance.get("metadata", {}).get("generator")],
            ["profile", instance.get("metadata", {}).get("profile")],
            ["base_seed", instance.get("metadata", {}).get("base_seed")],
            ["instance_seed", instance.get("metadata", {}).get("instance_seed")],
            ["S shifts", instance.get("sets", {}).get("S")],
            ["T days/week", instance.get("sets", {}).get("T")],
            ["K weeks", instance.get("sets", {}).get("K")],
            ["note", "This XLSX mirrors instance.json for review in Excel. JSON remains the canonical machine-readable file."],
        ]),
        ("Sets", [["set", "count"], *[[k, v] for k, v in instance.get("sets", {}).items()]]),
        ("Groups_I", _rows_from_dicts(instance.get("groups", []), ["group_id", "i_index", "semester", "mem"])),
        ("Courses_D", _rows_from_dicts(instance.get("courses", []), ["course_id", "d_index", "semester", "Du_days", "O_consecutive_days", "PW", "requires_consecutive_days"])),
        ("Wards_W", _rows_from_dicts(instance.get("wards", []), ["ward_id", "w_index", "name", "hospital_id"])),
        ("Hospitals_H", _rows_from_dicts(instance.get("hospitals", []), ["hospital_id", "h_index"])),
        ("B_wh", _rows_from_dicts(params.get("B", []), ["ward_id", "hospital_id", "exists"])),
        ("Course_Params", _course_params(instance)),
        ("Semester_Plan", _semester_plan(instance)),
        ("Mea_dw", _rows_from_dicts(params.get("Mea", []), ["course_id", "ward_id", "defined"])),
        ("Dur_weeks_dw", _dur_weeks(instance)),
        ("Comm_id", _rows_from_dicts(params.get("Comm", []), ["group_id", "course_id", "required"])),
        ("Com_idw", _rows_from_dicts(params.get("Com", []), ["group_id", "course_id", "ward_id", "required"])),
        ("Eb_dwh", _rows_from_dicts(params.get("Eb", []), ["course_id", "ward_id", "hospital_id", "eligible"])),
        ("Cap_dwh", _rows_from_dicts(params.get("Cap", []), ["course_id", "ward_id", "hospital_id", "capacity"])),
        ("Av_itk", _rows_from_dicts(params.get("Av", []), ["group_id", "week", "day", "available"])),
        ("Avb_whtk", _rows_from_dicts(params.get("Avb", []), ["ward_id", "hospital_id", "week", "day", "available"])),
        ("ne_nee_dw", _ne_nee(instance)),
        ("nt_w", _rows_from_dicts(params.get("nt", []), ["ward_id", "interference_allowed"])),
        ("Planted_Solution", _rows_from_dicts(list(schedule))),
        ("Metadata", complexity_rows),
    ]
    workbook_tables.extend(_gams_workbook_tables(instance))
    return workbook_tables


def _safe_sheet_name(name: str, used: set[str]) -> str:
    invalid = '[]:*?/\\'
    cleaned = ''.join('_' if ch in invalid else ch for ch in name)[:MAX_SHEET_NAME]
    base = cleaned or "Sheet"
    candidate = base
    n = 1
    while candidate in used:
        suffix = f"_{n}"
        candidate = base[: MAX_SHEET_NAME - len(suffix)] + suffix
        n += 1
    used.add(candidate)
    return candidate


def write_instance_xlsx(path: str | Path, instance: Dict[str, Any], schedule: Sequence[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
    """Write a review-friendly Excel workbook for a generated SNAP instance.

    The JSON file remains the canonical machine-readable representation. The XLSX
    workbook is intended for human inspection, GitHub releases, and non-Python users.
    It is written using the Python standard library only.
    """
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_tables = build_instance_workbook_tables(instance, schedule, metadata)
    used: set[str] = set()
    sheets = [(_safe_sheet_name(name, used), rows) for name, rows in raw_tables]

    workbook_sheets_xml = []
    workbook_rels_xml = []
    content_types_xml = [
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for idx, (sheet_name, _rows) in enumerate(sheets, start=1):
        escaped_name = _xml_text(sheet_name)
        workbook_sheets_xml.append(f'<sheet name="{escaped_name}" sheetId="{idx}" r:id="rId{idx}"/>')
        workbook_rels_xml.append(
            f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>'
        )
        content_types_xml.append(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    style_rid = len(sheets) + 1
    workbook_rels_xml.append(
        f'<Relationship Id="rId{style_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<bookViews><workbookView activeTab="0"/></bookViews>'
        f'<sheets>{"".join(workbook_sheets_xml)}</sheets>'
        '</workbook>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        '</Relationships>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(workbook_rels_xml)}'
        '</Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        f'{"".join(content_types_xml)}'
        '</Types>'
    )
    core_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:title>SNAP MIP Instance</dc:title>'
        '<dc:creator>snapgen</dc:creator>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
        '</cp:coreProperties>'
    )
    app_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>snapgen</Application>'
        '</Properties>'
    )

    with ZipFile(output, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("docProps/core.xml", core_xml)
        zf.writestr("docProps/app.xml", app_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/styles.xml", _styles_xml())
        for idx, (_sheet_name, rows) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", _worksheet_xml(rows, freeze_header=True))

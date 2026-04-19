from rdc_correlate.mappings import (
    diff_findings,
    inject_section,
    parse_parameters_md,
    render_tentative_section,
)


SAMPLE_MD = """\
# Params

## Confirmed Mappings

| Wire ID | Decimal | Cloud Field |
|---|---|---|
| `0x044C` | 1100 | engineSpeedRpm |
| `0x0453` | 1107 | batteryVoltageV |

## Tentative Mappings

| Wire ID | Decimal | Probable Field |
|---|---|---|
| `0x09EC` | 2540 | utilityVoltageV_B |

## Confirmed Absent

Nothing here.
"""


def test_parse_splits_by_section():
    r = parse_parameters_md(SAMPLE_MD)
    assert r["confirmed"] == {0x044C, 0x0453}
    assert r["tentative"] == {0x09EC}
    assert r["all"] == {0x044C, 0x0453, 0x09EC}


def test_diff_filters_out_known():
    findings = [
        {"param_id": 0x044C, "cloud_path": "engineSpeedRpm", "r": 0.99, "scale": 1.0, "n": 30},
        {"param_id": 0xDEAD, "cloud_path": "unknown_new", "r": 0.98, "scale": 2.5, "n": 40},
    ]
    new = diff_findings(findings, {0x044C, 0x0453, 0x09EC})
    assert len(new) == 1
    assert new[0]["param_id"] == 0xDEAD


def test_render_tentative_section_emits_table():
    f = [{"param_id": 0xDEAD, "cloud_path": "newField", "r": 0.99, "scale": 10.0, "n": 42}]
    md = render_tentative_section(f, "2026-04-18T10:00:00Z")
    assert "Machine-verified discoveries (2026-04-18)" in md
    assert "`0xDEAD`" in md
    assert "`newField`" in md
    assert "| 10.0 | 42 | 0.99 |" in md


def test_render_tentative_empty_returns_empty_string():
    assert render_tentative_section([], "2026-04-18T00:00:00Z") == ""


def test_inject_section_places_before_confirmed_absent():
    md_new = "### Machine-verified discoveries (2026-04-18)\ncontent\n"
    out = inject_section(SAMPLE_MD, md_new)
    abs_idx = out.find("## Confirmed Absent")
    new_idx = out.find("### Machine-verified")
    assert new_idx != -1
    assert new_idx < abs_idx


def test_inject_section_appends_when_no_absent_heading():
    md = "## Confirmed Mappings\nfoo\n"
    new = "### Machine-verified discoveries (x)\nbar\n"
    out = inject_section(md, new)
    assert out.endswith(new)

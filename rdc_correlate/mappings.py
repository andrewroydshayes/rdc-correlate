"""Parse PARAMETERS.md from rdc-protocol-research to know what's already mapped."""

import re


HEX_ID = re.compile(r"`0x([0-9A-Fa-f]{4})`")


def parse_parameters_md(text):
    """Return set of already-confirmed param_ids (int) from the markdown.

    Looks for `0xXXXX` tokens inside tables. Heuristic but robust: any row in
    a markdown table that starts with a hex ID is considered a recorded mapping.
    """
    seen = set()
    # Split into sections on H2 headings
    confirmed = set()
    tentative = set()
    current_section = None
    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            if "confirmed" in heading and "absent" not in heading:
                current_section = "confirmed"
            elif "tentative" in heading:
                current_section = "tentative"
            else:
                current_section = None
            continue
        m = HEX_ID.search(line)
        if not m:
            continue
        pid = int(m.group(1), 16)
        seen.add(pid)
        if current_section == "confirmed":
            confirmed.add(pid)
        elif current_section == "tentative":
            tentative.add(pid)
    return {"all": seen, "confirmed": confirmed, "tentative": tentative}


def diff_findings(findings, recorded):
    """Return the subset of findings whose param_id is not already in `recorded`."""
    return [f for f in findings if f["param_id"] not in recorded]


def render_tentative_section(new_findings, generated_at_iso):
    """Render an additional 'Machine-verified discoveries (YYYY-MM-DD)' subsection
    to append under the existing 'Tentative Mappings' section."""
    if not new_findings:
        return ""
    lines = []
    lines.append(f"### Machine-verified discoveries ({generated_at_iso[:10]})")
    lines.append("")
    lines.append("Emitted by [rdc-correlate](https://github.com/andrewroydshayes/rdc-correlate). Pearson r computed")
    lines.append("against time-aligned Rehlko cloud samples.")
    lines.append("")
    lines.append("| Wire ID | Decimal | Cloud Field | Scale | n | r |")
    lines.append("|---|---|---|---|---|---|")
    for f in new_findings:
        lines.append(
            f"| `0x{f['param_id']:04X}` | {f['param_id']} | `{f['cloud_path']}` | {f['scale']} | {f['n']} | {f['r']} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def inject_section(markdown, new_section):
    """Insert the new subsection just BEFORE the '## Confirmed Absent' heading,
    or at the end if that heading doesn't exist."""
    if not new_section:
        return markdown
    anchor = "## Confirmed Absent"
    idx = markdown.find(anchor)
    if idx == -1:
        return markdown.rstrip() + "\n\n" + new_section
    return markdown[:idx] + new_section + "\n" + markdown[idx:]

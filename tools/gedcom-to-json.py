#!/usr/bin/env python3
"""Convert an Ancestry GEDCOM export into the redacted data the heritage page uses.

    python3 tools/gedcom-to-json.py export.ged

Writes data/tree.json (redacted) and prints a static nested <ol> to stdout for
pasting into heritage/index.html as the no-JavaScript fallback.

The raw .ged is never committed (see .gitignore) and never uploaded. Redaction
happens HERE, not in the browser: an individual judged living is emitted with an
id and their family links only, so their name and dates exist nowhere in the
published output and cannot be recovered from view-source.
"""

import json
import pathlib
import re
import sys
from datetime import date

# An individual is treated as living unless proven otherwise.
LIFESPAN = 100

# Tags carrying free text, contact details, media or Ancestry back-references.
# Dropped from every record, living or dead.
STRIP_TAGS = {"NOTE", "ADDR", "PHON", "EMAIL", "WWW", "OBJE", "FILE", "SOUR",
              "_APID", "_LINK", "RIN", "AFN", "CONT", "CONC"}

ANCESTRY_URL = re.compile(r"(ancestry\.[a-z.]+|/tree/person|_APID)", re.I)
YEAR = re.compile(r"\b(\d{3,4})\b")


def parse(path):
    """GEDCOM lines -> nested records. Levels are the whole grammar."""
    records, stack = [], []
    for raw in pathlib.Path(path).read_text(encoding="utf-8-sig",
                                            errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(" ", 2)
        if len(parts) < 2 or not parts[0].isdigit():
            continue
        level = int(parts[0])
        if parts[1].startswith("@"):                     # 0 @I1@ INDI
            xref, tag = parts[1].strip("@"), (parts[2] if len(parts) > 2 else "")
            value = ""
        else:
            xref, tag = None, parts[1]
            value = parts[2] if len(parts) > 2 else ""
        node = {"tag": tag, "xref": xref, "value": value, "children": []}
        del stack[level:]
        (records if level == 0 else stack[level - 1]["children"]).append(node)
        stack.append(node)
    return records


def child(node, tag):
    return next((c for c in node["children"] if c["tag"] == tag), None)


def year_of(node, tag):
    ev = child(node, tag)
    if not ev:
        return None
    d = child(ev, "DATE")
    if not d:
        return None
    m = YEAR.search(d["value"])
    return int(m.group(1)) if m else None


def is_living(birth, death, has_death_record, this_year):
    if has_death_record:
        return False
    if birth is None:
        return True
    return birth > this_year - LIFESPAN


def clean(text):
    """Refuse anything that smells like an Ancestry back-reference."""
    return "" if not text or ANCESTRY_URL.search(text) else text.strip()


def convert(path, this_year=None):
    this_year = this_year or date.today().year
    records = parse(path)

    people, families, redacted = {}, {}, 0
    for rec in records:
        if rec["tag"] == "INDI" and rec["xref"]:
            rec["children"] = [c for c in rec["children"]
                               if c["tag"] not in STRIP_TAGS]
            birth, death = year_of(rec, "BIRT"), year_of(rec, "DEAT")
            has_death = child(rec, "DEAT") is not None
            pid = rec["xref"]

            if is_living(birth, death, has_death, this_year):
                people[pid] = {"id": pid, "living": True, "name": "Living"}
                redacted += 1
                continue

            nm = child(rec, "NAME")
            name = clean(nm["value"].replace("/", "").strip()) if nm else ""
            people[pid] = {
                "id": pid,
                "living": False,
                "name": name or "Unknown",
                "birth": birth,
                "death": death,
                "place": clean((child(child(rec, "BIRT") or rec, "PLAC") or {}).get("value", "")),
            }
        elif rec["tag"] == "FAM" and rec["xref"]:
            families[rec["xref"]] = {
                "husb": (child(rec, "HUSB") or {}).get("value", "").strip("@") or None,
                "wife": (child(rec, "WIFE") or {}).get("value", "").strip("@") or None,
                "children": [c["value"].strip("@") for c in rec["children"]
                             if c["tag"] == "CHIL"],
            }

    # Parent -> children edges, which is all the descendant tree needs.
    for p in people.values():
        p["children"] = []
    for fam in families.values():
        for parent in (fam["husb"], fam["wife"]):
            if parent in people:
                for kid in fam["children"]:
                    if kid in people and kid not in people[parent]["children"]:
                        people[parent]["children"].append(kid)

    has_parent = {k for f in families.values() for k in f["children"]}
    roots = [p["id"] for p in people.values() if p["id"] not in has_parent]

    return {
        "meta": {
            "generated": this_year,
            "redactionRule": f"no death record and born after {this_year - LIFESPAN}",
            "redactedCount": redacted,
            "total": len(people),
        },
        "roots": roots,
        "people": people,
    }


def as_list(data, pid, depth=0, seen=None):
    """Static nested <ol> — the tree without JavaScript."""
    seen = seen if seen is not None else set()
    if pid in seen or pid not in data["people"]:
        return ""
    seen.add(pid)
    p, pad = data["people"][pid], "  " * depth
    if p["living"]:
        label = '<span class="tree__name tree__name--living">Living</span>'
    else:
        span = ""
        if p.get("birth") or p.get("death"):
            span = f'<span class="tree__dates">{p.get("birth") or "?"}–{p.get("death") or "?"}</span>'
        label = f'<span class="tree__name">{p["name"]}</span>{span}'
    kids = "".join(as_list(data, c, depth + 2, seen) for c in p["children"])
    inner = f'\n{pad}  <ol>{kids}\n{pad}  </ol>' if kids else ""
    return f'\n{pad}<li id="p-{pid}">{label}{inner}\n{pad}</li>'


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    data = convert(sys.argv[1])
    out = pathlib.Path("data/tree.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    m = data["meta"]
    print(f"wrote {out}: {m['total']} people, {m['redactedCount']} redacted as Living",
          file=sys.stderr)
    for root in data["roots"]:
        print(as_list(data, root))

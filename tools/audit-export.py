#!/usr/bin/env python3
"""Audit a real GEDCOM against the published output before you deploy.

    python3 tools/audit-export.py path/to/export.ged

Reads the raw export, works out which individuals should have been redacted,
and checks whether any string belonging only to them reached data/tree.json or
heritage/index.html.

Strings shared with a deceased individual (a common place name, a year that is
also someone's death date) are reported separately: those are collisions, not
disclosures, and adjudicating them automatically is the whole point of this
script. Anything listed under DISCLOSURES is a real problem.

Exits non-zero if there is a disclosure, so it can gate a deploy.
"""

import json
import pathlib
import re
import sys
from datetime import date

LIFESPAN = 100
OUTPUTS = ("data/tree.json", "heritage/index.html")
VENDOR = ("_APID", "_OID", "_USER", "ancestry.")


def read_individuals(path):
    people, cur, key = [], None, None
    for raw in pathlib.Path(path).read_text(encoding="utf-8-sig",
                                            errors="replace").splitlines():
        s = raw.strip()
        p = s.split(" ", 2)
        if len(p) >= 3 and p[0] == "0" and p[1].startswith("@") and p[2] == "INDI":
            cur = {"names": [], "dates": [], "places": [], "death": False, "birth": None}
            people.append(cur)
            key = None
            continue
        if p[0] == "0":
            cur = None
            continue
        if cur is None:
            continue
        tag = p[1] if len(p) > 1 else ""
        val = p[2] if len(p) > 2 else ""
        if p[0] == "1":
            key = tag
        if tag == "NAME" and val:
            cur["names"].append(val.replace("/", " ").strip())
        if tag in ("GIVN", "SURN") and val:
            cur["names"].append(val.strip())
        if tag == "DEAT":
            cur["death"] = True
        if tag == "DATE" and val:
            cur["dates"].append(val.strip())
            if key == "BIRT":
                m = re.search(r"\b(\d{4})\b", val)
                cur["birth"] = int(m.group(1)) if m else None
        if tag == "PLAC" and val:
            cur["places"].append(val.strip())
    return people


def tokens(person):
    out = set()
    for n in person["names"]:
        out.update(t for t in re.split(r"[\s,]+", n) if len(t) > 3)
    out.update(d for d in person["dates"] if len(d) > 3)
    out.update(p for p in person["places"] if len(p) > 3)
    return out


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    this_year = date.today().year
    people = read_individuals(sys.argv[1])
    living = [p for p in people
              if not p["death"] and (p["birth"] is None or p["birth"] > this_year - LIFESPAN)]
    dead = [p for p in people if p not in living]

    private = set().union(*(tokens(p) for p in living)) if living else set()
    public = set().union(*(tokens(p) for p in dead)) if dead else set()

    blob = "".join(pathlib.Path(f).read_text(encoding="utf-8")
                   for f in OUTPUTS if pathlib.Path(f).exists()).lower()

    # The site owner is not a third party on their own site: their name is in the
    # byline, the copyright and the meta author tag by design. Take the name from
    # the page itself rather than hardcoding it, and say so in the report.
    owner_tokens = set()
    page = pathlib.Path("heritage/index.html")
    if page.exists():
        m = re.search(r'<meta name="author" content="([^"]+)"', page.read_text(encoding="utf-8"))
        if m:
            owner_tokens = {t.lower() for t in re.split(r"[\s,]+", m.group(1)) if len(t) > 3}

    disclosures, collisions = [], []
    for s in sorted(private):
        if s.lower() not in blob:
            continue
        if s.lower() in owner_tokens:            # the author's own byline
            continue
        # Shared with someone published, or a substring of their data? Collision.
        shared = s.lower() in {p.lower() for p in public} or \
            any(s.lower() in p.lower() for p in public)
        (collisions if shared else disclosures).append(s)

    print(f"individuals: {len(people)}  living: {len(living)}  published: {len(dead)}")
    print(f"private strings checked: {len(private)}")
    if owner_tokens:
        print(f"site owner's own name excluded: {sorted(owner_tokens)}")

    tree = pathlib.Path("data/tree.json")
    if tree.exists():
        d = json.loads(tree.read_text(encoding="utf-8"))
        allowed = {"id", "living", "name", "children", "parents"}
        bad = [p["id"] for p in d["people"].values()
               if p["living"] and set(p) != allowed]
        print(f"living records with extra keys: {bad or 'none'}")
        # A living record carrying anything beyond ids and the Living label is a
        # disclosure by construction, whether or not the value came from the
        # export. This must fail the audit, not merely be reported.
        for pid in bad:
            extra = sorted(set(d["people"][pid]) - allowed)
            disclosures.append(f"living record {pid} carries {extra}")
        for pid, person in d["people"].items():
            if person["living"] and person.get("name") != "Living":
                disclosures.append(f"living record {pid} is named {person.get('name')!r}")
        for v in VENDOR:
            n = tree.read_text(encoding="utf-8").lower().count(v.lower())
            if n:
                disclosures.append(f"{v} appears {n}x in data/tree.json")

    if collisions:
        print(f"\ncollisions ({len(collisions)}) — shared with a published individual, not a leak:")
        for c in collisions:
            print(f"    {c}")
    if disclosures:
        print(f"\nDISCLOSURES ({len(disclosures)}) — unique to a living individual:")
        for x in disclosures:
            print(f"    {x}")
        print("\nAUDIT: FAIL")
        return 1
    print("\nAUDIT: PASS — nothing unique to a living individual reached the output")
    return 0


if __name__ == "__main__":
    sys.exit(main())

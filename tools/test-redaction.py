#!/usr/bin/env python3
"""Prove the GEDCOM converter never emits a living person's details.

    python3 tools/test-redaction.py

Run this before publishing any change that touches the converter or the tree
data. It builds a synthetic export containing a living relative with a name,
birth date, address, phone, email, note and Ancestry back-reference, converts
it, and asserts none of those strings survive into the output.
"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import importlib.util

spec = importlib.util.spec_from_file_location(
    "conv", pathlib.Path(__file__).parent / "gedcom-to-json.py")
conv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conv)

SYNTHETIC = """0 HEAD
0 @I1@ INDI
1 NAME Hector /Maclaine/
1 BIRT
2 DATE 12 MAR 1841
2 PLAC Lochbuie, Isle of Mull
1 DEAT
2 DATE 4 JUN 1903
1 FAMS @F1@
0 @I2@ INDI
1 NAME SECRETNAME /SECRETSURNAME/
1 BIRT
2 DATE 17 SEP 1988
2 PLAC 42 SECRETSTREET, Melbourne
1 ADDR 42 SECRETSTREET
1 EMAIL secret@example.com
1 PHON +61400111222
1 NOTE SECRETNOTE
1 _APID 1,60525::9999999
1 WWW https://www.ancestry.com/family-tree/person/tree/1/person/2
1 FAMC @F1@
0 @I3@ INDI
1 NAME Mary /Ross/
1 BIRT
2 DATE 1866
1 DEAT
2 DATE 1940
1 FAMS @F1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I3@
1 CHIL @I2@
0 TRLR
"""

MUST_NOT_APPEAR = ["SECRETNAME", "SECRETSURNAME", "SECRETSTREET", "SECRETNOTE",
                   "secret@example.com", "+61400111222", "ancestry.com",
                   "_APID", "1988", "Melbourne"]
MUST_APPEAR = ["Hector Maclaine", "1841", "1903", "Mary Ross"]


def main():
    with tempfile.NamedTemporaryFile("w", suffix=".ged", delete=False) as fh:
        fh.write(SYNTHETIC)
        path = fh.name

    data = conv.convert(path, this_year=2026)
    blob = repr(data) + "".join(conv.as_list(data, r) for r in data["roots"])

    failures = []
    for needle in MUST_NOT_APPEAR:
        if needle.lower() in blob.lower():
            failures.append(f"LEAKED: {needle!r} reached the output")
    for needle in MUST_APPEAR:
        if needle.lower() not in blob.lower():
            failures.append(f"MISSING: {needle!r} should be published")

    living = data["people"]["I2"]
    if set(living) != {"id", "living", "name", "children"}:
        failures.append(f"living record has unexpected keys: {sorted(living)}")
    if living["name"] != "Living":
        failures.append(f"living record name is {living['name']!r}, not 'Living'")
    if data["meta"]["redactedCount"] != 1:
        failures.append(f"expected 1 redaction, got {data['meta']['redactedCount']}")

    pathlib.Path(path).unlink()

    if failures:
        for f in failures:
            print("  " + f)
        print("REDACTION TEST: FAIL")
        return 1
    print(f"  {len(MUST_NOT_APPEAR)} private strings withheld, "
          f"{len(MUST_APPEAR)} public facts kept, living record shape correct")
    print("REDACTION TEST: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

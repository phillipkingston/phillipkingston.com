#!/usr/bin/env python3
"""Render tartan setts to SVG from published threadcounts.

Writes one SVG per tartan into img/. Run from the repository root:

    python3 tools/make-tartans.py

Every threadcount, palette and reference below is transcribed from a published
source, named in PROVENANCE. Nothing here is invented: a tartan is a record,
and a sett that does not match its source is a forgery rather than a mistake.

The Scottish Register of Tartans holds the authoritative record but reveals
threadcounts only behind a login, so these counts come from published
transcriptions of the same pre-2009 Scottish Tartans Society records, and each
was cross-checked against at least two independent collections. Where the
collections disagree the disagreement is stated on the page, not smoothed over.

The restricted Maclaine of Lochbuie Auld Sett (register ref 12067) is
deliberately absent: it needs the Chief's written permission.
"""

import os
import re
import sys

# Thread width in the SVG user space is 1, so a viewBox is the sett in threads.
HATCH_DIVISOR = 90      # twill hatch spacing, as a fraction of the sett
WEFT_ALPHA = 0.5        # a crossing at half alpha is the mean of the two threads


# --- Data -------------------------------------------------------------------
# name, slug, threadcount, palette {code: (hex, display name)}, reference

TARTANS = [
    {
        "slug": "maclaine-of-lochbuie",
        "name": "Maclaine of Lochbuie",
        "count": "R/64 HG16 A8 Y/2",
        "ref": "STA/STWR 1462",
        "palette": {
            "R": ("#C80000", "red"),
            "HG": ("#285800", "hunting green"),
            "A": ("#5C8CA8", "azure"),
            "Y": ("#E8C000", "yellow"),
        },
    },
    {
        "slug": "mcfadyen",
        "name": "McFadyen",
        "record": "MacFadzean",
        "count": "B/96 W4 K40 G44 R6 G/8",
        "ref": "STWR 645",
        "palette": {
            "B": ("#2C4084", "blue"),
            "W": ("#E0E0E0", "white"),
            "K": ("#101010", "black"),
            "G": ("#005020", "green"),
            "R": ("#DC0000", "red"),
        },
    },
    {
        "slug": "ross",
        "name": "Ross",
        "count": ("G/36 R4 G36 R36 G4 R8 G4 R36 B36 R4 B36 R36 B2 R2 B4 R2 "
                  "B2 R36 B2 R2 B4 R2 B2 R36 G36 R4 G/36"),
        "ref": "STWR 864",
        "palette": {
            "G": ("#005020", "green"),
            "R": ("#DC0000", "red"),
            "B": ("#2C4084", "blue"),
        },
    },
    {
        "slug": "anderson",
        "name": "Anderson",
        "count": ("R/6 AL12 R4 K4 R4 AL36 K6 W6 K6 DY4 K4 DY4 K8 R4 B8 R6 "
                  "G12 R4 G12 R/8"),
        "ref": "STA/STWR 1394",
        "palette": {
            "R": ("#C80000", "red"),
            "AL": ("#48A4C0", "Anderson blue"),
            "K": ("#101010", "black"),
            "W": ("#E0E0E0", "white"),
            "DY": ("#E8C000", "gold"),
            "B": ("#2C2C80", "blue"),
            "G": ("#006818", "green"),
        },
    },
]

# Two setts with a thread total published independently of any threadcount, by
# the chief's own clan society. They are the external check on the pivot rule
# below: get the reflection wrong and neither total comes out.
SELF_TEST = [
    ("R/64 HG16 A8 Y/2", 114),   # Maclaine of Lochbuie (Coburn)
    ("B/64 R6 B8 Y/6", 98),      # Maclaine of Lochbuie hunting
]

TOKEN = re.compile(r"^([A-Z]+)(/?)(\d+)$")


# --- Sett expansion ---------------------------------------------------------

def parse(count):
    """Return [(colour, pivot, threads)] for a threadcount string."""
    out = []
    for tok in count.split():
        m = TOKEN.match(tok)
        if not m:
            raise ValueError("cannot read threadcount token %r" % tok)
        out.append((m.group(1), m.group(2) == "/", int(m.group(3))))
    return out


def expand(count):
    """Expand a threadcount to the full sett as [(colour, threads)].

    A "/" marks a pivot. The half sett runs from the first pivot to the last
    inclusive; the full sett is the half sett followed by the reverse of the
    half sett with both pivot stripes dropped, because a pivot stripe is shared
    between the two halves rather than repeated. A count with no pivot is
    already a full sett and simply repeats.
    """
    toks = parse(count)
    pivots = [i for i, t in enumerate(toks) if t[1]]
    if len(pivots) < 2:
        return [(c, n) for c, _, n in toks]
    half = toks[pivots[0]:pivots[-1] + 1]
    full = list(half) + list(reversed(half[1:-1]))
    return [(c, n) for c, _, n in full]


def self_test():
    for count, total in SELF_TEST:
        got = sum(n for _, n in expand(count))
        if got != total:
            sys.exit("self-test failed: %s expands to %d threads, published "
                     "total is %d" % (count, got, total))
    print("self-test: pivot expansion matches both published sett totals "
          "(%s)" % ", ".join(str(t) for _, t in SELF_TEST))


# --- Rendering --------------------------------------------------------------

def stripes(sett):
    """[(colour, start, width)] over the full sett."""
    out, x = [], 0
    for colour, n in sett:
        out.append((colour, x, n))
        x += n
    return out


def alt_text(t, sett, total):
    seen = []
    for colour, _ in sett:
        if colour not in seen:
            seen.append(colour)
    ordered = sorted(seen, key=lambda c: -sum(n for cc, n in sett if cc == c))
    names = [t["palette"][c][1] for c in ordered]
    if len(names) > 1:
        names = ", ".join(names[:-1]) + " and " + names[-1]
    else:
        names = names[0]
    article = "an" if str(total)[0] in "8" else "a"
    recorded = ("" if t.get("record") in (None, t["name"])
                else ", recorded as %s" % t["record"])
    return ("The %s tartan%s: %s %d-thread sett in %s."
            % (t["name"], recorded, article, total, names))


def render(t):
    sett = expand(t["count"])
    total = sum(n for _, n in sett)
    bars = stripes(sett)
    hex_of = lambda c: t["palette"][c][0]

    tile = max(2, round(total / HATCH_DIVISOR))
    hair = max(0.5, total / 900.0)

    L = []
    L.append('<svg xmlns="http://www.w3.org/2000/svg" '
             'viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
             'aria-labelledby="t">' % (total, total, total, total))
    L.append('<title id="t">%s</title>' % alt_text(t, sett, total))
    L.append('<!-- %s. %s. One full sett, %d threads, expanded from the '
             'published threadcount: %s -->'
             % (t["name"], t["ref"], total, t["count"]))

    # Twill hatch: a 2/2 twill runs on the diagonal, so a faint diagonal
    # suggests cloth rather than a grid. Texture, not a claim about the weave.
    L.append('<defs><pattern id="twill" patternUnits="userSpaceOnUse" '
             'width="%d" height="%d" patternTransform="rotate(45)">'
             '<line x1="0" y1="0" x2="0" y2="%d" stroke="#ffffff" '
             'stroke-width="%.3f" stroke-opacity="0.10"/></pattern></defs>'
             % (tile, tile, tile, hair))

    # Warp: vertical threads.
    L.append('<g>')
    for colour, x, w in bars:
        L.append('<rect x="%d" y="0" width="%d" height="%d" fill="%s"/>'
                 % (x, w, total, hex_of(colour)))
    L.append('</g>')

    # Weft: horizontal threads at half alpha, so each crossing shows the mean
    # of the two thread colours — which is what a 50/50 mix reads as.
    L.append('<g fill-opacity="%s">' % WEFT_ALPHA)
    for colour, y, h in bars:
        L.append('<rect x="0" y="%d" width="%d" height="%d" fill="%s"/>'
                 % (y, total, h, hex_of(colour)))
    L.append('</g>')

    L.append('<rect width="%d" height="%d" fill="url(#twill)"/>'
             % (total, total))

    L.append('</svg>')
    return "\n".join(L) + "\n", total, alt_text(t, sett, total)


def main():
    self_test()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "img")
    if not os.path.isdir(out_dir):
        sys.exit("no img/ directory at %s" % out_dir)
    for t in TARTANS:
        svg, total, alt = render(t)
        path = os.path.join(out_dir, "tartan-%s.svg" % t["slug"])
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print("%-34s %5d threads  %6d bytes  %s"
              % (os.path.relpath(path, root), total, len(svg.encode("utf-8")),
                 t["ref"]))
        print("    alt: %s" % alt)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Draw a stylised map of Scotland marking the two clan seats and Applecross.

    python3 tools/make-scotland-map.py ne_10m_admin_0_map_subunits.geojson

Prints an <svg> block on stdout for pasting into heritage/index.html. It is
inline rather than a file because the coastline is stroked in var(--ink) and has
to follow the site's three-state theme toggle, which an <img>-loaded SVG cannot.

Coastline: Natural Earth 1:10m admin-0 map subunits, subunit "Scotland".
Natural Earth is public domain. The file is not committed; pass it as argv[1].
Get it from https://github.com/nvkelso/natural-earth-vector (geojson/).

The three marks are seats and origins — a castle, a castle, an abbacy — not
clan territories. Historical clan boundaries are contested and drawing them
would be invention, so the map does not.
"""

import json
import math
import sys

# --- Frame ------------------------------------------------------------------
# The main frame stops short of Shetland, which goes in an inset. Fitting
# Shetland into the same frame would shrink Mull, and Lochbuie is on Mull.

MAIN = dict(lon0=-7.75, lon1=-0.70, lat0=54.55, lat1=59.30)
INSET = dict(lon0=-1.95, lon1=-0.60, lat0=59.75, lat1=60.90)

STD_PARALLEL = 57.0        # x scaled by cos(this), so the aspect is right
AREA_MIN = 0.012           # square degrees; drops skerries, keeps real islands
TOLERANCE = 0.013          # Douglas-Peucker, in projected units

MAP_H = 560.0              # main frame height in user units
PAD_L, PAD_R, PAD_T, PAD_B = 92.0, 112.0, 16.0, 26.0

# --- Places -----------------------------------------------------------------
# lat, lon fetched from the cited sources; label and leader anchors chosen so
# every leader runs over open water rather than across an island.

PLACES = [
    {
        "name": "Lochbuie",
        "gloss": "Moy Castle, Isle of Mull",
        "at": (56.35583, -5.85861),
        "to": (55.95, -6.70),
        "anchor": "end",
    },
    {
        # Due east, which is the one bearing out of Applecross that crosses no
        # coastline at all: the peninsula is hemmed in by sea lochs on every
        # other side. The label lands in the blank interior of the mainland.
        "name": "Applecross",
        "gloss": "the hereditary abbacy",
        "at": (57.43304, -5.80958),
        "to": (57.43304, -4.95),
        "anchor": "start",
    },
    {
        "name": "Balnagown",
        "gloss": "Easter Ross",
        "at": (57.74940, -4.08060),
        "to": (58.15, -2.60),
        "anchor": "start",
    },
]


# --- Geometry ---------------------------------------------------------------

def ring_area(ring):
    s = 0.0
    for i in range(len(ring) - 1):
        s += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return abs(s) / 2.0


def simplify(points, tol):
    """Douglas-Peucker. Keeps the endpoints; drops points inside tol of the
    chord they sit on."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi - lo < 2:
            continue
        ax, ay = points[lo]
        bx, by = points[hi]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        worst, at = -1.0, None
        for i in range(lo + 1, hi):
            px, py = points[i]
            if norm == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dy * (px - ax) - dx * (py - ay)) / norm
            if d > worst:
                worst, at = d, i
        if worst > tol:
            keep[at] = True
            stack.append((lo, at))
            stack.append((at, hi))
    return [p for p, k in zip(points, keep) if k]


class Projection(object):
    """Equirectangular with x scaled by cos(standard parallel). Over five
    degrees of latitude this is visually indistinguishable from Mercator and
    needs no iteration."""

    def __init__(self, frame, height, ox, oy):
        self.k = math.cos(math.radians(STD_PARALLEL))
        self.f = frame
        w = (frame["lon1"] - frame["lon0"]) * self.k
        h = frame["lat1"] - frame["lat0"]
        self.s = height / h
        self.w = w * self.s
        self.h = height
        self.ox, self.oy = ox, oy

    def xy(self, lat, lon):
        x = self.ox + (lon - self.f["lon0"]) * self.k * self.s
        y = self.oy + (self.f["lat1"] - lat) * self.s
        return x, y

    def inside(self, lat, lon):
        f = self.f
        return f["lon0"] <= lon <= f["lon1"] and f["lat0"] <= lat <= f["lat1"]


def rings_for(geometry):
    out = []
    for poly in geometry["coordinates"]:
        for ring in poly:                      # outer ring, then any holes
            out.append(ring)
            break                              # Scotland has no inland holes
    return out


def path_for(ring, proj):
    pts = [proj.xy(lat, lon) for lon, lat in ring]
    pts = simplify(pts, TOLERANCE * proj.s)
    if len(pts) < 3:
        return None, 0
    d = "M" + " ".join("%.1f,%.1f" % p for p in pts) + "Z"
    return d, len(pts)


# --- Output -----------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    feats = [f for f in data["features"]
             if f["properties"].get("SUBUNIT") == "Scotland"]
    if not feats:
        sys.exit("no feature with SUBUNIT == Scotland in %s" % sys.argv[1])
    rings = [r for r in rings_for(feats[0]["geometry"])
             if ring_area(r) >= AREA_MIN]
    rings.sort(key=ring_area, reverse=True)

    main_p = Projection(MAIN, MAP_H, PAD_L, PAD_T)
    total_w = PAD_L + main_p.w + PAD_R
    total_h = PAD_T + main_p.h + PAD_B

    # The inset sits in the top-right margin, which the main frame leaves empty.
    inset_h = 132.0
    inset_p = Projection(INSET, inset_h, 0, 0)
    ins_x = total_w - inset_p.w - 14.0
    ins_y = 22.0
    inset_p.ox, inset_p.oy = ins_x, ins_y

    L, kept, pts_out = [], 0, 0
    L.append('<svg viewBox="0 0 %.0f %.0f" role="img" '
             'aria-labelledby="map-title map-desc">' % (total_w, total_h))
    L.append('<title id="map-title">Where the two clans held land</title>')
    L.append('<desc id="map-desc">A stylised outline of Scotland marking '
             'Lochbuie on the Isle of Mull, the seat of Maclaine of Lochbuie; '
             'Balnagown in Easter Ross, the seat of Clan Ross; and Applecross '
             'on the west coast, the hereditary abbacy the earls of Ross came '
             'from. Shetland is shown in an inset.</desc>')

    for frame_proj, group in ((main_p, "mp-land"), (inset_p, "mp-land")):
        L.append('<g class="%s">' % group)
        for ring in rings:
            lons = [p[0] for p in ring]
            lats = [p[1] for p in ring]
            cx = (min(lons) + max(lons)) / 2.0
            cy = (min(lats) + max(lats)) / 2.0
            if not frame_proj.inside(cy, cx):
                continue
            d, n = path_for(ring, frame_proj)
            if not d:
                continue
            L.append('<path d="%s"/>' % d)
            kept += 1
            pts_out += n
        L.append('</g>')

    # Inset surround, so a detached Shetland cannot read as an island offshore.
    L.append('<g class="mp-inset">')
    L.append('<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f"/>'
             % (ins_x - 8, ins_y - 8, inset_p.w + 16, inset_p.h + 16))
    L.append('<text x="%.0f" y="%.0f">Shetland</text>'
             % (ins_x - 8, ins_y + inset_p.h + 22))
    L.append('</g>')

    # Marks.
    for p in PLACES:
        lat, lon = p["at"]
        x, y = main_p.xy(lat, lon)
        dx = -9 if p["anchor"] == "end" else 9
        L.append('<g class="mp-mark">')
        if p["to"]:
            tx, ty = main_p.xy(*p["to"])
            L.append('<path class="mp-lead" d="M%.1f,%.1f L%.1f,%.1f"/>'
                     % (x, y, tx, ty))
        else:
            tx, ty = x, y + 4
        L.append('<circle class="mp-dot" cx="%.1f" cy="%.1f" r="3.2"/>'
                 % (x, y))
        L.append('<text class="mp-place" x="%.1f" y="%.1f" '
                 'text-anchor="%s">%s</text>'
                 % (tx + dx, ty, p["anchor"], p["name"].upper()))
        L.append('<text class="mp-gloss" x="%.1f" y="%.1f" '
                 'text-anchor="%s">%s</text>'
                 % (tx + dx, ty + 15, p["anchor"], p["gloss"]))
        L.append('</g>')

    L.append('</svg>')

    sys.stderr.write("rings kept: %d   points after simplification: %d\n"
                     % (kept, pts_out))
    sys.stdout.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

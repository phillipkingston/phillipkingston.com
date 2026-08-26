#!/usr/bin/env python3
"""Render the four-line chronology, 2000 BC to 1600, as SVG and as list rows.

    python3 tools/make-chronology.py           # both, to stdout
    python3 tools/make-chronology.py --svg     # the figure only
    python3 tools/make-chronology.py --rows    # the dated list only

Both views come out of the one EVENTS table below, so the figure and the list
cannot drift apart. The SVG goes inline in the page rather than into a file:
its ink is var(--ink) and has to follow the site's three-state theme toggle,
which an <img>-loaded SVG cannot do.

The time axis is deliberately broken into three segments at different scales.
Thirty of the thirty-four events fall after 1200, and a linear axis would put
four thousand years of prehistory in a smear at the left and stack the rest on
top of each other at the right. The breaks are drawn and the spans are labelled,
because a compressed axis that hides its compression misrepresents the very
thing this page is about: the record is thin early and thick late.
"""

import sys

M, L, R, A = "M", "L", "R", "A"
LANES = [(M, "McFadyen"), (L, "Maclaine"), (R, "Ross"), (A, "Anderson")]
ALL = (M, L, R, A)

# year, display year, title, detail, lines touched, label it on the figure?
EVENTS = [
    (-2450, "c. 2450 BC", "Beaker migration",
     "Around 90% of British Y-lineages replaced. Whatever these paternal lines "
     "were doing before this, they were not doing it in Britain.", ALL, True),
    (-2000, "c. 2000 BC", "The Rathlin men",
     "Three Early Bronze Age men from Rathlin Island: R1b-L21, about 32% steppe "
     "ancestry, blue-eye haplotypes, lactase persistence. Closest to modern "
     "Irish, Scottish and Welsh.", ALL, True),
    (-1980, "c. 2000 BC", "Lochbuie stone circle already old",
     "Nine granite slabs, 12.3 m across, standing on Mull for centuries already "
     "— built by the population the Beaker migrants replaced.", (M, L), False),
    (-1000, "1000–875 BC", "Continental influx into southern Britain",
     "Farmer ancestry rises in England and Wales through migrants closest to "
     "Iron Age France. Scotland sits it out.", ALL, False),
    (500, "c. AD 500", "Dál Riata",
     "Cenél Loairn hold Lorn and Mull. The ancestral polity of both "
     "Hebridean lines.", (M, L), False),
    (563, "563", "Columba founds Iona",
     "Five miles from Mull. For two centuries the best-documented place in "
     "northern Britain.", (M, L), True),
    (685, "685", "Dun Nechtain",
     "The Picts halt Northumbrian expansion. The northern and north-eastern "
     "ground is Pictish, not Dál Riatan.", (R, A), False),
    (795, "795–825", "Viking raids on Iona",
     "The annalistic record shifts from Iona to Ireland, and western Scotland "
     "stops being reported consistently. Argyll did not stop having a history; "
     "it stopped having a historian.", (M, L), True),
    (1100, "c. 1100–1300", "Hereditary surnames form",
     "None of these four names existed before this window. Any named chief of "
     "any of them before about 1100 is fiction.", ALL, False),
    (1215, "1215", "Fearchar knighted",
     "For crushing the rebellion in Moray and Ross against Alexander II. Most "
     "accounts give the day as 15 June.", (R,), True),
    (1226, "c. 1226", "Fearchar created Earl of Ross",
     "Probably 1226, possibly 1221; certainly styled Comes de Ross by 1232.",
     (R,), False),
    (1251, "1251", "Fearchar dies",
     "Buried at Fearn Abbey, which he had founded and moved. The 1251 date is "
     "traditional; he was certainly dead by the 1250s.", (R,), False),
    (1263, "1263", "Battle of Largs",
     "Gillean of the Battleaxe is placed here by tradition, not by record.",
     (L,), False),
    (1266, "1266", "Treaty of Perth",
     "The Hebrides pass from Norway to Scotland.", (M, L), False),
    (1296, "1296", "David and Duncan fiz Andreu swear fealty",
     "Burgess of Peebles and a man of Dumfries. The earliest Andersons on "
     "record, in French, in the Lowlands.", (A,), False),
    (1304, "1304", "Malcolm Macpadene, charter witness, Kintyre",
     "The earliest instance of the surname anywhere. It survives as a recital "
     "inside a confirmation registered at least 120 years later, so the "
     "name-form has passed through a fifteenth-century clerk's hands.",
     (M,), True),
    (1314, "1314", "Bannockburn",
     "Walter of Ross killed.", (R,), False),
    (1354, "1354", "Mull detached from Lorn",
     "The exiled MacDougall heir quitclaims any right over Mull to the Lord of "
     "the Isles.", (M, L), False),
    (1360, "1360", "Hector Reaganach granted Lochbuie",
     "Four score merks of land that had been occupied by the McFadyens. From "
     "here the two Mull lines are bound together, one as lord and one as "
     "tenant.", (M, L), True),
    (1372, "1372", "The earldom leaves Clan Ross",
     "Uilleam III dies without sons; the Earldom of Ross passes toward the "
     "MacDonald Lords of the Isles.", (R,), False),
    (1374, "1374", "Hugh Ross, 1st of Balnagown",
     "The chiefship separates from the earldom and settles at Balnagown, where "
     "it still is.", (R,), False),
    (1390, "1390", "Conghan MacPaden petitions for the archdeaconry of Argyll",
     "One of the few McFadyens visible in the fifteenth century — because "
     "he touched an institution with a writing desk.", (M,), False),
    (1457, "1457", "John McFadyeane in Edinburgh",
     "Exchequer Rolls.", (M,), False),
    (1473, "1473", "Donald M'Fadzeane in Kirkcudbright",
     "A composition made. The z spelling, and the southwest.", (M,), False),
    (1476, "1476", "Earldom of Ross forfeited to the Crown",
     "The Balnagown chiefs are regional lairds now, not provincial magnates.",
     (R,), True),
    (1493, "1493", "Lordship of the Isles forfeited",
     "Its archive did not survive. This is the single largest reason the west "
     "has no records for this period.", (M, L), True),
    (1494, "1494", "Iain Òg of Lochbuie chartered by James IV",
     "March 1494, two years ahead of Duart: vassals of the Lord of the Isles "
     "become tenants-in-chief of the Crown.", (L,), False),
    (1507, "1507–1540", "Donald Macfadzane, precentor of Lismore",
     "Probably the same man as Sir Donald McFadzeane, chaplain of Tibbermore, "
     "whose death is recorded in 1540.", (M,), False),
    (1532, "1532", "M'Faden on Iona",
     "And Finlay M'Fedden, canon of the Isles, witnessing a charter of "
     "Muckairn.", (M,), False),
    (1539, "1539–40", "Murchadh Gearr flees to Antrim, then retakes Moy",
     "Dispossessed by his uncle with Duart's backing; back within the year with "
     "the MacCormacks.", (L,), False),
    (1553, "1553", "First surviving Scottish parish register",
     "Errol, Perthshire. Required from 1552; most parishes far later, and "
     "Argyll far later again.", ALL, True),
    (1566, "1566", "Forman-Workman armorial: Anderson of that Ilk",
     "The name becomes visible as a family rather than a patronymic.",
     (A,), False),
    (1598, "1598", "Tràigh Ghruinneart",
     "Hector, 8th of Lochbuie, fights with the MacDonalds of Islay against "
     "Duart.", (L,), False),
    (1600, "c. 1600", "Hector, 8th of Lochbuie, adopts the Maclaine spelling",
     "Until now Lochbuie and Duart wrote the name the same way. This is the "
     "point at which a Maclaine line becomes a distinguishable object at all.",
     (L,), True),
]

# --- Figure geometry --------------------------------------------------------

# Three segments, each with its own scale. Fractions of the plot width.
SEGMENTS = [
    (-2500, 500, 0.22, "2500 BC – AD 500"),
    (500, 1200, 0.20, "500 – 1200"),
    (1200, 1640, 0.58, "1200 – 1600"),
]

GUTTER = 96.0      # lane names
PLOT_W = 700.0
PAD_R = 18.0
TOP = 40.0         # segment captions
LANE_H = 30.0
AXIS_GAP = 22.0
LABEL_H = 46.0     # two staggered rows of year labels
BREAK_W = 9.0      # visual width of a break mark


def x_of(year):
    """Project a year onto the broken axis."""
    x = GUTTER
    for lo, hi, frac, _ in SEGMENTS:
        w = PLOT_W * frac
        if year <= lo:
            return x
        if year <= hi:
            return x + w * (year - lo) / float(hi - lo)
        x += w
    return x


def svg():
    lanes_top = TOP + 14
    axis_y = lanes_top + LANE_H * len(LANES) + AXIS_GAP
    total_w = GUTTER + PLOT_W + PAD_R
    total_h = axis_y + LABEL_H

    O = []
    O.append('<svg viewBox="0 0 %.0f %.0f" role="img" '
             'aria-labelledby="chr-title chr-desc">' % (total_w, total_h))
    O.append('<title id="chr-title">Four lines against a broken time axis, '
             '2450 BC to 1600</title>')
    O.append('<desc id="chr-desc">Four horizontal lanes — McFadyen, '
             'Maclaine, Ross and Anderson — with a mark on each lane an '
             'event touches. The time axis is broken into three segments at '
             'different scales, because thirty of the thirty-four events fall '
             'after 1200. Events touching all four lines are drawn as a rule '
             'across every lane. The dated list below carries every event in '
             'full.</desc>')

    # Segment captions and the two break marks.
    x = GUTTER
    for i, (lo, hi, frac, caption) in enumerate(SEGMENTS):
        w = PLOT_W * frac
        O.append('<text class="cr-era" x="%.1f" y="%.1f">%s</text>'
                 % (x + w / 2.0, TOP - 16, caption))
        O.append('<line class="cr-seg" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                 % (x + 2, TOP - 8, x + w - 2, TOP - 8))
        if i:
            O.append('<g class="cr-break">'
                     '<path d="M%.1f,%.1f l6,-9"/><path d="M%.1f,%.1f l6,-9"/>'
                     '</g>' % (x - BREAK_W / 2, TOP - 3, x + 1, TOP - 3))
        x += w

    # Lanes.
    for i, (key, name) in enumerate(LANES):
        y = lanes_top + LANE_H * i + LANE_H / 2.0
        O.append('<text class="cr-lane" x="%.1f" y="%.1f" '
                 'text-anchor="end">%s</text>' % (GUTTER - 14, y + 3.5, name))
        O.append('<line class="cr-track" x1="%.1f" y1="%.1f" x2="%.1f" '
                 'y2="%.1f"/>' % (GUTTER, y, GUTTER + PLOT_W, y))

    lane_y = {k: lanes_top + LANE_H * i + LANE_H / 2.0
              for i, (k, _) in enumerate(LANES)}
    top_y = lanes_top + 4
    bot_y = lanes_top + LANE_H * len(LANES) - 4

    # Events.
    for year, _disp, _title, _detail, lines, _anchor in EVENTS:
        x = x_of(year)
        if len(lines) == len(LANES):
            O.append('<line class="cr-rule" x1="%.1f" y1="%.1f" x2="%.1f" '
                     'y2="%.1f"/>' % (x, top_y, x, bot_y))
            continue
        ys = sorted(lane_y[k] for k in lines)
        if len(ys) > 1:
            O.append('<line class="cr-join" x1="%.1f" y1="%.1f" x2="%.1f" '
                     'y2="%.1f"/>' % (x, ys[0], x, ys[-1]))
        for yy in ys:
            O.append('<circle class="cr-mark" cx="%.1f" cy="%.1f" r="3.4"/>'
                     % (x, yy))

    # Axis, with the labelled anchors staggered over two rows so they do not
    # collide where the record thickens.
    O.append('<line class="cr-axis" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
             % (GUTTER, axis_y, GUTTER + PLOT_W, axis_y))
    row = 0
    for year, disp, _t, _d, _l, anchor in EVENTS:
        if not anchor:
            continue
        x = x_of(year)
        drop = 15 if row % 2 == 0 else 33
        O.append('<line class="cr-tick" x1="%.1f" y1="%.1f" x2="%.1f" '
                 'y2="%.1f"/>' % (x, axis_y, x, axis_y + drop - 10))
        # Clamp the end labels inward, or the first runs back into the lane
        # names and the last runs off the plot.
        half = len(disp) * 3.1
        if x - half < GUTTER:
            anchor, tx = "start", GUTTER
        elif x + half > GUTTER + PLOT_W:
            anchor, tx = "end", GUTTER + PLOT_W
        else:
            anchor, tx = "middle", x
        O.append('<text class="cr-year" x="%.1f" y="%.1f" '
                 'text-anchor="%s">%s</text>' % (tx, axis_y + drop, anchor, disp))
        row += 1

    O.append('</svg>')
    return "\n".join(O)


CHIP = {M: "McFadyen", L: "Maclaine", R: "Ross", A: "Anderson"}


def rows(indent=24):
    pad = " " * indent
    O = [pad + '<div class="timeline">']
    for _year, disp, title, detail, lines, _anchor in EVENTS:
        if len(lines) == len(LANES):
            names = ["all four"]
        else:
            names = [CHIP[k] for k, _ in LANES if k in lines]
        chips = "".join('<span class="tl__clan">%s</span>' % n for n in names)
        O.append(pad + '    <div class="tl">')
        O.append(pad + '        <p class="tl__year">%s</p>' % disp)
        O.append(pad + '        <div class="tl__body">')
        O.append(pad + '            <p class="tl__title">%s%s</p>'
                 % (title, chips))
        O.append(pad + '            <p>%s</p>' % detail)
        O.append(pad + '        </div>')
        O.append(pad + '    </div>')
    O.append(pad + '</div>')
    return "\n".join(O)


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else "--both"
    marks = sum(1 for e in EVENTS if len(e[4]) < len(LANES))
    rules = len(EVENTS) - marks
    sys.stderr.write("events: %d  (%d on named lanes, %d across all four)  "
                     "labelled on the figure: %d\n"
                     % (len(EVENTS), marks, rules,
                        sum(1 for e in EVENTS if e[5])))
    if want in ("--svg", "--both"):
        sys.stdout.write(svg() + "\n")
    if want == "--both":
        sys.stdout.write("\n<!-- rows -->\n")
    if want in ("--rows", "--both"):
        sys.stdout.write(rows() + "\n")


if __name__ == "__main__":
    main()

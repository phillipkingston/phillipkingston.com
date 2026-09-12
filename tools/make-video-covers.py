#!/usr/bin/env python3
"""Fit and downsize the hand-picked cover art for entries on /videos/.

    python3 tools/make-video-covers.py            # img/videos/_src
    python3 tools/make-video-covers.py ~/Downloads

Writes img/videos/<slug>-1280.jpg and img/videos/<slug>-640.jpg for every
entry in COVERS, from the original named in "source" inside the given
directory, which defaults to img/videos/_src, where originals are kept from
now on: it means a poster can be regenerated without hunting for the photograph
again, and the recipe recorded here is what makes that reproducible. The three
oldest entries predate that and their originals were never committed, so an
entry whose source is not in the directory is skipped with a note rather than
stopping the run.

Most videos use YouTube's own frame (tools/fetch-video-posters.py). These use a
photograph or a designed card from the event instead, because the frame YouTube
picked does not show the talk, or because there is no video at all. They go
through the same pipeline as the frames: fitted to the 16:9 slot the page lays
every poster out in, so nothing is left to object-fit to trim, then 1280 wide
for desktop and 640 for a single-column phone at 2x, progressive JPEG at the
posters' quality.

Two ways to reach 16:9, set per entry by "fit":

  "crop"  the default, and the right answer for a photograph. The box is
          chosen by hand because the subject is rarely centred and, on an
          entry that plays, the play button sits dead centre on top of
          whatever is there.

  "pad"   for a designed card, where a crop would cut the artwork. The card
          is centred at full width over a blurred, dimmed enlargement of
          itself, so the slot is filled without a hard letterbox edge and
          without losing a logo or a line of type to the crop.
"""

import os
import sys

from PIL import Image, ImageEnhance, ImageFilter

# slug, source filename, and either a crop box (left, top, right, bottom) in
# source pixels or "fit": "pad".
COVERS = [
    {
        # Palantir DevCon 2024 keynote. 1536x1024: keep headroom over the
        # speaker and lose the audience's heads along the bottom.
        "slug": "palantir-cover",
        "source": "Palantir-Cover.jpeg",
        "box": (0, 60, 1536, 924),
    },
    {
        # MBZUAI, Abu Dhabi. 1600x897, a video still letterboxed in black bars
        # (the picture is x 18-1597, y 39-848); crop inside the bars.
        "slug": "mbzuai-cover",
        "source": "MBZUAI-Cover.jpeg",
        "box": (92, 41, 1523, 846),
    },
    {
        # Decoding Data Science, Dubai. 3000x2000, and a PNG despite its name.
        "slug": "decoding-data-science-cover",
        "source": "DecodingDataScience-Cover.jpg",
        "box": (0, 190, 3000, 1878),
    },
    {
        # The Kyiv lecture card. 1145x576, a banner wider than 16:9, with the
        # university's mark hard against the left edge and Kingston's name and
        # title against the right. There is no 121px of width anywhere in it
        # that can be lost, so it is padded rather than cropped.
        "slug": "kyiv-aviation-cover",
        "source": "NationalAviationUniversity-Kingston-Cover.jpg",
        "fit": "pad",
    },
    {
        # The "Powering AI startups" panel at Step Conference 2024. 1280x720
        # and already the shape of the slot: the box is the whole photograph.
        "slug": "step-2024-cover",
        "source": "Step-Cover-Kingston-2024.jpeg",
        "box": (0, 0, 1280, 720),
    },
    {
        # The /function1 speaker card. 1600x900, also already 16:9. The second
        # cut of the card, without the "CTO" line under the name.
        "slug": "function1-2025-cover",
        "source": "function1-kingston-cover-2025.png",
        "box": (0, 0, 1600, 900),
    },
]

SRC_DIR = os.path.join("img", "videos", "_src")
OUT_DIR = os.path.join("img", "videos")
WIDTHS = (1280, 640)
QUALITY = 82
EXPECTED_RATIO = 16 / 9

# Enough blur that the band behind the card reads as tone rather than a second,
# smaller picture of the same thing, and enough dimming that the card's own
# edge stays visible against it.
PAD_BLUR = 18
PAD_DIM = 0.88


def pad_to_ratio(img, slug):
    """Centre a card too wide for 16:9 on a blurred enlargement of itself."""
    if img.width / img.height < EXPECTED_RATIO:
        raise SystemExit("%s: %dx%d is taller than 16:9, so padding it sideways "
                         "would box the card in; crop it instead"
                         % (slug, img.width, img.height))
    height = round(img.width / EXPECTED_RATIO)
    scale = height / img.height
    back = img.resize((round(img.width * scale), height), Image.LANCZOS)
    left = (back.width - img.width) // 2
    back = back.crop((left, 0, left + img.width, height))
    back = back.filter(ImageFilter.GaussianBlur(PAD_BLUR))
    back = ImageEnhance.Brightness(back).enhance(PAD_DIM)
    back.paste(img, (0, (height - img.height) // 2))
    return back


def main():
    src_dir = os.path.expanduser(sys.argv[1]) if len(sys.argv) == 2 else SRC_DIR
    if len(sys.argv) > 2:
        raise SystemExit("usage: python3 tools/make-video-covers.py [directory of originals]")
    os.makedirs(OUT_DIR, exist_ok=True)
    for entry in COVERS:
        source = os.path.join(src_dir, entry["source"])
        if not os.path.exists(source):
            print("%s: no %s in %s, skipped" % (entry["slug"], entry["source"], src_dir),
                  file=sys.stderr)
            continue
        img = Image.open(source).convert("RGB")
        if entry.get("fit") == "pad":
            img = pad_to_ratio(img, entry["slug"])
        else:
            left, top, right, bottom = entry["box"]
            if right > img.width or bottom > img.height:
                raise SystemExit("%s: crop box runs outside the %dx%d photo"
                                 % (entry["slug"], img.width, img.height))
            if abs((right - left) / (bottom - top) - EXPECTED_RATIO) > 0.01:
                raise SystemExit("%s: crop box is not 16:9" % entry["slug"])
            img = img.crop(entry["box"])
        for width in WIDTHS:
            height = round(width * 9 / 16)
            out = os.path.join(OUT_DIR, "%s-%d.jpg" % (entry["slug"], width))
            img.resize((width, height), Image.LANCZOS).save(
                out, "JPEG", quality=QUALITY, optimize=True, progressive=True)
            print("%s  %dx%d  %.0f KB" % (out, width, height, os.path.getsize(out) / 1024),
                  file=sys.stderr)


if __name__ == "__main__":
    main()

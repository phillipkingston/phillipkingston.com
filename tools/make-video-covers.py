#!/usr/bin/env python3
"""Crop and downsize the hand-picked cover photos for videos on /videos/.

    python3 tools/make-video-covers.py ~/Downloads

Writes img/videos/<slug>-1280.jpg and img/videos/<slug>-640.jpg for every
entry in COVERS, from the original photo named in "source" inside the given
directory. The originals are not committed; the crop box recorded here is what
makes the output reproducible from them.

Most videos use YouTube's own frame (tools/fetch-video-posters.py). These use a
photograph from the event instead, because the frame YouTube picked does not
show the talk. They go through the same pipeline as the frames: cropped to the
16:9 slot the page lays every poster out in, so nothing is left to object-fit
to trim, then 1280 wide for desktop and 640 for a single-column phone at 2x,
progressive JPEG at the posters' quality. The crop is chosen by hand for each
photo because the subject is rarely centred and the play button sits dead
centre on top of whatever is there.
"""

import os
import sys

from PIL import Image

# slug, source filename, crop box (left, top, right, bottom) in source pixels.
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
]

OUT_DIR = os.path.join("img", "videos")
WIDTHS = (1280, 640)
QUALITY = 82
EXPECTED_RATIO = 16 / 9


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 tools/make-video-covers.py <directory of originals>")
    src_dir = os.path.expanduser(sys.argv[1])
    os.makedirs(OUT_DIR, exist_ok=True)
    for entry in COVERS:
        img = Image.open(os.path.join(src_dir, entry["source"])).convert("RGB")
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

#!/usr/bin/env python3
"""Fetch and downsize the poster frames for the videos on /videos/.

    python3 tools/fetch-video-posters.py

Writes img/videos/<id>-1280.jpg and img/videos/<id>-640.jpg for every video
listed in VIDEOS, from YouTube's own maxresdefault frame for that video.

The posters are committed rather than hotlinked from i.ytimg.com on purpose.
/videos/ loads nothing from Google until the reader presses play, and a poster
served from ytimg would break that: it would hand YouTube a request, and an IP
address, from every reader who merely scrolled past. Serving the frame from
this domain is what keeps that true.

Two widths so the page can offer a srcset: 1280 is the frame as YouTube stores
it, 640 covers a single-column phone at 2x. Both are progressive JPEG, which
is what a photograph at this size wants; the site's own artwork is SVG.
"""

import io
import os
import sys
import urllib.request

from PIL import Image

# Video ids in the order they appear on the page. The id is the filename stem,
# so a video dropped from the page leaves an obvious orphan in img/videos/.
# The Palantir, MBZUAI and Decoding Data Science videos are not here: they use
# a photograph from the event, made by tools/make-video-covers.py.
VIDEOS = [
    "b80GKpEcr0M",  # AWS for AI ep 1 — a podcast that is also a video
    "P8IVkxhXCw8",  # The Derby Mill Series ep 15 — a podcast that is also a video
    "PrUwBkPCvXA",  # February 2024 hackathon winners
]

SOURCE = "https://i.ytimg.com/vi/{id}/maxresdefault.jpg"
OUT_DIR = os.path.join("img", "videos")
WIDTHS = (1280, 640)
QUALITY = 82

# maxresdefault is the only frame YouTube stores at the video's own 16:9 size.
# hqdefault and sddefault are letterboxed into 4:3, so a 16:9 slot would have
# to crop them and the crop would eat the frame. A video without a maxres
# frame is a hard error rather than a silent fallback to a letterboxed one.
EXPECTED_RATIO = 16 / 9


def fetch(video_id):
    url = SOURCE.format(id=video_id)
    req = urllib.request.Request(url, headers={"User-Agent": "phillipkingston.com poster fetch"})
    with urllib.request.urlopen(req, timeout=60) as r:
        if r.status != 200:
            raise SystemExit("%s: HTTP %s" % (video_id, r.status))
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for video_id in VIDEOS:
        img = fetch(video_id)
        ratio = img.width / img.height
        if abs(ratio - EXPECTED_RATIO) > 0.02:
            raise SystemExit(
                "%s: poster is %dx%d, not 16:9 — YouTube has no maxres frame for it"
                % (video_id, img.width, img.height)
            )
        for width in WIDTHS:
            height = round(width * img.height / img.width)
            out = os.path.join(OUT_DIR, "%s-%d.jpg" % (video_id, width))
            resized = img if img.width == width else img.resize((width, height), Image.LANCZOS)
            resized.save(out, "JPEG", quality=QUALITY, optimize=True, progressive=True)
            print("%s  %dx%d  %.0f KB" % (out, width, height, os.path.getsize(out) / 1024),
                  file=sys.stderr)


if __name__ == "__main__":
    main()

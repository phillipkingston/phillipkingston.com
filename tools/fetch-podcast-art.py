#!/usr/bin/env python3
"""Fetch and downsize the cover art for the podcasts on /videos/.

    python3 tools/fetch-podcast-art.py

Writes img/videos/<slug>-560.jpg and img/videos/<slug>-280.jpg for every show
listed in SHOWS, from the artwork the show publishes to Apple Podcasts.

An audio episode has no frame of its own, so the show's cover art is what a
reader recognises it by, the same way a listing in any podcast app does. The
art belongs to the show, not to this site: it is used here only to identify an
episode Kingston appears on, each entry records where it came from, and the
page links back to the show on every platform that carries it.

Committing the file rather than hotlinking Apple's CDN is the same call the
video posters make — opening the page should not send a request to a platform
the reader has not chosen to visit.
"""

import io
import os
import sys
import urllib.request

from PIL import Image

# slug, show, source. The source is Apple's artwork URL at 1200x1200, which is
# the largest square Apple serves; the path is stable per show, and re-running
# this script is how the art gets refreshed if a show ever changes it.
SHOWS = [
    {
        "slug": "aws-for-ai",
        "show": "AWS for AI Podcast",
        "source": (
            "https://is1-ssl.mzstatic.com/image/thumb/Podcasts211/v4/18/47/e4/"
            "1847e4ee-a9a0-c83f-c73d-a337383a90c8/mza_6562904297147485806.jpeg/"
            "1200x1200bf-60.jpg"
        ),
    },
]

OUT_DIR = os.path.join("img", "videos")
WIDTHS = (560, 280)
QUALITY = 84


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "phillipkingston.com art fetch"})
    with urllib.request.urlopen(req, timeout=60) as r:
        if r.status != 200:
            raise SystemExit("%s: HTTP %s" % (url, r.status))
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for entry in SHOWS:
        img = fetch(entry["source"])
        if abs(img.width - img.height) > 2:
            raise SystemExit(
                "%s: art is %dx%d, not square — the page lays it out as a square tile"
                % (entry["slug"], img.width, img.height)
            )
        for width in WIDTHS:
            out = os.path.join(OUT_DIR, "%s-%d.jpg" % (entry["slug"], width))
            resized = img if img.width == width else img.resize((width, width), Image.LANCZOS)
            resized.save(out, "JPEG", quality=QUALITY, optimize=True, progressive=True)
            print("%s  %dx%d  %.0f KB" % (out, width, width, os.path.getsize(out) / 1024),
                  file=sys.stderr)


if __name__ == "__main__":
    main()

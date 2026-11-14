#!/usr/bin/env python3
"""Fast parallel theme image fetcher with aspect-balanced selection and Commons fallback."""

import json
import math
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from build_timeline import BEAT_SLOTS

UA = "BeatReelStudio/1.0 (personal-video-render; contact@local.dev)"
BAD_KEYWORDS = (".svg", "flag", "map_", "_map", "logo", "icon", "signature", "monogram", "diagram")


def api_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_wiki_pageimages(titles: list[str], thumb_px: int = 960) -> dict[str, dict]:
    """Query Wikipedia pageimages in batches of 40 titles."""
    batches = [titles[i : i + 40] for i in range(0, len(titles), 40)]

    def query_batch(batch: list[str]) -> dict[str, dict]:
        qs = urllib.parse.urlencode({
            "action": "query",
            "titles": "|".join(batch),
            "prop": "pageimages",
            "pithumbsize": str(thumb_px),
            "redirects": "1",
            "format": "json",
        })
        data = api_get(f"https://en.wikipedia.org/w/api.php?{qs}")
        q = data.get("query", {})
        rmap = {r["to"]: r["from"] for r in q.get("redirects", [])}
        nmap = {n["to"]: n["from"] for n in q.get("normalized", [])}
        out: dict[str, dict] = {}
        for page in q.get("pages", {}).values():
            title = page.get("title", "")
            orig = nmap.get(rmap.get(title, title), rmap.get(title, title))
            thumb = page.get("thumbnail")
            if not thumb:
                continue
            src = thumb.get("source", "")
            w = int(thumb.get("width", 0))
            h = int(thumb.get("height", 0))
            low = src.lower()
            if any(k in low for k in BAD_KEYWORDS) or w < 380 or h < 320:
                continue
            out[orig] = {"url": src, "w": w, "h": h, "resolved": title}
        return out

    merged: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for res in ex.map(query_batch, batches):
            merged.update(res)
    return merged


def fetch_commons_fallback(query: str, thumb_px: int = 960) -> dict | None:
    """Fallback search directly against Wikimedia Commons namespace 6."""
    qs = urllib.parse.urlencode({
        "action": "query",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrlimit": "6",
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "iiurlwidth": str(thumb_px),
        "format": "json",
    })
    try:
        data = api_get(f"https://commons.wikimedia.org/w/api.php?{qs}")
    except Exception:
        return None
    for page in data.get("query", {}).get("pages", {}).values():
        ii = (page.get("imageinfo") or [{}])[0]
        mime = ii.get("mime", "")
        url = ii.get("thumburl") or ii.get("url", "")
        w = int(ii.get("thumbwidth") or ii.get("width") or 0)
        h = int(ii.get("thumbheight") or ii.get("height") or 0)
        low = url.lower()
        if mime in ("image/jpeg", "image/png") and not any(k in low for k in BAD_KEYWORDS) and w >= 420 and h >= 320:
            return {"url": url, "w": w, "h": h, "resolved": page.get("title", query)}
    return None


def select_best_aspect_subset(pool: list[tuple[str, dict]], grid: list[list[int]]) -> list[tuple[str, dict]]:
    """Select n candidates from pool that best match the grid's aspect-ratio spectrum."""
    needed = len(grid)
    if len(pool) <= needed:
        return list(pool)

    def ar_cost(info: dict, slot: list[int]) -> float:
        im_ar = info["w"] / max(1, info["h"])
        sl_ar = slot[2] / max(1, slot[3])
        return abs(math.log(im_ar / sl_ar))

    rem = list(pool)
    selected: list[tuple[str, dict]] = []
    # Prioritize matching extreme slots (tall portraits & wide strips) first
    sorted_slots = sorted(grid, key=lambda s: abs(math.log(s[2] / max(1, s[3]))), reverse=True)
    for sl in sorted_slots:
        best_i = min(range(len(rem)), key=lambda i: ar_cost(rem[i][1], sl))
        selected.append(rem.pop(best_i))
    return selected


def download_image(job: tuple[str, int, str, dict, Path]) -> dict | None:
    era_id, idx, title, info, img_dir = job
    ext = ".png" if ".png" in info["url"].lower() else ".jpg"
    fname = f"{era_id}_{idx:02d}{ext}"
    fpath = img_dir / fname
    for attempt in range(3):
        try:
            req = urllib.request.Request(info["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
            if len(data) < 12000:
                raise ValueError(f"Too small: {len(data)}")
            if not (data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Invalid JPEG/PNG signature")
            fpath.write_bytes(data)
            return {
                "era": era_id,
                "idx": idx,
                "title": title,
                "file": fname,
                "w": info["w"],
                "h": info["h"],
                "bytes": len(data),
            }
        except Exception as exc:
            if attempt == 2:
                print(f"  [WARN] Failed {era_id} '{title}': {exc}", file=sys.stderr)
                return None
            time.sleep(0.4 * (attempt + 1))
    return None


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: fetch_theme.py <theme_dir>", file=sys.stderr)
        return 1

    t0 = time.perf_counter()
    theme_dir = Path(sys.argv[1]).resolve()
    theme = json.loads((theme_dir / "theme.json").read_text(encoding="utf-8"))
    img_dir = theme_dir / "assets" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    for old in img_dir.iterdir():
        if old.is_file():
            old.unlink()

    all_titles: list[str] = []
    for ch in theme["chapters"]:
        all_titles.extend(ch["queries"])

    t_api0 = time.perf_counter()
    img_map = fetch_wiki_pageimages(all_titles)
    t_api = time.perf_counter() - t_api0
    print(f"[fetch] Wikipedia batch resolved {len(img_map)}/{len(all_titles)} titles in {t_api:.2f}s")

    jobs: list[tuple[str, int, str, dict, Path]] = []
    backup_by_era: dict[str, list[tuple[str, dict]]] = {}

    for ch, beat in zip(theme["chapters"], BEAT_SLOTS):
        era_id = ch["id"]
        needed = len(beat["grid"])
        pool: list[tuple[str, dict]] = []
        missing: list[str] = []
        for q in ch["queries"]:
            if q in img_map:
                pool.append((q, img_map[q]))
            else:
                missing.append(q)

        # Commons fallback only if needed
        if len(pool) < needed and missing:
            with ThreadPoolExecutor(max_workers=4) as ex:
                fbs = list(ex.map(fetch_commons_fallback, missing))
            for q, fb in zip(missing, fbs):
                if fb:
                    pool.append((q, fb))

        chosen = select_best_aspect_subset(pool, beat["grid"])
        chosen_titles = {c[0] for c in chosen}
        backup_by_era[era_id] = [c for c in pool if c[0] not in chosen_titles]

        for idx, (q, info) in enumerate(chosen, start=1):
            jobs.append((era_id, idx, q, info, img_dir))
        print(f"  {era_id:22s}: {len(chosen)}/{needed} matched (pool={len(pool)})")

    t_dl0 = time.perf_counter()
    manifest: dict[str, list[dict]] = {}
    failed_slots: list[tuple[str, int]] = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(download_image, j): j for j in jobs}
        for fut in as_completed(futs):
            era_id, idx, _, _, _ = futs[fut]
            res = fut.result()
            if res:
                manifest.setdefault(era_id, []).append(res)
            else:
                failed_slots.append((era_id, idx))

    # Retry failed slots with spare candidates from backup_by_era
    for era_id, idx in failed_slots:
        pool = backup_by_era.get(era_id, [])
        while pool:
            q, info = pool.pop(0)
            res = download_image((era_id, idx, q, info, img_dir))
            if res:
                manifest.setdefault(era_id, []).append(res)
                break

    t_dl = time.perf_counter() - t_dl0

    # Verify exact pixel dimensions locally via sips
    all_files = sorted(str(p) for p in img_dir.iterdir() if p.is_file())
    sips_out = subprocess.check_output(["sips", "-g", "pixelWidth", "-g", "pixelHeight"] + all_files, text=True)
    dims: dict[str, tuple[int, int]] = {}
    cur = None
    w_val = 0
    for line in sips_out.splitlines():
        s = line.strip()
        if s.startswith("/"):
            cur = Path(s).name
        elif s.startswith("pixelWidth:"):
            w_val = int(s.split(":")[1].strip())
        elif s.startswith("pixelHeight:") and cur:
            dims[cur] = (w_val, int(s.split(":")[1].strip()))

    for era_id in manifest:
        manifest[era_id].sort(key=lambda x: x["idx"])
        for entry in manifest[era_id]:
            if entry["file"] in dims:
                entry["w"], entry["h"] = dims[entry["file"]]

    manifest_path = theme_dir / "assets" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    total_imgs = sum(len(v) for v in manifest.values())
    elapsed = time.perf_counter() - t0
    print(f"[fetch] Downloaded & verified {total_imgs} images in {t_dl:.2f}s (total fetch phase: {elapsed:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Multi-motif Pinterest candidate fetcher for beat-reel themes.

Reads per-chapter `queries` from `<theme_dir>/theme.json` and downloads each
sub-motif query into `<theme_dir>/.candidates/<chapter_id>/q<idx:02d>_<slug>/`
so visual curation preserves both palette cohesion and broad visual diversity.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def find_pinterest_dl() -> list[str]:
    """Locate a working pinterest-dl CLI invocation."""
    direct = shutil.which("pinterest-dl")
    if direct:
        return [direct]
    repo_root = Path(__file__).resolve().parent.parent
    for cand in (
        repo_root / ".venv" / "bin" / "pinterest-dl",
        Path("/tmp/pdl_venv/bin/pinterest-dl"),
    ):
        if cand.exists():
            return [str(cand)]
    raise FileNotFoundError(
        "pinterest-dl CLI not found. Install it via `pip install -r requirements.txt` "
        "(or create a virtualenv containing pinterest-dl)."
    )


def slugify_query(text: str, max_len: int = 24) -> str:
    """Turn a search phrase into a compact ASCII directory slug."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    joined = "_".join(words[:3]) if words else "motif"
    return joined[:max_len].strip("_") or "motif"


def parse_query_entry(entry: str | list[str] | dict[str, str]) -> tuple[str, str]:
    """Normalize a query entry into `(slug, search_query)`."""
    if isinstance(entry, str):
        return slugify_query(entry), entry
    if isinstance(entry, list) and len(entry) >= 2:
        return slugify_query(entry[0]), entry[1]
    if isinstance(entry, dict) and "query" in entry:
        return slugify_query(entry.get("slug") or entry["query"]), entry["query"]
    raise ValueError(f"Unsupported query entry format: {entry!r}")


def fetch_one(
    pdl_cmd: list[str],
    out_root: Path,
    era_id: str,
    idx: int,
    slug: str,
    query: str,
    per_query: int,
    min_res: str,
    client: str,
    timeout: int,
) -> tuple[str, int, str, int, str]:
    """Fetch images for one chapter sub-motif query."""
    out_dir = out_root / era_id / f"q{idx:02d}_{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = [p for p in out_dir.iterdir() if p.suffix.lower() in IMG_EXTS and p.stat().st_size > 12000]
    if len(existing) >= max(1, per_query - 2):
        return era_id, idx, slug, len(existing), "cached"

    cmd = [
        *pdl_cmd,
        "search",
        query,
        "-o",
        str(out_dir),
        "-n",
        str(per_query),
        "-r",
        min_res,
        "--caption",
        "json",
        "--client",
        client,
        "--timeout",
        str(timeout),
        "--delay",
        "0.15",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=max(30, timeout * 4))
    files = [p for p in out_dir.iterdir() if p.suffix.lower() in IMG_EXTS and p.stat().st_size > 12000]
    err = ""
    if not files:
        lines = (res.stderr or res.stdout or "").strip().splitlines()
        err = lines[-1][:120] if lines else "no images"
    return era_id, idx, slug, len(files), err


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch multi-motif Pinterest candidates for a beat-reel theme.")
    parser.add_argument("theme_dir", help="Path to theme directory containing theme.json")
    parser.add_argument("--out", help="Candidate output directory (default: <theme_dir>/.candidates)")
    parser.add_argument("--per-query", type=int, default=6, help="Pins to request per sub-motif query (default: 6)")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent query workers (default: 4)")
    parser.add_argument("--min-res", default="500x500", help="Minimum resolution WxH filter (default: 500x500)")
    parser.add_argument("--client", default="api", choices=["api", "chromium", "firefox"], help="pinterest-dl client")
    parser.add_argument("--timeout", type=int, default=15, help="Per-request timeout in seconds (default: 15)")
    args = parser.parse_args()

    theme_dir = Path(args.theme_dir).resolve()
    theme = json.loads((theme_dir / "theme.json").read_text(encoding="utf-8"))
    out_root = Path(args.out).resolve() if args.out else (theme_dir / ".candidates")
    out_root.mkdir(parents=True, exist_ok=True)

    pdl_cmd = find_pinterest_dl()

    tasks: list[tuple[str, int, str, str]] = []
    by_era: dict[str, int] = {}
    for ch in theme["chapters"]:
        era_id = ch["id"]
        by_era[era_id] = 0
        raw_queries = ch.get("queries", [])
        if not raw_queries:
            print(f"[WARN] Chapter {era_id} has empty queries list; skipping.", file=sys.stderr)
            continue
        for i, raw_q in enumerate(raw_queries, start=1):
            slug, query = parse_query_entry(raw_q)
            tasks.append((era_id, i, slug, query))

    if not tasks:
        print("No queries found in theme.json.", file=sys.stderr)
        return 1

    # Probe the first task synchronously so network/sandbox failures abort immediately.
    first_era, first_i, first_slug, first_cnt, first_err = fetch_one(
        pdl_cmd, out_root, *tasks[0], args.per_query, args.min_res, args.client, args.timeout
    )
    print(f"[probe] {first_era}/q{first_i:02d}_{first_slug}: {first_cnt} imgs ({first_err})", flush=True)
    if first_cnt == 0:
        print("Connectivity probe returned 0 images; aborting.", file=sys.stderr)
        return 1

    by_era[first_era] += first_cnt
    total = first_cnt

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = [
            pool.submit(
                fetch_one,
                pdl_cmd,
                out_root,
                *t,
                args.per_query,
                args.min_res,
                args.client,
                args.timeout,
            )
            for t in tasks[1:]
        ]
        for fut in as_completed(futs):
            era_id, idx, slug, cnt, err = fut.result()
            by_era[era_id] += cnt
            total += cnt
            status = err if cnt == 0 else "ok"
            print(f"[{era_id}] q{idx:02d}_{slug}: {cnt} ({status})", flush=True)

    print("\nSummary by chapter:")
    for era_id, cnt in by_era.items():
        print(f"  {era_id:22s}: {cnt} images")
    print(f"Total fetched: {total} -> {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

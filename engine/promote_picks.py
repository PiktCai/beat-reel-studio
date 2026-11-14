#!/usr/bin/env python3
"""Promote curated candidate pickIds from `<candidates>/picks.json` into `<theme_dir>/assets/`.

Validates slot counts against `BEAT_SLOTS`, converts non-JPEG sources to clean
RGB JPEGs via `sips`, measures exact pixel dimensions, and emits `manifest.json`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from build_timeline import BEAT_SLOTS


def sips_dimensions(path: Path) -> tuple[int, int]:
    """Read pixel width and height using macOS sips."""
    out = subprocess.check_output(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
        text=True,
    )
    w = h = 0
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("pixelWidth:"):
            w = int(s.split(":", 1)[1].strip())
        elif s.startswith("pixelHeight:"):
            h = int(s.split(":", 1)[1].strip())
    return w, h


def convert_to_jpeg(src: Path, dst: Path) -> None:
    """Copy JPEG assets or convert PNG/WebP candidates to high-quality JPEG."""
    if src.suffix.lower() in {".jpg", ".jpeg"}:
        shutil.copy2(src, dst)
        return
    subprocess.run(
        ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92", str(src), "--out", str(dst)],
        check=True,
        capture_output=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote curated candidate picks into theme assets.")
    parser.add_argument("theme_dir", help="Path to theme directory containing theme.json")
    parser.add_argument(
        "picks_json",
        nargs="?",
        help="Path to picks JSON mapping chapter_id -> [pickId, ...] (default: <candidates>/picks.json)",
    )
    parser.add_argument(
        "--candidates",
        help="Candidates root directory holding index_<chapter>.json (default: <theme_dir>/.candidates)",
    )
    args = parser.parse_args()

    theme_dir = Path(args.theme_dir).resolve()
    theme = json.loads((theme_dir / "theme.json").read_text(encoding="utf-8"))
    layout_key = "orbit" if theme.get("layoutMode", "swiss") == "orbital" else "swiss"

    cand_root = Path(args.candidates).resolve() if args.candidates else (theme_dir / ".candidates")
    picks_path = Path(args.picks_json).resolve() if args.picks_json else (cand_root / "picks.json")
    picks = json.loads(picks_path.read_text(encoding="utf-8"))

    assets_dir = theme_dir / "assets"
    images_dir = assets_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    for old in images_dir.iterdir():
        if old.is_file():
            old.unlink()

    manifest: dict[str, list[dict]] = {}
    chapters = theme["chapters"]
    if len(chapters) != len(BEAT_SLOTS):
        raise ValueError(f"Expected {len(BEAT_SLOTS)} chapters in theme.json, got {len(chapters)}")

    for ch, beat in zip(chapters, BEAT_SLOTS):
        era_id = ch["id"]
        need = len(beat[layout_key])
        chosen_ids = picks.get(era_id, [])
        if len(chosen_ids) != need:
            raise ValueError(f"{era_id}: expected {need} picks, got {len(chosen_ids)}")
        if len(set(chosen_ids)) != len(chosen_ids):
            raise ValueError(f"{era_id}: duplicate pickId in selection: {chosen_ids}")

        idx_data = json.loads((cand_root / f"index_{era_id}.json").read_text(encoding="utf-8"))
        by_id = {item["pickId"]: item for item in idx_data}

        entries = []
        wide_cnt = 0
        for idx, pid in enumerate(chosen_ids, start=1):
            item = by_id[pid]
            src = Path(item["srcPath"])
            out_name = f"{era_id}_{idx:02d}.jpg"
            dst = images_dir / out_name
            convert_to_jpeg(src, dst)
            w, h = sips_dimensions(dst)
            if w / max(1, h) >= 0.95:
                wide_cnt += 1
            title = (item.get("alt") or item.get("motif") or era_id).strip()
            entries.append({
                "era": era_id,
                "idx": idx,
                "srcPin": item.get("stem", ""),
                "motif": item.get("motif", ""),
                "title": title,
                "file": out_name,
                "w": w,
                "h": h,
                "bytes": dst.stat().st_size,
            })
        manifest[era_id] = entries
        print(f"Promoted {era_id:20s}: {len(entries)} images (wide/sq={wide_cnt}, portrait={len(entries) - wide_cnt})")

    manifest_path = assets_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

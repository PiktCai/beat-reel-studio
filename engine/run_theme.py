#!/usr/bin/env python3
"""One-command theme video builder with per-stage wall-clock timing."""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


def run_step(label: str, cmd: list[str]) -> float:
    t0 = time.perf_counter()
    print(f"\n==> [{label}] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    dt = time.perf_counter() - t0
    print(f"<== [{label}] finished in {dt:.2f}s")
    return dt


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("Usage: run_theme.py <theme_dir> [--with-fetch] [--keep-frames]", file=sys.stderr)
        return 1

    theme_dir = Path(args[0]).resolve()
    with_fetch = "--with-fetch" in args
    keep_frames = "--keep-frames" in args

    engine_dir = Path(__file__).resolve().parent
    studio_dir = engine_dir.parent
    bin_path = studio_dir / "bin" / "render_bin"
    swift_src = engine_dir / "render.swift"
    audio_path = studio_dir / "audio" / "audio.wav"

    timings: dict[str, float] = {}
    t_total0 = time.perf_counter()

    if with_fetch:
        timings["fetch_images"] = run_step(
            "fetch_images",
            [sys.executable, str(engine_dir / "fetch_theme.py"), str(theme_dir)],
        )

    # Auto-compile render.swift only if binary missing or source edited
    if not bin_path.exists() or swift_src.stat().st_mtime > bin_path.stat().st_mtime:
        bin_path.parent.mkdir(parents=True, exist_ok=True)
        Path("/tmp/swift_cache").mkdir(parents=True, exist_ok=True)
        timings["compile_swift"] = run_step(
            "compile_swift",
            ["swiftc", "-O", "-module-cache-path", "/tmp/swift_cache", str(swift_src), "-o", str(bin_path)],
        )

    timings["build_timeline"] = run_step(
        "build_timeline",
        [sys.executable, str(engine_dir / "build_timeline.py"), str(theme_dir)],
    )

    timeline = json.loads((theme_dir / "timeline.json").read_text(encoding="utf-8"))
    out_dir = theme_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / timeline.get("outputFile", f"{theme_dir.name}.mp4")

    timings["render_frames"] = run_step(
        "render_frames",
        [str(bin_path), str(theme_dir)],
    )

    timings["ffmpeg_encode"] = run_step(
        "ffmpeg_encode",
        [
            "ffmpeg", "-y", "-framerate", str(timeline["fps"]),
            "-i", str(theme_dir / ".render_frames" / "frame_%04d.png"),
            "-i", str(audio_path),
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-crf", "15", "-preset", "slow",
            "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k", "-shortest",
            str(out_file),
        ],
    )

    timings["verify_sync"] = run_step(
        "verify_sync",
        [sys.executable, str(engine_dir / "verify_sync.py"), str(theme_dir), str(out_file)],
    )

    if not keep_frames:
        frames_dir = theme_dir / ".render_frames"
        if frames_dir.exists():
            shutil.rmtree(frames_dir)

    total_dt = time.perf_counter() - t_total0
    print("\n================ PIPELINE TIMING SUMMARY ================")
    for k, v in timings.items():
        print(f"  {k:18s}: {v:6.2f}s")
    print(f"  {'TOTAL':18s}: {total_dt:6.2f}s")
    print(f"  Output MP4       : {out_file}")
    print("=========================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

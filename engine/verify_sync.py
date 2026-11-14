#!/usr/bin/env python3
"""Verify container metadata and frame-exact visual-audio sync of any encoded theme MP4."""

import json
import subprocess
import sys
from pathlib import Path


def load_expected_change_frames(timeline: dict) -> list[int]:
    """Compute sorted unique frame indices (> 0) where visual state changes."""
    events: set[int] = set()
    intro = timeline["intro"]
    for key in ("title1", "title2", "episode", "category"):
        f = int(intro[key]["frame"])
        if 0 < f < intro["endFrame"]:
            events.add(f)
    for thumb in intro["thumbs"]:
        f = int(thumb["frame"])
        if 0 < f < intro["endFrame"]:
            events.add(f)
    vol_hide = int(intro["volHideFrame"])
    if 0 < vol_hide < intro["endFrame"]:
        events.add(vol_hide)

    for scene in timeline["scenes"]:
        start = int(scene["startFrame"])
        if start > 0:
            events.add(start)
        for item in scene["items"]:
            f = start + int(item["offsetFrame"])
            if 0 < f < timeline["totalFrames"]:
                events.add(f)
    return sorted(events)


def check_streams(video_path: Path, timeline: dict) -> None:
    """Validate FFprobe stream properties against expected 3:4 30fps specs."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(video_path),
    ]
    raw = subprocess.check_output(cmd, text=True)
    probe = json.loads(raw)

    streams = {s["codec_type"]: s for s in probe["streams"]}
    if "video" not in streams or "audio" not in streams:
        raise AssertionError(f"Expected video+audio streams, got {list(streams.keys())}")

    v = streams["video"]
    a = streams["audio"]
    expected_w = int(round(timeline["designWidth"] * timeline["outputScale"]))
    expected_h = int(round(timeline["designHeight"] * timeline["outputScale"]))
    expected_frames = int(timeline["totalFrames"])
    expected_dur = expected_frames / float(timeline["fps"])

    assert v["codec_name"] == "h264", f"Unexpected video codec: {v['codec_name']}"
    assert int(v["width"]) == expected_w, f"Width {v['width']} != {expected_w}"
    assert int(v["height"]) == expected_h, f"Height {v['height']} != {expected_h}"
    assert v["r_frame_rate"] == f"{timeline['fps']}/1", f"FPS {v['r_frame_rate']}"
    assert int(v["nb_frames"]) == expected_frames, f"Frames {v['nb_frames']} != {expected_frames}"

    assert a["codec_name"] == "aac", f"Unexpected audio codec: {a['codec_name']}"
    assert int(a["sample_rate"]) == 44100, f"Sample rate {a['sample_rate']}"
    assert int(a["channels"]) == 2, f"Channels {a['channels']} != 2"

    v_dur = float(v["duration"])
    a_dur = float(a["duration"])
    assert abs(v_dur - expected_dur) < 0.02, f"Video duration {v_dur:.4f}s != {expected_dur:.4f}s"
    assert abs(a_dur - expected_dur) < 0.06, f"Audio duration {a_dur:.4f}s != {expected_dur:.4f}s"

    print(
        f"[OK] Streams: H.264 {v['width']}x{v['height']} @ {v['r_frame_rate']}, "
        f"{v['nb_frames']} frames ({v_dur:.3f}s); "
        f"AAC {a['sample_rate']}Hz {a['channels']}ch ({a_dur:.3f}s)"
    )


def detect_visual_change_frames(video_path: Path, expected_frames: int) -> tuple[list[int], dict[int, float]]:
    """Decode scaled RGB frames from encoded MP4 and find consecutive frame diffs."""
    w, h = 270, 360
    frame_bytes = w * h * 3
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-vf",
        f"scale={w}:{h}:flags=area",
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    assert proc.stdout is not None

    prev_frame: bytes | None = None
    changed_ratio_by_frame: dict[int, float] = {}
    detected: list[int] = []
    idx = 0

    while True:
        buf = proc.stdout.read(frame_bytes)
        if not buf:
            break
        if len(buf) != frame_bytes:
            raise AssertionError(f"Short read at frame {idx}: {len(buf)} bytes")
        if prev_frame is not None:
            diff_bytes = sum(1 for a_b, b_b in zip(prev_frame, buf) if abs(a_b - b_b) > 8)
            ratio = diff_bytes / frame_bytes
            changed_ratio_by_frame[idx] = ratio
            if ratio > 0.0005:
                detected.append(idx)
        prev_frame = buf
        idx += 1

    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg decode exited with {rc}")
    assert idx == expected_frames, f"Decoded {idx} frames != expected {expected_frames}"
    return detected, changed_ratio_by_frame


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: verify_sync.py <theme_dir> [video_path]", file=sys.stderr)
        return 1

    theme_dir = Path(sys.argv[1]).resolve()
    timeline_path = theme_dir / "timeline.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))

    if len(sys.argv) >= 3:
        video_path = Path(sys.argv[2]).resolve()
    else:
        out_name = timeline.get("outputFile") or f"{theme_dir.name}.mp4"
        video_path = theme_dir / "output" / out_name

    if not video_path.exists():
        print(f"[ERR] Missing encoded video: {video_path}", file=sys.stderr)
        return 1

    check_streams(video_path, timeline)

    expected = load_expected_change_frames(timeline)
    detected, ratios = detect_visual_change_frames(video_path, int(timeline["totalFrames"]))

    expected_set = set(expected)
    detected_set = set(detected)
    missing = sorted(expected_set - detected_set)
    unexpected = sorted(detected_set - expected_set)

    static_ratios = [r for f, r in ratios.items() if f not in expected_set]
    max_static = max(static_ratios) if static_ratios else 0.0
    min_event = min((ratios[f] for f in expected if f in ratios), default=0.0)

    print(f"[INFO] Expected transition frames: {len(expected)}, Detected in MP4: {len(detected)}")
    print(
        f"[INFO] Min pixel-channel change on beat events: {min_event * 100:.3f}%, "
        f"Max change on static hold frames: {max_static * 100:.4f}%"
    )

    if missing or unexpected:
        print(f"[FAIL] Missing transitions: {missing}", file=sys.stderr)
        print(f"[FAIL] Unexpected transitions: {unexpected}", file=sys.stderr)
        return 1

    print("[OK] 1:1 FRAME-EXACT SYNC VERIFIED: 0 missing beats, 0 extra transitions, 0 frame drift!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

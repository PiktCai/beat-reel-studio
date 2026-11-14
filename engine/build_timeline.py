#!/usr/bin/env python3
"""Parametric timeline builder supporting both Swiss modular grids and Clockwise Orbital Zine layouts."""

import json
import math
import sys
from pathlib import Path

# Swiss Safe Center Lightwell
SAFE_SWISS = (192, 248, 528 - 192, 656 - 248)

# Orbital Editorial Center Zone (tighter island around typography so perimeter plates shine larger)
SAFE_ORBIT = (212, 276, 508 - 212, 668 - 276)

# ---- Layout Mode 1: Swiss Modular Bricks (for Architecture Ep02 / Painting Ep03) ----
GRID_A_11 = [
    [24,  24,  268, 216], [432, 664, 264, 272], [496, 24,  200, 216],
    [24,  420, 160, 236], [300, 24,  188, 216], [536, 248, 160, 236],
    [192, 664, 232, 132], [24,  248, 160, 164], [24,  664, 160, 272],
    [536, 492, 160, 164], [192, 804, 232, 132],
]
GRID_B_11 = [
    [24,  24,  160, 286], [192, 24,  292, 216], [492, 24,  204, 216],
    [536, 248, 160, 200], [24,  664, 268, 272], [24,  318, 160, 178],
    [464, 664, 232, 132], [536, 456, 160, 200], [24,  504, 160, 152],
    [300, 664, 156, 272], [464, 804, 232, 132],
]
GRID_C_11 = [
    [536, 24,  160, 286], [24,  24,  250, 216], [282, 24,  246, 216],
    [24,  248, 160, 224], [462, 664, 234, 272], [24,  664, 248, 132],
    [536, 318, 160, 165], [280, 664, 174, 272], [24,  480, 160, 176],
    [536, 491, 160, 165], [24,  804, 248, 132],
]
GRID_SYM_10 = [
    [250, 24,  220, 216], [24,  664, 218, 272], [478, 24,  218, 216],
    [24,  248, 160, 200], [478, 664, 218, 272], [536, 248, 160, 200],
    [24,  24,  218, 216], [536, 456, 160, 200], [250, 664, 220, 272],
    [24,  456, 160, 200],
]

# ---- Layout Mode 2: Lush Larger Clockwise Zine Orbits (for Ep04+ editorial style) ----
# Strictly ordered sequentially CLOCKWISE around (360, 480) with 10-16px staggered seams & large showcase area!
ORBIT_A_11 = [
    [24,  50,  182, 212],  # 0: ~10:30 Top-Left tall
    [220, 40,  274, 212],  # 1: 12:00 Top-Center hero
    [508, 60,  188, 200],  # 2: 1:30 Top-Right
    [520, 274, 178, 184],  # 3: 2:45 Right-Upper
    [518, 470, 178, 188],  # 4: 4:00 Right-Lower
    [512, 674, 184, 222],  # 5: 5:15 Bottom-Right tall
    [352, 682, 146, 232],  # 6: 6:00 Bottom-Mid-Right tall
    [194, 688, 144, 212],  # 7: 6:45 Bottom-Mid-Left
    [26,  676, 154, 224],  # 8: 7:45 Bottom-Left tall
    [22,  474, 176, 186],  # 9: 8:45 Left-Lower
    [26,  276, 174, 184],  # 10: 9:45 Left-Upper
]

ORBIT_B_11 = [
    [218, 42,  276, 208],  # 0: Starts 12:00 Top-Center!
    [508, 56,  188, 204],  # 1: 1:30
    [518, 274, 180, 186],  # 2: 2:45
    [522, 474, 176, 184],  # 3: 4:00
    [506, 676, 190, 224],  # 4: 5:15
    [348, 686, 146, 226],  # 5: 6:00
    [190, 680, 144, 218],  # 6: 6:45
    [24,  676, 152, 220],  # 7: 7:45
    [26,  478, 174, 184],  # 8: 8:45
    [22,  278, 176, 186],  # 9: 9:45
    [24,  52,  180, 212],  # 10: 10:30 Closes top ring!
]

ORBIT_SYM_10 = [
    [26,  54,  182, 208],  # 0: 10:30 Top-Left
    [222, 40,  274, 212],  # 1: 12:00 Top-Center
    [510, 54,  182, 208],  # 2: 1:30 Top-Right
    [520, 276, 178, 186],  # 3: 2:45 Right-Upper
    [520, 476, 178, 186],  # 4: 4:15 Right-Lower
    [472, 678, 222, 226],  # 5: 5:15 Bottom-Right hero
    [266, 686, 192, 224],  # 6: 6:00 Bottom-Center
    [28,  678, 224, 226],  # 7: 7:15 Bottom-Left hero
    [22,  476, 178, 186],  # 8: 8:30 Left-Lower
    [22,  276, 178, 186],  # 9: 9:45 Left-Upper
]

ORBIT_C_11 = [
    [506, 56,  190, 204],  # 0: Starts 1:30 Top-Right!
    [518, 274, 180, 186],  # 1: 2:45
    [520, 474, 176, 186],  # 2: 4:00
    [510, 676, 186, 224],  # 3: 5:15
    [350, 686, 146, 228],  # 4: 6:00
    [192, 682, 144, 214],  # 5: 6:45
    [24,  676, 154, 222],  # 6: 7:45
    [22,  476, 178, 184],  # 7: 8:45
    [26,  278, 174, 184],  # 8: 9:45
    [24,  50,  182, 214],  # 9: 10:30
    [220, 40,  272, 212],  # 10: 12:00 Closes top center!
]

BEAT_SLOTS = [
    {"startFrame": 107, "endFrame": 150, "swiss": GRID_A_11,   "orbit": ORBIT_A_11,   "offsets": [0, 5, 9, 11, 14, 16, 18, 20, 24, 26, 32]},
    {"startFrame": 150, "endFrame": 196, "swiss": GRID_B_11,   "orbit": ORBIT_B_11,   "offsets": [0, 2, 4, 7, 10, 13, 16, 19, 23, 28, 33]},
    {"startFrame": 196, "endFrame": 242, "swiss": GRID_SYM_10, "orbit": ORBIT_SYM_10, "offsets": [0, 2, 4, 6, 8, 11, 13, 16, 21, 29]},
    {"startFrame": 242, "endFrame": 288, "swiss": GRID_C_11,   "orbit": ORBIT_C_11,   "offsets": [0, 2, 5, 8, 12, 16, 20, 24, 27, 30, 35]},
    {"startFrame": 288, "endFrame": 331, "swiss": GRID_A_11,   "orbit": ORBIT_A_11,   "offsets": [0, 2, 5, 8, 12, 16, 20, 23, 26, 29, 34]},
    {"startFrame": 331, "endFrame": 377, "swiss": GRID_B_11,   "orbit": ORBIT_B_11,   "offsets": [0, 3, 6, 9, 12, 16, 19, 22, 26, 29, 34]},
    {"startFrame": 377, "endFrame": 422, "swiss": GRID_C_11,   "orbit": ORBIT_C_11,   "offsets": [0, 3, 6, 9, 12, 16, 19, 23, 26, 30, 35]},
    {"startFrame": 422, "endFrame": 472, "swiss": GRID_C_11,   "orbit": ORBIT_A_11,   "offsets": [0, 3, 6, 9, 12, 16, 20, 23, 27, 30, 35]},
]

COVER_SLOTS_SWISS = [
    {"frame": 48, "rect": [34,  340, 212, 268]},
    {"frame": 52, "rect": [254, 340, 212, 186]},
    {"frame": 58, "rect": [474, 340, 212, 268]},
    {"frame": 61, "rect": [34,  616, 212, 150]},
    {"frame": 64, "rect": [254, 534, 212, 232]},
    {"frame": 69, "rect": [474, 616, 212, 150]},
]

COVER_SLOTS_ORBIT = [
    {"frame": 48, "rect": [36,  352, 192, 236]},
    {"frame": 52, "rect": [258, 326, 202, 170]},
    {"frame": 58, "rect": [488, 356, 194, 222]},
    {"frame": 61, "rect": [52,  614, 182, 144]},
    {"frame": 64, "rect": [262, 520, 196, 236]},
    {"frame": 69, "rect": [482, 606, 198, 152]},
]


def rects_overlap(a, b, pad=0):
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    return not (ax0 + aw + pad <= bx0 or bx0 + bw + pad <= ax0 or ay0 + ah + pad <= by0 or by0 + bh + pad <= ay0)


def validate_grid(rects, safe_box, min_pad=7):
    for i, r in enumerate(rects):
        x, y, w, h = r
        assert 20 <= x and x + w <= 702, f"Out of X bounds {i}: {r}"
        assert 24 <= y and y + h <= 936, f"Out of Y bounds {i}: {r}"
        assert not rects_overlap(r, safe_box, pad=6), f"Overlaps safe zone {i}: {r}"
        for j in range(i + 1, len(rects)):
            assert not rects_overlap(r, rects[j], pad=min_pad), f"Spacing violation {i},{j}: {r} vs {rects[j]}"


def relax_rect_to_image(slot, img):
    """Subtly adapt slot box to image aspect ratio (never expanding outside slot bounds!)."""
    x, y, w, h = slot
    im_ar = img["w"] / max(1, img["h"])
    sl_ar = w / max(1, h)
    # Keep at least 91% of both dimensions so cards stay big & punchy while keeping natural aspect
    if im_ar >= sl_ar:
        rw = w
        rh = max(int(round(h * 0.91)), min(h, int(round(w / im_ar))))
    else:
        rh = h
        rw = max(int(round(w * 0.91)), min(w, int(round(h * im_ar))))
    cx, cy = x + w * 0.5, y + h * 0.5
    return [int(round(cx - rw * 0.5)), int(round(cy - rh * 0.5)), rw, rh]


def assign_optimal_aspect(images, slots, orbital_relax=False):
    n = len(slots)
    assert len(images) >= n, f"Need >= {n} images, got {len(images)}"

    def cost(im, sl):
        im_ar = im["w"] / max(1, im["h"])
        sl_ar = sl[2] / max(1, sl[3])
        return abs(math.log(im_ar / sl_ar))

    if len(images) > n:
        chosen = []
        rem = list(images)
        for sl in sorted(slots, key=lambda s: s[2] / s[3]):
            best_i = min(range(len(rem)), key=lambda i: cost(rem[i], sl))
            chosen.append(rem.pop(best_i))
        imgs = chosen
    else:
        imgs = list(images[:n])

    sl_order = sorted(range(n), key=lambda i: slots[i][2] / slots[i][3])
    im_order = sorted(range(n), key=lambda i: imgs[i]["w"] / imgs[i]["h"])
    perm = [0] * n
    for si, ii in zip(sl_order, im_order):
        perm[si] = ii

    improved = True
    while improved:
        improved = False
        for i in range(n):
            for j in range(i + 1, n):
                before = cost(imgs[perm[i]], slots[i]) + cost(imgs[perm[j]], slots[j])
                after = cost(imgs[perm[j]], slots[i]) + cost(imgs[perm[i]], slots[j])
                if after < before - 1e-9:
                    perm[i], perm[j] = perm[j], perm[i]
                    improved = True

    ordered = [imgs[perm[i]] for i in range(n)]
    if orbital_relax:
        rects = [relax_rect_to_image(slots[i], ordered[i]) for i in range(n)]
    else:
        rects = [list(s) for s in slots]
    return ordered, rects


def pick_cover_file(cands, target_ar, preferred_file=None):
    if preferred_file:
        for item in cands:
            if item["file"] == preferred_file:
                return item["file"]
    return min(cands, key=lambda x: abs((x["w"] / max(1, x["h"])) - target_ar))["file"]


def build_timeline(theme_dir: Path) -> Path:
    theme = json.loads((theme_dir / "theme.json").read_text(encoding="utf-8"))
    manifest = json.loads((theme_dir / "assets" / "manifest.json").read_text(encoding="utf-8"))

    layout_mode = theme.get("layoutMode", "swiss")
    typo_style = theme.get("typoStyle", "monograph")
    cover_style = theme.get("coverStyle", typo_style)
    is_orbital = (layout_mode == "orbital")

    chapters = theme["chapters"]
    assert len(chapters) == 8, f"Expected 8 chapters, got {len(chapters)}"

    timeline_scenes = []
    for idx, (meta, beat) in enumerate(zip(chapters, BEAT_SLOTS), start=1):
        sid = meta["id"]
        slots = beat["orbit"] if is_orbital else beat["swiss"]
        validate_grid(slots, SAFE_ORBIT if is_orbital else SAFE_SWISS, min_pad=10 if is_orbital else 7)
        imgs = manifest[sid]
        assigned_imgs, rects = assign_optimal_aspect(imgs, slots, orbital_relax=is_orbital)
        items = [
            {
                "file": im["file"],
                "title": im["title"],
                "offsetFrame": off,
                "rect": rect,
            }
            for im, rect, off in zip(assigned_imgs, rects, beat["offsets"])
        ]
        timeline_scenes.append({
            "id": sid,
            "indexBadge": meta.get("indexBadge", f"{idx:02d}"),
            "topLeft": meta.get("topLeft"),
            "startFrame": beat["startFrame"],
            "endFrame": beat["endFrame"],
            "bgHex": meta["bgHex"],
            "accentHex": meta.get("accentHex"),
            "bodyHex": meta.get("bodyHex"),
            "sealHex": meta.get("sealHex"),
            "titleCn": meta["titleCn"],
            "titleEn": meta["titleEn"],
            "years": meta.get("years", ""),
            "descCn": meta["descCn"],
            "kwHeader": meta.get("kwHeader"),
            "tagsEn": meta["tagsEn"],
            "items": items,
        })

    intro_meta = theme["intro"]
    cover_spec = intro_meta.get("coverEras") or [ch["id"] for ch in chapters[:6]]
    use_orbit_cover = is_orbital and (cover_style == "editorial_zine")
    cover_slots = COVER_SLOTS_ORBIT if use_orbit_cover else COVER_SLOTS_SWISS
    intro_thumbs = []
    for idx, slot in enumerate(cover_slots):
        spec = cover_spec[idx]
        if isinstance(spec, str):
            era_id, pref = spec, None
        else:
            era_id, pref = spec[0], spec[1]
        r = list(slot["rect"])
        target_ar = r[2] / r[3]
        f = pick_cover_file(manifest[era_id], target_ar, pref)
        if use_orbit_cover:
            matched_im = next(x for x in manifest[era_id] if x["file"] == f)
            r = relax_rect_to_image(r, matched_im)
        intro_thumbs.append({"file": f, "frame": slot["frame"], "rect": r})

    config = {
        "designWidth": 720,
        "designHeight": 960,
        "outputScale": 1.5,
        "fps": 30,
        "totalFrames": 472,
        "outputFile": theme.get("outputFile", f"{theme_dir.name}_1to1.mp4"),
        "cropBiasY": theme.get("cropBiasY", 0.50),
        "typoStyle": typo_style,
        "coverStyle": cover_style,
        "layoutMode": layout_mode,
        "episodeLabel": theme["episodeLabel"],
        "intro": {
            "endFrame": 107,
            "paperHex": intro_meta.get("paperHex", "#EFECE6"),
            "accentHex": intro_meta.get("accentHex", "#C03D22"),
            "metaLeft": intro_meta["metaLeft"],
            "metaRight": intro_meta["metaRight"],
            "kicker": intro_meta["kicker"],
            "subtitleEn": intro_meta.get("subtitleEn", "Visual Aesthetics"),
            "title1": {"text": intro_meta["title1"], "frame": 9},
            "title2": {"text": intro_meta["title2"], "frame": 34},
            "thumbs": intro_thumbs,
            "episode": {"text": theme["episodeLabel"], "frame": 76},
            "category": {"text": intro_meta["category"], "frame": 83},
            "tags": intro_meta["tags"],
            "volText": "vol",
            "volNum": intro_meta["volNum"],
            "volHideFrame": 107,
        },
        "scenes": timeline_scenes,
    }

    out_path = theme_dir / "timeline.json"
    out_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: build_timeline.py <theme_dir>", file=sys.stderr)
        return 1
    out = build_timeline(Path(sys.argv[1]).resolve())
    print(f"Generated beat-synced timeline -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

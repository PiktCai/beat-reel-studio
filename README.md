# Beat Reel Studio

Programmatic beat-synchronized vertical editorial video generator (`1080×1440`, `30 fps`, `472` frames / `15.733s`) built with **Python + Swift CoreGraphics/AppKit + FFmpeg**.

Includes two curated flagship reference episodes ready to rebuild offline in ~8 seconds:
- **`themes/painting_ep03`** — *Swiss Monograph Style*: modular dark-gallery grid, academic serif/sans pairing, Wikipedia/Commons fetcher (`engine/fetch_theme.py`).
- **`themes/core_ep04`** — *Editorial Orbital Zine + Monograph Cover*: clockwise orbital reveal around compact cotton-paper center typography, powered by diversified multi-motif Pinterest curation (`engine/fetch_pinterest.py`, `engine/make_contact_sheets.swift`, `engine/promote_picks.py`).

AI Agents using this repo should read **[`AGENTS.md`](./AGENTS.md)** before generating a new episode.

---

## Prerequisites

- **macOS** (uses native Swift `AppKit`/`CoreGraphics`/`ImageIO` and `sips`)
- **Xcode Command Line Tools** (`swift`, `swiftc`)
- **FFmpeg & FFprobe** (`brew install ffmpeg`)
- **Python 3.10+**
- *(Optional, for Pinterest curation)* **`pinterest-dl`** (`pip install -r requirements.txt`)

## Quick Start (Offline Rebuild)

Rebuild either reference video from its committed `assets/` and verify exact `97/97` frame-to-audio transition sync (`0` drift):

```bash
python3 engine/run_theme.py themes/core_ep04
python3 engine/run_theme.py themes/painting_ep03
```

Outputs are written to `themes/<name>/output/<outputFile>`.

## Creating a New Episode (Pinterest Orbital Zine Workflow)

```bash
# 1. Copy the starter template and customize copy, palettes, and 10-12 distinct motif queries/chapter
cp -r themes/_template themes/my_ep05

# 2. Fetch diversified sub-motif Pinterest candidates into themes/my_ep05/.candidates/
python3 engine/fetch_pinterest.py themes/my_ep05 --per-query 6

# 3. Generate deduplicated contact sheets (sheet_<era>.png + index_<era>.json)
swift -module-cache-path /tmp/swift_cache engine/make_contact_sheets.swift themes/my_ep05

# 4. Inspect every sheet_<era>.png visually and write themes/my_ep05/.candidates/picks.json
#    (11 pickIds per chapter; 10 for chapter 3)
python3 engine/promote_picks.py themes/my_ep05

# 5. Update intro.coverEras in themes/my_ep05/theme.json if needed, then render & verify sync
python3 engine/run_theme.py themes/my_ep05 --keep-frames
```

## Project Layout

```text
beat-reel-studio/
├── AGENTS.md                        # Step-by-step agent playbook & aesthetic QA rules
├── CLAUDE.md                        # Agent entry pointer to AGENTS.md
├── README.md
├── requirements.txt                 # pinterest-dl dependency
├── audio/
│   └── audio.wav                    # Master beat track (15.733s, 97 visual transition cues)
├── bin/                             # Auto-compiled binary output (gitignored)
├── engine/
│   ├── build_timeline.py            # Beat slots, Swiss & Orbital grids, aspect optimization
│   ├── render.swift                 # High-DPI CoreGraphics frame renderer (98 unique states)
│   ├── run_theme.py                 # Full pipeline runner + auto-compile + FFmpeg encode
│   ├── verify_sync.py               # FFprobe + area-scaled pixel diff 1:1 beat verifier
│   ├── fetch_theme.py               # Wikipedia / Commons image fetcher (Style A themes)
│   ├── fetch_pinterest.py           # Multi-motif Pinterest fetcher (Style B themes)
│   ├── make_contact_sheets.swift    # Visual dedupe, cutout/alt filtering & sheet builder
│   └── promote_picks.py             # Converts & validates picks.json into assets/manifest.json
└── themes/
    ├── _template/                   # Copy-ready orbital zine theme.json scaffold
    ├── painting_ep03/               # Reference Style A: Swiss Monograph (87 curated works)
    └── core_ep04/                   # Reference Style B: Core Aesthetics Ep04 (87 Pinterest picks)
```

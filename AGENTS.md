# AGENTS.md — Beat Reel Studio Agent Playbook

This repository renders 9:12 (`1080x1440`, `30 fps`, `472` frames / `15.733s`) beat-synchronized visual anthology short videos anchored to the fixed track in `audio/audio.wav` (`97` exact visual transitions, verified at `0` frame drift).

Use this playbook to reproduce either of the two reference styles (`themes/painting_ep03` or `themes/core_ep04`) or generate an all-new episode on any topic.

---

## 1. Style Presets (`theme.json`)

Every episode requires **8 chapters** paired to `BEAT_SLOTS` in `engine/build_timeline.py`:
- Chapter card counts (fixed to beat timing): `[11, 11, 10, 11, 11, 11, 11, 11]` (`87` chapter slots total; **Chapter 3 has 10 slots**, all others have **11**).
- Audio/Visual timeline (`0..471`, 1-indexed output PNGs `frame_0001.png`..`frame_0472.png`):
  - **Intro / Cover**: frames `0..106` (all 6 cover plates revealed cleanly around `frame_0091.png`)
  - **Ch 01**: `107..149` (settled frame `frame_0145.png`)
  - **Ch 02**: `150..195` (settled frame `frame_0194.png`)
  - **Ch 03**: `196..241` (`10` cards, settled frame `frame_0240.png`)
  - **Ch 04**: `242..287` (settled frame `frame_0285.png`)
  - **Ch 05**: `288..330` (settled frame `frame_0329.png`)
  - **Ch 06**: `331..376` (settled frame `frame_0375.png`)
  - **Ch 07**: `377..421` (settled frame `frame_0420.png`)
  - **Ch 08**: `422..471` (settled frame `frame_0470.png`)

Choose your style combination in `theme.json`:

| Key | `painting_ep03` (Swiss Monograph) | `core_ep04` (Editorial Orbital Zine — Recommended for Pop Aesthetics) |
| :--- | :--- | :--- |
| `layoutMode` | `"swiss"` | `"orbital"` (staggered clockwise orbit, `10-16px` gaps, `min_scale=0.91`) |
| `coverStyle` | `"monograph"` | `"monograph"` (keeps high-contrast Swiss gallery cover) |
| `typoStyle` | `"monograph"` | `"editorial_zine"` (light pastel/cotton-paper spread + Baskerville/PingFang/STFangsong + circular seal) |
| `bgHex` | Deep jewel/dark canvas (`#5B1B18`, `#0F3554`, `#16534C`) | Light cotton paper (`#F1ECF6`, `#E8EFF5`, `#F2ECE3`, etc.) |
| `accentHex`, `bodyHex`, `sealHex` | Unused (white ink over dark ground) | Required in each chapter for high-contrast dark ink + seal circle |
| Asset source | `engine/fetch_theme.py` (Wikipedia/Commons works of art) | `engine/fetch_pinterest.py` + contact-sheet curation + `engine/promote_picks.py` |

---

## 2. End-to-End Replication Workflow (New Episode in Style B / Ep04)

### Step 1: Scaffold `themes/<ep_name>/theme.json`
Start from `themes/_template/theme.json` and fill in 8 chapters:
- **Typography fit (`SAFE_ORBIT` center column is `296x392` px)**:
  - `titleEn`: Keep under ~14–16 chars (`34pt` Baskerville `(Title)` auto-shrinks if wider).
  - `titleCn`: Crisp 3–6 Chinese characters (`27pt` PingFangSC).
  - `descCn`: **Exactly 2 short lines** (`<= 14` CJK chars per line with `\n` break).
  - `tagsEn`: **3 concise lowercase search phrases** separated by `\n`.
- **Per-Chapter Query Design (CRITICAL — Prevent Series Repetition!)**:
  - NEVER run 1–2 broad queries with `-n 30` (Pinterest returns 8 angles of the same viral post or creator series).
  - Instead, write **10–12 mutually exclusive visual sub-motif queries** in `ch["queries"]` spanning different subjects, spatial scales (macro, still-life object, interior, architecture, urban dusk, open landscape), and compositions, while sharing a unified color mood.
  - Avoid query words like `meme`, `quote`, `collage`, `poster`, `typography`, `template`, `clipart`, `sticker`. Prefer concrete photographic or 3D lighting descriptors (`"... photography"`, `"... interior"`, `"... close up"`).

### Step 2: Fetch Pinterest Candidates
Ensure `pinterest-dl` is installed (`pip install -r requirements.txt`). Then run:
```bash
python3 engine/fetch_pinterest.py themes/<ep_name> --per-query 6
```
Candidates download into `themes/<ep_name>/.candidates/<chapter_id>/q<idx>_<slug>/` alongside `.json` metadata.
*(Note: If running inside a network-restricted sandbox, run this network command outside the sandbox; run all subsequent build/sheet/promote steps sandboxed.)*

### Step 3: Build & Visually Inspect Contact Sheets
Compile/run the Swift visual filter and sheet builder:
```bash
swift -module-cache-path /tmp/swift_cache engine/make_contact_sheets.swift themes/<ep_name>
```
This automatically filters tiny/broken files, `BAD_TOKENS` in metadata, pure `#FFFFFF` sticker cutouts, exact Pin ID duplicates, and perceptual `8x8` RGB re-upload duplicates (`RMS < 0.085`), outputting `sheet_<chapter_id>.png` and `index_<chapter_id>.json` in `themes/<ep_name>/.candidates/`.

Inspect every `sheet_<chapter_id>.png` visually and pick `pickId`s (`10` for Ch 03, `11` for all other chapters) into `themes/<ep_name>/.candidates/picks.json`:
```json
{
  "c1_style": [2, 6, 10, 13, 19, 21, 27, 30, 36, 40, 41],
  "...": "..."
}
```
Follow the **"和而不同、美美与共"** curation standard strictly:
1. **Zero repetition**: At most **1 pick per sub-motif query** (`qXX`) and never 2 angles/recolors of the same building, statue, prop, or artist series inside a chapter.
2. **Cohesive palette**: All 10–11 picks on one screen must share harmonious lighting/color temperature (reject glaring white studio backgrounds inside moody chapters, or neon oranges clashing with cool cyan chapters).
3. **Aspect ratio balance**: Look at `WIDE/SQ` badges on the sheet (`ar >= 0.95`). Pick **2–4 `WIDE/SQ`** images and **7–9 portrait** (`ar 0.56–0.85`) images per chapter so `assign_optimal_aspect` fits `12:00` (`274x212`, `ar=1.29`) and horizontal orbital cards cleanly without heavy cropping.
4. **Zero-slop hygiene**: Immediately reject any candidate showing watermarks, embedded corner badges, meme captions, white sticker margins, borders, or collage-of-collages.
5. **Hero Cover selection (`coverEras`)**: Pick 6 striking, scroll-stopping thumbnails for `intro.coverEras`:
   - `COVER_SLOTS_SWISS` indices `0, 2, 4` (`01`, `03`, `05`) are **portrait** (`~0.79–0.91`).
   - `COVER_SLOTS_SWISS` indices `1, 3, 5` (`02`, `04`, `06`) are **horizontal (`WIDE/SQ`, `ar >= 0.95`)** (`1.14–1.41`). Pin `["chapter_id", "chapter_id_XX.jpg"]` to match slot shapes!

### Step 4: Promote Assets, Build & Verify 1:1 Beat Sync
```bash
python3 engine/promote_picks.py themes/<ep_name>
```
Update `intro.coverEras` in `themes/<ep_name>/theme.json` if slot filenames changed, then render and verify:
```bash
python3 engine/run_theme.py themes/<ep_name> --keep-frames
```
Confirm `verify_sync.py` prints:
`[OK] 1:1 FRAME-EXACT SYNC VERIFIED: 0 missing beats, 0 extra transitions, 0 frame drift!`

### Step 5: Final Visual Audit & Cleanup
Inspect `.render_frames/frame_0091.png` (cover) and the 8 settled chapter frames (`0145`, `0194`, `0240`, `0285`, `0329`, `0375`, `0420`, `0470`) plus `output/<outputFile>` as video. Fix any residual watermark/edge crop/motif repeat by swapping the `pickId` in `picks.json`, re-running `promote_picks.py` + `run_theme.py`.

Once satisfied, remove temporary working directories (also ignored by `.gitignore`):
```bash
rm -rf themes/<ep_name>/.candidates themes/<ep_name>/.render_frames
```

---

## 3. Reproducing Wikimedia / Museum Episodes (Style A / Ep03)

For fine art, architecture, or historical subjects covered well by Wikipedia:
```bash
python3 engine/run_theme.py themes/painting_ep03 --with-fetch
```
Or rebuild offline directly from committed `assets/`:
```bash
python3 engine/run_theme.py themes/core_ep04
python3 engine/run_theme.py themes/painting_ep03
```

---
name: kaka-vision-producer
description: End-to-end production workflow for 卡卡老师《视光小课堂》 1080x1920 30fps editorial medical short videos (Kaka Vision Video Kit v2.0). Use when creating, updating, or auditing new episodes (EP05+).
---

# Kaka Vision Video Producer (v4.0 Three.js 3D Cinema & Swiss Editorial)

Standard operating workflow for producing cinema-grade 1080×1920 @ 30fps vertical optometry science short videos in `kaka-vision-video-kit` using WebGL 2.0 Three.js PBR 3D scenes, Swiss editorial typography, and freshly illustrated sunlit architectural scenes.

## 1. Locked Voice & Audio Baseline (方案 01 · 活力眼科小姐姐)

- **Engine**: `edge` (`src/synthesize_voice.py`)
- **Voice**: `zh-CN-XiaoyiNeural`
- **Default Parameters**: `rate="+8%"`, `pitch="-4Hz"`, `-16 LUFS` loudness normalization, 24kHz mono WAV master.
- **BGM & SFX (`src/audio_mix_v2.py`)**: Warm felt-pad + glass-marimba + soft groove pulse (boosted ~2.2× in v2.2 so clearly audible and musical beneath speech, with smooth ducking `0.40`/`0.74`) plus bespoke procedural SFX (`impact`, `whoosh`, `ping`, `pop`, `chime`, `alert`, `shield`, `anchor`, `chain_1..5`).
- **Dynamic Rhythm Overrides**:
  - Fast causal chains / enumerations: progressively step `rate` from `+12%` up to `+20%` with tight `post_pause: 0.08`.
  - Memory anchor keywords (e.g., `"光学降噪"`): slow down (`rate: "-6%"`, `pitch: "-5Hz"`), paired with `sfx: "anchor"`.
- **Mandatory Pronunciation Audit**:
  Always listen to the synthesized voiceover before final rendering and use `tts_text` (separate from on-screen `subtitle`) to fix polyphones and acronyms:
  - `少长` / `别再长了` (meaning "grow") -> write `少涨` / `别再涨了` in `tts_text` so TTS reads `zhǎng` instead of `cháng`.
  - English trial acronyms (`CYPRESS`, `CATHAY`) -> use Title Case (`Cypress`, `Cathay`) in `tts_text`; `DOT 0.2` -> `D O T 零点二`; `"3.0"字样` -> `三点零字样`.
  - `ON/OFF` -> write `ON OFF` with spaces.
  - Always terminate every `tts_text` with Chinese punctuation (`，`, `。`, `？`, `！`) to prevent Edge TTS truncation.

## 2. Visual & Motion Design System (v4.0 Three.js 3D Cinema · Anti-PPT Swiss Editorial)

- **Canvas**: `1080 × 1920`, `30 fps`, deterministic `window.renderFrame(state)` inside `episodes/<ep_dir>/scene.html`.
- **WebGL 2.0 + Local Three.js (`vendor/three.min.js`)**: `src/web_render_v2.py` launches Chromium with ANGLE SwiftShader WebGL 2.0 (`--use-gl=angle --use-angle=swiftshader --enable-webgl`). Render Three.js synchronously inside `window.renderFrame(state)` (strictly driven by `state.t`, never `requestAnimationFrame`) at `720×1280` internal WebGL resolution with `antialias: true`, while HTML Swiss typography & Teacher Kaka render at native `1080×1920` for both ultra-crisp text and ~4× faster CPU WebGL speed!
- **Anti-PPT Swiss Editorial Aesthetic (NO "土气" Template Clutter)**:
  - **NEVER** use dark/navy backgrounds — keep sunlit bright alabaster/pearl-stone 3D daylight studios (`#ECEFEB`) with sculpted directional key/fill lighting & PMREM softbox reflections.
  - **NO** top rounded chapter progress bar, **NO** big white rounded card containers framing the 3D scene, **NO** loud rainbow gradient headlines or excessive colored pill badges.
  - Use generous whitespace, charcoal `#111827` editorial typography, and at most **1–2 restrained accent colors** (e.g., Optical Ice Blue `#0284C7` + Editorial Coral `#E11D48`).
- **Plan A Cinematic Teacher Kaka Choreography (`92px` L/R tall-phone safe, Douyin bottom safe)**:
  - **Host / Intro / Metaphor / Outro scenes**: Half-body Teacher Kaka (`left: 530px; top: 1295px; width: 472px;`) paired with a borderless frosted-alabaster editorial caption bar (`left: 92px; top: 1418px; width: 468px; border-left: 4px solid #0284C7;`).
  - **Full-Screen 3D Immersion scenes** (3D macro optics, first-person POV, Vision Pro glass stack): Teacher Kaka glides smoothly out of frame so the full-bleed 3D camera shines unobstructed, with a clean cinema lower-third frosted caption at `top: 1468px; left: 92px; right: 92px;`.
- **Fresh Per-Episode Custom Backgrounds (`assets/backgrounds/`)**: Always illustrate a fresh, bright, theme-matched sunlit architectural background (e.g., `bg_minimalist_vision_loft.jpg`) instead of reusing previous clinic backgrounds!
- **Custom-Illustrated Sunlit Backgrounds** (`assets/backgrounds/`):
  - `bg_optics_research_lab.jpg` (sunlit Scandinavian optometry lab with biometer & lens display)
  - `bg_pediatric_consultation_studio.jpg` (sunlit terrace-view pediatric consultation studio)
- **0.0px Mouth Rig**: Never manually overlay mouths in HTML/CSS; `src/web_render_v2.py` pre-bakes 0.0px offscreen-calibrated sprites (`682×1024`) from `POSE_MOUTH_RIG` into `.cache/kaka_sprites_v2/`.
- **Canvas Layering Rule**: Any optical graphics meant to appear crisp over frosted `backdrop-filter` glass cards MUST draw on foreground `#fg-canvas` above those cards (never behind `backdrop-filter`).

## 3. Production & Quality Gate Commands

```bash
# Step 1: Synthesize voiceover & exact timeline
.venv/bin/python -m src.synthesize_voice \
  --script episodes/<ep_dir>/script.json \
  --out-dir audio/<prefix>

# Step 2: Render 12 high-res keyframes + contact sheet (MANDATORY VISUAL AUDIT)
.venv/bin/python -m src.web_render_v2 \
  --scene episodes/<ep_dir>/scene.html \
  --audio-dir audio/<prefix> \
  --prefix <prefix> \
  --out-dir output \
  --keyframes

# Step 3: Full 30fps 4-worker render + zero-NAL-error check + <20MB pure HTML export
.venv/bin/python -m src.web_render_v2 \
  --scene episodes/<ep_dir>/scene.html \
  --audio-dir audio/<prefix> \
  --prefix <prefix> \
  --out-dir output \
  --title "<Episode Page Title>" \
  --fps 30 \
  --workers 4
```

## 4. Mandatory Pre-Delivery Checklist

- [ ] Audio audited by ear: zero polyphone errors, zero truncated segments, smooth BGM ducking, tasteful SFX.
- [ ] All 12 keyframes visually audited at full resolution: zero text clipping, zero orphan characters, zero card/character overlap, crisp typography.
- [ ] `ffmpeg -v error -i <mp4> -f null -` passes with zero errors.
- [ ] Pure video HTML exported under 20 MB for one-tap mobile/browser playback.
- [ ] Code/script/scene committed to GitHub (`main`); rendered `.mp4` delivered to Google Drive `episodes_1080p_mp4/` (never commit large `.mp4` files to Git).

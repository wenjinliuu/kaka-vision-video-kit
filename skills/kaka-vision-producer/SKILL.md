---
name: kaka-vision-producer
description: End-to-end production workflow for 卡卡老师《视光小课堂》 1080x1920 30fps editorial medical short videos (Kaka Vision Video Kit v2.0). Use when creating, updating, or auditing new episodes (EP05+).
---

# Kaka Vision Video Producer (v2.3)

Standard operating workflow for producing magazine-grade 1080×1920 @ 30fps vertical optometry science short videos in `kaka-vision-video-kit`.

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

## 2. Visual & Motion Design System (v2.3 Unified Half-Body Lecture · Tall-Phone & Douyin Safe · All-Bright Vibrant)

- **Canvas**: `1080 × 1920`, `30 fps`, deterministic `window.renderFrame(state)` inside `episodes/<ep_dir>/scene.html`.
- **Mandatory Bright Palette Rule**: Always use **bright, airy porcelain/pastel-sky studio backgrounds** (NO dark/navy screens!) paired with vibrant same-hue gradients (`PALETTES`: 晴空蓝青 `#1A8CFF→#14C8B8`, 暖阳橙粉 `#FF8A34→#FF2E63`, 星夜紫 `#6366F1→#A855F7`, 翡翠薄荷 `#10B981→#34D399`, 琥珀金 `#F59E0B→#FBBF24`, 玫瑰珊瑚 `#E11D48→#FB7185`).
- **Strict v2.3 Tall-Phone (19.5:9 / 20:9) & Douyin Safe Area**:
  - **Left & Right**: **`92px`** (`X: 92..988`, usable width `896px`) so tall-screen social feeds never clip top-left/top-right pills or card edges.
  - **Top chrome**: `top: 156px`; editorial header: `top: 224px`; main visual stage: **`Y: 400..1285`** (strictly `<= 1290px` so upper charts/cards NEVER collide with half-body Teacher Kaka).
  - **Unified Half-Body Teacher Kaka + Speech Card (`#classic-layer`, ALL teaching scenes — NO circular PiP!)**:
    - `#classic-kaka-img`: `left: 530px; top: 1295px; width: 472px;` (silhouette stays well inside `92px` right safe margin, head starts at `Y ≈ 1323px`).
    - `#classic-sub-card`: `left: 92px; top: 1405px; width: 474px; min-height: 148px;` with speaker kicker `卡卡老师 · 视光科普`, `30px` bold highlighted subtitle, and right-pointing speech tail (`bottom ~325px`, cleanly above Douyin's bottom caption).
  - **Outro CTA card**: `top: 1385px` (`bottom: 290px`) with full-body waving `kaka_02`.
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

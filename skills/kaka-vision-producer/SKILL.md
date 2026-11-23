---
name: kaka-vision-producer
description: End-to-end production workflow for 卡卡老师《视光小课堂》 1080x1920 30fps editorial medical short videos (Kaka Vision Video Kit v5.0). Use when creating, updating, or auditing new episodes (EP05+).
---

# Kaka Vision Video Producer (v5.0 Pixar / Apple Health 3D Art + 2.5D Cinema)

Standard operating workflow for producing cinema-grade 1080×1920 @ 30fps vertical optometry science short videos in `kaka-vision-video-kit` using **Pixar / Apple Health Octane-grade 3D artworks + smooth 2.5D camera motion + live HTML5 Canvas optical FX + sunlit energetic palettes + lip-synced half-body & animated-mouth circular Teacher Kaka**.

## 1. Locked Voice & Audio Baseline (方案 01 · 活力眼科小姐姐)

- **Engine**: `edge` (`src/synthesize_voice.py`)
- **Voice**: `zh-CN-XiaoyiNeural`
- **Default Parameters**: `rate="+8%"`, `pitch="-4Hz"`, `-16 LUFS` loudness normalization, 24kHz mono WAV master.
- **BGM & SFX (`src/audio_mix_v2.py`)**: Warm felt-pad + glass-marimba + soft groove pulse (boosted ~2.2× so clearly audible and musical beneath speech, with smooth ducking `0.40`/`0.74`) plus bespoke procedural SFX (`impact`, `whoosh`, `ping`, `pop`, `chime`, `alert`, `shield`, `anchor`, `chain_1..5`).
- **Dynamic Rhythm Overrides**:
  - Fast causal chains / enumerations: progressively step `rate` from `+12%` up to `+20%` with tight `post_pause: 0.08`.
  - Memory anchor keywords (e.g., `"光学降噪"`, `"视功能"`): slow down (`rate: "-6%"`, `pitch: "-5Hz"`), paired with `sfx: "anchor"`.
- **Mandatory Pronunciation Audit**:
  Always listen to the synthesized voiceover before final rendering and use `tts_text` (separate from on-screen `subtitle`) to fix polyphones and acronyms:
  - `少长` / `别再长了` (meaning "grow") -> write `少涨` / `别再涨了` in `tts_text` so TTS reads `zhǎng` instead of `cháng`.
  - English trial acronyms (`CYPRESS`, `CATHAY`) -> use Title Case (`Cypress`, `Cathay`) in `tts_text`; `DOT 0.2` -> `D O T 零点二`; `"3.0"字样` -> `三点零字样`.
  - `ON/OFF` -> write `ON OFF` with spaces.
  - Always terminate every `tts_text` with Chinese punctuation (`，`, `。`, `？`, `！`) to prevent Edge TTS truncation.

## 2. Visual & Motion Design System (v5.0 Pixar / Apple Health 3D Art + 2.5D Cinema)

- **Canvas**: `1080 × 1920`, `30 fps`, deterministic `window.renderFrame(state)` inside `episodes/<ep_dir>/scene.html`.
- **Why 3D Art Stills + 2.5D Motion + Live Optical Canvas FX (Not Raw Procedural Three.js)**:
  - Hand-coded Three.js primitive geometries (`TorusGeometry`/`SphereGeometry`/`CylinderGeometry`) look crude/plastic for real eyeglasses, eyeballs, brains, and architectural scenes, and run slowly on CPU SwiftShader.
  - Instead, generate cohesive **9:16 Apple Health / Cinema 4D Octane / Pixar 3D hero artworks** per scene (`episodes/<ep_dir>/assets/*.jpg`) with spotless bright top/bottom negative spaces, animate them with smooth 2.5D Ken Burns camera push-ins / depth rack-focus / floating levitation, and composite **millimeter-calibrated live HTML5 Canvas optical beams, reticles, depth-shift ghost overlays, and flowing neural photons** on top!
  - **SwiftShader Canvas Rule**: Always call `fxCtx.clearRect(0, 0, 1080, 1920)` AND explicitly set `fxCanvas.style.opacity = hasCanvasFx ? "1" : "0"` on non-FX scenes so headless Chromium never displays stale canvas tiles.
- **Bright, Fresh, Energetic Sunlit Palettes Only**:
  - **NEVER** use dark/navy backgrounds and **NEVER** use dull muddy gray (`#ECEFEB`).
  - Use luminous sunlit sky-white (`#edf8fe`), pale mint (`#def3ee`), warm honey-oak & morning sunlight cream, paired with crisp editorial charcoal (`#0f172a`), Optical Sky Blue (`#0ea5e9` / `#0284c7`), Fresh Teal (`#0d9488`), and Alert Coral Rose (`#f43f5e` / `#e11d48`).
- **Zero-Occlusion & Tall-Phone Safe Zones**:
  - Left/Right margins strictly `>= 92px` (protects 20:9 tall phones from horizontal edge cropping).
  - Top Masthead at `top: 154px`; bottom caption & Teacher Kaka dock cleanly above Douyin bottom title (`Y <= 1615px`).
  - **NEVER** cover central 3D hero models with floating annotation cards; stage models asymmetrically (e.g., left-staged 3D sculpture + right-column frosted glass annotations with hairline leader dots) and measure exact pixel coordinates before placing any reticle or beam.
- **Teacher Kaka Choreography & Grounded Perspective**:
  - **Opening & Summary scenes**: Half-body lip-synced Teacher Kaka (`right: 86px; top: 1244px; width: 392px;` with soft bottom mask fade) + frosted editorial caption on the left.
  - **Full-Bleed Visual / Science Demo scenes**: Compact **192px Animated-Mouth Circular Teacher Kaka Dock** (`right: 92px; top: 1412px;`) using per-pose `POSE_MOUTH_RIG` offsets so her smiling face & 30fps lip-synced mouth stay pixel-locked dead-center across pose changes, accented with live audio-reactive equalizer bars (`卡卡讲解中`) and a soft voice-pulse halo.
  - **Full-Body Standing Outro**: NEVER float full-body Teacher Kaka in mid-air against a wall! Measure the background's actual floor/baseboard Y coordinate (e.g., `Y = 1450px` on `bg_minimalist_vision_loft.jpg`), plant her sneakers solidly on the wood floor plane (`Y ≈ 1560px`), render realistic **dual-layer floor contact + directional window-light cast shadows** beneath her shoes, and anchor standing sway at `transform-origin: 50% 98%`.
- **Fresh Per-Episode Backgrounds**: Never recycle old clinic backgrounds for new episodes; generate fresh sunlit architectural scenes matched to the episode's theme.
- **0.0px Mouth Rig**: Never manually overlay mouths in HTML/CSS; `src/web_render_v2.py` pre-bakes 0.0px offscreen-calibrated sprites (`682×1024`) from `POSE_MOUTH_RIG` into `.cache/kaka_sprites_v2/`.

## 3. Production & Quality Gate Commands

```bash
# Step 1: Synthesize voiceover & exact timeline
.venv/bin/python -m src.synthesize_voice \
  --script episodes/<ep_dir>/script.json \
  --out-dir audio/<prefix>

# Step 2: Render all key beats + contact sheet (MANDATORY FULL-RES VISUAL AUDIT)
.venv/bin/python -m src.web_render_v2 \
  --scene episodes/<ep_dir>/scene.html \
  --audio-dir audio/<prefix> \
  --prefix <prefix> \
  --out-dir output/<prefix> \
  --keyframes

# Step 3: Full 30fps 4-worker render + zero-NAL-error check + <20MB pure HTML export
.venv/bin/python -m src.web_render_v2 \
  --scene episodes/<ep_dir>/scene.html \
  --audio-dir audio/<prefix> \
  --prefix <prefix> \
  --out-dir output/<prefix> \
  --title "<Episode Page Title>" \
  --fps 30 \
  --workers 4
```

## 4. Delivery Rules & Mandatory Pre-Delivery Checklist

- **ZERO Large Files or Releases on GitHub**: NEVER upload `.mp4` or Pure HTML Releases to GitHub! GitHub (`wenjinliuu/kaka-vision-video-kit` `main`) stores ONLY lightweight source code, scripts, `scene.html`, and compressed episode hero JPGs.
- **Direct Google Drive Delivery via `rclone`**: Upload finished MP4 & Pure HTML directly to `gdrive:kaka-vision-video-kit/episodes_1080p_mp4/` (`rclone copyto ...`), and move superseded Drive versions to Trash via `google_workspace` `update_drive_file(trashed=true)`.
- **Checklist**:
  - [ ] Audio audited by ear: zero polyphone errors, zero truncated segments, smooth BGM ducking, tasteful SFX.
  - [ ] Every keyframe visually audited at full 1080×1920 resolution: zero text clipping, zero card/subject overlap, zero stale canvas artifacts, grounded outro stance.
  - [ ] `ffmpeg -v error -i <mp4> -f null -` passes with zero errors.
  - [ ] Pure video HTML exported under 20 MB for one-tap mobile/browser playback.
  - [ ] Clean code committed & pushed to GitHub `main` (ZERO Releases); finished `.mp4` + `.html` verified in Google Drive `episodes_1080p_mp4/`.

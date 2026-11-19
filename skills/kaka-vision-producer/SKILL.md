---
name: kaka-vision-producer
description: End-to-end production workflow for 卡卡老师《视光小课堂》 1080x1920 30fps editorial medical short videos (Kaka Vision Video Kit v2.0). Use when creating, updating, or auditing new episodes (EP05+).
---

# Kaka Vision Video Producer (v2.0)

Standard operating workflow for producing magazine-grade 1080×1920 @ 30fps vertical optometry science short videos in `kaka-vision-video-kit`.

## 1. Locked Voice Baseline (方案 01 · 活力眼科小姐姐)

- **Engine**: `edge` (`src/synthesize_voice.py`)
- **Voice**: `zh-CN-XiaoyiNeural`
- **Default Parameters**: `rate="+8%"`, `pitch="-4Hz"`, `-16 LUFS` loudness normalization, 24kHz mono WAV master.
- **Dynamic Rhythm Overrides**:
  - Fast causal chains / enumerations: progressively step `rate` from `+12%` up to `+20%` with tight `post_pause: 0.08`.
  - Memory anchor keywords (e.g., `"光学降噪"`): slow down (`rate: "-6%"`, `pitch: "-5Hz"`), paired with `sfx: "anchor"`.
- **Mandatory Pronunciation Audit**:
  Always listen to the synthesized voiceover before final rendering and use `tts_text` (separate from on-screen `subtitle`) to fix polyphones and acronyms:
  - `少长` (meaning "grow less") -> write `少涨` in `tts_text` so TTS reads `shǎo zhǎng` instead of `shǎo cháng`.
  - English trial acronyms (`CYPRESS`, `CATHAY`) -> use Title Case (`Cypress`, `Cathay`) in `tts_text` so TTS pronounces them as words rather than spelling individual letters.
  - `ON/OFF` -> write `ON OFF` with spaces.
  - Always terminate every `tts_text` with Chinese punctuation (`，`, `。`, `？`, `！`) to prevent Edge TTS truncation.

## 2. Visual & Motion Design System (v2.1 Bright Vibrant & Douyin-Safe)

- **Canvas**: `1080 × 1920`, `30 fps`, deterministic `window.renderFrame(state)` inside `episodes/<ep_dir>/scene.html`.
- **Mandatory Bright Palette Rule**: Always use **bright, airy porcelain/pastel-sky studio backgrounds** (NO dark/navy screens!) paired with vibrant same-hue gradients (`PALETTES`: 晴空蓝青 `#1A8CFF→#14C8B8`, 暖阳橙粉 `#FF8A34→#FF2E63`, 星夜紫 `#6366F1→#A855F7`, 翡翠薄荷 `#10B981→#34D399`, 琥珀金 `#F59E0B→#FBBF24`, 玫瑰珊瑚 `#E11D48→#FB7185`).
- **Strict Douyin / WeChat Channels Safe Area**:
  - Top chrome: `Y >= 126px` (clear of top navigation tabs).
  - Critical content, subtitles, circular PiP Teacher Kaka, and outro CTA cards: **MUST stay above `Y <= 1445px`** (`bottom >= 475px`) so Douyin's bottom-left username/title/hashtag overlay never covers faces or text!
  - PiP dock horizontal span: `X: 56..936px` (subtitle left + circular PiP Teacher Kaka on the right, staying `144px` clear of Douyin's right-edge Like/Comment/Share buttons!).
- **Dynamic Layout Modes**:
  1. `fullscreen_hook`: Bright pastel split-screen optical comparison cards with crisp foreground rays on `#fg-canvas` and vivid orange-pink `VS` orb.
  2. `pip_stage`: Spacious bright porcelain stage (`Y: 382..1245`) for optical lens macro, ray diagrams, or biological cascades, paired with the Douyin-safe subtitle-left + PiP-right dock (`Y: 1264..1440`).
  3. `classic_stage`: Custom-illustrated sunlit optometry lab background (`assets/backgrounds/bg_optics_research_lab.jpg`), half-body lecturing Teacher Kaka on lower-right, sleek speech card on lower-left (`Y: 1226..1375`), vibrant gradient journal cards above.
  4. `fullscreen_anchor`: Bright sunlit studio with expanding pastel blue-teal ripples, pure-white frosted crystal slab with monumental `blue_teal` gradient typography, and dual vibrant summary cards.
  5. `outro_wave`: Sunlit clinic background, full-body waving `kaka_02` with animated amber wave arcs, top brand badge (`关注卡卡老师`), and bottom interactive card strictly above `Y <= 1440px`.
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

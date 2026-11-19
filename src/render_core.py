#!/usr/bin/env python3
"""
Portable Full-HD 1080x1920 rendering core for Kaka Vision Video Kit.

Features:
- Real-scene pastel anime backgrounds (9:16) with atmospheric depth-of-field & airy top scrim
- 2x supersampled UI cards, gradient pills, vertical bars, vector check/cross & sparkle primitives
- 0.0px offscreen mouth compositing + silky zero-twitch breathing & gentle swaying
- Half-body lecturing framing (M01-M05) + unified full-body waving outro (M06)
- Procedural BGM + pop/chime SFX mixer with automatic voice ducking
- Atomic H.264 High Profile encoding, zero-NAL-error verification, and pure video-only HTML export
"""
import os
import math
import json
import base64
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
CLEAN_POSE_DIR = ASSETS_DIR / "kaka_teacher" / "clean_base"
MOUTH_DIR = ASSETS_DIR / "kaka_teacher" / "mouths"
BG_DIR = ASSETS_DIR / "backgrounds"
DEFAULT_OUT_DIR = REPO_ROOT / "output"
DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_font_path(env_key, candidates):
    env_path = os.environ.get(env_key)
    if env_path and os.path.exists(env_path):
        return env_path
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        f"No CJK font found. Install Noto Sans CJK or set {env_key}=/path/to/font.ttc"
    )


FONT_BOLD = _resolve_font_path(
    "KAKA_FONT_BOLD",
    [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "/usr/share/fonts/truetype/SimHei.ttf",
    ],
)
FONT_REG = _resolve_font_path(
    "KAKA_FONT_REG",
    [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        FONT_BOLD,
    ],
)


def get_font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


F_TAG = get_font(34, bold=True)
F_H1 = get_font(68, bold=True)
F_CARD_H2 = get_font(40, bold=True)
F_CARD_SUB = get_font(32, bold=True)
F_CARD_BODY = get_font(27, bold=True)
F_CARD_SM = get_font(24, bold=False)
F_CARD_XS = get_font(21, bold=True)
F_BUBBLE = get_font(42, bold=True)
F_OUTRO_H1 = get_font(78, bold=True)
F_OUTRO_BUB = get_font(44, bold=True)

PALETTES = {
    "blue_teal":    ((26, 140, 255), (20, 200, 184)),
    "orange_pink":  ((255, 138, 52), (255, 46, 99)),
    "purple_lav":   ((99, 102, 241), (168, 85, 247)),
    "emerald_mint": ((16, 185, 129), (52, 211, 153)),
    "amber_gold":   ((245, 158, 11), (251, 191, 36)),
    "rose_coral":   ((225, 29, 72),  (251, 113, 133)),
}

# Calibrated mouth anchor coordinates in 682x1024 pose space.
# Standard white-coat lecturing poses (recommended for everyday science videos):
POSE_MOUTH_RIG = {
    "kaka_01": {"mx": 348, "my": 268, "scale": 0.48, "rot": 0},
    "kaka_02": {"mx": 344, "my": 268, "scale": 0.48, "rot": 0},
    "kaka_03": {"mx": 370, "my": 290, "scale": 0.48, "rot": 0},
    "kaka_04": {"mx": 370, "my": 290, "scale": 0.48, "rot": 0},
    "kaka_05": {"mx": 376, "my": 288, "scale": 0.48, "rot": 0},
    "kaka_06": {"mx": 368, "my": 292, "scale": 0.48, "rot": 0},
    "kaka_07": {"mx": 389, "my": 280, "scale": 0.48, "rot": -7},
    "kaka_08": {"mx": 374, "my": 293, "scale": 0.42, "rot": 0},
    "kaka_09": {"mx": 378, "my": 288, "scale": 0.48, "rot": -4},
    "kaka_10": {"mx": 370, "my": 291, "scale": 0.48, "rot": 0},
    "kaka_11": {"mx": 354, "my": 268, "scale": 0.48, "rot": 0},
    "kaka_16": {"mx": 358, "my": 279, "scale": 0.42, "rot": 0},
}

POSES = {}
for fname in sorted(os.listdir(CLEAN_POSE_DIR)):
    if fname.endswith(".png") and fname.startswith("kaka_"):
        key = fname[:7]
        if key in POSE_MOUTH_RIG:
            POSES[key] = Image.open(CLEAN_POSE_DIR / fname).convert("RGBA")

MOUTHS = {
    i: Image.open(MOUTH_DIR / f"mouth_0{i}.png").convert("RGBA")
    for i in range(1, 7)
}


def prepare_real_scene_bg(bg_filename, top_veil=175, mid_veil=95, bot_veil=35, blur_px=1.2):
    """
    Loads a 9:16 real-scene pastel background from assets/backgrounds/,
    scales/crops to 1080x1920, applies subtle depth-of-field blur, and
    composites a smooth top-to-bottom translucent veil so headlines and cards pop.
    """
    p = Path(bg_filename)
    if not p.is_absolute():
        p = BG_DIR / bg_filename
    im = Image.open(p).convert("RGB")
    tw, th = 1080, 1920
    scale = max(tw / im.width, th / im.height)
    nw, nh = int(round(im.width * scale)), int(round(im.height * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    x0 = (nw - tw) // 2
    y0 = (nh - th) // 2
    im = im.crop((x0, y0, x0 + tw, y0 + th))
    if blur_px > 0:
        im = im.filter(ImageFilter.GaussianBlur(blur_px))
    im = im.convert("RGBA")

    y_arr = np.linspace(0.0, 1.0, th, dtype=np.float32)
    alpha_y = np.where(
        y_arr < 0.30,
        top_veil - (top_veil - mid_veil) * (y_arr / 0.30),
        mid_veil - (mid_veil - bot_veil) * ((y_arr - 0.30) / 0.70),
    )
    veil_rgba = np.zeros((th, tw, 4), dtype=np.uint8)
    veil_rgba[:, :, 0] = 250
    veil_rgba[:, :, 1] = 251
    veil_rgba[:, :, 2] = 254
    veil_rgba[:, :, 3] = np.clip(alpha_y[:, None], 0, 255).astype(np.uint8)
    im.alpha_composite(Image.fromarray(veil_rgba, "RGBA"))
    return im


def make_rounded_crop(im, box, target_size, radius=28):
    crop = im.crop(box).resize(target_size, Image.Resampling.LANCZOS)
    w2, h2 = target_size[0] * 2, target_size[1] * 2
    m2 = Image.new("L", (w2, h2), 0)
    ImageDraw.Draw(m2).rounded_rectangle([0, 0, w2 - 1, h2 - 1], radius=radius * 2, fill=255)
    crop.putalpha(m2.resize(target_size, Image.Resampling.LANCZOS))
    return crop


def draw_centered_text(draw, cx, y, text, font, fill):
    tw = draw.textlength(text, font=font)
    draw.text((cx - tw / 2, y), text, font=font, fill=fill)


def draw_ambient_sparkles(canvas, t_sec, count=8):
    """Subtle drifting sunlit bokeh circles across the scene."""
    draw = ImageDraw.Draw(canvas)
    for i in range(count):
        seed_x = ((i * 193 + 87) % 960) + 60
        base_y = ((i * 271 + 140) % 1050) + 340
        dx = math.sin(t_sec * 0.9 + i * 1.3) * 14
        dy = math.cos(t_sec * 1.1 + i * 0.8) * 10
        r = 5 + (i % 3) * 3
        a = int(55 + 45 * math.sin(t_sec * 2.2 + i))
        col = (255, 255, 255, a) if i % 2 == 0 else (253, 224, 71, int(a * 0.7))
        cx, cy = int(seed_x + dx), int(base_y + dy)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)


_GRAD_TEXT_CACHE = {}
def draw_gradient_text(canvas_rgba, text, x, y, font, palette_key="orange_pink"):
    c1, c2 = PALETTES.get(palette_key, PALETTES["orange_pink"])
    key = (text, id(font), c1, c2)
    if key not in _GRAD_TEXT_CACHE:
        dummy = ImageDraw.Draw(canvas_rgba)
        bbox = dummy.textbbox((0, 0), text, font=font)
        tw = max(1, bbox[2] - bbox[0])
        th = max(1, bbox[3] - bbox[1] + 16)
        mask = Image.new("L", (tw, th), 0)
        ImageDraw.Draw(mask).text((-bbox[0], -bbox[1]), text, font=font, fill=255)
        t = np.linspace(0, 1, tw, dtype=np.float32)[None, :, None]
        col1, col2 = np.array(c1, dtype=np.float32), np.array(c2, dtype=np.float32)
        grad_rgb = np.broadcast_to((1.0 - t) * col1 + t * col2, (th, tw, 3)).astype(np.uint8)
        grad_im = Image.fromarray(grad_rgb, "RGB").convert("RGBA")
        grad_im.putalpha(mask)
        _GRAD_TEXT_CACHE[key] = (grad_im, bbox[0], bbox[1], tw)
    grad_im, bx0, by0, tw = _GRAD_TEXT_CACHE[key]
    canvas_rgba.alpha_composite(grad_im, (int(x + bx0), int(y + by0)))
    return tw


_CARD_CACHE = {}
def draw_soft_card(canvas_rgba, x, y, w, h, radius=42, bg_rgba=(255, 255, 255, 242), border_rgba=(255, 255, 255, 255)):
    key = (int(w), int(h), int(radius), bg_rgba, border_rgba)
    if key not in _CARD_CACHE:
        pad = 36
        layer = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
        ldraw = ImageDraw.Draw(layer)
        ldraw.rounded_rectangle([pad, pad + 10, pad + w, pad + h + 10], radius=radius, fill=(15, 23, 42, 26))
        layer = layer.filter(ImageFilter.GaussianBlur(15))
        w2, h2 = w * 2, h * 2
        card_hi = Image.new("RGBA", (w2, h2), (0, 0, 0, 0))
        ImageDraw.Draw(card_hi).rounded_rectangle(
            [0, 0, w2 - 1, h2 - 1],
            radius=radius * 2,
            fill=bg_rgba,
            outline=border_rgba,
            width=4,
        )
        card_lo = card_hi.resize((w, h), Image.Resampling.LANCZOS)
        layer.alpha_composite(card_lo, (pad, pad))
        _CARD_CACHE[key] = (layer, pad)
    layer, pad = _CARD_CACHE[key]
    canvas_rgba.alpha_composite(layer, (int(x - pad), int(y - pad)))


_PILL_CACHE = {}
def draw_grad_pill(canvas_rgba, x, y, w, h, radius, palette_key="blue_teal"):
    c1, c2 = PALETTES.get(palette_key, PALETTES["blue_teal"])
    w, h = max(4, int(w)), max(4, int(h))
    key = (w, h, int(radius), c1, c2)
    if key not in _PILL_CACHE:
        t = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
        col1, col2 = np.array(c1, dtype=np.float32), np.array(c2, dtype=np.float32)
        grad_rgb = np.broadcast_to((1.0 - t) * col1 + t * col2, (h, w, 3)).astype(np.uint8)
        grad_im = Image.fromarray(grad_rgb, "RGB").convert("RGBA")
        m2 = Image.new("L", (w * 2, h * 2), 0)
        ImageDraw.Draw(m2).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=radius * 2, fill=255)
        grad_im.putalpha(m2.resize((w, h), Image.Resampling.LANCZOS))
        _PILL_CACHE[key] = grad_im
    canvas_rgba.alpha_composite(_PILL_CACHE[key], (int(x), int(y)))


def draw_vgrad_bar(canvas_rgba, x, y, w, h, radius, palette_key="orange_pink"):
    c_top, c_bot = PALETTES.get(palette_key, PALETTES["orange_pink"])
    w, h = max(4, int(w)), max(4, int(h))
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    col1, col2 = np.array(c_top, dtype=np.float32), np.array(c_bot, dtype=np.float32)
    grad_rgb = np.broadcast_to((1.0 - t) * col1 + t * col2, (h, w, 3)).astype(np.uint8)
    grad_im = Image.fromarray(grad_rgb, "RGB").convert("RGBA")
    m2 = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(m2).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=radius * 2, fill=255)
    grad_im.putalpha(m2.resize((w, h), Image.Resampling.LANCZOS))
    canvas_rgba.alpha_composite(grad_im, (int(x), int(y)))


def draw_check_or_cross(canvas, cx, cy, r, is_check=True, pal="emerald_mint"):
    """Vector checkmark or cross badge (avoids missing Unicode glyph boxes in CJK fonts)."""
    draw_grad_pill(canvas, cx - r, cy - r, r * 2, r * 2, r, pal)
    d = ImageDraw.Draw(canvas)
    w = max(4, int(r * 0.22))
    if is_check:
        pts = [(cx - r * 0.44, cy + r * 0.02), (cx - r * 0.12, cy + r * 0.34), (cx + r * 0.46, cy - r * 0.30)]
        d.line(pts, fill=(255, 255, 255, 255), width=w, joint="curve")
    else:
        off = r * 0.36
        d.line([(cx - off, cy - off), (cx + off, cy + off)], fill=(255, 255, 255, 255), width=w)
        d.line([(cx - off, cy + off), (cx + off, cy - off)], fill=(255, 255, 255, 255), width=w)


def draw_sparkle(draw, cx, cy, r, fill=(251, 191, 36, 255)):
    pts = [
        (cx, cy - r), (cx + r * 0.28, cy - r * 0.28),
        (cx + r, cy), (cx + r * 0.28, cy + r * 0.28),
        (cx, cy + r), (cx - r * 0.28, cy + r * 0.28),
        (cx - r, cy), (cx - r * 0.28, cy - r * 0.28),
    ]
    draw.polygon(pts, fill=fill)


def render_top_header(canvas, line1, line2_pre, line2_grad, palette_key="orange_pink", tag_text="视光小课堂"):
    draw_soft_card(canvas, 84, 134, 212, 52, radius=26, bg_rgba=(255, 255, 255, 225))
    draw = ImageDraw.Draw(canvas)
    draw.text((104, 141), tag_text, font=F_TAG, fill=(90, 102, 118, 255))
    draw.text((84, 200), line1, font=F_H1, fill=(26, 29, 36, 255))
    draw.text((84, 286), line2_pre, font=F_H1, fill=(26, 29, 36, 255))
    pre_w = draw.textlength(line2_pre, font=F_H1) if line2_pre else 0
    draw_gradient_text(canvas, line2_grad, 84 + pre_w + 4, 286, F_H1, palette_key)


def render_speech_bubble(canvas, segments, hl_palette="orange_pink", ease_p=1.0, center_mode=False, y_pos=1292):
    draw = ImageDraw.Draw(canvas)
    font = F_OUTRO_BUB if center_mode else F_BUBBLE
    total_w = sum(draw.textlength(txt, font=font) for txt, _ in segments)
    pad_x = 46 if center_mode else 40
    bh = 104 if center_mode else 94
    bw = int(total_w + pad_x * 2)

    if center_mode:
        bx = (1080 - bw) // 2
        by = y_pos
    else:
        bx = max(76, min(140, 525 - bw))
        by = int(y_pos + (1.0 - ease_p) * 14)

    draw_soft_card(canvas, bx, by, bw, bh, radius=30, bg_rgba=(255, 255, 255, 250))
    draw = ImageDraw.Draw(canvas)
    if not center_mode:
        tx = bx + bw - 6
        ty = by + bh // 2 + 4
        draw.polygon([(tx, ty - 12), (tx + 22, ty + 2), (tx, ty + 14)], fill=(255, 255, 255, 250))

    hl_rgb = PALETTES.get(hl_palette, PALETTES["orange_pink"])[0]
    kw_color = (245, 130, 32, 255) if hl_palette in ("orange_pink", "amber_gold") else (*hl_rgb, 255)

    cx = bx + pad_x
    cy = by + (bh - (52 if center_mode else 48)) // 2 - 4
    for txt, is_hl in segments:
        color = kw_color if is_hl else (26, 29, 36, 255)
        draw.text((cx, cy), txt, font=font, fill=color)
        cx += draw.textlength(txt, font=font)


_CHAR_CACHE = {}
def render_kaka_rig_halfbody(canvas, pose_id, mouth_id, t_sec, is_ending_wave=False):
    target_w = 570 if is_ending_wave else 620
    target_h = int((1024 / 682) * target_w)
    cache_key = (pose_id, mouth_id, target_w)
    if cache_key not in _CHAR_CACHE:
        base_im = POSES.get(pose_id, POSES["kaka_01"]).copy()
        rig = POSE_MOUTH_RIG.get(pose_id, POSE_MOUTH_RIG["kaka_01"])
        m_im = MOUTHS[mouth_id]
        mw = max(2, int(m_im.width * rig["scale"]))
        mh = max(2, int(m_im.height * rig["scale"]))
        m_resized = m_im.resize((mw, mh), Image.Resampling.LANCZOS)
        if rig["rot"] != 0:
            m_resized = m_resized.rotate(-rig["rot"], expand=True, resample=Image.Resampling.BICUBIC)
        px = int(rig["mx"] - m_resized.width / 2)
        py = int(rig["my"] - m_resized.height / 2)
        base_im.alpha_composite(m_resized, (px, py))
        _CHAR_CACHE[cache_key] = base_im.resize((target_w, target_h), Image.Resampling.LANCZOS)

    if is_ending_wave:
        char_scaled = _CHAR_CACHE[cache_key].copy()
        cdraw = ImageDraw.Draw(char_scaled)
        w_alpha = int((0.45 + 0.45 * abs(math.sin(t_sec * 4.5))) * 255)
        hx, hy = int(target_w * 0.64), int(target_h * 0.31)
        cdraw.arc([hx - 74, hy - 74, hx + 74, hy + 74], start=-28, end=32, fill=(245, 158, 11, w_alpha), width=6)
        cdraw.arc([hx - 92, hy - 92, hx + 92, hy + 92], start=-28, end=32, fill=(251, 191, 36, int(w_alpha * 0.75)), width=5)

        sway_deg = math.sin(t_sec * 2.2) * 0.95
        float_y = math.sin(t_sec * 2.2) * 3.0
        char_rot = char_scaled.rotate(-sway_deg, expand=False, center=(target_w // 2, int(target_h * 0.85)), resample=Image.Resampling.BICUBIC)
        bx = (1080 - target_w) // 2
        by = int(495 + float_y)
        canvas.alpha_composite(char_rot, (bx, by))
    else:
        char_scaled = _CHAR_CACHE[cache_key]
        sway_q = round(math.sin(t_sec * 1.5) * 0.42, 2)
        float_y = math.sin(t_sec * 1.8) * 2.5
        rot_key = (cache_key, sway_q)
        if rot_key not in _CHAR_CACHE:
            _CHAR_CACHE[rot_key] = char_scaled.rotate(-sway_q, expand=False, center=(target_w // 2, int(target_h * 0.65)), resample=Image.Resampling.BICUBIC)
        char_rot = _CHAR_CACHE[rot_key]
        bx = 468
        by = int(1228 + float_y)
        canvas.alpha_composite(char_rot, (bx, by))


def build_bgm_and_sfx_mix(vo_wav, sr, timeline, chime_ids=("c03", "c05", "c07", "c09", "c11")):
    n_samples = len(vo_wav)
    bpm = 112.0
    eighth_sec = (60.0 / bpm) / 2.0
    bgm = np.zeros(n_samples, dtype=np.float32)

    chords = [
        [261.63, 329.63, 392.00, 523.25],
        [196.00, 246.94, 293.66, 392.00],
        [220.00, 261.63, 329.63, 440.00],
        [174.61, 220.00, 261.63, 349.23],
    ]
    pattern = [0, 1, 2, 3, 2, 1, 3, 2]

    total_eighths = int((n_samples / sr) / eighth_sec) + 2
    for idx in range(total_eighths):
        onset_i = int(idx * eighth_sec * sr)
        if onset_i >= n_samples:
            break
        chord = chords[(idx // 8) % len(chords)]
        freq = chord[pattern[idx % len(pattern)]]
        dur_i = min(int(sr * 0.42), n_samples - onset_i)
        nt = np.arange(dur_i, dtype=np.float32) / sr
        env = np.exp(-nt * 9.5) * (1.0 - np.exp(-nt * 180.0))
        note = (np.sin(2 * np.pi * freq * nt) + 0.25 * np.sin(2 * np.pi * freq * 2 * nt) * np.exp(-nt * 18.0)) * env
        bgm[onset_i:onset_i + dur_i] += note * 0.14

    win = int(sr * 0.08)
    vo_env = np.convolve(np.abs(vo_wav), np.ones(win, dtype=np.float32) / win, mode="same")
    duck_gain = np.where(vo_env > 0.012, 0.22, 0.42).astype(np.float32)
    smooth_k = np.ones(int(sr * 0.18), dtype=np.float32) / int(sr * 0.18)
    duck_gain = np.convolve(duck_gain, smooth_k, mode="same")
    bgm *= duck_gain

    sfx = np.zeros(n_samples, dtype=np.float32)

    def add_pop(time_s, f_start=520.0, f_end=860.0, amp=0.075):
        i0 = int(time_s * sr)
        n = min(int(sr * 0.065), n_samples - i0)
        if i0 >= 0 and n > 0:
            nt = np.arange(n, dtype=np.float32) / sr
            f_inst = np.linspace(f_start, f_end, n)
            env = np.sin(np.pi * nt / 0.065) * np.exp(-nt * 25.0)
            sfx[i0:i0 + n] += np.sin(2 * np.pi * f_inst * nt) * env * amp

    def add_chime(time_s):
        for offset, freq in [(0.0, 783.99), (0.08, 1046.50)]:
            i0 = int((time_s + offset) * sr)
            n = min(int(sr * 0.26), n_samples - i0)
            if i0 >= 0 and n > 0:
                nt = np.arange(n, dtype=np.float32) / sr
                env = np.exp(-nt * 12.0)
                sfx[i0:i0 + n] += np.sin(2 * np.pi * freq * nt) * env * 0.075

    for cl in timeline["clauses"]:
        add_pop(cl["start"])
        if cl["id"] in chime_ids:
            add_chime(cl["start"])

    fade_out_n = int(sr * 0.45)
    if n_samples > fade_out_n:
        bgm[-fade_out_n:] *= np.linspace(1.0, 0.0, fade_out_n)

    return np.clip(vo_wav + bgm + sfx, -0.98, 0.98)


def compute_mouth_sequence(vo_wav, sr, total_frames, fps=25):
    raw_energies = np.zeros(total_frames, dtype=np.float32)
    for f_idx in range(total_frames):
        t_s = f_idx / fps
        i0 = max(0, int((t_s - 0.04) * sr))
        i1 = min(len(vo_wav), int((t_s + 0.06) * sr))
        w = vo_wav[i0:i1]
        rms = float(np.sqrt(np.mean(w ** 2) + 1e-9)) if len(w) > 0 else 0.0
        raw_energies[f_idx] = min(1.0, rms / 0.21)

    smooth_energies = np.convolve(raw_energies, np.array([0.2, 0.6, 0.2], dtype=np.float32), mode="same")
    mouth_seq = []
    curr_mouth = 1
    hold_count = 0
    for f_idx in range(total_frames):
        e = float(smooth_energies[f_idx])
        if e < 0.07:
            target_m = 1
        elif e < 0.22:
            target_m = 6
        elif e < 0.45:
            target_m = 2
        elif e < 0.68:
            target_m = 3
        elif e < 0.84:
            target_m = 5 if (f_idx // 5) % 2 == 0 else 3
        else:
            target_m = 4

        if target_m == 1:
            curr_mouth = 1
            hold_count = 0
        elif hold_count >= 3 or curr_mouth == 1:
            curr_mouth = target_m
            hold_count = 1
        else:
            hold_count += 1
        mouth_seq.append(curr_mouth)
    return mouth_seq, smooth_energies


def export_pure_video_html(mp4_path, html_path, page_title, max_embed_mb=13.0):
    """Packages a 1080x1920 MP4 into a standalone pure <video>-only HTML file (<20MB display friendly)."""
    mp4_path = Path(mp4_path)
    html_path = Path(html_path)
    embed_mp4 = html_path.with_suffix(".embed_tmp.mp4")

    # Dynamically keep embedded MP4 compact so Base64 HTML stays comfortably below 20MB
    crf = "22"
    audio_br = "96k"
    extra_rate = []
    size_mb = mp4_path.stat().st_size / (1024 * 1024)
    if size_mb > 34.0:
        crf = "24"
        audio_br = "80k"
        extra_rate = ["-maxrate", "680k", "-bufsize", "1360k"]
    elif size_mb > max_embed_mb:
        crf = "23"
        extra_rate = ["-maxrate", "1050k", "-bufsize", "2100k"]

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(mp4_path),
            "-c:v", "libx264", "-preset", "slow", "-tune", "animation",
            "-profile:v", "high", "-level", "4.2", "-crf", crf, *extra_rate,
            "-g", "50", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", audio_br, "-ac", "1",
            "-movflags", "+faststart", str(embed_mp4),
        ],
        check=True,
    )
    b64 = base64.b64encode(embed_mp4.read_bytes()).decode("ascii")
    embed_mp4.unlink(missing_ok=True)

    pure_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>{page_title}</title>
<style>
  html, body {{
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    background: #000000;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }}
  video {{
    width: 100%;
    height: 100%;
    max-height: 100vh;
    object-fit: contain;
    display: block;
    background: #000000;
  }}
</style>
</head>
<body>
<video id="v" controls playsinline preload="auto"></video>
<script>
  const B64_MP4 = "{b64}";
  const raw = atob(B64_MP4);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  const blobUrl = URL.createObjectURL(new Blob([bytes], {{ type: "video/mp4" }}));
  document.getElementById("v").src = blobUrl;
</script>
</body>
</html>
"""
    html_path.write_text(pure_html, encoding="utf-8")


def render_episode(
    audio_dir,
    prefix,
    scene_headers,
    get_bg_fn,
    render_scene_fn,
    out_dir=DEFAULT_OUT_DIR,
    page_title="卡卡老师《视光小课堂》(1080P)",
    chime_ids=("c03", "c05", "c07", "c09", "c11"),
    fps=25,
    export_html=True,
    tag_text="视光小课堂",
):
    audio_dir = Path(audio_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    vo_path = audio_dir / f"{prefix}_vo_master.wav"
    meta_path = audio_dir / f"{prefix}_timeline.json"
    timeline = json.loads(meta_path.read_text(encoding="utf-8"))

    vo_wav, sr = sf.read(str(vo_path))
    vo_wav = np.asarray(vo_wav, dtype=np.float32)

    mixed_audio = build_bgm_and_sfx_mix(vo_wav, sr, timeline, chime_ids=chime_ids)
    mixed_wav_path = audio_dir / f"{prefix}_final_mix.wav"
    sf.write(str(mixed_wav_path), mixed_audio, sr)

    total_sec = timeline["total_duration"]
    total_frames = int(total_sec * fps)
    mouth_seq, _ = compute_mouth_sequence(vo_wav, sr, total_frames, fps=fps)

    out_mp4 = out_dir / f"{prefix}_master.mp4"
    tmp_mp4 = out_dir / f"{prefix}_master.tmp.mp4"

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", "1080x1920", "-pix_fmt", "rgba", "-r", str(fps),
        "-i", "-",
        "-i", str(mixed_wav_path),
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.2",
        "-preset", "fast", "-tune", "animation",
        "-crf", "18", "-g", "50", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
        "-movflags", "+faststart", "-shortest",
        str(tmp_mp4),
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    clauses = timeline["clauses"]
    scenes = timeline["scenes"]

    for f_idx in range(total_frames):
        t_sec = f_idx / fps
        active_cl = clauses[0]
        for cl in clauses:
            if cl["start"] <= t_sec <= cl["end"] + 0.45:
                active_cl = cl
            if cl["start"] <= t_sec <= cl["end"]:
                active_cl = cl
                break

        sc_code = active_cl["scene"]
        sc_info = scenes[sc_code]
        sc_prog = max(0.0, min(1.0, (t_sec - sc_info["start"]) / max(0.1, sc_info["end"] - sc_info["start"])))
        cl_prog = max(0.0, min(1.0, (t_sec - active_cl["start"]) / max(0.1, active_cl["end"] - active_cl["start"])))

        canvas = get_bg_fn(sc_code).copy()
        draw_ambient_sparkles(canvas, t_sec, count=8)

        mouth_id = mouth_seq[f_idx]
        if sc_code == "M06":
            draw = ImageDraw.Draw(canvas)
            bub_txt = "".join(t for t, _ in active_cl.get("bubble", []))
            top_txt = "关注卡卡老师" if (active_cl["id"] == "c11" or "关注" in bub_txt) else "带你看懂孩子的眼睛"
            tw = draw.textlength(top_txt, font=F_OUTRO_H1)
            draw_soft_card(canvas, int((1080 - tw) / 2) - 36, 248, int(tw) + 72, 114, radius=36, bg_rgba=(255, 255, 255, 228))
            draw = ImageDraw.Draw(canvas)
            draw.text(((1080 - tw) / 2, 265), top_txt, font=F_OUTRO_H1, fill=(26, 29, 36, 255))

            render_kaka_rig_halfbody(canvas, "kaka_02", mouth_id, t_sec, is_ending_wave=True)
            render_speech_bubble(canvas, active_cl["bubble"], hl_palette="orange_pink", ease_p=1.0, center_mode=True, y_pos=1445)
        else:
            h1, h2_pre, h2_grad, pal_key = scene_headers[sc_code]
            render_top_header(canvas, h1, h2_pre, h2_grad, pal_key, tag_text=tag_text)
            render_scene_fn(canvas, sc_code, sc_prog, t_sec, active_cl["id"])

            pose_id = active_cl["pose"]
            if pose_id == "kaka_01" and (t_sec % 3.8) > 3.62:
                pose_id = "kaka_11"

            ease_cl = 1.0 - (1.0 - min(1.0, cl_prog * 4.0)) ** 3
            render_kaka_rig_halfbody(canvas, pose_id, mouth_id, t_sec, is_ending_wave=False)
            render_speech_bubble(
                canvas,
                active_cl["bubble"],
                hl_palette=active_cl.get("hl", "orange_pink"),
                ease_p=ease_cl,
                center_mode=False,
                y_pos=1292,
            )

        proc.stdin.write(canvas.tobytes())
        if f_idx % 200 == 0 or f_idx == total_frames - 1:
            print(f"  [{prefix}] frame {f_idx + 1}/{total_frames} ({t_sec:.1f}s / {total_sec:.1f}s)", flush=True)

    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"ffmpeg exited with code {ret}")
    os.replace(tmp_mp4, out_mp4)

    # Full zero-NAL-error decode verification
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(out_mp4), "-f", "null", "-"], check=True)
    print(f"[{prefix}] Verified ZERO H.264 decode errors -> {out_mp4}")

    if export_html:
        pure_html = out_dir / f"{prefix}_pure_video.html"
        export_pure_video_html(out_mp4, pure_html, page_title)
        print(f"[{prefix}] Exported pure video HTML -> {pure_html}")
    return out_mp4

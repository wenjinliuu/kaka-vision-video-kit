#!/usr/bin/env python3
"""
Starter episode renderer template for Kaka Vision Video Kit.

Usage:
  1) Preview static 2-scene check image (no audio required):
       python -m src.render_episode_template --preview output/template_preview.png

  2) Render full 1080x1920 MP4 + pure HTML video after running synthesize_voice.py:
       python -m src.render_episode_template --audio-dir audio/sample --prefix sample
"""
import argparse
import math
from PIL import Image, ImageDraw
from src.render_core import (
    F_CARD_H2, F_CARD_SUB, F_CARD_BODY, F_OUTRO_H1,
    prepare_real_scene_bg, draw_centered_text, draw_ambient_sparkles,
    draw_soft_card, draw_grad_pill, draw_vgrad_bar, draw_check_or_cross,
    draw_sparkle, render_top_header, render_kaka_rig_halfbody,
    render_speech_bubble, render_episode,
)

BG_CLINIC = prepare_real_scene_bg("bg_clinic_room.jpg", top_veil=172, mid_veil=92, bot_veil=32)
BG_STUDY  = prepare_real_scene_bg("bg_children_room.png", top_veil=178, mid_veil=96, bot_veil=38)


def get_bg(sc_code):
    return BG_STUDY if sc_code in ("M02",) else BG_CLINIC


SCENE_HEADERS = {
    "M01": ("孩子近视防控", "科学护眼", "最重要！", "blue_teal"),
    "M02": ("每天户外2小时", "自然阳光", "最省钱", "emerald_mint"),
}


def render_scene_cards(canvas, sc_code, sc_prog, t_sec, active_clause_id):
    ease_p = 1.0 - (1.0 - min(1.0, sc_prog * 3.0)) ** 3

    if sc_code == "M01":
        y_off = int((1.0 - ease_p) * 24)
        draw_soft_card(canvas, 84, 392 + y_off, 442, 560, radius=42)
        draw_soft_card(canvas, 554, 392 + y_off, 442, 560, radius=42)

        draw_check_or_cross(canvas, 305, 560 + y_off, 68, is_check=True, pal="emerald_mint")
        draw_check_or_cross(canvas, 775, 560 + y_off, 68, is_check=False, pal="rose_coral")

        draw_grad_pill(canvas, 130, 710 + y_off, 350, 72, 36, "emerald_mint")
        draw_grad_pill(canvas, 600, 710 + y_off, 350, 72, 36, "orange_pink")
        draw = ImageDraw.Draw(canvas)
        draw_centered_text(draw, 305, 727 + y_off, "科学验配 · 定期复查", F_CARD_SUB, (255, 255, 255, 255))
        draw_centered_text(draw, 305, 818 + y_off, "建立屈光发育档案", F_CARD_BODY, (15, 118, 110, 255))
        draw_centered_text(draw, 775, 727 + y_off, "盲目跟风 · 迷信偏方", F_CARD_SUB, (255, 255, 255, 255))
        draw_centered_text(draw, 775, 818 + y_off, "延误最佳防控时机", F_CARD_BODY, (190, 18, 60, 255))

        draw_grad_pill(canvas, 84, 990 + y_off, 912, 102, 51, "blue_teal")
        draw = ImageDraw.Draw(canvas)
        draw_centered_text(draw, 540, 1020 + y_off, "替换此处为你的科普图表、插画或物理动效", F_CARD_SUB, (255, 255, 255, 255))
        draw_sparkle(draw, 128, 1041 + y_off, 14, fill=(253, 224, 71, 240))
        draw_sparkle(draw, 952, 1041 + y_off, 14, fill=(253, 224, 71, 240))

    elif sc_code == "M02":
        draw_soft_card(canvas, 84, 392, 912, 680, radius=42)
        draw = ImageDraw.Draw(canvas)
        draw.text((132, 430), "2x 超采样动态柱状图示例", font=F_CARD_H2, fill=(30, 41, 59, 255))
        draw.line([(150, 910), (930, 910)], fill=(203, 213, 225, 255), width=4)

        h1 = int(160 * ease_p)
        h2 = int(310 * ease_p + math.sin(t_sec * 3.0) * 6)
        draw_vgrad_bar(canvas, 240, 910 - h1, 180, h1, 28, "amber_gold")
        draw_vgrad_bar(canvas, 640, 910 - h2, 180, h2, 28, "emerald_mint")
        draw = ImageDraw.Draw(canvas)
        draw_centered_text(draw, 330, 932, "缺乏户外活动", F_CARD_BODY, (180, 83, 9, 255))
        draw_centered_text(draw, 730, 932, "每天户外 2 小时+", F_CARD_BODY, (5, 150, 105, 255))


def render_preview(out_png):
    sheet = Image.new("RGB", (540 * 2, 960), (240, 240, 240))
    # Left: M01 lecturing frame
    c1 = get_bg("M01").copy()
    draw_ambient_sparkles(c1, 2.0)
    render_top_header(c1, *SCENE_HEADERS["M01"])
    render_scene_cards(c1, "M01", 0.8, 2.0, "c01")
    render_kaka_rig_halfbody(c1, "kaka_04", 3, 2.0, is_ending_wave=False)
    render_speech_bubble(c1, [["科学护眼", False], ["从今天开始", True]], hl_palette="blue_teal")
    sheet.paste(c1.convert("RGB").resize((540, 960), Image.Resampling.LANCZOS), (0, 0))

    # Right: M06 unified waving outro
    c2 = get_bg("M06").copy()
    draw_ambient_sparkles(c2, 5.0)
    draw = ImageDraw.Draw(c2)
    tw = draw.textlength("关注卡卡老师", font=F_OUTRO_H1)
    draw_soft_card(c2, int((1080 - tw) / 2) - 36, 248, int(tw) + 72, 114, radius=36, bg_rgba=(255, 255, 255, 228))
    draw = ImageDraw.Draw(c2)
    draw.text(((1080 - tw) / 2, 265), "关注卡卡老师", font=F_OUTRO_H1, fill=(26, 29, 36, 255))
    render_kaka_rig_halfbody(c2, "kaka_02", 3, 5.0, is_ending_wave=True)
    render_speech_bubble(c2, [["关注", False], ["卡卡老师", True]], hl_palette="orange_pink", center_mode=True, y_pos=1445)
    sheet.paste(c2.convert("RGB").resize((540, 960), Image.Resampling.LANCZOS), (540, 0))

    sheet.save(out_png)
    print(f"Saved preview sheet -> {out_png}")


def main():
    parser = argparse.ArgumentParser(description="Render an episode using Kaka Vision Video Kit.")
    parser.add_argument("--preview", help="Generate a 2-scene static preview PNG without audio")
    parser.add_argument("--audio-dir", default="audio/sample", help="Directory containing <prefix>_vo_master.wav & <prefix>_timeline.json")
    parser.add_argument("--prefix", default="sample", help="Episode filename prefix")
    parser.add_argument("--out-dir", default="output", help="Output directory")
    args = parser.parse_args()

    if args.preview:
        render_preview(args.preview)
        return

    render_episode(
        audio_dir=args.audio_dir,
        prefix=args.prefix,
        scene_headers=SCENE_HEADERS,
        get_bg_fn=get_bg,
        render_scene_fn=render_scene_cards,
        out_dir=args.out_dir,
        page_title="卡卡老师《视光小课堂》模板示例 (1080P)",
    )


if __name__ == "__main__":
    main()

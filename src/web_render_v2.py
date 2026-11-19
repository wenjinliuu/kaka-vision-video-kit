#!/usr/bin/env python3
"""
Kaka Vision Video Kit v2.0 — Deterministic High-End Web/SVG/Canvas Renderer (1080x1920 @ 30fps).

Features:
- Pre-bakes 0.0px offscreen-calibrated Teacher Kaka pose+mouth sprites from assets/
- Drives any episode `scene.html` via deterministic `window.renderFrame(state)`
- Fast `--keyframes` inspection mode (renders key beats + 4x3 contact sheet in seconds)
- Multi-process parallel Chromium rendering across CPU cores, piping straight into FFmpeg
- Studio audio mix (`audio_mix_v2`), atomic MP4 write, zero-NAL-error check, pure HTML export
"""
import argparse
import base64
import json
import math
import multiprocessing as mp
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image

from src.audio_mix_v2 import build_editorial_mix, compute_mouth_sequence
from src.render_core import CLEAN_POSE_DIR, MOUTH_DIR, POSE_MOUTH_RIG, export_pure_video_html

REPO_ROOT = Path(__file__).resolve().parent.parent
SPRITE_CACHE_DIR = REPO_ROOT / ".cache" / "kaka_sprites_v2"


def prebake_kaka_sprites(poses_needed):
    """
    Pre-composites 0.0px calibrated mouth sprites onto each required Teacher Kaka pose
    in original 682x1024 coordinates and caches transparent PNGs in .cache/kaka_sprites_v2/.
    """
    SPRITE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    needed = sorted(set(poses_needed) | {"kaka_01", "kaka_11", "kaka_02"})

    pose_files = {}
    for fname in sorted(os.listdir(CLEAN_POSE_DIR)):
        if fname.endswith(".png") and fname.startswith("kaka_"):
            pose_files[fname[:7]] = CLEAN_POSE_DIR / fname

    mouths = {
        i: Image.open(MOUTH_DIR / f"mouth_0{i}.png").convert("RGBA")
        for i in range(1, 7)
    }

    sprite_map = {}
    for pose_id in needed:
        if pose_id not in pose_files or pose_id not in POSE_MOUTH_RIG:
            continue
        rig = POSE_MOUTH_RIG[pose_id]
        base_orig = None
        sprite_map[pose_id] = {}
        for m_id in range(1, 7):
            out_p = SPRITE_CACHE_DIR / f"{pose_id}_m{m_id}.png"
            if not out_p.exists():
                if base_orig is None:
                    base_orig = Image.open(pose_files[pose_id]).convert("RGBA")
                im = base_orig.copy()
                m_im = mouths[m_id]
                mw = max(2, int(m_im.width * rig["scale"]))
                mh = max(2, int(m_im.height * rig["scale"]))
                m_res = m_im.resize((mw, mh), Image.Resampling.LANCZOS)
                if rig["rot"] != 0:
                    m_res = m_res.rotate(-rig["rot"], expand=True, resample=Image.Resampling.BICUBIC)
                px = int(rig["mx"] - m_res.width / 2)
                py = int(rig["my"] - m_res.height / 2)
                im.alpha_composite(m_res, (px, py))
                im.save(out_p)
            sprite_map[pose_id][str(m_id)] = out_p.resolve().as_uri()
    return sprite_map


def compute_energy_envelope(vo_wav, sr, total_frames, fps=30):
    vo_wav = np.asarray(vo_wav, dtype=np.float32)
    if vo_wav.ndim > 1:
        vo_wav = vo_wav.mean(axis=1)
    env = np.zeros(total_frames, dtype=np.float32)
    for f_idx in range(total_frames):
        t_s = f_idx / fps
        i0 = max(0, int((t_s - 0.03) * sr))
        i1 = min(len(vo_wav), int((t_s + 0.05) * sr))
        w = vo_wav[i0:i1]
        rms = float(np.sqrt(np.mean(w ** 2) + 1e-9)) if len(w) > 0 else 0.0
        env[f_idx] = min(1.0, rms / 0.20)
    env = np.convolve(env, np.array([0.25, 0.5, 0.25], dtype=np.float32), mode="same")
    return [round(float(x), 3) for x in env]


def build_frame_state(f_idx, fps, timeline, mouth_seq, energy_seq):
    t_sec = f_idx / fps
    segments = timeline["segments"]
    active_seg = segments[0]
    active_idx = 0
    for idx, seg in enumerate(segments):
        if seg["start"] <= t_sec <= seg["end_with_pause"]:
            active_seg = seg
            active_idx = idx
            break
        if t_sec >= seg["start"]:
            active_seg = seg
            active_idx = idx

    sc_code = active_seg["scene"]
    sc_info = timeline["scenes"][sc_code]
    sc_dur = max(0.05, sc_info["end"] - sc_info["start"])
    sc_prog = max(0.0, min(1.0, (t_sec - sc_info["start"]) / sc_dur))

    seg_dur = max(0.05, active_seg["end"] - active_seg["start"])
    seg_prog = max(0.0, min(1.0, (t_sec - active_seg["start"]) / seg_dur))
    beat_elapsed = max(0.0, t_sec - active_seg["start"])

    pose_id = active_seg.get("pose", "kaka_01")
    if pose_id == "kaka_01" and (t_sec % 3.8) > 3.62:
        pose_id = "kaka_11"

    return {
        "frame": f_idx,
        "fps": fps,
        "t": round(t_sec, 4),
        "totalDuration": timeline["total_duration"],
        "scene": sc_code,
        "sceneStart": sc_info["start"],
        "sceneEnd": sc_info["end"],
        "sceneProg": round(sc_prog, 5),
        "sceneElapsed": round(max(0.0, t_sec - sc_info["start"]), 4),
        "segIndex": active_idx,
        "segId": active_seg["id"],
        "beat": active_seg.get("beat", active_seg["id"]),
        "segStart": active_seg["start"],
        "segEnd": active_seg["end"],
        "segProg": round(seg_prog, 5),
        "beatElapsed": round(beat_elapsed, 4),
        "subtitle": active_seg.get("subtitle", active_seg["text"]),
        "highlights": active_seg.get("highlights", []),
        "pose": pose_id,
        "layout": active_seg.get("layout", "pip_stage"),
        "mouth": int(mouth_seq[f_idx]),
        "energy": float(energy_seq[f_idx]),
    }


def _launch_page(pw, scene_uri, init_payload):
    browser = pw.chromium.launch(
        headless=True,
        args=[
            "--allow-file-access-from-files",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--font-render-hinting=none",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1080, "height": 1920},
        device_scale_factor=1,
    )
    page = context.new_page()
    page.goto(scene_uri, wait_until="load")
    page.evaluate("async (payload) => { await window.initEpisode(payload); }", init_payload)
    return browser, page


def _worker_render_chunk(args):
    (
        worker_id,
        scene_uri,
        init_payload,
        frame_start,
        frame_end,
        fps,
        timeline,
        mouth_seq,
        energy_seq,
        chunk_mp4,
        img_format,
    ) = args
    from playwright.sync_api import sync_playwright

    t0 = time.time()
    n_frames = frame_end - frame_start
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "image2pipe",
        "-vcodec", "mjpeg" if img_format == "jpeg" else "png",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.2",
        "-preset", "fast", "-crf", "16", "-g", str(fps * 2),
        "-pix_fmt", "yuv420p",
        str(chunk_mp4),
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    with sync_playwright() as pw:
        browser, page = _launch_page(pw, scene_uri, init_payload)
        for local_i, f_idx in enumerate(range(frame_start, frame_end)):
            state = build_frame_state(f_idx, fps, timeline, mouth_seq, energy_seq)
            page.evaluate("(s) => window.renderFrame(s)", state)
            if img_format == "jpeg":
                raw = page.screenshot(type="jpeg", quality=96)
            else:
                raw = page.screenshot(type="png")
            proc.stdin.write(raw)
            if local_i % 150 == 0 or local_i == n_frames - 1:
                elapsed = time.time() - t0
                rate = (local_i + 1) / max(0.1, elapsed)
                print(
                    f"  [worker {worker_id}] {local_i + 1}/{n_frames} "
                    f"(frame {f_idx}, {rate:.1f} fps)",
                    flush=True,
                )
        browser.close()

    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"Worker {worker_id} ffmpeg exited with code {ret}")
    return str(chunk_mp4)


def render_keyframes(scene_html, timeline, mouth_seq, energy_seq, init_payload, out_dir, fps=30):
    from playwright.sync_api import sync_playwright

    kf_dir = Path(out_dir) / f"{timeline['prefix']}_keyframes"
    kf_dir.mkdir(parents=True, exist_ok=True)
    scene_uri = Path(scene_html).resolve().as_uri()

    # Choose representative moments across segments
    segs = timeline["segments"]
    picks = []
    # Pick up to 12 key beats that showcase every scene & peak transition
    target_beats = [
        "hook_split", "hook_promise", "lens_density", "lens_center",
        "lens_soften", "chain_3", "chain_6", "chain_shield",
        "data_cypress", "data_cathay", "anchor_word", "outro_cta",
    ]
    beat_map = {s["beat"]: s for s in segs}
    matched_targets = [b for b in target_beats if b in beat_map]
    if len(matched_targets) >= 6:
        for b in matched_targets:
            s = beat_map[b]
            frac = 0.72 if b != "anchor_word" else 0.65
            t_pick = s["start"] + (s["end"] - s["start"]) * frac
            picks.append((b, min(len(mouth_seq) - 1, max(0, int(round(t_pick * fps))))))
    elif segs:
        # Universal episode-agnostic keyframe sampling across all segments (up to 12)
        if len(segs) <= 12:
            chosen = segs
        else:
            idxs = sorted({round(i * (len(segs) - 1) / 11) for i in range(12)})
            chosen = [segs[i] for i in idxs]
        for s in chosen:
            t_pick = s["start"] + (s["end"] - s["start"]) * 0.72
            label = s.get("beat") or s.get("id") or "seg"
            picks.append((label, min(len(mouth_seq) - 1, max(0, int(round(t_pick * fps))))))
    if not picks:
        step = max(1, len(mouth_seq) // 12)
        picks = [(f"f{i}", i) for i in range(0, len(mouth_seq), step)][:12]

    t0 = time.time()
    saved_paths = []
    with sync_playwright() as pw:
        browser, page = _launch_page(pw, scene_uri, init_payload)
        for idx, (label, f_idx) in enumerate(picks, 1):
            state = build_frame_state(f_idx, fps, timeline, mouth_seq, energy_seq)
            page.evaluate("(s) => window.renderFrame(s)", state)
            out_png = kf_dir / f"{idx:02d}_{label}_f{f_idx:04d}.png"
            page.screenshot(path=str(out_png), type="png")
            saved_paths.append(out_png)
            print(f"  KF {idx:02d}/{len(picks)}: {out_png.name} (t={state['t']:.2f}s)", flush=True)
        browser.close()

    # Build a crisp 4x3 contact sheet for fast holistic audit
    cols, rows = 4, math.ceil(len(saved_paths) / 4)
    tw, th = 360, 640
    sheet = Image.new("RGB", (cols * tw, rows * th), (12, 16, 28))
    for i, p in enumerate(saved_paths):
        im = Image.open(p).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
    sheet_path = kf_dir / "contact_sheet.png"
    sheet.save(sheet_path)
    print(f"Rendered {len(saved_paths)} keyframes in {time.time() - t0:.1f}s -> {sheet_path}")
    return saved_paths, sheet_path


def render_web_episode(
    scene_html,
    audio_dir,
    prefix,
    out_dir,
    page_title,
    fps=30,
    workers=4,
    keyframes_only=False,
    export_html=True,
    img_format="jpeg",
):
    audio_dir = Path(audio_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    vo_path = audio_dir / f"{prefix}_vo_master.wav"
    tl_path = audio_dir / f"{prefix}_timeline.json"
    timeline = json.loads(tl_path.read_text(encoding="utf-8"))

    vo_wav, sr = sf.read(str(vo_path))
    vo_wav = np.asarray(vo_wav, dtype=np.float32)

    total_sec = float(timeline["total_duration"])
    total_frames = int(round(total_sec * fps))
    mouth_seq = compute_mouth_sequence(vo_wav, sr, total_frames, fps=fps)
    energy_seq = compute_energy_envelope(vo_wav, sr, total_frames, fps=fps)

    poses_needed = [s.get("pose", "kaka_01") for s in timeline["segments"]]
    sprite_map = prebake_kaka_sprites(poses_needed)

    bg_dir = REPO_ROOT / "assets" / "backgrounds"
    bg_map = {
        p.name: p.resolve().as_uri()
        for p in sorted(bg_dir.iterdir())
        if p.is_file()
    }

    init_payload = {
        "timeline": timeline,
        "sprites": sprite_map,
        "backgrounds": bg_map,
    }

    if keyframes_only:
        return render_keyframes(scene_html, timeline, mouth_seq, energy_seq, init_payload, out_dir, fps=fps)

    t0 = time.time()
    mixed_audio = build_editorial_mix(vo_wav, sr, timeline)
    mixed_wav_path = audio_dir / f"{prefix}_final_mix.wav"
    sf.write(str(mixed_wav_path), mixed_audio, sr)
    print(f"[{prefix}] Built editorial audio mix -> {mixed_wav_path} ({total_sec:.2f}s)", flush=True)

    scene_uri = Path(scene_html).resolve().as_uri()
    workers = max(1, min(workers, os.cpu_count() or 4))
    chunk_size = math.ceil(total_frames / workers)
    tasks = []
    chunk_files = []
    for w_id in range(workers):
        f0 = w_id * chunk_size
        f1 = min(total_frames, f0 + chunk_size)
        if f0 >= f1:
            continue
        chunk_mp4 = out_dir / f".{prefix}_chunk_{w_id}.mp4"
        chunk_files.append(chunk_mp4)
        tasks.append((
            w_id,
            scene_uri,
            init_payload,
            f0,
            f1,
            fps,
            timeline,
            mouth_seq,
            energy_seq,
            str(chunk_mp4),
            img_format,
        ))

    print(f"[{prefix}] Rendering {total_frames} frames @ {fps}fps across {len(tasks)} Chromium workers...", flush=True)
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=len(tasks)) as pool:
        pool.map(_worker_render_chunk, tasks)

    concat_list = out_dir / f".{prefix}_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in chunk_files) + "\n",
        encoding="utf-8",
    )

    out_mp4 = out_dir / f"{prefix}_master.mp4"
    tmp_mp4 = out_dir / f"{prefix}_master.tmp.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-i", str(mixed_wav_path),
            "-c:v", "copy",
            "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
            "-movflags", "+faststart", "-shortest",
            str(tmp_mp4),
        ],
        check=True,
    )
    os.replace(tmp_mp4, out_mp4)

    for p in chunk_files:
        p.unlink(missing_ok=True)
    concat_list.unlink(missing_ok=True)

    # Full zero-NAL-error decode verification
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(out_mp4), "-f", "null", "-"], check=True)
    size_mb = out_mp4.stat().st_size / (1024 * 1024)
    print(f"[{prefix}] Verified ZERO H.264 errors -> {out_mp4} ({size_mb:.2f} MB) in {time.time() - t0:.1f}s", flush=True)

    if export_html:
        pure_html = out_dir / f"{prefix}_pure_video.html"
        export_pure_video_html(out_mp4, pure_html, page_title)
        h_mb = pure_html.stat().st_size / (1024 * 1024)
        print(f"[{prefix}] Exported pure video HTML -> {pure_html} ({h_mb:.2f} MB)", flush=True)

    return out_mp4


def main():
    parser = argparse.ArgumentParser(description="Kaka Vision Video Kit v2.0 Web/SVG/Canvas Episode Renderer.")
    parser.add_argument("--scene", required=True, help="Path to episode scene.html")
    parser.add_argument("--audio-dir", required=True, help="Directory with <prefix>_vo_master.wav & <prefix>_timeline.json")
    parser.add_argument("--prefix", required=True, help="Episode prefix (e.g. ep06)")
    parser.add_argument("--out-dir", default="output", help="Output directory")
    parser.add_argument("--title", default="卡卡老师《视光小课堂》(1080P)", help="HTML page title")
    parser.add_argument("--fps", type=int, default=30, help="Frame rate (default: 30)")
    parser.add_argument("--workers", type=int, default=4, help="Parallel Chromium worker count")
    parser.add_argument("--keyframes", action="store_true", help="Render keyframe audit pack only")
    parser.add_argument("--no-html", action="store_true", help="Skip pure HTML video export")
    parser.add_argument("--format", default="jpeg", choices=["jpeg", "png"], help="Intermediate pipe format")
    args = parser.parse_args()

    render_web_episode(
        scene_html=args.scene,
        audio_dir=args.audio_dir,
        prefix=args.prefix,
        out_dir=args.out_dir,
        page_title=args.title,
        fps=args.fps,
        workers=args.workers,
        keyframes_only=args.keyframes,
        export_html=not args.no_html,
        img_format=args.format,
    )


if __name__ == "__main__":
    main()

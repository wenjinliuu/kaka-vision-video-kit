#!/usr/bin/env python3
"""
Generic Qwen3-TTS Pure Baseline Voice Synthesizer for Kaka Vision Video Kit.

Design principles (battle-tested for natural Chinese science narration):
- Model: Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
- Speaker: "Serena", language="Chinese", instruct=None (pure baseline, zero over-acting artifacts)
- 1.0x native neural waveform (NO atempo time-stretching)
- Zero internal silence chopping (only trims outer dead silence; uses pause valleys read-only for subtitle timing)
- Segment-level .wav cache so interrupted runs resume cleanly
"""
import argparse
import json
import os
import time
from pathlib import Path
import numpy as np
import soundfile as sf
import torch


def trim_outer_and_locate_splits(wav, sr, num_clauses):
    wav = np.asarray(wav, dtype=np.float32)
    frame_len = int(sr * 0.02)
    hop = int(sr * 0.01)
    rms = np.array([
        np.sqrt(np.mean(wav[i:i + frame_len] ** 2) + 1e-9)
        for i in range(0, max(1, len(wav) - frame_len), hop)
    ])
    thresh = max(0.006, np.percentile(rms, 90) * 0.04)
    active = np.where(rms > thresh)[0]
    if len(active) > 0:
        start_idx = max(0, (active[0] - 4) * hop)
        end_idx = min(len(wav), (active[-1] + 8) * hop)
        wav = wav[start_idx:end_idx].copy()

    fade_n = int(sr * 0.01)
    if len(wav) > fade_n * 2:
        wav[:fade_n] *= np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
        wav[-fade_n:] *= np.linspace(1.0, 0.0, fade_n, dtype=np.float32)

    active_samples = wav[np.abs(wav) > 0.01]
    if len(active_samples) > 0:
        active_rms = float(np.sqrt(np.mean(active_samples ** 2) + 1e-8))
        wav = np.clip(wav * (0.155 / active_rms), -0.95, 0.95)

    total_sec = len(wav) / sr
    if num_clauses == 1:
        return wav, [(0.0, total_sec)]

    rms = np.array([
        np.sqrt(np.mean(wav[i:i + frame_len] ** 2) + 1e-9)
        for i in range(0, max(1, len(wav) - frame_len), hop)
    ])
    is_silent = rms < (thresh * 1.2)
    valleys = []
    in_v = False
    v_start = 0
    for idx, val in enumerate(is_silent):
        if val and not in_v:
            in_v = True
            v_start = idx
        elif not val and in_v:
            in_v = False
            dur = (idx - v_start) * 0.01
            if dur >= 0.06 and v_start > 15 and idx < len(is_silent) - 15:
                center_sec = ((v_start + idx) * 0.5 * hop) / sr
                valleys.append((center_sec, dur))

    split_secs = []
    for k in range(1, num_clauses):
        ideal_s = total_sec * (k / num_clauses)
        if valleys:
            best_v = min(valleys, key=lambda v: abs(v[0] - ideal_s))
            if abs(best_v[0] - ideal_s) < total_sec * 0.28:
                split_secs.append(best_v[0])
            else:
                split_secs.append(ideal_s)
        else:
            split_secs.append(ideal_s)
    split_secs = sorted(split_secs)
    pts = [0.0] + split_secs + [total_sec]
    return wav, [(pts[i], pts[i + 1]) for i in range(num_clauses)]


def synthesize_from_script(script_json_path, out_dir, device="auto", speaker="Serena"):
    from qwen_tts import Qwen3TTSModel

    script_cfg = json.loads(Path(script_json_path).read_text(encoding="utf-8"))
    prefix = script_cfg["prefix"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if device == "auto":
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(max(1, os.cpu_count() or 4))

    model = None
    sr_out = 24000
    master_chunks = [np.zeros(int(sr_out * 0.25), dtype=np.float32)]
    current_time = 0.25
    timeline = {"sr": sr_out, "scenes": {}, "clauses": []}

    for seg in script_cfg["segments"]:
        wav_p = out_dir / f"{seg['id']}_pure_base.wav"
        if wav_p.exists() and wav_p.stat().st_size > 8192:
            raw_wav, sr = sf.read(str(wav_p))
            print(f"  {seg['id']}: reused cached {len(raw_wav) / sr:.2f}s", flush=True)
        else:
            if model is None:
                print(f"Loading Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice on {device} (speaker={speaker}, instruct=None)...", flush=True)
                t0 = time.time()
                model = Qwen3TTSModel.from_pretrained(
                    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
                    device_map=device,
                    dtype=torch.bfloat16,
                )
                print(f"Model loaded in {time.time() - t0:.1f}s", flush=True)
            ts = time.time()
            wavs, sr = model.generate_custom_voice(
                text=seg["text"],
                language="Chinese",
                speaker=speaker,
                instruct=None,
            )
            raw_wav = wavs[0]
            sf.write(str(wav_p), raw_wav, sr)
            print(f"  {seg['id']}: synthesized {len(raw_wav) / sr:.2f}s (gen {time.time() - ts:.1f}s)", flush=True)

        clean_wav, bounds = trim_outer_and_locate_splits(raw_wav, sr, len(seg["clauses"]))
        seg_dur = len(clean_wav) / sr
        seg_start = current_time
        seg_end = seg_start + seg_dur

        sc_code = seg["scene"]
        post_pause = float(seg.get("post_pause", 0.35))
        if sc_code not in timeline["scenes"]:
            timeline["scenes"][sc_code] = {"start": round(seg_start, 3), "end": round(seg_end + post_pause, 3)}
        else:
            timeline["scenes"][sc_code]["end"] = round(seg_end + post_pause, 3)

        for c_meta, (b_start, b_end) in zip(seg["clauses"], bounds):
            timeline["clauses"].append({
                "id": c_meta["id"],
                "scene": sc_code,
                "pose": c_meta["pose"],
                "hl": c_meta.get("hl", "orange_pink"),
                "bubble": c_meta["bubble"],
                "start": round(seg_start + b_start, 3),
                "end": round(seg_start + b_end, 3),
            })

        master_chunks.append(clean_wav)
        master_chunks.append(np.zeros(int(sr * post_pause), dtype=np.float32))
        current_time = seg_end + post_pause

    master_vo = np.concatenate(master_chunks)
    timeline["total_duration"] = round(len(master_vo) / sr_out, 3)

    vo_path = out_dir / f"{prefix}_vo_master.wav"
    meta_path = out_dir / f"{prefix}_timeline.json"
    sf.write(str(vo_path), master_vo, sr_out)
    meta_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done! {timeline['total_duration']}s -> {vo_path}")


def main():
    parser = argparse.ArgumentParser(description="Synthesize Kaka Teacher voiceover from a JSON script.")
    parser.add_argument("--script", required=True, help="Path to episode script JSON (see examples/sample_script.json)")
    parser.add_argument("--out-dir", required=True, help="Output directory for WAV and timeline JSON")
    parser.add_argument("--device", default="auto", help="PyTorch device: auto, cpu, or cuda:0")
    parser.add_argument("--speaker", default="Serena", help="Qwen3-TTS CustomVoice speaker name")
    args = parser.parse_args()
    synthesize_from_script(args.script, args.out_dir, device=args.device, speaker=args.speaker)


if __name__ == "__main__":
    main()

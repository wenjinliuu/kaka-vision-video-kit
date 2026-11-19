#!/usr/bin/env python3
"""
Multi-engine Voice Synthesizer for Kaka Vision Video Kit (v2.0).

Supported engines:
1) edge (default): Microsoft Edge Neural TTS
   - Default voice: zh-CN-XiaoyiNeural (rate=+8%, pitch=-4Hz) "活力眼科小姐姐"
   - Supports per-segment `rate`, `pitch`, and `tts_text` overrides in script JSON
   - Broadcast loudness matching (-16 LUFS) + 24kHz mono WAV master output
   - Fast (~3-5s per full episode on CPU) with segment-level caching
2) qwen3: Local Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice (Serena / Vivian)
"""
import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
import numpy as np
import soundfile as sf


DEFAULT_EDGE_VOICE = "zh-CN-XiaoyiNeural"
DEFAULT_EDGE_RATE = "+8%"
DEFAULT_EDGE_PITCH = "-4Hz"


def trim_outer_and_locate_splits(wav, sr, num_clauses):
    wav = np.asarray(wav, dtype=np.float32)
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    frame_len = int(sr * 0.02)
    hop = int(sr * 0.01)
    rms = np.array([
        np.sqrt(np.mean(wav[i:i + frame_len] ** 2) + 1e-9)
        for i in range(0, max(1, len(wav) - frame_len), hop)
    ])
    thresh = max(0.005, np.percentile(rms, 90) * 0.035)
    active = np.where(rms > thresh)[0]
    if len(active) > 0:
        start_idx = max(0, (active[0] - 3) * hop)
        end_idx = min(len(wav), (active[-1] + 7) * hop)
        wav = wav[start_idx:end_idx].copy()

    fade_n = int(sr * 0.008)
    if len(wav) > fade_n * 2:
        wav[:fade_n] *= np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
        wav[-fade_n:] *= np.linspace(1.0, 0.0, fade_n, dtype=np.float32)

    active_samples = wav[np.abs(wav) > 0.01]
    if len(active_samples) > 0:
        active_rms = float(np.sqrt(np.mean(active_samples ** 2) + 1e-8))
        wav = np.clip(wav * (0.165 / active_rms), -0.95, 0.95)

    total_sec = len(wav) / sr
    if num_clauses <= 1:
        return wav, [(0.0, total_sec)]

    rms = np.array([
        np.sqrt(np.mean(wav[i:i + frame_len] ** 2) + 1e-9)
        for i in range(0, max(1, len(wav) - frame_len), hop)
    ])
    is_silent = rms < (thresh * 1.25)
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
            if dur >= 0.05 and v_start > 12 and idx < len(is_silent) - 12:
                center_sec = ((v_start + idx) * 0.5 * hop) / sr
                valleys.append((center_sec, dur))

    split_secs = []
    for k in range(1, num_clauses):
        ideal_s = total_sec * (k / num_clauses)
        if valleys:
            best_v = min(valleys, key=lambda v: abs(v[0] - ideal_s))
            if abs(best_v[0] - ideal_s) < total_sec * 0.30:
                split_secs.append(best_v[0])
            else:
                split_secs.append(ideal_s)
        else:
            split_secs.append(ideal_s)
    split_secs = sorted(split_secs)
    pts = [0.0] + split_secs + [total_sec]
    return wav, [(pts[i], pts[i + 1]) for i in range(num_clauses)]


async def _edge_synth_one(text, mp3_path, voice, rate, pitch):
    import edge_tts

    comm = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    await comm.save(str(mp3_path))


def _mp3_to_24k_wav(mp3_path, wav_path):
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(mp3_path),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le",
            str(wav_path),
        ],
        check=True,
    )


def _seg_cache_key(engine, voice, rate, pitch, text):
    payload = f"{engine}|{voice}|{rate}|{pitch}|{text}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:10]


def synthesize_from_script(
    script_json_path,
    out_dir,
    engine="edge",
    device="auto",
    voice=None,
    rate=None,
    pitch=None,
    speaker="Serena",
):
    script_cfg = json.loads(Path(script_json_path).read_text(encoding="utf-8"))
    prefix = script_cfg["prefix"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    voice_defaults = script_cfg.get("voice", {})
    engine = engine or voice_defaults.get("engine", "edge")
    edge_voice = voice or voice_defaults.get("voice", DEFAULT_EDGE_VOICE)
    edge_rate = rate or voice_defaults.get("rate", DEFAULT_EDGE_RATE)
    edge_pitch = pitch or voice_defaults.get("pitch", DEFAULT_EDGE_PITCH)

    qwen_model = None
    sr_out = 24000
    lead_in = float(script_cfg.get("lead_in", 0.28))
    master_chunks = [np.zeros(int(sr_out * lead_in), dtype=np.float32)]
    current_time = lead_in
    timeline = {
        "prefix": prefix,
        "engine": engine,
        "voice": edge_voice if engine == "edge" else speaker,
        "sr": sr_out,
        "scenes": {},
        "segments": [],
        "clauses": [],
    }

    for seg in script_cfg["segments"]:
        spoken_text = seg.get("tts_text", seg["text"])
        seg_voice = seg.get("voice", edge_voice)
        seg_rate = seg.get("rate", edge_rate)
        seg_pitch = seg.get("pitch", edge_pitch)

        ck = _seg_cache_key(
            engine,
            seg_voice if engine == "edge" else speaker,
            seg_rate if engine == "edge" else "1.0",
            seg_pitch if engine == "edge" else "0",
            spoken_text,
        )
        wav_p = out_dir / f"{seg['id']}_{engine}_{ck}.wav"

        if wav_p.exists() and wav_p.stat().st_size > 4096:
            raw_wav, sr = sf.read(str(wav_p))
            print(f"  {seg['id']}: reused cached {len(raw_wav) / sr:.2f}s", flush=True)
        elif engine == "edge":
            ts = time.time()
            tmp_mp3 = out_dir / f"{seg['id']}_{ck}.tmp.mp3"
            asyncio.run(_edge_synth_one(spoken_text, tmp_mp3, seg_voice, seg_rate, seg_pitch))
            _mp3_to_24k_wav(tmp_mp3, wav_p)
            tmp_mp3.unlink(missing_ok=True)
            raw_wav, sr = sf.read(str(wav_p))
            print(
                f"  {seg['id']}: edge [{seg_voice} {seg_rate} {seg_pitch}] "
                f"{len(raw_wav) / sr:.2f}s (gen {time.time() - ts:.2f}s)",
                flush=True,
            )
        elif engine == "qwen3":
            import torch
            from qwen_tts import Qwen3TTSModel

            if qwen_model is None:
                if device == "auto":
                    device = "cuda:0" if torch.cuda.is_available() else "cpu"
                torch.set_num_threads(max(1, os.cpu_count() or 4))
                print(
                    f"Loading Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice on {device} (speaker={speaker})...",
                    flush=True,
                )
                t0 = time.time()
                dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
                qwen_model = Qwen3TTSModel.from_pretrained(
                    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
                    device_map=device,
                    dtype=dtype,
                )
                print(f"Model loaded in {time.time() - t0:.1f}s", flush=True)
            ts = time.time()
            wavs, sr = qwen_model.generate_custom_voice(
                text=spoken_text,
                language="Chinese",
                speaker=speaker,
                instruct=None,
            )
            raw_wav = wavs[0]
            sf.write(str(wav_p), raw_wav, sr)
            print(f"  {seg['id']}: qwen3 {len(raw_wav) / sr:.2f}s (gen {time.time() - ts:.1f}s)", flush=True)
        else:
            raise ValueError(f"Unknown TTS engine: {engine}")

        clauses_cfg = seg.get("clauses")
        if not clauses_cfg:
            clauses_cfg = [{
                "id": seg["id"],
                "bubble": seg.get("bubble", [[seg["text"], False]]),
                "subtitle": seg.get("subtitle", seg["text"]),
                "pose": seg.get("pose", "kaka_01"),
                "hl": seg.get("hl", "blue_teal"),
            }]

        clean_wav, bounds = trim_outer_and_locate_splits(raw_wav, sr, len(clauses_cfg))
        seg_dur = len(clean_wav) / sr
        seg_start = current_time
        seg_end = seg_start + seg_dur

        sc_code = seg["scene"]
        post_pause = float(seg.get("post_pause", 0.28))
        if sc_code not in timeline["scenes"]:
            timeline["scenes"][sc_code] = {
                "start": round(seg_start, 3),
                "end": round(seg_end + post_pause, 3),
            }
        else:
            timeline["scenes"][sc_code]["end"] = round(seg_end + post_pause, 3)

        seg_entry = {
            "id": seg["id"],
            "scene": sc_code,
            "beat": seg.get("beat", seg["id"]),
            "text": seg["text"],
            "subtitle": seg.get("subtitle", seg["text"]),
            "highlights": seg.get("highlights", []),
            "pose": seg.get("pose", clauses_cfg[0].get("pose", "kaka_01")),
            "layout": seg.get("layout", "stage"),
            "sfx": seg.get("sfx", None),
            "start": round(seg_start, 3),
            "end": round(seg_end, 3),
            "end_with_pause": round(seg_end + post_pause, 3),
        }
        timeline["segments"].append(seg_entry)

        for c_meta, (b_start, b_end) in zip(clauses_cfg, bounds):
            timeline["clauses"].append({
                "id": c_meta["id"],
                "scene": sc_code,
                "beat": c_meta.get("beat", seg.get("beat", seg["id"])),
                "pose": c_meta.get("pose", seg.get("pose", "kaka_01")),
                "hl": c_meta.get("hl", "blue_teal"),
                "bubble": c_meta.get("bubble", []),
                "subtitle": c_meta.get("subtitle", seg.get("subtitle", seg["text"])),
                "highlights": c_meta.get("highlights", seg.get("highlights", [])),
                "start": round(seg_start + b_start, 3),
                "end": round(seg_start + b_end, 3),
            })

        master_chunks.append(clean_wav)
        if post_pause > 0:
            master_chunks.append(np.zeros(int(sr * post_pause), dtype=np.float32))
        current_time = seg_end + post_pause

    master_vo = np.concatenate(master_chunks)
    timeline["total_duration"] = round(len(master_vo) / sr_out, 3)

    vo_path = out_dir / f"{prefix}_vo_master.wav"
    meta_path = out_dir / f"{prefix}_timeline.json"
    sf.write(str(vo_path), master_vo, sr_out)
    meta_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done! {timeline['total_duration']}s -> {vo_path}")
    return vo_path, meta_path


def main():
    parser = argparse.ArgumentParser(description="Synthesize Kaka Teacher voiceover from a JSON script.")
    parser.add_argument("--script", required=True, help="Path to episode script JSON")
    parser.add_argument("--out-dir", required=True, help="Output directory for WAV and timeline JSON")
    parser.add_argument("--engine", default="edge", choices=["edge", "qwen3"], help="TTS backend (default: edge)")
    parser.add_argument("--voice", default=None, help="Edge TTS voice name (default: zh-CN-XiaoyiNeural)")
    parser.add_argument("--rate", default=None, help="Edge TTS rate (default: +8%%)")
    parser.add_argument("--pitch", default=None, help="Edge TTS pitch (default: -4Hz)")
    parser.add_argument("--device", default="auto", help="PyTorch device for qwen3: auto, cpu, or cuda:0")
    parser.add_argument("--speaker", default="Serena", help="Qwen3-TTS speaker name")
    args = parser.parse_args()
    synthesize_from_script(
        args.script,
        args.out_dir,
        engine=args.engine,
        device=args.device,
        voice=args.voice,
        rate=args.rate,
        pitch=args.pitch,
        speaker=args.speaker,
    )


if __name__ == "__main__":
    main()

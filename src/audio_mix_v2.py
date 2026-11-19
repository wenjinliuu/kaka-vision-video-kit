#!/usr/bin/env python3
"""
Studio-grade procedural editorial science BGM + cinematic SFX mixer for Kaka Vision Video Kit v2.0.
"""
import numpy as np
from scipy.signal import butter, filtfilt


def _lowpass(sig, sr, cutoff_hz, order=3):
    nyq = 0.5 * sr
    b, a = butter(order, min(0.95, cutoff_hz / nyq), btype="low")
    return filtfilt(b, a, sig).astype(np.float32)


def _bandpass(sig, sr, lo_hz, hi_hz, order=2):
    nyq = 0.5 * sr
    b, a = butter(order, [max(0.005, lo_hz / nyq), min(0.95, hi_hz / nyq)], btype="band")
    return filtfilt(b, a, sig).astype(np.float32)


def _add_at(buf, i0, wave):
    if i0 < 0:
        wave = wave[-i0:]
        i0 = 0
    if i0 >= len(buf) or len(wave) == 0:
        return
    n = min(len(wave), len(buf) - i0)
    buf[i0:i0 + n] += wave[:n]


def build_editorial_mix(vo_wav, sr, timeline):
    """
    Creates a refined editorial science BGM bed (warm felt-keys + gentle pluck + soft sub pulse)
    with smooth voice-following ducking and beat-synced cinematic UI/optical SFX.
    """
    vo_wav = np.asarray(vo_wav, dtype=np.float32)
    if vo_wav.ndim > 1:
        vo_wav = vo_wav.mean(axis=1)
    n_samples = len(vo_wav)

    # 1. Warm Editorial Science BGM (104 BPM, Cmaj7 - Am9 - Fmaj7 - G6)
    bpm = 104.0
    beat_sec = 60.0 / bpm
    eighth_sec = beat_sec / 2.0
    bgm = np.zeros(n_samples, dtype=np.float32)

    # Chords: (sub_root, [voicing_freqs])
    progression = [
        (130.81, [261.63, 329.63, 392.00, 493.88, 587.33]),  # Cmaj9
        (110.00, [220.00, 261.63, 329.63, 392.00, 493.88]),  # Am9
        (87.31,  [174.61, 220.00, 261.63, 329.63, 392.00]),  # Fmaj9
        (98.00,  [196.00, 246.94, 293.66, 392.00, 493.88]),  # G6/9
    ]
    arp_pattern = [0, 2, 3, 4, 2, 3, 1, 4]

    total_eighths = int((n_samples / sr) / eighth_sec) + 2
    for idx in range(total_eighths):
        onset_i = int(idx * eighth_sec * sr)
        if onset_i >= n_samples:
            break
        bar_idx = (idx // 8) % len(progression)
        step_in_bar = idx % 8
        sub_f, chord = progression[bar_idx]

        # Warm sustained felt-pad on downbeat of each bar
        if step_in_bar == 0:
            dur_s = min(beat_sec * 4.2, (n_samples - onset_i) / sr)
            dur_i = int(dur_s * sr)
            if dur_i > 64:
                t = np.arange(dur_i, dtype=np.float32) / sr
                env = (1.0 - np.exp(-t * 5.5)) * np.exp(-t * 0.55)
                pad = np.sin(2 * np.pi * sub_f * t) * 0.36
                for f in chord[:4]:
                    pad += (
                        np.sin(2 * np.pi * f * t) * 0.14
                        + np.sin(2 * np.pi * f * 2.0 * t) * 0.025 * np.exp(-t * 2.5)
                    )
                _add_at(bgm, onset_i, pad * env * 0.13)

        # Delicate glass-marimba arpeggio pluck
        freq = chord[arp_pattern[step_in_bar]]
        pluck_dur = min(0.55, (n_samples - onset_i) / sr)
        dur_i = int(pluck_dur * sr)
        if dur_i > 32:
            t = np.arange(dur_i, dtype=np.float32) / sr
            env = np.exp(-t * 7.8) * (1.0 - np.exp(-t * 240.0))
            accent = 1.0 if step_in_bar in (0, 3, 6) else 0.72
            note = (
                np.sin(2 * np.pi * freq * t)
                + 0.20 * np.sin(2 * np.pi * freq * 2.0 * t) * np.exp(-t * 18.0)
                + 0.06 * np.sin(2 * np.pi * freq * 3.0 * t) * np.exp(-t * 28.0)
            ) * env * accent * 0.095
            _add_at(bgm, onset_i, note)

    # Gentle low-pass polish on BGM so it sits warmly behind voice without competing with sibilants
    bgm = _lowpass(bgm, sr, 4200.0, order=2)

    # Smooth voice-following ducking envelope
    win = max(1, int(sr * 0.07))
    vo_env = np.convolve(np.abs(vo_wav), np.ones(win, dtype=np.float32) / win, mode="same")
    duck_target = np.where(vo_env > 0.011, 0.24, 0.52).astype(np.float32)
    smooth_len = max(1, int(sr * 0.24))
    duck_gain = np.convolve(duck_target, np.ones(smooth_len, dtype=np.float32) / smooth_len, mode="same")
    bgm *= duck_gain

    # Fade in & out BGM gracefully
    fi = min(int(sr * 0.35), n_samples)
    fo = min(int(sr * 0.85), n_samples)
    if fi > 0:
        bgm[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)
    if fo > 0:
        bgm[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)

    # 2. Cinematic UI & Optical SFX
    sfx = np.zeros(n_samples, dtype=np.float32)
    rng = np.random.default_rng(42)

    def sfx_impact(t_s):
        i0 = int(t_s * sr)
        n = int(sr * 0.36)
        t = np.arange(n, dtype=np.float32) / sr
        sub = np.sin(2 * np.pi * np.linspace(145.0, 48.0, n) * t) * np.exp(-t * 11.0) * 0.16
        bell = np.sin(2 * np.pi * 880.0 * t) * np.exp(-t * 14.0) * 0.055
        _add_at(sfx, i0, sub + bell)

    def sfx_whoosh(t_s):
        i0 = int(max(0.0, t_s - 0.08) * sr)
        n = int(sr * 0.28)
        t = np.arange(n, dtype=np.float32) / sr
        noise = rng.standard_normal(n).astype(np.float32)
        noise = _bandpass(noise, sr, 420.0, 2600.0, order=2)
        env = np.sin(np.pi * t / 0.28) ** 1.6
        _add_at(sfx, i0, noise * env * 0.085)

    def sfx_ping(t_s, f1=987.77, f2=1479.98, amp=0.062):
        i0 = int(t_s * sr)
        n = int(sr * 0.32)
        t = np.arange(n, dtype=np.float32) / sr
        env = np.exp(-t * 11.5) * (1.0 - np.exp(-t * 320.0))
        w = (np.sin(2 * np.pi * f1 * t) + 0.35 * np.sin(2 * np.pi * f2 * t)) * env * amp
        _add_at(sfx, i0, w)

    def sfx_pop(t_s):
        i0 = int(t_s * sr)
        n = int(sr * 0.075)
        t = np.arange(n, dtype=np.float32) / sr
        f = np.linspace(480.0, 920.0, n)
        env = np.sin(np.pi * t / 0.075) * np.exp(-t * 22.0)
        _add_at(sfx, i0, np.sin(2 * np.pi * f * t) * env * 0.075)

    def sfx_chime(t_s):
        for off, freq in [(0.0, 783.99), (0.085, 1046.50)]:
            sfx_ping(t_s + off, freq, freq * 1.5, amp=0.058)

    def sfx_alert(t_s):
        for off, freq in [(0.0, 440.0), (0.09, 392.0)]:
            i0 = int((t_s + off) * sr)
            n = int(sr * 0.22)
            t = np.arange(n, dtype=np.float32) / sr
            env = np.exp(-t * 12.0) * (1.0 - np.exp(-t * 240.0))
            w = (np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 1.5 * t)) * env * 0.08
            _add_at(sfx, i0, w)

    def sfx_shield(t_s):
        for idx, freq in enumerate([523.25, 659.25, 783.99, 987.77, 1318.51]):
            sfx_ping(t_s + idx * 0.048, freq, freq * 2.0, amp=0.050)

    def sfx_anchor(t_s):
        i0 = int(max(0.0, t_s - 0.04) * sr)
        n = int(sr * 0.95)
        t = np.arange(n, dtype=np.float32) / sr
        env = (1.0 - np.exp(-t * 18.0)) * np.exp(-t * 2.8)
        w = (
            np.sin(2 * np.pi * 261.63 * t) * 0.38
            + np.sin(2 * np.pi * 392.00 * t) * 0.26
            + np.sin(2 * np.pi * 523.25 * t) * 0.24
            + np.sin(2 * np.pi * 659.25 * t) * 0.16
        ) * env * 0.11
        _add_at(sfx, i0, w)

    chain_freqs = {
        "chain_1": 523.25,
        "chain_2": 587.33,
        "chain_3": 659.25,
        "chain_4": 783.99,
        "chain_5": 880.00,
    }

    for seg in timeline.get("segments", []):
        kind = seg.get("sfx")
        t_s = float(seg["start"])
        if not kind:
            continue
        if kind == "impact":
            sfx_impact(t_s)
        elif kind == "whoosh":
            sfx_whoosh(t_s)
        elif kind == "ping":
            sfx_ping(t_s)
        elif kind == "pop":
            sfx_pop(t_s)
        elif kind == "chime":
            sfx_chime(t_s)
        elif kind == "alert":
            sfx_alert(t_s)
        elif kind == "shield":
            sfx_shield(t_s)
        elif kind == "anchor":
            sfx_anchor(t_s)
        elif kind in chain_freqs:
            f = chain_freqs[kind]
            sfx_ping(t_s, f, f * 1.5, amp=0.068)

    mixed = vo_wav + bgm + sfx
    peak = float(np.max(np.abs(mixed)) + 1e-8)
    if peak > 0.96:
        mixed = mixed * (0.96 / peak)
    return np.clip(mixed, -0.98, 0.98).astype(np.float32)


def compute_mouth_sequence(vo_wav, sr, total_frames, fps=30):
    """Smooth 30fps lip-sync state machine (mouth IDs 1..6) with zero jitter."""
    vo_wav = np.asarray(vo_wav, dtype=np.float32)
    if vo_wav.ndim > 1:
        vo_wav = vo_wav.mean(axis=1)
    raw_energies = np.zeros(total_frames, dtype=np.float32)
    for f_idx in range(total_frames):
        t_s = f_idx / fps
        i0 = max(0, int((t_s - 0.035) * sr))
        i1 = min(len(vo_wav), int((t_s + 0.055) * sr))
        w = vo_wav[i0:i1]
        rms = float(np.sqrt(np.mean(w ** 2) + 1e-9)) if len(w) > 0 else 0.0
        raw_energies[f_idx] = min(1.0, rms / 0.21)

    smooth_energies = np.convolve(raw_energies, np.array([0.2, 0.6, 0.2], dtype=np.float32), mode="same")
    mouth_seq = []
    curr_mouth = 1
    hold_count = 0
    min_hold = max(3, int(round(fps / 9.0)))
    for f_idx in range(total_frames):
        e = float(smooth_energies[f_idx])
        if e < 0.065:
            target_m = 1
        elif e < 0.21:
            target_m = 6
        elif e < 0.44:
            target_m = 2
        elif e < 0.66:
            target_m = 3
        elif e < 0.83:
            target_m = 5 if (f_idx // 5) % 2 == 0 else 3
        else:
            target_m = 4

        if target_m == 1:
            curr_mouth = 1
            hold_count = 0
        elif hold_count >= min_hold or curr_mouth == 1:
            curr_mouth = target_m
            hold_count = 1
        else:
            hold_count += 1
        mouth_seq.append(curr_mouth)
    return mouth_seq

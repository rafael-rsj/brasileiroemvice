"""Trilha synthwave original gerada por código (sem direitos autorais de terceiros).

make_track(path, seconds, seed) grava um .wav estéreo 48 kHz no clima de Vice City:
pad de acordes, baixo pulsando, arpejo e bateria eletrônica. O seed muda tom, andamento e timbre.
"""
import wave

import numpy as np

SR = 48000
PROGRESSIONS = [
    [(0, 3, 7), (-4, 0, 3), (3, 7, 10), (-2, 2, 5)],    # i  VI III VII
    [(0, 3, 7), (5, 8, 12), (-4, 0, 3), (-2, 2, 5)],    # i  iv VI VII
    [(0, 3, 7), (-2, 2, 5), (-4, 0, 3), (-5, -1, 2)],   # i  VII VI V
]


def _freq(semi, base):
    return base * 2 ** (semi / 12)


def _saw(f, t, detune=0.0):
    out = np.zeros_like(t)
    for d in (-detune, 0, detune):
        ph = (t * f * (1 + d)) % 1.0
        out += 2 * ph - 1
    return out / 3


def _env(n, a=0.005, r=0.2):
    e = np.ones(n)
    na, nr = min(int(a * SR), n // 2), min(int(r * SR), n // 2)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def _lowpass(x, k):
    """Filtro passa-baixa simples (janela suave), sem dependências extras."""
    w = max(3, int(1 / k))
    ker = np.hanning(w)
    ker /= ker.sum()
    return np.convolve(x, ker, mode="same")


def make_track(path, seconds=24.0, seed=0):
    rng = np.random.default_rng(seed)
    bpm = float(rng.choice([92, 98, 104, 110]))
    base = 110.0 * 2 ** (int(rng.integers(-3, 4)) / 12)  # tom
    prog = PROGRESSIONS[seed % len(PROGRESSIONS)]
    beat = 60 / bpm
    bar = 4 * beat
    n = int(seconds * SR)
    t = np.arange(n) / SR
    mix = np.zeros(n)

    # pad (acordes longos)
    pad = np.zeros(n)
    for b in range(int(seconds / bar) + 1):
        s0, s1 = int(b * bar * SR), min(int((b + 1) * bar * SR), n)
        if s0 >= n:
            break
        chord = prog[b % 4]
        tt = t[s0:s1]
        seg = sum(_saw(_freq(c + 12, base), tt, 0.004) for c in chord) / 3
        pad[s0:s1] = seg * _env(s1 - s0, 0.3, 0.4)
    pad = _lowpass(pad, 0.06)
    mix += pad * 0.35

    # baixo em colcheias
    step = beat / 2
    for k in range(int(seconds / step)):
        s0 = int(k * step * SR)
        s1 = min(s0 + int(step * SR * 0.9), n)
        chord = prog[int(k * step / bar) % 4]
        f = _freq(chord[0] - 12, base)
        tt = t[s0:s1] - t[s0]
        mix[s0:s1] += _saw(f, tt) * _env(s1 - s0, 0.002, 0.05) * 0.28

    # arpejo em semicolcheias
    arp_step = beat / 4
    for k in range(int(seconds / arp_step)):
        s0 = int(k * arp_step * SR)
        s1 = min(s0 + int(arp_step * SR), n)
        chord = prog[int(k * arp_step / bar) % 4]
        note = chord[k % 3] + 24 + (12 if (k // 3) % 4 == 3 else 0)
        tt = t[s0:s1] - t[s0]
        sq = np.sign(np.sin(2 * np.pi * _freq(note, base) * tt))
        mix[s0:s1] += sq * np.exp(-tt * 18) * 0.07

    # bateria: bumbo 1 e 3, caixa 2 e 4, chimbal em colcheias
    for k in range(int(seconds / beat)):
        s0 = int(k * beat * SR)
        if k % 2 == 0:
            m = min(int(0.35 * SR), n - s0)
            tt = np.arange(m) / SR
            kick = np.sin(2 * np.pi * (50 + 120 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)
            mix[s0:s0 + m] += kick * 0.75
        else:
            m = min(int(0.25 * SR), n - s0)
            tt = np.arange(m) / SR
            snare = rng.standard_normal(m) * np.exp(-tt * 18) * 0.25 + np.sin(2 * np.pi * 190 * tt) * np.exp(-tt * 25) * 0.2
            mix[s0:s0 + m] += snare
    for k in range(int(seconds / (beat / 2))):
        s0 = int(k * beat / 2 * SR)
        m = min(int(0.05 * SR), n - s0)
        hat = np.diff(rng.standard_normal(m + 1)) * np.exp(-np.arange(m) / SR * 80) * 0.06
        mix[s0:s0 + m] += hat

    # fade in/out e normalização
    fade = int(1.2 * SR)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.85
    # estéreo com leve atraso no canal direito
    right = np.concatenate([np.zeros(int(0.012 * SR)), mix])[:n]
    stereo = (np.stack([mix, right * 0.95 + mix * 0.05], axis=1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())
    return path

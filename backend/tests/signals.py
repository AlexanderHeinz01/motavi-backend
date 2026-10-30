"""Synthetic feature signals for the cycle tests."""
from __future__ import annotations

import numpy as np


def waveform(phase: np.ndarray) -> np.ndarray:
    """Six channels of one work cycle (phase 0..1): reach, grip, place."""
    p = 2 * np.pi * phase
    bump = np.exp(-(((phase - 0.3) % 1.0) ** 2) / 0.005)  # grip
    return np.column_stack([
        np.sin(p) + 0.5 * np.sin(2 * p + 1.0),
        np.cos(p + 0.3),
        bump,
        np.sin(3 * p) * 0.4 + phase,
        np.cos(2 * p) * 0.6,
        np.sin(p - 0.8) * 0.3,
    ])


def periodic(period_s=12.0, n_cycles=10, rate=15.0, jitter=0.0, noise=0.1, seed=0):
    """Cycles of varying length (period * (1 + jitter * u), u in -1..1) plus noise.

    Returns t, raw features [F, 6] and the true cycle durations.
    """
    rng = np.random.default_rng(seed)
    durations = period_s * (1 + jitter * rng.uniform(-1, 1, n_cycles))
    phases = [np.arange(int(round(d * rate))) / (d * rate) for d in durations]
    phase = np.concatenate(phases)
    x = waveform(phase) + rng.normal(0, noise, (len(phase), 6))
    t = np.arange(len(phase)) / rate
    return t, x, durations


def pause(seconds, rate=15.0, noise=0.1, seed=1, level=None):
    """Standing still: constant posture plus noise."""
    rng = np.random.default_rng(seed)
    n = int(round(seconds * rate))
    base = waveform(np.zeros(1)) if level is None else level
    return np.repeat(base, n, axis=0) + rng.normal(0, noise, (n, 6))


def aperiodic(seconds=240.0, rate=15.0, seed=3):
    """Smoothed random walk: movement without a repeating pattern."""
    rng = np.random.default_rng(seed)
    n = int(round(seconds * rate))
    steps = rng.normal(0, 1, (n, 6))
    walk = np.cumsum(steps, axis=0)
    kernel = np.ones(15) / 15
    smooth = np.column_stack([np.convolve(walk[:, c], kernel, mode="same") for c in range(6)])
    return np.arange(n) / rate, smooth + rng.normal(0, 0.3, (n, 6))

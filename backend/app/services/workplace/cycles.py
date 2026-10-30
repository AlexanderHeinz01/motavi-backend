"""Cycle detection (STECKBRIEF_MODUL §4.1).

Signal: feature vector per frame from the normalised wrist positions, the
trunk inclination and the shoulder width (projected shoulder width changes
when the trunk rotates). Each channel is standardised.

1. Dominant period from the autocorrelation of the features (masked, so
   gaps do not count), search range 3 to 180 s.
2. Cycle boundaries by template matching: the window of one period that
   best repeats itself is the first template; a normalised cross
   correlation finds its repetitions; the mean of the found cycles becomes
   the refined template, and the search runs once more.
3. Outliers: cycles that are too long (interruption, side task), too short
   or too dissimilar to the template are marked and not used for the
   cycle time.

No recurring cycle is a result as well: "Kein wiederkehrender Zyklus
erkannt", with all cycle metrics "nicht belastbar messbar".
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.signal import correlate, find_peaks

from .preprocess import Prepared
from .quality import Kennzahl

KEIN_ZYKLUS = "Kein wiederkehrender Zyklus erkannt"


@dataclass(frozen=True)
class CycleConfig:
    min_period_s: float = 3.0
    max_period_s: float = 180.0
    min_cycles: int = 3  # at least this many valid cycles
    min_periodicity: float = 0.25  # autocorrelation at the period
    min_similarity: float = 0.5  # correlation of a cycle with the template
    duration_tolerance: float = 0.35  # valid cycle: median duration ± 35 %
    min_coverage: float = 0.6  # share of frames with a person
    reliable: float = 0.5  # quality threshold for the metrics
    min_cycles_cv: int = 5  # variation coefficient needs more cycles
    harmonic_ratio: float = 0.85  # prefer an earlier peak of at least this height


@dataclass(frozen=True)
class Zyklus:
    """A detected cycle or an interruption between cycles (art)."""

    start_s: float
    ende_s: float
    dauer_s: float
    aehnlichkeit: float
    gueltig: bool
    grund: str | None = None  # why it is an outlier
    art: str = "zyklus"  # "zyklus" or "unterbrechung"


@dataclass(frozen=True)
class ZyklusErgebnis:
    erkannt: bool
    hinweis: str | None
    periode_s: float | None  # from the autocorrelation
    periodizitaet: float  # autocorrelation at the period, 0 to 1
    konfidenz: float  # 0 to 1, see _konfidenz
    anzahl_gueltig: int
    zyklen: list[Zyklus]
    zykluszeit_median: Kennzahl
    zykluszeit_mittel: Kennzahl
    zykluszeit_std: Kennzahl
    zykluszeit_vk: Kennzahl
    zyklen_pro_schicht: Kennzahl
    zeitanteil_in_zyklen: Kennzahl
    # for plots and later steps
    t: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0))
    signal: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0))
    acf_lags_s: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0))
    acf: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0))


# ── features ─────────────────────────────────────────────────────────────────


def features(prep: Prepared) -> tuple[np.ndarray, np.ndarray]:
    """Feature matrix [F, C] (standardised, NaN where missing) and frame mask."""
    lw, rw = prep.joint("left_wrist")[:, :2], prep.joint("right_wrist")[:, :2]
    ls, rs = prep.joint("left_shoulder")[:, :2], prep.joint("right_shoulder")[:, :2]
    sh = (ls + rs) / 2
    trunk = np.degrees(np.arctan2(sh[:, 0], -sh[:, 1]))  # inclination, signed
    width = np.linalg.norm(ls - rs, axis=1)  # rotation proxy
    raw = np.column_stack([lw, rw, trunk / 45.0, width])
    raw[~prep.valid] = np.nan
    return standardise(raw)


def standardise(raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = ~np.isnan(raw).any(axis=1)
    x = raw.copy()
    keep = []
    for c in range(raw.shape[1]):
        v = raw[mask, c]
        sd = float(np.std(v)) if v.size else 0.0
        if sd > 1e-6:
            x[:, c] = (raw[:, c] - float(np.mean(v))) / sd
            keep.append(c)
    return x[:, keep], mask


# ── autocorrelation ──────────────────────────────────────────────────────────


def masked_acf(x: np.ndarray, mask: np.ndarray, max_lag: int) -> tuple[np.ndarray, np.ndarray]:
    """Autocorrelation per channel, counting only valid frame pairs.

    Returns acf[0..max_lag, C] and the number of valid pairs per lag.
    """
    f = len(mask)
    m = mask.astype(float)
    xs = np.where(mask[:, None], x, 0.0)
    n = 1 << int(np.ceil(np.log2(2 * f)))
    fm = np.fft.rfft(m, n)
    pairs = np.fft.irfft(fm * np.conj(fm), n)[: max_lag + 1]
    acc = np.zeros((max_lag + 1, xs.shape[1]))
    for c in range(xs.shape[1]):
        fx = np.fft.rfft(xs[:, c], n)
        acc[:, c] = np.fft.irfft(fx * np.conj(fx), n)[: max_lag + 1]
    pairs = np.maximum(np.round(pairs), 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        acf = acc / pairs[:, None]
    return acf, pairs


def channel_weights(acf_ch: np.ndarray, rate: float) -> np.ndarray:
    """Weight per channel: how much it moves rather than just carries noise.

    The largest absolute autocorrelation at lags of 0.5 s and 1 s. Noise (a
    hand at rest, smoothed over about 0.3 s) is almost uncorrelated there,
    a moving channel is clearly correlated at least at one of the two lags
    (two lags, so a sine whose quarter period is exactly one lag still
    counts). So noise channels cannot dilute the period of the moving ones,
    and the weight does not depend on the period, so an overtone cannot pull
    the result to half the period.
    """
    lags = [min(len(acf_ch) - 1, max(1, int(round(f * rate)))) for f in (0.5, 1.0)]
    vals = np.abs(np.nan_to_num(acf_ch[lags], nan=0.0))
    return np.clip(vals.max(axis=0), 0, 1)


def dominant_period(x: np.ndarray, mask: np.ndarray, rate: float, cfg: CycleConfig) -> tuple[float | None, float, np.ndarray, np.ndarray]:
    """Period in seconds (None if none), its periodicity (0 to 1), the
    weighted acf and the channel weights."""
    valid = int(mask.sum())
    min_lag = max(2, int(round(cfg.min_period_s * rate)))
    # at least min_cycles periods must fit into the valid data
    max_lag = min(int(round(cfg.max_period_s * rate)), valid // cfg.min_cycles)
    ones = np.ones(x.shape[1])
    if max_lag <= min_lag + 2 or x.shape[1] == 0:
        return None, 0.0, np.zeros(1), ones
    acf_ch, pairs = masked_acf(x, mask, max_lag)
    weights = channel_weights(acf_ch, rate)
    if weights.sum() <= 0:
        return None, 0.0, np.zeros(1), ones
    acf = np.where(pairs >= 0.25 * valid, acf_ch @ weights / weights.sum(), np.nan)
    search = np.nan_to_num(acf, nan=-1.0)
    peaks, props = find_peaks(search[: max_lag + 1], prominence=0.1)
    peaks = peaks[(peaks >= min_lag) & (peaks <= max_lag)]
    if peaks.size == 0:
        return None, 0.0, acf, ones
    heights = search[peaks]
    best = float(heights.max())
    # fundamental: the first peak that is nearly as high as the best one
    first = peaks[np.argmax(heights >= cfg.harmonic_ratio * best)]
    h = float(search[first])
    # parabolic refinement of the lag
    lag = float(first)
    if 0 < first < len(search) - 1:
        a, b, c = search[first - 1], search[first], search[first + 1]
        denom = a - 2 * b + c
        if abs(denom) > 1e-12:
            lag = first + 0.5 * (a - c) / denom
    if h < cfg.min_periodicity:
        return None, h, acf, ones
    return lag / rate, h, acf, weights


# ── template matching ────────────────────────────────────────────────────────


def smooth_for_period(x: np.ndarray, mask: np.ndarray, period_frames: int) -> np.ndarray:
    """Masked moving average over about 1/40 of the period.

    Frame noise does not matter for the shape of a long cycle, but it lowers
    the correlation of single cycles with the template. Short cycles stay
    unchanged (window of one frame).
    """
    w = max(1, int(round(period_frames / 40)))
    if w == 1:
        return x
    k = np.ones(w)
    m = mask.astype(float)
    xs = np.where(mask[:, None], x, 0.0)
    num = np.column_stack([np.convolve(xs[:, c], k, mode="same") for c in range(x.shape[1])])
    den = np.convolve(m, k, mode="same")
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den[:, None]
    out[~mask] = np.nan
    return out


def _window_sums(v: np.ndarray, length: int) -> np.ndarray:
    c = np.concatenate([[0.0], np.cumsum(v)])
    return c[length:] - c[:-length]


def template_correlation(x: np.ndarray, mask: np.ndarray, template: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
    """Correlation of the template [L, C] with every window of x.

    Pearson per channel (each window centred on its own mean), then the mean
    over the channels (weighted by their periodicity). Per channel, so that a still posture whose channel
    levels happen to match the template does not look like a cycle. Only
    valid frames count; windows with less than 80 % valid frames get NaN.
    """
    f, ch = x.shape
    length = template.shape[0]
    if f < length:
        return np.empty(0)
    m = mask.astype(float)
    xs = np.where(mask[:, None], x, 0.0)
    n = _window_sums(m, length)
    w = np.ones(ch) if weights is None else np.asarray(weights, dtype=float)
    total = np.zeros(f - length + 1)
    for c in range(ch):
        if w[c] <= 0:
            continue
        tc = template[:, c]
        sx = _window_sums(xs[:, c], length)
        sxx = _window_sums(xs[:, c] ** 2, length)
        sxt = correlate(xs[:, c], tc, mode="valid", method="fft")
        st = correlate(m, tc, mode="valid", method="fft")
        stt = correlate(m, tc**2, mode="valid", method="fft")
        with np.errstate(invalid="ignore", divide="ignore"):
            r = (n * sxt - sx * st) / np.sqrt(np.maximum(n * sxx - sx**2, 0) * np.maximum(n * stt - st**2, 0))
        total += w[c] * np.nan_to_num(r, nan=0.0)
    r = total / w.sum()
    r[n < 0.8 * length] = np.nan
    return r


def _best_repeating_window(x: np.ndarray, mask: np.ndarray, length: int, weights: np.ndarray) -> int | None:
    """Start of the window that is most similar to the window one period later."""
    f = len(mask)
    best, best_r = None, -np.inf
    for s in range(0, f - 2 * length + 1, max(1, length // 8)):
        a, b = slice(s, s + length), slice(s + length, s + 2 * length)
        ok = mask[a] & mask[b]
        if ok.mean() < 0.9:
            continue
        rc = np.array([np.corrcoef(x[a][ok, c], x[b][ok, c])[0, 1] for c in range(x.shape[1])])
        r = float(np.nansum(weights * rc) / weights.sum())
        if r > best_r:
            best, best_r = s, r
    return best


def _boundaries(corr: np.ndarray, length: int, cfg: CycleConfig) -> np.ndarray:
    """Cycle starts: peaks of the template correlation (also at the edges)."""
    padded = np.concatenate([[-1.0], np.nan_to_num(corr, nan=-1.0), [-1.0]])
    peaks, _ = find_peaks(padded, height=cfg.min_similarity, distance=max(1, int(0.65 * length)))
    return peaks - 1


# ── main ─────────────────────────────────────────────────────────────────────


def _konfidenz(periodicity: float, similarity: float, valid_share: float, coverage: float) -> float:
    """Geometric mean of the four quality components (each 0 to 1)."""
    parts = np.clip([periodicity / 0.6, similarity, valid_share, coverage], 1e-6, 1.0)
    return float(np.exp(np.mean(np.log(parts))))


def _kein_zyklus(t, signal, lags, acf, periodicity, hinweis=KEIN_ZYKLUS) -> ZyklusErgebnis:
    k = Kennzahl.fehlt(hinweis)
    return ZyklusErgebnis(
        erkannt=False, hinweis=hinweis, periode_s=None, periodizitaet=periodicity, konfidenz=0.0,
        anzahl_gueltig=0, zyklen=[],
        zykluszeit_median=Kennzahl.fehlt(hinweis, "s"), zykluszeit_mittel=Kennzahl.fehlt(hinweis, "s"),
        zykluszeit_std=Kennzahl.fehlt(hinweis, "s"), zykluszeit_vk=k,
        zyklen_pro_schicht=k, zeitanteil_in_zyklen=k,
        t=t, signal=signal, acf_lags_s=lags, acf=acf,
    )


def detect_cycles_features(t: np.ndarray, x: np.ndarray, mask: np.ndarray, rate: float, shift_min: float, cfg: CycleConfig = CycleConfig()) -> ZyklusErgebnis:
    """Cycle detection on a standardised feature matrix (see features())."""
    signal = _first_component(x, mask)
    coverage = float(mask.mean()) if mask.size else 0.0
    period, periodicity, acf, weights = dominant_period(x, mask, rate, cfg)
    lags = np.arange(len(acf)) / rate
    if coverage < cfg.min_coverage:
        return _kein_zyklus(t, signal, lags, acf, periodicity, "Zu wenig Bilder mit erkannter Person")
    if period is None:
        return _kein_zyklus(t, signal, lags, acf, periodicity)

    length = int(round(period * rate))
    x = smooth_for_period(x, mask, length)
    start = _best_repeating_window(x, mask, length, weights)
    if start is None:
        return _kein_zyklus(t, signal, lags, acf, periodicity)
    template = x[start : start + length]
    corr = template_correlation(x, mask, template, weights)
    bounds = _boundaries(corr, length, cfg)
    if len(bounds) >= 2:
        # refine: mean of the found windows as template
        windows = [x[b : b + length] for b in bounds if b + length <= len(x) and mask[b : b + length].all()]
        if len(windows) >= 2:
            template = np.mean(windows, axis=0)
            corr = template_correlation(x, mask, template, weights)
            bounds = _boundaries(corr, length, cfg)

    zyklen = _zyklen(t, mask, corr, bounds, rate, cfg)
    gueltig = [z for z in zyklen if z.gueltig]
    if len(gueltig) < cfg.min_cycles:
        return _kein_zyklus(t, signal, lags, acf, periodicity)

    d = np.array([z.dauer_s for z in gueltig])
    sim = float(np.mean([z.aehnlichkeit for z in gueltig]))
    valid_share = len(gueltig) / len([z for z in zyklen if z.art == "zyklus"])
    konf = _konfidenz(periodicity, sim, valid_share, coverage)
    duration = float(mask.sum()) / rate  # time with a person in view
    in_cycles = float(d.sum()) / duration if duration > 0 else 0.0
    median, mean, std = float(np.median(d)), float(d.mean()), float(d.std(ddof=1)) if len(d) > 1 else 0.0
    per_shift = len(gueltig) / duration * shift_min * 60 if duration > 0 else None
    vk_quality = konf if len(gueltig) >= cfg.min_cycles_cv else 0.0
    return ZyklusErgebnis(
        erkannt=True, hinweis=None, periode_s=period, periodizitaet=periodicity, konfidenz=konf,
        anzahl_gueltig=len(gueltig), zyklen=zyklen,
        zykluszeit_median=Kennzahl.bewertet(median, konf, cfg.reliable, "s"),
        zykluszeit_mittel=Kennzahl.bewertet(mean, konf, cfg.reliable, "s"),
        zykluszeit_std=Kennzahl.bewertet(std, vk_quality, cfg.reliable, "s"),
        zykluszeit_vk=Kennzahl.bewertet(std / mean if mean > 0 else None, vk_quality, cfg.reliable),
        zyklen_pro_schicht=Kennzahl.bewertet(per_shift, konf, cfg.reliable),
        zeitanteil_in_zyklen=Kennzahl.bewertet(min(1.0, in_cycles), konf, cfg.reliable),
        t=t, signal=signal, acf_lags_s=lags, acf=acf,
    )


def _zyklen(t, mask, corr, bounds, rate, cfg, length: int = 0) -> list[Zyklus]:
    if len(bounds) < 2:
        return []
    dur = np.diff(bounds) / rate
    median = float(np.median(dur))
    ends = list(bounds[1:])
    # the last cycle has no following start: it ends one median cycle later,
    # if that is still inside the recording
    last_end = bounds[-1] + int(round(median * rate))
    if last_end <= len(mask):
        ends.append(last_end)
    starts = bounds[: len(ends)]
    dur = (np.array(ends) - starts) / rate
    med_frames = int(round(median * rate))

    def zeit(i: int) -> float:
        return float(t[i]) if i < len(t) else float(t[-1] + 1 / rate)

    out = []
    for i, (a, b) in enumerate(zip(starts, ends)):
        b = int(b)
        d = float(dur[i])
        sim = float(corr[a])
        if d > (1 + cfg.duration_tolerance) * median:
            # a typical cycle followed by an interruption (pause, side task)
            c = a + med_frames
            if sim >= cfg.min_similarity and mask[a:c].all():
                out.append(Zyklus(zeit(a), zeit(c), med_frames / rate, sim, True))
            else:
                c = a
            luecke = not mask[c:b].all()
            grund = "Lücke in den Daten" if luecke else "Unterbrechung oder Nebentätigkeit"
            out.append(Zyklus(zeit(c), zeit(b), float(b - c) / rate, float("nan"), False, grund, "unterbrechung"))
            continue
        grund = None
        if d < (1 - cfg.duration_tolerance) * median:
            grund = "zu kurz"
        elif sim < cfg.min_similarity:
            grund = "weicht vom typischen Ablauf ab"
        elif not mask[a:b].all():
            grund = "Lücke in den Daten"
        out.append(Zyklus(zeit(a), zeit(b), d, sim, grund is None, grund))
    return out


def _first_component(x: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """First principal component of the features, for plots."""
    out = np.full(len(mask), np.nan)
    if x.shape[1] == 0 or mask.sum() < 3:
        return out
    v = x[mask]
    _, _, vt = np.linalg.svd(v - v.mean(axis=0), full_matrices=False)
    out[mask] = v @ vt[0]
    return out


def detect_cycles(prep: Prepared, shift_min: float = 480.0, cfg: CycleConfig = CycleConfig()) -> ZyklusErgebnis:
    x, mask = features(prep)
    return detect_cycles_features(prep.t, x, mask, prep.rate_hz, shift_min, cfg)

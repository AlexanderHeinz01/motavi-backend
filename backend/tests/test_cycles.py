"""Cycle detection (S2, STECKBRIEF_MODUL §4.1) with synthetic signals:
known period with noise, varying cycle length, interruptions, data gaps,
aperiodic movement."""
import numpy as np
import pytest

from backend.app.services.workplace.cycles import KEIN_ZYKLUS, CycleConfig, detect_cycles, detect_cycles_features, standardise
from backend.app.services.workplace.quality import NICHT_BELASTBAR
from backend.tests.prepared import prepared_from_wrists
from backend.tests.signals import aperiodic, pause, periodic

RATE = 15.0


def run(raw, shift_min=480.0, cfg=CycleConfig()):
    x, m = standardise(raw)
    return detect_cycles_features(np.arange(len(raw)) / RATE, x, m, RATE, shift_min, cfg)


@pytest.mark.parametrize("period", [3.5, 8.0, 12.0, 38.4, 60.0, 150.0])
@pytest.mark.parametrize("noise", [0.1, 0.4])
def test_known_period_within_5_percent(period, noise):
    n = 10 if period < 60 else (6 if period < 120 else 5)
    t, raw, _ = periodic(period, n, rate=RATE, noise=noise, seed=int(period))
    r = run(raw)
    assert r.erkannt
    assert r.zykluszeit_median.belastbar
    assert r.zykluszeit_median.wert == pytest.approx(period, rel=0.05)
    assert r.periode_s == pytest.approx(period, rel=0.05)
    # complete cycles only: the template may start mid-cycle, so one cycle can be split at the edges
    assert n - 1 <= r.anzahl_gueltig <= n


def test_varying_cycle_length_median_and_cv():
    t, raw, durations = periodic(20.0, 15, rate=RATE, jitter=0.1, noise=0.2, seed=7)
    r = run(raw)
    assert r.zykluszeit_median.wert == pytest.approx(float(np.median(durations)), rel=0.05)
    true_cv = float(np.std(durations, ddof=1) / np.mean(durations))
    assert r.zykluszeit_vk.belastbar
    assert r.zykluszeit_vk.wert == pytest.approx(true_cv, abs=0.03)


def test_interruption_is_marked_and_not_counted():
    _, a, _ = periodic(12.0, 6, rate=RATE, noise=0.2, seed=4)
    _, c, _ = periodic(12.0, 6, rate=RATE, noise=0.2, seed=5)
    raw = np.vstack([a, pause(45.0, RATE), c])
    r = run(raw)
    assert r.zykluszeit_median.wert == pytest.approx(12.0, rel=0.05)
    pausen = [z for z in r.zyklen if z.art == "unterbrechung"]
    assert len(pausen) == 1 and pausen[0].dauer_s == pytest.approx(45.0, abs=12.0)
    # time share in cycles: 144 s of cycles in 189 s
    assert r.zeitanteil_in_zyklen.wert == pytest.approx(144 / 189, abs=0.1)


def test_gap_in_data_marks_affected_cycle():
    _, raw, _ = periodic(12.0, 10, rate=RATE, noise=0.2, seed=2)
    raw[int(40 * RATE) : int(44 * RATE)] = np.nan  # 4 s without a person
    r = run(raw)
    assert r.zykluszeit_median.wert == pytest.approx(12.0, rel=0.05)
    assert any(z.grund == "Lücke in den Daten" for z in r.zyklen)
    assert not any(z.grund == "Unterbrechung oder Nebentätigkeit" for z in r.zyklen)
    assert all(not (z.start_s < 42 < z.ende_s) or not z.gueltig for z in r.zyklen)


def test_two_similar_sub_movements_give_the_full_cycle():
    # a cycle with two grips: the half period must not win
    t, raw, _ = periodic(16.0, 8, rate=RATE, noise=0.15, seed=9)
    phase = (t % 16.0) / 16.0
    raw[:, 2] = np.exp(-(((phase - 0.25) % 1) ** 2) / 0.003) + np.exp(-(((phase - 0.75) % 1) ** 2) / 0.003)
    r = run(raw)
    assert r.zykluszeit_median.wert == pytest.approx(16.0, rel=0.05)


@pytest.mark.parametrize("seed", range(5))
def test_aperiodic_gives_fallback(seed):
    _, raw = aperiodic(240.0, RATE, seed=seed)
    r = run(raw)
    assert not r.erkannt and r.hinweis == KEIN_ZYKLUS
    for k in (r.zykluszeit_median, r.zykluszeit_vk, r.zyklen_pro_schicht, r.zeitanteil_in_zyklen):
        assert k.wert is None and not k.belastbar and k.anzeige == "nicht belastbar messbar"


def test_standing_still_gives_fallback():
    r = run(pause(120.0, RATE))
    assert not r.erkannt


def test_too_few_cycles_gives_fallback():
    _, raw, _ = periodic(30.0, 2, rate=RATE, noise=0.1)
    assert not run(raw).erkannt


def test_low_coverage_gives_fallback_with_reason():
    _, raw, _ = periodic(10.0, 12, rate=RATE, noise=0.1)
    raw[::2] = np.nan  # every second frame without a person
    r = run(raw)
    assert not r.erkannt and r.hinweis == "Zu wenig Bilder mit erkannter Person"


def test_noisy_cycles_have_lower_quality():
    _, clean, _ = periodic(12.0, 10, rate=RATE, noise=0.1, seed=1)
    _, noisy, _ = periodic(12.0, 10, rate=RATE, noise=1.2, seed=1)
    a, b = run(clean), run(noisy)
    assert a.konfidenz > b.konfidenz


def test_quality_threshold_hides_values():
    _, raw, _ = periodic(12.0, 10, rate=RATE, noise=0.1)
    r = run(raw, cfg=CycleConfig(reliable=0.999))
    assert r.erkannt and r.zykluszeit_median.wert is None and r.zykluszeit_median.grund == NICHT_BELASTBAR


def test_cycles_per_shift_extrapolated():
    _, raw, _ = periodic(12.0, 10, rate=RATE, noise=0.1, seed=3)
    r = run(raw, shift_min=480)
    # about one cycle per 12 s of recording
    assert r.zyklen_pro_schicht.wert == pytest.approx(480 * 60 / 12.0, rel=0.12)


def test_one_moving_hand_among_noise_channels():
    # only the left hand works, everything else is noise: must still be found
    _, raw, _ = periodic(10.0, 12, rate=RATE, noise=0.1, seed=11)
    rng = np.random.default_rng(0)
    raw[:, 1:] = rng.normal(0, 1, raw[:, 1:].shape)
    r = run(raw)
    assert r.erkannt and r.zykluszeit_median.wert == pytest.approx(10.0, rel=0.05)


def test_end_to_end_with_prepared_pose():
    t = np.arange(int(120 * RATE)) / RATE
    phase = (t % 8.0) / 8.0
    lx = 0.4 + 0.5 * np.sin(2 * np.pi * phase)
    ly = -0.4 + 0.3 * np.cos(2 * np.pi * phase)
    prep = prepared_from_wrists(t, (lx, ly), (0.3 + 0 * t, 0.1 + 0 * t), noise=0.02)
    r = detect_cycles(prep, shift_min=480)
    assert r.erkannt and r.zykluszeit_median.wert == pytest.approx(8.0, rel=0.05)


@pytest.mark.parametrize("period", [3.0, 5.0, 38.4, 120.0])
@pytest.mark.parametrize("seed", range(3))
def test_strong_noise(period, seed):
    n = 10 if period < 60 else 6
    _, raw, _ = periodic(period, n, rate=RATE, noise=0.6, seed=seed + 100)
    r = run(raw)
    assert r.erkannt and r.zykluszeit_median.wert == pytest.approx(period, rel=0.05)


def test_hidden_far_hand_does_not_block_detection():
    t = np.arange(int(120 * RATE)) / RATE
    phase = (t % 8.0) / 8.0
    lx = 0.4 + 0.5 * np.sin(2 * np.pi * phase)
    ly = -0.4 + 0.3 * np.cos(2 * np.pi * phase)
    prep = prepared_from_wrists(t, (lx, ly), (0.3 + 0 * t, 0.1 + 0 * t), noise=0.02)
    prep.rel[: int(0.8 * len(t)), list(prep.names).index("right_wrist")] = np.nan  # hidden 80 % of the time
    r = detect_cycles(prep)
    assert r.erkannt and r.zykluszeit_median.wert == pytest.approx(8.0, rel=0.05)

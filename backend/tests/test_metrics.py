from __future__ import annotations

import numpy as np
import pytest

from evaluation.metrics import (
    bpcer_at_apcer,
    equal_error_rate,
    error_rates,
    pad_metrics,
    roc_curve,
    threshold_at_far,
)


def test_error_rates() -> None:
    rates = error_rates([0.9, 0.8, 0.3], [0.1, 0.5, 0.85], threshold=0.5)
    assert rates.frr == pytest.approx(1 / 3)
    assert rates.far == pytest.approx(2 / 3)


def test_perfect_separation_has_zero_eer() -> None:
    result = equal_error_rate([0.8, 0.9, 1.0], [0.0, 0.1, 0.2])
    assert result.eer == pytest.approx(0.0)
    assert 0.2 <= result.threshold <= 0.8


def test_eer_symmetric_overlap() -> None:
    rng = np.random.default_rng(42)
    genuine = rng.normal(1.0, 1.0, 20_000)
    impostor = rng.normal(-1.0, 1.0, 20_000)
    result = equal_error_rate(genuine, impostor)
    # analytic EER for two unit Gaussians 2 sigma apart = Phi(-1) ≈ 0.1587
    assert result.eer == pytest.approx(0.1587, abs=0.01)
    assert result.threshold == pytest.approx(0.0, abs=0.05)


def test_roc_monotonic() -> None:
    rng = np.random.default_rng(1)
    _, far, frr = roc_curve(rng.random(100), rng.random(100))
    assert np.all(np.diff(far) <= 0)
    assert np.all(np.diff(frr) >= 0)
    assert far[-1] == 0.0 and frr[-1] == 1.0


def test_threshold_at_far() -> None:
    impostor = np.linspace(0, 1, 101)
    threshold = threshold_at_far(impostor, 0.05)
    assert error_rates([1.0], impostor, threshold).far <= 0.05
    assert error_rates([1.0], impostor, threshold - 0.011).far > 0.05


def test_pad_metrics() -> None:
    report = pad_metrics(
        bona_fide=[0.9, 0.95, 0.4, 0.8],
        attacks={"print": [0.1, 0.2, 0.75], "replay": [0.05, 0.1]},
        threshold=0.7,
    )
    assert report.bpcer == pytest.approx(0.25)
    assert report.apcer_per_type == {"print": pytest.approx(1 / 3), "replay": 0.0}
    assert report.apcer == pytest.approx(1 / 3)
    assert report.acer == pytest.approx((1 / 3 + 0.25) / 2)


def test_bpcer_at_apcer() -> None:
    bpcer, threshold = bpcer_at_apcer([0.9, 0.6, 0.3], np.linspace(0, 0.5, 100), 0.05)
    assert threshold > 0.45
    assert bpcer == pytest.approx(1 / 3)

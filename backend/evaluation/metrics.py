from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ErrorRates:
    threshold: float
    far: float
    frr: float


@dataclass(frozen=True, slots=True)
class EerResult:
    eer: float
    threshold: float


def _as_array(values: Sequence[float] | np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).ravel()
    if array.size == 0:
        raise ValueError("Empty score list")
    return array


def error_rates(
    genuine: Sequence[float], impostor: Sequence[float], threshold: float
) -> ErrorRates:
    g, i = _as_array(genuine), _as_array(impostor)
    return ErrorRates(
        threshold=threshold,
        far=float(np.mean(i >= threshold)),
        frr=float(np.mean(g < threshold)),
    )


def roc_curve(
    genuine: Sequence[float], impostor: Sequence[float]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    g, i = np.sort(_as_array(genuine)), np.sort(_as_array(impostor))
    thresholds = np.unique(np.concatenate([g, i, [np.inf]]))
    far = 1.0 - np.searchsorted(i, thresholds, side="left") / i.size
    frr = np.searchsorted(g, thresholds, side="left") / g.size
    return thresholds, far, frr


def equal_error_rate(genuine: Sequence[float], impostor: Sequence[float]) -> EerResult:
    thresholds, far, frr = roc_curve(genuine, impostor)
    diff = far - frr
    idx = int(np.argmax(diff <= 0))
    if idx == 0:
        return EerResult(eer=float((far[0] + frr[0]) / 2), threshold=float(thresholds[0]))
    d0, d1 = diff[idx - 1], diff[idx]
    w = d0 / (d0 - d1) if d0 != d1 else 0.0
    eer = (
        far[idx - 1] + w * (far[idx] - far[idx - 1]) + frr[idx - 1] + w * (frr[idx] - frr[idx - 1])
    ) / 2
    t1 = thresholds[idx] if np.isfinite(thresholds[idx]) else thresholds[idx - 1]
    threshold = thresholds[idx - 1] + w * (t1 - thresholds[idx - 1])
    return EerResult(eer=float(eer), threshold=float(threshold))


def threshold_at_far(impostor: Sequence[float], target_far: float) -> float:
    i = np.sort(_as_array(impostor))
    allowed = int(np.floor(target_far * i.size))
    if allowed >= i.size:
        return float(i[0])
    return float(np.nextafter(i[i.size - allowed - 1], np.inf))


@dataclass(frozen=True, slots=True)
class PadReport:
    threshold: float
    apcer: float
    apcer_per_type: dict[str, float]
    bpcer: float
    acer: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def pad_metrics(
    bona_fide: Sequence[float], attacks: Mapping[str, Sequence[float]], threshold: float
) -> PadReport:
    if not attacks:
        raise ValueError("At least one attack type is required")
    bpcer = float(np.mean(_as_array(bona_fide) < threshold))
    per_type = {name: float(np.mean(_as_array(s) >= threshold)) for name, s in attacks.items()}
    apcer = max(per_type.values())
    return PadReport(
        threshold=threshold,
        apcer=apcer,
        apcer_per_type=per_type,
        bpcer=bpcer,
        acer=(apcer + bpcer) / 2,
    )


def bpcer_at_apcer(
    bona_fide: Sequence[float], attack_scores: Sequence[float], target_apcer: float
) -> tuple[float, float]:
    threshold = threshold_at_far(attack_scores, target_apcer)
    return float(np.mean(_as_array(bona_fide) < threshold)), threshold

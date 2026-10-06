"""Matplotlib figures for the technical report (PNG + PDF for LaTeX)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

from evaluation.metrics import roc_curve

plt.rcParams.update({"figure.dpi": 120, "savefig.bbox": "tight", "font.size": 10})


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path.with_suffix(".png"))
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)


def score_histogram(
    groups: Mapping[str, Sequence[float]],
    path: Path,
    *,
    threshold: float | None = None,
    xlabel: str = "Skóre",
    title: str = "",
) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    bins = np.linspace(
        min(min(v) for v in groups.values()), max(max(v) for v in groups.values()), 50
    )
    for label, values in groups.items():
        ax.hist(values, bins=bins, alpha=0.55, density=True, label=f"{label} (n={len(values)})")
    if threshold is not None:
        ax.axvline(
            threshold, color="k", linestyle="--", linewidth=1, label=f"prah = {threshold:.3f}"
        )
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Hustota")
    if title:
        ax.set_title(title)
    ax.legend()
    _save(fig, path)


def far_frr_curve(
    genuine: Sequence[float],
    impostor: Sequence[float],
    path: Path,
    *,
    far_label: str = "FAR",
    frr_label: str = "FRR",
    eer_threshold: float | None = None,
) -> None:
    thresholds, far, frr = roc_curve(genuine, impostor)
    finite = np.isfinite(thresholds)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(thresholds[finite], far[finite] * 100, label=far_label)
    ax.plot(thresholds[finite], frr[finite] * 100, label=frr_label)
    if eer_threshold is not None:
        ax.axvline(eer_threshold, color="k", linestyle=":", linewidth=1, label="EER")
    ax.set_xlabel("Prah")
    ax.set_ylabel("Chybovosť [%]")
    ax.legend()
    ax.grid(alpha=0.3)
    _save(fig, path)


def roc_plot(
    curves: Mapping[str, tuple[Sequence[float], Sequence[float]]],
    path: Path,
    *,
    far_label: str = "FAR",
) -> None:
    """ROC: genuine acceptance rate (1-FRR) vs. FAR on a log axis."""
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    for label, (genuine, impostor) in curves.items():
        _, far, frr = roc_curve(genuine, impostor)
        ax.plot(np.clip(far, 1e-5, 1), 1 - frr, label=label)
    ax.set_xscale("log")
    ax.set_xlim(1e-4, 1)
    ax.set_xlabel(f"{far_label} (log)")
    ax.set_ylabel("1 - FRR")
    ax.grid(alpha=0.3, which="both")
    ax.legend(loc="lower right")
    _save(fig, path)


def det_plot(
    curves: Mapping[str, tuple[Sequence[float], Sequence[float]]],
    path: Path,
    *,
    xlabel: str = "FAR [%]",
    ylabel: str = "FRR [%]",
) -> None:
    """Detection Error Trade-off on normal-deviate axes (ISO/IEC 19795-1)."""
    ticks = np.array([0.001, 0.01, 0.05, 0.2, 0.5])
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    for label, (genuine, impostor) in curves.items():
        _, far, frr = roc_curve(genuine, impostor)
        eps = 1e-4
        ax.plot(
            norm.ppf(np.clip(far, eps, 1 - eps)), norm.ppf(np.clip(frr, eps, 1 - eps)), label=label
        )
    positions = norm.ppf(ticks)
    labels = [f"{t * 100:g}" for t in ticks]
    ax.set_xticks(positions, labels)
    ax.set_yticks(positions, labels)
    ax.set_xlim(positions[0], positions[-1])
    ax.set_ylim(positions[0], positions[-1])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3)
    ax.legend()
    _save(fig, path)


def bar_chart(values: Mapping[str, float], path: Path, *, ylabel: str, title: str = "") -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    names = list(values)
    ax.bar(names, [values[n] for n in names], color="#3b6ea5")
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    _save(fig, path)

"""Verification accuracy of the face recogniser (genuine vs. impostor comparisons).

Data sources:
  --lfw          Labeled Faces in the Wild, official 10-fold "pairs" protocol
                 (downloaded automatically via scikit-learn, ~230 MB)
  --dir PATH     own dataset: PATH/<identity>/<image>.jpg

Usage::

    python -m evaluation.evaluate_recognition --lfw
    python -m evaluation.evaluate_recognition --dir data/faces --max-impostors 20000
"""

from __future__ import annotations

import argparse
import itertools
import random
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

from app.biometrics.embedder import cosine_similarity
from app.biometrics.engine import BiometricEngine
from evaluation import plots
from evaluation.common import (
    iter_media,
    load_engine,
    markdown_table,
    output_dir,
    percent,
    write_csv,
    write_json,
)
from evaluation.metrics import equal_error_rate, error_rates, threshold_at_far

Pair = tuple[np.ndarray, np.ndarray, bool]


def embed(engine: BiometricEngine, image: np.ndarray) -> np.ndarray | None:
    """Embedding of the largest face; no quality gate (we measure the recogniser itself)."""
    faces = engine.detector.detect(image)
    if not faces:
        return None
    return engine.embedder.embed(image, faces[0])


def lfw_pairs() -> Iterator[Pair]:
    from sklearn.datasets import fetch_lfw_pairs

    data = fetch_lfw_pairs(subset="10_folds", color=True, resize=1.0, slice_=None)
    for (a, b), label in zip(data.pairs, data.target, strict=True):
        yield _to_bgr(a), _to_bgr(b), bool(label)


def _to_bgr(image: np.ndarray) -> np.ndarray:
    scale = 255.0 if image.max() <= 1.0 else 1.0
    rgb = np.clip(image * scale, 0, 255).astype(np.uint8)
    padded = cv2.copyMakeBorder(rgb, 40, 40, 40, 40, cv2.BORDER_REPLICATE)  # context for detector
    return cv2.cvtColor(padded, cv2.COLOR_RGB2BGR)


def folder_scores(
    engine: BiometricEngine, root: Path, max_impostors: int, seed: int
) -> tuple[list[float], list[float], int, int]:
    embeddings: dict[str, list[np.ndarray]] = {}
    attempted = failed = 0
    for identity_dir in tqdm(sorted(p for p in root.iterdir() if p.is_dir()), desc="embedding"):
        for _, image in iter_media(identity_dir):
            attempted += 1
            vector = embed(engine, image)
            if vector is None:
                failed += 1
                continue
            embeddings.setdefault(identity_dir.name, []).append(vector)

    genuine = [
        cosine_similarity(a, b)
        for vectors in embeddings.values()
        for a, b in itertools.combinations(vectors, 2)
    ]
    flat = [(name, v) for name, vectors in embeddings.items() for v in vectors]
    rng = random.Random(seed)
    impostor: list[float] = []
    candidates = [
        (i, j)
        for i in range(len(flat))
        for j in range(i + 1, len(flat))
        if flat[i][0] != flat[j][0]
    ]
    for i, j in rng.sample(candidates, min(max_impostors, len(candidates))):
        impostor.append(cosine_similarity(flat[i][1], flat[j][1]))
    return genuine, impostor, attempted, failed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--lfw", action="store_true")
    source.add_argument("--dir", type=Path)
    parser.add_argument("--max-impostors", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    engine, settings = load_engine()
    genuine: list[float] = []
    impostor: list[float] = []
    if args.lfw:
        dataset = "LFW (10 folds, 6000 pairs)"
        attempted = failed = 0
        for a, b, same in tqdm(lfw_pairs(), total=6000, desc="LFW pairs"):
            attempted += 2
            ea, eb = embed(engine, a), embed(engine, b)
            failed += (ea is None) + (eb is None)
            if ea is None or eb is None:
                continue
            (genuine if same else impostor).append(cosine_similarity(ea, eb))
    else:
        dataset = str(args.dir)
        genuine, impostor, attempted, failed = folder_scores(
            engine, args.dir, args.max_impostors, args.seed
        )

    out = output_dir(args.out, "recognition")
    threshold = settings.matching.threshold
    eer = equal_error_rate(genuine, impostor)
    at_system = error_rates(genuine, impostor, threshold)
    operating_points = []
    for target in (0.01, 0.001):
        t = threshold_at_far(impostor, target)
        operating_points.append((f"FAR ≤ {target:g}", t, error_rates(genuine, impostor, t)))

    summary = {
        "dataset": dataset,
        "model": settings.models.recognizer_version,
        "samples_attempted": attempted,
        "failure_to_acquire": failed / attempted if attempted else 0.0,
        "genuine_comparisons": len(genuine),
        "impostor_comparisons": len(impostor),
        "eer": eer.eer,
        "eer_threshold": eer.threshold,
        "system_threshold": threshold,
        "far_at_system_threshold": at_system.far,
        "frr_at_system_threshold": at_system.frr,
        "operating_points": [
            {"name": n, "threshold": t, "far": r.far, "frr": r.frr} for n, t, r in operating_points
        ],
    }
    write_json(out / "summary.json", summary)
    write_csv(
        out / "scores.csv",
        ["type", "score"],
        [("genuine", s) for s in genuine] + [("impostor", s) for s in impostor],
    )
    rows = [
        ("EER", eer.threshold, percent(eer.eer), percent(eer.eer)),
        ("Systémový prah", threshold, percent(at_system.far), percent(at_system.frr)),
        *[(n, t, percent(r.far), percent(r.frr)) for n, t, r in operating_points],
    ]
    table = markdown_table(["Pracovný bod", "Prah", "FAR", "FRR"], rows)
    (out / "table.md").write_text(
        f"Dataset: {dataset}\n\nFTA: {percent(summary['failure_to_acquire'])}\n\n{table}",
        encoding="utf-8",
    )

    plots.score_histogram(
        {"genuine": genuine, "impostor": impostor},
        out / "score_distribution",
        threshold=threshold,
        xlabel="Kosínusová podobnosť",
    )
    plots.far_frr_curve(genuine, impostor, out / "far_frr", eer_threshold=eer.threshold)
    plots.roc_plot({"SFace": (genuine, impostor)}, out / "roc")
    plots.det_plot({"SFace": (genuine, impostor)}, out / "det")

    print(table)
    print(f"Results written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

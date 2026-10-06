"""Latency benchmark of the individual pipeline stages on CPU.

Usage::

    python -m evaluation.benchmark --image path/to/face.jpg --runs 200
"""

from __future__ import annotations

import argparse
import platform
import time
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

from app.biometrics.liveness.pose import estimate_head_pose
from evaluation import plots
from evaluation.common import load_engine, markdown_table, output_dir, write_json


def measure(fn: Callable[[], object], runs: int, warmup: int = 10) -> dict[str, float]:
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    arr = np.array(samples)
    return {
        "mean_ms": float(arr.mean()),
        "p50_ms": float(np.percentile(arr, 50)),
        "p95_ms": float(np.percentile(arr, 95)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    image = cv2.imread(str(args.image))
    if image is None:
        parser.error(f"Cannot read {args.image}")
    engine, settings = load_engine()
    faces = engine.detector.detect(image)
    if not faces:
        parser.error("No face detected in the benchmark image")
    face = faces[0]

    stages: dict[str, Callable[[], object]] = {
        "Detekcia (YuNet)": lambda: engine.detector.detect(image),
        "Kvalita vzorky": lambda: engine.quality.assess(image, faces),
        "Odhad pózy hlavy": lambda: estimate_head_pose(face.landmarks),
        "Pasívna živosť (2× MiniFASNet)": lambda: engine.passive_liveness.score(image, face),
        "Extrakcia príznakov (SFace)": lambda: engine.embedder.embed(image, face),
        "Celý snímok": lambda: engine.analyze_frame(image),
    }
    results = {name: measure(fn, args.runs) for name, fn in stages.items()}
    steps = settings.active_liveness.steps + 1  # center + random actions
    per_session = results["Celý snímok"]["mean_ms"] * steps * settings.challenge.frames_per_step

    out = output_dir(args.out, "benchmark")
    write_json(
        out / "summary.json",
        {
            "image": str(args.image),
            "resolution": list(image.shape[:2]),
            "runs": args.runs,
            "cpu": platform.processor(),
            "python": platform.python_version(),
            "stages": results,
            "estimated_session_processing_ms": per_session,
        },
    )
    table = markdown_table(
        ["Fáza", "Priemer [ms]", "Medián [ms]", "P95 [ms]"],
        [(n, r["mean_ms"], r["p50_ms"], r["p95_ms"]) for n, r in results.items()],
    )
    (out / "table.md").write_text(table, encoding="utf-8")
    plots.bar_chart(
        {n: r["mean_ms"] for n, r in results.items() if n != "Celý snímok"},
        out / "latency",
        ylabel="Čas [ms]",
    )
    print(table)
    print(f"Estimated server time per session: {per_session:.0f} ms")
    print(f"Results written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

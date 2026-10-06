"""Presentation attack detection (passive anti-spoofing) evaluation – ISO/IEC 30107-3.

Expected dataset layout (images and/or videos)::

    DATA/
      bona_fide/            live faces
      attack/
        print/              printed photos
        replay/             phone / tablet / monitor replays
        mask/ ...           any other attack species (sub-folder name = type)

``evaluation.capture_dataset`` records such a dataset with a webcam. Public
datasets (CelebA-Spoof, Replay-Attack, OULU-NPU) can be arranged the same way.

Usage::

    python -m evaluation.evaluate_pad --dir data/pad
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tqdm import tqdm

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
from evaluation.metrics import bpcer_at_apcer, equal_error_rate, pad_metrics


def score_folder(engine, folder: Path, stride: int) -> tuple[list[tuple[str, float]], int, int]:  # type: ignore[no-untyped-def]
    scores: list[tuple[str, float]] = []
    attempted = failed = 0
    for sample_id, image in tqdm(list(iter_media(folder, stride)), desc=folder.name, leave=False):
        attempted += 1
        faces = engine.detector.detect(image)
        if not faces:
            failed += 1
            continue
        scores.append((sample_id, engine.passive_liveness.score(image, faces[0])))
    return scores, attempted, failed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--video-stride", type=int, default=5)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    bona_dir, attack_dir = args.dir / "bona_fide", args.dir / "attack"
    if not bona_dir.is_dir() or not attack_dir.is_dir():
        parser.error("DATA must contain 'bona_fide/' and 'attack/<type>/' folders")

    engine, settings = load_engine()
    bona, attempted, failed = score_folder(engine, bona_dir, args.video_stride)
    attacks: dict[str, list[tuple[str, float]]] = {}
    for type_dir in sorted(p for p in attack_dir.iterdir() if p.is_dir()):
        scores, a, f = score_folder(engine, type_dir, args.video_stride)
        attempted, failed = attempted + a, failed + f
        if scores:
            attacks[type_dir.name] = scores
    if not bona or not attacks:
        parser.error("No faces detected in bona fide or attack samples")

    bona_scores = [s for _, s in bona]
    attack_scores = {name: [s for _, s in items] for name, items in attacks.items()}
    all_attacks = [s for values in attack_scores.values() for s in values]

    threshold = settings.passive_liveness.threshold
    report = pad_metrics(bona_scores, attack_scores, threshold)
    eer = equal_error_rate(bona_scores, all_attacks)
    bpcer20, t20 = bpcer_at_apcer(bona_scores, all_attacks, 0.05)
    bpcer100, t100 = bpcer_at_apcer(bona_scores, all_attacks, 0.01)

    out = output_dir(args.out, "pad")
    write_json(
        out / "summary.json",
        {
            "dataset": str(args.dir),
            "samples_attempted": attempted,
            "failure_to_acquire": failed / attempted if attempted else 0.0,
            "bona_fide_samples": len(bona_scores),
            "attack_samples": {k: len(v) for k, v in attack_scores.items()},
            "system_threshold": report.to_dict(),
            "eer": eer.eer,
            "eer_threshold": eer.threshold,
            "bpcer20": {"bpcer": bpcer20, "threshold": t20},
            "bpcer100": {"bpcer": bpcer100, "threshold": t100},
        },
    )
    write_csv(
        out / "scores.csv",
        ["class", "sample", "live_score"],
        [("bona_fide", i, s) for i, s in bona]
        + [(name, i, s) for name, items in attacks.items() for i, s in items],
    )

    rows = [
        *[(f"APCER ({name})", percent(v)) for name, v in report.apcer_per_type.items()],
        ("APCER (max)", percent(report.apcer)),
        ("BPCER", percent(report.bpcer)),
        ("ACER", percent(report.acer)),
        ("EER", percent(eer.eer)),
        ("BPCER20 (APCER = 5 %)", percent(bpcer20)),
        ("BPCER100 (APCER = 1 %)", percent(bpcer100)),
    ]
    table = markdown_table(["Metrika", f"Hodnota (prah {threshold:.2f})"], rows)
    (out / "table.md").write_text(table, encoding="utf-8")

    plots.score_histogram(
        {"bona fide": bona_scores, **attack_scores},
        out / "score_distribution",
        threshold=threshold,
        xlabel="Skóre živosti (MiniFASNet ensemble)",
    )
    plots.far_frr_curve(
        bona_scores,
        all_attacks,
        out / "apcer_bpcer",
        far_label="APCER",
        frr_label="BPCER",
        eer_threshold=eer.threshold,
    )
    plots.det_plot(
        {name: (bona_scores, values) for name, values in attack_scores.items()},
        out / "det",
        xlabel="APCER [%]",
        ylabel="BPCER [%]",
    )
    plots.bar_chart(
        {name: v * 100 for name, v in report.apcer_per_type.items()},
        out / "apcer_per_type",
        ylabel="APCER [%]",
    )
    print(table)
    print(f"Results written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

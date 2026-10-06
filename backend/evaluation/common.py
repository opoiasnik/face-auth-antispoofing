"""Helpers shared by the evaluation scripts."""

from __future__ import annotations

import csv
import json
import logging
from collections.abc import Iterable, Iterator, Sequence
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from app.biometrics.engine import BiometricEngine
from app.biometrics.factory import build_engine
from app.core.config import Settings

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def load_engine(settings: Settings | None = None) -> tuple[BiometricEngine, Settings]:
    logging.getLogger().setLevel(logging.WARNING)
    settings = settings or Settings()
    return build_engine(settings), settings


def output_dir(base: Path | None, name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = (base or DEFAULT_REPORTS_DIR) / f"{name}-{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def iter_media(folder: Path, video_stride: int = 5) -> Iterator[tuple[str, np.ndarray]]:
    """Yield ``(sample_id, BGR image)`` for every image and every n-th video frame."""
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        suffix = path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is not None:
                yield str(path.relative_to(folder)), image
        elif suffix in VIDEO_EXTENSIONS:
            capture = cv2.VideoCapture(str(path))
            index = 0
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if index % video_stride == 0:
                    yield f"{path.relative_to(folder)}#{index}", frame
                index += 1
            capture.release()


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=float), encoding="utf-8")


def write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def markdown_table(header: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    def fmt(value: object) -> str:
        return f"{value:.4f}" if isinstance(value, float) else str(value)

    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def percent(value: float) -> str:
    return f"{value * 100:.2f} %"

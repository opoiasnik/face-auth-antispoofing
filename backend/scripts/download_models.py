from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DEST = Path(__file__).resolve().parents[1] / "models"


@dataclass(frozen=True)
class ModelFile:
    name: str
    url: str
    min_bytes: int
    sha256: str


MODELS = (
    ModelFile(
        "face_detection_yunet_2023mar.onnx",
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/"
        "face_detection_yunet_2023mar.onnx",
        200_000,
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    ModelFile(
        "face_recognition_sface_2021dec.onnx",
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/"
        "face_recognition_sface_2021dec.onnx",
        30_000_000,
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    ),
    ModelFile(
        "MiniFASNetV2.onnx",
        "https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV2.onnx",
        1_000_000,
        "b32929adc2d9c34b9486f8c4c7bc97c1b69bc0ea9befefc380e4faae4e463907",
    ),
    ModelFile(
        "MiniFASNetV1SE.onnx",
        "https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV1SE.onnx",
        1_000_000,
        "ebab7f90c7833fbccd46d3a555410e78d969db5438e169b6524be444862b3676",
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(model: ModelFile, dest: Path, force: bool) -> Path:
    target = dest / model.name
    if target.exists() and target.stat().st_size >= model.min_bytes and not force:
        if _sha256(target) != model.sha256:
            raise RuntimeError(f"{model.name}: SHA-256 mismatch; use --force to re-download")
        print(f"[skip] {model.name} already present (SHA-256 verified)")
        return target
    tmp = target.with_suffix(".part")
    print(f"[get ] {model.name}")
    request = urllib.request.Request(model.url, headers={"User-Agent": "face-auth-setup"})
    with urllib.request.urlopen(request, timeout=120) as response, tmp.open("wb") as fh:
        while chunk := response.read(1 << 20):
            fh.write(chunk)
    size = tmp.stat().st_size
    if size < model.min_bytes:
        tmp.unlink()
        raise RuntimeError(f"{model.name}: downloaded file too small ({size} B) - Git LFS pointer?")
    if _sha256(tmp) != model.sha256:
        tmp.unlink()
        raise RuntimeError(f"{model.name}: SHA-256 mismatch in downloaded model")
    tmp.replace(target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    args = parser.parse_args()

    args.dest.mkdir(parents=True, exist_ok=True)
    lines = []
    for model in MODELS:
        path = download(model, args.dest, args.force)
        lines.append(f"{_sha256(path)}  {model.name}")
    (args.dest / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())

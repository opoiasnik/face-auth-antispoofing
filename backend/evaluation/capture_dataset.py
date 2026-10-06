"""Record a PAD dataset with a webcam.

Run once per presentation type, e.g.::

    python -m evaluation.capture_dataset --out data/pad --label bona_fide --count 150
    python -m evaluation.capture_dataset --out data/pad --label attack/print --count 150
    python -m evaluation.capture_dataset --out data/pad --label attack/replay --count 150

Controls: SPACE starts/pauses recording, Q quits. Only frames with exactly one
detected face are stored. Vary distance, lighting and angle while recording.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2

from evaluation.common import load_engine


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", required=True, help="bona_fide | attack/<type>")
    parser.add_argument("--count", type=int, default=150)
    parser.add_argument("--interval", type=float, default=0.25, help="Seconds between saved frames")
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()

    if args.label != "bona_fide" and not args.label.startswith("attack/"):
        parser.error("label must be 'bona_fide' or 'attack/<type>'")
    target = args.out / args.label
    target.mkdir(parents=True, exist_ok=True)
    engine, _ = load_engine()

    capture = cv2.VideoCapture(args.camera)
    if not capture.isOpened():
        parser.error(f"Cannot open camera {args.camera}")
    saved, recording, last = len(list(target.glob("*.jpg"))), False, 0.0
    goal = saved + args.count
    try:
        while saved < goal:
            ok, frame = capture.read()
            if not ok:
                break
            faces = engine.detector.detect(frame)
            preview = frame.copy()
            for face in faces:
                x, y, w, h = (int(v) for v in face.bbox)
                cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 200, 0), 2)
            if recording and len(faces) == 1 and time.time() - last >= args.interval:
                cv2.imwrite(str(target / f"{int(time.time() * 1000)}.jpg"), frame)
                saved, last = saved + 1, time.time()
            status = "REC" if recording else "PAUSED (space)"
            cv2.putText(
                preview,
                f"{args.label}  {saved}/{goal}  {status}",
                (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255) if recording else (255, 255, 255),
                2,
            )
            cv2.imshow("capture dataset", preview)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(" "):
                recording = not recording
            elif key in (ord("q"), 27):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()
    print(f"{saved} frames in {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

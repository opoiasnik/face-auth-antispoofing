"""Decoding and normalisation of images received from clients."""

from __future__ import annotations

import base64
import binascii

import cv2
import numpy as np

from app.core.errors import InvalidImageError, PayloadTooLargeError

_DATA_URL_SEPARATOR = ";base64,"


def decode_base64_image(data: str, *, max_bytes: int, max_side: int) -> np.ndarray:
    """Decode a base64 (optionally ``data:`` URL) JPEG/PNG into a BGR ``uint8`` array."""
    if _DATA_URL_SEPARATOR in data[:64]:
        data = data.split(_DATA_URL_SEPARATOR, 1)[1]
    # base64 inflates size by 4/3 – reject early before decoding
    if len(data) * 3 // 4 > max_bytes:
        raise PayloadTooLargeError("Image exceeds the maximum allowed size")
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidImageError("Image is not valid base64") from exc
    return decode_image_bytes(raw, max_side=max_side)


def decode_image_bytes(raw: bytes, *, max_side: int) -> np.ndarray:
    buffer = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise InvalidImageError("Unsupported or corrupted image")
    return limit_size(image, max_side)


def limit_size(image: np.ndarray, max_side: int) -> np.ndarray:
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return image
    scale = max_side / longest
    return cv2.resize(image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)

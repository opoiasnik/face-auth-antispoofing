from pathlib import Path

import pytest

from scripts.download_models import ModelFile, _sha256, download


def test_existing_model_hash_is_verified(tmp_path: Path) -> None:
    target = tmp_path / "test.onnx"
    target.write_bytes(b"correct-model")
    model = ModelFile(target.name, "https://invalid.example/model", 1, _sha256(target))
    assert download(model, tmp_path, False) == target
    target.write_bytes(b"corrupt-model")
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        download(model, tmp_path, False)


def test_bad_download_does_not_replace_model(tmp_path: Path, monkeypatch) -> None:
    import io

    target = tmp_path / "test.onnx"
    target.write_bytes(b"existing-model")
    expected = _sha256(target)
    model = ModelFile(target.name, "https://invalid.example/model", 1, expected)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: io.BytesIO(b"bad-download"))
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        download(model, tmp_path, True)
    assert target.read_bytes() == b"existing-model"
    assert not target.with_suffix(".part").exists()

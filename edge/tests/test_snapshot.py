import numpy as np

from src.snapshot import SnapshotEncoder


def _frame():
    return np.zeros((100, 100, 3), dtype=np.uint8)


def test_fits_at_high_quality():
    # encode_fn returns small payload regardless of quality
    enc = SnapshotEncoder(
        max_bytes=1000,
        encode_fn=lambda frame, q: b"x" * 100,
        resize_fn=lambda frame, s: frame,
    )
    result = enc.encode(_frame())
    assert result.present
    assert result.omitted_reason is None
    assert len(result.data) == 100


def test_reduces_quality_to_fit():
    # bytes depend on quality: higher quality = bigger
    def encode_fn(frame, q):
        return b"x" * (q * 20)  # q=90 -> 1800, q=30 -> 600

    enc = SnapshotEncoder(max_bytes=700, min_quality=30, encode_fn=encode_fn,
                          resize_fn=lambda f, s: f)
    result = enc.encode(_frame())
    assert result.present
    assert result.quality == 30
    assert len(result.data) <= 700


def test_downscales_when_quality_insufficient():
    calls = {"scaled": False}

    def resize_fn(frame, scale):
        calls["scaled"] = True
        return frame  # pretend smaller

    def encode_fn(frame, q):
        # full-res always too big; after resize, return small
        return b"x" * (50 if calls["scaled"] else 5000)

    enc = SnapshotEncoder(max_bytes=1000, min_quality=30, encode_fn=encode_fn,
                          resize_fn=resize_fn)
    result = enc.encode(_frame())
    assert result.present
    assert calls["scaled"]


def test_omits_with_flag_as_last_resort():
    # always too big -> omitted with reason
    enc = SnapshotEncoder(
        max_bytes=10,
        min_quality=30,
        encode_fn=lambda f, q: b"x" * 10000,
        resize_fn=lambda f, s: f,
    )
    result = enc.encode(_frame())
    assert not result.present
    assert result.omitted_reason == "exceeds_max_size"

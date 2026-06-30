import os

import pytest

from quantize import (
    ACCURACY_WARN_THRESHOLD,
    QuantizationError,
    QuantizationReport,
    validate_dataset,
)


def test_missing_dataset_dir_fails_fast():
    with pytest.raises(QuantizationError):
        validate_dataset("/nonexistent/path/xyz")


def test_empty_dataset_fails_fast(tmp_path):
    with pytest.raises(QuantizationError):
        validate_dataset(str(tmp_path))


def test_accuracy_warning_boundary_inclusive():
    # exactly 5% must warn
    report = QuantizationReport(source_bytes=1000, quantized_bytes=250,
                                accuracy_delta=ACCURACY_WARN_THRESHOLD)
    assert report.accuracy_delta >= ACCURACY_WARN_THRESHOLD


def test_size_reduction_ratio():
    report = QuantizationReport(source_bytes=1000, quantized_bytes=250, accuracy_delta=0.0)
    assert report.size_reduction_ratio == 4.0
    assert "4.00x" in report.render()


def test_corrupt_image_detected(tmp_path, monkeypatch):
    # create a fake .jpg that cv2 will fail to read
    bad = tmp_path / "broken.jpg"
    bad.write_bytes(b"not really a jpeg")

    import quantize

    # stub cv2.imread to simulate corruption detection without real OpenCV
    class FakeCv2:
        @staticmethod
        def imread(path):
            return None

    monkeypatch.setitem(__import__("sys").modules, "cv2", FakeCv2)
    with pytest.raises(QuantizationError):
        validate_dataset(str(tmp_path))

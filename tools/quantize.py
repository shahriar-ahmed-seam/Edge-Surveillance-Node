"""Model quantization toolchain: float32 ONNX -> INT8 ONNX."""
from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger("tools.quantize")

ACCURACY_WARN_THRESHOLD = 0.05  # 5%, boundary inclusive
_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp")


class QuantizationError(Exception):
    pass


@dataclass
class QuantizationReport:
    source_bytes: int
    quantized_bytes: int
    accuracy_delta: float
    warning: Optional[str] = None

    @property
    def size_reduction_ratio(self) -> float:
        if self.quantized_bytes == 0:
            return 0.0
        return self.source_bytes / self.quantized_bytes

    def render(self) -> str:
        lines = [
            "Quantization report",
            f"  source size      : {self.source_bytes:,} bytes",
            f"  quantized size   : {self.quantized_bytes:,} bytes",
            f"  size reduction   : {self.size_reduction_ratio:.2f}x",
            f"  accuracy delta   : {self.accuracy_delta * 100:.2f}%",
        ]
        if self.warning:
            lines.append(f"  WARNING          : {self.warning}")
        return "\n".join(lines)


def validate_dataset(dataset_dir: str) -> List[str]:
    """Validate the representative dataset; fail fast if missing/corrupt."""
    if not dataset_dir or not os.path.isdir(dataset_dir):
        raise QuantizationError(
            f"Representative dataset directory not found: {dataset_dir!r}"
        )
    images = [
        os.path.join(dataset_dir, f)
        for f in sorted(os.listdir(dataset_dir))
        if f.lower().endswith(_IMAGE_EXTS)
    ]
    if not images:
        raise QuantizationError(
            f"Representative dataset {dataset_dir!r} contains no usable images"
        )
    # Probe-read each image to detect corruption early.
    import cv2

    valid: List[str] = []
    for path in images:
        img = cv2.imread(path)
        if img is None:
            raise QuantizationError(f"Corrupt or unreadable calibration image: {path}")
        valid.append(path)
    return valid


def _build_calibration_reader(images: List[str], input_name: str, input_size: int):
    import cv2
    import numpy as np
    from onnxruntime.quantization import CalibrationDataReader

    class _Reader(CalibrationDataReader):
        def __init__(self):
            self._iter = iter(images)

        def get_next(self):
            path = next(self._iter, None)
            if path is None:
                return None
            img = cv2.imread(path)
            img = cv2.resize(img, (input_size, input_size))
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            tensor = rgb.astype(np.float32).transpose(2, 0, 1)[np.newaxis, ...] / 255.0
            return {input_name: tensor}

    return _Reader()


def validate_output_loads(model_path: str) -> None:
    """Ensure the quantized model loads in ONNX Runtime."""
    import onnxruntime as ort

    try:
        ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    except Exception as exc:
        raise QuantizationError(f"Quantized model failed to load: {exc}") from exc


def quantize(
    source_model: str,
    output_model: str,
    dataset_dir: str,
    *,
    input_size: int = 320,
    accuracy_delta: float = 0.0,
) -> QuantizationReport:
    if not os.path.isfile(source_model):
        raise QuantizationError(f"Source model not found: {source_model}")

    # Fail fast on bad calibration data BEFORE producing any artifact.
    images = validate_dataset(dataset_dir)
    logger.info("Validated %d calibration images", len(images))

    import onnx
    from onnxruntime.quantization import QuantType, quantize_static

    model = onnx.load(source_model)
    input_name = model.graph.input[0].name

    reader = _build_calibration_reader(images, input_name, input_size)
    quantize_static(
        source_model,
        output_model,
        calibration_data_reader=reader,
        quant_format=None,
        weight_type=QuantType.QInt8,
        activation_type=QuantType.QInt8,
    )

    validate_output_loads(output_model)

    report = QuantizationReport(
        source_bytes=os.path.getsize(source_model),
        quantized_bytes=os.path.getsize(output_model),
        accuracy_delta=accuracy_delta,
    )
    if accuracy_delta >= ACCURACY_WARN_THRESHOLD:
        report.warning = (
            f"accuracy delta {accuracy_delta * 100:.2f}% >= 5% threshold "
            "-- review quantization quality"
        )
        logger.warning(report.warning)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Quantize a float32 ONNX model to INT8.")
    parser.add_argument("--source", required=True, help="Path to source float32 ONNX model")
    parser.add_argument("--output", required=True, help="Output path for INT8 ONNX model")
    parser.add_argument("--dataset", required=True, help="Representative dataset directory")
    parser.add_argument("--input-size", type=int, default=320)
    parser.add_argument(
        "--accuracy-delta",
        type=float,
        default=0.0,
        help="Measured accuracy delta vs float32 baseline (0-1), for reporting",
    )
    args = parser.parse_args(argv)
    try:
        report = quantize(
            args.source,
            args.output,
            args.dataset,
            input_size=args.input_size,
            accuracy_delta=args.accuracy_delta,
        )
    except QuantizationError as exc:
        logger.error("Quantization failed: %s", exc)
        return 1
    print(report.render())
    return 0


if __name__ == "__main__":
    sys.exit(main())

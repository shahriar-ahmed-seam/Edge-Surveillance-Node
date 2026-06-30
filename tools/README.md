# Quantization Toolchain

Converts a float32 ONNX detection model into an INT8 quantized ONNX artifact for
the edge agent, using static quantization with calibration over a representative
dataset.

## Usage

```bash
pip install -r requirements.txt

python quantize.py \
  --source models/detector.fp32.onnx \
  --output models/detector.int8.onnx \
  --dataset data/calibration_images/ \
  --input-size 320 \
  --accuracy-delta 0.03
```

## Behavior

- **Fails fast** if the representative dataset is missing, empty, or contains
  corrupt images — it never falls back to default/random calibration.
- **Validates** that the produced model loads in ONNX Runtime before reporting success.
- **Reports** size-reduction ratio and accuracy delta.
- **Warns** when the accuracy delta is at or above 5%.

`--accuracy-delta` is the measured top-1/mAP delta from your own evaluation
harness (range 0–1); it is used for the report and the 5% warning.

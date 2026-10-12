"""Train and export the best validated signature/stamp YOLOv8n checkpoint.

Run with python -m tools.train_yolo --data <prepared/data.yaml>.
Ultralytics, torch, onnx and onnxruntime are training-only dependencies.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import tempfile

from tools.prepare_yolo import CLASSES, external_output, scan_dataset


def validate_export(path: Path, image_size: int) -> dict:
    import numpy as np
    import onnx
    import onnxruntime as ort

    model = onnx.load(str(path))
    onnx.checker.check_model(model)
    metadata = {item.key: item.value for item in model.metadata_props}
    names = ast.literal_eval(metadata.get("names", "{}"))
    if metadata.get("task") != "detect" or names != dict(enumerate(CLASSES)):
        raise ValueError(f"Unexpected ONNX task/classes: {metadata.get('task')}, {names}")
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    image_input = session.get_inputs()[0]
    if image_input.shape != [1, 3, image_size, image_size]:
        raise ValueError(f"Expected static batch=1 RGB ONNX input, got {image_input.shape}")
    outputs = session.run(None, {image_input.name: np.zeros((1, 3, image_size, image_size), dtype=np.float32)})
    if len(outputs) != 1 or outputs[0].ndim != 3 or outputs[0].shape[:2] != (1, 4 + len(CLASSES)):
        raise ValueError(f"Expected raw YOLOv8 detection output [1,6,N], got {[o.shape for o in outputs]}")
    if not np.isfinite(outputs[0]).all():
        raise ValueError("ONNX inference returned non-finite values")
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "names": names,
            "input_shape": image_input.shape, "output_shape": list(outputs[0].shape)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(tempfile.gettempdir()) / "opencode" / "yolo" / "runs")
    parser.add_argument("--name", default="signature_stamp")
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--minutes", type=float, default=20)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="0")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    output = external_output(args.output)
    if not args.name or Path(args.name).name != args.name or args.name in {".", ".."}:
        parser.error("--name must be a directory name")
    if args.imgsz % 32 or min(args.epochs, args.patience, args.imgsz, args.batch, args.minutes) <= 0:
        parser.error("positive training parameters and imgsz divisible by 32 required")
    if (output / args.name).exists():
        parser.error("Run directory already exists; use a new --name")
    _, dataset_report = scan_dataset(args.data)
    if dataset_report["source_names"] != dict(enumerate(CLASSES)):
        parser.error("Run tools.prepare_yolo first to create canonical class metadata")
    output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(output / "config"))
    os.environ.setdefault("YOLO_AUTOINSTALL", "false")
    # Lazy imports keep data validation usable without a GPU/training installation.
    import torch
    from ultralytics import YOLO

    if args.device != "cpu" and not torch.cuda.is_available():
        parser.error("CUDA is unavailable; explicitly choose --device cpu")
    weights = args.weights.resolve() if args.weights else output / "pretrained" / "yolov8n.pt"
    weights.parent.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(weights), task="detect")
    model.train(data=str(args.data.resolve()), epochs=args.epochs, patience=args.patience,
                time=args.minutes / 60, imgsz=args.imgsz, batch=args.batch, device=args.device,
                seed=args.seed, deterministic=True, workers=0, cache=False, amp=True,
                project=str(output), name=args.name, exist_ok=False,
                fliplr=0.0, flipud=0.0, degrees=5.0, mosaic=0.25, close_mosaic=5,
                save=True, plots=True)
    best_path = Path(model.trainer.best).resolve()
    if not best_path.is_file():
        raise RuntimeError("Training did not produce best.pt; export aborted")
    # Always reload best.pt: the in-memory model may contain the last epoch.
    best = YOLO(str(best_path), task="detect")
    metrics = best.val(data=str(args.data.resolve()), split="val", imgsz=args.imgsz,
                       batch=args.batch, device=args.device, workers=0,
                       project=str(output), name=args.name + "_validation")
    export_path = Path(best.export(format="onnx", imgsz=args.imgsz, batch=1,
                                  dynamic=False, half=False, nms=False,
                                  simplify=False, opset=17, device="cpu"))
    export_report = validate_export(export_path, args.imgsz)
    report = {"best_pt": str(best_path), "onnx": str(export_path), "export": export_report,
              "dataset": dataset_report, "validation": metrics.results_dict,
              "per_class": metrics.summary(), "parameters": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
              "limitations": "Validation measures this dataset only; presence is not authenticity. Test split was not used for model selection."}
    (best_path.parent.parent / "training_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

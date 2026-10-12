"""Validate and copy an explicitly labelled YOLO dataset for signatures and stamps.

Example (no images or models are written into the repository)::

    python -m tools.prepare_yolo --source-yaml D:/raw/data.yaml \
        --source-url https://example.org/dataset --license CC-BY-4.0

The source YAML supplies class IDs. Unknown classes require an explicit name map,
e.g. --class-map '{"Signature":"signature","Seal":"stamp","logo":null}'.
MWS-Vision-Bench is evaluation data and must never be used here.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile

from PIL import Image, ImageOps
import yaml


CLASSES = ("signature", "stamp")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
DEFAULT_OUTPUT = Path(tempfile.gettempdir()) / "opencode" / "yolo" / "prepared"
REPOSITORY = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Sample:
    image: Path
    split: str
    labels: tuple[tuple[int, float, float, float, float], ...]
    pixel_sha256: str
    group: str


def external_output(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path == REPOSITORY or REPOSITORY in path.parents:
        raise ValueError("Dataset and model output must be outside the repository")
    return path


def load_names(value: object) -> dict[int, str]:
    if isinstance(value, list):
        names = dict(enumerate(value))
    elif isinstance(value, dict):
        try:
            names = {int(key): name for key, name in value.items()}
        except (TypeError, ValueError) as exc:
            raise ValueError("names must have integer class IDs") from exc
        if len(names) != len(value):
            raise ValueError("Duplicate class IDs")
    else:
        raise ValueError("Source YAML must declare names (list or ID/name dictionary)")
    if not names or any(key < 0 for key in names):
        raise ValueError("Class IDs must be nonnegative")
    if any(not isinstance(name, str) or not name.strip() for name in names.values()):
        raise ValueError("Class names must be nonempty strings")
    if len(set(names.values())) != len(names):
        raise ValueError("Duplicate class names")
    return names


def class_mapping(names: dict[int, str], aliases: dict[str, str | None] | None = None) -> dict[int, int | None]:
    aliases = aliases or {}
    if set(aliases) - set(names.values()):
        raise ValueError("Class map contains names absent from the source YAML")
    result = {}
    for number, name in names.items():
        canonical = aliases[name] if name in aliases else name.strip().lower()
        if canonical is None:
            result[number] = None  # Explicitly ignored class, never guessed.
        elif canonical in CLASSES:
            result[number] = CLASSES.index(canonical)
        else:
            raise ValueError(f"Unknown source class {name!r}; supply an explicit --class-map")
    if set(result.values()) - {None} != set(range(len(CLASSES))):
        raise ValueError("Dataset must contain both signature and stamp classes")
    return result


def parse_labels(path: Path, mapping: dict[int, int | None]) -> tuple:
    if not path.is_file():
        raise ValueError(f"Missing annotation: {path}; use an empty file for a verified negative")
    labels = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split()
        try:
            if len(parts) != 5 or not parts[0].isdigit():
                raise ValueError("expected integer class + 4 normalized box coordinates")
            source_class = int(parts[0])
            if source_class not in mapping:
                raise ValueError(f"undeclared class ID {source_class}")
            x, y, width, height = map(float, parts[1:])
            if not all(math.isfinite(value) for value in (x, y, width, height)):
                raise ValueError("non-finite box")
            if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < width <= 1 and 0 < height <= 1):
                raise ValueError("box coordinates out of range")
            if min(x - width / 2, y - height / 2) < -1e-6 or max(x + width / 2, y + height / 2) > 1 + 1e-6:
                raise ValueError("box extends outside image")
        except ValueError as exc:
            raise ValueError(f"{path}:{number}: {exc}") from exc
        target_class = mapping[source_class]
        if target_class is not None:
            labels.append((target_class, x, y, width, height))
    if len(set(labels)) != len(labels):
        raise ValueError(f"Duplicate boxes in {path}")
    return tuple(labels)


def image_fingerprint(path: Path) -> str:
    with Image.open(path) as image:
        if image.getexif().get(274, 1) != 1:
            raise ValueError(f"EXIF rotation needs matching annotation conversion: {path}")
        rgb = ImageOps.exif_transpose(image).convert("RGB")
        digest = hashlib.sha256(str(rgb.size).encode("ascii") + rgb.tobytes())
    return digest.hexdigest()


def image_group(path: Path) -> str:
    # Roboflow generated siblings share the prefix before .rf.; keep them together.
    return path.stem.split(".rf.", 1)[0].casefold()


def scan_dataset(source_yaml: Path, aliases: dict | None = None, source_root: Path | None = None) -> tuple[list[Sample], dict]:
    source_yaml = source_yaml.resolve()
    source = yaml.safe_load(source_yaml.read_text(encoding="utf-8-sig"))
    if not isinstance(source, dict):
        raise ValueError("Source YAML must be a mapping")
    if "mws-vision-bench" in (str(source_yaml) + json.dumps(source)).lower():
        raise ValueError("MWS-Vision-Bench is reserved for evaluation, not training")
    names = load_names(source.get("names"))
    mapping = class_mapping(names, aliases)
    root = source_root.resolve() if source_root else (source_yaml.parent / source.get("path", ".")).resolve()
    samples = []
    pixel_splits: dict[str, str] = {}
    group_splits: dict[str, str] = {}
    counts = {}
    for split in ("train", "val", "test"):
        entry = source.get(split)
        if not entry:
            if split == "test":
                continue
            raise ValueError(f"Source must declare a nonempty {split} split")
        if not isinstance(entry, str):
            raise ValueError("Split must be an image directory, not a list or executable download")
        image_dir = (root / entry).resolve()
        if not image_dir.is_relative_to(root):
            raise ValueError(f"Split escapes dataset root: {image_dir}; use --source-root to relocate")
        if not image_dir.is_dir() or image_dir.name != "images" and "images" not in image_dir.parts:
            raise ValueError(f"Expected an existing images directory for {split}: {image_dir}")
        parts = list(image_dir.parts)
        index = len(parts) - 1 - parts[::-1].index("images")
        parts[index] = "labels"
        label_dir = Path(*parts)
        images = sorted(p for p in image_dir.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS and p.is_file())
        if not images:
            raise ValueError(f"Empty {split} image split")
        per_class: Counter = Counter()
        seen_labels = set()
        for image in images:
            if not image.resolve().is_relative_to(root):
                raise ValueError(f"Image symlink escapes dataset root: {image}")
            label_path = label_dir / image.relative_to(image_dir).with_suffix(".txt")
            if not label_path.resolve().is_relative_to(root):
                raise ValueError(f"Label symlink escapes dataset root: {label_path}")
            if label_path in seen_labels:
                raise ValueError(f"Ambiguous image stems use the same annotation: {label_path}")
            seen_labels.add(label_path)
            labels = parse_labels(label_path, mapping)
            fingerprint = image_fingerprint(image)
            group = image_group(image)
            for key, tracker in ((fingerprint, pixel_splits), (group, group_splits)):
                if key in tracker and tracker[key] != split:
                    raise ValueError(f"Image leakage across {tracker[key]}/{split}: {image}")
                tracker[key] = split
            samples.append(Sample(image, split, labels, fingerprint, group))
            per_class.update(row[0] for row in labels)
        orphan_labels = set(label_dir.rglob("*.txt")) - seen_labels
        if orphan_labels:
            raise ValueError(f"Annotation without image: {sorted(orphan_labels)[0]}")
        if split in {"train", "val"} and set(per_class) != {0, 1}:
            raise ValueError(f"{split} must contain labelled examples of both signature and stamp")
        counts[split] = {"images": len(images), "boxes": {CLASSES[key]: per_class[key] for key in range(2)}}
    return samples, {"source_names": names, "class_mapping": mapping, "splits": counts}


def prepare_dataset(source_yaml: Path, output: Path, source_url: str, license_name: str,
                    aliases: dict | None = None, source_root: Path | None = None) -> dict:
    if not source_url.strip() or not license_name.strip():
        raise ValueError("Source URL and dataset license are required provenance")
    if "mws-vision-bench" in source_url.lower():
        raise ValueError("MWS-Vision-Bench is reserved for evaluation, not training")
    output = external_output(output)
    if output.exists():
        raise ValueError(f"Output already exists; select a new directory: {output}")
    samples, report = scan_dataset(source_yaml, aliases, source_root)
    report.update(source_url=source_url, license=license_name, source_yaml=str(source_yaml.resolve()),
                  names=dict(enumerate(CLASSES)), duplicate_check="decoded RGB SHA256 and Roboflow source filename groups")
    output.mkdir(parents=True)
    manifest = []
    for index, sample in enumerate(samples):
        # Unique names avoid flattened-path collisions and retain original group in manifest.
        stem = f"{index:06d}_{sample.pixel_sha256[:12]}"
        destination = output / "images" / sample.split / (stem + sample.image.suffix.lower())
        annotation = output / "labels" / sample.split / (stem + ".txt")
        destination.parent.mkdir(parents=True, exist_ok=True)
        annotation.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sample.image, destination)
        annotation.write_text("".join(f"{row[0]} " + " ".join(f"{v:.9f}" for v in row[1:]) + "\n" for row in sample.labels), encoding="utf-8")
        manifest.append({"image": destination.relative_to(output).as_posix(), "source": str(sample.image),
                         "pixel_sha256": sample.pixel_sha256, "source_group": sample.group, "split": sample.split})
    config = {"path": output.as_posix(), "train": "images/train", "val": "images/val", "names": dict(enumerate(CLASSES))}
    if "test" in report["splits"]:
        config["test"] = "images/test"
    (output / "data.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    (output / "dataset_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (output / "manifest.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-yaml", required=True, type=Path)
    parser.add_argument("--source-root", type=Path, help="Relocate YAML path while preserving its split paths")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--license", required=True, dest="license_name")
    parser.add_argument("--class-map", type=json.loads, help="JSON mapping source class names to signature/stamp/null")
    args = parser.parse_args(argv)
    try:
        report = prepare_dataset(args.source_yaml, args.output, args.source_url, args.license_name, args.class_map, args.source_root)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Vehicle detection via YOLOv8 (ultralytics).

Uses a pretrained COCO checkpoint (`yolov8n.pt` — the smallest/fastest
YOLOv8 variant — by default) rather than a custom-trained
parking-violation model, since there's no labeled parking-violation image
dataset to fine-tune on yet. COCO already includes the vehicle classes we
actually need (car, motorcycle, bus, truck), so this gives real vehicle
detection out of the box. What it can't tell you is whether a given
vehicle is *illegally* parked — that's a separate, much harder question
(see illegal_parking.py for the honest version of that heuristic).
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import List

# COCO class names relevant to a parking-violation photo. Anything else
# YOLO detects in the frame (person, bicycle, dog, ...) isn't useful
# evidence for a parking complaint and is filtered out here rather than
# left for every caller to re-filter.
VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck"}


@dataclass
class Detection:
    vehicle_class: str
    confidence: float
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float


@lru_cache
def _get_model(weights: str):
    import os

    # PyTorch 2.6+ defaults torch.load(weights_only=True). Ultralytics
    # 8.2.58 checkpoints include DetectionModel and fail that check.
    os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

    from ultralytics import YOLO  # heavy import, loaded lazily

    return YOLO(weights)


def detect_vehicles(
    image_path: str, weights: str = "yolov8n.pt", confidence_threshold: float = 0.25
) -> List[Detection]:
    """Runs YOLOv8 on the image at `image_path` and returns only
    vehicle-class detections above `confidence_threshold`, as plain
    Detection objects (bbox in pixel coordinates: x, y, width, height)."""
    model = _get_model(weights)
    results = model.predict(source=image_path, conf=confidence_threshold, verbose=False)

    detections: List[Detection] = []
    for result in results:
        names = result.names
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = names.get(class_id, str(class_id))
            if class_name not in VEHICLE_CLASSES:
                continue

            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
            detections.append(
                Detection(
                    vehicle_class=class_name,
                    confidence=float(box.conf[0]),
                    bbox_x=x1,
                    bbox_y=y1,
                    bbox_width=x2 - x1,
                    bbox_height=y2 - y1,
                )
            )
    return detections

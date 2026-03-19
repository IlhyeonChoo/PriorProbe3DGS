from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.oracle_features import build_oracle_query_features


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color=color).save(path)


def test_build_oracle_query_features_updates_single_target_metadata(tmp_path: Path) -> None:
    scene_root = tmp_path / "room_0"
    crops_dir = scene_root / "oracle" / "crops"
    _write_image(crops_dir / "000.png", (255, 0, 0))
    _write_image(crops_dir / "001.png", (0, 255, 0))
    target_path = scene_root / "oracle" / "target.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps({"object_id": 74, "category": "chair", "crop_dir": "oracle/crops"}, indent=2),
        encoding="utf-8",
    )

    outputs = build_oracle_query_features(scene_root, backend="mean_rgb")

    updated = json.loads(target_path.read_text(encoding="utf-8"))
    assert len(outputs) == 1
    assert outputs[0].exists()
    assert updated["query_feature_paths"]["mean_rgb"] == "oracle/query_feature_mean_rgb.npy"


def test_build_oracle_query_features_updates_multi_target_metadata(tmp_path: Path) -> None:
    scene_root = tmp_path / "room_0"
    object_dir = scene_root / "oracle" / "objects" / "74" / "crops"
    _write_image(object_dir / "000.png", (255, 0, 0))
    targets_path = scene_root / "oracle" / "targets.json"
    targets_path.parent.mkdir(parents=True, exist_ok=True)
    targets_path.write_text(
        json.dumps([{"object_id": 74, "category": "chair", "crop_dir": "oracle/objects/74/crops"}], indent=2),
        encoding="utf-8",
    )

    outputs = build_oracle_query_features(scene_root, backend="mean_rgb")

    updated = json.loads(targets_path.read_text(encoding="utf-8"))
    assert outputs
    assert outputs[0].exists()
    assert updated[0]["query_feature_paths"]["mean_rgb"] == "oracle/objects/74/query_feature_mean_rgb.npy"


def test_build_oracle_query_features_supports_clip_geom(tmp_path: Path) -> None:
    scene_root = tmp_path / "room_0"
    crops_dir = scene_root / "oracle" / "crops"
    images_dir = scene_root / "images"
    _write_image(crops_dir / "000.png", (255, 0, 0))
    _write_image(images_dir / "000.png", (255, 255, 255))
    target_path = scene_root / "oracle" / "target.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps(
            {
                "object_id": 74,
                "category": "chair",
                "crop_dir": "oracle/crops",
                "sizes": [0.9, 0.8, 1.1],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with patch(
        "priorprobe.oracle_features.extract_image_features",
        return_value=np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
    ):
        outputs = build_oracle_query_features(scene_root, backend="clip_geom")

    updated = json.loads(target_path.read_text(encoding="utf-8"))
    feature = np.load(outputs[0])
    assert updated["query_feature_paths"]["clip_geom"] == "oracle/query_feature_clip_geom.npy"
    assert "geometry_stats" in updated
    assert len(updated["geometry_stats"]["geometry_feature"]) == 7
    assert feature.shape[0] == 11

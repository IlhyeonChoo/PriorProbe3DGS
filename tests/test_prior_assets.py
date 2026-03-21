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

from priorprobe.prior_assets import build_prior_library, stage_shapesplat_assets


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color=color).save(path)


def _write_point_cloud_ply(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "ply",
                "format ascii 1.0",
                "element vertex 4",
                "property float x",
                "property float y",
                "property float z",
                "property float nx",
                "property float ny",
                "property float nz",
                "property uchar red",
                "property uchar green",
                "property uchar blue",
                "end_header",
                "-0.5 -0.5 0.0 0 0 1 255 0 0",
                "0.5 -0.5 0.0 0 0 1 0 255 0",
                "-0.5 0.5 1.0 0 0 1 0 0 255",
                "0.5 0.5 1.0 0 0 1 255 255 255",
            ]
        ),
        encoding="utf-8",
    )


def test_stage_shapesplat_assets_copies_assets_and_builds_fallback_feature(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    target_root = tmp_path / "project"
    gaussian_source = source_root / "chair_001.ply"
    _write_point_cloud_ply(gaussian_source)
    _write_image(source_root / "renders" / "000.png", (255, 0, 0))
    _write_image(source_root / "renders" / "001.png", (0, 255, 0))

    config = {
        "asset_prep": {
            "feature_backend": "fallback",
            "render_sample_count": 2,
        },
        "library": {
            "source": "shapesplat",
            "default_objects": [
                {
                    "object_id": "chair_001",
                    "category": "chair",
                    "source_gaussian_path": str(gaussian_source.relative_to(tmp_path)),
                    "source_render_dir": str((source_root / "renders").relative_to(tmp_path)),
                    "gaussian_path": "project/data/priors/shapesplat/assets/chair/chair_001/splat.ply",
                    "render_dir": "project/data/priors/shapesplat/assets/chair/chair_001/renders",
                    "feature_path": "project/data/priors/shapesplat/features/chair/chair_001.npy",
                    "source_split": "shapenet_chair",
                    "tags": ["indoor"],
                }
            ],
        },
    }

    results = stage_shapesplat_assets(config, root=tmp_path)

    assert len(results) == 1
    result = results[0]
    assert result.gaussian_path.exists()
    assert result.render_dir is not None and result.render_dir.exists()
    assert result.render_count == 2
    assert result.feature_path is not None and result.feature_path.exists()
    assert result.canonical_seed_center_path is not None and result.canonical_seed_center_path.exists()
    assert result.canonical_seed_floor_path is not None and result.canonical_seed_floor_path.exists()
    assert result.canonical_metadata_path is not None and result.canonical_metadata_path.exists()
    feature = np.load(result.feature_path)
    assert feature.ndim == 1
    assert result.feature_dim == feature.shape[0]
    assert result.feature_backend == "fallback"


def test_build_prior_library_includes_asset_metadata_extras(tmp_path: Path) -> None:
    feature_root = tmp_path / "project" / "data" / "priors" / "shapesplat"
    render_dir = feature_root / "assets" / "chair" / "chair_001" / "renders"
    gaussian_path = feature_root / "assets" / "chair" / "chair_001" / "splat.ply"
    feature_path = feature_root / "features" / "chair" / "chair_001.npy"
    _write_point_cloud_ply(gaussian_path)
    render_dir.mkdir(parents=True, exist_ok=True)
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    _write_image(render_dir / "000.png", (255, 255, 255))
    _write_image(render_dir / "001.png", (0, 0, 255))
    np.save(feature_path, np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32))

    config = {
        "asset_prep": {"feature_backend": "fallback"},
        "library": {
            "source": "shapesplat",
            "default_objects": [
                {
                    "object_id": "chair_001",
                    "category": "chair",
                    "gaussian_path": str(gaussian_path.relative_to(tmp_path / "project")),
                    "render_dir": str(render_dir.relative_to(tmp_path / "project")),
                    "feature_path": str(feature_path.relative_to(tmp_path / "project")),
                    "source_split": "shapenet_chair",
                    "metadata_extras": {
                        "source_domain": "replica",
                        "replica_scene_id": "room_0",
                        "replica_object_id": 6,
                        "exact_match_key": "room_0:6",
                    },
                }
            ],
        },
    }

    library = build_prior_library(config, root=tmp_path / "project")
    manifest_path = tmp_path / "manifest.json"
    library.dump_manifest(manifest_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert payload["entries"][0]["metadata"]["extras"]["source_split"] == "shapenet_chair"
    assert payload["entries"][0]["metadata"]["extras"]["render_count"] == 2
    assert payload["entries"][0]["metadata"]["extras"]["feature_dim"] == 4
    assert payload["entries"][0]["metadata"]["extras"]["support_type"] == "floor"
    assert payload["entries"][0]["metadata"]["extras"]["exact_match_key"] == "room_0:6"
    assert payload["entries"][0]["metadata"]["extras"]["canonical_seed_floor_path"].endswith(
        "canonical_seed_floor.ply"
    )
    assert payload["entries"][0]["metadata"]["extras"]["canonical_bbox_size"] == [1.0, 1.0, 1.0]


def test_stage_shapesplat_assets_records_clip_geom_stats(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    target_root = tmp_path / "project"
    gaussian_source = source_root / "chair_001.ply"
    _write_point_cloud_ply(gaussian_source)
    _write_image(source_root / "renders" / "000.png", (255, 0, 0))
    _write_image(source_root / "renders" / "001.png", (0, 0, 0))

    config = {
        "asset_prep": {
            "feature_backend": "clip_geom",
            "feature_model_name": "ViT-B-32",
            "render_sample_count": 2,
        },
        "library": {
            "source": "shapesplat",
            "default_objects": [
                {
                    "object_id": "chair_001",
                    "category": "chair",
                    "source_gaussian_path": str(gaussian_source.relative_to(tmp_path)),
                    "source_render_dir": str((source_root / "renders").relative_to(tmp_path)),
                    "gaussian_path": "project/data/priors/shapesplat/assets/chair/chair_001/splat.ply",
                    "render_dir": "project/data/priors/shapesplat/assets/chair/chair_001/renders",
                    "feature_path": "project/data/priors/shapesplat/features/chair/chair_001.npy",
                    "scale_meters": [0.8, 0.9, 1.1],
                    "source_split": "modelnet_chair",
                }
            ],
        },
    }

    with patch(
        "priorprobe.prior_assets.extract_image_features",
        return_value=np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
    ):
        results = stage_shapesplat_assets(config, root=tmp_path)

    result = results[0]
    assert result.geometry_stats is not None
    assert len(result.geometry_stats["geometry_feature"]) == 7
    library = build_prior_library(config, root=tmp_path)
    entry = library.get("chair_001")
    assert entry.metadata is not None
    assert entry.metadata.extras["geometry_stats"]["size_xyz"] == [0.8, 0.9, 1.1]

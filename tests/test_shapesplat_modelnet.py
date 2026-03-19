from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.shapesplat_modelnet import (
    build_modelnet_prior_config,
    extract_modelnet_assets,
    list_modelnet_point_clouds,
    render_point_cloud_views,
)


def _write_ascii_point_cloud_ply(path: Path) -> None:
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
                "property uchar red",
                "property uchar green",
                "property uchar blue",
                "end_header",
                "-1 -1 0 255 0 0",
                "1 -1 0 0 255 0",
                "-1 1 0 0 0 255",
                "1 1 0 255 255 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_list_modelnet_point_clouds_filters_split_and_category(tmp_path: Path) -> None:
    zip_path = tmp_path / "chair.zip"
    source = tmp_path / "source"
    _write_ascii_point_cloud_ply(source / "point_cloud.ply")
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(source / "point_cloud.ply", arcname="train/chair_0001/point_cloud.ply")
        archive.write(source / "point_cloud.ply", arcname="train/table_0001/point_cloud.ply")
        archive.write(source / "point_cloud.ply", arcname="test/chair_0002/point_cloud.ply")

    entries = list_modelnet_point_clouds(zip_path, category="chair", split="train")

    assert entries == [("chair_0001", "train/chair_0001/point_cloud.ply")]


def test_render_point_cloud_views_writes_expected_images(tmp_path: Path) -> None:
    ply_path = tmp_path / "chair_0001.ply"
    render_dir = tmp_path / "renders"
    _write_ascii_point_cloud_ply(ply_path)

    image_paths, bbox_size = render_point_cloud_views(
        ply_path,
        render_dir,
        num_views=4,
        image_size=64,
        point_limit=0,
    )

    assert len(image_paths) == 4
    assert all(path.exists() for path in image_paths)
    assert np.allclose(np.asarray(bbox_size), np.asarray([2.0, 2.0, 1e-6]), atol=1e-5)


def test_extract_assets_and_build_config(tmp_path: Path) -> None:
    zip_path = tmp_path / "chair.zip"
    source = tmp_path / "source"
    _write_ascii_point_cloud_ply(source / "point_cloud.ply")
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(source / "point_cloud.ply", arcname="train/chair_0001/point_cloud.ply")

    assets = extract_modelnet_assets(
        zip_path,
        tmp_path / "extract",
        category="chair",
        split="train",
        max_objects=1,
        num_views=4,
        image_size=64,
        point_limit=0,
    )
    config = build_modelnet_prior_config(
        assets,
        manifest_path=tmp_path / "manifest.json",
        stage_root=tmp_path / "stage",
        category="chair",
        render_sample_count=4,
        min_render_count=4,
    )

    assert len(assets) == 1
    assert assets[0].gaussian_path.exists()
    assert (assets[0].render_dir / "000.png").exists()
    object_entry = config["library"]["default_objects"][0]
    assert object_entry["object_id"] == "chair_0001"
    assert object_entry["gaussian_path"].endswith("stage/assets/chair/chair_0001/splat.ply")

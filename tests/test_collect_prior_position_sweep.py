from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    script_path = ROOT / "scripts" / "collect_prior_position_sweep.py"
    spec = importlib.util.spec_from_file_location("collect_prior_position_sweep", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_select_views_for_contact_prefers_evenly_spaced_valid_views() -> None:
    module = _load_module()
    view_metrics = {
        f"{index:05d}.png": {"status": "valid", "centroid_distance_px": float(index)}
        for index in range(8)
    }

    selected = module._select_views_for_contact(view_metrics, 4)

    assert selected == ["00000.png", "00002.png", "00004.png", "00007.png"]


def test_make_comparison_view_image_renders_two_panels() -> None:
    module = _load_module()
    image = np.zeros((10, 12, 3), dtype=np.uint8)
    image[:, :6, :] = 120
    gt_mask = np.zeros((10, 12), dtype=bool)
    gt_mask[2:7, 2:5] = True
    prior_mask = np.zeros((10, 12), dtype=bool)
    prior_mask[3:8, 6:9] = True

    canvas = module._make_comparison_view_image(
        image=image,
        gt_mask=gt_mask,
        prior_mask=prior_mask,
        title="demo",
        metrics={
            "mask_iou": 0.5,
            "bbox_iou": 0.6,
            "centroid_distance_px": 12.0,
            "edge_distance_px": 8.0,
        },
    )

    assert canvas.width == 24
    assert canvas.height == 54


def test_selected_priors_for_sweep_rejects_empty_filtered_selection() -> None:
    module = _load_module()

    with pytest.raises(ValueError, match="requested object ids: 74"):
        module._selected_priors_for_sweep(
            [{"target_object_id": 77}, {"target_object_id": 78}],
            {74},
        )

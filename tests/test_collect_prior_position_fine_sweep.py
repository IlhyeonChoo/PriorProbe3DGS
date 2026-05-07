from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    script_path = ROOT / "scripts" / "collect_prior_position_fine_sweep.py"
    spec = importlib.util.spec_from_file_location("collect_prior_position_fine_sweep", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_distribute_counts_balances_remainder() -> None:
    module = _load_module()
    assert module._distribute_counts(100, 3) == [34, 33, 33]
    assert module._distribute_counts(100, 2) == [50, 50]


def test_build_object_variant_plan_uses_anchor_offsets_and_total_count(tmp_path: Path) -> None:
    module = _load_module()
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "variants": [
                    {
                        "variant": "v020_dx-0p08_dy+0p24_dz+0p00",
                        "offset_local_x_m": -0.08,
                        "offset_local_y_m": 0.24,
                        "offset_local_z_m": 0.0,
                    },
                    {
                        "variant": "v027_dx+0p00_dy+0p24_dz+0p00",
                        "offset_local_x_m": 0.0,
                        "offset_local_y_m": 0.24,
                        "offset_local_z_m": 0.0,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    micro_offsets = module._sorted_micro_offsets([-0.01, 0.0, 0.01], [0.0])

    plan = module._build_object_variant_plan(
        object_id=11,
        anchor_variants=["v020_dx-0p08_dy+0p24_dz+0p00", "v027_dx+0p00_dy+0p24_dz+0p00"],
        coarse_object_summary=summary_path,
        micro_offsets=micro_offsets,
        total_count=6,
    )

    assert len(plan) == 6
    assert {item["anchor_variant"] for item in plan} == {
        "v020_dx-0p08_dy+0p24_dz+0p00",
        "v027_dx+0p00_dy+0p24_dz+0p00",
    }
    assert any(abs(item["candidate_local_offset_m"][0] + 0.08) < 1e-6 and abs(item["candidate_local_offset_m"][1] - 0.24) < 1e-6 for item in plan)
    assert any(abs(item["candidate_local_offset_m"][0] - 0.0) < 1e-6 and abs(item["candidate_local_offset_m"][1] - 0.24) < 1e-6 for item in plan)


def test_build_object_variant_plan_rejects_empty_anchor_list(tmp_path: Path) -> None:
    module = _load_module()
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps({"variants": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="Anchor variant list is empty"):
        module._build_object_variant_plan(
            object_id=11,
            anchor_variants=[],
            coarse_object_summary=summary_path,
            micro_offsets=module._sorted_micro_offsets([0.0], [0.0]),
            total_count=1,
        )


def test_validate_variants_per_object_rejects_non_positive() -> None:
    module = _load_module()

    with pytest.raises(ValueError, match="variants-per-object"):
        module._validate_variants_per_object(0)


def test_selected_fine_sweep_object_ids_rejects_empty_filtered_selection() -> None:
    module = _load_module()

    with pytest.raises(ValueError, match="requested object ids: 74"):
        module._selected_fine_sweep_object_ids({"77": ["v001"]}, {74})

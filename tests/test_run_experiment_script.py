from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.prior_library.library import PriorEntry, PriorLibrary
from priorprobe.prior_library.metadata import PriorMetadata
from priorprobe.retrieval.retriever import RetrievalResult


def _load_run_experiment_module():
    script_path = ROOT / "scripts" / "run_experiment.py"
    spec = importlib.util.spec_from_file_location("priorprobe_run_experiment", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_select_exact_target_prior_matches_scene_and_object(tmp_path: Path) -> None:
    run_experiment = _load_run_experiment_module()
    library = PriorLibrary(
        [
            PriorEntry(
                object_id="replica_room0_obj6",
                category="lamp",
                gaussian_path=tmp_path / "lamp.ply",
                metadata=PriorMetadata(
                    category="lamp",
                    source="replica_same_scene",
                    extras={
                        "replica_scene_id": "room_0",
                        "replica_object_id": 6,
                        "exact_match_key": "room_0:6",
                    },
                ),
            )
        ]
    )

    selected = run_experiment._select_exact_target_prior(
        library,
        target_payload={"scene_id": "room_0", "object_id": 6, "category": "lamp"},
    )

    assert selected.object_id == "replica_room0_obj6"
    assert selected.mode == "oracle_target_object"
    assert selected.score == 1.0


def test_build_oracle_target_box_alignment_payload_uses_target_box_directly(tmp_path: Path) -> None:
    run_experiment = _load_run_experiment_module()
    payload = run_experiment._build_oracle_target_box_alignment_payload(
        target_payload={
            "scene_id": "room_0",
            "object_id": 6,
            "category": "lamp",
            "center": [1.0, 2.0, 3.0],
            "sizes": [4.0, 5.0, 6.0],
            "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
        },
        selected_prior=RetrievalResult(
            object_id="lamp_exact",
            score=1.0,
            mode="oracle_target_object",
            gaussian_path=tmp_path / "lamp.ply",
            category="lamp",
            candidate_count=1,
            fallback_used=False,
        ),
        canonical_seed_path=tmp_path / "canonical_seed_floor.ply",
        source_prior_path=tmp_path / "lamp.ply",
        prior_bbox_size=np.asarray([2.0, 5.0, 3.0], dtype=np.float32),
        anchor_mode="floor",
        support_type="floor",
        feature_backend="clip",
    )

    assert payload["scale"] == [2.0, 1.0, 2.0]
    assert payload["rotation_matrix"] == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    assert payload["translation"] == [1.0, 2.0, 0.0]
    assert payload["metadata"]["alignment_mode"] == "oracle_target_box"
    assert payload["metadata"]["center_error"] == [0.0, 0.0, 0.0]

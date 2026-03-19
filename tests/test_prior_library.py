from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.prior_library.library import PriorEntry, PriorLibrary
from priorprobe.prior_library.metadata import PriorMetadata
from priorprobe.retrieval.retriever import PriorRetriever


def test_prior_library_manifest_round_trip(tmp_path: Path) -> None:
    metadata = PriorMetadata(
        category="chair",
        source="unit_test",
        scale_meters=(0.6, 0.9, 0.6),
        tags=("baseline",),
    )
    library = PriorLibrary(
        [
            PriorEntry(
                object_id="chair_basic",
                category="chair",
                gaussian_path=Path("data/chair_basic.ply"),
                feature_path=Path("data/chair_basic.npy"),
                metadata=metadata,
            )
        ]
    )

    manifest_path = tmp_path / "manifest.json"
    library.dump_manifest(manifest_path)
    restored = PriorLibrary.load_manifest(manifest_path)

    assert restored.get("chair_basic").metadata is not None
    assert restored.get("chair_basic").metadata.scale_meters == (0.6, 0.9, 0.6)


def test_prior_library_dump_is_json(tmp_path: Path) -> None:
    library = PriorLibrary()
    manifest_path = library.dump_manifest(tmp_path / "empty_manifest.json")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert payload["version"] == 1
    assert payload["entries"] == []


def test_retriever_returns_gaussian_path_and_category() -> None:
    metadata = PriorMetadata(category="chair", source="unit_test")
    library = PriorLibrary(
        [
            PriorEntry(
                object_id="chair_basic",
                category="chair",
                gaussian_path=Path("data/chair_basic.ply"),
                feature_path=Path("data/chair_basic.npy"),
                metadata=metadata,
            )
        ]
    )

    retriever = PriorRetriever(library)
    result = retriever.retrieve(top_k=1)[0]

    assert result.object_id == "chair_basic"
    assert result.gaussian_path == Path("data/chair_basic.ply")
    assert result.category == "chair"


def test_retriever_uses_query_features_with_oracle_category(tmp_path: Path) -> None:
    feature_root = tmp_path / "features"
    feature_root.mkdir(parents=True)
    chair_a_feature = feature_root / "chair_a.npy"
    chair_b_feature = feature_root / "chair_b.npy"
    np.save(chair_a_feature, np.asarray([1.0, 0.0, 0.0], dtype=np.float32))
    np.save(chair_b_feature, np.asarray([0.0, 1.0, 0.0], dtype=np.float32))

    library = PriorLibrary(
        [
            PriorEntry(
                object_id="chair_a",
                category="chair",
                gaussian_path=Path("data/chair_a.ply"),
                feature_path=chair_a_feature,
                metadata=PriorMetadata(category="chair", source="unit_test"),
            ),
            PriorEntry(
                object_id="chair_b",
                category="chair",
                gaussian_path=Path("data/chair_b.ply"),
                feature_path=chair_b_feature,
                metadata=PriorMetadata(category="chair", source="unit_test"),
            ),
        ]
    )

    retriever = PriorRetriever(library)
    result = retriever.retrieve(
        query_features=np.asarray([0.0, 1.0, 0.0], dtype=np.float32),
        top_k=1,
        oracle_category="chair",
    )[0]

    assert result.object_id == "chair_b"
    assert result.candidate_count == 2
    assert result.fallback_used is False


def test_retriever_falls_back_to_full_library_when_category_is_missing(tmp_path: Path) -> None:
    feature_root = tmp_path / "features"
    feature_root.mkdir(parents=True)
    lamp_feature = feature_root / "lamp.npy"
    np.save(lamp_feature, np.asarray([0.0, 0.0, 1.0], dtype=np.float32))

    library = PriorLibrary(
        [
            PriorEntry(
                object_id="lamp_a",
                category="lamp",
                gaussian_path=Path("data/lamp_a.ply"),
                feature_path=lamp_feature,
                metadata=PriorMetadata(category="lamp", source="unit_test"),
            )
        ]
    )

    retriever = PriorRetriever(library)
    result = retriever.retrieve(
        query_features=np.asarray([0.0, 0.0, 1.0], dtype=np.float32),
        top_k=1,
        oracle_category="chair",
    )[0]

    assert result.object_id == "lamp_a"
    assert result.candidate_count == 1
    assert result.fallback_used is True

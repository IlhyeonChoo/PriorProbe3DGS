from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .metadata import PriorMetadata


@dataclass(slots=True)
class PriorEntry:
    """Single object prior registered in the library."""

    object_id: str
    category: str
    gaussian_path: Path
    feature_path: Path | None = None
    metadata: PriorMetadata | None = None

    def to_manifest_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "object_id": self.object_id,
            "category": self.category,
            "gaussian_path": str(self.gaussian_path),
        }
        if self.feature_path is not None:
            record["feature_path"] = str(self.feature_path)
        if self.metadata is not None:
            record["metadata"] = self.metadata.to_dict()
        return record

    @classmethod
    def from_manifest_record(cls, record: dict[str, Any]) -> "PriorEntry":
        metadata = record.get("metadata")
        return cls(
            object_id=record["object_id"],
            category=record["category"],
            gaussian_path=Path(record["gaussian_path"]),
            feature_path=Path(record["feature_path"]) if record.get("feature_path") else None,
            metadata=PriorMetadata.from_dict(metadata) if metadata else None,
        )


class PriorLibrary:
    """In-memory registry with JSON manifest helpers."""

    def __init__(self, entries: Iterable[PriorEntry] | None = None) -> None:
        self._entries: dict[str, PriorEntry] = {}
        if entries is not None:
            for entry in entries:
                self.add_entry(entry)

    def add_entry(self, entry: PriorEntry) -> None:
        if entry.object_id in self._entries:
            raise ValueError(f"Duplicate prior object_id: {entry.object_id}")
        self._entries[entry.object_id] = entry

    def get(self, object_id: str) -> PriorEntry:
        return self._entries[object_id]

    def list_entries(self) -> list[PriorEntry]:
        return list(self._entries.values())

    def find_by_category(self, category: str) -> list[PriorEntry]:
        return [entry for entry in self._entries.values() if entry.category == category]

    def to_manifest(self) -> dict[str, Any]:
        return {
            "version": 1,
            "entries": [entry.to_manifest_record() for entry in self.list_entries()],
        }

    def dump_manifest(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_manifest(), indent=2), encoding="utf-8")
        return path

    @classmethod
    def load_manifest(cls, path: Path) -> "PriorLibrary":
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = [PriorEntry.from_manifest_record(record) for record in payload.get("entries", [])]
        return cls(entries)

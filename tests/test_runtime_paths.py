from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from priorprobe.runtime_paths import resolve_runtime_path, to_repo_relative_path


def test_resolve_runtime_path_reads_project_config(tmp_path: Path) -> None:
    config_path = tmp_path / "configs" / "base" / "project.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
runtime:
  outputs_dir: outputs/pointcloud
  logs_dir: logs/pointcloud
""".strip(),
        encoding="utf-8",
    )

    assert resolve_runtime_path(tmp_path, "outputs_dir", fallback="outputs") == (
        tmp_path / "outputs" / "pointcloud"
    )
    assert resolve_runtime_path(tmp_path, "logs_dir", fallback="logs") == (
        tmp_path / "logs" / "pointcloud"
    )


def test_to_repo_relative_path_returns_relative_path_inside_root(tmp_path: Path) -> None:
    path = tmp_path / "outputs" / "pointcloud" / "prior_library" / "manifest.json"

    assert to_repo_relative_path(path, root=tmp_path) == "outputs/pointcloud/prior_library/manifest.json"


def test_to_repo_relative_path_keeps_absolute_path_outside_root(tmp_path: Path) -> None:
    path = Path("/tmp/priorprobe/manifest.json")

    assert to_repo_relative_path(path, root=tmp_path) == str(path)

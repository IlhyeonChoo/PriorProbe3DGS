from __future__ import annotations

import importlib.util
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = ROOT / "scripts" / "build_recent_inspection_viewers.py"
    spec = importlib.util.spec_from_file_location("build_recent_inspection_viewers", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_list_recent_experiment_dirs_sorts_by_mtime(tmp_path: Path) -> None:
    script = _load_script_module()
    experiment_a = tmp_path / "experiment_a"
    experiment_b = tmp_path / "experiment_b"
    experiment_c = tmp_path / "experiment_c"
    experiment_a.mkdir()
    experiment_b.mkdir()
    experiment_c.mkdir()

    os.utime(experiment_a, ns=(1_000_000_000, 1_000_000_000))
    os.utime(experiment_b, ns=(2_000_000_000, 2_000_000_000))
    os.utime(experiment_c, ns=(3_000_000_000, 3_000_000_000))

    recent = script.list_recent_experiment_dirs(tmp_path, count=2)

    assert recent == [experiment_c, experiment_b]


def test_discover_backend_run_dirs_filters_scene_dirs_with_cfg_args(tmp_path: Path) -> None:
    script = _load_script_module()
    experiment_dir = tmp_path / "experiment"
    room_dir = experiment_dir / "room_0"
    office_dir = experiment_dir / "office_0"
    notes_dir = experiment_dir / "notes"

    room_dir.mkdir(parents=True)
    office_dir.mkdir(parents=True)
    notes_dir.mkdir(parents=True)
    (room_dir / "cfg_args").write_text("Namespace()", encoding="utf-8")
    (office_dir / "cfg_args").write_text("Namespace()", encoding="utf-8")

    discovered = script.discover_backend_run_dirs(experiment_dir)

    assert discovered == [office_dir, room_dir]


def test_build_viewer_command_points_to_existing_viewer_script(tmp_path: Path) -> None:
    script = _load_script_module()
    backend_run_dir = tmp_path / "room_0"

    command = script.build_viewer_command(backend_run_dir, max_views=9)

    assert command[0]
    assert command[1] == str(ROOT / "scripts" / "build_initial_snapshot_viewer.py")
    assert command[2:] == ["--backend-run-dir", str(backend_run_dir), "--max-views", "9"]


def test_resolve_count_reads_from_input(monkeypatch) -> None:
    script = _load_script_module()
    monkeypatch.setattr("builtins.input", lambda _: "4")

    count = script.resolve_count(None)

    assert count == 4

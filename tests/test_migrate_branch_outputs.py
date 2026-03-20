from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module() -> object:
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "migrate_branch_outputs.py"
    spec = importlib.util.spec_from_file_location("migrate_branch_outputs", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migrate_outputs_and_logs_moves_standard_and_legacy_dirs(tmp_path: Path) -> None:
    module = _load_module()

    outputs_root = tmp_path / "outputs"
    logs_root = tmp_path / "logs"
    (outputs_root / "backend_runs" / "exp_a").mkdir(parents=True)
    (outputs_root / "experiments" / "exp_a").mkdir(parents=True)
    (outputs_root / "prior_library").mkdir(parents=True)
    (outputs_root / "reports").mkdir(parents=True)
    (outputs_root / "smoke_room0_baseline_iter1").mkdir(parents=True)
    logs_root.mkdir(parents=True)

    (outputs_root / "backend_runs" / "exp_a" / "metadata.json").write_text("{}", encoding="utf-8")
    (outputs_root / "smoke_room0_baseline_iter1" / "note.txt").write_text("legacy", encoding="utf-8")

    module.migrate_outputs(outputs_root, branch_slug="pointcloud", dry_run=False)
    module.migrate_logs(logs_root, branch_slug="pointcloud", dry_run=False)

    assert not (outputs_root / "backend_runs").exists()
    assert (outputs_root / "pointcloud" / "backend_runs" / "exp_a" / "metadata.json").exists()
    assert (outputs_root / "pointcloud" / "experiments" / "exp_a").exists()
    assert (outputs_root / "pointcloud" / "prior_library").exists()
    assert (outputs_root / "pointcloud" / "reports").exists()
    assert (outputs_root / "pointcloud" / "legacy_misc" / "smoke_room0_baseline_iter1" / "note.txt").exists()
    assert (logs_root / "pointcloud" / ".gitkeep").exists()


def test_migrate_outputs_dry_run_does_not_mutate(tmp_path: Path) -> None:
    module = _load_module()

    outputs_root = tmp_path / "outputs"
    logs_root = tmp_path / "logs"
    (outputs_root / "backend_runs").mkdir(parents=True)
    (logs_root / ".gitkeep").parent.mkdir(parents=True)
    (logs_root / ".gitkeep").write_text("", encoding="utf-8")

    module.migrate_outputs(outputs_root, branch_slug="pointcloud", dry_run=True)
    module.migrate_logs(logs_root, branch_slug="pointcloud", dry_run=True)

    assert (outputs_root / "backend_runs").exists()
    assert not (outputs_root / "pointcloud").exists()
    assert not (logs_root / "pointcloud").exists()


def test_migrate_outputs_merges_into_existing_branch_root(tmp_path: Path) -> None:
    module = _load_module()

    outputs_root = tmp_path / "outputs"
    (outputs_root / "backend_runs" / "legacy_exp").mkdir(parents=True)
    (outputs_root / "pointcloud" / "backend_runs" / "new_exp").mkdir(parents=True)

    module.migrate_outputs(outputs_root, branch_slug="pointcloud", dry_run=False)

    assert not (outputs_root / "backend_runs").exists()
    assert (outputs_root / "pointcloud" / "backend_runs" / "legacy_exp").exists()
    assert (outputs_root / "pointcloud" / "backend_runs" / "new_exp").exists()


def test_migrate_outputs_archives_conflicting_files_under_legacy_misc(tmp_path: Path) -> None:
    module = _load_module()

    outputs_root = tmp_path / "outputs"
    (outputs_root / "reports").mkdir(parents=True)
    (outputs_root / "pointcloud" / "reports").mkdir(parents=True)
    (outputs_root / "reports" / "summary.md").write_text("old", encoding="utf-8")
    (outputs_root / "pointcloud" / "reports" / "summary.md").write_text("new", encoding="utf-8")

    module.migrate_outputs(outputs_root, branch_slug="pointcloud", dry_run=False)

    assert (outputs_root / "pointcloud" / "reports" / "summary.md").read_text(encoding="utf-8") == "new"
    assert (outputs_root / "pointcloud" / "legacy_misc" / "reports" / "summary.md").read_text(encoding="utf-8") == "old"

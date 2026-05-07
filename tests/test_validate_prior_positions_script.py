from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from priorprobe.validation.prior_position_validator import PositionValidationResult


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    script_path = ROOT / "scripts" / "validate_prior_positions.py"
    spec = importlib.util.spec_from_file_location("validate_prior_positions_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_main_emits_null_contact_sheet_when_missing(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _load_module()
    output_dir = tmp_path / "report"

    def fake_validate_prior_positions(*args, **kwargs):
        summary_path = output_dir / "summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text("{}", encoding="utf-8")
        return PositionValidationResult(
            decision="INPUT_MISMATCH",
            summary={"decision_reasons": ["cfg_args missing"]},
            per_object_metrics={},
            per_view_metrics={},
            output_dir=output_dir,
        )

    monkeypatch.setattr(module, "validate_prior_positions", fake_validate_prior_positions)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_prior_positions.py",
            "--backend-run-dir",
            str(tmp_path / "backend"),
            "--output-dir",
            str(output_dir),
        ],
    )

    exit_code = module.main()

    payload = json.loads(capsys.readouterr().out.strip())
    assert exit_code == 3
    assert payload["contact_sheet"] is None

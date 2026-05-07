from __future__ import annotations

import os
import re
from pathlib import Path


_PROTECTION_MODES = {"none", "freeze", "weak"}
_DATED_EXPERIMENT_RE = re.compile(r"^\d{2}_\d{2}_(.+)_\d{4}$")
_DROP_TOKENS = {
    "gaussian",
    "direct",
    "clip",
    "mean",
    "rgb",
    "geom",
    "vanilla",
    "3dgs",
    "multi",
    "single",
    "diverse",
}
_ITERATION_TOKEN_RE = re.compile(r"^\d+(?:k)?$")


def sanitize_label(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "result"


def _strip_label_suffix_tokens(tokens: list[str]) -> list[str]:
    while tokens and _ITERATION_TOKEN_RE.fullmatch(tokens[-1]):
        tokens = tokens[:-1]
    if len(tokens) >= 2 and tokens[-2] == "diverse" and tokens[-1].isdigit():
        tokens = tokens[:-2]
    while tokens and tokens[-1] == "smoke":
        tokens = tokens[:-1]
    if tokens and tokens[-1] in _PROTECTION_MODES - {"none"}:
        tokens = tokens[:-1]
    return tokens


def experiment_result_label(experiment_name: str) -> str:
    normalized = sanitize_label(experiment_name)
    dated_match = _DATED_EXPERIMENT_RE.fullmatch(normalized)
    if dated_match:
        tokens = dated_match.group(1).split("_")
    else:
        tokens = normalized.split("_")
    if tokens[:2] == ["gaussian", "direct"]:
        tokens = tokens[2:]
    tokens = _strip_label_suffix_tokens(tokens)
    filtered = [token for token in tokens if token not in _DROP_TOKENS and not token.isdigit()]
    return "_".join(filtered) if filtered else normalized


def protection_result_label(
    *,
    mode: str | None,
    protect_from_prune: bool,
    protect_from_densify: bool,
) -> str | None:
    normalized_mode = sanitize_label(mode or "none")
    if normalized_mode == "none":
        return None
    parts = [normalized_mode]
    if protect_from_prune or protect_from_densify:
        parts.append("protect")
        if protect_from_prune:
            parts.append("prune")
        if protect_from_densify:
            parts.append("densify")
    return "_".join(parts)


def result_ply_filename(
    *,
    experiment_name: str,
    iteration: int,
    protection_mode: str | None = None,
    protect_from_prune: bool = False,
    protect_from_densify: bool = False,
) -> str:
    parts = [experiment_result_label(experiment_name)]
    protection = protection_result_label(
        mode=protection_mode,
        protect_from_prune=protect_from_prune,
        protect_from_densify=protect_from_densify,
    )
    if protection:
        parts.append(protection)
    parts.extend(["iter", str(int(iteration))])
    return "_".join(parts) + ".ply"


def infer_experiment_name(model_path: Path) -> str:
    normalized = Path(model_path).resolve()
    if normalized.parent.name.strip() == "backend_runs":
        return normalized.name
    parent_name = normalized.parent.name.strip()
    return parent_name or normalized.name


def ensure_named_point_cloud(
    *,
    iteration_dir: Path,
    experiment_name: str,
    iteration: int,
    protection_mode: str | None = None,
    protect_from_prune: bool = False,
    protect_from_densify: bool = False,
) -> Path:
    iteration_dir = iteration_dir.resolve()
    canonical_path = iteration_dir / "point_cloud.ply"
    target_name = result_ply_filename(
        experiment_name=experiment_name,
        iteration=iteration,
        protection_mode=protection_mode,
        protect_from_prune=protect_from_prune,
        protect_from_densify=protect_from_densify,
    )
    target_path = iteration_dir / target_name

    if canonical_path.is_symlink():
        current_link = Path(os.readlink(canonical_path))
        current_target = (iteration_dir / current_link).resolve()
        if current_target != target_path and current_target.exists() and not target_path.exists():
            current_target.rename(target_path)
    elif canonical_path.exists() and canonical_path != target_path and not target_path.exists():
        canonical_path.rename(target_path)

    if not target_path.exists() and canonical_path.exists() and not canonical_path.is_symlink():
        canonical_path.rename(target_path)

    if canonical_path.exists() or canonical_path.is_symlink():
        canonical_path.unlink()
    canonical_path.symlink_to(target_path.name)
    return target_path

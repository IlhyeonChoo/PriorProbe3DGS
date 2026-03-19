#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
from argparse import Namespace
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from plyfile import PlyData

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a static viewer and contact sheets for an iteration-0 initialization snapshot."
    )
    parser.add_argument(
        "--backend-run-dir",
        required=True,
        type=Path,
        help="Path to a backend model directory under outputs/backend_runs/...",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory. Defaults to <backend-run-dir>/inspection.",
    )
    parser.add_argument(
        "--max-views",
        type=int,
        default=6,
        help="Number of evenly spaced train/test views to place in each contact sheet.",
    )
    parser.add_argument(
        "--max-scene-points",
        type=int,
        default=60000,
        help="Maximum scene sparse points used for orthographic projections.",
    )
    parser.add_argument(
        "--max-prior-points",
        type=int,
        default=16000,
        help="Maximum points per aligned prior used for orthographic projections.",
    )
    return parser.parse_args()


def parse_cfg_args(path: Path) -> Namespace:
    text = path.read_text(encoding="utf-8").strip()
    namespace = eval(text, {"Namespace": Namespace}, {})
    if not isinstance(namespace, Namespace):
        raise ValueError(f"Expected Namespace in cfg_args, got {type(namespace)!r}")
    return namespace


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def list_pngs(path: Path) -> list[Path]:
    return sorted(candidate for candidate in path.glob("*.png") if candidate.is_file())


def select_evenly_spaced(paths: list[Path], count: int) -> list[Path]:
    if count <= 0 or not paths:
        return []
    if len(paths) <= count:
        return paths
    indices = np.linspace(0, len(paths) - 1, num=count, dtype=int)
    return [paths[index] for index in indices.tolist()]


def fit_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.contain(image.convert("RGB"), size)


def diff_image(left: Image.Image, right: Image.Image) -> Image.Image:
    left_arr = np.asarray(left.convert("RGB"), dtype=np.int16)
    right_arr = np.asarray(right.convert("RGB"), dtype=np.int16)
    diff = np.abs(left_arr - right_arr)
    diff = np.clip(diff * 3, 0, 255).astype(np.uint8)
    return Image.fromarray(diff, mode="RGB")


def labeled_panel(image: Image.Image, label: str, tile_size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGB", (tile_size[0], tile_size[1] + 26), color=(255, 255, 255))
    canvas.paste(fit_image(image, tile_size), (0, 26))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, tile_size[0] - 1, 25), fill=(245, 245, 245), outline=(200, 200, 200))
    draw.text((8, 7), label, fill=(0, 0, 0))
    return canvas


def make_render_contact_sheet(gt_dir: Path, render_dir: Path, title: str, max_views: int) -> Image.Image:
    gt_paths = list_pngs(gt_dir)
    render_paths = list_pngs(render_dir)
    if not gt_paths or not render_paths:
        raise FileNotFoundError(f"Missing render inputs under {gt_dir} or {render_dir}")
    paired = list(zip(select_evenly_spaced(gt_paths, max_views), select_evenly_spaced(render_paths, max_views), strict=False))
    tile_size = (224, 224)
    gap = 14
    header_h = 50
    row_h = tile_size[1] + 26
    width = gap + (tile_size[0] * 3) + (gap * 3)
    height = header_h + len(paired) * (row_h + gap) + gap
    canvas = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 12), title, fill=(0, 0, 0))
    draw.text((12, 30), "Columns: GT | iter0 render | abs diff x3", fill=(70, 70, 70))
    for row_index, (gt_path, render_path) in enumerate(paired):
        gt = Image.open(gt_path).convert("RGB")
        render = Image.open(render_path).convert("RGB")
        diff = diff_image(gt, render)
        y = header_h + row_index * (row_h + gap)
        labels = [
            (gt, f"GT {gt_path.stem}"),
            (render, f"iter0 {render_path.stem}"),
            (diff, f"diff {render_path.stem}"),
        ]
        for column_index, (image, label) in enumerate(labels):
            panel = labeled_panel(image, label, tile_size)
            x = gap + column_index * (tile_size[0] + gap)
            canvas.paste(panel, (x, y))
    return canvas


def load_xyz(path: Path, max_points: int) -> np.ndarray:
    data = PlyData.read(path)
    vertex = data["vertex"]
    points = np.stack(
        [
            np.asarray(vertex["x"], dtype=np.float32),
            np.asarray(vertex["y"], dtype=np.float32),
            np.asarray(vertex["z"], dtype=np.float32),
        ],
        axis=1,
    )
    if max_points > 0 and len(points) > max_points:
        indices = np.linspace(0, len(points) - 1, num=max_points, dtype=int)
        points = points[indices]
    return points


def projection_axes(name: str) -> tuple[int, int]:
    if name == "top_xy":
        return 0, 1
    if name == "front_xz":
        return 0, 2
    if name == "side_yz":
        return 1, 2
    raise ValueError(f"Unsupported projection name: {name}")


def map_points_to_canvas(points: np.ndarray, axes: tuple[int, int], bounds_min: np.ndarray, bounds_max: np.ndarray, size: int) -> np.ndarray:
    x_axis, y_axis = axes
    selected = points[:, [x_axis, y_axis]]
    lo = bounds_min[[x_axis, y_axis]]
    hi = bounds_max[[x_axis, y_axis]]
    span = np.maximum(hi - lo, 1e-6)
    norm = (selected - lo) / span
    coords = np.empty_like(norm)
    coords[:, 0] = norm[:, 0] * (size - 1)
    coords[:, 1] = (1.0 - norm[:, 1]) * (size - 1)
    return coords


def draw_points(draw: ImageDraw.ImageDraw, coords: np.ndarray, color: tuple[int, int, int], radius: int) -> None:
    for x, y in coords:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def draw_scene_bbox(
    draw: ImageDraw.ImageDraw,
    axes: tuple[int, int],
    scene_min: np.ndarray,
    scene_max: np.ndarray,
    union_min: np.ndarray,
    union_max: np.ndarray,
    size: int,
) -> None:
    corners = np.array(
        [
            [scene_min[0], scene_min[1], scene_min[2]],
            [scene_max[0], scene_min[1], scene_min[2]],
            [scene_max[0], scene_max[1], scene_max[2]],
            [scene_min[0], scene_max[1], scene_max[2]],
        ],
        dtype=np.float32,
    )
    projected = map_points_to_canvas(corners, axes, union_min, union_max, size)
    xs = projected[:, 0]
    ys = projected[:, 1]
    draw.rectangle((xs.min(), ys.min(), xs.max(), ys.max()), outline=(35, 35, 35), width=2)


def make_projection_sheet(
    scene_points: np.ndarray,
    prior_entries: list[dict],
    targets_by_id: dict[int, dict],
    max_prior_points: int,
) -> Image.Image:
    palette = [
        (220, 20, 60),
        (30, 144, 255),
        (34, 139, 34),
        (255, 140, 0),
        (148, 0, 211),
        (0, 128, 128),
    ]
    prior_clouds: list[tuple[dict, np.ndarray, tuple[int, int, int]]] = []
    for index, entry in enumerate(prior_entries):
        aligned_path = Path(entry["aligned_prior"])
        cloud = load_xyz(aligned_path, max_prior_points)
        prior_clouds.append((entry, cloud, palette[index % len(palette)]))

    union_points = [scene_points] + [cloud for _, cloud, _ in prior_clouds]
    union_min = np.min(np.concatenate(union_points, axis=0), axis=0)
    union_max = np.max(np.concatenate(union_points, axis=0), axis=0)
    scene_min = np.min(scene_points, axis=0)
    scene_max = np.max(scene_points, axis=0)

    panel_size = 420
    gap = 18
    legend_w = 420
    header_h = 60
    width = gap * 4 + panel_size * 3 + legend_w
    height = header_h + panel_size + gap * 2
    canvas = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((14, 12), "Scene sparse points + aligned priors", fill=(0, 0, 0))
    draw.text((14, 32), "Dark rectangle = scene-only bbox. Colored points = aligned priors.", fill=(70, 70, 70))

    projections = [
        ("top_xy", "Top (X/Y)"),
        ("front_xz", "Front (X/Z)"),
        ("side_yz", "Side (Y/Z)"),
    ]
    for panel_index, (projection_name, label) in enumerate(projections):
        axes = projection_axes(projection_name)
        panel = Image.new("RGB", (panel_size, panel_size), color=(252, 252, 252))
        panel_draw = ImageDraw.Draw(panel)
        scene_coords = map_points_to_canvas(scene_points, axes, union_min, union_max, panel_size)
        draw_points(panel_draw, scene_coords, (185, 185, 185), radius=1)
        draw_scene_bbox(panel_draw, axes, scene_min, scene_max, union_min, union_max, panel_size)
        for entry, cloud, color in prior_clouds:
            coords = map_points_to_canvas(cloud, axes, union_min, union_max, panel_size)
            draw_points(panel_draw, coords, color, radius=1)
            center = np.asarray(targets_by_id[entry["target_object_id"]]["center"], dtype=np.float32)[None, :]
            center_coords = map_points_to_canvas(center, axes, union_min, union_max, panel_size)[0]
            panel_draw.ellipse(
                (center_coords[0] - 4, center_coords[1] - 4, center_coords[0] + 4, center_coords[1] + 4),
                outline=(0, 0, 0),
                width=2,
            )
        panel_draw.rectangle((0, 0, panel_size - 1, panel_size - 1), outline=(210, 210, 210))
        x = gap + panel_index * (panel_size + gap)
        y = header_h
        canvas.paste(panel, (x, y))
        draw.text((x + 12, y + 12), label, fill=(0, 0, 0))

    legend_x = gap * 4 + panel_size * 3
    legend_y = header_h
    draw.rectangle((legend_x, legend_y, legend_x + legend_w - gap, legend_y + panel_size), outline=(220, 220, 220))
    draw.text((legend_x + 12, legend_y + 12), "Selected priors", fill=(0, 0, 0))
    legend_cursor = legend_y + 40
    for entry, _, color in prior_clouds:
        target = targets_by_id[entry["target_object_id"]]
        draw.rectangle((legend_x + 12, legend_cursor + 4, legend_x + 28, legend_cursor + 20), fill=color, outline=color)
        lines = [
            f"target {entry['target_object_id']} ({entry['target_category']})",
            f"prior {entry['prior_object_id']} | score {entry['prior_score']:.4f}",
            f"center {np.round(np.asarray(target['center']), 3).tolist()}",
        ]
        draw.multiline_text((legend_x + 38, legend_cursor), "\n".join(lines), fill=(0, 0, 0), spacing=3)
        legend_cursor += 62
    return canvas


def sample_middle_png(path: Path) -> Path | None:
    images = list_pngs(path)
    if not images:
        return None
    return images[len(images) // 2]


def make_retrieval_sheet(scene_root: Path, prior_entries: list[dict], targets_by_id: dict[int, dict]) -> Image.Image:
    tile_size = (220, 220)
    gap = 14
    header_h = 54
    row_h = tile_size[1] + 26
    width = gap + (tile_size[0] * 2) + (gap * 2) + 520
    height = header_h + len(prior_entries) * (row_h + gap) + gap
    canvas = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 12), "Oracle target crops vs selected prior renders", fill=(0, 0, 0))
    draw.text((12, 32), "One row per inserted prior.", fill=(70, 70, 70))
    for row_index, entry in enumerate(prior_entries):
        target = targets_by_id[entry["target_object_id"]]
        crop_dir = scene_root / target["crop_dir"]
        crop_path = sample_middle_png(crop_dir)
        source_prior = Path(entry["source_prior"])
        render_dir = source_prior.parent / "renders"
        render_path = sample_middle_png(render_dir)
        if crop_path is None or render_path is None:
            continue
        crop_panel = labeled_panel(Image.open(crop_path), f"target {target['object_id']}", tile_size)
        prior_panel = labeled_panel(Image.open(render_path), f"prior {entry['prior_object_id']}", tile_size)
        y = header_h + row_index * (row_h + gap)
        canvas.paste(crop_panel, (gap, y))
        canvas.paste(prior_panel, (gap * 2 + tile_size[0], y))
        info_lines = [
            f"target category: {target['category']}",
            f"target center: {np.round(np.asarray(target['center']), 3).tolist()}",
            f"target sizes: {np.round(np.asarray(target['sizes']), 3).tolist()}",
            f"selected prior: {entry['prior_object_id']}",
            f"score: {entry['prior_score']:.4f}",
            f"aligned file: {Path(entry['aligned_prior']).name}",
        ]
        draw.multiline_text((gap * 3 + tile_size[0] * 2, y + 12), "\n".join(info_lines), fill=(0, 0, 0), spacing=4)
    return canvas


def relative_link(target: Path, base: Path) -> str:
    return os.path.relpath(target, start=base).replace(os.sep, "/")


def write_html(
    output_path: Path,
    backend_run_dir: Path,
    scene_root: Path,
    summary: dict,
    generated_images: dict[str, Path],
    prior_entries: list[dict],
) -> None:
    output_dir = output_path.parent
    lines = [
        "<!doctype html>",
        "<html lang='en'>",
        "<head>",
        "  <meta charset='utf-8'>",
        "  <title>PriorProbe3DGS Initial Snapshot Viewer</title>",
        "  <style>",
        "    body { font-family: sans-serif; margin: 24px; color: #111; }",
        "    h1, h2 { margin-bottom: 8px; }",
        "    .muted { color: #555; }",
        "    img { max-width: 100%; border: 1px solid #ddd; margin: 8px 0 20px; }",
        "    table { border-collapse: collapse; margin: 12px 0 24px; }",
        "    th, td { border: 1px solid #ddd; padding: 8px 10px; text-align: left; vertical-align: top; }",
        "    code { background: #f6f6f6; padding: 1px 4px; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>Initial Snapshot Viewer</h1>",
        f"  <p class='muted'>backend run: <code>{backend_run_dir}</code></p>",
        f"  <p class='muted'>scene root: <code>{scene_root}</code></p>",
        "  <h2>Summary</h2>",
        "  <table>",
        "    <tr><th>Scene</th><td>{scene}</td></tr>".format(scene=summary["scene_id"]),
        "    <tr><th>Initialization</th><td>{init}</td></tr>".format(init=summary["initialization"]),
        "    <tr><th>Selected priors</th><td>{priors}</td></tr>".format(
            priors=", ".join(summary["prior_object_ids"]) if summary["prior_object_ids"] else "none"
        ),
        "  </table>",
        "  <h2>Generated Visuals</h2>",
    ]
    for title, image_path in generated_images.items():
        rel = relative_link(image_path, output_dir)
        lines.append(f"  <h3>{title}</h3>")
        lines.append(f"  <img src='{rel}' alt='{title}'>")

    lines.extend(
        [
            "  <h2>Selected Priors</h2>",
            "  <table>",
            "    <tr><th>Target</th><th>Category</th><th>Prior</th><th>Score</th><th>Aligned PLY</th></tr>",
        ]
    )
    for entry in prior_entries:
        aligned_path = Path(entry["aligned_prior"])
        rel = relative_link(aligned_path, output_dir)
        lines.append(
            "    <tr>"
            f"<td>{entry['target_object_id']}</td>"
            f"<td>{entry['target_category']}</td>"
            f"<td>{entry['prior_object_id']}</td>"
            f"<td>{entry['prior_score']:.4f}</td>"
            f"<td><a href='{rel}'>{aligned_path.name}</a></td>"
            "</tr>"
        )
    lines.extend(
        [
            "  </table>",
            "  <h2>Useful Paths</h2>",
            "  <ul>",
            f"    <li><a href='{relative_link(scene_root / 'images', output_dir)}'>scene images</a></li>",
            f"    <li><a href='{relative_link(backend_run_dir / 'point_cloud' / 'iteration_0' / 'point_cloud.ply', output_dir)}'>iteration_0 point cloud</a></li>",
            f"    <li><a href='{relative_link(backend_run_dir / 'test' / 'ours_0' / 'renders', output_dir)}'>iter0 test renders</a></li>",
            f"    <li><a href='{relative_link(backend_run_dir / 'test' / 'ours_0' / 'gt', output_dir)}'>iter0 test gt</a></li>",
            "  </ul>",
            "</body>",
            "</html>",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    backend_run_dir = args.backend_run_dir.resolve()
    output_dir = (args.output_dir or backend_run_dir / "inspection").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg_args = parse_cfg_args(backend_run_dir / "cfg_args")
    scene_root = Path(cfg_args.source_path).resolve()
    results = load_json(backend_run_dir / "results.json")
    prior_metadata_path = backend_run_dir / "prior_init" / "metadata.json"
    prior_entries = load_json(prior_metadata_path)["selected_priors"] if prior_metadata_path.exists() else []
    targets = load_json(scene_root / "oracle" / "targets.json")
    targets_by_id = {entry["object_id"]: entry for entry in targets}

    generated_images: dict[str, Path] = {}

    for split in ("train", "test"):
        gt_dir = backend_run_dir / split / "ours_0" / "gt"
        render_dir = backend_run_dir / split / "ours_0" / "renders"
        if gt_dir.exists() and render_dir.exists():
            image = make_render_contact_sheet(gt_dir, render_dir, f"{split} views: GT vs iteration-0 render", args.max_views)
            output_path = output_dir / f"initial_{split}_contact_sheet.png"
            image.save(output_path)
            generated_images[f"Initial {split} contact sheet"] = output_path

    scene_sparse_path = scene_root / "sparse" / "0" / "points3D.ply"
    scene_points = load_xyz(scene_sparse_path, args.max_scene_points)
    projection_sheet = make_projection_sheet(scene_points, prior_entries, targets_by_id, args.max_prior_points)
    projection_path = output_dir / "prior_projection_sheet.png"
    projection_sheet.save(projection_path)
    generated_images["Scene sparse + aligned priors"] = projection_path

    if prior_entries:
        retrieval_sheet = make_retrieval_sheet(scene_root, prior_entries, targets_by_id)
        retrieval_path = output_dir / "retrieval_contact_sheet.png"
        retrieval_sheet.save(retrieval_path)
        generated_images["Target crops vs selected prior renders"] = retrieval_path

    summary = {
        "scene_id": results.get("scene_id") or scene_root.name,
        "initialization": results.get("init_mode", "from_scratch"),
        "prior_object_ids": [entry["prior_object_id"] for entry in prior_entries],
    }
    html_path = output_dir / "viewer.html"
    write_html(html_path, backend_run_dir, scene_root, summary, generated_images, prior_entries)

    print(f"Generated viewer in {output_dir}")
    for title, path in generated_images.items():
        print(f"- {title}: {path}")
    print(f"- HTML viewer: {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# Author: Johanna Girodolle

"""Build a combined HTML gallery for pairwise dotplot SVG files."""

from __future__ import annotations

import argparse
import csv
import html
import logging
import os
from pathlib import Path

from attrs import define


LOGGER = logging.getLogger(__name__)


@define(frozen=True)
class SampleRecord:
    """Store one sample record from the sample sheet."""

    fasta: str
    sample: str


@define(frozen=True)
class GalleryCell:
    """Store one gallery cell."""

    cell_type: str
    row_sample: str = ""
    col_sample: str = ""
    label: str = ""
    svg_rel_path: str = ""


@define(frozen=True)
class GalleryConfig:
    """Store gallery rendering configuration."""

    samples_path: Path
    svg_dir: Path
    output_path: Path
    pivot: str = ""


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Build a combined HTML gallery for pairwise dotplot SVG files."
    )
    parser.add_argument(
        "--samples",
        required=True,
        help="Input sample sheet with 2 or 3 tab-separated columns.",
    )
    parser.add_argument(
        "--svg-dir",
        required=True,
        help="Directory containing pairwise dotplot SVG files.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output HTML file path.",
    )
    parser.add_argument(
        "--pivot",
        default="",
        help="Optional pivot sample name. If provided, render a single-row gallery.",
    )
    return parser.parse_args()


def configure_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )


def build_config_from_args(args: argparse.Namespace) -> GalleryConfig:
    """Build a gallery configuration from parsed arguments."""
    return GalleryConfig(
        samples_path=Path(args.samples),
        svg_dir=Path(args.svg_dir),
        output_path=Path(args.output),
        pivot=str(args.pivot).strip(),
    )


def read_samples(samples_path: Path) -> list[SampleRecord]:
    """Read samples from a tab-separated sample sheet."""
    records: list[SampleRecord] = []

    with open(samples_path, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for row in reader:
            if not row:
                continue
            if len(row) not in {2, 3}:
                raise ValueError(
                    f"Invalid line in sample sheet {samples_path!r}: "
                    f"expected 2 or 3 tab-separated columns, got {len(row)} -> {row!r}"
                )
            fasta_path, sample_name = row[:2]
            records.append(SampleRecord(fasta=str(fasta_path), sample=sample_name))

    if not records:
        raise ValueError(f"Sample sheet {samples_path!r} is empty.")

    return records


def extract_sample_names(records: list[SampleRecord]) -> list[str]:
    """Extract sample names while preserving input order."""
    return [record.sample for record in records]


def validate_pivot(sample_names: list[str], pivot: str) -> None:
    """Validate the optional pivot sample."""
    if pivot and pivot not in sample_names:
        raise ValueError(
            f"Unknown pivot sample {pivot!r}. Expected one of: {sample_names}"
        )


def build_pair_id(sample_a: str, sample_b: str) -> str:
    """Build a stable pair identifier."""
    return f"{sample_a}__vs__{sample_b}"


def build_svg_path(pair_id: str, svg_dir: Path) -> Path:
    """Build the expected SVG path for one pair."""
    return svg_dir / f"{pair_id}.simple.svg"


def build_relative_svg_path(output_path: Path, svg_path: Path) -> str:
    """Build a relative SVG path from the HTML output location."""
    return os.path.relpath(svg_path, start=output_path.parent)


def create_missing_cell(row_sample: str, col_sample: str, label: str) -> GalleryCell:
    """Create a missing gallery cell."""
    return GalleryCell(
        cell_type="missing",
        row_sample=row_sample,
        col_sample=col_sample,
        label=label,
    )


def create_plot_cell(
    row_sample: str,
    col_sample: str,
    label: str,
    svg_rel_path: str,
) -> GalleryCell:
    """Create a plot gallery cell."""
    return GalleryCell(
        cell_type="plot",
        row_sample=row_sample,
        col_sample=col_sample,
        label=label,
        svg_rel_path=svg_rel_path,
    )


def build_full_matrix_rows(
    sample_names: list[str],
    svg_dir: Path,
    output_path: Path,
) -> list[list[GalleryCell]]:
    """Build rows for a triangular full matrix gallery."""
    rows: list[list[GalleryCell]] = []

    for row_index, row_sample in enumerate(sample_names):
        row_cells: list[GalleryCell] = []
        row_cells.append(
            GalleryCell(
                cell_type="row_header",
                row_sample=row_sample,
                label=row_sample,
            )
        )

        for col_index, col_sample in enumerate(sample_names):
            if col_index < row_index:
                row_cells.append(
                    GalleryCell(
                        cell_type="empty",
                        row_sample=row_sample,
                        col_sample=col_sample,
                    )
                )
                continue

            if col_index == row_index:
                row_cells.append(
                    GalleryCell(
                        cell_type="diagonal",
                        row_sample=row_sample,
                        col_sample=col_sample,
                        label=row_sample,
                    )
                )
                continue

            pair_id = build_pair_id(row_sample, col_sample)
            svg_path = build_svg_path(pair_id, svg_dir)
            label = f"{row_sample} vs {col_sample}"

            if svg_path.exists():
                row_cells.append(
                    create_plot_cell(
                        row_sample=row_sample,
                        col_sample=col_sample,
                        label=label,
                        svg_rel_path=build_relative_svg_path(output_path, svg_path),
                    )
                )
            else:
                row_cells.append(
                    create_missing_cell(
                        row_sample=row_sample,
                        col_sample=col_sample,
                        label=label,
                    )
                )

        rows.append(row_cells)

    return rows


def build_pivot_rows(
    sample_names: list[str],
    pivot: str,
    svg_dir: Path,
    output_path: Path,
) -> list[list[GalleryCell]]:
    """Build rows for a pivot-based one-line gallery."""
    row_cells: list[GalleryCell] = [
        GalleryCell(
            cell_type="row_header",
            row_sample=pivot,
            label=pivot,
        )
    ]

    for sample_name in sample_names:
        if sample_name == pivot:
            continue

        pair_id = build_pair_id(pivot, sample_name)
        svg_path = build_svg_path(pair_id, svg_dir)
        label = f"{pivot} vs {sample_name}"

        if svg_path.exists():
            row_cells.append(
                create_plot_cell(
                    row_sample=pivot,
                    col_sample=sample_name,
                    label=label,
                    svg_rel_path=build_relative_svg_path(output_path, svg_path),
                )
            )
        else:
            row_cells.append(
                create_missing_cell(
                    row_sample=pivot,
                    col_sample=sample_name,
                    label=label,
                )
            )

    return [row_cells]


def build_column_headers(sample_names: list[str], pivot: str) -> list[str]:
    """Build column header labels."""
    if pivot:
        return [""] + [sample for sample in sample_names if sample != pivot]
    return [""] + sample_names


def render_column_headers(column_headers: list[str]) -> str:
    """Render HTML for the column header row."""
    parts = ['<div class="corner-cell"></div>']
    for header in column_headers[1:]:
        parts.append(
            f'<div class="col-header">{html.escape(header)}</div>'
        )
    return "\n".join(parts)


def render_gallery_cell(cell: GalleryCell) -> str:
    """Render one gallery cell as HTML."""
    if cell.cell_type == "row_header":
        return f'<div class="row-header">{html.escape(cell.label)}</div>'

    if cell.cell_type == "empty":
        return '<div class="gallery-cell empty-cell"></div>'

    if cell.cell_type == "diagonal":
        return (
            '<div class="gallery-cell diagonal-cell">'
            f'<span>{html.escape(cell.label)}</span>'
            '</div>'
        )

    if cell.cell_type == "missing":
        return (
            '<div class="gallery-cell missing-cell">'
            f'<div class="cell-label">{html.escape(cell.label)}</div>'
            '<div class="missing-note">Missing SVG</div>'
            '</div>'
        )

    return (
        '<div class="gallery-cell plot-cell">'
        f'<div class="cell-label">{html.escape(cell.label)}</div>'
        f'<img src="{html.escape(cell.svg_rel_path)}" '
        f'alt="{html.escape(cell.label)}" loading="lazy" />'
        '</div>'
    )


def render_rows(rows: list[list[GalleryCell]]) -> str:
    """Render all gallery rows as HTML."""
    rendered_cells: list[str] = []

    for row in rows:
        for cell in row:
            rendered_cells.append(render_gallery_cell(cell))

    return "\n".join(rendered_cells)


def infer_grid_column_count(column_headers: list[str]) -> int:
    """Infer the CSS grid column count."""
    return len(column_headers)


def build_html_document(
    sample_names: list[str],
    pivot: str,
    column_headers: list[str],
    rows: list[list[GalleryCell]],
) -> str:
    """Build the full HTML document."""
    mode_label = "pivot" if pivot else "full matrix"
    grid_columns = infer_grid_column_count(column_headers)
    title = "Combined dotplot gallery"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #f6f8fb;
      --panel: #ffffff;
      --border: #d9dee8;
      --text: #1f2937;
      --muted: #6b7280;
      --empty: #eef2f7;
      --missing: #fff3cd;
      --diagonal: #eef6ff;
      --shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}

    .page {{
      padding: 20px;
    }}

    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 20;
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      padding: 12px 0 16px 0;
      background: var(--bg);
    }}

    .toolbar button {{
      border: 1px solid var(--border);
      background: var(--panel);
      color: var(--text);
      border-radius: 8px;
      padding: 8px 12px;
      cursor: pointer;
      box-shadow: var(--shadow);
    }}

    .summary {{
      color: var(--muted);
      font-size: 14px;
      margin-left: 8px;
    }}

    .viewport {{
      overflow: auto;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--panel);
      box-shadow: var(--shadow);
      padding: 16px;
    }}

    .zoom-layer {{
      transform-origin: top left;
      width: fit-content;
    }}

    .gallery-grid {{
      display: grid;
      grid-template-columns: 140px repeat({grid_columns - 1}, minmax(260px, 1fr));
      gap: 12px;
      align-items: start;
      min-width: fit-content;
    }}

    .corner-cell,
    .col-header,
    .row-header,
    .gallery-cell {{
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--panel);
    }}

    .corner-cell {{
      background: transparent;
      border: none;
    }}

    .col-header,
    .row-header {{
      padding: 12px;
      font-weight: 700;
      text-align: center;
      background: #f9fafb;
    }}

    .gallery-cell {{
      padding: 10px;
      min-height: 120px;
    }}

    .plot-cell img {{
      width: 100%;
      height: auto;
      display: block;
      border-radius: 8px;
      background: white;
    }}

    .cell-label {{
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 8px;
      text-align: center;
    }}

    .empty-cell {{
      background: transparent;
      border-style: dashed;
      min-height: 120px;
    }}

    .diagonal-cell {{
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--diagonal);
      font-weight: 700;
      color: var(--muted);
    }}

    .missing-cell {{
      background: var(--missing);
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
    }}

    .missing-note {{
      font-size: 13px;
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <div class="page">
    <div class="toolbar">
      <button type="button" id="zoom-out">-</button>
      <button type="button" id="zoom-in">+</button>
      <button type="button" id="zoom-reset">Reset</button>
      <span class="summary">
        Mode: {html.escape(mode_label)} | Samples: {len(sample_names)}
      </span>
    </div>

    <div class="viewport">
      <div class="zoom-layer" id="zoom-layer">
        <div class="gallery-grid">
          {render_column_headers(column_headers)}
          {render_rows(rows)}
        </div>
      </div>
    </div>
  </div>

  <script>
    const zoomLayer = document.getElementById("zoom-layer");
    const zoomInButton = document.getElementById("zoom-in");
    const zoomOutButton = document.getElementById("zoom-out");
    const zoomResetButton = document.getElementById("zoom-reset");

    let zoomLevel = 1.0;
    const zoomStep = 0.1;
    const zoomMin = 0.2;
    const zoomMax = 4.0;

    function applyZoom() {{
      zoomLayer.style.transform = `scale(${{zoomLevel}})`;
    }}

    function zoomIn() {{
      zoomLevel = Math.min(zoomMax, zoomLevel + zoomStep);
      applyZoom();
    }}

    function zoomOut() {{
      zoomLevel = Math.max(zoomMin, zoomLevel - zoomStep);
      applyZoom();
    }}

    function zoomReset() {{
      zoomLevel = 1.0;
      applyZoom();
    }}

    zoomInButton.addEventListener("click", zoomIn);
    zoomOutButton.addEventListener("click", zoomOut);
    zoomResetButton.addEventListener("click", zoomReset);

    applyZoom();
  </script>
</body>
</html>
"""


def write_html(output_path: Path, content: str) -> None:
    """Write the final HTML document."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def main() -> None:
    """Run the gallery builder."""
    configure_logging()
    args = parse_args()
    config = build_config_from_args(args)
    sample_records = read_samples(config.samples_path)
    sample_names = extract_sample_names(sample_records)
    validate_pivot(sample_names, config.pivot)
    column_headers = build_column_headers(sample_names, config.pivot)

    if config.pivot:
        rows = build_pivot_rows(
            sample_names=sample_names,
            pivot=config.pivot,
            svg_dir=config.svg_dir,
            output_path=config.output_path,
        )
    else:
        rows = build_full_matrix_rows(
            sample_names=sample_names,
            svg_dir=config.svg_dir,
            output_path=config.output_path,
        )

    html_document = build_html_document(
        sample_names=sample_names,
        pivot=config.pivot,
        column_headers=column_headers,
        rows=rows,
    )
    write_html(config.output_path, html_document)
    LOGGER.info("Wrote gallery HTML to %s", config.output_path)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Author: Johanna Girodolle

"""Build a JSON manifest for pairwise dotplot-only SVG files."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Build a JSON manifest for pairwise dotplot-only SVG files."
    )
    parser.add_argument("--samples", required=True, help="Input sample sheet TSV.")
    parser.add_argument("--svg-dir", required=True, help="Directory containing SVG files.")
    parser.add_argument("--output", required=True, help="Output JSON manifest path.")
    return parser.parse_args()


def read_sample_names(samples_path: Path) -> list[str]:
    """Read sample names from a 2- or 3-column sample sheet."""
    sample_names: list[str] = []

    with samples_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for row in reader:
            if not row:
                continue
            if len(row) not in {2, 3}:
                raise ValueError(
                    f"Invalid line in {samples_path}: expected 2 or 3 columns, got {len(row)}."
                )
            sample_names.append(row[1])

    if not sample_names:
        raise ValueError(f"Sample sheet is empty: {samples_path}")

    return sample_names


def build_pair_id(sample_a: str, sample_b: str) -> str:
    """Build the pair identifier used by the dotplot workflow."""
    return f"{sample_a}__vs__{sample_b}"


def build_dotplot_records(
    sample_names: list[str],
    svg_dir: Path,
    output_path: Path,
) -> list[dict[str, str]]:
    """Build manifest records for existing dotplot-only SVG files."""
    records: list[dict[str, str]] = []

    for row_index, row_sample in enumerate(sample_names[:-1]):
        for col_sample in sample_names[row_index + 1:]:
            pair_id = build_pair_id(row_sample, col_sample)
            svg_path = svg_dir / f"{pair_id}.dotplot_only.svg"

            if not svg_path.exists():
                continue

            records.append(
                {
                    "pair_id": pair_id,
                    "x_sample": col_sample,
                    "y_sample": row_sample,
                    "svg_rel_path": os.path.relpath(svg_path, start=output_path.parent),
                }
            )

    return records


def write_manifest(output_path: Path, records: list[dict[str, str]]) -> None:
    """Write the dotplot manifest as JSON."""
    payload = {
        "format_version": 1,
        "dotplots": records,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    """Run the manifest builder."""
    args = parse_args()
    output_path = Path(args.output)

    sample_names = read_sample_names(Path(args.samples))
    records = build_dotplot_records(
        sample_names=sample_names,
        svg_dir=Path(args.svg_dir),
        output_path=output_path,
    )
    write_manifest(output_path, records)


if __name__ == "__main__":
    main()

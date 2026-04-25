#!/usr/bin/env python3
# Author: Johanna Girodolle

"""Filter a long-format SNP table using a selected marker list."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import polars as pl


LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Filter a long-format SNP table by selected block/alignment positions."
    )
    parser.add_argument(
        "--snp-long",
        required=True,
        type=Path,
        help="Input long-format SNP TSV file.",
    )
    parser.add_argument(
        "--selected-markers",
        required=True,
        type=Path,
        help="Input TSV file with at least block_id and aln_pos columns.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output filtered long-format SNP TSV file.",
    )
    return parser.parse_args()


def configure_logging() -> None:
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )


def read_tsv(path: Path) -> pl.DataFrame:
    """Read a TSV file as a Polars dataframe."""
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")

    return pl.read_csv(
        path,
        separator="\t",
        infer_schema_length=0,
    )


def validate_required_columns(
    dataframe: pl.DataFrame,
    required_columns: set[str],
    path: Path,
) -> None:
    """Validate that required columns are present."""
    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required column(s) in {path}: {missing}")


def normalize_marker_columns(dataframe: pl.DataFrame) -> pl.DataFrame:
    """Normalize marker key columns before joining."""
    return dataframe.with_columns(
        pl.col("block_id").cast(pl.Utf8),
        pl.col("aln_pos").cast(pl.Int64),
    )


def filter_snp_long_by_markers(
    snp_long: pl.DataFrame,
    selected_markers: pl.DataFrame,
) -> pl.DataFrame:
    """Keep SNP-long rows matching selected block/alignment positions."""
    required_columns = {"block_id", "aln_pos"}

    validate_required_columns(snp_long, required_columns, Path("--snp-long"))
    validate_required_columns(selected_markers, required_columns, Path("--selected-markers"))

    normalized_snp_long = normalize_marker_columns(snp_long)
    normalized_markers = (
        normalize_marker_columns(selected_markers)
        .select(["block_id", "aln_pos"])
        .unique()
    )

    return normalized_snp_long.join(
        normalized_markers,
        on=["block_id", "aln_pos"],
        how="inner",
    )


def write_tsv(dataframe: pl.DataFrame, output_path: Path) -> None:
    """Write a dataframe to a TSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.write_csv(output_path, separator="\t")


def main() -> None:
    """Run the SNP-long filtering command."""
    configure_logging()
    args = parse_args()

    snp_long = read_tsv(args.snp_long)
    selected_markers = read_tsv(args.selected_markers)

    filtered_snp_long = filter_snp_long_by_markers(
        snp_long=snp_long,
        selected_markers=selected_markers,
    )

    write_tsv(filtered_snp_long, args.output)

    LOGGER.info(
        "Kept %d rows from %d input SNP-long rows using %d selected marker(s).",
        filtered_snp_long.height,
        snp_long.height,
        selected_markers.height,
    )


if __name__ == "__main__":
    main()

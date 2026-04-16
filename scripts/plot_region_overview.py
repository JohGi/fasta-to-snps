#!/usr/bin/env python3
# Author: Johanna Girodolle

"""Generate an interactive Konva-based region overview HTML."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from region_viewer.builder import RegionOverviewBuilder


LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate an interactive Konva-based region overview HTML."
    )
    parser.add_argument("--samples-tsv", type=Path, required=True)
    parser.add_argument("--blocks-gff", type=Path, required=True)
    parser.add_argument("--snp-long", type=Path, required=True)
    parser.add_argument("--fasta-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def setup_logging(log_level: str) -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(levelname)s | %(message)s",
    )


def main() -> None:
    """Run the region overview generator."""
    args = parse_args()
    setup_logging(args.log_level)

    builder = RegionOverviewBuilder(
        samples_tsv_path=args.samples_tsv,
        blocks_gff_path=args.blocks_gff,
        snp_long_path=args.snp_long,
        fasta_dir=args.fasta_dir,
        output_path=args.output,
    )
    builder.run()


if __name__ == "__main__":
    main()

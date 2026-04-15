#!/usr/bin/env python3
"""Write pairwise highlight regions from a filtered GFF file."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from attrs import define, field


LOGGER = logging.getLogger(__name__)


@define(frozen=True)
class GffBlockRecord:
    """Store one GFF block record."""

    sequence_id: str
    start_1based: int
    end_1based: int
    block_id: str


@define
class PairwiseHighlightWriter:
    """Build a highlight TSV for one pair of samples."""

    gff_path: Path
    sample_a: str
    sample_b: str
    color: str
    output_path: Path
    records_by_block: dict[str, dict[str, GffBlockRecord]] = field(factory=dict)

    def run(self) -> None:
        """Run the full highlight generation workflow."""
        self.records_by_block = read_gff_records(self.gff_path)
        rows = self.build_rows()
        write_highlight_rows(rows, self.output_path)

    def build_rows(self) -> list[tuple[str, int, int, str]]:
        """Build highlight rows for the selected pair."""
        rows: list[tuple[str, int, int, str]] = []

        for block_id in sorted(self.records_by_block):
            block_records = self.records_by_block[block_id]

            if self.sample_a not in block_records or self.sample_b not in block_records:
                continue

            record_a = block_records[self.sample_a]
            record_b = block_records[self.sample_b]

            rows.append(
                (
                    record_a.sequence_id,
                    record_a.start_1based - 1,
                    record_a.end_1based,
                    self.color,
                )
            )
            rows.append(
                (
                    record_b.sequence_id,
                    record_b.start_1based - 1,
                    record_b.end_1based,
                    self.color,
                )
            )

        if not rows:
            raise ValueError(
                f"No shared filtered blocks found for pair {self.sample_a!r} vs {self.sample_b!r}"
            )

        return rows


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Write a pairwise highlight TSV from a filtered GFF file."
    )
    parser.add_argument("--gff", required=True, type=Path)
    parser.add_argument("--sample-a", required=True)
    parser.add_argument("--sample-b", required=True)
    parser.add_argument("--color", required=True)
    parser.add_argument("--output", required=True, type=Path)
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


def parse_block_id(attributes: str) -> str:
    """Extract the ID attribute from a GFF attribute column."""
    for item in attributes.split(";"):
        if item.startswith("ID="):
            return item.removeprefix("ID=")
    raise ValueError(f"Could not find ID=... in GFF attributes: {attributes!r}")


def read_gff_records(gff_path: Path) -> dict[str, dict[str, GffBlockRecord]]:
    """Read filtered GFF records grouped by block and sample."""
    records_by_block: dict[str, dict[str, GffBlockRecord]] = {}

    with gff_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue

            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"Invalid GFF line with {len(fields)} columns: {line.rstrip()}")

            sequence_id = fields[0]
            start_1based = int(fields[3])
            end_1based = int(fields[4])
            block_id = parse_block_id(fields[8])

            record = GffBlockRecord(
                sequence_id=sequence_id,
                start_1based=start_1based,
                end_1based=end_1based,
                block_id=block_id,
            )
            records_by_block.setdefault(block_id, {})[sequence_id] = record

    return records_by_block


def write_highlight_rows(
    rows: list[tuple[str, int, int, str]],
    output_path: Path,
) -> None:
    """Write highlight rows to a TSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for sequence_id, start_0based, end_1based, color in rows:
            handle.write(f"{sequence_id}\t{start_0based}\t{end_1based}\t{color}\n")

    LOGGER.info("Wrote %d highlight rows to %s", len(rows), output_path)


def main() -> None:
    """Run the script."""
    args = parse_args()
    setup_logging(args.log_level)

    writer = PairwiseHighlightWriter(
        gff_path=args.gff,
        sample_a=args.sample_a,
        sample_b=args.sample_b,
        color=args.color,
        output_path=args.output,
    )
    writer.run()


if __name__ == "__main__":
    main()

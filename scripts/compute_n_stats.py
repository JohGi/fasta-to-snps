#!/usr/bin/env python3
# Author: Johanna Girodolle

"""Write N-content statistics for one masked block FASTA file."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compute N-content statistics for one masked block FASTA file."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Masked block FASTA file.",
    )
    return parser.parse_args()


def extract_block_id(fasta_path: Path) -> str:
    """Extract the block ID from the FASTA filename."""
    return fasta_path.name.split(".", 1)[0]


def extract_sample_name(header: str) -> str:
    """Extract the sample name from a FASTA header."""
    return header.rsplit(":", 1)[0]


def parse_fasta(fasta_path: Path) -> list[tuple[str, str]]:
    """Parse a FASTA file into header/sequence pairs."""
    records: list[tuple[str, str]] = []
    header: str | None = None
    sequence_parts: list[str] = []

    with fasta_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    records.append((header, "".join(sequence_parts)))
                header = line[1:].strip()
                sequence_parts = []
                continue
            sequence_parts.append(line)

    if header is not None:
        records.append((header, "".join(sequence_parts)))

    return records


def count_n(sequence: str) -> int:
    """Count uppercase and lowercase N characters."""
    return sequence.count("N") + sequence.count("n")


def build_rows(fasta_path: Path) -> list[str]:
    """Build TSV rows for one masked block FASTA file."""
    block_id = extract_block_id(fasta_path)
    rows: list[str] = []

    for sample_header, sequence in parse_fasta(fasta_path):
        sample = extract_sample_name(sample_header)
        length_bp = len(sequence)
        n_count = count_n(sequence)
        n_pct = 0.0 if length_bp == 0 else (n_count / length_bp) * 100
        rows.append(
            f"{block_id}\t{sample}\t{length_bp}\t{n_count}\t{n_pct:.2f}"
        )

    return rows


def main() -> None:
    """Run the script."""
    args = parse_args()
    fasta_path = Path(args.input)

    for row in build_rows(fasta_path):
        print(row)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Author: Johanna Girodolle

from __future__ import annotations

from pathlib import Path

import polars as pl
import logging

from .models import BlockFeature, SampleRecord, SnpFeature


LOGGER = logging.getLogger(__name__)



def read_samples(path: Path) -> list[SampleRecord]:
    """Read the samples TSV."""
    records: list[SampleRecord] = []

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            fields = stripped.split()
            if len(fields) < 2:
                raise ValueError(
                    f"Expected at least 2 columns in samples TSV at line {line_number}: {line.rstrip()}"
                )

            fasta_path = Path(fields[0])
            sample = fields[1]
            zone_start = int(fields[2]) if len(fields) > 2 else 1
            records.append(
                SampleRecord(
                    fasta_path=fasta_path,
                    sample=sample,
                    zone_start_in_source_seq=zone_start,
                )
            )

    if not records:
        raise ValueError(f"Samples TSV is empty: {path}")

    return records


def read_single_fasta_length(path: Path) -> int:
    """Read the sequence length of a single-sequence FASTA."""
    if not path.is_file():
        raise FileNotFoundError(f"FASTA file not found: {path}")

    header_count = 0
    sequence_chunks: list[str] = []

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(">"):
                header_count += 1
                continue
            sequence_chunks.append(stripped)

    if header_count != 1:
        raise ValueError(f"Expected exactly one sequence in FASTA {path}, found {header_count}")

    sequence = "".join(sequence_chunks)
    if not sequence:
        raise ValueError(f"Empty sequence in FASTA: {path}")

    return len(sequence)


def read_fasta_lengths(fasta_dir: Path) -> dict[str, int]:
    """Read lengths from per-sample FASTA files."""
    if not fasta_dir.is_dir():
        raise FileNotFoundError(f"FASTA directory not found: {fasta_dir}")

    lengths: dict[str, int] = {}
    for fasta_path in sorted(fasta_dir.glob("*.fasta")):
        lengths[fasta_path.stem] = read_single_fasta_length(fasta_path)

    if not lengths:
        raise ValueError(f"No FASTA files found in directory: {fasta_dir}")

    return lengths


def parse_block_id(attributes: str) -> str:
    """Extract the block ID from a GFF attribute column."""
    for item in attributes.split(";"):
        if item.startswith("ID="):
            return item.removeprefix("ID=").strip()
    raise ValueError(f"Could not find ID=... in GFF attributes: {attributes!r}")


def read_blocks(path: Path) -> dict[str, list[BlockFeature]]:
    """Read conserved blocks from the filtered GFF."""
    blocks_by_sample: dict[str, list[BlockFeature]] = {}

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            fields = stripped.split("\t")
            if len(fields) != 9:
                raise ValueError(f"Invalid GFF line with {len(fields)} columns: {line.rstrip()}")

            sample = fields[0]
            start = int(fields[3])
            end = int(fields[4])
            block_id = parse_block_id(fields[8])
            blocks_by_sample.setdefault(sample, []).append(
                BlockFeature(sample=sample, block_id=block_id, start=start, end=end)
            )

    return blocks_by_sample


def read_snps(path: Path) -> dict[str, list[SnpFeature]]:
    """Read SNPs from the long-format SNP TSV."""
    dataframe = pl.read_csv(path, separator="\t")
    required_columns = {
        "block_id",
        "aln_pos",
        "sample",
        "nt",
        "pos_in_block",
        "pos_in_zone",
        "pos_in_source_seq",
    }
    missing_columns = required_columns - set(dataframe.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns in SNP TSV {path}: {sorted(missing_columns)}")

    snps_by_sample: dict[str, list[SnpFeature]] = {}
    for row in dataframe.iter_rows(named=True):
        snp = SnpFeature(
            sample=str(row["sample"]),
            block_id=str(row["block_id"]),
            aln_pos=int(row["aln_pos"]),
            nt=str(row["nt"]),
            pos_in_block=int(row["pos_in_block"]),
            pos_in_zone=int(row["pos_in_zone"]),
            pos_in_source_seq=int(row["pos_in_source_seq"]),
        )
        snps_by_sample.setdefault(snp.sample, []).append(snp)

    return snps_by_sample

def write_html(html: str, output_path: Path) -> None:
    """Write the final HTML file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    LOGGER.info("Wrote %s", output_path)

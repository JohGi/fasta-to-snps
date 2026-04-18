#!/usr/bin/env python3
# Author: Johanna Girodolle

from __future__ import annotations

from pathlib import Path

import polars as pl
import json
import logging

from .models import BlockFeature, SampleRecord, SnpFeature, DistanceMatrix


LOGGER = logging.getLogger(__name__)

# FLOAT_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")



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


def read_blocks(path: Path) -> dict[str, list[BlockFeature]]:
    """Read conserved blocks from the enriched block coordinates TSV."""
    dataframe = pl.read_csv(path, separator="\t")

    required_columns = {
        "block_id",
        "sample",
        "block_start_in_zone",
        "block_end_in_zone",
        "block_start_in_source_seq",
        "block_end_in_source_seq",
    }
    missing_columns = required_columns - set(dataframe.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns in block coordinates TSV {path}: {sorted(missing_columns)}"
        )

    blocks_by_sample: dict[str, list[BlockFeature]] = {}
    for row in dataframe.iter_rows(named=True):
        block = BlockFeature(
            sample=str(row["sample"]),
            block_id=str(row["block_id"]),
            block_start_in_zone=int(row["block_start_in_zone"]),
            block_end_in_zone=int(row["block_end_in_zone"]),
            block_start_in_source_seq=int(row["block_start_in_source_seq"]),
            block_end_in_source_seq=int(row["block_end_in_source_seq"]),
        )
        blocks_by_sample.setdefault(block.sample, []).append(block)

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


def read_summary_stats(path: Path) -> dict[str, object]:
    """Read summary statistics from a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_masked_block_n_stats(
    path: Path,
) -> dict[str, dict[str, dict[str, int | float]]]:
    """Read masked block N-content statistics as a nested dictionary."""
    dataframe = pl.read_csv(path, separator="\t")

    stats: dict[str, dict[str, dict[str, int | float]]] = {}

    for row in dataframe.iter_rows(named=True):
        block_id = str(row["block_id"])
        sample = str(row["sample"])

        stats.setdefault(block_id, {})[sample] = {
            "length_bp": int(row["length_bp"]),
            "n_count": int(row["n_count"]),
            "n_pct": float(row["n_pct"]),
        }

    return stats


def normalize_distance(value: float) -> float:
    """Normalize near-zero distances."""
    return 0.0 if abs(value) < 1e-9 else value


def parse_mash_matrix(path: Path, sample_order: list[str]) -> DistanceMatrix:
    """Parse a Mash square distance matrix."""
    rows = path.read_text(encoding="utf-8").splitlines()
    header = rows[0].split("\t")[1:]

    values_by_pair: dict[tuple[str, str], float] = {}

    for row in rows[1:]:
        fields = row.split("\t")
        row_label = fields[0]
        distances = [float(value) for value in fields[1:]]

        for col_label, distance in zip(header, distances):
            values_by_pair[(row_label, col_label)] = normalize_distance(distance)

    values = [
        [
            values_by_pair[(row_label, col_label)]
            for col_label in sample_order
        ]
        for row_label in sample_order
    ]

    return DistanceMatrix(
        labels=sample_order,
        values=values,
        source="mash",
        title="Mash distances, whole region",
        unit="mash_distance",
    )


def parse_emboss_distmat(path: Path, sample_order: list[str], block_id: str) -> DistanceMatrix:
    """Parse an EMBOSS distmat triangular matrix."""
    lines = path.read_text(encoding="utf-8").splitlines()

    labels: list[str] = []
    triangle_rows: list[list[float]] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        tokens = stripped.split()
        if len(tokens) < 2:
            continue

        if not tokens[-1].isdigit():
            continue

        label = tokens[-2]
        numeric_part = tokens[:-2]

        try:
            distances = [normalize_distance(float(value)) for value in numeric_part]
        except ValueError:
            continue

        labels.append(label)
        triangle_rows.append(distances)

    n = len(labels)
    matrix_by_label = {
        label: {other_label: 0.0 for other_label in labels}
        for label in labels
    }

    for row_index, row_values in enumerate(triangle_rows):
        row_label = labels[row_index]

        for offset, distance in enumerate(row_values):
            col_index = row_index + offset
            col_label = labels[col_index]

            matrix_by_label[row_label][col_label] = distance
            matrix_by_label[col_label][row_label] = distance

    values = [
        [
            matrix_by_label[row_label][col_label]
            for col_label in sample_order
        ]
        for row_label in sample_order
    ]

    return DistanceMatrix(
        labels=sample_order,
        values=values,
        source="kimura2p",
        title="Kimura 2P distances",
        unit="substitutions_per_100_bases",
    )


def parse_kimura2p_distmat_dir(
    distmat_dir: Path,
    sample_order: list[str],
) -> dict[str, dict[str, object]]:
    """Parse all Kimura 2P EMBOSS distmat files from a directory."""
    matrices = {}

    for path in sorted(distmat_dir.glob("*.kimura2p.distmat")):
        block_id = path.name.split(".", 1)[0]
        matrices[block_id] = parse_emboss_distmat(
            path=path,
            sample_order=sample_order,
            block_id=block_id,
        ).to_dict()

    return matrices


def write_html(html: str, output_path: Path) -> None:
    """Write the final HTML file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    LOGGER.info("Wrote %s", output_path)

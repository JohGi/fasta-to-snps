#!/usr/bin/env python3
# Author: Johanna Girodolle

from __future__ import annotations

from pathlib import Path

from attrs import define, field

@define(frozen=True)
class SampleRecord:
    """Store one sample definition from the samples TSV."""

    fasta_path: Path
    sample: str
    zone_start_in_source_seq: int = 1


@define(frozen=True)
class BlockFeature:
    """Store one conserved block for one sample."""

    sample: str
    block_id: str
    block_start_in_zone: int
    block_end_in_zone: int
    block_start_in_source_seq: int
    block_end_in_source_seq: int

    @property
    def feature_id(self) -> str:
        """Return a shared feature identifier."""
        return f"block::{self.block_id}"


@define(frozen=True)
class SnpFeature:
    """Store one SNP for one sample."""

    sample: str
    block_id: str
    aln_pos: int
    nt: str
    pos_in_block: int
    pos_in_zone: int
    pos_in_source_seq: int

    @property
    def feature_id(self) -> str:
        """Return a shared feature identifier."""
        return f"snp::{self.block_id}::{self.aln_pos}"


@define(frozen=True)
class SampleData:
    """Store all display data for one sample."""

    sample: str
    zone_length: int
    blocks: list[BlockFeature] = field(factory=list)
    snps: list[SnpFeature] = field(factory=list)


@define(frozen=True)
class DistanceMatrix:
    """Represent a square distance matrix."""

    labels: list[str]
    values: list[list[float]]
    source: str
    title: str
    unit: str

    def to_dict(self) -> dict[str, object]:
        """Convert the distance matrix to a JSON-compatible dictionary."""
        return {
            "labels": self.labels,
            "values": self.values,
            "source": self.source,
            "title": self.title,
            "unit": self.unit,
        }

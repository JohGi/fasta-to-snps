#!/usr/bin/env python3
# Author: Johanna Girodolle

from __future__ import annotations

from pathlib import Path

from attrs import define

from .html_template import build_html

from .payload import (
    build_config_payload,
    build_region_payload,
    build_sample_data,
)
from .io import (
    read_blocks,
    read_fasta_lengths,
    read_samples,
    read_snps,
    write_html,
)

@define
class RegionOverviewBuilder:
    """Build the final Konva HTML from workflow outputs."""

    samples_tsv_path: Path
    blocks_gff_path: Path
    snp_long_path: Path
    fasta_dir: Path
    output_path: Path

    def run(self) -> None:
        """Run the full HTML generation workflow."""
        sample_records = read_samples(self.samples_tsv_path)
        fasta_lengths = read_fasta_lengths(self.fasta_dir)
        blocks_by_sample = read_blocks(self.blocks_gff_path)
        snps_by_sample = read_snps(self.snp_long_path)
        sample_data = build_sample_data(
            sample_records=sample_records,
            fasta_lengths=fasta_lengths,
            blocks_by_sample=blocks_by_sample,
            snps_by_sample=snps_by_sample,
        )
        region_data = build_region_payload(sample_data)
        config = build_config_payload()
        html = build_html(region_data)
        write_html(html, self.output_path)

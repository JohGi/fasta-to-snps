#!/usr/bin/env python3
# Author: Johanna Girodolle

"""Build the region overview HTML from workflow outputs."""

from __future__ import annotations

from pathlib import Path

from attrs import define

from .html_template import build_html
from .io import (
    parse_kimura2p_distmat_dir,
    parse_mash_matrix,
    read_block_alignments,
    read_blocks,
    read_fasta_lengths,
    read_gff_gene_tracks,
    read_gff_tracks_json,
    read_masked_block_n_stats,
    read_samples,
    read_snps,
    read_summary_stats,
    write_html,
)
from .models import BlockFeature
from .payload import build_region_payload, build_sample_data


@define
class RegionOverviewBuilder:
    """Build the final Konva HTML from workflow outputs."""

    samples_tsv_path: Path
    block_coords_tsv_path: Path
    snp_long_path: Path
    fasta_dir: Path
    summary_stats_json_path: Path
    mash_matrix_path: Path
    kimura2p_distmat_dir: Path
    masked_block_n_stats_path: Path
    masked_align_dir: Path
    gff_tracks_json_path: Path
    output_path: Path

    def run(self) -> None:
        """Run the full HTML generation workflow."""
        sample_records = read_samples(self.samples_tsv_path)
        sample_order = [record.sample for record in sample_records]

        fasta_lengths = read_fasta_lengths(self.fasta_dir)
        blocks_by_sample = read_blocks(self.block_coords_tsv_path)
        block_ids = self.get_block_ids(blocks_by_sample)
        block_alignments = read_block_alignments(
            align_dir=self.masked_align_dir,
            block_ids=block_ids,
        )
        snps_by_sample = read_snps(self.snp_long_path)

        summary_stats = read_summary_stats(self.summary_stats_json_path)
        mash_matrix = parse_mash_matrix(
            path=self.mash_matrix_path,
            sample_order=sample_order,
        ).to_dict()
        kimura2p_matrices = parse_kimura2p_distmat_dir(
            distmat_dir=self.kimura2p_distmat_dir,
            sample_order=sample_order,
        )
        masked_block_n_stats = read_masked_block_n_stats(
            self.masked_block_n_stats_path
        )

        sample_data = build_sample_data(
            sample_records=sample_records,
            fasta_lengths=fasta_lengths,
            blocks_by_sample=blocks_by_sample,
            snps_by_sample=snps_by_sample,
        )

        gff_tracks_config = read_gff_tracks_json(self.gff_tracks_json_path)
        gff_tracks_by_sample = read_gff_gene_tracks(
            gff_tracks=gff_tracks_config,
            sample_data=sample_data,
        )

        region_data = build_region_payload(
            sample_data=sample_data,
            summary_stats=summary_stats,
            mash_matrix=mash_matrix,
            kimura2p_matrices=kimura2p_matrices,
            masked_block_n_stats=masked_block_n_stats,
            block_alignments=block_alignments,
            gff_tracks_by_sample=gff_tracks_by_sample,
        )

        html = build_html(region_data)
        write_html(html, self.output_path)

    @staticmethod
    def get_block_ids(blocks_by_sample: dict[str, list[BlockFeature]]) -> list[str]:
        """Return sorted unique block IDs from sample-indexed block records."""
        return sorted(
            {
                block.block_id
                for sample_blocks in blocks_by_sample.values()
                for block in sample_blocks
            }
        )

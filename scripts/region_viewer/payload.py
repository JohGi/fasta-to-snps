#!/usr/bin/env python3
# Author: Johanna Girodolle

from __future__ import annotations

from .models import BlockFeature, SampleData, SampleRecord, SnpFeature

from .constants import (
    BOTTOM_MARGIN,
    FEATURE_HEIGHT,
    LEFT_MARGIN,
    PANEL_GAP,
    PANEL_HEIGHT,
    RIGHT_MARGIN,
    SNP_HEIGHT,
    SNP_LINE_WIDTH,
    TOP_MARGIN,
    TRACK_HEIGHT,
    TRACK_Y_OFFSET,
    VIEWER_MIN_WIDTH,
)

def build_sample_data(
    sample_records: list[SampleRecord],
    fasta_lengths: dict[str, int],
    blocks_by_sample: dict[str, list[BlockFeature]],
    snps_by_sample: dict[str, list[SnpFeature]],
) -> list[SampleData]:
    """Build plotting data in samples TSV order."""
    sample_data: list[SampleData] = []

    for sample_record in sample_records:
        sample = sample_record.sample
        if sample not in fasta_lengths:
            raise ValueError(f"Missing FASTA length for sample {sample!r}")

        sample_data.append(
            SampleData(
                sample=sample,
                zone_length=fasta_lengths[sample],
                blocks=sorted(
                    blocks_by_sample.get(sample, []),
                    key=lambda block: (block.start, block.end, block.block_id),
                ),
                snps=sorted(
                    snps_by_sample.get(sample, []),
                    key=lambda snp: (snp.pos_in_zone, snp.block_id, snp.aln_pos),
                ),
            )
        )

    return sample_data


def build_region_payload(sample_data: list[SampleData]) -> dict[str, object]:
    """Build the JSON payload injected into the HTML."""
    max_zone_length = max(sample.zone_length for sample in sample_data)

    return {
        "title": "Region overview",
        "max_zone_length": max_zone_length,
        "samples": [
            {
                "sample": sample.sample,
                "zone_length": sample.zone_length,
                "blocks": [
                    {
                        "feature_id": block.feature_id,
                        "block_id": block.block_id,
                        "start": block.start,
                        "end": block.end,
                    }
                    for block in sample.blocks
                ],
                "snps": [
                    {
                        "feature_id": snp.feature_id,
                        "block_id": snp.block_id,
                        "aln_pos": snp.aln_pos,
                        "nt": snp.nt,
                        "pos_in_block": snp.pos_in_block,
                        "pos_in_zone": snp.pos_in_zone,
                        "pos_in_source_seq": snp.pos_in_source_seq,
                    }
                    for snp in sample.snps
                ],
            }
            for sample in sample_data
        ],
    }


def build_config_payload() -> dict[str, object]:
    """Build the JavaScript config payload."""
    return {
        "minWidth": VIEWER_MIN_WIDTH,
        "leftMargin": LEFT_MARGIN,
        "rightMargin": RIGHT_MARGIN,
        "topMargin": TOP_MARGIN,
        "bottomMargin": BOTTOM_MARGIN,
        "panelHeight": PANEL_HEIGHT,
        "panelGap": PANEL_GAP,
        "trackY": TRACK_Y_OFFSET,
        "trackHeight": TRACK_HEIGHT,
        "featureHeight": FEATURE_HEIGHT,
        "snpHeight": SNP_HEIGHT,
        "axisTicks": 6,
        "snpStrokeWidth": SNP_LINE_WIDTH,
        "blockFill": "rgba(160,160,160,0.65)",
        "snpColor": "rgb(220,0,0)",
        "highlightColor": "rgb(0,120,255)",
    }

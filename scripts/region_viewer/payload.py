#!/usr/bin/env python3
# Author: Johanna Girodolle

from __future__ import annotations

from .constants import (
    BLOCK_FILL,
    BLOCK_HIGHLIGHT_MIN_WIDTH_PX,
    BLOCK_MIN_WIDTH_PX,
    BOTTOM_MARGIN,
    BP_TO_KB_THRESHOLD_BP,
    END_PADDING_PX,
    FEATURE_HEIGHT,
    HOVER_HIGHLIGHT_COLOR,
    KB_TO_MB_THRESHOLD_BP,
    LEFT_MARGIN,
    MAX_ZOOM_CAP,
    PANEL_GAP,
    PANEL_HEIGHT,
    PIN_HIGHLIGHT_COLOR,
    RIGHT_MARGIN,
    SNP_COLOR,
    SNP_HEIGHT,
    SNP_HIGHLIGHT_MIN_WIDTH_PX,
    SNP_LINE_WIDTH,
    SNP_MIN_WIDTH_PX,
    TARGET_TICK_SPACING_PX,
    TARGET_VISIBLE_BP,
    TOP_MARGIN,
    TRACK_HEIGHT,
    TRACK_Y_OFFSET,
    VIEWER_MIN_WIDTH,
    VIEWER_TOP_UI_HEIGHT,
    ZOOM_STEPS,
    RESIZER_WIDTH,
    SIDEBAR_MAX_WIDTH_RATIO,
    SIDEBAR_MIN_WIDTH,
)
from .models import BlockFeature, SampleData, SampleRecord, SnpFeature, BlockAlignment

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
                    key=lambda block: (
                        block.block_start_in_zone,
                        block.block_end_in_zone,
                        block.block_id,
                    ),
                ),
                snps=sorted(
                    snps_by_sample.get(sample, []),
                    key=lambda snp: (snp.pos_in_zone, snp.block_id, snp.aln_pos),
                ),
            )
        )

    return sample_data


def build_region_payload(
    sample_data: list[SampleData],
    summary_stats: dict[str, object] | None = None,
    mash_matrix: dict[str, object] | None = None,
    kimura2p_matrices: dict[str, dict[str, object]] | None = None,
    masked_block_n_stats: dict[str, dict[str, dict[str, int | float]]] | None = None,
    block_alignments: dict[str, BlockAlignment] | None = None,
) -> dict[str, object]:
    """Build the JSON payload injected into the HTML."""
    max_zone_length = max(sample.zone_length for sample in sample_data)

    payload: dict[str, object] = {
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
                        "block_start_in_zone": block.block_start_in_zone,
                        "block_end_in_zone": block.block_end_in_zone,
                        "block_start_in_source_seq": block.block_start_in_source_seq,
                        "block_end_in_source_seq": block.block_end_in_source_seq,
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
        "summary_stats": summary_stats or {},
        "mash_matrix": mash_matrix or {},
        "kimura2p_matrices": kimura2p_matrices or {},
        "masked_block_n_stats": masked_block_n_stats or {},
        "block_alignments": {
            block_id: alignment.to_payload()
            for block_id, alignment in (block_alignments or {}).items()
        },
    }

    return payload


def build_config_payload() -> dict[str, object]:
    """Build the viewer configuration payload."""
    return {
        "minWidth": VIEWER_MIN_WIDTH,
        "leftMargin": LEFT_MARGIN,
        "rightMargin": RIGHT_MARGIN,
        "topMargin": TOP_MARGIN,
        "bottomMargin": BOTTOM_MARGIN,
        "endPaddingPx": END_PADDING_PX,
        "panelHeight": PANEL_HEIGHT,
        "panelGap": PANEL_GAP,
        "trackY": TRACK_Y_OFFSET,
        "trackHeight": TRACK_HEIGHT,
        "featureHeight": FEATURE_HEIGHT,
        "snpHeight": SNP_HEIGHT,
        "snpStrokeWidth": SNP_LINE_WIDTH,
        "blockFill": BLOCK_FILL,
        "snpColor": SNP_COLOR,
        "viewerTopUiHeight": VIEWER_TOP_UI_HEIGHT,
        "targetVisibleBp": TARGET_VISIBLE_BP,
        "targetTickSpacingPx": TARGET_TICK_SPACING_PX,
        "bpToKbThresholdBp": BP_TO_KB_THRESHOLD_BP,
        "kbToMbThresholdBp": KB_TO_MB_THRESHOLD_BP,
        "maxZoomCap": MAX_ZOOM_CAP,
        "zoomSteps": ZOOM_STEPS,
        "blockMinWidthPx": BLOCK_MIN_WIDTH_PX,
        "blockHighlightMinWidthPx": BLOCK_HIGHLIGHT_MIN_WIDTH_PX,
        "snpMinWidthPx": SNP_MIN_WIDTH_PX,
        "snpHighlightMinWidthPx": SNP_HIGHLIGHT_MIN_WIDTH_PX,
        "pinHighlightColor": PIN_HIGHLIGHT_COLOR,
        "hoverHighlightColor": HOVER_HIGHLIGHT_COLOR,
        "sidebarMinWidth": SIDEBAR_MIN_WIDTH,
        "sidebarMaxWidthRatio": SIDEBAR_MAX_WIDTH_RATIO,
        "resizerWidth": RESIZER_WIDTH,
    }

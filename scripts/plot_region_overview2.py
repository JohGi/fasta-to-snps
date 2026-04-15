#!/usr/bin/env python3
# Author: Johanna Girodolle

"""Generate an interactive region overview HTML using Konva."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import polars as pl
from attrs import define, field


LOGGER = logging.getLogger(__name__)

PANEL_HEIGHT = 90
PANEL_GAP = 28
LEFT_MARGIN = 110
RIGHT_MARGIN = 40
TOP_MARGIN = 30
BOTTOM_MARGIN = 30
TRACK_HEIGHT = 28
TRACK_Y_OFFSET = 18
SNP_LINE_WIDTH = 2
VIEWER_WIDTH = 1400
SIDEBAR_WIDTH = 380


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Region Overview</title>
  <script src="https://unpkg.com/konva@10/konva.min.js"></script>
  <style>
    :root {
      --bg: #ffffff;
      --panel-bg: #fafafa;
      --border: #d9d9d9;
      --text: #1f1f1f;
      --muted: #6b7280;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: Arial, sans-serif;
      color: var(--text);
      background: var(--bg);
    }

    .app {
      display: flex;
      flex-direction: row;
      align-items: flex-start;
      gap: 20px;
      padding: 20px;
    }

    .viewer {
      border: 1px solid var(--border);
      border-radius: 10px;
      background: white;
      overflow: auto;
      max-width: calc(100vw - 500px);
    }

    .sidebar {
      width: %(sidebar_width)spx;
      min-width: %(sidebar_width)spx;
      max-height: calc(100vh - 40px);
      overflow-y: auto;
      padding: 14px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: var(--panel-bg);
    }

    .sidebar h2 {
      margin: 0 0 12px 0;
      font-size: 18px;
    }

    .hint {
      color: var(--muted);
      line-height: 1.4;
      margin: 0;
    }

    .sample-card {
      margin-top: 10px;
      padding: 10px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: white;
    }

    .sample-card h3 {
      margin: 0 0 8px 0;
      font-size: 15px;
    }

    .kv {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 4px 8px;
      font-size: 13px;
    }

    .kv .key {
      color: var(--muted);
    }

    .tooltip {
      position: fixed;
      pointer-events: none;
      z-index: 20;
      display: none;
      max-width: 280px;
      padding: 8px 10px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.96);
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
      font-size: 12px;
      line-height: 1.35;
      white-space: normal;
    }
  </style>
</head>
<body>
  <div class="app">
    <div id="viewer" class="viewer"></div>
    <aside id="sidebar" class="sidebar">
      <h2>Feature info</h2>
      <p class="hint">Hover a block or a SNP to highlight the corresponding feature across all samples.</p>
    </aside>
  </div>
  <div id="tooltip" class="tooltip"></div>

  <script>
    const REGION_DATA = %(region_data)s;
    const CONFIG = %(config)s;

    const state = {
      hoveredFeatureId: null,
      hoveredFeatureType: null,
      featureGroups: new Map(),
      highlightNodes: new Map()
    };

    function buildFeatureGroups(data) {
      const groups = new Map();
      for (const sample of data.samples) {
        for (const block of sample.blocks) {
          const entry = {
            sample: sample.sample,
            featureType: 'block',
            featureId: block.feature_id,
            info: {
              sample: sample.sample,
              block_id: block.block_id,
              start: block.start,
              end: block.end,
              length: block.end - block.start + 1
            }
          };
          if (!groups.has(block.feature_id)) {
            groups.set(block.feature_id, []);
          }
          groups.get(block.feature_id).push(entry);
        }
        for (const snp of sample.snps) {
          const entry = {
            sample: sample.sample,
            featureType: 'snp',
            featureId: snp.feature_id,
            info: {
              sample: sample.sample,
              block_id: snp.block_id,
              aln_pos: snp.aln_pos,
              nt: snp.nt,
              pos_in_block: snp.pos_in_block,
              pos_in_zone: snp.pos_in_zone,
              pos_in_source_seq: snp.pos_in_source_seq
            }
          };
          if (!groups.has(snp.feature_id)) {
            groups.set(snp.feature_id, []);
          }
          groups.get(snp.feature_id).push(entry);
        }
      }
      return groups;
    }

    function buildSidebarDefault() {
      const sidebar = document.getElementById('sidebar');
      sidebar.innerHTML = `
        <h2>Feature info</h2>
        <p class="hint">Hover a block or a SNP to highlight the corresponding feature across all samples.</p>
      `;
    }

    function renderSidebar(featureType, featureId) {
      const sidebar = document.getElementById('sidebar');
      const entries = state.featureGroups.get(featureId) || [];
      if (entries.length === 0) {
        buildSidebarDefault();
        return;
      }

      const kind = featureType === 'snp' ? 'SNP' : 'Block';
      const firstInfo = entries[0].info;
      const title = featureType === 'snp'
        ? `${firstInfo.block_id}:${firstInfo.aln_pos}`
        : `${firstInfo.block_id}`;

      let html = `<h2>${kind}</h2><p class="hint"><b>ID:</b> ${escapeHtml(title)}</p>`;

      for (const sampleName of REGION_DATA.samples.map(sample => sample.sample)) {
        const entry = entries.find(item => item.sample === sampleName);
        html += `<div class="sample-card"><h3>${escapeHtml(sampleName)}</h3>`;
        if (!entry) {
          html += `<p class="hint">No corresponding feature in this sample.</p>`;
        } else {
          html += '<div class="kv">';
          for (const [key, value] of Object.entries(entry.info)) {
            html += `<div class="key">${escapeHtml(key)}</div><div>${escapeHtml(String(value))}</div>`;
          }
          html += '</div>';
        }
        html += '</div>';
      }

      sidebar.innerHTML = html;
    }

    function escapeHtml(text) {
      return String(text)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
    }

    function showTooltip(html, clientX, clientY) {
      const tooltip = document.getElementById('tooltip');
      tooltip.innerHTML = html;
      tooltip.style.display = 'block';
      tooltip.style.left = `${clientX + 12}px`;
      tooltip.style.top = `${clientY + 12}px`;
    }

    function moveTooltip(clientX, clientY) {
      const tooltip = document.getElementById('tooltip');
      if (tooltip.style.display !== 'block') {
        return;
      }
      tooltip.style.left = `${clientX + 12}px`;
      tooltip.style.top = `${clientY + 12}px`;
    }

    function hideTooltip() {
      const tooltip = document.getElementById('tooltip');
      tooltip.style.display = 'none';
      tooltip.innerHTML = '';
    }

    function setHighlight(featureType, featureId) {
      clearHighlight();
      state.hoveredFeatureType = featureType;
      state.hoveredFeatureId = featureId;
      const nodes = state.highlightNodes.get(featureId) || [];
      for (const node of nodes) {
        node.visible(true);
      }
      renderSidebar(featureType, featureId);
      stage.batchDraw();
    }

    function clearHighlight() {
      for (const nodes of state.highlightNodes.values()) {
        for (const node of nodes) {
          node.visible(false);
        }
      }
      state.hoveredFeatureType = null;
      state.hoveredFeatureId = null;
      buildSidebarDefault();
      stage.batchDraw();
    }

    function addHighlightNode(featureId, node) {
      if (!state.highlightNodes.has(featureId)) {
        state.highlightNodes.set(featureId, []);
      }
      state.highlightNodes.get(featureId).push(node);
    }

    function buildFeatureTooltip(featureType, feature) {
      if (featureType === 'block') {
        return [
          `<b>Block ${escapeHtml(feature.block_id)}</b>`,
          `start: ${escapeHtml(feature.start)}`,
          `end: ${escapeHtml(feature.end)}`,
          `length: ${escapeHtml(feature.end - feature.start + 1)}`
        ].join('<br>');
      }

      return [
        `<b>SNP ${escapeHtml(feature.block_id)}:${escapeHtml(feature.aln_pos)}</b>`,
        `nt: ${escapeHtml(feature.nt)}`,
        `pos_in_zone: ${escapeHtml(feature.pos_in_zone)}`,
        `pos_in_source_seq: ${escapeHtml(feature.pos_in_source_seq)}`
      ].join('<br>');
    }

    function attachInteraction(node, featureType, feature) {
      const tooltipHtml = buildFeatureTooltip(featureType, feature);
      node.on('mouseenter', event => {
        document.body.style.cursor = 'pointer';
        setHighlight(featureType, feature.feature_id);
        showTooltip(tooltipHtml, event.evt.clientX, event.evt.clientY);
      });
      node.on('mousemove', event => {
        moveTooltip(event.evt.clientX, event.evt.clientY);
      });
      node.on('mouseleave', () => {
        document.body.style.cursor = 'default';
        hideTooltip();
        clearHighlight();
      });
    }

    function computeTrackWidth() {
      return CONFIG.width - CONFIG.leftMargin - CONFIG.rightMargin;
    }

    function computePanelTop(panelIndex) {
      return CONFIG.topMargin + panelIndex * (CONFIG.panelHeight + CONFIG.panelGap);
    }

    function scaleX(position, zoneLength) {
      const trackWidth = computeTrackWidth();
      if (zoneLength <= 1) {
        return CONFIG.leftMargin;
      }
      return CONFIG.leftMargin + ((position - 1) / (zoneLength - 1)) * trackWidth;
    }

    function drawAxis(layer, panelTop, zoneLength) {
      const x0 = CONFIG.leftMargin;
      const x1 = CONFIG.leftMargin + computeTrackWidth();
      const y0 = panelTop + CONFIG.trackY;
      const y1 = y0 + CONFIG.trackHeight;

      const outline = new Konva.Rect({
        x: x0,
        y: y0,
        width: x1 - x0,
        height: y1 - y0,
        stroke: 'black',
        strokeWidth: 1,
        listening: false
      });
      layer.add(outline);

      for (let i = 0; i <= CONFIG.axisTicks; i += 1) {
        const ratio = i / CONFIG.axisTicks;
        const x = x0 + ratio * (x1 - x0);
        const value = Math.round(1 + ratio * (zoneLength - 1));

        const tick = new Konva.Line({
          points: [x, y1, x, y1 + 5],
          stroke: '#444444',
          strokeWidth: 1,
          listening: false
        });
        const label = new Konva.Text({
          x: x - 18,
          y: y1 + 7,
          width: 60,
          text: formatBp(value),
          fontSize: 10,
          fill: '#555555',
          align: 'center',
          listening: false
        });
        layer.add(tick);
        layer.add(label);
      }
    }

    function formatBp(value) {
      if (value >= 1000000) {
        return `${(value / 1000000).toFixed(1)}M`;
      }
      if (value >= 1000) {
        return `${(value / 1000).toFixed(1)}k`;
      }
      return String(value);
    }

    function drawSampleLabel(layer, panelTop, sampleName) {
      const label = new Konva.Text({
        x: 10,
        y: panelTop + CONFIG.trackY + 4,
        width: CONFIG.leftMargin - 20,
        text: sampleName,
        fontSize: 16,
        fontStyle: 'bold',
        fill: '#222222',
        listening: false
      });
      layer.add(label);
    }

    function createBlockShape(sample, feature, panelTop) {
      const x0 = scaleX(feature.start, sample.zone_length);
      const x1 = scaleX(feature.end, sample.zone_length);
      const y0 = panelTop + CONFIG.trackY;
      return new Konva.Rect({
        x: x0,
        y: y0,
        width: Math.max(1, x1 - x0),
        height: CONFIG.trackHeight,
        fill: CONFIG.blockFill,
        strokeWidth: 0,
        listening: false
      });
    }

    function createBlockHitbox(sample, feature, panelTop) {
      const x0 = scaleX(feature.start, sample.zone_length);
      const x1 = scaleX(feature.end, sample.zone_length);
      const y0 = panelTop + CONFIG.trackY;
      return new Konva.Rect({
        x: x0,
        y: y0,
        width: Math.max(6, x1 - x0),
        height: CONFIG.trackHeight,
        fill: 'rgba(0,0,0,0)'
      });
    }

    function createBlockHighlight(sample, feature, panelTop) {
      const x0 = scaleX(feature.start, sample.zone_length);
      const x1 = scaleX(feature.end, sample.zone_length);
      const y0 = panelTop + CONFIG.trackY;
      return new Konva.Rect({
        x: x0,
        y: y0,
        width: Math.max(1, x1 - x0),
        height: CONFIG.trackHeight,
        stroke: CONFIG.highlightColor,
        strokeWidth: 3,
        visible: false,
        listening: false
      });
    }

    function createSnpLine(sample, feature, panelTop) {
      const x = scaleX(feature.pos_in_zone, sample.zone_length);
      const y0 = panelTop + CONFIG.trackY;
      const y1 = y0 + CONFIG.trackHeight;
      return new Konva.Line({
        points: [x, y0, x, y1],
        stroke: CONFIG.snpColor,
        strokeWidth: CONFIG.snpStrokeWidth,
        listening: false
      });
    }

    function createSnpHitbox(sample, feature, panelTop) {
      const x = scaleX(feature.pos_in_zone, sample.zone_length);
      const y0 = panelTop + CONFIG.trackY;
      return new Konva.Rect({
        x: x - 5,
        y: y0,
        width: 10,
        height: CONFIG.trackHeight,
        fill: 'rgba(0,0,0,0)'
      });
    }

    function createSnpHighlight(sample, feature, panelTop) {
      const x = scaleX(feature.pos_in_zone, sample.zone_length);
      const y0 = panelTop + CONFIG.trackY;
      const y1 = y0 + CONFIG.trackHeight;
      return new Konva.Line({
        points: [x, y0, x, y1],
        stroke: CONFIG.highlightColor,
        strokeWidth: 5,
        visible: false,
        listening: false
      });
    }

    function drawSample(featureLayer, interactionLayer, highlightLayer, sample, panelIndex) {
      const panelTop = computePanelTop(panelIndex);
      drawSampleLabel(featureLayer, panelTop, sample.sample);
      drawAxis(featureLayer, panelTop, sample.zone_length);

      for (const block of sample.blocks) {
        const base = createBlockShape(sample, block, panelTop);
        const hitbox = createBlockHitbox(sample, block, panelTop);
        const highlight = createBlockHighlight(sample, block, panelTop);

        featureLayer.add(base);
        interactionLayer.add(hitbox);
        highlightLayer.add(highlight);

        addHighlightNode(block.feature_id, highlight);
        attachInteraction(hitbox, 'block', block);
      }

      for (const snp of sample.snps) {
        const base = createSnpLine(sample, snp, panelTop);
        const hitbox = createSnpHitbox(sample, snp, panelTop);
        const highlight = createSnpHighlight(sample, snp, panelTop);

        featureLayer.add(base);
        interactionLayer.add(hitbox);
        highlightLayer.add(highlight);

        addHighlightNode(snp.feature_id, highlight);
        attachInteraction(hitbox, 'snp', snp);
      }
    }

    const contentHeight = CONFIG.topMargin
      + REGION_DATA.samples.length * CONFIG.panelHeight
      + Math.max(0, REGION_DATA.samples.length - 1) * CONFIG.panelGap
      + CONFIG.bottomMargin;

    const stage = new Konva.Stage({
      container: 'viewer',
      width: CONFIG.width,
      height: contentHeight
    });

    const backgroundLayer = new Konva.Layer();
    const featureLayer = new Konva.Layer();
    const highlightLayer = new Konva.Layer();
    const interactionLayer = new Konva.Layer();

    backgroundLayer.add(new Konva.Rect({
      x: 0,
      y: 0,
      width: CONFIG.width,
      height: contentHeight,
      fill: 'white',
      listening: false
    }));

    stage.add(backgroundLayer);
    stage.add(featureLayer);
    stage.add(highlightLayer);
    stage.add(interactionLayer);

    state.featureGroups = buildFeatureGroups(REGION_DATA);
    REGION_DATA.samples.forEach((sample, index) => {
      drawSample(featureLayer, interactionLayer, highlightLayer, sample, index);
    });

    buildSidebarDefault();
    stage.draw();
  </script>
</body>
</html>
"""


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
    start: int
    end: int

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
        html = build_html(region_data)
        write_html(html, self.output_path)


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
    return {
        "title": "Region overview",
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
        "width": VIEWER_WIDTH,
        "leftMargin": LEFT_MARGIN,
        "rightMargin": RIGHT_MARGIN,
        "topMargin": TOP_MARGIN,
        "bottomMargin": BOTTOM_MARGIN,
        "panelHeight": PANEL_HEIGHT,
        "panelGap": PANEL_GAP,
        "trackY": TRACK_Y_OFFSET,
        "trackHeight": TRACK_HEIGHT,
        "axisTicks": 6,
        "snpStrokeWidth": SNP_LINE_WIDTH,
        "blockFill": "rgba(160,160,160,0.65)",
        "snpColor": "rgb(220,0,0)",
        "highlightColor": "rgb(0,120,255)",
    }


def build_html(region_data: dict[str, object]) -> str:
    """Render the final HTML document."""
    return HTML_TEMPLATE % {
        "region_data": json.dumps(region_data),
        "config": json.dumps(build_config_payload()),
        "sidebar_width": SIDEBAR_WIDTH,
    }


def write_html(html: str, output_path: Path) -> None:
    """Write the final HTML file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    LOGGER.info("Wrote %s", output_path)


def main() -> None:
    """Run the script."""
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

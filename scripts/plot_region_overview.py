#!/usr/bin/env python3
# Author: Johanna Girodolle

"""Plot an interactive region overview with synchronized hover across samples."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import polars as pl
from attrs import define, field


LOGGER = logging.getLogger(__name__)

ZONE_Y0 = 0.0
ZONE_Y1 = 1.0
BLOCK_Y0 = 0.0
BLOCK_Y1 = 1.0
SNP_Y0 = 0.0
SNP_Y1 = 1.0

BLOCK_FILL_COLOR = "rgba(160,160,160,0.60)"
SNP_COLOR = "rgba(220,0,0,1.0)"
SNP_HOVER_MARKER_COLOR = "rgba(255,0,0,0)"
BLOCK_HOVER_MARKER_COLOR = "rgba(0,0,255,0)"
HIGHLIGHT_COLOR = "rgba(0,120,255,1.0)"

PANEL_HEIGHT_PX = 260
VERTICAL_SPACING = 0.10


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
    def length(self) -> int:
        """Return block length in base pairs."""
        return self.end - self.start + 1

    @property
    def feature_id(self) -> str:
        """Return the shared block identifier."""
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
        """Return the shared SNP identifier."""
        return f"snp::{self.block_id}::{self.aln_pos}"


@define(frozen=True)
class SampleData:
    """Store plotting data for one sample."""

    sample: str
    zone_length: int
    blocks: list[BlockFeature] = field(factory=list)
    snps: list[SnpFeature] = field(factory=list)


@define(frozen=True)
class TraceCoordinates:
    """Store grouped coordinates for one trace."""

    x: list[int | float | None]
    y: list[float | None]


@define(frozen=True)
class HoverTraceData:
    """Store hover marker data for one trace."""

    x: list[int | float]
    y: list[float]
    text: list[str]
    customdata: list[list[str]]


@define(frozen=True)
class HighlightEntry:
    """Store one feature entry used by the synchronized JS highlight."""

    sample: str
    feature_type: str
    feature_id: str
    label: str
    x0: int
    x1: int
    y0: float
    y1: float
    info: dict[str, int | str]


@define
class RegionOverviewPlotter:
    """Build the Plotly figure and export it as an interactive HTML page."""

    samples_tsv_path: Path
    blocks_gff_path: Path
    snp_long_path: Path
    fasta_dir: Path
    output_path: Path

    def run(self) -> None:
        """Run the full workflow."""
        sample_records = read_samples(self.samples_tsv_path)
        fasta_lengths = read_fasta_lengths(self.fasta_dir)
        blocks_by_sample = read_blocks(self.blocks_gff_path)
        snps_by_sample = read_snps(self.snp_long_path)

        data = build_data(
            sample_records=sample_records,
            fasta_lengths=fasta_lengths,
            blocks_by_sample=blocks_by_sample,
            snps_by_sample=snps_by_sample,
        )
        highlight_payload = build_highlight_payload(data)
        figure = build_plot(data)
        write_html_with_js(figure, self.output_path, highlight_payload)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Plot an interactive region overview with synchronized hover across samples."
        )
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

            parts = stripped.split()
            if len(parts) < 2:
                raise ValueError(
                    f"Expected at least 2 columns in samples TSV at line {line_number}: {line.rstrip()}"
                )

            fasta_path = Path(parts[0])
            sample = parts[1]
            zone_start_in_source_seq = int(parts[2]) if len(parts) > 2 else 1
            records.append(
                SampleRecord(
                    fasta_path=fasta_path,
                    sample=sample,
                    zone_start_in_source_seq=zone_start_in_source_seq,
                )
            )

    if not records:
        raise ValueError(f"Samples TSV is empty: {path}")

    return records


def read_single_fasta_length(path: Path) -> int:
    """Read the length of a single-sequence FASTA."""
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
    """Read sequence lengths from cleaned per-sample FASTA files."""
    if not fasta_dir.is_dir():
        raise FileNotFoundError(f"FASTA directory not found: {fasta_dir}")

    lengths: dict[str, int] = {}
    for fasta_path in sorted(fasta_dir.glob("*.fasta")):
        lengths[fasta_path.stem] = read_single_fasta_length(fasta_path)

    if not lengths:
        raise ValueError(f"No FASTA files found in directory: {fasta_dir}")

    return lengths


def parse_block_id(attributes: str) -> str:
    """Extract block ID from a GFF attribute string."""
    for item in attributes.split(";"):
        if item.startswith("ID="):
            return item.removeprefix("ID=").strip()
    raise ValueError(f"Could not find ID=... in GFF attributes: {attributes!r}")


def read_blocks(path: Path) -> dict[str, list[BlockFeature]]:
    """Read block features from the filtered GFF."""
    blocks_by_sample: dict[str, list[BlockFeature]] = {}

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            parts = stripped.split("\t")
            if len(parts) != 9:
                raise ValueError(f"Invalid GFF line with {len(parts)} columns: {line.rstrip()}")

            sample = parts[0]
            start = int(parts[3])
            end = int(parts[4])
            block_id = parse_block_id(parts[8])

            blocks_by_sample.setdefault(sample, []).append(
                BlockFeature(
                    sample=sample,
                    block_id=block_id,
                    start=start,
                    end=end,
                )
            )

    return blocks_by_sample


def read_snps(path: Path) -> dict[str, list[SnpFeature]]:
    """Read SNP features from the long-format SNP TSV."""
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


def build_data(
    sample_records: list[SampleRecord],
    fasta_lengths: dict[str, int],
    blocks_by_sample: dict[str, list[BlockFeature]],
    snps_by_sample: dict[str, list[SnpFeature]],
) -> list[SampleData]:
    """Build per-sample plotting data in sample TSV order."""
    data: list[SampleData] = []

    for sample_record in sample_records:
        sample = sample_record.sample
        if sample not in fasta_lengths:
            raise ValueError(f"Missing FASTA length for sample {sample!r}")

        data.append(
            SampleData(
                sample=sample,
                zone_length=fasta_lengths[sample],
                blocks=sorted(
                    blocks_by_sample.get(sample, []),
                    key=lambda feature: (feature.start, feature.end, feature.block_id),
                ),
                snps=sorted(
                    snps_by_sample.get(sample, []),
                    key=lambda feature: (feature.pos_in_zone, feature.block_id, feature.aln_pos),
                ),
            )
        )

    return data


def build_block_fill_trace_coordinates(blocks: list[BlockFeature]) -> TraceCoordinates:
    """Build grouped polygon coordinates for visible block fills."""
    x_values: list[int | None] = []
    y_values: list[float | None] = []

    for block in blocks:
        x_values.extend([block.start, block.start, block.end, block.end, block.start, None])
        y_values.extend([BLOCK_Y0, BLOCK_Y1, BLOCK_Y1, BLOCK_Y0, BLOCK_Y0, None])

    return TraceCoordinates(x=x_values, y=y_values)


def build_block_hover_trace_data(blocks: list[BlockFeature]) -> HoverTraceData:
    """Build invisible block hover markers."""
    x_values: list[float] = []
    y_values: list[float] = []
    text_values: list[str] = []
    customdata_values: list[list[str]] = []

    for block in blocks:
        x_values.append((block.start + block.end) / 2.0)
        y_values.append(0.25)
        text_values.append(
            "<br>".join(
                [
                    f"sample: {block.sample}",
                    f"block: {block.block_id}",
                    f"start: {block.start}",
                    f"end: {block.end}",
                    f"length: {block.length}",
                ]
            )
        )
        customdata_values.append(["block", block.feature_id, block.sample])

    return HoverTraceData(
        x=x_values,
        y=y_values,
        text=text_values,
        customdata=customdata_values,
    )


def build_snp_line_trace_coordinates(snps: list[SnpFeature]) -> TraceCoordinates:
    """Build grouped coordinates for visible SNP vertical segments."""
    x_values: list[int | None] = []
    y_values: list[float | None] = []

    for snp in snps:
        x_values.extend([snp.pos_in_zone, snp.pos_in_zone, None])
        y_values.extend([SNP_Y0, SNP_Y1, None])

    return TraceCoordinates(x=x_values, y=y_values)


def build_snp_hover_trace_data(snps: list[SnpFeature]) -> HoverTraceData:
    """Build invisible SNP hover markers."""
    x_values: list[int] = []
    y_values: list[float] = []
    text_values: list[str] = []
    customdata_values: list[list[str]] = []

    for snp in snps:
        x_values.append(snp.pos_in_zone)
        y_values.append((SNP_Y0 + SNP_Y1) / 2.0)
        text_values.append(
            "<br>".join(
                [
                    f"sample: {snp.sample}",
                    f"block: {snp.block_id}",
                    f"aln_pos: {snp.aln_pos}",
                    f"nt: {snp.nt}",
                    f"pos_in_block: {snp.pos_in_block}",
                    f"pos_in_zone: {snp.pos_in_zone}",
                    f"pos_in_source_seq: {snp.pos_in_source_seq}",
                ]
            )
        )
        customdata_values.append(["snp", snp.feature_id, snp.sample])

    return HoverTraceData(
        x=x_values,
        y=y_values,
        text=text_values,
        customdata=customdata_values,
    )


def add_zone_trace(figure: go.Figure, row: int, sample_data: SampleData) -> None:
    """Add the zone outline."""
    figure.add_trace(
        go.Scatter(
            x=[1, sample_data.zone_length, sample_data.zone_length, 1, 1],
            y=[ZONE_Y0, ZONE_Y0, ZONE_Y1, ZONE_Y1, ZONE_Y0],
            mode="lines",
            line=dict(color="black", width=1),
            hoverinfo="skip",
            showlegend=False,
        ),
        row=row,
        col=1,
    )


def add_block_fill_trace(figure: go.Figure, row: int, sample_data: SampleData) -> None:
    """Add visible block fills."""
    if not sample_data.blocks:
        return

    coordinates = build_block_fill_trace_coordinates(sample_data.blocks)
    figure.add_trace(
        go.Scatter(
            x=coordinates.x,
            y=coordinates.y,
            mode="lines",
            fill="toself",
            fillcolor=BLOCK_FILL_COLOR,
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=False,
        ),
        row=row,
        col=1,
    )


def add_block_hover_trace(figure: go.Figure, row: int, sample_data: SampleData) -> None:
    """Add invisible block hover markers."""
    if not sample_data.blocks:
        return

    hover_data = build_block_hover_trace_data(sample_data.blocks)
    figure.add_trace(
        go.Scatter(
            x=hover_data.x,
            y=hover_data.y,
            mode="markers",
            marker=dict(size=14, color=BLOCK_HOVER_MARKER_COLOR),
            text=hover_data.text,
            customdata=hover_data.customdata,
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        ),
        row=row,
        col=1,
    )


def add_snp_line_trace(figure: go.Figure, row: int, sample_data: SampleData) -> None:
    """Add visible SNP segments."""
    if not sample_data.snps:
        return

    coordinates = build_snp_line_trace_coordinates(sample_data.snps)
    figure.add_trace(
        go.Scatter(
            x=coordinates.x,
            y=coordinates.y,
            mode="lines",
            line=dict(color=SNP_COLOR, width=2),
            hoverinfo="skip",
            showlegend=False,
        ),
        row=row,
        col=1,
    )


def add_snp_hover_trace(figure: go.Figure, row: int, sample_data: SampleData) -> None:
    """Add invisible SNP hover markers."""
    if not sample_data.snps:
        return

    hover_data = build_snp_hover_trace_data(sample_data.snps)
    figure.add_trace(
        go.Scatter(
            x=hover_data.x,
            y=hover_data.y,
            mode="markers",
            marker=dict(size=12, color=SNP_HOVER_MARKER_COLOR),
            text=hover_data.text,
            customdata=hover_data.customdata,
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        ),
        row=row,
        col=1,
    )


def add_block_highlight_trace(figure: go.Figure, row: int) -> None:
    """Add an initially empty block highlight trace."""
    figure.add_trace(
        go.Scatter(
            x=[],
            y=[],
            mode="lines",
            line=dict(color=HIGHLIGHT_COLOR, width=3),
            hoverinfo="skip",
            showlegend=False,
        ),
        row=row,
        col=1,
    )


def add_snp_highlight_trace(figure: go.Figure, row: int) -> None:
    """Add an initially empty SNP highlight trace."""
    figure.add_trace(
        go.Scatter(
            x=[],
            y=[],
            mode="lines",
            line=dict(color=HIGHLIGHT_COLOR, width=5),
            hoverinfo="skip",
            showlegend=False,
        ),
        row=row,
        col=1,
    )


def build_plot(data: list[SampleData]) -> go.Figure:
    """Build the full multi-sample Plotly figure."""
    figure = make_subplots(
        rows=len(data),
        cols=1,
        shared_xaxes=False,
        vertical_spacing=VERTICAL_SPACING,
        subplot_titles=[sample.sample for sample in data],
    )

    for row_index, sample_data in enumerate(data, start=1):
        add_zone_trace(figure, row_index, sample_data)
        add_block_fill_trace(figure, row_index, sample_data)
        add_snp_line_trace(figure, row_index, sample_data)
        add_block_hover_trace(figure, row_index, sample_data)
        add_snp_hover_trace(figure, row_index, sample_data)
        add_block_highlight_trace(figure, row_index)
        add_snp_highlight_trace(figure, row_index)

        figure.update_xaxes(
            range=[1, sample_data.zone_length],
            row=row_index,
            col=1,
            showgrid=False,
            zeroline=False,
            showline=True,
            ticks="inside",
            title_text="Position in zone (bp)",
        )
        figure.update_yaxes(
            visible=False,
            range=[-0.05, 1.05],
            row=row_index,
            col=1,
        )

    figure.update_layout(
        height=max(450, PANEL_HEIGHT_PX * len(data)),
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="closest",
        margin=dict(l=60, r=30, t=70, b=40),
        title="Region overview",
    )
    return figure


def build_highlight_payload(data: list[SampleData]) -> dict[str, list[HighlightEntry]]:
    """Build the synchronized highlight payload used by the injected JS."""
    payload: dict[str, list[HighlightEntry]] = {}

    for sample_data in data:
        for block in sample_data.blocks:
            payload.setdefault(block.feature_id, []).append(
                HighlightEntry(
                    sample=block.sample,
                    feature_type="block",
                    feature_id=block.feature_id,
                    label=block.block_id,
                    x0=block.start,
                    x1=block.end,
                    y0=BLOCK_Y0,
                    y1=BLOCK_Y1,
                    info={
                        "sample": block.sample,
                        "block_id": block.block_id,
                        "start": block.start,
                        "end": block.end,
                        "length": block.length,
                    },
                )
            )

        for snp in sample_data.snps:
            payload.setdefault(snp.feature_id, []).append(
                HighlightEntry(
                    sample=snp.sample,
                    feature_type="snp",
                    feature_id=snp.feature_id,
                    label=f"{snp.block_id}:{snp.aln_pos}",
                    x0=snp.pos_in_zone,
                    x1=snp.pos_in_zone,
                    y0=SNP_Y0,
                    y1=SNP_Y1,
                    info={
                        "sample": snp.sample,
                        "block_id": snp.block_id,
                        "aln_pos": snp.aln_pos,
                        "nt": snp.nt,
                        "pos_in_block": snp.pos_in_block,
                        "pos_in_zone": snp.pos_in_zone,
                        "pos_in_source_seq": snp.pos_in_source_seq,
                    },
                )
            )

    return payload


def serialize_highlight_payload(
    payload: dict[str, list[HighlightEntry]],
) -> dict[str, list[dict[str, int | float | str | dict[str, int | str]]]]:
    """Convert highlight entries to JSON-serializable dictionaries."""
    serializable: dict[str, list[dict[str, int | float | str | dict[str, int | str]]]] = {}

    for feature_id, entries in payload.items():
        serializable[feature_id] = [
            {
                "sample": entry.sample,
                "feature_type": entry.feature_type,
                "feature_id": entry.feature_id,
                "label": entry.label,
                "x0": entry.x0,
                "x1": entry.x1,
                "y0": entry.y0,
                "y1": entry.y1,
                "info": entry.info,
            }
            for entry in entries
        ]

    return serializable


def build_post_script(
    highlight_payload: dict[str, list[HighlightEntry]],
    sample_names: list[str],
) -> str:
    """Build the injected JavaScript used for synchronized highlight and info display."""
    payload_json = json.dumps(serialize_highlight_payload(highlight_payload))
    sample_names_json = json.dumps(sample_names)

    return f"""
(function() {{
  const gd = document.getElementById('{{plot_id}}');
  const payload = {payload_json};
  const sampleNames = {sample_names_json};

  const plotWrapper = gd.parentNode;
  plotWrapper.style.display = 'flex';
  plotWrapper.style.flexDirection = 'row';
  plotWrapper.style.alignItems = 'flex-start';
  plotWrapper.style.gap = '20px';

  const infoBox = document.createElement('div');
  infoBox.id = 'feature-info-panel';
  infoBox.style.width = '360px';
  infoBox.style.minWidth = '360px';
  infoBox.style.maxHeight = '90vh';
  infoBox.style.overflowY = 'auto';
  infoBox.style.padding = '12px';
  infoBox.style.border = '1px solid #cccccc';
  infoBox.style.borderRadius = '8px';
  infoBox.style.background = '#fafafa';
  infoBox.style.fontFamily = 'sans-serif';
  infoBox.style.fontSize = '13px';
  infoBox.innerHTML = '<b>Feature info</b><br><br>Hover a SNP or a block to highlight it across all samples.';
  plotWrapper.appendChild(infoBox);

  const blockHighlightTraceIndices = [];
  const snpHighlightTraceIndices = [];
  const sampleToPanelIndex = {{}};

  let snpHoverCount = 0;
  let blockHoverCount = 0;
  let snpHighlightCount = 0;
  let blockHighlightCount = 0;

  gd.data.forEach((trace, index) => {{
    const traceName = trace.name || '';
    const traceMode = trace.mode || '';
    if (traceMode === 'markers' && Array.isArray(trace.customdata) && trace.customdata.length > 0) {{
      const first = trace.customdata[0];
      if (Array.isArray(first) && first.length >= 3) {{
        const featureType = first[0];
        const sample = first[2];
        if (!(sample in sampleToPanelIndex)) {{
          sampleToPanelIndex[sample] = Object.keys(sampleToPanelIndex).length;
        }}
        if (featureType === 'snp') {{
          snpHoverCount += 1;
        }}
        if (featureType === 'block') {{
          blockHoverCount += 1;
        }}
      }}
    }}

    if (traceMode === 'lines' && Array.isArray(trace.x) && trace.x.length === 0) {{
      if (trace.line && trace.line.width === 5) {{
        snpHighlightTraceIndices.push(index);
        snpHighlightCount += 1;
      }}
      if (trace.line && trace.line.width === 3) {{
        blockHighlightTraceIndices.push(index);
        blockHighlightCount += 1;
      }}
    }}
  }});

  function getHighlightTraceIndex(featureType, panelIndex) {{
    if (featureType === 'snp') {{
      return snpHighlightTraceIndices[panelIndex];
    }}
    return blockHighlightTraceIndices[panelIndex];
  }}

  function buildRectangleCoordinates(entry) {{
    return {{
      x: [entry.x0, entry.x0, entry.x1, entry.x1, entry.x0, null],
      y: [entry.y0, entry.y1, entry.y1, entry.y0, entry.y0, null]
    }};
  }}

  function buildSegmentCoordinates(entry) {{
    return {{
      x: [entry.x0, entry.x1, null],
      y: [entry.y0, entry.y1, null]
    }};
  }}

  function clearHighlights() {{
    const indices = blockHighlightTraceIndices.concat(snpHighlightTraceIndices);
    const xUpdate = indices.map(() => []);
    const yUpdate = indices.map(() => []);
    Plotly.restyle(gd, {{ x: xUpdate, y: yUpdate }}, indices);
  }}

  function escapeHtml(text) {{
    return String(text)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;');
  }}

  function renderInfo(featureType, featureId) {{
    const entries = payload[featureId] || [];
    if (entries.length === 0) {{
      infoBox.innerHTML = '<b>Feature info</b><br><br>No data available.';
      return;
    }}

    const title = featureType === 'snp' ? 'SNP' : 'Block';
    let html = `<b>${{title}}</b><br><br>`;
    html += `<b>ID:</b> ${{escapeHtml(entries[0].label)}}<br><br>`;

    const entryBySample = {{}};
    entries.forEach(entry => {{
      entryBySample[entry.sample] = entry;
    }});

    sampleNames.forEach(sample => {{
      html += `<div style="margin-bottom:10px;padding:8px;border:1px solid #dddddd;border-radius:6px;background:white;">`;
      html += `<b>${{escapeHtml(sample)}}</b><br>`;
      if (!(sample in entryBySample)) {{
        html += 'No corresponding feature in this sample.';
      }} else {{
        const info = entryBySample[sample].info;
        Object.entries(info).forEach(([key, value]) => {{
          html += `${{escapeHtml(key)}}: ${{escapeHtml(value)}}<br>`;
        }});
      }}
      html += `</div>`;
    }});

    infoBox.innerHTML = html;
  }}

  function applyHighlight(featureType, featureId) {{
    const entries = payload[featureId] || [];
    clearHighlights();
    renderInfo(featureType, featureId);

    const xMap = new Map();
    const yMap = new Map();

    entries.forEach(entry => {{
      const panelIndex = sampleToPanelIndex[entry.sample];
      const traceIndex = getHighlightTraceIndex(featureType, panelIndex);
      let coords = null;

      if (featureType === 'snp') {{
        coords = buildSegmentCoordinates(entry);
      }} else {{
        coords = buildRectangleCoordinates(entry);
      }}

      xMap.set(traceIndex, coords.x);
      yMap.set(traceIndex, coords.y);
    }});

    const traceIndices = Array.from(xMap.keys());
    const xUpdate = traceIndices.map(index => xMap.get(index));
    const yUpdate = traceIndices.map(index => yMap.get(index));
    Plotly.restyle(gd, {{ x: xUpdate, y: yUpdate }}, traceIndices);
  }}

  gd.on('plotly_hover', function(eventData) {{
    if (!eventData || !eventData.points || eventData.points.length === 0) {{
      return;
    }}

    const point = eventData.points[0];
    if (!point.customdata || point.customdata.length < 2) {{
      return;
    }}

    const featureType = point.customdata[0];
    const featureId = point.customdata[1];
    applyHighlight(featureType, featureId);
  }});

  gd.on('plotly_unhover', function() {{
    clearHighlights();
    infoBox.innerHTML = '<b>Feature info</b><br><br>Hover a SNP or a block to highlight it across all samples.';
  }});
}})();
"""


def write_html_with_js(
    figure: go.Figure,
    output_path: Path,
    highlight_payload: dict[str, list[HighlightEntry]],
) -> None:
    """Write the HTML file with injected JavaScript."""
    sample_names = []
    subplot_titles = figure.layout.annotations or []
    for annotation in subplot_titles:
        if hasattr(annotation, "text"):
            sample_names.append(str(annotation.text))

    post_script = build_post_script(highlight_payload, sample_names)
    html = figure.to_html(
        include_plotlyjs=True,
        full_html=True,
        post_script=post_script,
        div_id="region-overview-plot",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    LOGGER.info("Wrote %s", output_path)


def main() -> None:
    """Run the script."""
    args = parse_args()
    setup_logging(args.log_level)

    plotter = RegionOverviewPlotter(
        samples_tsv_path=args.samples_tsv,
        blocks_gff_path=args.blocks_gff,
        snp_long_path=args.snp_long,
        fasta_dir=args.fasta_dir,
        output_path=args.output,
    )
    plotter.run()


if __name__ == "__main__":
    main()

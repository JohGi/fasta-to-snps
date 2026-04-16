#!/usr/bin/env python3
# Author: Johanna Girodolle

"""HTML template rendering for the region overview viewer."""

from __future__ import annotations

import json

from .constants import SIDEBAR_WIDTH
from .payload import build_config_payload


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
      --viewer-top-ui-height: %(viewer_top_ui_height)spx;
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
      flex-direction: column;
      align-items: stretch;
      gap: 16px;
      padding: 20px;
    }

    .info-panel {
      width: 100%%;
      padding: 14px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: var(--panel-bg);
    }

    .info-panel h2 {
      margin: 0 0 12px 0;
      font-size: 18px;
    }

    .content-row {
      display: flex;
      align-items: flex-start;
      gap: 16px;
      width: 100%%;
    }

    .viewer-column {
      flex: 1 1 auto;
      min-width: 0;
      display: flex;
      flex-direction: column;
    }

    .viewer-wrapper {
      position: relative;
      width: 100%%;
    }

    .viewer-toolbar {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: var(--viewer-top-ui-height);
      z-index: 10;
      display: flex;
      justify-content: flex-end;
      align-items: center;
      gap: 8px;
      padding: 8px 10px 0 10px;
      pointer-events: none;
    }

    .viewer-toolbar button {
      padding: 6px 10px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.94);
      color: var(--text);
      cursor: pointer;
      font-size: 13px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      pointer-events: auto;
    }

    .viewer-toolbar button:hover {
      background: #f5f5f5;
    }

    .viewer {
      width: 100%%;
      min-width: 0;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: white;
      overflow: auto;
    }

    .sidebar {
      flex: 0 0 %(sidebar_width)spx;
      width: %(sidebar_width)spx;
      max-height: 80vh;
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
  </style>
</head>
<body>
  <div class="app">
    <section id="info-panel" class="info-panel">
      <h2>Region viewer</h2>
      <p class="hint">Hover a block or a SNP to highlight the corresponding feature across all samples.</p>
    </section>

    <div class="content-row">
      <div class="viewer-column">
        <div class="viewer-wrapper">
          <div class="viewer-toolbar">
            <button id="zoom-out" type="button">−</button>
            <button id="zoom-in" type="button">+</button>
            <button id="zoom-reset" type="button">Reset</button>
          </div>
          <div id="viewer" class="viewer"></div>
        </div>
      </div>

      <aside id="sidebar" class="sidebar">
        <h2>Hovered feature</h2>
        <p class="hint">Hover a block or a SNP to display its details across all samples.</p>
      </aside>
    </div>
  </div>

  <script>
    const REGION_DATA = %(region_data)s;
    const CONFIG = %(config)s;

    const state = {
      hoveredFeatureId: null,
      hoveredFeatureType: null,
      featureGroups: new Map(),
      highlightNodes: new Map(),
      zoomX: 1
    };

    function buildFeatureGroups(data) {
      const groups = new Map();

      for (const sample of data.samples) {
        for (const block of sample.blocks) {
          const entry = {
            sample: sample.sample,
            featureType: "block",
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
            featureType: "snp",
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

    function renderSidebarDefault() {
      const sidebar = document.getElementById("sidebar");
      sidebar.innerHTML = `
        <h2>Hovered feature</h2>
        <p class="hint">Hover a block or a SNP to display its details across all samples.</p>
      `;
    }

    function renderFeatureSidebar(featureType, featureId) {
      const sidebar = document.getElementById("sidebar");
      const entries = state.featureGroups.get(featureId) || [];

      if (entries.length === 0) {
        renderSidebarDefault();
        return;
      }

      const kind = featureType === "snp" ? "SNP" : "Collinear block";
      const firstInfo = entries[0].info;
      const title = featureType === "snp"
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
          const hiddenKeys = new Set(["sample", "block_id", "aln_pos", "pos_in_block"]);

          for (const [key, value] of Object.entries(entry.info)) {
            if (hiddenKeys.has(key)) {
              continue;
            }
            html += `<div class="key">${escapeHtml(key)}</div><div>${escapeHtml(String(value))}</div>`;
          }

          html += "</div>";
        }

        html += "</div>";
      }

      sidebar.innerHTML = html;
    }

    function escapeHtml(text) {
      return String(text)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
    }

    function setHighlight(featureType, featureId) {
      clearHighlight();
      state.hoveredFeatureType = featureType;
      state.hoveredFeatureId = featureId;

      const nodes = state.highlightNodes.get(featureId) || [];
      for (const node of nodes) {
        node.visible(true);
      }

      renderFeatureSidebar(featureType, featureId);
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
      renderSidebarDefault();
      stage.batchDraw();
    }

    function addHighlightNode(featureId, node) {
      if (!state.highlightNodes.has(featureId)) {
        state.highlightNodes.set(featureId, []);
      }
      state.highlightNodes.get(featureId).push(node);
    }

    function attachInteraction(node, featureType, featureId) {
      node.on("mouseenter", () => {
        document.body.style.cursor = "pointer";
        setHighlight(featureType, featureId);
      });

      node.on("mouseleave", () => {
        document.body.style.cursor = "default";
        clearHighlight();
      });
    }

    function getBaseViewerWidth() {
      const viewerElement = document.getElementById("viewer");
      return Math.max(CONFIG.minWidth, viewerElement.clientWidth);
    }

    function getInitialZoomX() {
      const viewerElement = document.getElementById("viewer");
      const availableWidth = viewerElement.clientWidth;

      if (availableWidth <= 0) {
        return 1;
      }

      return availableWidth / getBaseViewerWidth();
    }

    function getMaxZoomX() {
      const theoretical = REGION_DATA.max_zone_length / CONFIG.targetVisibleBp;
      return Math.min(CONFIG.maxZoomCap, Math.max(getInitialZoomX(), theoretical));
    }

    function getZoomFactor() {
      const maxZoom = getMaxZoomX();
      return Math.pow(maxZoom / getInitialZoomX(), 1 / CONFIG.zoomSteps);
    }

    function getStageWidth() {
      return getBaseViewerWidth() * state.zoomX;
    }

    function computeTrackWidth() {
      return getStageWidth() - CONFIG.leftMargin - CONFIG.rightMargin;
    }

    function computePanelTop(panelIndex) {
      return CONFIG.viewerTopUiHeight + CONFIG.topMargin
        + panelIndex * (CONFIG.panelHeight + CONFIG.panelGap);
    }

    function scaleX(position) {
      const trackWidth = computeTrackWidth();
      const globalLength = REGION_DATA.max_zone_length;

      if (globalLength <= 1) {
        return CONFIG.leftMargin;
      }

      return CONFIG.leftMargin + ((position - 1) / (globalLength - 1)) * trackWidth;
    }

    function formatBp(value) {
      if (value >= 1000000) {
        return `${(value / 1000000).toFixed(1)} Mb`;
      }
      if (value >= 1000) {
        return `${(value / 1000).toFixed(1)} kb`;
      }
      return `${value} bp`;
    }

    function niceStep(value) {
      if (value <= 0) {
        return 1;
      }

      const exponent = Math.floor(Math.log10(value));
      const fraction = value / Math.pow(10, exponent);

      let niceFraction;
      if (fraction <= 1) {
        niceFraction = 1;
      } else if (fraction <= 2) {
        niceFraction = 2;
      } else if (fraction <= 5) {
        niceFraction = 5;
      } else {
        niceFraction = 10;
      }

      return niceFraction * Math.pow(10, exponent);
    }

    function drawGlobalAxis(layer) {
      const x0 = CONFIG.leftMargin;
      const x1 = CONFIG.leftMargin + computeTrackWidth();
      const axisY = CONFIG.viewerTopUiHeight + 24;
      const trackWidth = computeTrackWidth();

      const axis = new Konva.Line({
        points: [x0, axisY, x1, axisY],
        stroke: "#444444",
        strokeWidth: 1,
        listening: false
      });
      layer.add(axis);

      const targetPx = CONFIG.targetTickSpacingPx;
      const bpPerPixel = REGION_DATA.max_zone_length / trackWidth;
      const rawStep = bpPerPixel * targetPx;
      const step = niceStep(rawStep);

      for (let value = step; value <= REGION_DATA.max_zone_length; value += step) {
        const x = scaleX(value);

        const tick = new Konva.Line({
          points: [x, axisY, x, axisY + 6],
          stroke: "#444444",
          strokeWidth: 1,
          listening: false
        });

        const label = new Konva.Text({
          x: x - 30,
          y: axisY - 18,
          width: 60,
          text: formatBp(value),
          fontSize: 10,
          fill: "#555555",
          align: "center",
          listening: false
        });

        layer.add(tick);
        layer.add(label);
      }
    }

    function drawSampleLabel(layer, panelTop, sampleName) {
      const label = new Konva.Text({
        x: 10,
        y: panelTop + CONFIG.trackY + 4,
        width: CONFIG.leftMargin - 20,
        text: sampleName,
        fontSize: 16,
        fontStyle: "bold",
        fill: "#222222",
        listening: false
      });
      layer.add(label);
    }

    function drawSampleOutline(layer, sample, panelTop) {
      const x0 = CONFIG.leftMargin;
      const x1 = scaleX(sample.zone_length);
      const y0 = panelTop + CONFIG.trackY;
      const width = Math.max(1, x1 - x0);

      const outline = new Konva.Rect({
        x: x0,
        y: y0,
        width: width,
        height: CONFIG.trackHeight,
        stroke: "black",
        strokeWidth: 1,
        listening: false
      });
      layer.add(outline);
    }

    function getFeatureY(panelTop) {
      return panelTop + CONFIG.trackY + (CONFIG.trackHeight - CONFIG.featureHeight) / 2;
    }

    function getSnpY(panelTop) {
      return panelTop + CONFIG.trackY + (CONFIG.trackHeight - CONFIG.snpHeight) / 2;
    }

    function createBlockShape(sample, feature, panelTop) {
      const x0 = scaleX(feature.start);
      const x1 = scaleX(feature.end);
      const y0 = getFeatureY(panelTop);

      return new Konva.Rect({
        x: x0,
        y: y0,
        width: Math.max(1, x1 - x0),
        height: CONFIG.featureHeight,
        fill: CONFIG.blockFill,
        strokeWidth: 0,
        listening: false
      });
    }

    function createBlockHitbox(sample, feature, panelTop) {
      const x0 = scaleX(feature.start);
      const x1 = scaleX(feature.end);
      const y0 = panelTop + CONFIG.trackY;

      return new Konva.Rect({
        x: x0,
        y: y0,
        width: Math.max(6, x1 - x0),
        height: CONFIG.trackHeight,
        fill: "rgba(0,0,0,0)"
      });
    }

    function createBlockHighlight(sample, feature, panelTop) {
      const x0 = scaleX(feature.start);
      const x1 = scaleX(feature.end);
      const y0 = getFeatureY(panelTop);

      return new Konva.Rect({
        x: x0,
        y: y0,
        width: Math.max(1, x1 - x0),
        height: CONFIG.featureHeight,
        stroke: CONFIG.highlightColor,
        strokeWidth: 1.5,
        visible: false,
        listening: false
      });
    }

    function createSnpLine(sample, feature, panelTop) {
      const x = scaleX(feature.pos_in_zone);
      const y0 = getSnpY(panelTop);
      const y1 = y0 + CONFIG.snpHeight;

      return new Konva.Line({
        points: [x, y0, x, y1],
        stroke: CONFIG.snpColor,
        strokeWidth: CONFIG.snpStrokeWidth,
        listening: false
      });
    }

    function createSnpHitbox(sample, feature, panelTop) {
      const x = scaleX(feature.pos_in_zone);
      const y0 = panelTop + CONFIG.trackY;

      return new Konva.Rect({
        x: x - 5,
        y: y0,
        width: 10,
        height: CONFIG.trackHeight,
        fill: "rgba(0,0,0,0)"
      });
    }

    function createSnpHighlight(sample, feature, panelTop) {
      const x = scaleX(feature.pos_in_zone);
      const y0 = getSnpY(panelTop);
      const y1 = y0 + CONFIG.snpHeight;

      return new Konva.Line({
        points: [x, y0, x, y1],
        stroke: CONFIG.highlightColor,
        strokeWidth: 2,
        visible: false,
        listening: false
      });
    }

    function drawSample(featureLayer, interactionLayer, highlightLayer, sample, panelIndex) {
      const panelTop = computePanelTop(panelIndex);

      drawSampleLabel(featureLayer, panelTop, sample.sample);
      drawSampleOutline(featureLayer, sample, panelTop);

      for (const block of sample.blocks) {
        const base = createBlockShape(sample, block, panelTop);
        const hitbox = createBlockHitbox(sample, block, panelTop);
        const highlight = createBlockHighlight(sample, block, panelTop);

        featureLayer.add(base);
        interactionLayer.add(hitbox);
        highlightLayer.add(highlight);

        addHighlightNode(block.feature_id, highlight);
        attachInteraction(hitbox, "block", block.feature_id);
      }

      for (const snp of sample.snps) {
        const base = createSnpLine(sample, snp, panelTop);
        const hitbox = createSnpHitbox(sample, snp, panelTop);
        const highlight = createSnpHighlight(sample, snp, panelTop);

        featureLayer.add(base);
        interactionLayer.add(hitbox);
        highlightLayer.add(highlight);

        addHighlightNode(snp.feature_id, highlight);
        attachInteraction(hitbox, "snp", snp.feature_id);
      }
    }

    const contentHeight = CONFIG.viewerTopUiHeight
      + CONFIG.topMargin
      + REGION_DATA.samples.length * CONFIG.panelHeight
      + Math.max(0, REGION_DATA.samples.length - 1) * CONFIG.panelGap
      + CONFIG.bottomMargin;

    const stage = new Konva.Stage({
      container: "viewer",
      width: 1,
      height: contentHeight
    });

    const backgroundLayer = new Konva.Layer();
    const featureLayer = new Konva.Layer();
    const highlightLayer = new Konva.Layer();
    const interactionLayer = new Konva.Layer();

    stage.add(backgroundLayer);
    stage.add(featureLayer);
    stage.add(highlightLayer);
    stage.add(interactionLayer);

    function redrawStage() {
      stage.width(getStageWidth());
      stage.height(contentHeight);

      backgroundLayer.destroyChildren();
      featureLayer.destroyChildren();
      highlightLayer.destroyChildren();
      interactionLayer.destroyChildren();

      state.highlightNodes = new Map();

      backgroundLayer.add(new Konva.Rect({
        x: 0,
        y: 0,
        width: getStageWidth(),
        height: contentHeight,
        fill: "white",
        listening: false
      }));

      drawGlobalAxis(featureLayer);

      REGION_DATA.samples.forEach((sample, index) => {
        drawSample(featureLayer, interactionLayer, highlightLayer, sample, index);
      });

      stage.draw();
    }

    function redrawStagePreserveScroll() {
      const viewerElement = document.getElementById("viewer");
      const oldScrollableWidth = Math.max(1, viewerElement.scrollWidth - viewerElement.clientWidth);
      const oldScrollRatio = oldScrollableWidth > 0
        ? viewerElement.scrollLeft / oldScrollableWidth
        : 0;

      redrawStage();

      const newScrollableWidth = Math.max(1, viewerElement.scrollWidth - viewerElement.clientWidth);
      viewerElement.scrollLeft = oldScrollRatio * newScrollableWidth;
    }

    state.featureGroups = buildFeatureGroups(REGION_DATA);
    renderSidebarDefault();
    state.zoomX = getInitialZoomX();
    redrawStage();

    window.addEventListener("resize", () => {
      redrawStagePreserveScroll();
    });

    document.getElementById("zoom-in").addEventListener("click", () => {
      state.zoomX = Math.min(getMaxZoomX(), state.zoomX * getZoomFactor());
      redrawStagePreserveScroll();
    });

    document.getElementById("zoom-out").addEventListener("click", () => {
      state.zoomX = Math.max(getInitialZoomX(), state.zoomX / getZoomFactor());
      redrawStagePreserveScroll();
    });

    document.getElementById("zoom-reset").addEventListener("click", () => {
      state.zoomX = getInitialZoomX();
      redrawStagePreserveScroll();
    });
  </script>
</body>
</html>
"""


def build_html(region_data: dict[str, object]) -> str:
    """Render the final HTML document."""
    config = build_config_payload()
    return HTML_TEMPLATE % {
        "region_data": json.dumps(region_data),
        "config": json.dumps(config),
        "sidebar_width": SIDEBAR_WIDTH,
        "viewer_top_ui_height": config["viewerTopUiHeight"],
    }

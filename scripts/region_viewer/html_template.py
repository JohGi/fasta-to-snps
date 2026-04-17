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
      min-width: 0;
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
      min-width: 0;
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
      overflow: hidden;
      touch-action: none;
      user-select: none;
      cursor: default;
      outline: none;
    }

    .sidebar {
      flex: 0 0 %(sidebar_width)spx;
      width: %(sidebar_width)spx;
      min-width: %(sidebar_width)spx;
      max-width: %(sidebar_width)spx;
      max-height: 80vh;
      overflow-y: scroll;
      scrollbar-gutter: stable;
      padding: 14px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: var(--panel-bg);
    }

    .sidebar-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 12px;
    }

    .sidebar-header h2 {
      margin: 0;
      font-size: 18px;
    }

    .pin-badge {
      display: inline-block;
      margin-top: 6px;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 12px;
      line-height: 1;
      background: #e8f1fb;
      color: #2f5f95;
      border: 1px solid #c7dbf2;
    }

    .sidebar-close {
      border: 1px solid var(--border);
      border-radius: 8px;
      background: white;
      color: var(--text);
      cursor: pointer;
      font-size: 14px;
      line-height: 1;
      padding: 6px 8px;
      flex: 0 0 auto;
    }

    .sidebar-close:hover {
      background: #f5f5f5;
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
      <p class="hint">Hover a block or a SNP to highlight the corresponding feature across all samples. Click a feature to pin it in the sidebar.</p>
    </section>

    <div class="content-row">
      <div class="viewer-column">
        <div class="viewer-wrapper">
          <div class="viewer-toolbar">
            <button id="pan-left" type="button">←</button>
            <button id="pan-right" type="button">→</button>
            <button id="zoom-out" type="button">−</button>
            <button id="zoom-in" type="button">+</button>
            <button id="zoom-reset" type="button">Reset</button>
          </div>
          <div id="viewer" class="viewer" tabindex="0"></div>
        </div>
      </div>

      <aside id="sidebar" class="sidebar">
        <div class="sidebar-header">
          <h2>Hovered feature</h2>
        </div>
        <p class="hint">Hover a block or a SNP to display its details across all samples.</p>
      </aside>
    </div>
  </div>

  <script>
    const REGION_DATA = %(region_data)s;
    const CONFIG = %(config)s;

    const SCROLLBAR = {
      height: 18,
      bottomPadding: 10,
      minThumbWidth: 36,
      trackInset: 8
    };

    const state = {
      hoveredFeatureId: null,
      hoveredFeatureType: null,
      pinnedFeatureId: null,
      pinnedFeatureType: null,
      featureGroups: new Map(),
      highlightNodes: new Map(),
      zoomX: 1,
      scrollX: 0,
      isDraggingViewport: false,
      dragStartPointerX: 0,
      dragStartScrollX: 0,
      isDraggingScrollbar: false,
      scrollbarDragOffsetX: 0,
      suppressHover: false
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

    function escapeHtml(text) {
      return String(text)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
    }

    function clearHighlightMap() {
      state.highlightNodes = new Map();
    }

    function addHighlightNode(featureId, node, featureType) {
      if (!state.highlightNodes.has(featureId)) {
        state.highlightNodes.set(featureId, []);
      }
      state.highlightNodes.get(featureId).push({
        node: node,
        featureType: featureType
      });
    }

    function styleHighlightNode(entry, mode) {
      const node = entry.node;
      const featureType = entry.featureType;
      const color = mode === "pin" ? CONFIG.pinHighlightColor : CONFIG.hoverHighlightColor;

      if (featureType === "block") {
        node.fill(color);
      } else {
        node.stroke(color);
      }
    }

    function hideAllHighlights() {
      for (const entries of state.highlightNodes.values()) {
        for (const entry of entries) {
          entry.node.visible(false);
        }
      }
    }

    function getDisplayedFeature() {
      if (state.hoveredFeatureId && state.hoveredFeatureType) {
        return {
          featureId: state.hoveredFeatureId,
          featureType: state.hoveredFeatureType,
          source: "hover"
        };
      }

      if (state.pinnedFeatureId && state.pinnedFeatureType) {
        return {
          featureId: state.pinnedFeatureId,
          featureType: state.pinnedFeatureType,
          source: "pin"
        };
      }

      return null;
    }

    function applyActiveDisplay() {
      hideAllHighlights();

      const displayed = getDisplayedFeature();
      if (!displayed) {
        renderSidebarDefault();
        stage.batchDraw();
        return;
      }

      const entries = state.highlightNodes.get(displayed.featureId) || [];
      for (const entry of entries) {
        styleHighlightNode(entry, displayed.source);
        entry.node.visible(true);
      }

      renderFeatureSidebar(
        displayed.featureType,
        displayed.featureId,
        displayed.source === "pin"
      );
      stage.batchDraw();
    }

    function renderSidebarDefault() {
      const sidebar = document.getElementById("sidebar");
      sidebar.innerHTML = `
        <div class="sidebar-header">
          <h2>Hovered feature</h2>
        </div>
        <p class="hint">Hover a block or a SNP to display its details across all samples.</p>
      `;
    }

    function renderFeatureSidebar(featureType, featureId, isPinned) {
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

      let header = `
        <div class="sidebar-header">
          <div>
            <h2>${kind}</h2>
            ${isPinned ? '<div class="pin-badge">Pinned</div>' : ""}
          </div>
          ${state.pinnedFeatureId ? '<button id="sidebar-unpin" class="sidebar-close" type="button" aria-label="Unpin feature">✕</button>' : ""}
        </div>
      `;

      let html = `${header}<p class="hint"><b>ID:</b> ${escapeHtml(title)}</p>`;

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

      const unpinButton = document.getElementById("sidebar-unpin");
      if (unpinButton) {
        unpinButton.addEventListener("click", () => {
          clearPinnedFeature();
        });
      }
    }

    function setHoveredFeature(featureType, featureId) {
      state.hoveredFeatureType = featureType;
      state.hoveredFeatureId = featureId;
      applyActiveDisplay();
    }

    function clearHoveredFeature() {
      state.hoveredFeatureType = null;
      state.hoveredFeatureId = null;
      applyActiveDisplay();
    }

    function setPinnedFeature(featureType, featureId) {
      state.pinnedFeatureType = featureType;
      state.pinnedFeatureId = featureId;
      applyActiveDisplay();
    }

    function clearPinnedFeature() {
      state.pinnedFeatureType = null;
      state.pinnedFeatureId = null;
      applyActiveDisplay();
    }

    function reapplyDisplayIfVisible() {
      applyActiveDisplay();
    }

    function attachInteraction(node, featureType, featureId) {
      node.on("mouseenter", () => {
        if (state.suppressHover) {
          return;
        }
        document.body.style.cursor = "pointer";
        setHoveredFeature(featureType, featureId);
      });

      node.on("mouseleave", () => {
        if (state.suppressHover) {
          return;
        }
        document.body.style.cursor = "default";
        clearHoveredFeature();
      });

      node.on("click", (event) => {
        event.cancelBubble = true;
        setPinnedFeature(featureType, featureId);
      });
    }

    function getViewerElement() {
      return document.getElementById("viewer");
    }

    function getStageWidth() {
      const viewerElement = getViewerElement();
      return Math.max(CONFIG.minWidth, viewerElement.clientWidth);
    }

    function getViewportTrackWidth() {
      return getStageWidth() - CONFIG.leftMargin - CONFIG.rightMargin;
    }

    function getDrawableTrackWidth() {
      return Math.max(1, getViewportTrackWidth() - CONFIG.endPaddingPx);
    }

    function getContentWidth() {
      return getDrawableTrackWidth() * state.zoomX;
    }

    function getMaxScrollX() {
      return Math.max(0, getContentWidth() - getDrawableTrackWidth());
    }

    function clampScrollX(value) {
      return Math.max(0, Math.min(getMaxScrollX(), value));
    }

    function normalizeScrollX() {
      state.scrollX = clampScrollX(state.scrollX);
    }

    function getInitialZoomX() {
      return 1;
    }

    function getMaxZoomX() {
      const theoretical = REGION_DATA.max_zone_length / CONFIG.targetVisibleBp;
      return Math.min(CONFIG.maxZoomCap, Math.max(getInitialZoomX(), theoretical));
    }

    function getZoomFactor() {
      const maxZoom = getMaxZoomX();
      return Math.pow(maxZoom / getInitialZoomX(), 1 / CONFIG.zoomSteps);
    }

    function getVisibleBpSpan() {
      return REGION_DATA.max_zone_length / state.zoomX;
    }

    function getMaxVisibleStartBp() {
      return Math.max(1, REGION_DATA.max_zone_length - getVisibleBpSpan() + 1);
    }

    function getVisibleStartBp() {
      const maxScroll = getMaxScrollX();

      if (maxScroll <= 0) {
        return 1;
      }

      const scrollRatio = state.scrollX / maxScroll;
      return 1 + scrollRatio * (getMaxVisibleStartBp() - 1);
    }

    function getVisibleEndBp() {
      return Math.min(
        REGION_DATA.max_zone_length,
        getVisibleStartBp() + getVisibleBpSpan() - 1
      );
    }

    function setVisibleStartBp(targetStartBp) {
      const clampedStart = Math.max(1, Math.min(getMaxVisibleStartBp(), targetStartBp));
      const maxScroll = getMaxScrollX();

      if (maxScroll <= 0) {
        state.scrollX = 0;
        return;
      }

      const startRatio = (clampedStart - 1) / Math.max(1, getMaxVisibleStartBp() - 1);
      state.scrollX = startRatio * maxScroll;
      normalizeScrollX();
    }

    function moveByViewportFraction(direction, fraction = 0.1) {
      const stepBp = getVisibleBpSpan() * fraction;
      const currentStart = getVisibleStartBp();
      setVisibleStartBp(currentStart + direction * stepBp);
      redrawStage();
    }

    function computePanelTop(panelIndex) {
      return CONFIG.viewerTopUiHeight + CONFIG.topMargin
        + panelIndex * (CONFIG.panelHeight + CONFIG.panelGap);
    }

    function getScrollbarY() {
      return contentHeight - SCROLLBAR.bottomPadding - SCROLLBAR.height;
    }

    function getWorldToScreenScale() {
      const visibleSpan = getVisibleBpSpan();
      const drawableWidth = getDrawableTrackWidth();

      if (visibleSpan <= 1) {
        return 0;
      }

      return drawableWidth / (visibleSpan - 1);
    }

    function worldXToScreenX(position) {
      const visibleStart = getVisibleStartBp();
      return CONFIG.leftMargin + (position - visibleStart) * getWorldToScreenScale();
    }

    function formatNumber(value, decimals = 0) {
      const fixed = value.toFixed(decimals);
      const parts = fixed.split(".");

      if (parts.length === 1) {
        return parts[0];
      }

      const trimmedFraction = parts[1].replace(/0+$/, "");
      if (trimmedFraction === "") {
        return parts[0];
      }

      return `${parts[0]}.${trimmedFraction}`;
    }

    function getAxisUnit() {
      const visibleSpan = getVisibleBpSpan();

      if (visibleSpan <= CONFIG.bpToKbThresholdBp) {
        return "bp";
      }

      if (visibleSpan <= CONFIG.kbToMbThresholdBp) {
        return "kb";
      }

      return "Mb";
    }

    function formatAxisValue(value) {
      const unit = getAxisUnit();

      if (unit === "bp") {
        return `${formatNumber(value, 0)} bp`;
      }

      if (unit === "kb") {
        return `${formatNumber(value / 1000, 1)} kb`;
      }

      return `${formatNumber(value / 1000000, 3)} Mb`;
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

    function intersectsRange(start, end, visibleStart, visibleEnd) {
      return end >= visibleStart && start <= visibleEnd;
    }

    function isPositionVisible(position, visibleStart, visibleEnd) {
      return position >= visibleStart && position <= visibleEnd;
    }

    function drawGlobalAxis(layer) {
      const x0 = CONFIG.leftMargin;
      const x1 = CONFIG.leftMargin + getDrawableTrackWidth();
      const axisY = CONFIG.viewerTopUiHeight + 24;

      const axis = new Konva.Line({
        points: [x0, axisY, x1, axisY],
        stroke: "#444444",
        strokeWidth: 1,
        listening: false
      });
      layer.add(axis);

      const visibleStart = getVisibleStartBp();
      const visibleEnd = getVisibleEndBp();
      const visibleSpan = Math.max(1, visibleEnd - visibleStart + 1);

      const targetPx = CONFIG.targetTickSpacingPx;
      const bpPerPixel = visibleSpan / Math.max(1, getDrawableTrackWidth());
      const rawStep = bpPerPixel * targetPx;
      const step = niceStep(rawStep);

      const firstTick = Math.ceil(visibleStart / step) * step;

      for (let value = firstTick; value <= visibleEnd; value += step) {
        const x = worldXToScreenX(value);

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
          text: formatAxisValue(value),
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
      const visibleStart = getVisibleStartBp();
      const visibleEnd = getVisibleEndBp();

      if (!intersectsRange(1, sample.zone_length, visibleStart, visibleEnd)) {
        return;
      }

      const clippedStart = Math.max(1, visibleStart);
      const clippedEnd = Math.min(sample.zone_length, visibleEnd);

      if (clippedEnd < clippedStart) {
        return;
      }

      const x0 = worldXToScreenX(clippedStart);
      const x1 = worldXToScreenX(clippedEnd);
      const yTop = panelTop + CONFIG.trackY;
      const yBottom = yTop + CONFIG.trackHeight;

      layer.add(new Konva.Line({
        points: [x0, yTop, x1, yTop],
        stroke: "black",
        strokeWidth: 1,
        listening: false
      }));

      layer.add(new Konva.Line({
        points: [x0, yBottom, x1, yBottom],
        stroke: "black",
        strokeWidth: 1,
        listening: false
      }));

      if (clippedStart === 1) {
        layer.add(new Konva.Line({
          points: [x0, yTop, x0, yBottom],
          stroke: "black",
          strokeWidth: 1,
          listening: false
        }));
      }

      if (clippedEnd === sample.zone_length) {
        layer.add(new Konva.Line({
          points: [x1, yTop, x1, yBottom],
          stroke: "black",
          strokeWidth: 1,
          listening: false
        }));
      }
    }

    function getFeatureY(panelTop) {
      return panelTop + CONFIG.trackY + 1;
    }

    function getSnpY(panelTop) {
      return panelTop + CONFIG.trackY;
    }

    function getBlockGeometry(feature, panelTop, minWidthPx) {
      const visibleStart = getVisibleStartBp();
      const visibleEnd = getVisibleEndBp();

      const clippedStart = Math.max(feature.start, visibleStart);
      const clippedEnd = Math.min(feature.end, visibleEnd);

      const x0 = worldXToScreenX(clippedStart);
      const x1 = worldXToScreenX(clippedEnd);
      const y0 = getFeatureY(panelTop);

      return {
        x: x0,
        y: y0,
        width: Math.max(minWidthPx, x1 - x0),
        height: CONFIG.featureHeight
      };
    }

    function createBlockShape(feature, panelTop) {
      const geometry = getBlockGeometry(feature, panelTop, CONFIG.blockMinWidthPx);

      return new Konva.Rect({
        x: geometry.x,
        y: geometry.y,
        width: geometry.width,
        height: geometry.height,
        fill: CONFIG.blockFill,
        strokeWidth: 0,
        listening: false
      });
    }

    function createBlockHighlight(feature, panelTop) {
      const visibleStart = getVisibleStartBp();
      const visibleEnd = getVisibleEndBp();

      const clippedStart = Math.max(feature.start, visibleStart);
      const clippedEnd = Math.min(feature.end, visibleEnd);

      const x0 = worldXToScreenX(clippedStart);
      const x1 = worldXToScreenX(clippedEnd);
      const y0 = panelTop + CONFIG.trackY;

      return new Konva.Rect({
        x: x0,
        y: y0,
        width: Math.max(CONFIG.blockHighlightMinWidthPx, x1 - x0),
        height: CONFIG.trackHeight,
        fill: CONFIG.pinHighlightColor,
        strokeWidth: 0,
        visible: false,
        listening: false
      });
    }

    function createBlockHitbox(feature, panelTop) {
      const visibleStart = getVisibleStartBp();
      const visibleEnd = getVisibleEndBp();

      const clippedStart = Math.max(feature.start, visibleStart);
      const clippedEnd = Math.min(feature.end, visibleEnd);

      const x0 = worldXToScreenX(clippedStart);
      const x1 = worldXToScreenX(clippedEnd);
      const y0 = panelTop + CONFIG.trackY;

      return new Konva.Rect({
        x: x0,
        y: y0,
        width: Math.max(6, x1 - x0),
        height: CONFIG.trackHeight,
        fill: "rgba(0,0,0,0)"
      });
    }

    function createSnpLine(feature, panelTop) {
      const x = worldXToScreenX(feature.pos_in_zone);
      const y0 = getSnpY(panelTop);
      const y1 = y0 + CONFIG.snpHeight;

      return new Konva.Line({
        points: [x, y0, x, y1],
        stroke: CONFIG.snpColor,
        strokeWidth: CONFIG.snpMinWidthPx,
        listening: false
      });
    }

    function createSnpHitbox(feature, panelTop) {
      const x = worldXToScreenX(feature.pos_in_zone);
      const y0 = panelTop + CONFIG.trackY;

      return new Konva.Rect({
        x: x - 5,
        y: y0,
        width: 10,
        height: CONFIG.trackHeight,
        fill: "rgba(0,0,0,0)"
      });
    }

    function createSnpHighlight(feature, panelTop) {
      const x = worldXToScreenX(feature.pos_in_zone);
      const y0 = getSnpY(panelTop);
      const y1 = y0 + CONFIG.snpHeight;

      return new Konva.Line({
        points: [x, y0, x, y1],
        stroke: CONFIG.pinHighlightColor,
        strokeWidth: CONFIG.snpHighlightMinWidthPx,
        visible: false,
        listening: false
      });
    }

    function drawSample(
      blockLayer,
      blockHighlightLayer,
      snpLayer,
      snpHighlightLayer,
      zoneOutlineLayer,
      interactionLayer,
      sample,
      panelIndex
    ) {
      const panelTop = computePanelTop(panelIndex);
      const visibleStart = getVisibleStartBp();
      const visibleEnd = getVisibleEndBp();

      drawSampleLabel(blockLayer, panelTop, sample.sample);
      drawSampleOutline(zoneOutlineLayer, sample, panelTop);

      for (const block of sample.blocks) {
        if (!intersectsRange(block.start, block.end, visibleStart, visibleEnd)) {
          continue;
        }

        const base = createBlockShape(block, panelTop);
        const hitbox = createBlockHitbox(block, panelTop);
        const highlight = createBlockHighlight(block, panelTop);

        blockLayer.add(base);
        blockHighlightLayer.add(highlight);
        interactionLayer.add(hitbox);

        addHighlightNode(block.feature_id, highlight, "block");
        attachInteraction(hitbox, "block", block.feature_id);
      }

      for (const snp of sample.snps) {
        if (!isPositionVisible(snp.pos_in_zone, visibleStart, visibleEnd)) {
          continue;
        }

        const base = createSnpLine(snp, panelTop);
        const hitbox = createSnpHitbox(snp, panelTop);
        const highlight = createSnpHighlight(snp, panelTop);

        snpLayer.add(base);
        snpHighlightLayer.add(highlight);
        interactionLayer.add(hitbox);

        addHighlightNode(snp.feature_id, highlight, "snp");
        attachInteraction(hitbox, "snp", snp.feature_id);
      }
    }

    function getScrollbarMetrics() {
      const trackX = CONFIG.leftMargin + SCROLLBAR.trackInset;
      const trackWidth = Math.max(1, getDrawableTrackWidth() - 2 * SCROLLBAR.trackInset);
      const trackY = getScrollbarY();
      const contentWidth = getContentWidth();
      const viewportWidth = getDrawableTrackWidth();

      if (contentWidth <= viewportWidth) {
        return {
          visible: false,
          trackX,
          trackY,
          trackWidth,
          thumbX: trackX,
          thumbWidth: trackWidth
        };
      }

      const ratio = viewportWidth / contentWidth;
      const thumbWidth = Math.max(SCROLLBAR.minThumbWidth, trackWidth * ratio);
      const maxThumbTravel = Math.max(0, trackWidth - thumbWidth);
      const scrollRatio = getMaxScrollX() > 0 ? state.scrollX / getMaxScrollX() : 0;
      const thumbX = trackX + scrollRatio * maxThumbTravel;

      return {
        visible: true,
        trackX,
        trackY,
        trackWidth,
        thumbX,
        thumbWidth
      };
    }

    function drawScrollbar(layer) {
      const metrics = getScrollbarMetrics();

      const track = new Konva.Rect({
        x: metrics.trackX,
        y: metrics.trackY,
        width: metrics.trackWidth,
        height: SCROLLBAR.height,
        fill: "#f0f0f0",
        stroke: "#d0d0d0",
        cornerRadius: 8,
        listening: false
      });
      layer.add(track);

      const thumb = new Konva.Rect({
        x: metrics.thumbX,
        y: metrics.trackY + 1,
        width: metrics.thumbWidth,
        height: SCROLLBAR.height - 2,
        fill: metrics.visible ? "#c2c2c2" : "#e0e0e0",
        stroke: "#b4b4b4",
        cornerRadius: 7
      });

      thumb.on("mouseenter", () => {
        if (!state.isDraggingViewport && !state.isDraggingScrollbar) {
          document.body.style.cursor = "grab";
        }
      });

      thumb.on("mouseleave", () => {
        if (!state.isDraggingViewport && !state.isDraggingScrollbar) {
          document.body.style.cursor = "default";
        }
      });

      thumb.on("pointerdown", (event) => {
        if (!metrics.visible) {
          return;
        }

        event.cancelBubble = true;
        state.isDraggingScrollbar = true;
        state.suppressHover = true;
        document.body.style.cursor = "grabbing";

        const pointer = stage.getPointerPosition();
        state.scrollbarDragOffsetX = pointer.x - metrics.thumbX;
      });

      layer.add(thumb);

      const clickArea = new Konva.Rect({
        x: metrics.trackX,
        y: metrics.trackY,
        width: metrics.trackWidth,
        height: SCROLLBAR.height,
        fill: "rgba(0,0,0,0)"
      });

      clickArea.on("pointerdown", (event) => {
        if (!metrics.visible) {
          return;
        }

        event.cancelBubble = true;
        const pointer = stage.getPointerPosition();
        const centeredThumbX = pointer.x - metrics.thumbWidth / 2;
        setScrollFromThumbX(centeredThumbX);
        redrawStage();
      });

      layer.add(clickArea);
    }

    function setScrollFromThumbX(thumbX) {
      const metrics = getScrollbarMetrics();
      const maxThumbTravel = Math.max(0, metrics.trackWidth - metrics.thumbWidth);

      if (maxThumbTravel <= 0) {
        state.scrollX = 0;
        return;
      }

      const clampedThumbX = Math.max(metrics.trackX, Math.min(metrics.trackX + maxThumbTravel, thumbX));
      const thumbRatio = (clampedThumbX - metrics.trackX) / maxThumbTravel;
      state.scrollX = thumbRatio * getMaxScrollX();
      normalizeScrollX();
    }

    function zoomAroundViewportCenter(nextZoom) {
      const previousZoom = state.zoomX;
      const clampedZoom = Math.max(getInitialZoomX(), Math.min(getMaxZoomX(), nextZoom));

      if (clampedZoom === previousZoom) {
        return;
      }

      const oldVisibleStart = getVisibleStartBp();
      const oldVisibleSpan = getVisibleBpSpan();
      const centerBp = oldVisibleStart + oldVisibleSpan / 2;

      state.zoomX = clampedZoom;

      const newVisibleSpan = getVisibleBpSpan();
      const targetVisibleStart = centerBp - newVisibleSpan / 2;
      setVisibleStartBp(targetVisibleStart);
    }

    const contentHeight = CONFIG.viewerTopUiHeight
      + CONFIG.topMargin
      + REGION_DATA.samples.length * CONFIG.panelHeight
      + Math.max(0, REGION_DATA.samples.length - 1) * CONFIG.panelGap
      + CONFIG.bottomMargin
      + SCROLLBAR.height
      + SCROLLBAR.bottomPadding;

    const stage = new Konva.Stage({
      container: "viewer",
      width: 1,
      height: contentHeight
    });

    const backgroundLayer = new Konva.Layer();
    const blockLayer = new Konva.Layer();
    const snpLayer = new Konva.Layer();
    const blockHighlightLayer = new Konva.Layer();
    const snpHighlightLayer = new Konva.Layer();
    const zoneOutlineLayer = new Konva.Layer();
    const interactionLayer = new Konva.Layer();

    stage.add(backgroundLayer);
    stage.add(blockLayer);
    stage.add(snpLayer);
    stage.add(blockHighlightLayer);
    stage.add(snpHighlightLayer);
    stage.add(zoneOutlineLayer);
    stage.add(interactionLayer);

    function redrawStage() {
      stage.width(getStageWidth());
      stage.height(contentHeight);

      backgroundLayer.destroyChildren();
      blockLayer.destroyChildren();
      snpLayer.destroyChildren();
      blockHighlightLayer.destroyChildren();
      snpHighlightLayer.destroyChildren();
      zoneOutlineLayer.destroyChildren();
      interactionLayer.destroyChildren();

      clearHighlightMap();

      backgroundLayer.add(new Konva.Rect({
        x: 0,
        y: 0,
        width: getStageWidth(),
        height: contentHeight,
        fill: "white",
        listening: false
      }));

      drawGlobalAxis(blockLayer);

      REGION_DATA.samples.forEach((sample, index) => {
        drawSample(
          blockLayer,
          blockHighlightLayer,
          snpLayer,
          snpHighlightLayer,
          zoneOutlineLayer,
          interactionLayer,
          sample,
          index
        );
      });

      drawScrollbar(interactionLayer);
      reapplyDisplayIfVisible();
      stage.draw();
    }

    function startViewportDrag(pointerX) {
      if (getMaxScrollX() <= 0) {
        return;
      }

      state.isDraggingViewport = true;
      state.suppressHover = true;
      state.dragStartPointerX = pointerX;
      state.dragStartScrollX = state.scrollX;
      document.body.style.cursor = "grabbing";
    }

    function updateViewportDrag(pointerX) {
      const deltaX = pointerX - state.dragStartPointerX;
      const worldDelta = deltaX * (getContentWidth() / getDrawableTrackWidth());
      state.scrollX = clampScrollX(state.dragStartScrollX - worldDelta);
      redrawStage();
    }

    function updateScrollbarDrag(pointerX) {
      setScrollFromThumbX(pointerX - state.scrollbarDragOffsetX);
      redrawStage();
    }

    function stopDrag() {
      const wasDragging = state.isDraggingViewport || state.isDraggingScrollbar;
      state.isDraggingViewport = false;
      state.isDraggingScrollbar = false;
      state.scrollbarDragOffsetX = 0;

      if (wasDragging) {
        state.suppressHover = false;
        document.body.style.cursor = "default";
      }
    }

    stage.on("pointerdown", (event) => {
      if (event.target !== stage) {
        return;
      }

      const pointer = stage.getPointerPosition();
      if (!pointer) {
        return;
      }

      const scrollbarY = getScrollbarY();
      if (pointer.y >= scrollbarY) {
        return;
      }

      startViewportDrag(pointer.x);
    });

    stage.on("pointermove", () => {
      const pointer = stage.getPointerPosition();
      if (!pointer) {
        return;
      }

      if (state.isDraggingViewport) {
        updateViewportDrag(pointer.x);
        return;
      }

      if (state.isDraggingScrollbar) {
        updateScrollbarDrag(pointer.x);
        return;
      }

      const scrollbarY = getScrollbarY();
      if (pointer.y < scrollbarY && getMaxScrollX() > 0) {
        document.body.style.cursor = "grab";
      } else {
        document.body.style.cursor = "default";
      }
    });

    stage.on("pointerup", stopDrag);
    stage.on("pointerleave", stopDrag);

    state.featureGroups = buildFeatureGroups(REGION_DATA);
    renderSidebarDefault();
    state.zoomX = getInitialZoomX();
    state.scrollX = 0;
    redrawStage();

    window.addEventListener("resize", () => {
      normalizeScrollX();
      redrawStage();
    });

    document.getElementById("pan-left").addEventListener("click", () => {
      moveByViewportFraction(-1, 0.1);
    });

    document.getElementById("pan-right").addEventListener("click", () => {
      moveByViewportFraction(1, 0.1);
    });

    document.getElementById("zoom-in").addEventListener("click", () => {
      zoomAroundViewportCenter(state.zoomX * getZoomFactor());
      redrawStage();
    });

    document.getElementById("zoom-out").addEventListener("click", () => {
      zoomAroundViewportCenter(state.zoomX / getZoomFactor());
      redrawStage();
    });

    document.getElementById("zoom-reset").addEventListener("click", () => {
      state.zoomX = getInitialZoomX();
      state.scrollX = 0;
      redrawStage();
    });

    window.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        moveByViewportFraction(-1, 0.1);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        moveByViewportFraction(1, 0.1);
      }
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

const REGION_DATA = {{ REGION_DATA }};
const CONFIG = {{ CONFIG }};

const SCROLLBAR = {
  height: 18,
  bottomPadding: 10,
  minThumbWidth: 36,
  trackInset: 8
};

const REGION_VIEWER = {
  axisToFirstSampleGap: 14,
  samplesToLegendGap: 10
};

const ALIGNMENT = {
  leftMargin: 120,
  topMargin: 28,
  rowHeight: 22,
  charWidth: 14,
  minCharWidth: 6,
  maxCharWidth: 28,
  letterFontSize: 9,
  labelFontSize: 13,
  axisHeight: 24,
  bottomPadding: 28,
  scrollbarHeight: 16,
  scrollbarBottomPadding: 8,
  scrollbarMinThumbWidth: 36,
  panFraction: 0.1
};

const GFF_TRACK = {
  height: 12,
  gap: 5,
  topGap: 8,
  labelFontSize: 11,
  minGeneWidthPx: 2,
  colors: [
    "#4e79a7",
    "#f28e2b",
    "#59a14f",
    "#e15759",
    "#76b7b2",
    "#edc948",
    "#b07aa1",
    "#ff9da7",
    "#9c755f",
    "#bab0ab"
  ]
};

const GFF_LEGEND = {
  height: 22,
  dotRadius: 4,
  fontSize: 11,
  itemGap: 16,
  dotTextGap: 6,
  topPadding: 6
};

const SAMPLE_LABEL = {
  x: 24,
  rightPadding: 4,
  fontSize: 16,
  fontStyle: "bold",
  minLeftMargin: 80
};

const SNP_POINTER_TOLERANCE_PX = 8;

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
  suppressHover: false,
  activeAlignmentBlockId: null,
  alignmentZoomX: 1,
  alignmentScrollX: 0,
  isDraggingAlignmentViewport: false,
  isDraggingAlignmentScrollbar: false,
  alignmentDragStartPointerX: 0,
  alignmentDragStartScrollX: 0,
  alignmentScrollbarDragOffsetX: 0,
  alignmentFocusedSnpColumn: null,
  activeKeyboardViewer: "region",
  isHoveringInteractiveFeature: false
};

const derivedData = {
  sampleOrder: [],
  allGffTrackNames: [],
  gffTrackColorByName: new Map(),
  orderedBlockFeatureIds: [],
  orderedSnpFeatureIds: [],
  kimura2pGlobalColorScaleBounds: { min: 0, max: 1 }
};

const lastAlignmentRenderState = {
  blockId: undefined,
  focusedSnpColumn: undefined,
  alignmentZoomX: NaN,
  alignmentScrollX: NaN,
  containerWidth: NaN
};

const lastSidebarRenderState = {
  mode: null,
  featureId: null,
  featureType: null,
  source: null,
  isPinned: false
};

function invalidateSidebarCache() {
  lastSidebarRenderState.mode = null;
  lastSidebarRenderState.featureId = null;
  lastSidebarRenderState.featureType = null;
  lastSidebarRenderState.source = null;
  lastSidebarRenderState.isPinned = false;
}

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
          block_start_in_zone: block.block_start_in_zone,
          block_end_in_zone: block.block_end_in_zone,
          block_start_in_source_seq: block.block_start_in_source_seq,
          block_end_in_source_seq: block.block_end_in_source_seq,
          length: block.block_end_in_zone - block.block_start_in_zone + 1
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

function getOrderedBlockFeatureIds() {
  return derivedData.orderedBlockFeatureIds;
}

function getOrderedSnpFeatureIds() {
  return derivedData.orderedSnpFeatureIds;
}

function getWrappedNeighbor(items, currentItem, direction) {
  if (items.length === 0) {
    return null;
  }

  const currentIndex = items.indexOf(currentItem);
  if (currentIndex === -1) {
    return null;
  }

  const nextIndex = (currentIndex + direction + items.length) % items.length;
  return items[nextIndex];
}

function getPinnedNavigationItems() {
  if (state.pinnedFeatureType === "block") {
    return getOrderedBlockFeatureIds();
  }

  if (state.pinnedFeatureType === "snp") {
    return getOrderedSnpFeatureIds();
  }

  return [];
}

function pinNeighborFeature(direction) {
  if (!state.pinnedFeatureId || !state.pinnedFeatureType) {
    return;
  }

  const items = getPinnedNavigationItems();
  const nextFeatureId = getWrappedNeighbor(
    items,
    state.pinnedFeatureId,
    direction
  );

  if (!nextFeatureId) {
    return;
  }

  setPinnedFeature(state.pinnedFeatureType, nextFeatureId);
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function getSampleOrder() {
  return derivedData.sampleOrder;
}

function estimateTextWidth(text, fontSize) {
  return String(text).length * fontSize * 0.62;
}

function getLongestSampleLabelWidth() {
  return Math.max(
    ...REGION_DATA.samples.map(sample =>
      estimateTextWidth(sample.sample, SAMPLE_LABEL.fontSize)
    ),
    0
  );
}

function getLeftMargin() {
  return Math.max(
    SAMPLE_LABEL.minLeftMargin,
    SAMPLE_LABEL.x + getLongestSampleLabelWidth() + SAMPLE_LABEL.rightPadding
  );
}

function getSampleGffTracks(sample) {
  return sample.gff_tracks || [];
}

function getAllGffTrackNames() {
  return derivedData.allGffTrackNames;
}

function getGffTrackColor(trackName) {
  return derivedData.gffTrackColorByName.get(trackName) ?? "#9ca3af";
}

function getSamplePanelHeight(sample) {
  const gffTrackCount = getSampleGffTracks(sample).length;

  return CONFIG.panelHeight
    + gffTrackCount * (GFF_TRACK.height + GFF_TRACK.gap);
}

function getGffLegendHeight() {
  return getAllGffTrackNames().length > 0 ? GFF_LEGEND.height : 0;
}

function getMainViewerContentHeight() {
  const sampleHeights = REGION_DATA.samples.reduce(
    (total, sample) => total + getSamplePanelHeight(sample),
    0
  );

  return getViewerToolbarHeight()
    + CONFIG.topMargin
    + REGION_VIEWER.axisToFirstSampleGap
    + sampleHeights
    + Math.max(0, REGION_DATA.samples.length - 1) * CONFIG.panelGap
    + REGION_VIEWER.samplesToLegendGap
    + getGffLegendHeight()
    + CONFIG.bottomMargin
    + SCROLLBAR.height
    + SCROLLBAR.bottomPadding;
}

function getSamplesBottomY() {
  const sampleHeights = REGION_DATA.samples.reduce(
    (total, sample) => total + getSamplePanelHeight(sample),
    0
  );

  return getViewerToolbarHeight()
    + CONFIG.topMargin
    + REGION_VIEWER.axisToFirstSampleGap
    + sampleHeights
    + Math.max(0, REGION_DATA.samples.length - 1) * CONFIG.panelGap;
}

function getGffLegendY() {
  return getSamplesBottomY() + REGION_VIEWER.samplesToLegendGap;
}

function drawGffTrackLegend(layer) {
  const trackNames = getAllGffTrackNames();

  if (trackNames.length === 0) {
    return;
  }

  let x = getLeftMargin();
  const y = getGffLegendY() + GFF_LEGEND.topPadding;

  for (const trackName of trackNames) {
    const color = getGffTrackColor(trackName);
    const textWidth = estimateTextWidth(trackName, GFF_LEGEND.fontSize);

    layer.add(new Konva.Circle({
      x: x + GFF_LEGEND.dotRadius,
      y: y + GFF_LEGEND.fontSize / 2,
      radius: GFF_LEGEND.dotRadius,
      fill: color,
      listening: false
    }));

    layer.add(new Konva.Text({
      x: x + GFF_LEGEND.dotRadius * 2 + GFF_LEGEND.dotTextGap,
      y,
      text: trackName,
      fontSize: GFF_LEGEND.fontSize,
      fill: "#4b5563",
      listening: false
    }));

    x += GFF_LEGEND.dotRadius * 2
      + GFF_LEGEND.dotTextGap
      + textWidth
      + GFF_LEGEND.itemGap;
  }
}

function formatDistanceValue(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "NA";
  }

  const numericValue = Number(value);
  const normalizedValue = Math.abs(numericValue) < 1e-9 ? 0 : numericValue;

  if (Math.abs(normalizedValue) >= 10) {
    return formatNumber(normalizedValue, 1);
  }

  if (Math.abs(normalizedValue) >= 1) {
    return formatNumber(normalizedValue, 2);
  }

  return formatNumber(normalizedValue, 4);
}

function getMatrixColorScaleBounds(matrix) {
  const values = [];

  matrix.values.forEach((row, rowIndex) => {
    row.forEach((value, colIndex) => {
      if (rowIndex === colIndex) {
        return;
      }

      const numericValue = Number(value);
      if (!Number.isNaN(numericValue)) {
        values.push(numericValue);
      }
    });
  });

  if (values.length === 0) {
    return { min: 0, max: 1 };
  }

  return {
    min: Math.min(...values),
    max: Math.max(...values)
  };
}

function getKimura2pGlobalColorScaleBounds() {
  return derivedData.kimura2pGlobalColorScaleBounds;
}

function interpolateChannel(start, end, ratio) {
  return Math.round(start + (end - start) * ratio);
}

function interpolateRgb(start, end, ratio) {
  return [
    interpolateChannel(start[0], end[0], ratio),
    interpolateChannel(start[1], end[1], ratio),
    interpolateChannel(start[2], end[2], ratio)
  ];
}

function matrixCellColor(value, minValue, maxValue, isDiagonal) {
  if (isDiagonal) {
    return "rgb(102, 190, 125)";
  }

  const numericValue = Number(value);
  if (Number.isNaN(numericValue) || maxValue <= minValue) {
    return "#ffffff";
  }

  const ratio = Math.max(0, Math.min(1, (numericValue - minValue) / (maxValue - minValue)));

  const green = [102, 190, 125];
  const yellow = [255, 235, 132];
  const orange = [248, 172, 89];

  const rgb = ratio <= 0.5
    ? interpolateRgb(green, yellow, ratio / 0.5)
    : interpolateRgb(yellow, orange, (ratio - 0.5) / 0.5);

  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

function getDistanceMatrixTooltip(matrix) {
  if (matrix.source === "kimura2p") {
    return `Values are substitutions per base (Kimura 2-parameter).\nComputed from unmasked block alignments using EMBOSS distmat (-nucmethod 2), scaled from per 100 bases.`;
  }

  return "";
}

function renderInfoTooltip(text) {
  if (!text) {
    return "";
  }

  return `<span class="info-tooltip" data-tooltip="${escapeHtml(text)}">Info</span>`;
}

function renderDistanceMatrix(matrix) {
  if (!matrix || !matrix.labels || !matrix.values) {
    return `
      <div class="distance-matrix-card">
        <p class="hint">No distance matrix available.</p>
      </div>
    `;
  }

  const labels = matrix.labels;
  const tooltip = getDistanceMatrixTooltip(matrix);
  const colorScale = matrix.source === "kimura2p"
    ? getKimura2pGlobalColorScaleBounds()
    : getMatrixColorScaleBounds(matrix);

  let html = `
    <div class="distance-matrix-card">
      <p class="distance-matrix-title">
        ${escapeHtml(matrix.title || "Distance matrix")}
        ${renderInfoTooltip(tooltip)}
      </p>
      <div class="distance-matrix-scroll">
        <table class="distance-matrix-table">
          <thead>
            <tr>
              <th></th>
  `;

  for (const label of labels) {
    html += `<th>${escapeHtml(label)}</th>`;
  }

  html += `
            </tr>
          </thead>
          <tbody>
  `;

  labels.forEach((rowLabel, rowIndex) => {
    html += `<tr><th class="row-label">${escapeHtml(rowLabel)}</th>`;

    labels.forEach((_colLabel, colIndex) => {
      if (colIndex < rowIndex) {
        html += `<td class="matrix-empty"></td>`;
        return;
      }

      const value = matrix.values[rowIndex]?.[colIndex];
      const backgroundColor = matrixCellColor(
        value,
        colorScale.min,
        colorScale.max,
        rowIndex === colIndex
      );

      html += `<td style="background-color: ${backgroundColor};">${escapeHtml(formatDistanceValue(value))}</td>`;
    });

    html += `</tr>`;
  });

  html += `
          </tbody>
        </table>
      </div>
    </div>
  `;

  return html;
}

function renderGlobalSummaryStats() {
  const globalStats = REGION_DATA.summary_stats?.global;

  if (!globalStats) {
    return `
      <div class="summary-card">
        <h3>Global statistics</h3>
        <p class="hint">No summary statistics available.</p>
      </div>
    `;
  }

  const entries = [
    ["Kept blocks", globalStats.n_blocks_kept],
    ["Smallest block (bp)", globalStats.min_block_len_bp],
    ["Largest block (bp)", globalStats.max_block_len_bp],
    ["Mean block length (bp)", globalStats.mean_block_len_bp],
    ["Kept SNPs", globalStats.n_snps_kept]
  ];

  let html = `
    <div class="summary-card">
      <h3>Global statistics</h3>
      <div class="kv">
  `;

  for (const [label, value] of entries) {
    html += `<div class="key">${escapeHtml(label)}</div><div>${escapeHtml(value)}</div>`;
  }

  html += `
      </div>
    </div>
  `;

  return html;
}

function formatSnpGroups(settings) {
  const groupA = settings.snp_group_a || [];
  const groupB = settings.snp_group_b || [];

  if (groupA.length === 0 && groupB.length === 0) {
    return "none";
  }

  if (groupA.length === 0) {
    return `all other samples vs ${groupB.join(", ")}`;
  }

  if (groupB.length === 0) {
    return `${groupA.join(", ")} vs all other samples`;
  }

  return `${groupA.join(", ")} vs ${groupB.join(", ")}`;
}

function renderAnalysisSettings() {
  const settings = REGION_DATA.analysis_settings;
  const container = document.getElementById("analysis-settings-content");

  if (!container) {
    return;
  }

  if (!settings || Object.keys(settings).length === 0) {
    return;
  }

  const minBlock = settings.minimum_block_length_bp !== null && settings.minimum_block_length_bp !== undefined
    ? `${settings.minimum_block_length_bp} bp`
    : "NA";

  const minFlank = settings.minimum_snp_flank_bp !== null && settings.minimum_snp_flank_bp !== undefined
    ? `${settings.minimum_snp_flank_bp} bp`
    : "NA";

  const snpGroups = formatSnpGroups(settings);

  const entries = [
    ["Minimum block length", minBlock],
    ["Minimum SNP flank", minFlank],
    ["SNP filtering groups", snpGroups]
  ];

  let html = `<div class="summary-card"><div class="kv">`;

  for (const [label, value] of entries) {
    html += `<div class="key">${escapeHtml(label)}</div><div>${escapeHtml(value)}</div>`;
  }

  html += `</div></div>`;

  container.innerHTML = html;
}

function renderSampleRegionStats() {
  const sampleStats = REGION_DATA.summary_stats?.samples;

  if (!sampleStats || Object.keys(sampleStats).length === 0) {
    return `
      <div class="summary-card">
        <h3>Sample region statistics</h3>
        <p class="hint">No per-sample region statistics available.</p>
      </div>
    `;
  }

  let html = `<div class="summary-card"><h3>Sample region statistics</h3>`;

  for (const sampleName of getSampleOrder()) {
    const stats = sampleStats[sampleName];
    html += `<div class="sample-card"><h3>${escapeHtml(sampleName)}</h3>`;

    if (!stats) {
      html += `<p class="hint">No data.</p>`;
    } else {
      const entries = [
        ["Zone length (bp)", stats.zone_length_bp],
        ["Covered by blocks (%)", `${formatNumber(Number(stats.covered_pct_of_zone), 2)}%`]
      ];

      html += `<div class="kv">`;
      for (const [label, value] of entries) {
        html += `<div class="key">${escapeHtml(label)}</div><div>${escapeHtml(String(value))}</div>`;
      }
      html += `</div>`;
    }

    html += `</div>`;
  }

  html += `</div>`;
  return html;
}

function getMaskedNStats(blockId, sampleName) {
  return REGION_DATA.masked_block_n_stats?.[String(blockId)]?.[sampleName] || null;
}

function formatFeatureInfoEntries(featureType, info) {
  if (featureType === "block") {
    return [
      ["Coords in zone", `${info.block_start_in_zone}-${info.block_end_in_zone}`],
      [
        "Coords in source seq",
        `${info.block_start_in_source_seq}-${info.block_end_in_source_seq}`
      ],
      ["Length", String(info.length)]
    ];
  }

  return [
    ["Allele", String(info.nt)],
    ["Pos in zone", String(info.pos_in_zone)],
    ["Pos in source seq", String(info.pos_in_source_seq)]
  ];
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

function updateAnalysisSettingsVisibility() {
  const analysisPanel = document.getElementById("analysis-settings-sidebar");

  if (!analysisPanel) {
    return;
  }

  const hasDisplayedFeature = Boolean(getDisplayedFeature());
  analysisPanel.classList.toggle("hidden", hasDisplayedFeature);
  syncSidebarHeightToViewerColumn();
}

function applyActiveDisplay() {
  hideAllHighlights();
  updateFeatureNavigationButtons();

  const displayed = getDisplayedFeature();
  updateAnalysisSettingsVisibility();

  if (!displayed) {
    renderSidebarDefault();
    updateActiveAlignmentViewer();
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
  updateActiveAlignmentViewer();
  stage.batchDraw();
}

function renderSidebarDefault() {
  if (lastSidebarRenderState.mode === "default") {
    return;
  }

  lastSidebarRenderState.mode = "default";
  lastSidebarRenderState.featureId = null;
  lastSidebarRenderState.featureType = null;
  lastSidebarRenderState.source = null;
  lastSidebarRenderState.isPinned = false;

  const sidebar = document.getElementById("sidebar");
  sidebar.innerHTML = `
    <div class="sidebar-header">
      <h2>Region overview</h2>
    </div>
    <div class="sidebar-section">
      ${renderDistanceMatrix(REGION_DATA.mash_matrix)}
    </div>
    <div class="sidebar-section">
      ${renderGlobalSummaryStats()}
    </div>
    <div class="sidebar-section">
      ${renderSampleRegionStats()}
    </div>
  `;
}

function renderSidebarHeader(title, isPinned) {
  return `
    <div class="sidebar-header">
      <div>
        <h2>${escapeHtml(title)}</h2>
        ${isPinned ? '<div class="pin-badge">Pinned</div>' : ""}
      </div>
      ${state.pinnedFeatureId ? '<button id="sidebar-unpin" class="sidebar-close" type="button" aria-label="Unpin feature">✕</button>' : ""}
    </div>
  `;
}

function attachSidebarUnpinHandler() {
  const unpinButton = document.getElementById("sidebar-unpin");
  if (unpinButton) {
    unpinButton.addEventListener("click", () => {
      clearPinnedFeature();
    });
  }
}

function updateFeatureNavigationButtons() {
  const previousButton = document.getElementById("feature-prev");
  const nextButton = document.getElementById("feature-next");

  if (!previousButton || !nextButton) {
    return;
  }

  const hasPinnedFeature = Boolean(state.pinnedFeatureId && state.pinnedFeatureType);

  previousButton.classList.toggle("hidden", !hasPinnedFeature);
  nextButton.classList.toggle("hidden", !hasPinnedFeature);

  if (!hasPinnedFeature) {
    return;
  }

  previousButton.textContent = "Previous";
  nextButton.textContent = "Next";
}

function renderBlockSidebar(featureId, isPinned) {
  const sidebar = document.getElementById("sidebar");
  const entries = state.featureGroups.get(featureId) || [];

  if (entries.length === 0) {
    renderSidebarDefault();
    return;
  }

  const firstInfo = entries[0].info;
  const blockId = String(firstInfo.block_id);
  const matrix = REGION_DATA.kimura2p_matrices?.[blockId];

  let html = `
    ${renderSidebarHeader("Block", isPinned)}
    <p class="hint"><b>ID:</b> ${escapeHtml(blockId)}</p>
    <div class="sidebar-section">
      ${renderDistanceMatrix(matrix)}
    </div>
  `;

  for (const sampleName of getSampleOrder()) {
    const entry = entries.find(item => item.sample === sampleName);
    html += `<div class="sample-card"><h3>${escapeHtml(sampleName)}</h3>`;

    if (!entry) {
      html += `<p class="hint">No corresponding feature in this sample.</p>`;
    } else {
      const nStats = getMaskedNStats(blockId, sampleName);
      const formattedEntries = formatFeatureInfoEntries("block", entry.info);

      if (nStats) {
        formattedEntries.push(["Total N (%)", `${formatNumber(Number(nStats.masked_n_pct), 2)}%`]);
        formattedEntries.push(["Repeat/TE N (%)", `${formatNumber(Number(nStats.repeat_masked_n_pct), 2)}%`]);
      } else {
        formattedEntries.push(["Total N (%)", "NA"]);
        formattedEntries.push(["Repeat/TE N (%)", "NA"]);
      }

      html += '<div class="kv">';

      for (const [label, value] of formattedEntries) {
        html += `<div class="key">${escapeHtml(label)}</div><div>${escapeHtml(value)}</div>`;
      }

      html += "</div>";
    }

    html += "</div>";
  }

  sidebar.innerHTML = html;
  attachSidebarUnpinHandler();
}

function renderSnpSidebar(featureId, isPinned) {
  const sidebar = document.getElementById("sidebar");
  const entries = state.featureGroups.get(featureId) || [];

  if (entries.length === 0) {
    renderSidebarDefault();
    return;
  }

  const firstInfo = entries[0].info;
  const title = `${firstInfo.block_id}:${firstInfo.aln_pos}`;

  let html = `${renderSidebarHeader("SNP", isPinned)}<p class="hint"><b>ID:</b> ${escapeHtml(title)}</p>`;

  for (const sampleName of getSampleOrder()) {
    const entry = entries.find(item => item.sample === sampleName);
    html += `<div class="sample-card"><h3>${escapeHtml(sampleName)}</h3>`;

    if (!entry) {
      html += `<p class="hint">No corresponding feature in this sample.</p>`;
    } else {
      html += '<div class="kv">';

      const formattedEntries = formatFeatureInfoEntries("snp", entry.info);
      for (const [label, value] of formattedEntries) {
        html += `<div class="key">${escapeHtml(label)}</div><div>${escapeHtml(value)}</div>`;
      }

      html += "</div>";
    }

    html += "</div>";
  }

  sidebar.innerHTML = html;
  attachSidebarUnpinHandler();
}

function renderFeatureSidebar(featureType, featureId, isPinned) {
  const source = isPinned ? "pin" : "hover";

  if (
    lastSidebarRenderState.mode === "feature" &&
    lastSidebarRenderState.featureId === featureId &&
    lastSidebarRenderState.featureType === featureType &&
    lastSidebarRenderState.source === source &&
    lastSidebarRenderState.isPinned === isPinned
  ) {
    return;
  }

  lastSidebarRenderState.mode = "feature";
  lastSidebarRenderState.featureId = featureId;
  lastSidebarRenderState.featureType = featureType;
  lastSidebarRenderState.source = source;
  lastSidebarRenderState.isPinned = isPinned;

  if (featureType === "block") {
    renderBlockSidebar(featureId, isPinned);
    return;
  }

  renderSnpSidebar(featureId, isPinned);
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
  invalidateSidebarCache();
  applyActiveDisplay();
}

function reapplyDisplayIfVisible() {
  applyActiveDisplay();
}

function attachInteraction(node, featureType, featureId) {
  node.setAttr("featureType", featureType);
  node.setAttr("featureId", featureId);
}

let _lastResolvedHoverKey = null;
let _hoverIndex = [];

function lowerBoundScreenX(arr, target) {
  let lo = 0;
  let hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (arr[mid].screenX < target) {
      lo = mid + 1;
    } else {
      hi = mid;
    }
  }
  return lo;
}

function lowerBoundX0(arr, target) {
  let lo = 0;
  let hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (arr[mid].x0 < target) {
      lo = mid + 1;
    } else {
      hi = mid;
    }
  }
  return lo;
}

function rebuildHoverSpatialIndex() {
  const visibleStart = getVisibleStartBp();
  const visibleEnd = getVisibleEndBp();

  _hoverIndex = REGION_DATA.samples.map((sample, i) => {
    const panelTop = computePanelTop(i);
    const trackTop = panelTop + CONFIG.trackY;
    const trackBottom = trackTop + CONFIG.trackHeight;

    const snps = [];
    for (const snp of sample.snps) {
      if (isPositionVisible(snp.pos_in_zone, visibleStart, visibleEnd)) {
        snps.push({ screenX: worldXToScreenX(snp.pos_in_zone), featureId: snp.feature_id });
      }
    }
    snps.sort((a, b) => a.screenX - b.screenX);

    const blocks = [];
    for (const block of sample.blocks) {
      if (intersectsRange(block.block_start_in_zone, block.block_end_in_zone, visibleStart, visibleEnd)) {
        const x0 = worldXToScreenX(Math.max(block.block_start_in_zone, visibleStart));
        const x1 = worldXToScreenX(Math.min(block.block_end_in_zone, visibleEnd));
        const x1eff = Math.max(x0 + CONFIG.blockMinWidthPx, x1);
        blocks.push({ x0, x1eff, featureId: block.feature_id });
      }
    }
    blocks.sort((a, b) => a.x0 - b.x0);

    return { trackTop, trackBottom, snps, blocks };
  });
}

function resolveHoveredFeature(pointerX, pointerY) {
  for (let i = 0; i < _hoverIndex.length; i += 1) {
    const entry = _hoverIndex[i];

    if (pointerY < entry.trackTop || pointerY > entry.trackBottom) {
      continue;
    }

    const snpLo = lowerBoundScreenX(entry.snps, pointerX - SNP_POINTER_TOLERANCE_PX);
    let closestSnpFeatureId = null;
    let closestSnpDist = SNP_POINTER_TOLERANCE_PX + 1;

    for (let j = snpLo; j < entry.snps.length; j += 1) {
      const snp = entry.snps[j];
      if (snp.screenX > pointerX + SNP_POINTER_TOLERANCE_PX) {
        break;
      }
      const dist = Math.abs(pointerX - snp.screenX);
      if (dist < closestSnpDist) {
        closestSnpDist = dist;
        closestSnpFeatureId = snp.featureId;
      }
    }

    if (closestSnpFeatureId !== null) {
      return { featureType: "snp", featureId: closestSnpFeatureId };
    }

    const blockIndex = lowerBoundX0(entry.blocks, pointerX) - 1;

    if (blockIndex >= 0) {
      const block = entry.blocks[blockIndex];
      if (pointerX <= block.x1eff) {
        return { featureType: "block", featureId: block.featureId };
      }
    }

    return null;
  }

  return null;
}

function applyResolvedHover(resolved) {
  const key = resolved ? `${resolved.featureType}:${resolved.featureId}` : null;

  if (key === _lastResolvedHoverKey) {
    return;
  }

  _lastResolvedHoverKey = key;

  if (!resolved) {
    state.isHoveringInteractiveFeature = false;
    clearHoveredFeature();
    return;
  }

  state.isHoveringInteractiveFeature = true;
  setHoveredFeature(resolved.featureType, resolved.featureId);
}

function getViewerElement() {
  return document.getElementById("viewer");
}

function setBodyCursor(cursor) {
  document.body.style.cursor = cursor;
}

function setViewerCursor(cursor) {
  const viewerElement = getViewerElement();
  if (viewerElement) {
    viewerElement.style.cursor = cursor;
  }
}

function setAlignmentCursor(cursor) {
  const el = document.getElementById("alignment-viewer");
  if (el) {
    el.style.cursor = cursor;
  }
}

function resetViewerCursors() {
  setViewerCursor("");
  setAlignmentCursor("");
}

function getStageWidth() {
  const viewerElement = getViewerElement();
  return Math.max(1, viewerElement.clientWidth);
}

function getViewportTrackWidth() {
  return getStageWidth() - getLeftMargin() - CONFIG.rightMargin;
}

function getDrawableTrackWidth() {
  return Math.max(1, getViewportTrackWidth() - CONFIG.endPaddingPx);
}

function getVisibleBiologicalEndX() {
  return worldXToScreenX(getVisibleEndBp());
}

function getVisibleBiologicalWidth() {
  return Math.max(1, getVisibleBiologicalEndX() - getLeftMargin());
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
  requestStageRedraw();
}

function computePanelTop(panelIndex) {
  let panelTop = getViewerToolbarHeight()
    + CONFIG.topMargin
    + REGION_VIEWER.axisToFirstSampleGap;

  for (let index = 0; index < panelIndex; index += 1) {
    panelTop += getSamplePanelHeight(REGION_DATA.samples[index]) + CONFIG.panelGap;
  }

  return panelTop;
}

function isPointerOverSampleTrack(pointerY) {
  for (let index = 0; index < REGION_DATA.samples.length; index += 1) {
    const panelTop = computePanelTop(index);
    const trackTop = panelTop + CONFIG.trackY;
    const trackBottom = trackTop + CONFIG.trackHeight;
    if (pointerY >= trackTop && pointerY <= trackBottom) {
      return true;
    }
  }
  return false;
}

function getScrollbarY() {
  return getMainViewerContentHeight() - SCROLLBAR.bottomPadding - SCROLLBAR.height;
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
  return getLeftMargin() + (position - visibleStart) * getWorldToScreenScale();
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
  const x0 = getLeftMargin();
  const x1 = getVisibleBiologicalEndX();
  const axisY = getViewerToolbarHeight() + 24;

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
    x: SAMPLE_LABEL.x,
    y: panelTop + CONFIG.trackY + 4,
    width: getLeftMargin() - SAMPLE_LABEL.x - SAMPLE_LABEL.rightPadding,
    text: sampleName,
    fontSize: SAMPLE_LABEL.fontSize,
    fontStyle: SAMPLE_LABEL.fontStyle,
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

function drawSampleTrackBackground(layer, sample, panelTop) {
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
  const y = panelTop + CONFIG.trackY;

  layer.add(new Konva.Rect({
    x: x0,
    y,
    width: Math.max(1, x1 - x0),
    height: CONFIG.trackHeight,
    fill: "#ffffff",
    strokeWidth: 0,
    listening: false
  }));
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

  const clippedStart = Math.max(feature.block_start_in_zone, visibleStart);
  const clippedEnd = Math.min(feature.block_end_in_zone, visibleEnd);

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

  const clippedStart = Math.max(feature.block_start_in_zone, visibleStart);
  const clippedEnd = Math.min(feature.block_end_in_zone, visibleEnd);

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

  const clippedStart = Math.max(feature.block_start_in_zone, visibleStart);
  const clippedEnd = Math.min(feature.block_end_in_zone, visibleEnd);

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

function getGffTrackY(panelTop, trackIndex) {
  return panelTop
    + CONFIG.trackY
    + CONFIG.trackHeight
    + GFF_TRACK.topGap
    + trackIndex * (GFF_TRACK.height + GFF_TRACK.gap);
}

function drawGffTrackBaseline(layer, sample, panelTop, trackIndex) {
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

  const y = getGffTrackY(panelTop, trackIndex) + GFF_TRACK.height / 2;
  const x0 = worldXToScreenX(clippedStart);
  const x1 = worldXToScreenX(clippedEnd);

  layer.add(new Konva.Line({
    points: [x0, y, x1, y],
    stroke: "#e5e7eb",
    strokeWidth: 1,
    listening: false
  }));
}

function drawGffGeneFeature(layer, gene, panelTop, trackIndex, color) {
  const visibleStart = getVisibleStartBp();
  const visibleEnd = getVisibleEndBp();

  if (!intersectsRange(gene.start_in_zone, gene.end_in_zone, visibleStart, visibleEnd)) {
    return;
  }

  const clippedStart = Math.max(gene.start_in_zone, visibleStart);
  const clippedEnd = Math.min(gene.end_in_zone, visibleEnd);

  if (clippedEnd < clippedStart) {
    return;
  }

  const x0 = worldXToScreenX(clippedStart);
  const x1 = worldXToScreenX(clippedEnd);
  const y = getGffTrackY(panelTop, trackIndex);

  layer.add(new Konva.Rect({
    x: x0,
    y,
    width: Math.max(GFF_TRACK.minGeneWidthPx, x1 - x0),
    height: GFF_TRACK.height,
    fill: color,
    opacity: 0.85,
    cornerRadius: 2,
    listening: false
  }));
}

function drawGffTracks(layer, sample, panelTop) {
  const tracks = getSampleGffTracks(sample);

  tracks.forEach((track, trackIndex) => {
    const color = getGffTrackColor(track.track_name);

    drawGffTrackBaseline(layer, sample, panelTop, trackIndex);

    for (const gene of track.features || []) {
      drawGffGeneFeature(layer, gene, panelTop, trackIndex, color);
    }
  });
}

function drawSamplePanelBackground(layer, sample, panelTop) {
  const backgroundX = 4;
  const backgroundRight = getVisibleBiologicalEndX() + 8;

  layer.add(new Konva.Rect({
    x: backgroundX,
    y: panelTop - 6,
    width: Math.max(1, backgroundRight - backgroundX),
    height: getSamplePanelHeight(sample) + 4,
    fill: "#f7f8fa",
    stroke: "#e9ecef",
    strokeWidth: 1,
    cornerRadius: 8,
    listening: false
  }));
}

function drawSample(
  backgroundLayer,
  blockLayer,
  blockHighlightLayer,
  snpLayer,
  snpHighlightLayer,
  zoneOutlineLayer,
  interactionLayer,
  snpHitboxQueue,
  sample,
  panelIndex
) {
  const panelTop = computePanelTop(panelIndex);
  const visibleStart = getVisibleStartBp();
  const visibleEnd = getVisibleEndBp();
  drawSamplePanelBackground(backgroundLayer, sample, panelTop);

  drawSampleLabel(blockLayer, panelTop, sample.sample);
  drawSampleTrackBackground(blockLayer, sample, panelTop);
  drawSampleOutline(zoneOutlineLayer, sample, panelTop);
  drawGffTracks(blockLayer, sample, panelTop);

  for (const block of sample.blocks) {
    if (!intersectsRange(
      block.block_start_in_zone,
      block.block_end_in_zone,
      visibleStart,
      visibleEnd
    )) {
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
    snpHitboxQueue.push(hitbox);

    addHighlightNode(snp.feature_id, highlight, "snp");
    attachInteraction(hitbox, "snp", snp.feature_id);
  }
}

function getScrollbarMetrics() {
  const trackX = getLeftMargin() + SCROLLBAR.trackInset;
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
      setViewerCursor("grab");
    }
  });

  thumb.on("mouseleave", () => {
    if (!state.isDraggingViewport && !state.isDraggingScrollbar) {
      setViewerCursor("");
    }
  });

  thumb.on("pointerdown", (event) => {
    if (!metrics.visible) {
      return;
    }

    event.cancelBubble = true;
    state.isDraggingScrollbar = true;
    state.suppressHover = true;
    setBodyCursor("grabbing");

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

const stage = new Konva.Stage({
  container: "viewer",
  width: 1,
  height: getMainViewerContentHeight()
});

const backgroundLayer = new Konva.FastLayer();
const blockLayer = new Konva.FastLayer();
const snpLayer = new Konva.FastLayer();
const blockHighlightLayer = new Konva.FastLayer();
const snpHighlightLayer = new Konva.FastLayer();
const zoneOutlineLayer = new Konva.FastLayer();
const interactionLayer = new Konva.Layer();

stage.add(backgroundLayer);
stage.add(blockLayer);
stage.add(snpLayer);
stage.add(blockHighlightLayer);
stage.add(snpHighlightLayer);
stage.add(zoneOutlineLayer);
stage.add(interactionLayer);

function getFeatureTarget(node) {
  if (!node || node === stage || node === interactionLayer) {
    return null;
  }
  const featureType = node.getAttr("featureType");
  const featureId = node.getAttr("featureId");
  if (!featureType || !featureId) {
    return null;
  }
  return { featureType, featureId };
}

interactionLayer.on("click", (event) => {
  const pointer = stage.getPointerPosition();
  if (!pointer) {
    return;
  }
  const resolved = resolveHoveredFeature(pointer.x, pointer.y);
  if (!resolved) {
    return;
  }
  event.cancelBubble = true;
  setPinnedFeature(resolved.featureType, resolved.featureId);
});

const alignmentStage = new Konva.Stage({
  container: "alignment-viewer",
  width: 1,
  height: 160
});

const alignmentBackgroundLayer = new Konva.FastLayer();
const alignmentSequenceLayer = new Konva.FastLayer();
const alignmentInteractionLayer = new Konva.Layer();

alignmentStage.add(alignmentBackgroundLayer);
alignmentStage.add(alignmentSequenceLayer);
alignmentStage.add(alignmentInteractionLayer);

let _stageRedrawPending = false;
let _alignmentRedrawPending = false;

function requestStageRedraw() {
  if (_stageRedrawPending) {
    return;
  }
  _stageRedrawPending = true;
  requestAnimationFrame(() => {
    _stageRedrawPending = false;
    redrawStage();
  });
}

function requestAlignmentRedraw() {
  if (_alignmentRedrawPending) {
    return;
  }
  _alignmentRedrawPending = true;
  requestAnimationFrame(() => {
    _alignmentRedrawPending = false;
    redrawAlignmentViewer();
  });
}

function showRenderingOverlay() {
  let overlay = document.getElementById("rendering-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "rendering-overlay";
    overlay.textContent = "Rendering viewer\u2026";
    overlay.style.cssText = [
      "position:fixed",
      "inset:0",
      "display:flex",
      "align-items:center",
      "justify-content:center",
      "background:rgba(255,255,255,0.85)",
      "font-size:16px",
      "color:#374151",
      "z-index:9999",
      "pointer-events:none"
    ].join(";");
    document.body.appendChild(overlay);
  }
  overlay.style.display = "flex";
}

function hideRenderingOverlay() {
  const overlay = document.getElementById("rendering-overlay");
  if (overlay) {
    overlay.style.display = "none";
  }
}

function redrawStage() {
  stage.width(getStageWidth());
  stage.height(getMainViewerContentHeight());

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
    height: getMainViewerContentHeight(),
    fill: "white",
    listening: false
  }));

  drawGlobalAxis(blockLayer);

  const snpHitboxQueue = [];

  REGION_DATA.samples.forEach((sample, index) => {
    drawSample(
      backgroundLayer,
      blockLayer,
      blockHighlightLayer,
      snpLayer,
      snpHighlightLayer,
      zoneOutlineLayer,
      interactionLayer,
      snpHitboxQueue,
      sample,
      index
    );
  });

  for (const hitbox of snpHitboxQueue) {
    interactionLayer.add(hitbox);
  }

  drawGffTrackLegend(blockLayer);
  drawScrollbar(interactionLayer);
  reapplyDisplayIfVisible();
  stage.draw();
  rebuildHoverSpatialIndex();
}

function getAlignmentContainer() {
  return document.getElementById("alignment-viewer");
}

function getAlignmentSubtitle() {
  return document.getElementById("alignment-subtitle");
}

function getAlignmentPanel() {
  return document.getElementById("alignment-panel");
}

function getBlockIdFromFeature(featureType, featureId) {
  if (featureType !== "block") {
    return null;
  }

  const entries = state.featureGroups.get(featureId) || [];
  if (entries.length === 0) {
    return null;
  }

  return String(entries[0].info.block_id);
}

function getFirstFeatureInfo(featureId) {
  const entries = state.featureGroups.get(featureId) || [];

  if (entries.length === 0) {
    return null;
  }

  return entries[0].info;
}

function getActiveAlignmentTarget() {
  if (state.hoveredFeatureId && state.hoveredFeatureType === "block") {
    return {
      blockId: getBlockIdFromFeature("block", state.hoveredFeatureId),
      focusColumn: null
    };
  }

  if (state.pinnedFeatureId && state.pinnedFeatureType === "snp") {
    const info = getFirstFeatureInfo(state.pinnedFeatureId);

    if (!info) {
      return null;
    }

    return {
      blockId: String(info.block_id),
      focusColumn: Number(info.aln_pos) - 1
    };
  }

  if (state.pinnedFeatureId && state.pinnedFeatureType === "block") {
    return {
      blockId: getBlockIdFromFeature("block", state.pinnedFeatureId),
      focusColumn: null
    };
  }

  return null;
}

function getAlignmentData(blockId) {
  if (!blockId) {
    return null;
  }

  return REGION_DATA.block_alignments?.[String(blockId)] || null;
}

function getAlignmentSampleNames(alignmentData) {
  if (!alignmentData) {
    return [];
  }

  const sampleOrder = getSampleOrder();
  const availableSamples = new Set(Object.keys(alignmentData));
  return sampleOrder.filter(sampleName => availableSamples.has(sampleName));
}

function getAlignmentLength(alignmentData) {
  if (!alignmentData) {
    return 0;
  }

  const sequences = Object.values(alignmentData);
  if (sequences.length === 0) {
    return 0;
  }

  return sequences[0].length;
}

function getAlignmentStageWidth() {
  const container = getAlignmentContainer();
  return Math.max(1, container.clientWidth);
}

function getAlignmentStageHeight(sampleCount) {
  return ALIGNMENT.topMargin
    + ALIGNMENT.axisHeight
    + sampleCount * ALIGNMENT.rowHeight
    + ALIGNMENT.bottomPadding
    + ALIGNMENT.scrollbarHeight
    + ALIGNMENT.scrollbarBottomPadding;
}

function getAlignmentViewportWidth() {
  return Math.max(1, getAlignmentStageWidth() - ALIGNMENT.leftMargin - 12);
}

function getAlignmentCharWidth() {
  return Math.max(
    ALIGNMENT.minCharWidth,
    Math.min(ALIGNMENT.maxCharWidth, ALIGNMENT.charWidth * state.alignmentZoomX)
  );
}

function getAlignmentContentWidth(alignmentLength) {
  return alignmentLength * getAlignmentCharWidth();
}

function getAlignmentMaxScrollX(alignmentLength) {
  return Math.max(
    0,
    getAlignmentContentWidth(alignmentLength) - getAlignmentViewportWidth()
  );
}

function clampAlignmentScrollX(value, alignmentLength) {
  return Math.max(0, Math.min(getAlignmentMaxScrollX(alignmentLength), value));
}

function normalizeAlignmentScrollX(alignmentLength) {
  state.alignmentScrollX = clampAlignmentScrollX(
    state.alignmentScrollX,
    alignmentLength
  );
}

function centerAlignmentOnColumn(columnIndex, alignmentLength) {
  if (
    columnIndex === null
    || columnIndex === undefined
    || Number.isNaN(Number(columnIndex))
    || alignmentLength === 0
  ) {
    return;
  }

  const charWidth = getAlignmentCharWidth();
  const targetCenterX = columnIndex * charWidth + charWidth / 2;

  state.alignmentScrollX = clampAlignmentScrollX(
    targetCenterX - getAlignmentViewportWidth() / 2,
    alignmentLength
  );
}

function getVisibleAlignmentColumnRange(alignmentLength) {
  const charWidth = getAlignmentCharWidth();
  const firstColumn = Math.max(0, Math.floor(state.alignmentScrollX / charWidth));
  const visibleColumnCount = Math.ceil(getAlignmentViewportWidth() / charWidth) + 2;
  const lastColumn = Math.min(alignmentLength, firstColumn + visibleColumnCount);

  return {
    firstColumn,
    lastColumn
  };
}

function alignmentColumnToX(columnIndex) {
  return ALIGNMENT.leftMargin
    + columnIndex * getAlignmentCharWidth()
    - state.alignmentScrollX;
}

function alignmentColumnCenterToX(columnIndex) {
  return alignmentColumnToX(columnIndex) + getAlignmentCharWidth() / 2;
}

function getBaseFill(base) {
  const normalizedBase = String(base).toUpperCase();

  if (normalizedBase === "A") {
    return "#7fc97f";
  }

  if (normalizedBase === "C") {
    return "#80b1d3";
  }

  if (normalizedBase === "G") {
    return "#fdb462";
  }

  if (normalizedBase === "T") {
    return "#fb8072";
  }

  if (normalizedBase === "-") {
    return "#e5e7eb";
  }

  if (normalizedBase === "N") {
    return "#d1d5db";
  }

  return "#f3f4f6";
}

function getBaseTextFill(base) {
  if (String(base) === "-") {
    return "#6b7280";
  }

  return "#111827";
}

function formatAlignmentAxisValue(value) {
  if (value <= CONFIG.bpToKbThresholdBp) {
    return `${formatNumber(value, 0)} bp`;
  }

  if (value <= CONFIG.kbToMbThresholdBp) {
    return `${formatNumber(value / 1000, 1)} kb`;
  }

  return `${formatNumber(value / 1000000, 3)} Mb`;
}

function drawAlignmentAxis(layer, alignmentLength, snpColumns) {
  const y = ALIGNMENT.topMargin;
  const x0 = ALIGNMENT.leftMargin;
  const x1 = ALIGNMENT.leftMargin + getAlignmentViewportWidth();

  layer.add(new Konva.Line({
    points: [x0, y, x1, y],
    stroke: "#444444",
    strokeWidth: 1,
    listening: false
  }));

  const charWidth = getAlignmentCharWidth();
  const bpPerPixel = 1 / Math.max(1, charWidth);
  const rawStep = bpPerPixel * 90;
  const step = niceStep(rawStep);
  const range = getVisibleAlignmentColumnRange(alignmentLength);
  const firstTick = Math.ceil((range.firstColumn + 1) / step) * step;

  for (let value = firstTick; value <= range.lastColumn; value += step) {
    const x = alignmentColumnCenterToX(value - 1);

    layer.add(new Konva.Line({
      points: [x, y, x, y + 6],
      stroke: "#444444",
      strokeWidth: 1,
      listening: false
    }));

    layer.add(new Konva.Text({
      x: x - 34,
      y: y - 18,
      width: 68,
      text: formatAlignmentAxisValue(value),
      fontSize: 10,
      fill: "#555555",
      align: "center",
      listening: false
    }));
  }
  const visibleSnpColumns = [...snpColumns].filter(
    columnIndex => columnIndex >= range.firstColumn && columnIndex < range.lastColumn
  );

  for (const columnIndex of visibleSnpColumns) {
    const x = alignmentColumnCenterToX(columnIndex);

    layer.add(new Konva.Text({
      x: x - 6,
      y: y + 12,
      width: 12,
      text: "*",
      fontSize: 13,
      fontStyle: "bold",
      fill: "#111827",
      align: "center",
      listening: false
    }));
  }
}

function getBlockSnpAlignmentColumns(blockId) {
  const snpColumns = new Set();

  if (!blockId) {
    return snpColumns;
  }

  for (const sample of REGION_DATA.samples) {
    for (const snp of sample.snps) {
      if (String(snp.block_id) !== String(blockId)) {
        continue;
      }

      const alnPos = Number(snp.aln_pos);
      if (!Number.isNaN(alnPos) && alnPos >= 1) {
        snpColumns.add(alnPos - 1);
      }
    }
  }

  return snpColumns;
}

function getBlockSnpColumns(blockId) {
  const columns = [];

  if (!blockId) {
    return columns;
  }

  for (const sample of REGION_DATA.samples) {
    for (const snp of sample.snps) {
      if (String(snp.block_id) !== String(blockId)) {
        continue;
      }

      const alnPos = Number(snp.aln_pos);
      if (!Number.isNaN(alnPos) && alnPos >= 1) {
        columns.push(alnPos - 1);
      }
    }
  }

  return [...new Set(columns)].sort((left, right) => left - right);
}

function getBlockSnpNavigationItems(blockId) {
  const itemsByFeatureId = new Map();

  if (!blockId) {
    return [];
  }

  for (const sample of REGION_DATA.samples) {
    for (const snp of sample.snps) {
      if (String(snp.block_id) !== String(blockId)) {
        continue;
      }

      const alnPos = Number(snp.aln_pos);
      if (Number.isNaN(alnPos) || alnPos < 1) {
        continue;
      }

      if (!itemsByFeatureId.has(snp.feature_id)) {
        itemsByFeatureId.set(snp.feature_id, {
          featureId: snp.feature_id,
          columnIndex: alnPos - 1
        });
      }
    }
  }

  return [...itemsByFeatureId.values()]
    .sort((left, right) => left.columnIndex - right.columnIndex);
}

function getCurrentAlignmentCenterColumn() {
  return (state.alignmentScrollX + getAlignmentViewportWidth() / 2)
    / getAlignmentCharWidth();
}

function getNearestSnpColumnIndex(snpColumns) {
  if (snpColumns.length === 0) {
    return -1;
  }

  const currentColumn = state.alignmentFocusedSnpColumn !== null
    ? state.alignmentFocusedSnpColumn
    : getCurrentAlignmentCenterColumn();

  let bestIndex = 0;
  let bestDistance = Math.abs(snpColumns[0] - currentColumn);

  for (let index = 1; index < snpColumns.length; index += 1) {
    const distance = Math.abs(snpColumns[index] - currentColumn);

    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = index;
    }
  }

  return bestIndex;
}

function focusNeighborAlignmentSnp(direction) {
  const blockId = state.activeAlignmentBlockId;
  const alignmentData = getAlignmentData(blockId);
  const alignmentLength = getAlignmentLength(alignmentData);
  const snpItems = getBlockSnpNavigationItems(blockId);

  if (alignmentLength === 0 || snpItems.length === 0) {
    return;
  }

  const snpColumns = snpItems.map(item => item.columnIndex);
  const currentIndex = getNearestSnpColumnIndex(snpColumns);

  if (currentIndex === -1) {
    return;
  }

  const nextIndex = (currentIndex + direction + snpItems.length) % snpItems.length;
  const nextItem = snpItems[nextIndex];

  state.alignmentFocusedSnpColumn = nextItem.columnIndex;
  setPinnedFeature("snp", nextItem.featureId);
}

function drawAlignmentRows(layer, alignmentData, sampleNames, alignmentLength, snpColumns) {
  const range = getVisibleAlignmentColumnRange(alignmentLength);
  const charWidth = getAlignmentCharWidth();
  const baseY = ALIGNMENT.topMargin + ALIGNMENT.axisHeight;

  sampleNames.forEach((sampleName, rowIndex) => {
    const rowY = baseY + rowIndex * ALIGNMENT.rowHeight;
    const sequence = alignmentData[sampleName] || "";

    layer.add(new Konva.Text({
      x: 10,
      y: rowY + 4,
      width: ALIGNMENT.leftMargin - 18,
      text: sampleName,
      fontSize: ALIGNMENT.labelFontSize,
      fontStyle: "bold",
      fill: "#222222",
      listening: false
    }));

    for (let columnIndex = range.firstColumn; columnIndex < range.lastColumn; columnIndex += 1) {
      const base = sequence[columnIndex] || "";
      const x = alignmentColumnToX(columnIndex);
      const isSnpColumn = snpColumns.has(columnIndex);

      layer.add(new Konva.Rect({
        x,
        y: rowY,
        width: Math.max(1, charWidth),
        height: ALIGNMENT.rowHeight - 1,
        fill: getBaseFill(base),
        stroke: "#ffffff",
        strokeWidth: 0.5,
        listening: false
      }));

      if (charWidth >= 9) {
        layer.add(new Konva.Text({
          x,
          y: rowY,
          width: charWidth,
          height: ALIGNMENT.rowHeight - 1,
          text: base,
          fontSize: isSnpColumn
            ? ALIGNMENT.letterFontSize + 2
            : ALIGNMENT.letterFontSize,
          fontStyle: isSnpColumn ? "bold" : "normal",
          fill: getBaseTextFill(base),
          align: "center",
          verticalAlign: "middle",
          listening: false
        }));
      }
    }
  });
}

function getAlignmentScrollbarY(sampleCount) {
  return getAlignmentStageHeight(sampleCount)
    - ALIGNMENT.scrollbarBottomPadding
    - ALIGNMENT.scrollbarHeight;
}

function getAlignmentScrollbarMetrics(alignmentLength, sampleCount) {
  const trackX = ALIGNMENT.leftMargin;
  const trackY = getAlignmentScrollbarY(sampleCount);
  const trackWidth = getAlignmentViewportWidth();
  const contentWidth = getAlignmentContentWidth(alignmentLength);
  const viewportWidth = getAlignmentViewportWidth();

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
  const thumbWidth = Math.max(ALIGNMENT.scrollbarMinThumbWidth, trackWidth * ratio);
  const maxThumbTravel = Math.max(0, trackWidth - thumbWidth);
  const maxScroll = getAlignmentMaxScrollX(alignmentLength);
  const scrollRatio = maxScroll > 0 ? state.alignmentScrollX / maxScroll : 0;
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

function setAlignmentScrollFromThumbX(thumbX, alignmentLength, sampleCount) {
  const metrics = getAlignmentScrollbarMetrics(alignmentLength, sampleCount);
  const maxThumbTravel = Math.max(0, metrics.trackWidth - metrics.thumbWidth);

  if (maxThumbTravel <= 0) {
    state.alignmentScrollX = 0;
    return;
  }

  const clampedThumbX = Math.max(
    metrics.trackX,
    Math.min(metrics.trackX + maxThumbTravel, thumbX)
  );
  const thumbRatio = (clampedThumbX - metrics.trackX) / maxThumbTravel;
  state.alignmentScrollX = thumbRatio * getAlignmentMaxScrollX(alignmentLength);
  normalizeAlignmentScrollX(alignmentLength);
}

function drawAlignmentScrollbar(layer, alignmentLength, sampleCount) {
  const metrics = getAlignmentScrollbarMetrics(alignmentLength, sampleCount);

  layer.add(new Konva.Rect({
    x: metrics.trackX,
    y: metrics.trackY,
    width: metrics.trackWidth,
    height: ALIGNMENT.scrollbarHeight,
    fill: "#f0f0f0",
    stroke: "#d0d0d0",
    cornerRadius: 8,
    listening: false
  }));

  const thumb = new Konva.Rect({
    x: metrics.thumbX,
    y: metrics.trackY + 1,
    width: metrics.thumbWidth,
    height: ALIGNMENT.scrollbarHeight - 2,
    fill: metrics.visible ? "#c2c2c2" : "#e0e0e0",
    stroke: "#b4b4b4",
    cornerRadius: 7
  });

  thumb.on("pointerdown", (event) => {
    if (!metrics.visible) {
      return;
    }

    event.cancelBubble = true;
    state.isDraggingAlignmentScrollbar = true;
    setBodyCursor("grabbing");

    const pointer = alignmentStage.getPointerPosition();
    state.alignmentScrollbarDragOffsetX = pointer.x - metrics.thumbX;
  });

  layer.add(thumb);

  const clickArea = new Konva.Rect({
    x: metrics.trackX,
    y: metrics.trackY,
    width: metrics.trackWidth,
    height: ALIGNMENT.scrollbarHeight,
    fill: "rgba(0,0,0,0)"
  });

  clickArea.on("pointerdown", (event) => {
    if (!metrics.visible) {
      return;
    }

    event.cancelBubble = true;
    const pointer = alignmentStage.getPointerPosition();
    const centeredThumbX = pointer.x - metrics.thumbWidth / 2;
    setAlignmentScrollFromThumbX(centeredThumbX, alignmentLength, sampleCount);
    redrawAlignmentViewer();
  });

  layer.add(clickArea);
}

function renderAlignmentEmpty(message) {
  const subtitle = getAlignmentSubtitle();
  if (subtitle) {
    subtitle.textContent = message;
  }

  alignmentStage.width(getAlignmentStageWidth());
  alignmentStage.height(160);

  alignmentBackgroundLayer.destroyChildren();
  alignmentSequenceLayer.destroyChildren();
  alignmentInteractionLayer.destroyChildren();

  alignmentBackgroundLayer.add(new Konva.Rect({
    x: 0,
    y: 0,
    width: getAlignmentStageWidth(),
    height: 160,
    fill: "white",
    listening: false
  }));

  alignmentSequenceLayer.add(new Konva.Text({
    x: 14,
    y: 18,
    width: Math.max(1, getAlignmentStageWidth() - 28),
    text: message,
    fontSize: 13,
    fill: "#6b7280",
    listening: false
  }));

  alignmentStage.draw();
  syncSidebarHeightToViewerColumn();
}

function redrawAlignmentViewer() {
  const panel = getAlignmentPanel();
  const blockId = state.activeAlignmentBlockId;
  const alignmentData = getAlignmentData(blockId);
  const containerWidth = getAlignmentStageWidth();

  const stateUnchanged =
    blockId === lastAlignmentRenderState.blockId &&
    state.alignmentFocusedSnpColumn === lastAlignmentRenderState.focusedSnpColumn &&
    state.alignmentZoomX === lastAlignmentRenderState.alignmentZoomX &&
    state.alignmentScrollX === lastAlignmentRenderState.alignmentScrollX &&
    containerWidth === lastAlignmentRenderState.containerWidth;

  if (stateUnchanged) {
    return;
  }

  lastAlignmentRenderState.blockId = blockId;
  lastAlignmentRenderState.focusedSnpColumn = state.alignmentFocusedSnpColumn;
  lastAlignmentRenderState.alignmentZoomX = state.alignmentZoomX;
  lastAlignmentRenderState.alignmentScrollX = state.alignmentScrollX;
  lastAlignmentRenderState.containerWidth = containerWidth;

  if (!blockId) {
    if (panel) {
      panel.classList.add("hidden");
    }
    syncSidebarHeightToViewerColumn();
    return;
  }

  if (panel) {
    panel.classList.remove("hidden");
  }

  if (!alignmentData) {
    renderAlignmentEmpty(`No alignment available for block ${blockId}.`);
    return;
  }

  const sampleNames = getAlignmentSampleNames(alignmentData);
  const alignmentLength = getAlignmentLength(alignmentData);

  if (sampleNames.length === 0 || alignmentLength === 0) {
    renderAlignmentEmpty(`Empty alignment for block ${blockId}.`);
    return;
  }

  normalizeAlignmentScrollX(alignmentLength);
  lastAlignmentRenderState.alignmentScrollX = state.alignmentScrollX;

  const subtitle = getAlignmentSubtitle();
  if (subtitle) {
    subtitle.textContent = `Block ${blockId} (${alignmentLength} bp)`;
  }

  const stageHeight = getAlignmentStageHeight(sampleNames.length);

  alignmentStage.width(getAlignmentStageWidth());
  alignmentStage.height(stageHeight);

  alignmentBackgroundLayer.destroyChildren();
  alignmentSequenceLayer.destroyChildren();
  alignmentInteractionLayer.destroyChildren();

  alignmentBackgroundLayer.add(new Konva.Rect({
    x: 0,
    y: 0,
    width: getAlignmentStageWidth(),
    height: stageHeight,
    fill: "white",
    listening: false
  }));

  const snpColumns = getBlockSnpAlignmentColumns(blockId);
  drawAlignmentAxis(alignmentSequenceLayer, alignmentLength, snpColumns);
  drawAlignmentRows(
    alignmentSequenceLayer,
    alignmentData,
    sampleNames,
    alignmentLength,
    snpColumns
  );
  drawAlignmentScrollbar(alignmentInteractionLayer, alignmentLength, sampleNames.length);

  alignmentStage.draw();
  syncSidebarHeightToViewerColumn();
}

function updateActiveAlignmentViewer() {
  const target = getActiveAlignmentTarget();

  if (!target || !target.blockId) {
    state.activeAlignmentBlockId = null;
    state.alignmentFocusedSnpColumn = null;
    redrawAlignmentViewer();
    return;
  }

  const nextBlockId = target.blockId;
  const nextFocusColumn = target.focusColumn;

  if (state.activeAlignmentBlockId !== nextBlockId) {
    state.activeAlignmentBlockId = nextBlockId;
    state.alignmentScrollX = 0;
    state.alignmentZoomX = 1;
  }

  state.alignmentFocusedSnpColumn = nextFocusColumn;

  const alignmentData = getAlignmentData(nextBlockId);
  const alignmentLength = getAlignmentLength(alignmentData);

  if (nextFocusColumn !== null) {
    centerAlignmentOnColumn(nextFocusColumn, alignmentLength);
  }

  redrawAlignmentViewer();
}

function moveAlignmentByViewportFraction(direction) {
  const alignmentData = getAlignmentData(state.activeAlignmentBlockId);
  const alignmentLength = getAlignmentLength(alignmentData);

  if (alignmentLength === 0) {
    return;
  }

  const stepPx = getAlignmentViewportWidth() * ALIGNMENT.panFraction;
  state.alignmentScrollX = clampAlignmentScrollX(
    state.alignmentScrollX + direction * stepPx,
    alignmentLength
  );

  requestAlignmentRedraw();
}

function zoomAlignmentAroundCenter(nextZoom) {
  const alignmentData = getAlignmentData(state.activeAlignmentBlockId);
  const alignmentLength = getAlignmentLength(alignmentData);

  if (alignmentLength === 0) {
    return;
  }

  const previousCharWidth = getAlignmentCharWidth();
  const centerColumn = (state.alignmentScrollX + getAlignmentViewportWidth() / 2)
    / previousCharWidth;

  state.alignmentZoomX = Math.max(0.5, Math.min(4, nextZoom));

  const nextCharWidth = getAlignmentCharWidth();
  state.alignmentScrollX = centerColumn * nextCharWidth - getAlignmentViewportWidth() / 2;
  normalizeAlignmentScrollX(alignmentLength);
  redrawAlignmentViewer();
}

function startAlignmentViewportDrag(pointerX) {
  const alignmentData = getAlignmentData(state.activeAlignmentBlockId);
  const alignmentLength = getAlignmentLength(alignmentData);

  if (getAlignmentMaxScrollX(alignmentLength) <= 0) {
    return;
  }

  state.isDraggingAlignmentViewport = true;
  state.alignmentDragStartPointerX = pointerX;
  state.alignmentDragStartScrollX = state.alignmentScrollX;
  setBodyCursor("grabbing");
}

function updateAlignmentViewportDrag(pointerX) {
  const alignmentData = getAlignmentData(state.activeAlignmentBlockId);
  const alignmentLength = getAlignmentLength(alignmentData);
  const deltaX = pointerX - state.alignmentDragStartPointerX;

  state.alignmentScrollX = clampAlignmentScrollX(
    state.alignmentDragStartScrollX - deltaX,
    alignmentLength
  );
  requestAlignmentRedraw();
}

function updateAlignmentScrollbarDrag(pointerX) {
  const alignmentData = getAlignmentData(state.activeAlignmentBlockId);
  const alignmentLength = getAlignmentLength(alignmentData);
  const sampleCount = getAlignmentSampleNames(alignmentData).length;

  setAlignmentScrollFromThumbX(
    pointerX - state.alignmentScrollbarDragOffsetX,
    alignmentLength,
    sampleCount
  );
  requestAlignmentRedraw();
}

function stopAlignmentDrag() {
  const wasDragging = state.isDraggingAlignmentViewport
    || state.isDraggingAlignmentScrollbar;

  state.isDraggingAlignmentViewport = false;
  state.isDraggingAlignmentScrollbar = false;
  state.alignmentScrollbarDragOffsetX = 0;

  if (wasDragging) {
    setBodyCursor("default");
    setAlignmentCursor("");
  }
}

function startViewportDrag(pointerX) {
  if (getMaxScrollX() <= 0) {
    return;
  }

  state.isDraggingViewport = true;
  state.suppressHover = true;
  state.dragStartPointerX = pointerX;
  state.dragStartScrollX = state.scrollX;
  setBodyCursor("grabbing");
}

function updateViewportDrag(pointerX) {
  const deltaX = pointerX - state.dragStartPointerX;
  const worldDelta = deltaX * (getContentWidth() / getDrawableTrackWidth());
  state.scrollX = clampScrollX(state.dragStartScrollX - worldDelta);
  requestStageRedraw();
}

function updateScrollbarDrag(pointerX) {
  setScrollFromThumbX(pointerX - state.scrollbarDragOffsetX);
  requestStageRedraw();
}

function stopDrag() {
  const wasDragging = state.isDraggingViewport || state.isDraggingScrollbar;
  state.isDraggingViewport = false;
  state.isDraggingScrollbar = false;
  state.scrollbarDragOffsetX = 0;
  state.isHoveringInteractiveFeature = false;
  _lastResolvedHoverKey = null;

  if (wasDragging) {
    state.suppressHover = false;
    setBodyCursor("default");
    setViewerCursor("");
  }
}

function setupColumnResizer() {
  const contentRow = document.getElementById("content-row");
  const rightColumn = document.getElementById("right-column");
  const resizer = document.getElementById("column-resizer");

  if (!contentRow || !rightColumn || !resizer) {
    return;
  }

  let isResizing = false;

  resizer.addEventListener("pointerdown", (event) => {
    isResizing = true;
    resizer.classList.add("is-dragging");
    setBodyCursor("col-resize");
    resizer.setPointerCapture(event.pointerId);
    event.preventDefault();
  });

  resizer.addEventListener("pointermove", (event) => {
    if (!isResizing) {
      return;
    }

    const rowRect = contentRow.getBoundingClientRect();
    const maxSidebarWidth = rowRect.width * CONFIG.sidebarMaxWidthRatio;
    const proposedWidth = rowRect.right - event.clientX;
    const sidebarWidth = Math.max(
      CONFIG.sidebarMinWidth,
      Math.min(maxSidebarWidth, proposedWidth)
    );

    rightColumn.style.flexBasis = `${sidebarWidth}px`;
    rightColumn.style.width = `${sidebarWidth}px`;

    normalizeScrollX();
    requestStageRedraw();
    syncSidebarHeightToViewerColumn();
  });

  function stopColumnResize(event) {
    if (!isResizing) {
      return;
    }

    isResizing = false;
    resizer.classList.remove("is-dragging");
    setBodyCursor("default");

    if (resizer.hasPointerCapture(event.pointerId)) {
      resizer.releasePointerCapture(event.pointerId);
    }
  }

  resizer.addEventListener("pointerup", stopColumnResize);
  resizer.addEventListener("pointercancel", stopColumnResize);
}

function syncSidebarHeightToViewerColumn() {
  // No-op: sidebar grows naturally with content; page scroll handles overflow.
}

function setupFloatingTooltips() {
  const tooltip = document.getElementById("floating-tooltip");

  if (!tooltip) {
    return;
  }

  document.addEventListener("mouseover", (event) => {
    const trigger = event.target.closest(".info-tooltip");

    if (!trigger) {
      return;
    }

    tooltip.textContent = trigger.dataset.tooltip || "";
    tooltip.style.display = "block";

    const triggerRect = trigger.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    const margin = 12;

    let left = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2;
    let top = triggerRect.top - tooltipRect.height - 8;

    left = Math.max(margin, Math.min(left, window.innerWidth - tooltipRect.width - margin));

    if (top < margin) {
      top = triggerRect.bottom + 8;
    }

    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  });

  document.addEventListener("mouseout", (event) => {
    const trigger = event.target.closest(".info-tooltip");

    if (!trigger) {
      return;
    }

    tooltip.style.display = "none";
  });
}

setupFloatingTooltips();

function getViewerToolbarHeight() {
  const toolbar = document.querySelector(".viewer-toolbar");

  if (!toolbar) {
    return CONFIG.viewerTopUiHeight;
  }

  return Math.max(
    CONFIG.viewerTopUiHeight,
    Math.ceil(toolbar.getBoundingClientRect().height) + 8
  );
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
  if (pointer.y >= scrollbarY) {
    applyResolvedHover(null);
    setViewerCursor("");
    return;
  }

  if (!state.suppressHover) {
    const resolved = resolveHoveredFeature(pointer.x, pointer.y);
    applyResolvedHover(resolved);

    if (resolved) {
      setViewerCursor("pointer");
      return;
    }
  }

  if (isPointerOverSampleTrack(pointer.y)) {
    setViewerCursor("");
  } else if (getMaxScrollX() > 0) {
    setViewerCursor("grab");
  } else {
    setViewerCursor("");
  }
});

stage.on("pointerup", stopDrag);
stage.on("pointerleave", () => {
  _lastResolvedHoverKey = null;
  state.isHoveringInteractiveFeature = false;
  stopDrag();
  setViewerCursor("");
});

alignmentStage.on("pointerdown", (event) => {
  if (event.target !== alignmentStage) {
    return;
  }

  const pointer = alignmentStage.getPointerPosition();
  if (!pointer) {
    return;
  }

  const alignmentData = getAlignmentData(state.activeAlignmentBlockId);
  const sampleCount = getAlignmentSampleNames(alignmentData).length;
  const scrollbarY = getAlignmentScrollbarY(sampleCount);

  if (pointer.y >= scrollbarY) {
    return;
  }

  startAlignmentViewportDrag(pointer.x);
});

alignmentStage.on("pointermove", () => {
  const pointer = alignmentStage.getPointerPosition();
  if (!pointer) {
    return;
  }

  if (state.isDraggingAlignmentViewport) {
    updateAlignmentViewportDrag(pointer.x);
    return;
  }

  if (state.isDraggingAlignmentScrollbar) {
    updateAlignmentScrollbarDrag(pointer.x);
    return;
  }

  if (state.activeAlignmentBlockId && getAlignmentData(state.activeAlignmentBlockId)) {
    setAlignmentCursor("grab");
  } else {
    setAlignmentCursor("");
  }
});

alignmentStage.on("pointerup", stopAlignmentDrag);
alignmentStage.on("pointerleave", () => {
  stopAlignmentDrag();
  setAlignmentCursor("");
});

function initDerivedData() {
  derivedData.sampleOrder = REGION_DATA.samples.map(function(s) {
    return s.sample;
  });

  const trackNameSet = new Set();
  for (const sample of REGION_DATA.samples) {
    for (const track of (sample.gff_tracks || [])) {
      trackNameSet.add(track.track_name);
    }
  }
  derivedData.allGffTrackNames = [...trackNameSet].sort();
  derivedData.gffTrackColorByName = new Map(
    derivedData.allGffTrackNames.map(function(name, index) {
      return [name, GFF_TRACK.colors[index % GFF_TRACK.colors.length]];
    })
  );

  const blockPositions = new Map();
  for (const sample of REGION_DATA.samples) {
    for (const block of sample.blocks) {
      if (!blockPositions.has(block.feature_id)) {
        blockPositions.set(block.feature_id, Number(block.block_start_in_zone));
      }
    }
  }
  derivedData.orderedBlockFeatureIds = [...blockPositions.entries()]
    .sort(function(a, b) { return a[1] - b[1]; })
    .map(function(entry) { return entry[0]; });

  const snpPositions = new Map();
  for (const sample of REGION_DATA.samples) {
    for (const snp of sample.snps) {
      if (!snpPositions.has(snp.feature_id)) {
        snpPositions.set(snp.feature_id, Number(snp.pos_in_zone));
      }
    }
  }
  derivedData.orderedSnpFeatureIds = [...snpPositions.entries()]
    .sort(function(a, b) { return a[1] - b[1]; })
    .map(function(entry) { return entry[0]; });

  const k2pValues = [];
  Object.entries(REGION_DATA.kimura2p_matrices || {}).forEach(function([blockId, matrix]) {
    if (!matrix || !matrix.values) {
      return;
    }
    matrix.values.forEach(function(row, rowIndex) {
      row.forEach(function(value, colIndex) {
        if (colIndex <= rowIndex) {
          return;
        }
        const numericValue = Number(value);
        if (!Number.isNaN(numericValue)) {
          k2pValues.push(numericValue);
        }
      });
    });
  });

  if (k2pValues.length === 0) {
    console.warn("Kimura 2P color scale: no numeric off-diagonal values found.");
    derivedData.kimura2pGlobalColorScaleBounds = { min: 0, max: 1 };
  } else {
    derivedData.kimura2pGlobalColorScaleBounds = {
      min: Math.min(...k2pValues),
      max: Math.max(...k2pValues)
    };
  }
}

state.featureGroups = buildFeatureGroups(REGION_DATA);
initDerivedData();
renderAnalysisSettings();
renderSidebarDefault();
state.zoomX = getInitialZoomX();
state.scrollX = 0;
setupColumnResizer();
setupWheelScrolling();
showRenderingOverlay();
requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    redrawStage();
    redrawAlignmentViewer();
    syncSidebarHeightToViewerColumn();
    hideRenderingOverlay();
  });
});

window.addEventListener("resize", () => {
  normalizeScrollX();
  requestStageRedraw();
  requestAlignmentRedraw();
  syncSidebarHeightToViewerColumn();
});

document.getElementById("feature-prev").addEventListener("click", () => {
  pinNeighborFeature(-1);
});

document.getElementById("feature-next").addEventListener("click", () => {
  pinNeighborFeature(1);
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

function getWheelDeltaX(event) {
  if (Math.abs(event.deltaX) > Math.abs(event.deltaY)) {
    return event.deltaX;
  }

  if (event.shiftKey) {
    return event.deltaY;
  }

  return 0;
}

function setActiveKeyboardViewer(viewerName) {
  state.activeKeyboardViewer = viewerName;
}

function setupWheelScrolling() {
  const viewerElement = document.getElementById("viewer");
  const alignmentElement = document.getElementById("alignment-viewer");

  viewerElement.addEventListener("wheel", (event) => {
    const deltaX = getWheelDeltaX(event);

    if (deltaX === 0) {
      return;
    }

    event.preventDefault();
    state.scrollX = clampScrollX(state.scrollX + deltaX);
    requestStageRedraw();
  }, { passive: false });

  alignmentElement.addEventListener("wheel", (event) => {
    const deltaX = getWheelDeltaX(event);

    if (deltaX === 0) {
      return;
    }

    event.preventDefault();
    const alignmentData = getAlignmentData(state.activeAlignmentBlockId);
    const alignmentLength = getAlignmentLength(alignmentData);
    state.alignmentScrollX = clampAlignmentScrollX(
      state.alignmentScrollX + deltaX,
      alignmentLength
    );
    requestAlignmentRedraw();
  }, { passive: false });

  viewerElement.addEventListener("pointerdown", () => {
    setActiveKeyboardViewer("region");
  });

  alignmentElement.addEventListener("pointerdown", () => {
    setActiveKeyboardViewer("alignment");
  });
}

window.addEventListener("keydown", (event) => {
  if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") {
    return;
  }

  event.preventDefault();
  const direction = event.key === "ArrowLeft" ? -1 : 1;

  if (state.activeKeyboardViewer === "alignment") {
    moveAlignmentByViewportFraction(direction);
  } else {
    moveByViewportFraction(direction, 0.1);
  }
});

document.getElementById("alignment-snp-prev").addEventListener("click", () => {
  focusNeighborAlignmentSnp(-1);
});

document.getElementById("alignment-snp-next").addEventListener("click", () => {
  focusNeighborAlignmentSnp(1);
});

document.getElementById("alignment-pan-left").addEventListener("click", () => {
  moveAlignmentByViewportFraction(-1);
});

document.getElementById("alignment-pan-right").addEventListener("click", () => {
  moveAlignmentByViewportFraction(1);
});

document.getElementById("alignment-zoom-in").addEventListener("click", () => {
  zoomAlignmentAroundCenter(state.alignmentZoomX * 1.25);
});

document.getElementById("alignment-zoom-out").addEventListener("click", () => {
  zoomAlignmentAroundCenter(state.alignmentZoomX / 1.25);
});

document.getElementById("alignment-zoom-reset").addEventListener("click", () => {
  state.alignmentZoomX = 1;
  state.alignmentScrollX = 0;
  redrawAlignmentViewer();
});

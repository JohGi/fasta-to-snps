#!/usr/bin/env python3
# Author: Johanna Girodolle

"""Constants used by the region overview generator."""

TRACK_HEIGHT = 28
FEATURE_HEIGHT = 22
SNP_HEIGHT = 20
TRACK_Y_OFFSET = 12
PANEL_BOTTOM_SPACE = 12
PANEL_HEIGHT = TRACK_Y_OFFSET + TRACK_HEIGHT + PANEL_BOTTOM_SPACE
PANEL_GAP = 6
VIEWER_TOP_UI_HEIGHT = 44
LEFT_MARGIN = 110
RIGHT_MARGIN = 40
TOP_MARGIN = 52
BOTTOM_MARGIN = 30
SNP_LINE_WIDTH = 1
VIEWER_MIN_WIDTH = 900
SIDEBAR_WIDTH = 320

# Zoom behaviour
TARGET_VISIBLE_BP = 500_000  # ~20 kb visible at max zoom
ZOOM_STEPS = 6              # number of clicks to reach max zoom
MAX_ZOOM_CAP = 1000         # hard cap to avoid huge canvases

# Axis behaviour
TARGET_TICK_SPACING_PX = 100  # desired pixel spacing between ticks

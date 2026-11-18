import html
import json
import os
import pathlib
import urllib.parse
from datetime import datetime, timezone

import networkx as nx
import pandas as pd
import streamlit as st
from streamlit_agraph import agraph, Config, Edge, Node


# Handle both local and Streamlit Cloud paths
_REPO_ROOT = pathlib.Path(__file__).parent.parent
_DATA_DIR = pathlib.Path(os.getenv("DATA_DIR", str(_REPO_ROOT / "data")))

# Also check common Streamlit Cloud mount paths
if not _DATA_DIR.exists():
    _DATA_DIR = pathlib.Path("/mount/src") / _REPO_ROOT.name / "data"
if not _DATA_DIR.exists():
    _DATA_DIR = pathlib.Path("/mount/src/data")

DATA_DIR = _DATA_DIR
FINDINGS_FILE = DATA_DIR / "scored_findings.jsonl"
GRAPH_FILE = DATA_DIR / "graph.graphml"
SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
SEVERITY_BASELINES = {
    "CRITICAL": 0.75,
    "HIGH": 0.60,
    "MEDIUM": 0.40,
    "LOW": 0.20,
    "INFO": 0.10,
}
PUBLIC_ADMIN_METHOD = "severity_plus_public_admin_reachability"
PRINCIPAL_ESCALATION_METHOD = "severity_plus_principal_escalation"

APP_CSS = """
<style>
/* ============================================================
   CSPM Console — Design System
   ============================================================ */
:root {
  /* ---- Color Palette ---- */
  /* Neutrals */
  --color-bg: #f4f7fb;
  --color-surface: #ffffff;
  --color-surface-hover: #f8fafc;
  --color-border: #dce5ef;
  --color-border-strong: #c7d2e0;
  --color-text: #172b45;
  --color-text-muted: #64748b;
  --color-text-subtle: #94a3b8;

  /* Brand */
  --color-navy: #10243a;
  --color-navy-light: #1a334f;
  --color-teal: #0d9488;
  --color-teal-light: #14b8a6;
  --color-teal-bg: #e6fbf8;
  --color-blue: #3b82f6;
  --color-blue-light: #60a5fa;
  --color-blue-bg: #eff6ff;

  /* Semantic / Severity */
  --color-critical: #dc2626;
  --color-critical-bg: #fef2f2;
  --color-critical-border: #fecaca;
  --color-high: #ea580c;
  --color-high-bg: #fff7ed;
  --color-high-border: #fed7aa;
  --color-medium: #d97706;
  --color-medium-bg: #fffbeb;
  --color-medium-border: #fde68a;
  --color-low: #16a34a;
  --color-low-bg: #f0fdf4;
  --color-low-border: #bbf7d0;
  --color-info: #0891b2;
  --color-info-bg: #f0f9ff;
  --color-info-border: #bae6fd;

  /* State */
  --color-focus: #3b82f6;
  --color-focus-ring: rgba(59, 130, 246, 0.3);
  --color-disabled: #e2e8f0;

  /* ---- Spacing Scale ---- */
  --space-1: 0.25rem;  /* 4px */
  --space-2: 0.5rem;   /* 8px */
  --space-3: 0.75rem;  /* 12px */
  --space-4: 1rem;     /* 16px */
  --space-5: 1.25rem;  /* 20px */
  --space-6: 1.5rem;   /* 24px */
  --space-8: 2rem;     /* 32px */
  --space-10: 2.5rem;  /* 40px */
  --space-12: 3rem;    /* 48px */

  /* ---- Border Radius ---- */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;
  --radius-full: 999px;

  /* ---- Shadows ---- */
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.05);
  --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.08);
  --shadow-lg: 0 12px 28px rgba(15, 23, 42, 0.1);
  --shadow-xl: 0 20px 40px rgba(15, 23, 42, 0.12);

  /* ---- Typography ---- */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: "SF Mono", "Fira Code", "Fira Mono", Menlo, Consolas, monospace;

  --text-xs: 0.6875rem;   /* 11px */
  --text-sm: 0.8125rem;   /* 13px */
  --text-base: 0.9375rem; /* 15px */
  --text-lg: 1.0625rem;   /* 17px */
  --text-xl: 1.25rem;     /* 20px */
  --text-2xl: 1.5rem;     /* 24px */
  --text-3xl: 1.875rem;   /* 30px */
  --text-4xl: 2.25rem;    /* 36px */

  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;

  /* ---- Layout ---- */
  --sidebar-width: 280px;
  --header-height: 64px;
  --max-content-width: 1440px;

  /* ---- Transitions ---- */
  --transition-fast: 120ms ease;
  --transition-base: 200ms ease;
}

/* ============================================================
   Global Reset & Base
   ============================================================ */
[data-testid="stAppViewContainer"] {
  background: var(--color-bg);
  font-family: var(--font-sans);
  color: var(--color-text);
}

[data-testid="stHeader"] {
  background: rgba(244, 247, 251, 0.95);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--color-border);
}

.main .block-container {
  max-width: var(--max-content-width);
  padding-top: var(--space-5);
  padding-bottom: var(--space-10);
  padding-left: var(--space-6);
  padding-right: var(--space-6);
}

/* ============================================================
   Sidebar
   ============================================================ */
[data-testid="stSidebar"] {
  background: var(--color-navy);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  width: var(--sidebar-width) !important;
  min-width: var(--sidebar-width) !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] .stRadio label {
  color: #e8edf5 !important;
}

[data-testid="stSidebar"] .stRadio > div {
  gap: var(--space-2);
}

[data-testid="stSidebar"] .stRadio label {
  font-weight: var(--font-medium) !important;
  font-size: var(--text-sm);
  padding: var(--space-2) var(--space-3) !important;
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}

[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(255, 255, 255, 0.06);
}

[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
  margin: 0 !important;
}

/* Sidebar navigation - custom buttons styled */
.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

/* Sidebar brand */
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-4) var(--space-4);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  margin-bottom: var(--space-3);
}

.sidebar-brand-icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, var(--color-teal) 0%, var(--color-blue) 100%);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(13, 148, 136, 0.3);
}

.sidebar-brand-icon svg {
  width: 24px;
  height: 24px;
  stroke: white;
}

.sidebar-brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.sidebar-brand-title {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: #ffffff;
  letter-spacing: -0.02em;
}

.sidebar-brand-subtitle {
  font-size: var(--text-xs);
  color: #8ca3bf;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: var(--font-medium);
}

/* Sidebar navigation */
.sidebar-nav {
  padding: 0 var(--space-3) var(--space-4);
}

.sidebar-nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  color: #c7d5e6;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
  background: transparent;
  width: 100%;
  text-align: left;
}

.sidebar-nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;
}

.sidebar-nav-item.active {
  background: rgba(13, 148, 136, 0.15);
  color: var(--color-teal-light);
}

.sidebar-nav-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sidebar-nav-icon svg {
  width: 20px;
  height: 20px;
  stroke: currentColor;
}

.sidebar-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
  margin: var(--space-4) var(--space-3);
}

.sidebar-footer {
  padding: var(--space-4);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  margin-top: var(--space-2);
}

.sidebar-footer-text {
  font-size: var(--text-xs);
  color: #6d8299;
  line-height: 1.5;
}

/* Refresh button in sidebar - high contrast */
.sidebar-refresh-btn {
  background: var(--color-teal) !important;
  color: white !important;
  border: none !important;
  font-weight: var(--font-semibold) !important;
}

.sidebar-refresh-btn:hover {
  background: var(--color-teal-light) !important;
  box-shadow: 0 4px 16px rgba(13, 148, 136, 0.3) !important;
}

/* Sidebar navigation radio - styled as horizontal icon buttons */
[data-testid="stSidebar"] .stRadio[data-testid="stRadio"] > div {
  display: flex !important;
  flex-direction: row !important;
  gap: var(--space-1);
  justify-content: center;
  padding: 0 var(--space-3) var(--space-4);
}

[data-testid="stSidebar"] .stRadio[data-testid="stRadio"] label {
  flex: 1;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  gap: var(--space-1);
  padding: var(--space-3) var(--space-2) !important;
  border-radius: var(--radius-md) !important;
  color: #c7d5e6 !important;
  font-size: var(--text-sm) !important;
  font-weight: var(--font-medium) !important;
  cursor: pointer;
  transition: all var(--transition-fast);
  background: transparent !important;
  border: none !important;
  min-height: 64px;
  position: relative;
}

/* Icon for Findings (house) */
[data-testid="stSidebar"] .stRadio[data-testid="stRadio"]
label:first-of-type::before {
  content: "";
  width: 22px;
  height: 22px;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' "
    "fill='none' stroke='%23c7d5e6' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round' "
    "xmlns='http://www.w3.org/2000/svg'%3E%3Cpath "
    "d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'%3E"
    "%3C/path%3E%3Cpolyline points='9 22 9 12 15 12 15 22'%3E"
    "%3C/polyline%3E%3C/svg%3E");
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  flex-shrink: 0;
}

/* Icon for Attack Graph (network) */
[data-testid="stSidebar"] .stRadio[data-testid="stRadio"]
label:last-of-type::before {
  content: "";
  width: 22px;
  height: 22px;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' "
    "fill='none' stroke='%23c7d5e6' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round' "
    "xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='12' "
    "cy='12' r='10'%3E%3C/circle%3E%3Cline x1='2' y1='12' "
    "x2='22' y2='12'%3E%3C/line%3E%3Cline x1='12' y1='2' "
    "x2='12' y2='22'%3E%3C/line%3E%3C/svg%3E");
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  flex-shrink: 0;
}

/* Hide the text labels - we use icons only */
[data-testid="stSidebar"] .stRadio[data-testid="stRadio"]
label > div[data-testid="stMarkdownContainer"] {
  display: none !important;
}

[data-testid="stSidebar"] .stRadio[data-testid="stRadio"] label:hover {
  background: rgba(255, 255, 255, 0.06) !important;
  color: #ffffff !important;
}

[data-testid="stSidebar"] .stRadio[data-testid="stRadio"]
label:hover::before {
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' "
    "fill='none' stroke='%23ffffff' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round' "
    "xmlns='http://www.w3.org/2000/svg'%3E%3Cpath "
    "d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'%3E"
    "%3C/path%3E%3Cpolyline points='9 22 9 12 15 12 15 22'%3E"
    "%3C/polyline%3E%3C/svg%3E") !important;
}

[data-testid="stSidebar"] .stRadio[data-testid="stRadio"]
label:last-of-type:hover::before {
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' "
    "fill='none' stroke='%23ffffff' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round' "
    "xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='12' "
    "cy='12' r='10'%3E%3C/circle%3E%3Cline x1='2' y1='12' "
    "x2='22' y2='12'%3E%3C/line%3E%3Cline x1='12' y1='2' "
    "x2='12' y2='22'%3E%3C/line%3E%3C/svg%3E") !important;
}

[data-testid="stSidebar"] .stRadio[data-testid="stRadio"]
label:has(input:checked) {
  background: rgba(13, 148, 136, 0.15) !important;
  color: var(--color-teal-light) !important;
}

[data-testid="stSidebar"] .stRadio[data-testid="stRadio"]
label:has(input:checked)::before {
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' "
    "fill='none' stroke='%2314b8a6' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round' "
    "xmlns='http://www.w3.org/2000/svg'%3E%3Cpath "
    "d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'%3E"
    "%3C/path%3E%3Cpolyline points='9 22 9 12 15 12 15 22'%3E"
    "%3C/polyline%3E%3C/svg%3E") !important;
}

[data-testid="stSidebar"] .stRadio[data-testid="stRadio"]
label:last-of-type:has(input:checked)::before {
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' "
    "fill='none' stroke='%2314b8a6' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round' "
    "xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='12' "
    "cy='12' r='10'%3E%3C/circle%3E%3Cline x1='2' y1='12' "
    "x2='22' y2='12'%3E%3C/line%3E%3Cline x1='12' y1='2' "
    "x2='12' y2='22'%3E%3C/line%3E%3C/svg%3E") !important;
}

[data-testid="stSidebar"] .stRadio[data-testid="stRadio"] input[type="radio"] {
  position: absolute !important;
  opacity: 0 !important;
  pointer-events: none !important;
  width: 0 !important;
  height: 0 !important;
}

/* Focus styles for accessibility */
[data-testid="stSidebar"] .stRadio[data-testid="stRadio"] label:has(input:focus-visible) {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

/* Hide Streamlit's default header chrome */
[data-testid="stHeader"] {
  background: rgba(244, 247, 251, 0.95);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--color-border);
}

[data-testid="stToolbar"] {
  display: none !important;
}

[data-testid="stDecoration"] {
  display: none !important;
}

/* ============================================================
   Hero / Page Header
   ============================================================ */
.hero {
  background: linear-gradient(135deg, var(--color-navy) 0%, #1a3a5c 50%, #1e4d66 100%);
  border: 1px solid rgba(37, 73, 96, 0.5);
  border-radius: var(--radius-xl);
  padding: var(--space-4) var(--space-5);
  margin: var(--space-2) 0 var(--space-5);
  color: #f7fbff;
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}

.hero::before {
  content: "";
  position: absolute;
  top: -50%;
  right: -20%;
  width: 60%;
  height: 200%;
  background: radial-gradient(ellipse, rgba(13, 148, 136, 0.08) 0%, transparent 70%);
  pointer-events: none;
}

.hero-kicker {
  color: #8ee1d1;
  font-size: var(--text-xs);
  letter-spacing: 0.14em;
  font-weight: var(--font-bold);
  text-transform: uppercase;
  margin: 0 0 var(--space-2);
  position: relative;
  z-index: 1;
}

.hero h1 {
  color: #ffffff;
  font-size: clamp(var(--text-xl), 3vw, var(--text-3xl));
  line-height: 1.2;
  margin: 0 0 var(--space-2);
  font-weight: var(--font-bold);
  letter-spacing: -0.02em;
  position: relative;
  z-index: 1;
}

.hero-copy {
  color: #d4e1ec;
  font-size: var(--text-sm);
  margin: 0 0 var(--space-3);
  max-width: 720px;
  line-height: 1.5;
  position: relative;
  z-index: 1;
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
  background: rgba(13, 148, 136, 0.12);
  color: #a3f0df;
  border: 1px solid rgba(142, 225, 209, 0.25);
  border-radius: var(--radius-full);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  position: relative;
  z-index: 1;
}

.hero-tag::before {
  content: "";
  width: 6px;
  height: 6px;
  background: var(--color-teal);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ============================================================
   Metrics / KPI Cards
   ============================================================ */
[data-testid="stMetric"] {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-5);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition-base), border-color var(--transition-base);
}

[data-testid="stMetric"]:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--color-border-strong);
}

[data-testid="stMetricLabel"] {
  padding-bottom: var(--space-1) !important;
}

[data-testid="stMetricLabel"] p {
  color: var(--color-text-muted) !important;
  font-weight: var(--font-medium) !important;
  font-size: var(--text-sm) !important;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

[data-testid="stMetricValue"] {
  color: var(--color-text) !important;
  font-weight: var(--font-bold) !important;
  font-size: var(--text-3xl) !important;
  line-height: 1.2;
}

[data-testid="stMetricDelta"] {
  font-size: var(--text-sm) !important;
  font-weight: var(--font-medium) !important;
}

/* ============================================================
   Section Headers
   ============================================================ */
.section-title {
  color: var(--color-text);
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  margin: var(--space-2) 0 var(--space-1);
  letter-spacing: -0.01em;
}

.section-copy {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  margin: 0 0 var(--space-5);
  line-height: 1.5;
}

.panel-title {
  color: var(--color-text);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  margin-bottom: var(--space-2);
}

/* ============================================================
   Pills / Badges
   ============================================================ */
.pill {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  border: 1px solid transparent;
  line-height: 1;
  white-space: nowrap;
}

.pill-critical {
  background: var(--color-critical-bg);
  color: var(--color-critical);
  border-color: var(--color-critical-border);
}
.pill-high {
  background: var(--color-high-bg);
  color: var(--color-high);
  border-color: var(--color-high-border);
}
.pill-medium {
  background: var(--color-medium-bg);
  color: var(--color-medium);
  border-color: var(--color-medium-border);
}
.pill-low {
  background: var(--color-low-bg);
  color: var(--color-low);
  border-color: var(--color-low-border);
}
.pill-info {
  background: var(--color-info-bg);
  color: var(--color-info);
  border-color: var(--color-info-border);
}

/* ============================================================
   Path Steps
   ============================================================ */
.path-step {
  border-left: 3px solid var(--color-blue);
  padding: var(--space-3) var(--space-4);
  margin: var(--space-2) 0;
  background: var(--color-blue-bg);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  color: var(--color-text);
  font-size: var(--text-sm);
  line-height: 1.5;
}

.path-step small {
  display: block;
  color: var(--color-text-muted);
  font-weight: var(--font-semibold);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: var(--space-1);
  font-size: var(--text-xs);
}

/* ============================================================
   Legend
   ============================================================ */
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3) var(--space-4);
  align-items: center;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  margin: var(--space-2) 0 var(--space-3);
  padding: var(--space-2) 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ============================================================
   Data Table
   ============================================================ */
[data-testid="stDataFrame"] {
  border: 1px solid var(--color-border) !important;
  border-radius: var(--radius-lg) !important;
  overflow: hidden !important;
  background: var(--color-surface);
}

[data-testid="stDataFrame"] > div {
  overflow-x: auto !important;
}

/* Table header */
[data-testid="stDataFrame"] [data-testid="stTable"] thead th,
[data-testid="stDataFrame"] thead th {
  background: #f8fafc !important;
  color: var(--color-text-muted) !important;
  font-weight: var(--font-semibold) !important;
  font-size: var(--text-xs) !important;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: var(--space-3) var(--space-4) !important;
  border-bottom: 2px solid var(--color-border) !important;
}

/* Table cells */
[data-testid="stDataFrame"] tbody td {
  padding: var(--space-3) var(--space-4) !important;
  font-size: var(--text-sm) !important;
  color: var(--color-text) !important;
  border-bottom: 1px solid var(--color-border) !important;
}

[data-testid="stDataFrame"] tbody tr:last-child td {
  border-bottom: none !important;
}

[data-testid="stDataFrame"] tbody tr:hover td {
  background: var(--color-surface-hover) !important;
}

/* ============================================================
   Form Controls
   ============================================================ */
.stTextInput > div > div > input,
.stSelectbox > div > div > div,
.stMultiSelect > div > div > div {
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--color-border) !important;
  background: var(--color-surface) !important;
  color: var(--color-text) !important;
  font-size: var(--text-sm) !important;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast) !important;
}

.stTextInput > div > div > input:focus,
.stSelectbox > div > div > div:focus-within,
.stMultiSelect > div > div > div:focus-within {
  border-color: var(--color-focus) !important;
  box-shadow: 0 0 0 3px var(--color-focus-ring) !important;
}

.stTextInput > div > div > input::placeholder {
  color: var(--color-text-subtle) !important;
}

/* Multiselect tags */
.stMultiSelect [data-baseweb="tag"] {
  background: var(--color-blue-bg) !important;
  color: var(--color-blue) !important;
  border-radius: var(--radius-sm) !important;
  font-size: var(--text-xs) !important;
  font-weight: var(--font-medium) !important;
}

.stMultiSelect [data-baseweb="tag"] [data-icon="close"] {
  color: var(--color-blue) !important;
}

/* ============================================================
   Buttons
   ============================================================ */
.stButton > button {
  border-radius: var(--radius-md) !important;
  font-weight: var(--font-semibold) !important;
  font-size: var(--text-sm) !important;
  padding: var(--space-2) var(--space-5) !important;
  transition: all var(--transition-fast) !important;
  border: none !important;
}

.stButton > button[kind="primary"] {
  background: var(--color-teal) !important;
  color: white !important;
}

.stButton > button[kind="primary"]:hover {
  background: var(--color-teal-light) !important;
  box-shadow: 0 4px 16px rgba(13, 148, 136, 0.3) !important;
}

.stButton > button[kind="secondary"] {
  background: var(--color-surface) !important;
  color: var(--color-text) !important;
  border: 1px solid var(--color-border) !important;
}

.stButton > button[kind="secondary"]:hover {
  background: var(--color-surface-hover) !important;
  border-color: var(--color-border-strong) !important;
}

/* ============================================================
   Filter Row
   ============================================================ */
.filter-row {
  display: flex;
  gap: var(--space-3);
  align-items: flex-end;
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}

.filter-row > div {
  flex: 1;
  min-width: 0;
}

/* Force consistent height and vertical alignment for all filter inputs */
.filter-row .stTextInput,
.filter-row .stMultiSelect,
.filter-row .stSelectbox,
.filter-row .stButton {
  display: flex;
  align-items: flex-end;
}

.filter-row .stTextInput > div > div > input,
.filter-row .stMultiSelect > div > div,
.filter-row .stSelectbox > div > div {
  height: 44px !important;
  min-height: 44px !important;
}

.filter-row .stButton > button {
  height: 44px !important;
  min-height: 44px !important;
  white-space: nowrap;
}

/* Severity multiselect chips */
.filter-row .stMultiSelect [data-baseweb="tag"] {
  background: var(--color-blue-bg) !important;
  color: var(--color-blue) !important;
  border-radius: var(--radius-sm) !important;
  font-size: var(--text-xs) !important;
  font-weight: var(--font-medium) !important;
  border: 1px solid var(--color-blue) !important;
}

.filter-row .stMultiSelect [data-baseweb="tag"] [data-icon="close"] {
  color: var(--color-blue) !important;
}

/* Active filter count badge */
.filter-badge {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-2);
  background: var(--color-teal-bg);
  color: var(--color-teal);
  border: 1px solid var(--color-teal);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  margin-left: var(--space-2);
}

/* Reset button styling */
.filter-row .stButton > button {
  height: 44px !important;
  white-space: nowrap;
}

/* ============================================================
   Graph Container
   ============================================================ */
.graph-container {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  position: relative;
  /* No fixed min-height - let content determine size */
}

.graph-container:focus-within {
  border-color: var(--color-focus);
  box-shadow: var(--shadow-md), 0 0 0 3px var(--color-focus-ring);
}

/* Ensure agraph canvas fills container */
.graph-container .stMarkdown > div > div {
  width: 100%;
}
.graph-container canvas {
  width: 100% !important;
  height: 100% !important;
}
.graph-canvas-wrapper {
  width: 100%;
  /* Height controlled by agraph config (600px), no fixed CSS height */
  position: relative;
}
.graph-canvas-wrapper > div {
  width: 100% !important;
  height: 100% !important;
}

/* Graph toolbar */
.graph-toolbar {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
  align-items: center;
  margin-top: calc(-1 * var(--space-3));
}

/* Reduce space between expander and toolbar */
[data-testid="stSidebar"] + .main .stExpander:last-child {
  margin-bottom: 0 !important;
}

/* Tight spacing for graph components in main area */
.main .block-container .stExpander:has(.graph-toolbar) + .graph-toolbar,
.main .block-container .stExpander + .graph-toolbar {
  margin-top: var(--space-1);
}

.graph-toolbar-btn {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  min-height: 36px;
}

.graph-toolbar-btn:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border-strong);
}

.graph-toolbar-btn:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}

.graph-toolbar-btn.primary {
  background: var(--color-teal);
  border-color: var(--color-teal);
  color: white;
}

.graph-toolbar-btn.primary:hover {
  background: var(--color-teal-light);
  border-color: var(--color-teal-light);
}

.graph-toolbar-divider {
  width: 1px;
  height: 24px;
  background: var(--color-border);
  margin: 0 var(--space-1);
}

.graph-toolbar-group {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.graph-toolbar-spacer {
  flex: 1;
}

/* Graph canvas wrapper for proper sizing */
.graph-canvas-wrapper {
  width: 100%;
  position: relative;
}

/* Loading state for graph */
.graph-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 600px;
  color: var(--color-text-muted);
  font-size: var(--text-base);
}

.graph-error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 600px;
  color: var(--color-critical);
  font-size: var(--text-sm);
  padding: var(--space-4);
  text-align: center;
}

/* ============================================================
   Expander
   ============================================================ */
.streamlit-expanderHeader {
  background: var(--color-surface) !important;
  border: 1px solid var(--color-border) !important;
  border-radius: var(--radius-md) !important;
  font-weight: var(--font-semibold) !important;
  font-size: var(--text-sm) !important;
  color: var(--color-text) !important;
}

.streamlit-expanderContent {
  border: 1px solid var(--color-border) !important;
  border-top: none !important;
  border-radius: 0 0 var(--radius-md) var(--radius-md) !important;
  background: var(--color-surface) !important;
  padding: var(--space-3) !important;
}

/* ============================================================
   Loading & Empty States
   ============================================================ */
.loading-skeleton {
  background: linear-gradient(90deg, var(--color-border) 25%, var(--color-border-strong) 50%, var(--color-border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-10) var(--space-6);
  text-align: center;
  color: var(--color-text-muted);
}

.empty-state-icon {
  width: 64px;
  height: 64px;
  color: var(--color-text-subtle);
  margin-bottom: var(--space-4);
  opacity: 0.6;
}

.empty-state-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.empty-state-message {
  font-size: var(--text-sm);
  line-height: 1.6;
  max-width: 400px;
}

/* Error state */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-6) var(--space-4);
  text-align: center;
  background: var(--color-critical-bg);
  border: 1px solid var(--color-critical-border);
  border-radius: var(--radius-lg);
  color: var(--color-critical);
}

.error-state-icon {
  width: 48px;
  height: 48px;
  margin-bottom: var(--space-3);
}

.error-state-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-2);
}

.error-state-message {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* ============================================================
   Alerts / Info / Warning
   ============================================================ */
.stAlert {
  border-radius: var(--radius-md) !important;
  border: none !important;
  padding: var(--space-3) var(--space-4) !important;
  font-size: var(--text-sm) !important;
}

.stAlert[data-baseweb="notification"][kind="info"] {
  background: var(--color-info-bg) !important;
  color: var(--color-info) !important;
  border-left: 4px solid var(--color-info) !important;
}

.stAlert[data-baseweb="notification"][kind="warning"] {
  background: var(--color-medium-bg) !important;
  color: var(--color-medium) !important;
  border-left: 4px solid var(--color-medium) !important;
}

.stAlert[data-baseweb="notification"][kind="error"] {
  background: var(--color-critical-bg) !important;
  color: var(--color-critical) !important;
  border-left: 4px solid var(--color-critical) !important;
}

.stAlert[data-baseweb="notification"][kind="success"] {
  background: var(--color-low-bg) !important;
  color: var(--color-low) !important;
  border-left: 4px solid var(--color-low) !important;
}

/* ============================================================
   Divider
   ============================================================ */
hr {
  border: none !important;
  border-top: 1px solid var(--color-border) !important;
  margin: var(--space-6) 0 !important;
}

/* ============================================================
   Scrollbar
   ============================================================ */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--color-border-strong);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-subtle);
}

/* ============================================================
   Responsive
   ============================================================ */
@media (max-width: 1200px) {
  .main .block-container {
    padding-left: var(--space-4);
    padding-right: var(--space-4);
  }

  .graph-toolbar {
    flex-wrap: wrap;
  }

  .graph-toolbar-group {
    flex: 1 1 50%;
  }
}

@media (max-width: 900px) {
  .hero {
    padding: var(--space-5) var(--space-5);
    border-radius: var(--radius-lg);
  }

  .filter-row {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-row > div {
    width: 100%;
  }

  .graph-toolbar-group {
    flex: 1 1 100%;
  }

  .graph-toolbar-divider {
    display: none;
  }

  .graph-toolbar .stColumns {
    width: 100% !important;
  }
}

@media (max-width: 760px) {
  .main .block-container {
    padding-left: var(--space-3);
    padding-right: var(--space-3);
    padding-top: var(--space-4);
  }

  .hero {
    padding: var(--space-4);
    border-radius: var(--radius-md);
    margin: var(--space-2) calc(var(--space-3) * -1) var(--space-5);
  }

  .hero h1 {
    font-size: var(--text-2xl);
  }

  .hero-copy {
    font-size: var(--text-sm);
  }

  [data-testid="stMetric"] {
    padding: var(--space-3) var(--space-4);
  }

  [data-testid="stMetricValue"] {
    font-size: var(--text-2xl) !important;
  }

  .section-title {
    font-size: var(--text-lg);
  }

  /* Stack table and detail panel on mobile */
  .stHorizontalBlock[data-testid="column"] {
    flex-direction: column;
  }

  /* Full width columns on mobile */
  [data-testid="column"] {
    width: 100% !important;
    min-width: 100% !important;
  }
}

/* Tablet: side-by-side but narrower */
@media (max-width: 1024px) and (min-width: 761px) {
  .stHorizontalBlock[data-testid="column"]:first-child {
    flex: 0 0 55% !important;
  }
  .stHorizontalBlock[data-testid="column"]:last-child {
    flex: 0 0 45% !important;
  }
}

/* ============================================================
   Focus Visible (Accessibility)
   ============================================================ */
:focus-visible {
  outline: 2px solid var(--color-focus) !important;
  outline-offset: 2px !important;
}

/* Ensure Streamlit inputs have visible focus */
.stTextInput > div > div > input:focus-visible,
.stSelectbox > div > div > div:focus-visible,
.stMultiSelect > div > div > div:focus-visible,
.stButton > button:focus-visible,
.stCheckbox > label:focus-visible,
.stRadio > div > label:focus-visible {
  outline: 2px solid var(--color-focus) !important;
  outline-offset: 2px !important;
  box-shadow: 0 0 0 3px var(--color-focus-ring) !important;
}

/* Skip link for keyboard navigation */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--color-focus);
  color: white;
  padding: var(--space-2) var(--space-4);
  z-index: 1000;
  border-radius: 0 0 var(--radius-md) 0;
  font-weight: var(--font-medium);
  text-decoration: none;
}

.skip-link:focus {
  top: 0;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  :root {
    --color-border: #000;
    --color-border-strong: #000;
    --color-text-muted: #333;
  }

  .graph-container {
    border-width: 2px;
  }

  .pill {
    border-width: 2px;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }

  .hero-tag::before {
    animation: none;
  }

  .loading-skeleton {
    animation: none;
  }
}

/* ============================================================
   Print
   ============================================================ */
@media print {
  [data-testid="stSidebar"],
  .stButton,
  .filter-row,
  .hero-tag,
  .streamlit-expanderHeader {
    display: none !important;
  }

  .main .block-container {
    max-width: 100%;
    padding: 0;
  }

  .hero {
    background: none !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0;
    margin-bottom: var(--space-4);
  }

  .hero h1 {
    color: var(--color-text) !important;
  }

  .hero-copy {
    color: var(--color-text-muted) !important;
  }
}
</style>
"""


@st.cache_data(show_spinner=False)
def load_findings(file_path, modified_ns, file_size):
    """Read scored JSONL; file metadata arguments invalidate cached results."""
    path = pathlib.Path(file_path)
    if not path.exists():
        return pd.DataFrame(), []

    rows = []
    errors = []
    with path.open(encoding="utf-8") as findings_file:
        for line_number, line in enumerate(findings_file, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except (json.JSONDecodeError, TypeError) as error:
                errors.append(f"Line {line_number}: {error}")
    return pd.DataFrame(rows), errors


@st.cache_data(show_spinner=False)
def load_graph(file_path, modified_ns, file_size):
    """Read GraphML with cache keys tied to the source file version."""
    path = pathlib.Path(file_path)
    if not path.exists():
        return nx.DiGraph(), None
    try:
        return nx.read_graphml(path), None
    except (OSError, nx.NetworkXError, ValueError) as error:
        return nx.DiGraph(), str(error)


def file_version(path):
    """Return stable cache-key inputs, including a missing-file sentinel."""
    try:
        stat = path.stat()
        return stat.st_mtime_ns, stat.st_size
    except OSError:
        return None, None


def normalize_findings(frame):
    """Fill optional columns and normalize score/severity types for display."""
    columns = [
        "resource_id",
        "rule_id",
        "static_severity",
        "risk_score",
        "scoring_method",
        "risk_reason",
        "attack_path",
        "attack_path_edges",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)

    normalized = frame.copy()
    for column in columns:
        if column not in normalized:
            normalized[column] = None
    normalized["static_severity"] = (
        normalized["static_severity"].fillna("INFO").astype(str).str.upper()
    )
    normalized["risk_score"] = pd.to_numeric(
        normalized["risk_score"], errors="coerce"
    )
    fallback_scores = normalized["static_severity"].map(SEVERITY_BASELINES).fillna(0.25)
    normalized["risk_score"] = normalized["risk_score"].fillna(fallback_scores)
    for column in ("attack_path", "attack_path_edges"):
        normalized[column] = normalized[column].map(
            lambda value: value if isinstance(value, list) else []
        )
    return normalized


def filter_findings(frame, search_text="", selected_severities=None):
    """Filter findings by severity and text across identifiers and explanation."""
    if frame.empty:
        return frame.copy()
    filtered = frame.copy()
    if selected_severities is not None:
        selected = {str(value).upper() for value in selected_severities}
        filtered = filtered[filtered["static_severity"].isin(selected)]
    term = str(search_text or "").strip().casefold()
    if term:
        searchable = [
            column
            for column in ("resource_id", "rule_id", "scoring_method", "risk_reason")
            if column in filtered
        ]
        combined = filtered[searchable].fillna("").astype(str).agg(" ".join, axis=1)
        filtered = filtered[combined.str.casefold().str.contains(term, regex=False)]
    return filtered


def summarize_findings(frame, graph):
    """Return accessible top-line dashboard metrics from current artifacts."""
    severities = frame.get("static_severity", pd.Series(dtype=str)).astype(str).str.upper()
    methods = frame.get("scoring_method", pd.Series(dtype=str)).fillna("").astype(str)
    admin_paths = methods.str.contains(
        "admin_reachability|principal_escalation", case=False, regex=True
    ).sum()
    return {
        "findings": len(frame),
        "urgent": int(severities.isin({"CRITICAL", "HIGH"}).sum()),
        "admin_paths": int(admin_paths),
        "graph_size": f"{graph.number_of_nodes()} / {graph.number_of_edges()}",
    }


def short_label(node_id, attrs, max_length=32):
    """Short label for node display with truncation."""
    name = attrs.get("name") or str(node_id).rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    label = str(name)
    return label if len(label) <= max_length else label[:max_length - 1] + "…"


def full_label(node_id, attrs):
    """Full label for tooltip/detail view."""
    name = attrs.get("name") or str(node_id).rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    principal_type = str(attrs.get("principal_type", "")).upper()
    resource_type = str(attrs.get("resource_type", "")).upper()
    is_admin = str(attrs.get("is_admin", "false")).lower() == "true"
    is_public = principal_type in {"ANY", "PUBLIC", "EXTERNAL"}

    # Determine semantic type
    if is_public:
        node_type = "Public / External"
    elif is_admin:
        node_type = "Admin Sink"
    elif resource_type:
        node_type = f"Resource ({resource_type})"
    elif principal_type in {"ROLE", "GROUP"}:
        node_type = f"Principal ({principal_type})"
    else:
        node_type = f"Principal ({principal_type or 'Unknown'})"

    return f"{name} ({node_type})\n{node_id}"


def graph_visual_data(
    graph, selected_path=None, smooth_edges=True, filter_types=None,
    search_term="", edge_filter_types=None
):
    """Build agraph nodes/edges with proper styling for clear graph visualization.

    Preserves node-type semantics (public, admin, resource, role/group, user/service)
    while highlighting selected path nodes with bold border and glow effect.
    """
    path = list(selected_path or [])
    path_nodes = set(path)
    path_edges = set(zip(path, path[1:]))

    # Prepare filters
    filter_types = set(filter_types) if filter_types else None
    edge_filter_types = set(edge_filter_types) if edge_filter_types else None
    search_lower = search_term.strip().lower() if search_term else None

    nodes = []
    for node_id, attrs in graph.nodes(data=True):
        principal_type = str(attrs.get("principal_type", "")).upper()
        resource_type = str(attrs.get("resource_type", "")).upper()
        is_admin = str(attrs.get("is_admin", "false")).lower() == "true"
        is_public = principal_type in {"ANY", "PUBLIC", "EXTERNAL"}
        in_path = node_id in path_nodes

        # Apply type filter
        node_type_key = None
        if is_public:
            node_type_key = "PUBLIC"
        elif is_admin:
            node_type_key = "ADMIN"
        elif resource_type:
            node_type_key = resource_type
        elif principal_type in {"ROLE", "GROUP"}:
            node_type_key = principal_type
        else:
            node_type_key = principal_type or "OTHER"

        if filter_types and node_type_key not in filter_types:
            continue

        # Apply search filter
        label = short_label(node_id, attrs)
        full = full_label(node_id, attrs)
        if search_lower and search_lower not in label.lower() and search_lower not in full.lower():
            continue

        # Determine node styling based on type (preserve semantic colors)
        if is_public:
            color = "#e3a33e"  # Gold for public/external
            shape = "star"
            base_size = 38
            border_color = "#b8860b"
        elif is_admin:
            color = "#c54253"  # Red for admin
            shape = "hexagon"
            base_size = 36
            border_color = "#8b0000"
        elif resource_type:
            color = "#4a90d9"  # Blue for resources
            shape = "box"
            base_size = 28
            border_color = "#2c5aa0"
        elif principal_type in {"ROLE", "GROUP"}:
            color = "#6b7c93"  # Slate for roles/groups
            shape = "diamond"
            base_size = 26
            border_color = "#4a5a6e"
        else:
            color = "#8b9bb3"  # Light slate for users/services
            shape = "dot"
            base_size = 24
            border_color = "#6a7a8e"

        # Path highlighting: keep semantic color, add bold border and size boost
        size = base_size + (6 if in_path else 0)
        border_width = 5 if in_path else 2

        # For path nodes, use a distinctive border color (bright blue)
        effective_border_color = "#1e90ff" if in_path else border_color

        title = full_label(node_id, attrs)

        nodes.append(
            Node(
                id=node_id,
                label=label,
                title=title,
                size=size,
                shape=shape,
                color=color,
                font={
                    "color": "#183047",
                    "size": 13,
                    "face": "Arial",
                    "bold": in_path,
                    "strokeWidth": 2 if in_path else 0,
                    "strokeColor": "#ffffff"
                },
                borderWidth=border_width,
                borderWidthSelected=5,
                borderColor=effective_border_color,
                chosen=True if in_path else False,
            )
        )

    edges = []
    node_ids = {n.id for n in nodes}
    for source, target, attrs in graph.edges(data=True):
        # Skip edges where either endpoint is filtered out
        if source not in node_ids or target not in node_ids:
            continue

        # Apply edge type filter
        edge_type = str(attrs.get("edge_type", "RELATION"))
        if edge_filter_types and edge_type not in edge_filter_types:
            continue

        in_path = (source, target) in path_edges
        action = str(attrs.get("action", ""))

        # Color and style based on edge type - stronger visual semantics
        if edge_type == "CAN_ESCALATE":
            base_color = "#c54253"  # Red for escalation
            dash = False
            base_width = 2.5
        elif edge_type == "CAN_ASSUME":
            base_color = "#4169e1"  # Blue for assume role
            dash = [8, 4]
            base_width = 2
        elif edge_type == "ACTS_AS":
            base_color = "#45c8b0"  # Teal for acts as
            dash = [5, 5]
            base_width = 2
        else:
            base_color = "#9aa8b8"
            dash = False
            base_width = 1.5

        # Path edges: bright blue, thick, solid
        color = "#1e90ff" if in_path else base_color
        width = 5 if in_path else base_width
        path_dash = False if in_path else dash

        # Show edge label for path edges, or all edges if enabled
        show_label = in_path or st.session_state.get("graph_edge_labels", False)
        edge_label = action if show_label else ""

        edges.append(
            Edge(
                source=source,
                target=target,
                label=edge_label,
                title=f"{edge_type} · {action}".strip(" ·"),
                color=color,
                width=width,
                arrows="to",
                arrowStrikethrough=False,
                font={
                    "color": "#1a2a3a",
                    "size": 12,
                    "align": "middle",
                    "bold": in_path,
                    "strokeWidth": 3 if in_path else 0,
                    "strokeColor": "#ffffff"
                },
                dashes=path_dash,
                smooth=(
                    {"type": "continuous", "roundness": 0.3}
                    if smooth_edges
                    else {"type": "straightCross", "roundness": 0}
                ),
            )
        )
    return nodes, edges


def get_node_types(graph):
    """Return sorted list of unique node types present in the graph."""
    types = set()
    for _, attrs in graph.nodes(data=True):
        principal_type = str(attrs.get("principal_type", "")).upper()
        resource_type = str(attrs.get("resource_type", "")).upper()
        is_admin = str(attrs.get("is_admin", "false")).lower() == "true"
        is_public = principal_type in {"ANY", "PUBLIC", "EXTERNAL"}

        if is_public:
            types.add("PUBLIC")
        elif is_admin:
            types.add("ADMIN")
        elif resource_type:
            types.add(resource_type)
        elif principal_type in {"ROLE", "GROUP"}:
            types.add(principal_type)
        else:
            types.add(principal_type or "OTHER")
    return sorted(types)


def get_edge_types(graph):
    """Return sorted list of unique edge types present in the graph."""
    types = set()
    for _, _, attrs in graph.edges(data=True):
        edge_type = str(attrs.get("edge_type", "RELATION"))
        types.add(edge_type)
    return sorted(types)


# ============================================================
# Phase 5: Advanced Graph Functionality
# ============================================================

def export_graph_json(graph):
    """Export graph as JSON with nodes and edges."""
    data = {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "nodes": [],
        "edges": [],
    }
    for node_id, attrs in graph.nodes(data=True):
        data["nodes"].append({
            "id": node_id,
            "name": attrs.get("name", ""),
            "principal_type": attrs.get("principal_type", ""),
            "resource_type": attrs.get("resource_type", ""),
            "node_type": attrs.get("node_type", ""),
            "is_admin": attrs.get("is_admin", "false"),
        })
    for source, target, attrs in graph.edges(data=True):
        data["edges"].append({
            "source": source,
            "target": target,
            "edge_type": attrs.get("edge_type", "RELATION"),
            "action": attrs.get("action", ""),
        })
    return json.dumps(data, indent=2)


def export_graph_graphml(graph):
    """Export graph as GraphML string."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.graphml', delete=False) as f:
        nx.write_graphml(graph, f.name)
        with open(f.name, 'r') as gf:
            content = gf.read()
        os.unlink(f.name)
    return content


def export_graph_png_placeholder():
    """Return a placeholder for PNG export (requires cytoscape.js or similar).
    In a full implementation, this would render the graph to PNG via a headless browser.
    """
    return None


def get_path_subgraph(graph, path):
    """Extract subgraph for a specific path (path isolation mode)."""
    if not path or len(path) < 2:
        return nx.DiGraph()
    subgraph = nx.DiGraph()
    path_edges = list(zip(path, path[1:]))
    for source, target in path_edges:
        if graph.has_edge(source, target):
            # Copy node attributes
            for node in (source, target):
                if not subgraph.has_node(node):
                    subgraph.add_node(node, **graph.nodes[node])
            # Copy edge attributes
            subgraph.add_edge(source, target, **graph.edges[source, target])
    return subgraph


def get_k_hop_subgraph(graph, center_nodes, k=2):
    """Get k-hop neighborhood around center nodes for focused view."""
    if not center_nodes:
        return nx.DiGraph()
    center_set = set(center_nodes)
    visited = set(center_set)
    current = set(center_set)
    for _ in range(k):
        next_nodes = set()
        for node in current:
            if node in graph:
                next_nodes.update(graph.predecessors(node))
                next_nodes.update(graph.successors(node))
        visited.update(next_nodes)
        current = next_nodes
    return graph.subgraph(visited).copy()


def graph_diff(graph1, graph2):
    """Compare two graphs and return added/removed nodes and edges."""
    nodes1 = set(graph1.nodes())
    nodes2 = set(graph2.nodes())
    edges1 = set(graph1.edges())
    edges2 = set(graph2.edges())
    return {
        "added_nodes": nodes2 - nodes1,
        "removed_nodes": nodes1 - nodes2,
        "added_edges": edges2 - edges1,
        "removed_edges": edges1 - edges2,
        "node_attr_changes": {
            n: dict(graph2.nodes[n]) for n in nodes1 & nodes2
            if dict(graph1.nodes[n]) != dict(graph2.nodes[n])
        },
    }


def get_query_params():
    """Parse URL query parameters for bookmarkable state."""
    try:
        return st.query_params
    except Exception:
        return {}


def set_query_params(params):
    """Set URL query parameters for bookmarkable state."""
    try:
        st.query_params.clear()
        st.query_params.update(params)
    except Exception:
        pass


def build_bookmark_url(graph, selected_path=None, filter_types=None, search_term="",
                       layout_mode="physics", hierarchical=False):
    """Build a bookmarkable URL with current graph state."""
    params = {}
    if selected_path:
        params["path"] = ",".join(selected_path)
    if filter_types:
        params["types"] = ",".join(filter_types)
    if search_term:
        params["search"] = search_term
    params["layout"] = "hierarchical" if hierarchical else "physics"
    # Note: Full graph state bookmarking would need a compressed graph ID
    return params


def apply_bookmark_state(graph, params):
    """Apply bookmark state from URL parameters."""
    state = {}
    if "path" in params:
        path_nodes = params["path"].split(",") if params["path"] else []
        state["selected_path"] = [n for n in path_nodes if n in graph]
    if "types" in params:
        state["graph_type_filter"] = params["types"].split(",") if params["types"] else []
    if "search" in params:
        state["graph_search"] = params["search"]
    if "layout" in params:
        state["graph_hierarchical"] = params["layout"] == "hierarchical"
    return state


def inject_keyboard_shortcuts():
    """Inject JavaScript for keyboard shortcuts."""
    st.markdown("""
    <script>
    document.addEventListener('keydown', function(e) {
        // Only trigger shortcuts when not in an input field
        const active = document.activeElement;
        const isInput = active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.isContentEditable;
        if (isInput) return;

        const shortcuts = {
            'f': () => document.querySelector('input[placeholder*="Search"]')?.focus(),
            'r': () => document.querySelector('button[key="graph_reset_layout"]')?.click(),
            't': () => document.querySelector('input[type="checkbox"][key="graph_show_text_view"]')?.click(),
            'h': () => document.querySelector('button[key="graph_fit_screen"]')?.click(),
            'p': () => document.querySelector('button[key="graph_focus_path"]')?.click(),
            'Escape': () => {
                const resetBtn = document.querySelector('button[key="graph_reset_layout"]');
                if (resetBtn) resetBtn.click();
            },
            '+': () => document.querySelector('button[key="graph_zoom_in"]')?.click(),
            '=': () => document.querySelector('button[key="graph_zoom_in"]')?.click(),
            '-': () => document.querySelector('button[key="graph_zoom_out"]')?.click(),
        };

        const handler = shortcuts[e.key];
        if (handler) {
            e.preventDefault();
            handler();
        }
    });
    </script>
    """, unsafe_allow_html=True)


def inject_graph_controls_js():
    """Inject JavaScript for graph canvas controls (fit, zoom, pan)."""
    st.markdown("""
    <script>
    // Store network reference globally for access from buttons
    window.cspmGraphNetwork = null;
    window.cspmGraphContainer = null;

    // Function to find and store the vis-network instance
    function initGraphControls() {
        // Find the canvas element
        const canvas = document.querySelector('.graph-canvas-wrapper canvas');
        if (canvas) {
            // The network is attached to the canvas via vis-network
            // We'll try to access it through the vis-network API
            window.cspmGraphContainer = canvas.parentElement;
        }

        // Also try to find network via vis-network's global registry
        if (window.visNetworkInstances && window.visNetworkInstances.length > 0) {
            window.cspmGraphNetwork = window.visNetworkInstances[0];
        }
    }

    // Fit to screen
    window.fitGraphToScreen = function() {
        initGraphControls();
        if (window.cspmGraphNetwork && typeof window.cspmGraphNetwork.fit === 'function') {
            window.cspmGraphNetwork.fit({
                animation: { duration: 500, easingFunction: 'easeInOutQuad' }
            });
            return true;
        }
        // Fallback: try to trigger via canvas
        const canvas = document.querySelector('.graph-canvas-wrapper canvas');
        if (canvas && canvas.network) {
            canvas.network.fit({ animation: { duration: 500 } });
            return true;
        }
        return false;
    };

    // Zoom in
    window.zoomGraphIn = function() {
        initGraphControls();
        if (window.cspmGraphNetwork && typeof window.cspmGraphNetwork.moveTo === 'function') {
            const scale = window.cspmGraphNetwork.getScale();
            window.cspmGraphNetwork.moveTo({
                scale: Math.min(scale * 1.3, 3),
                animation: { duration: 300, easingFunction: 'easeOutQuad' }
            });
            return true;
        }
        return false;
    };

    // Zoom out
    window.zoomGraphOut = function() {
        initGraphControls();
        if (window.cspmGraphNetwork && typeof window.cspmGraphNetwork.moveTo === 'function') {
            const scale = window.cspmGraphNetwork.getScale();
            window.cspmGraphNetwork.moveTo({
                scale: Math.max(scale / 1.3, 0.1),
                animation: { duration: 300, easingFunction: 'easeOutQuad' }
            });
            return true;
        }
        return false;
    };

    // Reset view
    window.resetGraphView = function() {
        initGraphControls();
        if (window.cspmGraphNetwork && typeof window.cspmGraphNetwork.moveTo === 'function') {
            window.cspmGraphNetwork.moveTo({
                position: { x: 0, y: 0 },
                scale: 1,
                animation: { duration: 500, easingFunction: 'easeInOutQuad' }
            });
            return true;
        }
        // Also try fit as fallback
        return window.fitGraphToScreen();
    };

    // Focus on selected path nodes
    window.focusGraphPath = function() {
        initGraphControls();
        if (window.cspmGraphNetwork && typeof window.cspmGraphNetwork.focus === 'function') {
            // Find nodes with bold border (path nodes)
            const nodes = window.cspmGraphNetwork.body.data.nodes.get();
            const pathNodeIds = [];
            for (const [id, node] of Object.entries(nodes)) {
                if (node.borderWidth && node.borderWidth >= 3) {
                    pathNodeIds.push(id);
                }
            }
            if (pathNodeIds.length > 0) {
                window.cspmGraphNetwork.focus(pathNodeIds, {
                    animation: { duration: 500, easingFunction: 'easeInOutQuad' },
                    scale: Math.min(window.cspmGraphNetwork.getScale() * 1.2, 1.5)
                });
                return true;
            }
        }
        return window.fitGraphToScreen();
    };

    // Auto-fit on load
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(initGraphControls, 500);
        setTimeout(window.fitGraphToScreen, 1000);
    });

    // Also try when Streamlit components render
    const observer = new MutationObserver(function(mutations) {
        for (const mutation of mutations) {
            if (mutation.addedNodes.length > 0) {
                for (const node of mutation.addedNodes) {
                    if (
    node.nodeType === 1 &&
    node.querySelector &&
    node.querySelector('.graph-canvas-wrapper canvas')
) {
                        setTimeout(initGraphControls, 300);
                        setTimeout(window.fitGraphToScreen, 800);
                        break;
                    }
                }
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    </script>
    """, unsafe_allow_html=True)


def render_graph_performance_info(graph):
    """Show performance info for large graphs."""
    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    if node_count > 500 or edge_count > 1000:
        st.warning(
            f"⚠️ Large graph detected ({node_count} nodes, {edge_count} edges). "
            "Consider using type filters or path isolation for better performance."
        )
    elif node_count > 200:
        st.info(
            f"ℹ️ Graph has {node_count} nodes and {edge_count} edges. "
            "Layout may take a moment to stabilize."
        )


def render_graph_text_view(graph, selected_path=None):
    """Render an accessible text-based relationship view of the graph."""
    path = list(selected_path or [])
    path_nodes = set(path)
    path_edges = set(zip(path, path[1:]))

    st.markdown("**Graph Structure (Text View)**")

    # Group by node type
    nodes_by_type = {}
    for node_id, attrs in graph.nodes(data=True):
        principal_type = str(attrs.get("principal_type", "")).upper()
        resource_type = str(attrs.get("resource_type", "")).upper()
        is_admin = str(attrs.get("is_admin", "false")).lower() == "true"
        is_public = principal_type in {"ANY", "PUBLIC", "EXTERNAL"}

        if is_public:
            node_type = "Public / External"
        elif is_admin:
            node_type = "Admin Sink"
        elif resource_type:
            node_type = f"Resource ({resource_type})"
        elif principal_type in {"ROLE", "GROUP"}:
            node_type = f"Principal ({principal_type})"
        else:
            node_type = f"Principal ({principal_type or 'Unknown'})"

        if node_type not in nodes_by_type:
            nodes_by_type[node_type] = []
        nodes_by_type[node_type].append((node_id, attrs))

    # Render nodes by type
    for node_type, nodes in sorted(nodes_by_type.items()):
        with st.expander(f"{node_type} ({len(nodes)})", expanded=False):
            for node_id, attrs in sorted(nodes, key=lambda x: x[1].get("name", x[0])):
                name = attrs.get("name", str(node_id).rsplit("/", 1)[-1].rsplit(":", 1)[-1])
                in_path_marker = " 🔵" if node_id in path_nodes else ""
                st.markdown(f"- **{name}** (`{node_id}`){in_path_marker}")

    # Render edges
    if graph.edges():
        st.markdown("---")
        st.markdown("**Relationships**")
        edges_by_type = {}
        for source, target, attrs in graph.edges(data=True):
            edge_type = str(attrs.get("edge_type", "RELATION"))
            action = str(attrs.get("action", ""))
            if edge_type not in edges_by_type:
                edges_by_type[edge_type] = []
            edges_by_type[edge_type].append((source, target, action))

        for edge_type, edges in sorted(edges_by_type.items()):
            with st.expander(f"{edge_type} ({len(edges)})", expanded=False):
                for source, target, action in sorted(edges, key=lambda x: (x[0], x[1])):
                    in_path_marker = " 🔵" if (source, target) in path_edges else ""
                    src_name = graph.nodes[source].get("name", source) if source in graph.nodes else source
                    tgt_name = graph.nodes[target].get("name", target) if target in graph.nodes else target
                    st.markdown(f"- **{src_name}** → **{tgt_name}** · `{action}`{in_path_marker}")


def path_edges_for(row):
    edges = row.get("attack_path_edges")
    return edges if isinstance(edges, list) else []


def render_score_panel(row):
    """Render comprehensive finding intelligence panel with evidence, paths, and remediation."""
    severity = str(row.get("static_severity", "INFO")).upper()
    pill_class = {
        "CRITICAL": "pill-critical",
        "HIGH": "pill-high",
        "MEDIUM": "pill-medium",
        "LOW": "pill-low",
        "INFO": "pill-info",
    }.get(severity, "pill-info")
    resource = str(row.get("resource_id", "Unknown resource"))
    rule = str(row.get("rule_id", "Unknown rule"))
    score = float(row.get("risk_score", 0.0) or 0.0)
    method = str(row.get("scoring_method", "severity_baseline"))
    reason = row.get("risk_reason") or "No scoring explanation is available in this saved result."
    evidence = row.get("evidence", {})
    attack_path = row.get("attack_path", [])
    attack_path_edges = row.get("attack_path_edges", [])

    # Helper: truncate long resource IDs with tooltip
    def _render_resource_id(res_id):
        display = res_id if len(res_id) <= 80 else res_id[:77] + "…"
        escaped = html.escape(res_id)
        style = 'font-size:0.85rem; color:var(--color-text-muted); cursor:help;'
        return f'<code title="{escaped}" style="{style}">{html.escape(display)}</code>'

    # ============================================================
    # SECTION 1: Overview & Risk Score (Always Expanded)
    # ============================================================
    st.markdown(
        f'<span class="pill {pill_class}">{severity}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"### {rule}")

    # Resource ID with copy button
    resource_col, copy_col = st.columns([0.85, 0.15])
    with resource_col:
        st.markdown(_render_resource_id(resource), unsafe_allow_html=True)
    with copy_col:
        if st.button(
            "📋",
            key=f"copy_resource_{resource[:20]}",
            help="Copy resource ARN/ID",
        ):
            st.write(
                f'<script>navigator.clipboard.writeText("{html.escape(resource)}")</script>',
                unsafe_allow_html=True,
            )
            st.toast("Copied!", icon="✅")

    # Risk Score metric
    st.metric(
        "Prototype risk score",
        f"{score:.2f}",
        help="Heuristic prioritization score (0–1), not a calibrated probability.",
    )

    # Method badge
    method_display = method.replace("_", " ").title()
    st.markdown(
        f'<span class="pill pill-info" style="font-size:0.7rem; margin-top:0.25rem;">Method: {method_display}</span>',
        unsafe_allow_html=True,
    )

    # Quick evidence type indicator
    if method == "severity_baseline":
        st.caption("ℹ️ Static severity baseline only — no modeled attack path to admin found.")
    elif "public_admin" in method:
        st.caption("🔴 **Strongest evidence**: Public entry + modeled path to admin sink.")
    elif "principal_escalation" in method:
        st.caption("🟡 **Moderate evidence**: Modeled escalation path to admin (no public entry).")
    elif "public_reachability" in method:
        st.caption("🟠 **Entry evidence**: Public reachability (no admin escalation path).")

    st.divider()

    # ============================================================
    # SECTION 2: Configuration Evidence (Collapsible)
    # ============================================================
    with st.expander("📋 Configuration Evidence", expanded=False):
        if evidence and isinstance(evidence, dict) and evidence:
            with st.expander("View raw evidence JSON", expanded=False):
                st.json(evidence)

            # Present key evidence fields in readable format
            for key, value in evidence.items():
                if isinstance(value, dict):
                    with st.expander(f"📄 {key.replace('_', ' ').title()}", expanded=True):
                        st.json(value)
                elif isinstance(value, list):
                    with st.expander(f"📄 {key.replace('_', ' ').title()} ({len(value)} items)", expanded=False):
                        for i, item in enumerate(value):
                            st.json(item)
                else:
                    st.caption(f"**{key.replace('_', ' ').title()}:** {value}")
        else:
            st.caption("No structured evidence available for this finding.")

    # ============================================================
    # SECTION 3: Why This Score (Collapsible)
    # ============================================================
    with st.expander("🎯 Why This Score", expanded=True):
        st.write(reason)

        # Distinguish evidence types with more detail
        if method == "severity_baseline":
            st.caption(
                "ℹ️ This finding uses the **static severity baseline** only. "
                "No modeled attack path to an administrative principal was found in the IAM graph."
            )
        elif "public_admin" in method:
            st.caption(
                "🔴 **Strongest evidence**: A public/external principal can reach this resource "
                "**and** there is a modeled escalation path to an administrative principal. "
                "This represents a potential external attack route."
            )
        elif "principal_escalation" in method:
            st.caption(
                "🟡 **Moderate evidence**: The finding target has a modeled escalation path to an "
                "administrative principal, but **external entry is not established**. "
                "An attacker would need an initial foothold first."
            )
        elif "public_reachability" in method:
            st.caption(
                "🟠 **Entry evidence**: A public/external principal can reach this resource, "
                "but no escalation path to admin was modeled."
            )

    # ============================================================
    # SECTION 4: Modeled Attack Path (Collapsible, expanded if path exists)
    # ============================================================
    has_path = (
        bool(attack_path_edges and isinstance(attack_path_edges, list))
        or bool(isinstance(attack_path, list) and attack_path)
    )
    with st.expander("🔗 Modeled Attack Path", expanded=has_path):

        def _render_path_edges(edges_list):
            if not edges_list:
                return
            for edge in edges_list:
                action_value = edge.get("action") or ""
                action = f" · {html.escape(str(action_value))}" if action_value else ""
                edge_type = html.escape(str(edge.get("edge_type", "RELATION")))
                source = html.escape(str(edge.get("source", "?")))
                target = html.escape(str(edge.get("target", "?")))

                # Edge type badge
                edge_type_class = {
                    "CAN_ESCALATE": "pill-critical",
                    "CAN_ASSUME": "pill-high",
                    "ACTS_AS": "pill-medium",
                }.get(edge_type, "pill-info")

                st.markdown(
                    f'<div class="path-step">'
                    f'<small><span class="pill {edge_type_class}">{edge_type}</span>{action}</small>'
                    f'<code>{source}</code> → <code>{target}</code>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        if attack_path_edges and isinstance(attack_path_edges, list):
            _render_path_edges(attack_path_edges)

            # Show path summary
            st.caption(f"Path length: {len(attack_path_edges)} hop(s) · "
                       f"Entry: {html.escape(str(attack_path_edges[0].get('source', '?')))} · "
                       f"Sink: {html.escape(str(attack_path_edges[-1].get('target', '?')))}")
        elif isinstance(attack_path, list) and attack_path:
            st.code(" → ".join(str(node) for node in attack_path), language=None)
        else:
            st.info(
                "No modeled attack path is attached to this finding. "
                "The risk score is based on static severity and available evidence only."
            )

    # ============================================================
    # SECTION 5: Suggested Remediation (Collapsible)
    # ============================================================
    with st.expander("🛡️ Suggested Remediation", expanded=True):

        remediation_map = {
            "S3_PUBLIC_READ": (
                "Remove public read ACL/bucket policy. "
                "Enable block public access settings."
            ),
            "S3_BUCKET_WILDCARD_POLICY": (
                "Restrict bucket policy to specific principals. "
                "Avoid wildcard (*) principals."
            ),
            "S3_VERSIONING_DISABLED": (
                "Enable versioning to protect against accidental "
                "deletion and ransomware."
            ),
            "S3_NO_ENCRYPTION": "Enable default bucket encryption (SSE-S3 or SSE-KMS).",
            "IAM_ROLE_ASSUMABLE_BY_ANYONE": (
                "Restrict trust policy to specific accounts/principals. "
                "Remove wildcard (*) principal."
            ),
            "IAM_ROLE_PASSROLE_LAMBDA_CREATE": (
                "Scope PassRole permissions to specific roles. "
                "Avoid wildcard resource."
            ),
            "IAM_POLICY_WILDCARD": (
                "Replace wildcard (*:*) policies with "
                "least-privilege permissions."
            ),
            "IAM_ROLE_ADMIN_DIRECT": (
                "Remove AdministratorAccess unless strictly required. "
                "Use scoped policies."
            ),
            "IAM_USER_ACCESS_KEY_NO_MFA": (
                "Enforce MFA for all IAM users with access keys. "
                "Rotate keys regularly."
            ),
            "IAM_USER_NO_MFA": (
                "Enable MFA for console access. "
                "Prefer IAM Identity Center (SSO)."
            ),
            "LAMBDA_RUNS_AS_ADMIN": (
                "Create least-privilege execution role. "
                "Remove AdministratorAccess from Lambda role."
            ),
            "LAMBDA_OUTDATED_RUNTIME": (
                "Upgrade to supported runtime "
                "(Python 3.11+, Node.js 18+)."
            ),
            "DYNAMODB_NO_ENCRYPTION": "Enable encryption at rest with AWS KMS.",
            "KMS_KEY_PERMISSIVE_POLICY": (
                "Restrict key policy to specific principals. "
                "Remove wildcard (*) principal."
            ),
            "KMS_KEY_ROTATION_DISABLED": "Enable automatic key rotation.",
            "SG_SSH_OPEN_WORLD": (
                "Restrict SSH (port 22) to bastion hosts or "
                "VPN CIDR ranges only."
            ),
            "SG_WEB_OPEN_WORLD": (
                "Consider WAF/ALB for HTTP/HTTPS. "
                "Restrict if internal only."
            ),
            "SG_OPEN_WORLD": (
                "Restrict security group ingress to "
                "required CIDR ranges."
            ),
            "SG_ALL_EGRESS": "Restrict egress to required destinations if possible.",
            "DEFAULT_SG_OPEN": (
                "Remove inbound rules from default security group. "
                "Create specific SGs."
            ),
            "RDS_PUBLIC_NO_ENCRYPTION": (
                "Disable public accessibility. "
                "Enable storage encryption."
            ),
            "CLOUDTRAIL_LOGGING_DISABLED": "Enable CloudTrail logging in all regions.",
            "SECRETS_MANAGER_PLAINTEXT": "Enable encryption with KMS key for all secrets.",
            "PARAMETER_STORE_PLAINTEXT": "Use SecureString type with KMS encryption for sensitive parameters.",
        }

        remediation = remediation_map.get(
            rule,
            "Review the finding and apply least-privilege principles. "
            "Consult AWS security best practices for this resource type."
        )

        st.markdown(
            f'<div style="background:var(--color-teal-bg); border:1px solid '
            f'var(--color-teal); border-radius:var(--radius-md); '
            f'padding:var(--space-3); margin-top:var(--space-2);">'
            f'<strong>Recommended action:</strong> {remediation}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ============================================================
    # SECTION 6: Raw JSON Evidence (Collapsible, at bottom)
    # ============================================================
    with st.expander("📦 Raw JSON Evidence", expanded=False):
        st.json(row)

    # Related findings hint
    if "scoring_method" in row and row["scoring_method"] != "severity_baseline":
        st.caption(
            "💡 This finding has modeled graph evidence. "
            "Use the **Attack Graph** view to explore the full attack path visually."
        )


def go_to_graph():
    st.session_state["workspace_view"] = "Attack Graph"


def _reset_all_filters():
    """Reset all filter state to defaults."""
    st.session_state["selected_severities"] = SEVERITIES.copy()
    st.session_state["severity_multiselect"] = SEVERITIES.copy()
    st.session_state["findings_search"] = ""
    st.session_state["findings_sort"] = "Risk score (desc)"


def render_findings(frame):
    st.markdown('<div class="section-title">Findings</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-copy">Search, filter, and sort findings to prioritize '
        'investigation. Select a row to view detailed evidence and modeled '
        'attack paths.</p>',
        unsafe_allow_html=True,
    )

    # Initialize session state
    if "selected_severities" not in st.session_state:
        st.session_state["selected_severities"] = SEVERITIES.copy()
    if "findings_sort" not in st.session_state:
        st.session_state["findings_sort"] = "Risk score (desc)"

    # Callback for multiselect
    def _on_severity_change():
        st.session_state["selected_severities"] = st.session_state["severity_multiselect"]

    # Callback for sort change
    def _on_sort_change():
        st.session_state["findings_sort"] = st.session_state["findings_sort_select"]

    # Filter controls row 1: Search + Severity + All/None (aligned with flex)
    st.markdown('<div class="filter-row">', unsafe_allow_html=True)
    # Use a single row with sub-columns that align properly
    search_col, severity_col, all_col = st.columns([3, 2, 1], gap="small")

    with search_col:
        search_text = st.text_input(
            "Search findings",
            placeholder="Search resource, rule, or scoring rationale…",
            label_visibility="collapsed",
            key="findings_search",
        )

    with severity_col:
        selected_severities = st.multiselect(
            "Severity",
            SEVERITIES,
            default=st.session_state["selected_severities"],
            placeholder="Filter by severity",
            key="severity_multiselect",
            on_change=_on_severity_change,
        )

    with all_col:
        def _toggle_all_severities():
            current = st.session_state.get("selected_severities", [])
            if len(current) < len(SEVERITIES):
                st.session_state["selected_severities"] = SEVERITIES.copy()
            else:
                st.session_state["selected_severities"] = []
            st.session_state["severity_multiselect"] = st.session_state["selected_severities"]

        st.button(
            "✓ All" if len(st.session_state["selected_severities"]) < len(SEVERITIES) else "✗ None",
            key="toggle_all_severities",
            help="Select or deselect all severities",
            use_container_width=True,
            on_click=_toggle_all_severities,
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # Filter controls row 2: Sort + Reset + Stats + Active Filters
    sort_col, reset_col, stats_col = st.columns([1.5, 1, 2.5], gap="medium")
    with sort_col:
        sort_options = [
            "Risk score (desc)",
            "Risk score (asc)",
            "Severity (critical first)",
            "Severity (low first)",
            "Resource (A-Z)",
            "Finding (A-Z)",
        ]
        st.selectbox(
            "Sort by",
            sort_options,
            index=sort_options.index(st.session_state["findings_sort"])
            if st.session_state["findings_sort"] in sort_options
            else 0,
            key="findings_sort_select",
            on_change=_on_sort_change,
            label_visibility="collapsed",
        )

    with reset_col:
        st.button(
            "🔄 Reset filters",
            key="reset_filters",
            help="Clear search, restore all severities, reset sort",
            use_container_width=True,
            on_click=_reset_all_filters,
        )

    with stats_col:
        selected_severities = st.session_state["selected_severities"]
        total = len(frame)
        # Active filter indicator
        active_filters = []
        if search_text:
            active_filters.append(f"Search: \"{search_text}\"")
        if len(selected_severities) < len(SEVERITIES):
            active_filters.append(f"Severity: {', '.join(selected_severities)}")
        if active_filters:
            badge_html = "".join(
                f"<span class='pill pill-info' style=\"font-size:0.7rem;\">"
                f"{html.escape(f)}</span>"
                for f in active_filters
            )
            st.markdown(
                f'<div style="display:flex; gap:0.5rem; align-items:center; '
                f'flex-wrap:wrap; margin-bottom:0.5rem;">'
                f'<span class="filter-badge">Active filters: {len(active_filters)}</span>'
                f'{badge_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
        # Quick severity distribution for visible (unfiltered) data
        sev_counts = frame["static_severity"].value_counts()
        sev_parts = []
        for sev in SEVERITIES:
            count = int(sev_counts.get(sev, 0))
            if count:
                sev_parts.append(f'<span class="pill pill-{sev.lower()}">{sev}: {count}</span>')
        st.markdown(
            f'<div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap;">'
            f'Total: <strong>{total}</strong> findings · '
            f'{" · ".join(sev_parts)}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Apply filters
    visible = filter_findings(frame, search_text, selected_severities)

    # Apply sorting
    sort_key = st.session_state["findings_sort"]
    if sort_key == "Risk score (desc)":
        visible = visible.sort_values("risk_score", ascending=False)
    elif sort_key == "Risk score (asc)":
        visible = visible.sort_values("risk_score", ascending=True)
    elif sort_key == "Severity (critical first)":
        sev_order = {s: i for i, s in enumerate(SEVERITIES)}
        visible = visible.copy()
        visible["_sev_rank"] = visible["static_severity"].map(sev_order).fillna(99)
        visible = visible.sort_values(["_sev_rank", "risk_score"], ascending=[True, False]).drop(columns=["_sev_rank"])
    elif sort_key == "Severity (low first)":
        sev_order = {s: i for i, s in enumerate(reversed(SEVERITIES))}
        visible = visible.copy()
        visible["_sev_rank"] = visible["static_severity"].map(sev_order).fillna(99)
        visible = visible.sort_values(["_sev_rank", "risk_score"], ascending=[True, False]).drop(columns=["_sev_rank"])
    elif sort_key == "Resource (A-Z)":
        visible = visible.sort_values("resource_id", ascending=True)
    elif sort_key == "Finding (A-Z)":
        visible = visible.sort_values("rule_id", ascending=True)

    st.caption(f"Showing {len(visible)} of {len(frame)} findings · sorted by {sort_key.lower()}")
    if visible.empty:
        st.info("No findings match those filters. Clear the search or select more severity levels.")
        st.session_state.pop("active_finding", None)
        st.session_state.pop("active_path", None)
        return

    # Selector for active finding
    if st.session_state.get("finding_selector") not in visible.index:
        st.session_state["finding_selector"] = visible.index[0]
    selected_index = st.selectbox(
        "Inspect a finding",
        options=visible.index.tolist(),
        key="finding_selector",
        format_func=lambda index: (
            f"{visible.loc[index, 'risk_score']:.2f} · "
            f"{visible.loc[index, 'static_severity']} · "
            f"{visible.loc[index, 'rule_id']} · "
            f"{visible.loc[index, 'resource_id'][:80]}"
        ),
        label_visibility="collapsed",
    )
    row = visible.loc[selected_index]
    active = row.to_dict()
    st.session_state["active_finding"] = active
    st.session_state["active_path"] = active.get("attack_path") or []

    # Full-width findings table
    display = visible[
        ["resource_id", "rule_id", "static_severity", "risk_score", "scoring_method"]
    ].rename(
        columns={
            "resource_id": "Resource",
            "rule_id": "Finding",
            "static_severity": "Severity",
            "risk_score": "Risk score",
            "scoring_method": "Scoring method",
        }
    )
    st.dataframe(
        display,
        width="stretch",
        height=480,
        hide_index=True,
        column_config={
            "Resource": st.column_config.TextColumn(
                "Resource",
                width="large",
                help="Resource ARN or identifier. Hover for full value, click to copy.",
            ),
            "Finding": st.column_config.TextColumn(
                "Finding",
                width="medium",
                help="Finding rule identifier",
            ),
            "Severity": st.column_config.TextColumn("Severity", width="small"),
            "Risk score": st.column_config.NumberColumn("Risk score", format="%.2f", width="small"),
            "Scoring method": st.column_config.TextColumn("Scoring method", width="medium"),
        },
    )

    # Detail panel in expander below table
    with st.expander("📋 Finding Details", expanded=True):
        render_score_panel(active)
        st.button(
            "Focus this path in the graph →",
            key="focus_selected_path",
            on_click=go_to_graph,
            type="primary",
            width="stretch",
        )


def render_graph(graph):
    # Handle None graph gracefully
    if graph is None:
        graph = nx.DiGraph()

    # Apply bookmark state from URL if present
    if "graph_bookmark_applied" not in st.session_state:
        params = get_query_params()
        if params:
            bookmark_state = apply_bookmark_state(graph, params)
            for key, value in bookmark_state.items():
                st.session_state[key] = value
        st.session_state["graph_bookmark_applied"] = True

    st.markdown('<div class="section-title">Attack Graph</div>', unsafe_allow_html=True)
    active = st.session_state.get("active_finding")
    selected_path = st.session_state.get("active_path") or []
    if active:
        active_rule = html.escape(str(active.get("rule_id", "selected finding")))
        st.markdown(
            f'<p class="section-copy">Focused on <strong>{active_rule}</strong>. '
            "Highlighted edges are modeled evidence, not proof of exploitability.</p>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p class="section-copy">Explore modeled IAM trust and escalation relationships. '
            'Use the controls to adjust layout. Nodes: ★ Public/External · '
            '◆ Role/Group · ▢ Resource · ● User/Service · ⬡ Admin sink.</p>',
            unsafe_allow_html=True,
        )

    # Initialize session state for graph controls
    if "graph_search" not in st.session_state:
        st.session_state["graph_search"] = ""
    if "graph_type_filter" not in st.session_state:
        st.session_state["graph_type_filter"] = []
    if "graph_show_text_view" not in st.session_state:
        st.session_state["graph_show_text_view"] = False
    if "graph_view_mode" not in st.session_state:
        st.session_state["graph_view_mode"] = "full"  # full, path, khop
    if "graph_khop" not in st.session_state:
        st.session_state["graph_khop"] = 2
    # Default to hierarchical layout for stable, fixed graph
    if "graph_hierarchical" not in st.session_state:
        st.session_state["graph_hierarchical"] = True
    if "graph_physics" not in st.session_state:
        st.session_state["graph_physics"] = False

    # Performance info
    render_graph_performance_info(graph)

    # Inject graph controls JavaScript
    inject_graph_controls_js()

    # ============================================================
    # GRAPH TOOLBAR — Organized in 3 groups: Exploration | Visualization | Export
    # ============================================================
    st.markdown('<div class="graph-toolbar">', unsafe_allow_html=True)

    # Group 1: Exploration
    st.markdown('<div class="graph-toolbar-group">', unsafe_allow_html=True)
    search_col, filter_col, edge_filter_col = st.columns([2.5, 1.5, 1.5], gap="small")
    with search_col:
        st.text_input(
            "Search nodes",
            placeholder="Search by name, ARN, or type…",
            label_visibility="collapsed",
            key="graph_search",
        )
    with filter_col:
        node_types = get_node_types(graph) or []
        st.multiselect(
            "Filter by node type",
            node_types,
            default=st.session_state.get("graph_type_filter", []),
            placeholder="Filter node types…",
            key="graph_type_filter",
            label_visibility="collapsed",
        )
    with edge_filter_col:
        edge_types = get_edge_types(graph)
        st.multiselect(
            "Filter by edge type",
            edge_types,
            default=st.session_state.get("graph_edge_type_filter", []),
            placeholder="Filter edge types…",
            key="graph_edge_type_filter",
            label_visibility="collapsed",
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<span class="graph-toolbar-divider"></span>', unsafe_allow_html=True)

    # Group 2: Visualization
    st.markdown('<div class="graph-toolbar-group">', unsafe_allow_html=True)
    view_col1, view_col2, view_col3 = st.columns([1, 1, 1.5], gap="small")
    with view_col1:
        view_mode = st.radio(
            "View Mode",
            ["Full Graph", "Path Isolation", "K-Hop Neighborhood"],
            index=["full", "path", "khop"].index(st.session_state.get("graph_view_mode", "full")),
            key="graph_view_mode_radio",
            horizontal=True,
            label_visibility="collapsed",
            help="Full: entire graph · Path: selected path only · K-Hop: neighborhood around path nodes",
        )
        st.session_state["graph_view_mode"] = {
            "Full Graph": "full",
            "Path Isolation": "path",
            "K-Hop Neighborhood": "khop",
        }[view_mode]
    with view_col2:
        if st.session_state["graph_view_mode"] == "khop":
            st.session_state["graph_khop"] = st.slider(
                "K hops",
                1, 4,
                st.session_state.get("graph_khop", 2),
                key="graph_khop_slider",
                help="Number of hops from path nodes to include",
                label_visibility="collapsed",
            )
    with view_col3:
        st.checkbox(
            "📋 Text View",
            value=st.session_state.get("graph_show_text_view", False),
            key="graph_show_text_view",
            help="Show accessible text-based relationship view",
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<span class="graph-toolbar-divider"></span>', unsafe_allow_html=True)

    # Group 3: View Controls (Zoom, Fit, Reset, Focus)
    st.markdown('<div class="graph-toolbar-group">', unsafe_allow_html=True)
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4, ctrl_col5 = st.columns([1, 1, 1, 1, 1], gap="small")
    with ctrl_col1:
        if st.button("🔍 Fit", key="graph_fit_screen", use_container_width=True, help="Fit graph to screen (H)"):
            st.session_state["graph_fit_screen_trigger"] = True
    with ctrl_col2:
        if st.button("➕", key="graph_zoom_in", use_container_width=True, help="Zoom in (+/=)"):
            st.session_state["graph_zoom_in_trigger"] = True
    with ctrl_col3:
        if st.button("➖", key="graph_zoom_out", use_container_width=True, help="Zoom out (-)"):
            st.session_state["graph_zoom_out_trigger"] = True
    with ctrl_col4:
        if st.button("↺ Reset", key="graph_reset_layout", use_container_width=True, help="Reset view (R)"):
            st.session_state["graph_reset_layout_trigger"] = True
    with ctrl_col5:
        if selected_path and st.button(
            "🎯 Focus Path",
            key="graph_focus_path",
            use_container_width=True,
            type="primary",
            help="Focus selected path (P)",
        ):
            st.session_state["graph_focus_path_trigger"] = True
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<span class="graph-toolbar-spacer"></span>', unsafe_allow_html=True)

    # Group 4: Export (right-aligned)
    st.markdown('<div class="graph-toolbar-group">', unsafe_allow_html=True)
    exp_col1, exp_col2, exp_col3, exp_col4 = st.columns([1, 1, 1, 1], gap="small")
    with exp_col1:
        graph_json = export_graph_json(graph)
        st.download_button(
            "📥 JSON",
            data=graph_json,
            file_name=f"graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
            help="Download graph as JSON",
        )
    with exp_col2:
        graph_graphml = export_graph_graphml(graph)
        st.download_button(
            "📥 GraphML",
            data=graph_graphml,
            file_name=f"graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.graphml",
            mime="application/xml",
            use_container_width=True,
            help="Download as GraphML",
        )
    with exp_col3:
        csv_nodes = "id,name,principal_type,resource_type,is_admin\n"
        for node_id, attrs in graph.nodes(data=True):
            csv_nodes += f'"{node_id}","{attrs.get("name", "")}","{attrs.get("principal_type", "")}",'
            csv_nodes += f'"{attrs.get("resource_type", "")}","{attrs.get("is_admin", "false")}"\n'
        csv_edges = "source,target,edge_type,action\n"
        for source, target, attrs in graph.edges(data=True):
            csv_edges += f'"{source}","{target}","{attrs.get("edge_type", "RELATION")}",'
            csv_edges += f'"{attrs.get("action", "")}"\n'
        csv_data = f"# Nodes\n{csv_nodes}\n# Edges\n{csv_edges}"
        st.download_button(
            "📥 CSV",
            data=csv_data,
            file_name=f"graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download as CSV",
        )
    with exp_col4:
        # Bookmark button
        bookmark_params = build_bookmark_url(
            graph,
            selected_path=selected_path,
            filter_types=st.session_state.get("graph_type_filter", []),
            search_term=st.session_state.get("graph_search", ""),
            layout_mode="hierarchical" if st.session_state.get("graph_hierarchical", False) else "physics",
            hierarchical=st.session_state.get("graph_hierarchical", False),
        )
        if bookmark_params:
            param_str = urllib.parse.urlencode(bookmark_params)
            st.markdown(
                f'<a href="?{param_str}" target="_blank" style="text-decoration:none;">'
                f'<button class="graph-toolbar-btn" style="width:100%;">🔗 Bookmark</button></a>',
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # Close graph-toolbar

    # Legend (compact, below toolbar)
    st.markdown(
        '<div class="legend">'
        '<span class="legend-item"><i class="legend-dot" style="background:#e3a33e"></i>Public / External</span>'
        '<span class="legend-item"><i class="legend-dot" style="background:#4169e1"></i>Selected Path</span>'
        '<span class="legend-item"><i class="legend-dot" style="background:#c54253"></i>Admin Sink</span>'
        '<span class="legend-item"><i class="legend-dot" style="background:#45c8b0"></i>Acts As</span>'
        '<span class="legend-item"><i class="legend-dot" style="background:#6b7c93"></i>Role / Group</span>'
        '<span class="legend-item"><i class="legend-dot" style="background:#4a90d9"></i>Resource</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Advanced layout controls in expandable section
    with st.expander("⚙️ Layout Controls", expanded=False):
        layout_col1, layout_col2, layout_col3, layout_col4 = st.columns(4)
        with layout_col1:
            st.checkbox(
                "Physics Simulation", value=False, key="graph_physics",
                help="Enable force-directed physics for automatic layout (disables hierarchical)"
            )
        with layout_col2:
            st.checkbox(
                "Hierarchical Layout", value=True, key="graph_hierarchical",
                help="Use top-down hierarchical layout for stable, fixed node positions"
            )
        with layout_col3:
            st.slider(
                "Node Spacing", 150, 500, 300, 20, key="graph_node_spacing",
                help="Horizontal spacing between nodes"
            )
        with layout_col4:
            st.slider(
                "Level Separation", 150, 500, 280, 20, key="graph_level_separation",
                help="Vertical spacing between hierarchy levels"
            )

        layout_col5, layout_col6 = st.columns(2)
        with layout_col5:
            st.checkbox(
                "Curved Edges", value=True, key="graph_smooth",
                help="Smooth curved edges for better readability"
            )
        with layout_col6:
            st.checkbox(
                "Show All Edge Labels", value=False, key="graph_edge_labels",
                help="Display action labels on all edges (can be cluttered)"
            )

    if graph.number_of_nodes() == 0:
        st.warning("The graph is not available yet. Run `make graph` to build it.")
        return

    # Determine which subgraph to display based on view mode
    display_graph = graph
    if st.session_state.get("graph_view_mode") == "path" and selected_path:
        display_graph = get_path_subgraph(graph, selected_path)
    elif st.session_state.get("graph_view_mode") == "khop" and selected_path:
        display_graph = get_k_hop_subgraph(graph, selected_path, st.session_state.get("graph_khop", 2))

    # Show text view if enabled
    if st.session_state.get("graph_show_text_view", False):
        render_graph_text_view(display_graph, selected_path)
        st.divider()

    # Get smooth_edges setting from session state
    smooth_edges = st.session_state.get("graph_smooth", True)
    filter_types = st.session_state.get("graph_type_filter", None)
    edge_filter_types = st.session_state.get("graph_edge_type_filter", None)
    search_term = st.session_state.get("graph_search", "")
    edge_filter_types = st.session_state.get("graph_edge_type_filter", None)
    nodes, edges = graph_visual_data(
        display_graph,
        selected_path,
        smooth_edges=smooth_edges,
        filter_types=filter_types,
        search_term=search_term,
        edge_filter_types=edge_filter_types,
    )

    if not nodes:
        if filter_types or search_term:
            st.info("No nodes match the current filters. Adjust your search or type filters.")
            return
        else:
            st.warning("The graph has no nodes to display.")
            return

    # Configure graph layout
    use_hierarchical = (
        st.session_state.get("graph_hierarchical", True)
        and not st.session_state.get("graph_physics", False)
    )

    # Use dimensions matching the canvas wrapper (600px height)
    # Width will be constrained by container via CSS
    graph_width = 1200
    graph_height = 600

    if use_hierarchical:
        # Hierarchical layout (top-down) - stable, no physics, fixed node positions
        config = Config(
            width=graph_width,
            height=graph_height,
            directed=True,
            physics=False,
            hierarchical=True,
            hierarchicalDirection="UD",
            hierarchicalSortMethod="directed",
            nodeSpacing=st.session_state.get("graph_node_spacing", 300),
            levelSeparation=st.session_state.get("graph_level_separation", 280),
            edgeMinimization=True,
            parentCentralization=True,
            # Interaction options - disable wheel zoom, allow keyboard/buttons zoom
            zoomView=True,
            dragView=True,
            dragNodes=False,  # Nodes fixed in hierarchical layout
            hover=True,
            keyboard=True,
            navigationButtons=True,
            zoomSpeed=0.5,
            wheel={"enabled": False},  # Disable scroll wheel zoom
            layout={
                "hierarchical": {
                    "enabled": True,
                    "direction": "UD",
                    "sortMethod": "directed",
                    "nodeSpacing": st.session_state.get("graph_node_spacing", 300),
                    "levelSeparation": st.session_state.get("graph_level_separation", 280),
                    "treeSpacing": 300,
                    "blockShifting": True,
                    "edgeMinimization": True,
                    "parentCentralization": True,
                }
            },
        )
    else:
        # Force-directed physics layout (fallback) - stable physics with overlap avoidance
        config = Config(
            width=graph_width,
            height=graph_height,
            directed=True,
            physics=True,
            hierarchical=False,
            solver="barnesHut",
            # Interaction options - disable wheel zoom
            zoomView=True,
            dragView=True,
            dragNodes=True,
            hover=True,
            keyboard=True,
            navigationButtons=True,
            zoomSpeed=0.5,
            wheel={"enabled": False},  # Disable scroll wheel zoom
            # Physics for stable layout with good spacing
            nodeSpacing=st.session_state.get("graph_node_spacing", 300),
            levelSeparation=st.session_state.get("graph_level_separation", 280),
            timestep=0.5,
            stabilization={
                "enabled": True,
                "iterations": 500,
                "updateInterval": 50,
                "fit": True,
                "onlyDynamicEdges": False,
            },
        )

    # Render graph in canvas wrapper for proper sizing
    st.markdown('<div class="graph-container">', unsafe_allow_html=True)
    st.markdown('<div class="graph-canvas-wrapper">', unsafe_allow_html=True)
    selected_node = agraph(nodes=nodes, edges=edges, config=config)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Handle graph control triggers via JavaScript
    if st.session_state.get("graph_fit_screen_trigger"):
        st.session_state["graph_fit_screen_trigger"] = False
        st.markdown('<script>window.fitGraphToScreen();</script>', unsafe_allow_html=True)
    if st.session_state.get("graph_zoom_in_trigger"):
        st.session_state["graph_zoom_in_trigger"] = False
        st.markdown('<script>window.zoomGraphIn();</script>', unsafe_allow_html=True)
    if st.session_state.get("graph_zoom_out_trigger"):
        st.session_state["graph_zoom_out_trigger"] = False
        st.markdown('<script>window.zoomGraphOut();</script>', unsafe_allow_html=True)
    if st.session_state.get("graph_reset_layout_trigger"):
        st.session_state["graph_reset_layout_trigger"] = False
        st.markdown('<script>window.resetGraphView();</script>', unsafe_allow_html=True)
    if st.session_state.get("graph_focus_path_trigger"):
        st.session_state["graph_focus_path_trigger"] = False
        st.markdown('<script>window.focusGraphPath();</script>', unsafe_allow_html=True)

    # Node selection detail panel
    node_id = selected_node.get("id") if isinstance(selected_node, dict) else selected_node
    if node_id and node_id in display_graph:
        attrs = display_graph.nodes[node_id]
        with st.container(border=True):
            st.markdown("**Selected Node Details**")
            name = attrs.get("name", str(node_id).rsplit("/", 1)[-1].rsplit(":", 1)[-1])
            principal_type = str(attrs.get("principal_type", "")).upper()
            resource_type = str(attrs.get("resource_type", "")).upper()
            is_admin = str(attrs.get("is_admin", "false")).lower() == "true"
            is_public = principal_type in {"ANY", "PUBLIC", "EXTERNAL"}

            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f"**Name:** {name}")
                st.markdown(f"**ID:** `{node_id}`")
            with col2:
                if is_public:
                    st.markdown('<span class="pill pill-high">★ Public / External</span>', unsafe_allow_html=True)
                elif is_admin:
                    st.markdown('<span class="pill pill-critical">⬡ Admin Sink</span>', unsafe_allow_html=True)
                elif resource_type:
                    st.markdown(
                        f'<span class="pill pill-info">▢ Resource ({resource_type})</span>',
                        unsafe_allow_html=True,
                    )
                elif principal_type in {"ROLE", "GROUP"}:
                    st.markdown(
                        f'<span class="pill pill-medium">◆ {principal_type}</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<span class="pill pill-low">● {principal_type or "Unknown"}</span>',
                        unsafe_allow_html=True,
                    )

            # Show connected edges
            in_edges = list(display_graph.in_edges(node_id, data=True))
            out_edges = list(display_graph.out_edges(node_id, data=True))
            if in_edges or out_edges:
                st.markdown("**Connections**")
                if in_edges:
                    st.markdown("*Incoming:*")
                    for src, _, eattrs in in_edges[:10]:
                        src_name = display_graph.nodes[src].get("name", src) if src in display_graph.nodes else src
                        action = eattrs.get("action", "")
                        etype = eattrs.get("edge_type", "RELATION")
                        st.caption(f"← {src_name} · {etype} · {action}")
                if out_edges:
                    st.markdown("*Outgoing:*")
                    for _, tgt, eattrs in out_edges[:10]:
                        tgt_name = display_graph.nodes[tgt].get("name", tgt) if tgt in display_graph.nodes else tgt
                        action = eattrs.get("action", "")
                        etype = eattrs.get("edge_type", "RELATION")
                        st.caption(f"→ {tgt_name} · {etype} · {action}")

    # Keyboard shortcuts hint
    with st.expander("⌨️ Keyboard Shortcuts", expanded=False):
        st.markdown("""
        | Key | Action |
        |-----|--------|
        | `F` | Focus search box |
        | `R` | Reset layout |
        | `T` | Toggle text view |
        | `H` | Fit to screen |
        | `P` | Focus selected path |
        | `Esc` | Reset layout |
        """)

    if active:
        st.caption(
            f"Focused finding: {active.get('rule_id', 'unknown')} · "
            f"risk score {float(active.get('risk_score', 0.0) or 0.0):.2f} (heuristic)"
        )

    # Inject keyboard shortcuts JavaScript
    inject_keyboard_shortcuts()


def main():
    st.set_page_config(
        page_title="CSPM Risk Console",
        page_icon="☁️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)
    findings_version = file_version(FINDINGS_FILE)
    graph_version = file_version(GRAPH_FILE)
    frame, findings_errors = load_findings(
        str(FINDINGS_FILE), findings_version[0], findings_version[1]
    )
    graph, graph_error = load_graph(str(GRAPH_FILE), graph_version[0], graph_version[1])
    frame = normalize_findings(frame)

    if "workspace_view" not in st.session_state:
        st.session_state["workspace_view"] = "Findings"

    # Handle view switching via query parameter (?view=Findings|Attack Graph)
    query_view = st.query_params.get("view")
    if query_view in ("Findings", "Attack Graph"):
        st.session_state["workspace_view"] = query_view

    # Sidebar with new design system
    with st.sidebar:
        # Brand header with SVG icon
        st.markdown(
            '<div class="sidebar-brand">'
            '<div class="sidebar-brand-icon">'
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"></path>'
            '<line x1="12" y1="2" x2="12" y2="22"></line>'
            '</svg>'
            '</div>'
            '<div class="sidebar-brand-text">'
            '<span class="sidebar-brand-title">CSPM Console</span>'
            '<span class="sidebar-brand-subtitle">Risk Analysis</span>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Navigation using native st.radio (reliable state management)
        # Icons added via CSS background images on labels
        st.radio(
            "Workspace",
            ["Findings", "Attack Graph"],
            key="workspace_view",
            index=0 if st.session_state["workspace_view"] == "Findings" else 1,
            horizontal=True,
            label_visibility="collapsed",
        )

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        # Data source info
        st.markdown(
            f'<div class="sidebar-footer">'
            f'<div class="sidebar-footer-text">'
            f'<strong>Data source:</strong> <code>{DATA_DIR}</code><br/>'
            f'Prototype risk scores are heuristic, not probabilities.'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Refresh button at bottom - high contrast
        if st.button("🔄 Refresh Data", use_container_width=True, key="sidebar_refresh", type="primary"):
            st.cache_data.clear()
            st.rerun()

    st.markdown(
        '<section class="hero">'
        '<p class="hero-kicker">Cloud security posture · Risk analysis</p>'
        '<h1>Risk Command Center</h1>'
        '<p class="hero-copy">Prioritize cloud findings with explainable severity and modeled IAM path evidence.</p>'
        '<span class="hero-tag">LOCAL ANALYSIS WORKSPACE</span>'
        '</section>',
        unsafe_allow_html=True,
    )

    metrics = summarize_findings(frame, graph)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Findings", metrics["findings"])
    metric_cols[1].metric("High / critical", metrics["urgent"])
    metric_cols[2].metric("Modeled admin paths", metrics["admin_paths"])
    metric_cols[3].metric("Graph nodes / edges", metrics["graph_size"])
    st.caption(
        "Risk scores are prototype prioritization signals—not calibrated "
        "probabilities or proof of exploitability."
    )
    st.divider()

    # SVG icons for reuse
    ERROR_ICON = (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"></circle>'
        '<line x1="12" y1="8" x2="12" y2="12"></line>'
        '<line x1="12" y1="16" x2="12.01" y2="16"></line>'
        '</svg>'
    )

    SEARCH_ICON = (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>'
        '</svg>'
    )

    GRAPH_ICON = (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"></circle>'
        '<line x1="2" y1="12" x2="22" y2="12"></line>'
        '<line x1="12" y1="2" x2="12" y2="22"></line>'
        '</svg>'
    )

    # Display errors with better styling
    for error in findings_errors:
        msg = html.escape(error)
        st.markdown(
            f'<div class="error-state">'
            f'<div class="error-state-icon">{ERROR_ICON}</div>'
            f'<div class="error-state-title">Data Warning</div>'
            f'<div class="error-state-message">Skipped malformed findings data — {msg}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    if graph_error:
        msg = html.escape(graph_error)
        st.markdown(
            f'<div class="error-state">'
            f'<div class="error-state-icon">{ERROR_ICON}</div>'
            f'<div class="error-state-title">Graph Load Error</div>'
            f'<div class="error-state-message">Could not read the graph file: {msg}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if st.session_state["workspace_view"] == "Findings":
        if frame.empty:
            st.markdown(
                '<div class="empty-state">'
                f'<div class="empty-state-icon">{SEARCH_ICON}</div>'
                '<div class="empty-state-title">No Findings Available</div>'
                '<div class="empty-state-message">Run <code>make scan graph score</code> '
                'to populate the dashboard with scored findings.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            render_findings(frame)
    else:
        if graph is None or graph.number_of_nodes() == 0:
            st.markdown(
                '<div class="empty-state">'
                f'<div class="empty-state-icon">{GRAPH_ICON}</div>'
                '<div class="empty-state-title">No Attack Graph Available</div>'
                '<div class="empty-state-message">Run <code>make graph</code> '
                'to build the IAM attack graph from scanned resources.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            render_graph(graph)


if __name__ == "__main__":
    main()

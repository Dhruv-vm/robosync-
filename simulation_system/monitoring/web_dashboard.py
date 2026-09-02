"""
Zero-dependency embedded Web Fleet Control Center for Sterlebom Decentralized AMR Fleet.
Serves a professional responsive dark-mode web application on http://localhost:8080.
Handles bidirectional simulation control (Pause, Resume, Speed, Reset, Scenarios, Obstacle Injection).
"""
import http.server
import socketserver
import threading
import json
import urllib.parse
from typing import Optional, Any

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STERLEBOM / ROBOSYNC — Fleet Control Center</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #090d16;
            --bg-card: #111827;
            --bg-card-alt: #1a2234;
            --bg-card-hover: #222d42;
            --border: #243046;
            --border-highlight: #3b82f6;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --text-subtle: #6b7280;
            --accent-blue: #38bdf8;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-emerald: #34d399;
            --accent-yellow: #f59e0b;
            --accent-amber: #fbbf24;
            --accent-red: #ef4444;
            --accent-purple: #a855f7;
            --shadow-card: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-base);
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            padding: 16px 24px 32px 24px;
            line-height: 1.4;
            min-height: 100vh;
        }

        /* Top Header Navbar */
        .top-navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 20px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            margin-bottom: 16px;
            box-shadow: var(--shadow-card);
        }
        .brand-section {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .brand-logo {
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .brand-subtitle {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
            border-left: 1px solid var(--border);
            padding-left: 14px;
        }

        /* Controls Section in Navbar */
        .controls-group {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .btn-ctrl {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            border: 1px solid var(--border);
            background: var(--bg-card-alt);
            color: var(--text-main);
            transition: all 0.15s ease;
        }
        .btn-ctrl:hover {
            background: var(--bg-card-hover);
            border-color: #4b5563;
        }
        .btn-ctrl:active { transform: scale(0.97); }
        .btn-primary { background: #1e3a8a; border-color: #3b82f6; color: #93c5fd; }
        .btn-primary:hover { background: #2563eb; color: #fff; }
        .btn-pause { background: #78350f; border-color: #f59e0b; color: #fde68a; }
        .btn-pause:hover { background: #d97706; color: #fff; }
        .btn-reset { background: #374151; border-color: #6b7280; color: #e5e7eb; }
        .btn-reset:hover { background: #4b5563; color: #fff; }
        .btn-hazard { background: #7f1d1d; border-color: #ef4444; color: #fca5a5; }
        .btn-hazard:hover { background: #dc2626; color: #fff; }

        .speed-selector {
            display: flex;
            background: var(--bg-base);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 2px;
        }
        .speed-pill {
            padding: 4px 9px;
            font-size: 11px;
            font-weight: 700;
            border-radius: 6px;
            cursor: pointer;
            color: var(--text-muted);
            border: none;
            background: transparent;
        }
        .speed-pill.active {
            background: #2563eb;
            color: #fff;
        }

        .scenario-select {
            background: var(--bg-base);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            outline: none;
            cursor: pointer;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }
        .badge-running { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
        .badge-paused { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
        .badge-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
        .badge-running .badge-dot { animation: blink 1.5s infinite; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

        /* ===================================================
           SIH DEMONSTRATION CONTROLS PANEL
           =================================================== */
        .demo-controls-card {
            background: linear-gradient(135deg, rgba(17, 24, 39, 0.95) 0%, rgba(15, 23, 42, 0.95) 100%);
            border: 1px solid rgba(56, 189, 248, 0.35);
            border-radius: 14px;
            padding: 14px 18px;
            margin-bottom: 18px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        }
        .demo-controls-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        .demo-brand-tag {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .demo-title {
            font-size: 14px;
            font-weight: 800;
            color: #fff;
            letter-spacing: 0.5px;
        }
        .demo-badge {
            font-size: 10px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 3px 8px;
            border-radius: 4px;
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-blue);
            border: 1px solid rgba(56, 189, 248, 0.4);
        }
        .demo-status-tag {
            font-size: 11px;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }

        .demo-buttons-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 10px;
        }
        .btn-demo {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: center;
            background: var(--bg-card-alt);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            text-align: left;
            position: relative;
            overflow: hidden;
        }
        .btn-demo:hover {
            background: var(--bg-card-hover);
            border-color: var(--accent-blue);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.15);
        }
        .btn-demo:active {
            transform: translateY(0);
        }
        .btn-demo.active {
            background: rgba(56, 189, 248, 0.12);
            border-color: var(--accent-blue);
            box-shadow: 0 0 16px rgba(56, 189, 248, 0.25);
        }
        .btn-demo.active::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 3px;
            background: var(--accent-blue);
        }
        .btn-demo-title {
            font-size: 12px;
            font-weight: 800;
            color: #fff;
            letter-spacing: 0.3px;
            margin-bottom: 2px;
            text-transform: uppercase;
        }
        .btn-demo.active .btn-demo-title {
            color: var(--accent-blue);
        }
        .btn-demo-sub {
            font-size: 10px;
            color: var(--text-muted);
            line-height: 1.25;
        }
        .btn-demo-reset {
            border-color: #475569;
        }
        .btn-demo-reset:hover {
            border-color: #94a3b8;
        }

        .demo-info-banner {
            margin-top: 10px;
            padding: 8px 12px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 6px;
            font-size: 11px;
            color: #cbd5e1;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Blocked Alert Banner */
        .alert-banner {
            display: none;
            background: linear-gradient(90deg, rgba(239, 68, 68, 0.2) 0%, rgba(245, 158, 11, 0.1) 100%);
            border: 1px solid var(--accent-red);
            border-radius: 12px;
            padding: 12px 18px;
            margin-bottom: 18px;
            animation: pulse-border 2s infinite ease-in-out;
        }
        .alert-banner.active { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
        @keyframes pulse-border {
            0%, 100% { border-color: rgba(239, 68, 68, 0.9); box-shadow: 0 0 15px rgba(239, 68, 68, 0.2); }
            50% { border-color: rgba(239, 68, 68, 0.4); box-shadow: 0 0 5px rgba(239, 68, 68, 0.1); }
        }
        .pipeline-steps {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 11px;
            font-weight: 700;
        }
        .pipeline-pill {
            padding: 3px 8px;
            border-radius: 6px;
            background: rgba(0,0,0,0.4);
            border: 1px solid #475569;
            color: #94a3b8;
        }
        .pipeline-pill.active {
            background: #ef4444;
            border-color: #f87171;
            color: #fff;
        }
        .pipeline-arrow { color: #64748b; }

        /* Metrics Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 12px;
            margin-bottom: 18px;
        }
        .metric-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px 14px;
            box-shadow: var(--shadow-card);
            display: flex;
            flex-direction: column;
        }
        .metric-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }
        .metric-val {
            font-size: 22px;
            font-weight: 800;
            color: #fff;
            letter-spacing: -0.5px;
        }
        .metric-sub {
            font-size: 10px;
            color: var(--text-subtle);
            margin-top: 2px;
        }

        /* Main Workspace Single-Column Layout */
        .workspace-layout {
            display: flex;
            flex-direction: column;
            gap: 18px;
            margin-bottom: 18px;
        }

        .panel-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px 18px;
            box-shadow: var(--shadow-card);
            display: flex;
            flex-direction: column;
        }
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 14px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .panel-title {
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.3px;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Interactive Task Creator Control Panel */
        .task-creator-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 10px;
            padding: 10px 14px;
            margin-bottom: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        .task-creator-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }
        .creator-step-btn {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid #334155;
            color: #94a3b8;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .creator-step-btn:hover {
            border-color: #64748b;
            color: #fff;
        }
        .creator-step-btn.active {
            background: rgba(56, 189, 248, 0.15);
            border-color: #38bdf8;
            color: #38bdf8;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.25);
        }
        .creator-step-btn.completed {
            background: rgba(16, 185, 129, 0.15);
            border-color: #10b981;
            color: #34d399;
        }
        .coord-tag {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 11px;
            font-family: 'JetBrains Mono', monospace;
            color: #cbd5e1;
        }
        .task-help-bar {
            margin-top: 8px;
            font-size: 11px;
            color: #94a3b8;
            line-height: 1.4;
            background: rgba(0, 0, 0, 0.25);
            padding: 6px 10px;
            border-radius: 6px;
            border-left: 3px solid #38bdf8;
        }

        /* 2D Canvas Map (Wide Landscape Format: 500-600px Height) */
        #map-container {
            position: relative;
            width: 100%;
            height: 540px;
            min-height: 420px;
            max-height: 580px;
            background: #080c14;
            border-radius: 10px;
            border: 1px solid #1e293b;
            overflow: hidden;
        }
        @media (max-width: 1024px) {
            #map-container { height: 460px; min-height: 380px; }
        }
        @media (max-width: 768px) {
            #map-container { height: 380px; min-height: 300px; }
        }
        #warehouse-canvas {
            display: block;
            width: 100%;
            height: 100%;
            cursor: crosshair;
        }
        .map-legend {
            display: flex;
            gap: 12px;
            margin-top: 10px;
            font-size: 11px;
            color: var(--text-muted);
            flex-wrap: wrap;
        }
        .legend-item { display: flex; align-items: center; gap: 5px; }
        .legend-box { width: 10px; height: 10px; border-radius: 2px; }

        /* Fleet Table */
        .fleet-table-container {
            overflow-x: auto;
            max-height: 480px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            text-align: left;
        }
        th {
            position: sticky;
            top: 0;
            background: var(--bg-card);
            color: var(--text-muted);
            font-weight: 700;
            text-transform: uppercase;
            font-size: 10px;
            letter-spacing: 0.5px;
            padding: 8px 10px;
            border-bottom: 1px solid var(--border);
        }
        td {
            padding: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }
        tr.amr-row {
            cursor: pointer;
            transition: background 0.15s ease;
        }
        tr.amr-row:hover {
            background: var(--bg-card-hover);
        }
        tr.amr-row.selected {
            background: rgba(56, 189, 248, 0.12);
            outline: 1px solid var(--accent-blue);
        }

        .robot-chip {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 6px;
        }
        .state-pill {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 999px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        .battery-bar {
            width: 100%;
            height: 6px;
            background: #1e293b;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 3px;
        }
        .battery-level { height: 100%; border-radius: 3px; }

        /* Secondary Row: Tasks & Events */
        .bottom-layout {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
            margin-bottom: 18px;
        }
        @media (max-width: 1024px) {
            .bottom-layout { grid-template-columns: 1fr; }
        }

        .task-list-container {
            max-height: 250px;
            overflow-y: auto;
        }
        .task-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            font-size: 12px;
        }
        .task-badge {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 11px;
            background: rgba(255,255,255,0.06);
        }

        .event-stream-container {
            max-height: 250px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
        }
        .event-entry {
            display: flex;
            gap: 8px;
            padding: 6px 8px;
            border-bottom: 1px solid rgba(255,255,255,0.03);
            align-items: flex-start;
        }
        .event-ts { color: var(--text-subtle); min-width: 58px; }
        .event-tag { font-weight: 700; min-width: 70px; }

        /* ===================================================
           FUTURE DEMONSTRATION UI SHELLS (EMPTY CONTAINERS)
           =================================================== */
        .demo-shells-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 18px;
            margin-bottom: 18px;
        }
        .empty-panel-box {
            min-height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(0, 0, 0, 0.25);
            border: 1px dashed var(--border);
            border-radius: 8px;
            padding: 20px;
        }
        .empty-state-text {
            font-size: 12px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-subtle);
            text-align: center;
        }

        /* Telemetry Modal / Drawer */
        #telemetry-drawer {
            display: none;
            position: fixed;
            top: 0; right: 0; bottom: 0;
            width: 380px;
            background: var(--bg-card);
            border-left: 1px solid var(--border);
            box-shadow: -10px 0 30px rgba(0,0,0,0.7);
            z-index: 999;
            padding: 24px;
            overflow-y: auto;
        }
        #telemetry-drawer.open { display: block; }
        .drawer-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
        }
        .drawer-close {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 20px;
            cursor: pointer;
        }
        .drawer-close:hover { color: #fff; }
        .tel-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            font-size: 12px;
        }
        .tel-label { color: var(--text-muted); }
        .tel-val { font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    </style>
</head>
<body>

    <!-- Header Navbar -->
    <div class="top-navbar">
        <div class="brand-section">
            <div class="brand-logo">ROBOSYNC</div>
            <div class="brand-subtitle">Decentralized AMR Fleet Control</div>
            <div class="status-badge badge-running" id="sim-status-badge">
                <div class="badge-dot"></div>
                <span id="sim-status-text">RUNNING</span>
            </div>
        </div>

        <div class="controls-group">
            <button class="btn-ctrl btn-primary" onclick="sendControl('resume')">Start</button>
            <button class="btn-ctrl btn-pause" id="btn-pause-toggle" onclick="togglePause()">Pause</button>
            <button class="btn-ctrl btn-reset" onclick="sendControl('reset')">Reset</button>
            <button class="btn-ctrl btn-hazard" onclick="injectDynamicObstacle()">Obstacle</button>

            <div class="speed-selector">
                <button class="speed-pill" onclick="setSpeed(0.25)">0.25x</button>
                <button class="speed-pill" onclick="setSpeed(0.5)">0.5x</button>
                <button class="speed-pill active" onclick="setSpeed(1.0)">1x</button>
                <button class="speed-pill" onclick="setSpeed(2.0)">2x</button>
                <button class="speed-pill" onclick="setSpeed(5.0)">5x</button>
                <button class="speed-pill" onclick="setSpeed(10.0)">10x</button>
            </div>
        </div>
    </div>

    <!-- ===================================================
         DEMONSTRATION CONTROLS SECTION
         =================================================== -->
    <div class="demo-controls-card">
        <div class="demo-controls-header">
            <div class="demo-brand-tag">
                <span class="demo-title">ROBO SYNC</span>
                <span class="demo-badge">DEMONSTRATION CONTROLS</span>
            </div>
            <div class="demo-status-tag" id="demo-active-label">
                Active Selection: <strong style="color: var(--accent-blue);" id="demo-active-name">NORMAL RUN</strong>
            </div>
        </div>

        <div class="demo-buttons-grid">
            <button class="btn-demo active" id="btn-demo-normal" onclick="selectDemoUI('normal', 'Run normal multi-AMR operations')">
                <span class="btn-demo-title">NORMAL RUN</span>
                <span class="btn-demo-sub">Run normal multi-AMR operations</span>
            </button>
            <button class="btn-demo" id="btn-demo-deadlock" onclick="selectDemoUI('deadlock', 'Demonstrate decentralized deadlock detection and resolution')">
                <span class="btn-demo-title">DEADLOCK DEMO</span>
                <span class="btn-demo-sub">Demonstrate decentralized deadlock detection and resolution</span>
            </button>
            <button class="btn-demo" id="btn-demo-intersection" onclick="selectDemoUI('intersection', 'Demonstrate collision-free intersection coordination')">
                <span class="btn-demo-title">INTERSECTION DEMO</span>
                <span class="btn-demo-sub">Demonstrate collision-free intersection coordination</span>
            </button>
            <button class="btn-demo" id="btn-demo-reservation" onclick="selectDemoUI('reservation', 'Demonstrate spatial-temporal cell reservations')">
                <span class="btn-demo-title">RESERVATION DEMO</span>
                <span class="btn-demo-sub">Demonstrate spatial-temporal cell reservations</span>
            </button>
            <button class="btn-demo" id="btn-demo-blocked" onclick="selectDemoUI('blocked', 'Demonstrate dynamic obstacle detection and local A* replanning')">
                <span class="btn-demo-title">BLOCKED AISLE DEMO</span>
                <span class="btn-demo-sub">Demonstrate dynamic obstacle detection and local A* replanning</span>
            </button>
            <button class="btn-demo btn-demo-reset" id="btn-demo-reset" onclick="selectDemoUI('reset', 'Reset the simulation to its initial state')">
                <span class="btn-demo-title">RESET SIMULATION</span>
                <span class="btn-demo-sub">Reset the simulation to its initial state</span>
            </button>
        </div>

        <div class="demo-info-banner" id="demo-info-banner">
            <strong style="color: var(--accent-blue);">Selected Demonstration:</strong> <span id="demo-info-text">Run normal multi-AMR operations</span>
        </div>
    </div>

    <!-- Active Blocked Aisle Alert Banner -->
    <div class="alert-banner" id="blocked-alert-banner">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 11px; font-weight: 800; color: #ef4444; border: 1px solid #ef4444; border-radius: 4px; padding: 2px 6px;">ALERT</span>
            <div>
                <strong style="color: #fca5a5; font-size: 13px;">DYNAMIC OBSTACLE DETECTED IN AISLE</strong>
                <div id="blocked-alert-detail" style="font-size: 11px; color: var(--text-muted); margin-top: 2px;"></div>
            </div>
        </div>
        <div class="pipeline-steps">
            <div class="pipeline-pill" id="pipe-blocked">PATH BLOCKED</div>
            <div class="pipeline-arrow">-></div>
            <div class="pipeline-pill" id="pipe-replanning">A* REPLANNING</div>
            <div class="pipeline-arrow">-></div>
            <div class="pipeline-pill" id="pipe-found">ALTERNATE PATH FOUND</div>
            <div class="pipeline-arrow">-></div>
            <div class="pipeline-pill" id="pipe-resumed">RESUMED</div>
        </div>
    </div>

    <!-- Metrics Cards Grid -->
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-title">Active AMRs</div>
            <div class="metric-val" id="m-amrs" style="color: var(--accent-blue);">6 / 6</div>
            <div class="metric-sub">Autonomous Agents</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">A* Planners</div>
            <div class="metric-val" id="m-planners" style="color: var(--accent-emerald);">6 Active</div>
            <div class="metric-sub">Decentralized Onboard</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Active Tasks</div>
            <div class="metric-val" id="m-active-tasks" style="color: var(--accent-cyan);">0</div>
            <div class="metric-sub">In Mission Lifecycle</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Tasks Completed</div>
            <div class="metric-val" id="m-completed-tasks" style="color: var(--accent-green);">0</div>
            <div class="metric-sub">Delivered Cargo</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">A* Replans</div>
            <div class="metric-val" id="m-replans" style="color: var(--accent-purple);">0</div>
            <div class="metric-sub">Dynamic Reroutes</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Conflicts & Deadlocks</div>
            <div class="metric-val" id="m-conflicts" style="color: var(--accent-yellow);">0</div>
            <div class="metric-sub" id="m-conflicts-sub">0 Deadlocks Resolved</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Safety Collisions</div>
            <div class="metric-val" id="m-collisions" style="color: var(--accent-emerald);">0</div>
            <div class="metric-sub">Physical Penetrations</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Fleet Distance</div>
            <div class="metric-val" id="m-distance">0.0 m</div>
            <div class="metric-sub" id="m-simtime">Sim Time: 0.0s</div>
        </div>
    </div>

    <!-- Main Workspace (Canvas Map + Fleet Sidebar) -->
    <div class="workspace-layout">
        <!-- 2D Warehouse Map -->
        <div class="panel-card">
            <div class="panel-header">
                <div class="panel-title">
                    <span>2D Interactive Warehouse Grid & A* Trajectory Map</span>
                </div>
                <div style="font-size: 11px; color: var(--text-muted);">
                    Click AMR to Inspect Telemetry
                </div>
            </div>

            <!-- Interactive Task Creator & Dynamic Obstacle Editor Control Bar -->
            <div class="task-creator-card" id="task-creator-panel">
                <div class="task-creator-header">
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <span style="font-weight: 700; color: #fff; font-size: 13px;">INTERACTIVE CONTROLS</span>
                        <span class="pipeline-pill" id="task-creator-mode-tag" style="font-size: 10px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; border-color: rgba(56, 189, 248, 0.4);">READY</span>
                        <span class="pipeline-pill" id="obstacle-mode-tag" style="font-size: 10px; background: rgba(239, 68, 68, 0.15); color: #ef4444; border-color: rgba(239, 68, 68, 0.4); display: none;">OBSTACLE EDIT MODE ACTIVE</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <button class="btn-ctrl" id="btn-toggle-obstacle-mode" onclick="toggleObstacleEditMode()" style="background: rgba(239, 68, 68, 0.2); border-color: #ef4444; color: #fca5a5; font-size: 12px; font-weight: 700; padding: 5px 14px;">
                            + / - Blocked Cell Editor
                        </button>
                        <button class="btn-ctrl btn-reset" id="btn-clear-obstacles" onclick="clearAllObstaclesUI()" style="padding: 5px 10px; font-size: 11px;">
                            Clear Obstacles
                        </button>
                        <button class="btn-ctrl btn-primary" id="btn-create-task-toggle" onclick="toggleTaskCreationMode()" style="padding: 5px 14px; font-size: 12px; font-weight: 700;">
                            + Create Task
                        </button>
                    </div>
                </div>

                <div class="task-help-bar" id="obstacle-help-bar" style="display: none; margin-top: 10px; background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3); color: #fca5a5;">
                    <strong>Obstacle Editor Active:</strong> Click any <span style="color: #38bdf8; font-weight: 700;">walkable aisle cell</span> to place a dynamic blockage, or click an <span style="color: #ef4444; font-weight: 700;">existing red blocked cell</span> to remove it. AMRs will detect obstacles and replan dynamically!
                </div>

                <div id="task-creation-controls" style="display: none; margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.06);">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            <button class="creator-step-btn active" id="btn-step-pickup" onclick="setTaskCreationStep('PICKUP')">
                                Step 1: Place Source Box (B)
                            </button>
                            <span style="color: #64748b; font-weight: 700;">-></span>
                            <button class="creator-step-btn" id="btn-step-dropoff" onclick="setTaskCreationStep('DROPOFF')">
                                Step 2: Place Target Destination (TD)
                            </button>
                        </div>

                        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            <div class="coord-tag" id="tag-pickup-coord">Source [B]: <strong style="color: #38bdf8;">Select on Map</strong></div>
                            <div class="coord-tag" id="tag-dropoff-coord">Destination [TD]: <strong style="color: #c084fc;">Select on Map</strong></div>
                            
                            <select id="custom-task-priority" class="scenario-select" style="padding: 4px 8px; font-size: 11px;">
                                <option value="1.0">Priority: Normal (1.0)</option>
                                <option value="1.5">Priority: High (1.5)</option>
                                <option value="2.0">Priority: Urgent (2.0)</option>
                            </select>

                            <button class="btn-ctrl" id="btn-assign-task" onclick="submitCustomTask()" style="background: #059669; border-color: #10b981; color: #fff; font-weight: 700; padding: 5px 14px; opacity: 0.5; cursor: not-allowed;" disabled>
                                Assign / Start Task
                            </button>
                            <button class="btn-ctrl btn-reset" onclick="cancelTaskCreation()" style="padding: 5px 10px;">
                                Cancel
                            </button>
                        </div>
                    </div>

                    <div class="task-help-bar" id="task-help-instructions">
                        <strong>Step 1:</strong> Click any walkable floor cell on the warehouse map to place the source box (B).
                    </div>
                </div>
            </div>

            <div id="map-container">
                <canvas id="warehouse-canvas"></canvas>
            </div>

            <div class="map-legend">
                <div class="legend-item"><div class="legend-box" style="background: #1e293b; border: 1px solid #475569;"></div> Shelf Racks</div>
                <div class="legend-item"><div class="legend-box" style="background: #0284c7;"></div> Pickup (P1-P4)</div>
                <div class="legend-item"><div class="legend-box" style="background: #059669;"></div> Dropoff (D1-D4)</div>
                <div class="legend-item"><div class="legend-box" style="background: #d97706;"></div> Charging Docks</div>
                <div class="legend-item"><div class="legend-box" style="background: rgba(239, 68, 68, 0.25); border: 1px solid #ef4444; color: #ef4444; font-weight: 800; font-size: 9px; display: flex; align-items: center; justify-content: center; font-family: monospace;">B</div> Blocked Way (Red B)</div>
                <div class="legend-item"><div class="legend-box" style="background: #38bdf8;"></div> Active A* Route</div>
                <div class="legend-item"><div class="legend-box" style="background: #b45309; border: 1px solid #fcd34d; color: #fff; font-weight: 800; font-size: 9px; display: flex; align-items: center; justify-content: center; font-family: monospace;">B</div> Warehouse Box / Obstacle (B)</div>
                <div class="legend-item"><div class="legend-box" style="background: rgba(192, 132, 252, 0.25); border: 1px solid #c084fc; color: #c084fc; font-weight: 800; font-size: 8px; display: flex; align-items: center; justify-content: center; font-family: monospace;">TD</div> Target Destination (TD)</div>
            </div>
        </div>

        <!-- Fleet Telemetry Sidebar -->
        <div class="panel-card">
            <div class="panel-header">
                <div class="panel-title">
                    <span>Fleet Telemetry & Local A* Planners</span>
                </div>
            </div>

            <div class="fleet-table-container">
                <table>
                    <thead>
                        <tr>
                            <th>AMR</th>
                            <th>Status</th>
                            <th>Mission</th>
                            <th>Battery</th>
                            <th>A* Route</th>
                        </tr>
                    </thead>
                    <tbody id="fleet-table-body">
                        <!-- Populated by JS -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- ===================================================
         DEMONSTRATION SHELLS: P2P, RESERVATIONS, DEADLOCK
         =================================================== -->
    <div class="demo-shells-grid">
        <!-- P2P Communication Panel (Empty Shell) -->
        <div class="panel-card">
            <div class="panel-header">
                <div class="panel-title">
                    <span>P2P COMMUNICATION</span>
                </div>
                <span class="pipeline-pill" style="font-size: 10px; color: var(--accent-blue); border-color: rgba(56, 189, 248, 0.4);">P2P MESH</span>
            </div>
            <div class="empty-panel-box" id="p2p-comm-container">
                <div class="empty-state-text">Waiting for live communication data...</div>
            </div>
        </div>

        <!-- Spatial-Temporal Reservations Panel (Empty Shell) -->
        <div class="panel-card">
            <div class="panel-header">
                <div class="panel-title">
                    <span>SPATIAL-TEMPORAL RESERVATIONS</span>
                </div>
                <span class="pipeline-pill" style="font-size: 10px; color: var(--accent-green); border-color: rgba(16, 185, 129, 0.4);">CELL + TIME WINDOW</span>
            </div>
            <div class="empty-panel-box" id="spatial-reservation-container">
                <div class="empty-state-text">No active reservations</div>
            </div>
        </div>

        <!-- Deadlock / Conflict Status Panel (Empty Shell) -->
        <div class="panel-card">
            <div class="panel-header">
                <div class="panel-title">
                    <span>DEADLOCK / CONFLICT STATUS</span>
                </div>
                <span class="pipeline-pill" style="font-size: 10px; color: var(--accent-yellow); border-color: rgba(245, 158, 11, 0.4);">CYCLE DETECTION</span>
            </div>
            <div class="empty-panel-box" id="deadlock-status-container">
                <div class="empty-state-text">No active conflicts</div>
            </div>
        </div>
    </div>

    <!-- Secondary Row: Decentralized Task Auctions & Live Event Log -->
    <div class="bottom-layout">
        <!-- Task Auction Table -->
        <div class="panel-card">
            <div class="panel-header">
                <div class="panel-title">
                    <span>Decentralized Task Auction Pool</span>
                </div>
            </div>
            <div class="task-list-container" id="task-list-body">
                <!-- Populated by JS -->
            </div>
        </div>

        <!-- Live Event Stream -->
        <div class="panel-card">
            <div class="panel-header">
                <div class="panel-title">
                    <span>Real-Time Coordination Event Stream</span>
                </div>
            </div>
            <div class="event-stream-container" id="event-stream-body">
                <!-- Populated by JS -->
            </div>
        </div>
    </div>

    <!-- Selected AMR Deep Telemetry Drawer -->
    <div id="telemetry-drawer">
        <div class="drawer-header">
            <h3 id="drawer-title" style="font-size: 16px; font-weight: 800; color: var(--accent-blue);">AMR-1 TELEMETRY</h3>
            <button class="drawer-close" onclick="closeDrawer()">x</button>
        </div>
        <div id="drawer-content">
            <!-- Populated by JS -->
        </div>
    </div>

    <script>
        const AMR_THEME = {
            'AMR-1': { color: '#38bdf8', fill: 'rgba(56, 189, 248, 0.2)' },
            'AMR-2': { color: '#f87171', fill: 'rgba(248, 113, 113, 0.2)' },
            'AMR-3': { color: '#4ade80', fill: 'rgba(74, 222, 128, 0.2)' },
            'AMR-4': { color: '#facc15', fill: 'rgba(250, 204, 21, 0.2)' },
            'AMR-5': { color: '#c084fc', fill: 'rgba(192, 132, 252, 0.2)' },
            'AMR-6': { color: '#2dd4bf', fill: 'rgba(45, 212, 191, 0.2)' }
        };

        let currentSnapshot = null;
        let selectedAmrId = null;
        let isPausedState = false;
        let pendingDemoId = null;
        let pendingDemoTime = 0;

        // Demonstration Control Button UI Handler
        function selectDemoUI(demoId, description) {
            if (demoId !== 'reset') {
                pendingDemoId = demoId;
                pendingDemoTime = Date.now();
            }

            // Update active styling on demo buttons
            document.querySelectorAll('.btn-demo').forEach(btn => btn.classList.remove('active'));
            const clickedBtn = document.getElementById('btn-demo-' + demoId);
            if (clickedBtn && demoId !== 'reset') {
                clickedBtn.classList.add('active');
            }

            const activeNameEl = document.getElementById('demo-active-name');
            const infoTextEl = document.getElementById('demo-info-text');

            const titleMap = {
                'normal': 'NORMAL RUN',
                'deadlock': 'DEADLOCK DEMO',
                'intersection': 'INTERSECTION DEMO',
                'reservation': 'RESERVATION DEMO',
                'blocked': 'BLOCKED AISLE DEMO',
                'reset': 'RESET SIMULATION'
            };

            if (activeNameEl) activeNameEl.innerText = titleMap[demoId] || demoId.toUpperCase();
            if (infoTextEl) infoTextEl.innerText = description;

            // Wire scenario switching
            if (demoId === 'deadlock') {
                if (obstacleEditMode) toggleObstacleEditMode();
                sendControl('set_scenario', { scenario: 'deadlock' });
            } else if (demoId === 'normal') {
                if (obstacleEditMode) toggleObstacleEditMode();
                sendControl('set_scenario', { scenario: 'normal' });
            } else if (demoId === 'intersection') {
                if (obstacleEditMode) toggleObstacleEditMode();
                sendControl('set_scenario', { scenario: 'intersection' });
            } else if (demoId === 'reservation') {
                if (obstacleEditMode) toggleObstacleEditMode();
                sendControl('set_scenario', { scenario: 'reservation' });
            } else if (demoId === 'blocked') {
                sendControl('set_scenario', { scenario: 'blocked' });
            } else if (demoId === 'reset') {
                if (obstacleEditMode) toggleObstacleEditMode();
                sendControl('reset');
            }
        }

        // Drawer
        function selectAmr(robotId) {
            selectedAmrId = robotId;
            const drawer = document.getElementById('telemetry-drawer');
            drawer.classList.add('open');
            if (currentSnapshot && currentSnapshot.fleet) {
                const amr = currentSnapshot.fleet.find(a => a.robot_id === robotId);
                updateDrawer(amr);
            }
        }

        function closeDrawer() {
            selectedAmrId = null;
            document.getElementById('telemetry-drawer').classList.remove('open');
            document.querySelectorAll('.amr-row').forEach(r => r.classList.remove('selected'));
        }

        function updateDrawer(amr) {
            if (!amr) return;
            document.getElementById('drawer-title').innerText = `${amr.robot_id} TELEMETRY`;
            document.getElementById('drawer-title').style.color = AMR_THEME[amr.robot_id]?.color || '#38bdf8';

            const astar = amr.astar_metrics || {};
            const content = document.getElementById('drawer-content');
            content.innerHTML = `
                <div class="tel-row"><span class="tel-label">Status</span><span class="tel-val" style="color:${AMR_THEME[amr.robot_id]?.color}">${amr.status}</span></div>
                <div class="tel-row"><span class="tel-label">Active Task</span><span class="tel-val">${amr.task_id}</span></div>
                <div class="tel-row"><span class="tel-label">Grid Coordinates</span><span class="tel-val">(${amr.grid_pos[0]}, ${amr.grid_pos[1]})</span></div>
                <div class="tel-row"><span class="tel-label">World Coordinates</span><span class="tel-val">(${amr.world_pos[0]}, ${amr.world_pos[1]})</span></div>
                <div class="tel-row"><span class="tel-label">Heading (Yaw)</span><span class="tel-val">${amr.yaw} rad</span></div>
                <div class="tel-row"><span class="tel-label">Target Destination</span><span class="tel-val">${amr.goal_desc}</span></div>
                <div class="tel-row"><span class="tel-label">Battery Level</span><span class="tel-val" style="color:#10b981">${amr.battery}%</span></div>
                <div class="tel-row"><span class="tel-label">Tasks Completed</span><span class="tel-val">${amr.completed_tasks}</span></div>
                <div class="tel-row"><span class="tel-label">Distance Travelled</span><span class="tel-val">${amr.total_distance} m</span></div>
                
                <h4 style="margin: 18px 0 8px 0; font-size: 11px; text-transform: uppercase; color: var(--text-muted); border-bottom: 1px solid var(--border); padding-bottom: 4px;">Onboard A* Path Planner</h4>
                <div class="tel-row"><span class="tel-label">Planning Status</span><span class="tel-val">${astar.planning_status || 'Ready'}</span></div>
                <div class="tel-row"><span class="tel-label">Planning Time</span><span class="tel-val" style="color:var(--accent-emerald)">${astar.planning_time_ms || 0} ms</span></div>
                <div class="tel-row"><span class="tel-label">Nodes Explored</span><span class="tel-val" style="color:var(--accent-purple)">${astar.nodes_explored || 0} nodes</span></div>
                <div class="tel-row"><span class="tel-label">Path Length</span><span class="tel-val">${astar.path_length || 0} steps</span></div>
                <div class="tel-row"><span class="tel-label">Computed Path Cost</span><span class="tel-val" style="color:var(--accent-blue)">${astar.path_cost || 0}</span></div>
                <div class="tel-row"><span class="tel-label">Lifetime Replans</span><span class="tel-val">${astar.replan_count || 0}</span></div>
            `;
        }

        // Interactive Task Creator State
        let taskCreationMode = false;
        let obstacleEditMode = false;
        let taskCreationStep = 'PICKUP';
        let selectedPickup = null;
        let selectedDropoff = null;
        let hoveredCell = null;
        let customTaskCounter = 1;

        function toggleObstacleEditMode() {
            obstacleEditMode = !obstacleEditMode;
            if (obstacleEditMode && taskCreationMode) {
                toggleTaskCreationMode();
            }
            const toggleBtn = document.getElementById('btn-toggle-obstacle-mode');
            const obsTag = document.getElementById('obstacle-mode-tag');
            const helpBar = document.getElementById('obstacle-help-bar');

            if (obstacleEditMode) {
                if (toggleBtn) {
                    toggleBtn.style.background = '#dc2626';
                    toggleBtn.style.borderColor = '#ef4444';
                    toggleBtn.style.color = '#fff';
                    toggleBtn.innerText = 'Exit Obstacle Editor';
                }
                if (obsTag) obsTag.style.display = 'inline-block';
                if (helpBar) helpBar.style.display = 'block';
            } else {
                if (toggleBtn) {
                    toggleBtn.style.background = 'rgba(239, 68, 68, 0.2)';
                    toggleBtn.style.borderColor = '#ef4444';
                    toggleBtn.style.color = '#fca5a5';
                    toggleBtn.innerText = '+ / - Blocked Cell Editor';
                }
                if (obsTag) obsTag.style.display = 'none';
                if (helpBar) helpBar.style.display = 'none';
            }
            if (currentSnapshot) drawMap(currentSnapshot);
        }

        async function clearAllObstaclesUI() {
            await sendControl('clear_obstacles');
        }

        const SHELF_BLOCKS = [
            { x: [5, 10], y: [3, 4] },
            { x: [5, 10], y: [8, 9] },
            { x: [5, 10], y: [11, 12] },
            { x: [14, 19], y: [3, 4] },
            { x: [14, 19], y: [8, 9] },
            { x: [14, 19], y: [11, 12] }
        ];

        const CHARGING_DOCKS = [
            [1, 2], [22, 2], [1, 13], [22, 13], [1, 7], [22, 7]
        ];

        function isCellWalkableFloor(gx, gy) {
            if (gx <= 0 || gx >= 23 || gy <= 0 || gy >= 15) return false;
            for (const shelf of SHELF_BLOCKS) {
                if (gx >= shelf.x[0] && gx <= shelf.x[1] && gy >= shelf.y[0] && gy <= shelf.y[1]) {
                    return false;
                }
            }
            for (const dock of CHARGING_DOCKS) {
                if (dock[0] === gx && dock[1] === gy) return false;
            }
            return true;
        }

        function isCellValidForTaskStep(gx, gy, step) {
            if (!isCellWalkableFloor(gx, gy)) return false;
            if (step === 'DROPOFF' && selectedPickup) {
                if (selectedPickup[0] === gx && selectedPickup[1] === gy) return false;
            }
            return true;
        }

        function toggleTaskCreationMode() {
            taskCreationMode = !taskCreationMode;
            if (taskCreationMode && obstacleEditMode) {
                toggleObstacleEditMode();
            }
            const controls = document.getElementById('task-creation-controls');
            const toggleBtn = document.getElementById('btn-create-task-toggle');
            const modeTag = document.getElementById('task-creator-mode-tag');

            if (taskCreationMode) {
                controls.style.display = 'block';
                toggleBtn.innerText = 'Close Panel';
                toggleBtn.className = 'btn-ctrl btn-reset';
                modeTag.innerText = 'SELECTING PICKUP';
                modeTag.style.color = '#38bdf8';
                modeTag.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                setTaskCreationStep('PICKUP');
            } else {
                controls.style.display = 'none';
                toggleBtn.innerText = '+ Create Task';
                toggleBtn.className = 'btn-ctrl btn-primary';
                modeTag.innerText = 'READY';
                modeTag.style.color = '#94a3b8';
                modeTag.style.borderColor = '#475569';
                resetTaskCreationForm();
            }
            if (currentSnapshot) drawMap(currentSnapshot);
        }

        function setTaskCreationStep(step) {
            taskCreationStep = step;
            const btnP = document.getElementById('btn-step-pickup');
            const btnD = document.getElementById('btn-step-dropoff');
            const modeTag = document.getElementById('task-creator-mode-tag');
            const helpText = document.getElementById('task-help-instructions');

            if (step === 'PICKUP') {
                if (btnP) btnP.className = 'creator-step-btn active';
                if (btnD) btnD.className = 'creator-step-btn' + (selectedDropoff ? ' completed' : '');
                if (modeTag) {
                    modeTag.innerText = 'SELECTING SOURCE (B)';
                    modeTag.style.color = '#38bdf8';
                }
                if (helpText) {
                    helpText.innerHTML = '<strong>Step 1:</strong> Click any walkable floor aisle cell on the warehouse map to place the source box (B).';
                }
            } else {
                if (btnP) btnP.className = 'creator-step-btn completed';
                if (btnD) btnD.className = 'creator-step-btn active';
                if (modeTag) {
                    modeTag.innerText = 'SELECTING DESTINATION (TD)';
                    modeTag.style.color = '#c084fc';
                }
                if (helpText) {
                    helpText.innerHTML = '<strong>Step 2:</strong> Click another walkable aisle cell to set the target destination point (TD).';
                }
            }
            if (currentSnapshot) drawMap(currentSnapshot);
        }

        function resetTaskCreationForm() {
            selectedPickup = null;
            selectedDropoff = null;
            hoveredCell = null;
            taskCreationStep = 'PICKUP';
            const tagP = document.getElementById('tag-pickup-coord');
            const tagD = document.getElementById('tag-dropoff-coord');
            if (tagP) tagP.innerHTML = 'Source [B]: <strong style="color: #38bdf8;">Select on Map</strong>';
            if (tagD) tagD.innerHTML = 'Destination [TD]: <strong style="color: #c084fc;">Select on Map</strong>';
            
            const assignBtn = document.getElementById('btn-assign-task');
            if (assignBtn) {
                assignBtn.disabled = true;
                assignBtn.style.opacity = '0.5';
                assignBtn.style.cursor = 'not-allowed';
                assignBtn.innerText = 'Assign / Start Task';
            }
            const btnP = document.getElementById('btn-step-pickup');
            const btnD = document.getElementById('btn-step-dropoff');
            if (btnP) btnP.className = 'creator-step-btn active';
            if (btnD) btnD.className = 'creator-step-btn';
        }

        function cancelTaskCreation() {
            toggleTaskCreationMode();
        }

        async function submitCustomTask() {
            if (!selectedPickup || !selectedDropoff) return;

            const priVal = parseFloat(document.getElementById('custom-task-priority').value) || 1.0;
            const customTaskId = `BLOCK-${String(customTaskCounter).padStart(2, '0')}`;
            customTaskCounter++;

            const payload = {
                action: 'create_custom_task',
                params: {
                    pickup: selectedPickup,
                    dropoff: selectedDropoff,
                    priority: priVal,
                    task_id: customTaskId
                }
            };

            const assignBtn = document.getElementById('btn-assign-task');
            if (assignBtn) {
                assignBtn.innerHTML = 'Dispatching Task...';
                assignBtn.disabled = true;
            }

            await sendControl('create_custom_task', payload.params);

            setTimeout(() => {
                resetTaskCreationForm();
                toggleTaskCreationMode();
            }, 300);
        }

        // Fetch State loop
        async function fetchState() {
            try {
                const res = await fetch('/api/state');
                if (res.ok) {
                    currentSnapshot = await res.json();
                    renderUI(currentSnapshot);
                }
            } catch (err) {
                console.error('Telemetry fetch error:', err);
            }
        }

        // Control API Calls
        async function sendControl(action, params = {}) {
            try {
                const res = await fetch('/api/control', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action, params })
                });
                if (res.ok) {
                    await fetchState();
                }
            } catch (err) {
                console.error('Control error:', err);
            }
        }

        let pendingPauseState = null;
        let pendingPauseTime = 0;

        function togglePause() {
            // Optimistically update UI button immediately to eliminate any lag or flicker
            const newPaused = (pendingPauseState !== null) ? !pendingPauseState : !isPausedState;
            pendingPauseState = newPaused;
            pendingPauseTime = Date.now();
            updatePauseButtonUI(newPaused);
            sendControl('toggle_pause');
        }

        function updatePauseButtonUI(isPaused) {
            const badge = document.getElementById('sim-status-badge');
            const badgeText = document.getElementById('sim-status-text');
            const pauseBtn = document.getElementById('btn-pause-toggle');
            if (isPaused) {
                if (badge) badge.className = 'status-badge badge-paused';
                if (badgeText) badgeText.innerText = 'PAUSED';
                if (pauseBtn) pauseBtn.innerText = 'Resume';
            } else {
                if (badge) badge.className = 'status-badge badge-running';
                if (badgeText) badgeText.innerText = 'RUNNING';
                if (pauseBtn) pauseBtn.innerText = 'Pause';
            }
        }

        function setSpeed(spd) {
            document.querySelectorAll('.speed-pill').forEach(el => el.classList.remove('active'));
            if (window.event && window.event.target) {
                window.event.target.classList.add('active');
            }
            sendControl('set_speed', { speed: spd });
        }

        function switchScenario(scen) {
            sendControl('set_scenario', { scenario: scen });
        }

        function injectDynamicObstacle() {
            sendControl('inject_obstacle', { cell: [11, 13] });
        }

        // UI Renderer
        function renderUI(data) {
            if (!data || !data.system) return;

            const sys = data.system;
            isPausedState = sys.is_paused;

            if (pendingPauseState !== null) {
                if (sys.is_paused === pendingPauseState || (Date.now() - pendingPauseTime > 1200)) {
                    pendingPauseState = null;
                }
            }

            const effectivePaused = (pendingPauseState !== null) ? pendingPauseState : sys.is_paused;
            updatePauseButtonUI(effectivePaused);

            // Sync Demonstration Button with backend scenario state
            if (sys.scenario) {
                const currentScen = sys.scenario.toLowerCase();
                if (pendingDemoId && (currentScen === pendingDemoId || (Date.now() - pendingDemoTime > 1500))) {
                    pendingDemoId = null;
                }
                
                if (!pendingDemoId) {
                    const btnConfig = {
                        'normal': { id: 'btn-demo-normal', name: 'NORMAL RUN', desc: 'Run normal multi-AMR operations' },
                        'deadlock': { id: 'btn-demo-deadlock', name: 'DEADLOCK DEMO', desc: 'Demonstrate decentralized deadlock detection and resolution' },
                        'blocked': { id: 'btn-demo-blocked', name: 'BLOCKED AISLE DEMO', desc: 'Demonstrate dynamic obstacle detection and local A* replanning' },
                        'intersection': { id: 'btn-demo-intersection', name: 'INTERSECTION DEMO', desc: 'Demonstrate collision-free intersection coordination' },
                        'reservation': { id: 'btn-demo-reservation', name: 'RESERVATION DEMO', desc: 'Demonstrate spatial-temporal cell reservations' },
                        'six_amr': { id: 'btn-demo-normal', name: '6-AMR BENCHMARK', desc: 'Run 6-AMR full fleet benchmark' }
                    };

                    const cfg = btnConfig[currentScen];
                    if (cfg) {
                        const btnEl = document.getElementById(cfg.id);
                        if (btnEl && !btnEl.classList.contains('active')) {
                            document.querySelectorAll('.btn-demo').forEach(b => b.classList.remove('active'));
                            btnEl.classList.add('active');
                            const activeNameEl = document.getElementById('demo-active-name');
                            const infoTextEl = document.getElementById('demo-info-text');
                            if (activeNameEl) activeNameEl.innerText = cfg.name;
                            if (infoTextEl) infoTextEl.innerText = cfg.desc;
                        }
                    }
                }
            }

            // Metrics Cards
            document.getElementById('m-amrs').innerText = sys.active_amrs + ' / 6';
            document.getElementById('m-planners').innerText = sys.active_planners + ' Active';
            document.getElementById('m-active-tasks').innerText = sys.tasks_active !== undefined ? sys.tasks_active : 0;
            document.getElementById('m-completed-tasks').innerText = sys.tasks_completed;
            document.getElementById('m-replans').innerText = sys.autonomous_replans;
            document.getElementById('m-conflicts').innerText = sys.conflicts_resolved;
            const subConf = document.getElementById('m-conflicts-sub');
            if (subConf) subConf.innerText = (sys.deadlocks_resolved || 0) + ' Deadlocks Resolved';
            document.getElementById('m-collisions').innerText = sys.collision_count;
            document.getElementById('m-distance').innerText = sys.total_distance + ' m';
            document.getElementById('m-simtime').innerText = 'Sim Time: ' + sys.sim_time + 's (' + sys.sim_speed + 'x)';

            // Blocked Alert Banner
            renderBlockedBanner(data.blocked_alert);

            // Fleet Table
            renderFleetTable(data.fleet);

            // Task List
            renderTaskList(data.tasks);

            // Event Stream
            renderEventStream(data.recent_events);

            // Draw 2D Canvas Map
            drawMap(data);

            // Update Drawer if Open
            if (selectedAmrId) {
                updateDrawer(data.fleet.find(a => a.robot_id === selectedAmrId));
            }
        }

        function renderBlockedBanner(alert) {
            const banner = document.getElementById('blocked-alert-banner');
            if (alert && alert.active) {
                banner.classList.add('active');
                const obsStr = alert.obstacle_pos ? `(${alert.obstacle_pos.join(', ')})` : '(11, 13)';
                document.getElementById('blocked-alert-detail').innerText = 
                    `Aisle location: ${obsStr} | Affected Vehicle: ${alert.affected_amr || 'AMR-3'}`;

                // Update pipeline pills
                ['blocked', 'replanning', 'found', 'resumed'].forEach(p => {
                    const el = document.getElementById('pipe-' + p);
                    el.classList.remove('active');
                });
                if (alert.stage === 'PATH BLOCKED') document.getElementById('pipe-blocked').classList.add('active');
                else if (alert.stage === 'A* REPLANNING') document.getElementById('pipe-replanning').classList.add('active');
                else if (alert.stage === 'ALTERNATE PATH FOUND') document.getElementById('pipe-found').classList.add('active');
                else if (alert.stage === 'RESUMED') document.getElementById('pipe-resumed').classList.add('active');
            } else {
                banner.classList.remove('active');
            }
        }

        function renderFleetTable(fleet) {
            const tbody = document.getElementById('fleet-table-body');
            tbody.innerHTML = '';
            (fleet || []).forEach(amr => {
                const tr = document.createElement('tr');
                tr.className = 'amr-row' + (selectedAmrId === amr.robot_id ? ' selected' : '');
                tr.onclick = () => selectAmr(amr.robot_id);

                const theme = AMR_THEME[amr.robot_id] || { color: '#fff', fill: '#1e293b' };
                const battColor = amr.battery > 50 ? '#10b981' : (amr.battery > 25 ? '#f59e0b' : '#ef4444');

                tr.innerHTML = `
                    <td>
                        <div class="robot-chip" style="background: ${theme.fill}; color: ${theme.color}; border: 1px solid ${theme.color}44;">
                            ${amr.robot_id}
                        </div>
                    </td>
                    <td><span class="state-pill" style="background: rgba(255,255,255,0.06); color: ${theme.color};">${amr.status}</span></td>
                    <td style="font-family: 'JetBrains Mono'; font-size: 11px;">${amr.task_id}</td>
                    <td style="min-width: 80px;">
                        <div style="font-size: 11px; font-weight: 700; color: ${battColor};">${amr.battery}%</div>
                        <div class="battery-bar"><div class="battery-level" style="width: ${amr.battery}%; background: ${battColor};"></div></div>
                    </td>
                    <td style="font-size: 11px; color: var(--text-muted);">${amr.planning_status}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function renderTaskList(tasks) {
            const container = document.getElementById('task-list-body');
            container.innerHTML = '';
            if (!tasks || tasks.length === 0) {
                container.innerHTML = '<div style="padding: 12px; color: var(--text-subtle); text-align: center;">No active tasks</div>';
                return;
            }

            tasks.forEach(t => {
                const assigned = t.assigned_to ? `<span style="color: ${AMR_THEME[t.assigned_to]?.color || '#38bdf8'}; font-weight: 700;">${t.assigned_to}</span>` : '<span style="color: #c084fc; font-weight: 600;">AUCTIONING</span>';
                
                let statusColor = '#f59e0b';
                let statusBadgeBg = 'rgba(245, 158, 11, 0.15)';
                let statusText = t.status;

                if (t.status === 'COMPLETED') {
                    statusColor = '#10b981';
                    statusBadgeBg = 'rgba(16, 185, 129, 0.15)';
                    statusText = 'DELIVERED';
                } else if (t.status === 'IN_PROGRESS' || t.status === 'PICKED_UP') {
                    statusColor = '#38bdf8';
                    statusBadgeBg = 'rgba(56, 189, 248, 0.15)';
                    statusText = 'IN TRANSIT';
                } else if (t.status === 'ASSIGNED') {
                    statusColor = '#facc15';
                    statusBadgeBg = 'rgba(250, 204, 21, 0.15)';
                    statusText = 'DISPATCHED';
                }

                const div = document.createElement('div');
                div.className = 'task-item';
                div.innerHTML = `
                    <div>
                        <div style="font-weight: 700; color: #fff; font-size: 12px;">${t.task_id}</div>
                        <div style="color: var(--text-muted); font-size: 11px;">Pickup ${t.pickup_zone} (${t.pickup_pos ? t.pickup_pos.join(',') : ''}) -> Drop ${t.dropoff_zone} (${t.dropoff_pos ? t.dropoff_pos.join(',') : ''})</div>
                    </div>
                    <div style="text-align: right;">
                        <div>${assigned}</div>
                        <span style="display: inline-block; margin-top: 2px; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px; background: ${statusBadgeBg}; color: ${statusColor};">${statusText}</span>
                    </div>
                `;
                container.appendChild(div);
            });
        }

        function renderEventStream(events) {
            const container = document.getElementById('event-stream-body');
            container.innerHTML = '';
            if (!events || events.length === 0) {
                container.innerHTML = '<div style="padding: 12px; color: var(--text-subtle); text-align: center;">Waiting for events...</div>';
                return;
            }

            events.slice().reverse().forEach(e => {
                const div = document.createElement('div');
                div.className = 'event-entry';
                const tagColor = AMR_THEME[e.tag]?.color || '#94a3b8';
                div.innerHTML = `
                    <span class="event-ts">${e.timestamp}</span>
                    <span class="event-tag" style="color: ${tagColor}">[${e.tag}]</span>
                    <span style="color: var(--text-main)">${e.message}</span>
                `;
                container.appendChild(div);
            });
        }

        // Draw Canvas Map
        function drawMap(data) {
            const canvas = document.getElementById('warehouse-canvas');
            const container = document.getElementById('map-container');
            if (!canvas || !container) return;

            // Handle Resize
            if (canvas.width !== container.clientWidth || canvas.height !== container.clientHeight) {
                canvas.width = container.clientWidth;
                canvas.height = container.clientHeight;
            }

            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            const gridW = 24;
            const gridH = 16;
            const cellW = canvas.width / gridW;
            const cellH = canvas.height / gridH;
            const cellR = Math.min(cellW, cellH);

            // Draw Subtle Grid
            ctx.strokeStyle = '#1e293b';
            ctx.lineWidth = 1;
            for (let x = 0; x <= gridW; x++) {
                ctx.beginPath();
                ctx.moveTo(x * cellW, 0);
                ctx.lineTo(x * cellW, canvas.height);
                ctx.stroke();
            }
            for (let y = 0; y <= gridH; y++) {
                ctx.beginPath();
                ctx.moveTo(0, y * cellH);
                ctx.lineTo(canvas.width, y * cellH);
                ctx.stroke();
            }

            // Draw Shelf Blocks
            const layout = data.layout || {};
            (layout.shelf_blocks || []).forEach(b => {
                const [xs, xe, ys, ye] = b;
                const bx = xs * cellW;
                const by = (gridH - 1 - ye) * cellH;
                const bw = (xe - xs + 1) * cellW;
                const bh = (ye - ys + 1) * cellH;

                ctx.fillStyle = '#0f172a';
                ctx.fillRect(bx, by, bw, bh);
                ctx.strokeStyle = '#334155';
                ctx.lineWidth = 1.5;
                ctx.strokeRect(bx, by, bw, bh);

                ctx.strokeStyle = '#1e293b';
                for (let sx = xs; sx <= xe; sx++) {
                    ctx.beginPath();
                    ctx.moveTo(sx * cellW, by);
                    ctx.lineTo(sx * cellW, by + bh);
                    ctx.stroke();
                }
            });

            // Draw Pickups (P1-P4)
            const pickups = layout.pickup_zones || {};
            for (const [pname, pos] of Object.entries(pickups)) {
                const px = pos[0] * cellW;
                const py = (gridH - 1 - pos[1]) * cellH;
                ctx.fillStyle = 'rgba(2, 132, 199, 0.25)';
                ctx.fillRect(px, py, cellW, cellH);
                ctx.strokeStyle = '#0284c7';
                ctx.lineWidth = 1.5;
                ctx.strokeRect(px, py, cellW, cellH);

                ctx.fillStyle = '#38bdf8';
                ctx.font = 'bold 11px sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(pname, px + cellW / 2, py + cellH / 2);
            }

            // Draw Dropoffs (D1-D4)
            const dropoffs = layout.dropoff_zones || {};
            for (const [dname, pos] of Object.entries(dropoffs)) {
                const dx = pos[0] * cellW;
                const dy = (gridH - 1 - pos[1]) * cellH;
                ctx.fillStyle = 'rgba(5, 150, 105, 0.25)';
                ctx.fillRect(dx, dy, cellW, cellH);
                ctx.strokeStyle = '#059669';
                ctx.lineWidth = 1.5;
                ctx.strokeRect(dx, dy, cellW, cellH);

                ctx.fillStyle = '#34d399';
                ctx.font = 'bold 11px sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(dname, dx + cellW / 2, dy + cellH / 2);
            }

            // Draw Charging Docks
            const docks = layout.charging_docks || {};
            for (const [dname, pos] of Object.entries(docks)) {
                const kx = pos[0] * cellW;
                const ky = (gridH - 1 - pos[1]) * cellH;
                ctx.fillStyle = 'rgba(217, 119, 6, 0.2)';
                ctx.fillRect(kx, ky, cellW, cellH);
                ctx.strokeStyle = '#d97706';
                ctx.lineWidth = 1;
                ctx.strokeRect(kx, ky, cellW, cellH);

                ctx.fillStyle = '#fbbf24';
                ctx.font = 'bold 9px monospace';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(dname.replace('AMR-', 'D'), kx + cellW / 2, ky + cellH / 2);
            }

            // Draw Tasks / Packages
            (data.tasks || []).forEach(t => {
                if (t.status !== 'COMPLETED') {
                    const isPickedUp = (t.status === 'IN_PROGRESS' || t.status === 'PICKED_UP');
                    if (!isPickedUp && t.pickup_pos) {
                        const px = t.pickup_pos[0] * cellW;
                        const py = (gridH - 1 - t.pickup_pos[1]) * cellH;

                        ctx.fillStyle = 'rgba(245, 158, 11, 0.25)';
                        ctx.beginPath();
                        ctx.arc(px + cellW / 2, py + cellH / 2, cellR * 0.45, 0, Math.PI * 2);
                        ctx.fill();

                        ctx.fillStyle = '#b45309';
                        ctx.fillRect(px + cellW * 0.15, py + cellH * 0.15, cellW * 0.7, cellH * 0.7);
                        ctx.strokeStyle = '#fcd34d';
                        ctx.lineWidth = 1.5;
                        ctx.strokeRect(px + cellW * 0.15, py + cellH * 0.15, cellW * 0.7, cellH * 0.7);

                        ctx.fillStyle = '#fff';
                        ctx.font = 'bold 12px monospace';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillText('B', px + cellW / 2, py + cellH / 2);
                    }

                    if (t.dropoff_pos) {
                        const dx = t.dropoff_pos[0] * cellW;
                        const dy = (gridH - 1 - t.dropoff_pos[1]) * cellH;

                        ctx.strokeStyle = 'rgba(192, 132, 252, 0.8)';
                        ctx.lineWidth = 1.5;
                        ctx.setLineDash([2, 2]);
                        ctx.beginPath();
                        ctx.arc(dx + cellW / 2, dy + cellH / 2, cellR * 0.42, 0, Math.PI * 2);
                        ctx.stroke();
                        ctx.setLineDash([]);

                        ctx.fillStyle = '#c084fc';
                        ctx.font = 'bold 11px monospace';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillText('TD', dx + cellW / 2, dy + cellH / 2);
                    }
                }
            });

            // Draw Interactive Task Creation Candidate Markers
            if (selectedPickup) {
                const spx = selectedPickup[0] * cellW;
                const spy = (gridH - 1 - selectedPickup[1]) * cellH;

                ctx.fillStyle = 'rgba(56, 189, 248, 0.3)';
                ctx.beginPath();
                ctx.arc(spx + cellW / 2, spy + cellH / 2, cellR * 0.48, 0, Math.PI * 2);
                ctx.fill();

                ctx.fillStyle = '#0284c7';
                ctx.fillRect(spx + cellW * 0.15, spy + cellH * 0.15, cellW * 0.7, cellH * 0.7);
                ctx.strokeStyle = '#38bdf8';
                ctx.lineWidth = 2;
                ctx.strokeRect(spx + cellW * 0.15, spy + cellH * 0.15, cellW * 0.7, cellH * 0.7);

                ctx.fillStyle = '#fff';
                ctx.font = 'bold 12px monospace';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('B', spx + cellW / 2, spy + cellH / 2);
            }

            if (selectedDropoff) {
                const sdx = selectedDropoff[0] * cellW;
                const sdy = (gridH - 1 - selectedDropoff[1]) * cellH;

                ctx.fillStyle = 'rgba(192, 132, 252, 0.3)';
                ctx.beginPath();
                ctx.arc(sdx + cellW / 2, sdy + cellH / 2, cellR * 0.48, 0, Math.PI * 2);
                ctx.fill();

                ctx.strokeStyle = '#c084fc';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(sdx + cellW / 2, sdy + cellH / 2, cellR * 0.4, 0, Math.PI * 2);
                ctx.stroke();

                ctx.fillStyle = '#fff';
                ctx.font = 'bold 11px monospace';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('TD', sdx + cellW / 2, sdy + cellH / 2);
            }

            // Draw Hover Reticle during Task Creation Mode
            if (taskCreationMode && hoveredCell) {
                const hx = hoveredCell[0] * cellW;
                const hy = (gridH - 1 - hoveredCell[1]) * cellH;
                const isValid = isCellValidForTaskStep(hoveredCell[0], hoveredCell[1], taskCreationStep);

                if (isValid) {
                    ctx.fillStyle = taskCreationStep === 'PICKUP' ? 'rgba(56, 189, 248, 0.25)' : 'rgba(192, 132, 252, 0.25)';
                    ctx.fillRect(hx, hy, cellW, cellH);
                    ctx.strokeStyle = taskCreationStep === 'PICKUP' ? '#38bdf8' : '#c084fc';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(hx + 1, hy + 1, cellW - 2, cellH - 2);

                    ctx.fillStyle = '#fff';
                    ctx.font = 'bold 11px monospace';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(taskCreationStep === 'PICKUP' ? 'B' : 'TD', hx + cellW / 2, hy + cellH / 2);
                } else {
                    ctx.fillStyle = 'rgba(239, 68, 68, 0.25)';
                    ctx.fillRect(hx, hy, cellW, cellH);
                    ctx.strokeStyle = '#ef4444';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(hx + 1, hy + 1, cellW - 2, cellH - 2);

                    ctx.fillStyle = '#ef4444';
                    ctx.font = 'bold 12px monospace';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText('B', hx + cellW / 2, hy + cellH / 2);
                }
            }

            // Draw Hover Reticle during Obstacle Edit Mode
            if (obstacleEditMode && hoveredCell) {
                const hx = hoveredCell[0] * cellW;
                const hy = (gridH - 1 - hoveredCell[1]) * cellH;
                const gx = hoveredCell[0];
                const gy = hoveredCell[1];
                const isExistingObs = (data.dynamic_obstacles || []).some(o => o[0] === gx && o[1] === gy);
                const isAmrOnCell = (data.fleet || []).some(a => a.grid_pos[0] === gx && a.grid_pos[1] === gy);
                const isWalkable = isCellWalkableFloor(gx, gy);

                if (isExistingObs) {
                    // Hovering over existing dynamic obstacle -> REMOVE action
                    ctx.fillStyle = 'rgba(239, 68, 68, 0.35)';
                    ctx.fillRect(hx, hy, cellW, cellH);
                    ctx.strokeStyle = '#ef4444';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(hx + 1, hy + 1, cellW - 2, cellH - 2);

                    ctx.fillStyle = '#fff';
                    ctx.font = 'bold 10px sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText('REMOVE', hx + cellW / 2, hy + cellH / 2);
                } else if (isAmrOnCell) {
                    // Cannot place on active robot
                    ctx.fillStyle = 'rgba(239, 68, 68, 0.25)';
                    ctx.fillRect(hx, hy, cellW, cellH);
                    ctx.strokeStyle = '#ef4444';
                    ctx.lineWidth = 2;
                    ctx.setLineDash([2, 2]);
                    ctx.strokeRect(hx + 1, hy + 1, cellW - 2, cellH - 2);
                    ctx.setLineDash([]);

                    ctx.fillStyle = '#fca5a5';
                    ctx.font = 'bold 9px sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText('AMR HERE', hx + cellW / 2, hy + cellH / 2);
                } else if (isWalkable) {
                    // Valid floor cell -> ADD action
                    ctx.fillStyle = 'rgba(249, 115, 22, 0.3)';
                    ctx.fillRect(hx, hy, cellW, cellH);
                    ctx.strokeStyle = '#f97316';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(hx + 1, hy + 1, cellW - 2, cellH - 2);

                    ctx.fillStyle = '#fed7aa';
                    ctx.font = 'bold 10px sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText('+ BLOCK', hx + cellW / 2, hy + cellH / 2);
                } else {
                    // Invalid (shelf, wall, dock)
                    ctx.fillStyle = 'rgba(100, 116, 139, 0.2)';
                    ctx.fillRect(hx, hy, cellW, cellH);
                    ctx.strokeStyle = '#64748b';
                    ctx.lineWidth = 1;
                    ctx.strokeRect(hx + 1, hy + 1, cellW - 2, cellH - 2);
                }
            }

            // Draw Dynamic Obstacles
            (data.dynamic_obstacles || []).forEach(obs => {
                const ox = obs[0] * cellW;
                const oy = (gridH - 1 - obs[1]) * cellH;

                ctx.fillStyle = 'rgba(239, 68, 68, 0.25)';
                ctx.fillRect(ox + 1, oy + 1, cellW - 2, cellH - 2);
                ctx.strokeStyle = '#ef4444';
                ctx.lineWidth = 2;
                ctx.strokeRect(ox + 1, oy + 1, cellW - 2, cellH - 2);

                ctx.fillStyle = '#ef4444';
                ctx.font = 'bold 15px monospace';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('B', ox + cellW / 2, oy + cellH / 2);
            });

            // Draw Old Blocked Path Trail (Red Dotted Line)
            (data.fleet || []).forEach(amr => {
                const replan = amr.last_replan;
                if (replan && replan.old_path && replan.old_path.length > 1) {
                    ctx.strokeStyle = 'rgba(239, 68, 68, 0.5)';
                    ctx.lineWidth = 2;
                    ctx.setLineDash([3, 3]);
                    ctx.beginPath();
                    replan.old_path.forEach((pt, i) => {
                        const wx = (pt[0] + 0.5) * cellW;
                        const wy = (gridH - 1 - pt[1] + 0.5) * cellH;
                        if (i === 0) ctx.moveTo(wx, wy);
                        else ctx.lineTo(wx, wy);
                    });
                    ctx.stroke();
                    ctx.setLineDash([]);
                }
            });

            // Draw Active AMR Routes
            (data.fleet || []).forEach(amr => {
                const path = amr.full_path || [];
                if (path.length > 1) {
                    const theme = AMR_THEME[amr.robot_id] || { color: '#38bdf8' };
                    ctx.strokeStyle = theme.color;
                    ctx.lineWidth = selectedAmrId === amr.robot_id ? 3.5 : 1.8;
                    ctx.setLineDash([4, 3]);

                    ctx.beginPath();
                    path.forEach((pt, i) => {
                        const wx = (pt[0] + 0.5) * cellW;
                        const wy = (gridH - 1 - pt[1] + 0.5) * cellH;
                        if (i === 0) ctx.moveTo(wx, wy);
                        else ctx.lineTo(wx, wy);
                    });
                    ctx.stroke();
                    ctx.setLineDash([]);

                    path.forEach((pt, i) => {
                        if (i > 0) {
                            const wx = (pt[0] + 0.5) * cellW;
                            const wy = (gridH - 1 - pt[1] + 0.5) * cellH;
                            ctx.fillStyle = theme.color;
                            ctx.beginPath();
                            ctx.arc(wx, wy, 2.5, 0, Math.PI * 2);
                            ctx.fill();
                        }
                    });
                }
            });

            // Draw AMRs & Heading Pointers
            (data.fleet || []).forEach(amr => {
                const theme = AMR_THEME[amr.robot_id] || { color: '#38bdf8' };
                const cx = (amr.grid_pos[0] + 0.5) * cellW;
                const cy = (gridH - 1 - amr.grid_pos[1] + 0.5) * cellH;
                const isSelected = selectedAmrId === amr.robot_id;

                if (isSelected) {
                    ctx.strokeStyle = '#fff';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.arc(cx, cy, cellR * 0.52, 0, Math.PI * 2);
                    ctx.stroke();
                }

                // Chassis
                ctx.fillStyle = theme.color;
                ctx.beginPath();
                ctx.arc(cx, cy, cellR * 0.4, 0, Math.PI * 2);
                ctx.fill();

                ctx.fillStyle = '#0f172a';
                ctx.beginPath();
                ctx.arc(cx, cy, cellR * 0.28, 0, Math.PI * 2);
                ctx.fill();

                // Heading pointer arrow
                if (amr.yaw !== undefined) {
                    const arrowLen = cellR * 0.45;
                    const hx = cx + Math.cos(-amr.yaw) * arrowLen;
                    const hy = cy + Math.sin(-amr.yaw) * arrowLen;
                    ctx.strokeStyle = '#fff';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(cx, cy);
                    ctx.lineTo(hx, hy);
                    ctx.stroke();
                }

                // Carried payload
                if (amr.is_carrying_payload) {
                    const bw = cellR * 0.44;
                    const bh = cellR * 0.44;
                    ctx.fillStyle = '#b45309';
                    ctx.fillRect(cx - bw / 2, cy - bh / 2, bw, bh);
                    ctx.strokeStyle = '#fcd34d';
                    ctx.lineWidth = 1.5;
                    ctx.strokeRect(cx - bw / 2, cy - bh / 2, bw, bh);

                    ctx.fillStyle = '#fff';
                    ctx.font = 'bold 9px monospace';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText('B', cx, cy);
                } else {
                    ctx.fillStyle = '#fff';
                    ctx.font = 'bold 9px monospace';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(amr.robot_id.replace('AMR-', ''), cx, cy);
                }
            });
        }

        // Canvas Mouse Events
        const canvasEl = document.getElementById('warehouse-canvas');

        canvasEl.addEventListener('mousemove', (e) => {
            const rect = canvasEl.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const clickY = e.clientY - rect.top;

            const gridW = 24;
            const gridH = 16;
            const cellW = canvasEl.width / gridW;
            const cellH = canvasEl.height / gridH;

            const gx = Math.floor(clickX / cellW);
            const gy = gridH - 1 - Math.floor(clickY / cellH);

            if (!hoveredCell || hoveredCell[0] !== gx || hoveredCell[1] !== gy) {
                hoveredCell = [gx, gy];
                if ((taskCreationMode || obstacleEditMode) && currentSnapshot) {
                    drawMap(currentSnapshot);
                }
            }
        });

        canvasEl.addEventListener('mouseleave', () => {
            if (hoveredCell) {
                hoveredCell = null;
                if ((taskCreationMode || obstacleEditMode) && currentSnapshot) {
                    drawMap(currentSnapshot);
                }
            }
        });

        canvasEl.addEventListener('click', (e) => {
            const rect = canvasEl.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const clickY = e.clientY - rect.top;

            const gridW = 24;
            const gridH = 16;
            const cellW = canvasEl.width / gridW;
            const cellH = canvasEl.height / gridH;

            const gx = Math.floor(clickX / cellW);
            const gy = gridH - 1 - Math.floor(clickY / cellH);

            // 1. Obstacle Edit Mode Click
            if (obstacleEditMode) {
                const isExistingObs = (currentSnapshot && currentSnapshot.dynamic_obstacles || []).some(o => o[0] === gx && o[1] === gy);
                const isAmrOnCell = (currentSnapshot && currentSnapshot.fleet || []).some(a => a.grid_pos[0] === gx && a.grid_pos[1] === gy);

                if (isExistingObs) {
                    sendControl('remove_obstacle', { cell: [gx, gy] });
                } else if (isAmrOnCell) {
                    const helpBar = document.getElementById('obstacle-help-bar');
                    if (helpBar) {
                        helpBar.innerHTML = `<strong style="color:#ef4444;">Warning:</strong> Cannot place obstacle directly on an active AMR at (${gx}, ${gy})!`;
                        setTimeout(() => {
                            if (helpBar && obstacleEditMode) {
                                helpBar.innerHTML = '<strong>Obstacle Editor Active:</strong> Click any <span style="color: #38bdf8; font-weight: 700;">walkable aisle cell</span> to place a dynamic blockage, or click an <span style="color: #ef4444; font-weight: 700;">existing red blocked cell</span> to remove it. AMRs will detect obstacles and replan dynamically!';
                            }
                        }, 2500);
                    }
                } else if (isCellWalkableFloor(gx, gy)) {
                    sendControl('add_obstacle', { cell: [gx, gy] });
                }
                return;
            }

            // 2. Task Creation Mode Click
            if (taskCreationMode) {
                if (taskCreationStep === 'PICKUP') {
                    if (isCellValidForTaskStep(gx, gy, 'PICKUP')) {
                        selectedPickup = [gx, gy];
                        document.getElementById('tag-pickup-coord').innerHTML = `Source [B]: <strong style="color: #34d399;">(${gx}, ${gy})</strong>`;
                        setTaskCreationStep('DROPOFF');
                    }
                } else if (taskCreationStep === 'DROPOFF') {
                    if (isCellValidForTaskStep(gx, gy, 'DROPOFF')) {
                        selectedDropoff = [gx, gy];
                        document.getElementById('tag-dropoff-coord').innerHTML = `Destination [TD]: <strong style="color: #c084fc;">(${gx}, ${gy})</strong>`;
                        
                        const assignBtn = document.getElementById('btn-assign-task');
                        assignBtn.disabled = false;
                        assignBtn.style.opacity = '1.0';
                        assignBtn.style.cursor = 'pointer';
                    }
                }
                if (currentSnapshot) drawMap(currentSnapshot);
                return;
            }

            // 3. Normal AMR selection click
            if (currentSnapshot && currentSnapshot.fleet) {
                const clickedAmr = currentSnapshot.fleet.find(a => a.grid_pos[0] === gx && a.grid_pos[1] === gy);
                if (clickedAmr) {
                    selectAmr(clickedAmr.robot_id);
                }
            }
        });

        // Initialize polling loop
        setInterval(fetchState, 100);
        fetchState();
    </script>
</body>
</html>
"""

class WebDashboardHandler(http.server.BaseHTTPRequestHandler):
    dashboard_instance: Optional[Any] = None
    sim_instance: Optional[Any] = None

    def log_message(self, format, *args):
        # Suppress noisy HTTP request terminal logs
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
        elif parsed.path == "/api/state":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if self.dashboard_instance:
                state_data = self.dashboard_instance.get_full_state_snapshot()
            else:
                state_data = {"system": {}, "fleet": []}
            self.wfile.write(json.dumps(state_data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/control":
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                action = data.get("action", "")
                params = data.get("params", {})
                success = False
                if self.sim_instance:
                    success = self.sim_instance.post_command(action, params)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": success, "queued": True, "action": action}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


class WebDashboardServer:
    def __init__(self, dashboard, sim_instance=None, port: int = 8080):
        self.dashboard = dashboard
        self.sim_instance = sim_instance
        self.port = port
        self.httpd: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        try:
            handler = WebDashboardHandler
            handler.dashboard_instance = self.dashboard
            handler.sim_instance = self.sim_instance
            socketserver.TCPServer.allow_reuse_address = True
            self.httpd = socketserver.TCPServer(("", self.port), handler)
            self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.thread.start()
            return True
        except Exception:
            try:
                self.port = 8081
                self.httpd = socketserver.TCPServer(("", self.port), handler)
                self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
                self.thread.start()
                return True
            except Exception:
                return False

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()

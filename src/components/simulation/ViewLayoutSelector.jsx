import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useSimulation, ViewMode, ConnectionStatus } from '../../context/SimulationContext';
import {
  LayoutGrid,
  Map,
  Bot,
  Layers,
  Terminal,
  Sliders,
  Columns,
  Wifi,
  WifiOff,
  Settings,
  Check,
  RotateCcw,
  X,
  Radio,
  Server,
  Activity,
  Clock,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react';

const VIEW_OPTIONS = [
  { id: ViewMode.COMMAND_HUB, label: 'COMMAND', icon: LayoutGrid },
  { id: ViewMode.MAP_2D, label: 'MAP 2D', icon: Map },
  { id: ViewMode.FLEET_MATRIX, label: 'FLEET', icon: Bot },
  { id: ViewMode.TASKS_AUCTIONS, label: 'TASKS', icon: Layers },
  { id: ViewMode.EVENT_STREAM, label: 'LOGS', icon: Terminal },
  { id: ViewMode.SCENARIO_CONTROLS, label: 'SCENARIOS', icon: Sliders },
  { id: ViewMode.SPLIT_VIEW, label: 'SPLIT', icon: Columns },
];

export default function ViewLayoutSelector() {
  const {
    activeView,
    setActiveView,
    splitLeftView,
    setSplitLeftView,
    splitRightView,
    setSplitRightView,
    connectionStatus,
    apiUrl,
    updateApiUrl,
    resetApiUrl,
    simulationData,
  } = useSimulation();

  const [showSettings, setShowSettings] = useState(false);
  const [customUrlInput, setCustomUrlInput] = useState(apiUrl);

  const sys = simulationData?.system || {};
  const isConnected = connectionStatus === ConnectionStatus.CONNECTED;

  // Sync input when apiUrl changes
  useEffect(() => {
    setCustomUrlInput(apiUrl);
  }, [apiUrl]);

  // Handle escape key to close settings modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && showSettings) {
        setShowSettings(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showSettings]);

  const handleOpenSettings = () => {
    setCustomUrlInput(apiUrl);
    setShowSettings(true);
  };

  const handleCloseSettings = () => {
    setShowSettings(false);
  };

  const handleSaveUrl = (e) => {
    e.preventDefault();
    if (customUrlInput && customUrlInput.trim()) {
      updateApiUrl(customUrlInput.trim());
      setShowSettings(false);
    }
  };

  const handleResetUrl = () => {
    resetApiUrl();
    setShowSettings(false);
  };

  // Render Settings Modal in Portal attached directly to document.body
  const settingsModal = showSettings && typeof document !== 'undefined'
    ? createPortal(
        <div
          className="settings-modal-backdrop"
          onClick={handleCloseSettings}
          role="dialog"
          aria-modal="true"
          aria-labelledby="settings-dialog-title"
        >
          <div
            className="settings-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="settings-modal-header">
              <div className="settings-modal-title-group">
                <div className="settings-icon-bubble">
                  <Server size={18} color="var(--accent-cyan)" />
                </div>
                <div>
                  <h3 id="settings-dialog-title" className="settings-modal-title">
                    Backend Host Connection
                  </h3>
                  <p className="settings-modal-subtitle">
                    Configure simulation API endpoint for LAN or Localhost
                  </p>
                </div>
              </div>
              <button
                type="button"
                className="settings-modal-close-btn"
                onClick={handleCloseSettings}
                aria-label="Close Settings"
              >
                <X size={18} />
              </button>
            </div>

            {/* Live Connection Status Strip */}
            <div className="settings-status-strip">
              <div className="settings-status-label">Current Status:</div>
              <div
                className={`conn-status-pill ${
                  connectionStatus === ConnectionStatus.CONNECTED
                    ? 'connected'
                    : connectionStatus === ConnectionStatus.CONNECTING
                    ? 'connecting'
                    : 'disconnected'
                }`}
              >
                {connectionStatus === ConnectionStatus.CONNECTED ? (
                  <Wifi size={12} />
                ) : (
                  <WifiOff size={12} />
                )}
                <span>{connectionStatus}</span>
              </div>
            </div>

            {/* Settings Form */}
            <form onSubmit={handleSaveUrl} className="settings-modal-form">
              <div className="settings-field-group">
                <label htmlFor="backend-url-input" className="settings-input-label">
                  Simulation Backend URL (REST API / 0.0.0.0:8080):
                </label>
                <div className="settings-input-wrap">
                  <Radio size={14} className="input-adornment-icon" />
                  <input
                    id="backend-url-input"
                    type="text"
                    className="settings-text-input"
                    value={customUrlInput}
                    onChange={(e) => setCustomUrlInput(e.target.value)}
                    placeholder="http://192.168.1.50:8080"
                    autoFocus
                  />
                </div>
                <div className="settings-help-text">
                  For multi-laptop hackathon deployment, enter the Host Laptop's LAN IP address (e.g. <code>http://192.168.1.X:8080</code>).
                </div>
              </div>

              {/* Action Buttons */}
              <div className="settings-modal-actions">
                <button
                  type="button"
                  className="btn-reset-endpoint"
                  onClick={handleResetUrl}
                  title="Reset to default environment endpoint"
                >
                  <RotateCcw size={13} />
                  <span>Restore Default</span>
                </button>

                <div className="settings-primary-actions">
                  <button
                    type="button"
                    className="btn-cancel-settings"
                    onClick={handleCloseSettings}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn-save-endpoint"
                  >
                    <Check size={14} />
                    <span>Save &amp; Connect</span>
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )
    : null;

  return (
    <>
      <div className="ops-command-bar">
        {/* Left: Brand Identity & Live Status */}
        <div className="ops-bar-left">
          <div className="ops-brand-badge">
            <span className="ops-pulse-dot" />
            <span className="ops-system-name">ROBOSYNC // OPERATIONS</span>
          </div>

          <div className="ops-telemetry-strip">
            <div className="ops-stat-item">
              <span className="ops-stat-k">TIME</span>
              <span className="ops-stat-v mono">{sys.sim_time !== undefined ? `${sys.sim_time.toFixed(1)}s` : '0.0s'}</span>
            </div>

            <div className="ops-stat-divider" />

            <div className="ops-stat-item">
              <span className="ops-stat-k">FLEET</span>
              <span className="ops-stat-v mono cyan">{sys.active_amrs || (isConnected ? 6 : 0)}/6 ACTIVE</span>
            </div>

            <div className="ops-stat-divider" />

            <div className="ops-stat-item">
              <span className="ops-stat-k">TASKS</span>
              <span className="ops-stat-v mono">{sys.tasks_active !== undefined ? sys.tasks_active : 0} IN-FLIGHT</span>
            </div>

            <div className="ops-stat-divider" />

            <div className="ops-stat-item">
              <span className="ops-stat-k">SAFETY</span>
              <span className="ops-stat-v mono green">0 PENETRATIONS</span>
            </div>
          </div>
        </div>

        {/* Center/Right: View Switching Workstation Toolbar */}
        <div className="ops-bar-right">
          <div className="view-mode-tabs">
            {VIEW_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              const isActive = activeView === opt.id;
              return (
                <button
                  key={opt.id}
                  className={`view-mode-tab-btn ${isActive ? 'active' : ''}`}
                  onClick={() => setActiveView(opt.id)}
                >
                  <Icon size={13} />
                  <span>{opt.label}</span>
                </button>
              );
            })}
          </div>

          {/* Split View Selectors if active */}
          {activeView === ViewMode.SPLIT_VIEW && (
            <div className="split-view-controls">
              <div className="split-select-group">
                <span className="split-label">L:</span>
                <select
                  className="split-select"
                  value={splitLeftView}
                  onChange={(e) => setSplitLeftView(e.target.value)}
                >
                  <option value={ViewMode.MAP_2D}>2D MAP</option>
                  <option value={ViewMode.FLEET_MATRIX}>FLEET</option>
                  <option value={ViewMode.TASKS_AUCTIONS}>TASKS</option>
                  <option value={ViewMode.EVENT_STREAM}>LOGS</option>
                  <option value={ViewMode.SCENARIO_CONTROLS}>SCENARIOS</option>
                </select>
              </div>

              <div className="split-select-group">
                <span className="split-label">R:</span>
                <select
                  className="split-select"
                  value={splitRightView}
                  onChange={(e) => setSplitRightView(e.target.value)}
                >
                  <option value={ViewMode.FLEET_MATRIX}>FLEET</option>
                  <option value={ViewMode.MAP_2D}>2D MAP</option>
                  <option value={ViewMode.TASKS_AUCTIONS}>TASKS</option>
                  <option value={ViewMode.EVENT_STREAM}>LOGS</option>
                  <option value={ViewMode.SCENARIO_CONTROLS}>SCENARIOS</option>
                </select>
              </div>
            </div>
          )}

          {/* Connection Status & Host Config Button */}
          <div className="ops-conn-cluster">
            <div
              className={`conn-status-pill ${
                connectionStatus === ConnectionStatus.CONNECTED
                  ? 'connected'
                  : connectionStatus === ConnectionStatus.CONNECTING
                  ? 'connecting'
                  : 'disconnected'
              }`}
              title={`Backend Host: ${apiUrl}`}
            >
              {connectionStatus === ConnectionStatus.CONNECTED ? (
                <Wifi size={11} />
              ) : (
                <WifiOff size={11} />
              )}
              <span>{connectionStatus}</span>
            </div>

            <button
              type="button"
              className="btn-settings-toggle"
              onClick={handleOpenSettings}
              title="Configure Simulation Backend Host / IP"
              aria-label="Open Connection Settings"
            >
              <Settings size={13} />
            </button>
          </div>
        </div>
      </div>

      {/* Top-Level Portal Render */}
      {settingsModal}
    </>
  );
}

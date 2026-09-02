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
} from 'lucide-react';

const VIEW_OPTIONS = [
  { id: ViewMode.COMMAND_HUB, label: 'Command Hub', icon: LayoutGrid },
  { id: ViewMode.MAP_2D, label: '2D Map', icon: Map },
  { id: ViewMode.FLEET_MATRIX, label: 'Fleet Telemetry', icon: Bot },
  { id: ViewMode.TASKS_AUCTIONS, label: 'Task Auctions', icon: Layers },
  { id: ViewMode.EVENT_STREAM, label: 'Event Logs', icon: Terminal },
  { id: ViewMode.SCENARIO_CONTROLS, label: 'Scenarios', icon: Sliders },
  { id: ViewMode.SPLIT_VIEW, label: 'Split View', icon: Columns },
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
  } = useSimulation();

  const [showSettings, setShowSettings] = useState(false);
  const [customUrlInput, setCustomUrlInput] = useState(apiUrl);

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
      <div className="view-selector-toolbar">
        {/* Left: View Switching Tabs */}
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
                <Icon size={14} />
                <span>{opt.label}</span>
              </button>
            );
          })}
        </div>

        {/* Center: Split View Selectors if active */}
        {activeView === ViewMode.SPLIT_VIEW && (
          <div className="split-view-controls">
            <div className="split-select-group">
              <span className="split-label">Left:</span>
              <select
                className="split-select"
                value={splitLeftView}
                onChange={(e) => setSplitLeftView(e.target.value)}
              >
                <option value={ViewMode.MAP_2D}>2D Warehouse Map</option>
                <option value={ViewMode.FLEET_MATRIX}>Fleet Telemetry</option>
                <option value={ViewMode.TASKS_AUCTIONS}>Task Auctions</option>
                <option value={ViewMode.EVENT_STREAM}>Event Logs</option>
                <option value={ViewMode.SCENARIO_CONTROLS}>Scenario Controls</option>
              </select>
            </div>

            <div className="split-select-group">
              <span className="split-label">Right:</span>
              <select
                className="split-select"
                value={splitRightView}
                onChange={(e) => setSplitRightView(e.target.value)}
              >
                <option value={ViewMode.FLEET_MATRIX}>Fleet Telemetry</option>
                <option value={ViewMode.MAP_2D}>2D Warehouse Map</option>
                <option value={ViewMode.TASKS_AUCTIONS}>Task Auctions</option>
                <option value={ViewMode.EVENT_STREAM}>Event Logs</option>
                <option value={ViewMode.SCENARIO_CONTROLS}>Scenario Controls</option>
              </select>
            </div>
          </div>
        )}

        {/* Right: Backend Connection Status & Host Config Button */}
        <div className="connection-status-cluster">
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
              <Wifi size={12} />
            ) : (
              <WifiOff size={12} />
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
            <Settings size={14} />
          </button>
        </div>
      </div>

      {/* Top-Level Portal Render */}
      {settingsModal}
    </>
  );
}

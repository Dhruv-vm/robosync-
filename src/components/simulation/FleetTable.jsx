import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Bot, Battery, Navigation, Activity, ArrowRight, Zap } from 'lucide-react';

const AMR_THEME = {
  'AMR-1': { color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.12)', border: '#38bdf8' },
  'AMR-2': { color: '#f87171', bg: 'rgba(248, 113, 113, 0.12)', border: '#f87171' },
  'AMR-3': { color: '#4ade80', bg: 'rgba(74, 222, 128, 0.12)', border: '#4ade80' },
  'AMR-4': { color: '#facc15', bg: 'rgba(250, 204, 21, 0.12)', border: '#facc15' },
  'AMR-5': { color: '#c084fc', bg: 'rgba(192, 132, 252, 0.12)', border: '#c084fc' },
  'AMR-6': { color: '#2dd4bf', bg: 'rgba(45, 212, 191, 0.12)', border: '#2dd4bf' },
};

export default function FleetTable() {
  const { simulationData, selectedAmrId, setSelectedAmrId } = useSimulation();
  const fleet = simulationData?.fleet || [];

  return (
    <div className="fleet-ops-panel">
      {/* Panel Header */}
      <div className="fleet-panel-header">
        <div className="fleet-panel-title-wrap">
          <Bot size={14} color="var(--accent-cyan)" />
          <span className="fleet-panel-title">FLEET OPERATIONS // TACTICAL STATUS</span>
        </div>
        <div className="fleet-count-tag">
          <span className="fleet-active-dot" />
          <span>{fleet.length} ONBOARD AGENTS</span>
        </div>
      </div>

      {/* Fleet Unit Rows */}
      <div className="fleet-units-list">
        {fleet.length === 0 ? (
          <div className="fleet-empty-state">
            <Activity size={18} className="spin-icon" color="var(--accent-cyan)" />
            <span>Connecting to onboard telemetry telemetry bus...</span>
          </div>
        ) : (
          fleet.map((amr) => {
            const theme = AMR_THEME[amr.robot_id] || { color: '#ffffff', bg: 'rgba(255,255,255,0.1)', border: '#ffffff' };
            const isSelected = selectedAmrId === amr.robot_id;
            const batteryColor =
              amr.battery > 50 ? '#10b981' : amr.battery > 25 ? '#f59e0b' : '#ef4444';
            
            const isCarrying = amr.is_carrying_payload;
            const isFailed = amr.status === 'FAILED';

            return (
              <div
                key={amr.robot_id}
                className={`fleet-unit-card ${isSelected ? 'selected' : ''} ${isFailed ? 'failed' : ''}`}
                onClick={() => setSelectedAmrId(amr.robot_id)}
                title="Click to open deep telemetry inspector"
              >
                {/* Unit ID Badge & Payload Indicator */}
                <div className="unit-card-left">
                  <div
                    className="unit-id-badge"
                    style={{
                      color: theme.color,
                      backgroundColor: theme.bg,
                      borderColor: `${theme.color}40`,
                    }}
                  >
                    <span className="unit-beacon-dot" style={{ backgroundColor: theme.color }} />
                    <span className="unit-name">{amr.robot_id}</span>
                  </div>

                  {isCarrying && (
                    <span className="unit-payload-chip" title="Carrying Logistics Cargo">
                      CARGO [B]
                    </span>
                  )}
                </div>

                {/* Status & Mission Info */}
                <div className="unit-card-mid">
                  <div className="unit-status-row">
                    <span
                      className={`unit-status-pill ${isFailed ? 'failed-pill' : ''}`}
                      style={{ color: isFailed ? '#ef4444' : theme.color }}
                    >
                      {amr.status}
                    </span>
                    <span className="unit-mission-tag">
                      {amr.task_id && amr.task_id !== 'IDLE' ? amr.task_id : 'STANDBY'}
                    </span>
                  </div>

                  <div className="unit-coords-row">
                    <span className="unit-coord-label">POS:</span>
                    <span className="unit-coord-val mono">
                      ({amr.grid_pos?.[0] ?? 0}, {amr.grid_pos?.[1] ?? 0})
                    </span>
                    {amr.target_goal && (
                      <>
                        <ArrowRight size={10} className="coord-arrow" />
                        <span className="unit-goal-val mono">
                          ({amr.target_goal[0]}, {amr.target_goal[1]})
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Battery & Route State */}
                <div className="unit-card-right">
                  <div className="unit-battery-group">
                    <div className="unit-battery-header">
                      <span className="battery-pct-label" style={{ color: batteryColor }}>
                        {amr.battery}%
                      </span>
                    </div>
                    <div className="unit-battery-track">
                      <div
                        className="unit-battery-fill"
                        style={{
                          width: `${Math.max(0, Math.min(100, amr.battery))}%`,
                          backgroundColor: batteryColor,
                        }}
                      />
                    </div>
                  </div>

                  <div className="unit-route-badge">
                    <span className="route-dot" />
                    <span className="route-state-txt">
                      {amr.planning_status || 'Idle'}
                      {amr.path_length ? ` (${amr.path_length}w)` : ''}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

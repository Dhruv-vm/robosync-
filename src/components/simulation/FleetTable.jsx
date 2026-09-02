import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Bot, Battery, Navigation, Activity } from 'lucide-react';

const AMR_THEME = {
  'AMR-1': { color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.12)' },
  'AMR-2': { color: '#f87171', bg: 'rgba(248, 113, 113, 0.12)' },
  'AMR-3': { color: '#4ade80', bg: 'rgba(74, 222, 128, 0.12)' },
  'AMR-4': { color: '#facc15', bg: 'rgba(250, 204, 21, 0.12)' },
  'AMR-5': { color: '#c084fc', bg: 'rgba(192, 132, 252, 0.12)' },
  'AMR-6': { color: '#2dd4bf', bg: 'rgba(45, 212, 191, 0.12)' },
};

export default function FleetTable() {
  const { simulationData, selectedAmrId, setSelectedAmrId } = useSimulation();
  const fleet = simulationData?.fleet || [];

  return (
    <div className="simulation-panel-card">
      <div className="sim-panel-header">
        <div className="sim-panel-title">
          <Bot size={15} color="var(--accent-cyan)" />
          <span>Fleet Telemetry &amp; Local A* Planners</span>
        </div>
        <div className="sim-panel-badge">
          {fleet.length} AMRs Active
        </div>
      </div>

      <div className="fleet-table-container">
        <table className="fleet-matrix-table">
          <thead>
            <tr>
              <th>AMR Unit</th>
              <th>Status</th>
              <th>Active Mission</th>
              <th>Battery</th>
              <th>A* Route Status</th>
            </tr>
          </thead>
          <tbody>
            {fleet.length === 0 ? (
              <tr>
                <td colSpan={5} className="empty-table-cell">
                  Waiting for live telemetry from simulation backend...
                </td>
              </tr>
            ) : (
              fleet.map((amr) => {
                const theme = AMR_THEME[amr.robot_id] || { color: '#ffffff', bg: 'rgba(255,255,255,0.1)' };
                const isSelected = selectedAmrId === amr.robot_id;
                const batteryColor =
                  amr.battery > 50 ? '#10b981' : amr.battery > 25 ? '#f59e0b' : '#ef4444';

                return (
                  <tr
                    key={amr.robot_id}
                    className={`fleet-row ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedAmrId(amr.robot_id)}
                  >
                    <td>
                      <div
                        className="robot-chip-badge"
                        style={{ background: theme.bg, color: theme.color, borderColor: `${theme.color}40` }}
                      >
                        <span className="chip-dot" style={{ backgroundColor: theme.color }} />
                        <span>{amr.robot_id}</span>
                      </div>
                    </td>
                    <td>
                      <span
                        className="status-pill-badge"
                        style={{ color: amr.status === 'FAILED' ? '#ef4444' : theme.color }}
                      >
                        {amr.status}
                      </span>
                    </td>
                    <td className="mono-cell">
                      {amr.task_id || 'IDLE'}
                    </td>
                    <td className="battery-cell">
                      <div className="battery-val" style={{ color: batteryColor }}>
                        {amr.battery}%
                      </div>
                      <div className="battery-track-bar">
                        <div
                          className="battery-fill-bar"
                          style={{ width: `${Math.max(0, Math.min(100, amr.battery))}%`, backgroundColor: batteryColor }}
                        />
                      </div>
                    </td>
                    <td className="route-cell">
                      <span className="route-status-tag">
                        {amr.planning_status || 'Idle'}
                      </span>
                      {amr.target_goal && (
                        <span className="goal-subtext"> &rarr; ({amr.target_goal[0]}, {amr.target_goal[1]})</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

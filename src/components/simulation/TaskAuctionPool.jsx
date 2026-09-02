import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Layers, ArrowRight, CheckCircle2, Clock, Package } from 'lucide-react';

const AMR_THEME = {
  'AMR-1': '#38bdf8',
  'AMR-2': '#f87171',
  'AMR-3': '#4ade80',
  'AMR-4': '#facc15',
  'AMR-5': '#c084fc',
  'AMR-6': '#2dd4bf',
};

export default function TaskAuctionPool() {
  const { simulationData } = useSimulation();
  const tasks = simulationData?.tasks || [];

  return (
    <div className="ops-panel-section">
      <div className="ops-panel-header">
        <div className="ops-panel-title-wrap">
          <Package size={14} color="var(--accent-cyan)" />
          <span className="ops-panel-title">MISSION POOL // CONTRACT NET BIDDING</span>
        </div>
        <div className="ops-panel-count">
          {tasks.length} LOGISTICS ORDERS
        </div>
      </div>

      <div className="task-auction-manifest">
        {tasks.length === 0 ? (
          <div className="ops-empty-log">No active logistics missions in bidding pool</div>
        ) : (
          tasks.map((t) => {
            const assignedColor = t.assigned_to ? (AMR_THEME[t.assigned_to] || '#38bdf8') : '#c084fc';
            
            let statusColor = '#f59e0b';
            let statusBg = 'rgba(245, 158, 11, 0.12)';
            let statusLabel = t.status;

            if (t.status === 'COMPLETED') {
              statusColor = '#10b981';
              statusBg = 'rgba(16, 185, 129, 0.12)';
              statusLabel = 'DELIVERED';
            } else if (t.status === 'IN_PROGRESS' || t.status === 'PICKED_UP') {
              statusColor = '#38bdf8';
              statusBg = 'rgba(56, 189, 248, 0.12)';
              statusLabel = 'IN TRANSIT';
            } else if (t.status === 'ASSIGNED') {
              statusColor = '#facc15';
              statusBg = 'rgba(250, 204, 21, 0.12)';
              statusLabel = 'DISPATCHED';
            }

            return (
              <div key={t.task_id} className="task-manifest-card">
                <div className="task-card-left">
                  <div className="task-id-tag mono">{t.task_id}</div>
                  <div className="task-routing-info">
                    <span className="routing-point">P: {t.pickup_zone}</span>
                    <ArrowRight size={10} className="routing-arrow" />
                    <span className="routing-point">D: {t.dropoff_zone}</span>
                    {t.priority > 1.0 && (
                      <span className="priority-pill">PRIORITY {t.priority}</span>
                    )}
                  </div>
                </div>

                <div className="task-card-right">
                  <div className="task-winner-tag" style={{ color: assignedColor }}>
                    {t.assigned_to ? `WINNER: ${t.assigned_to}` : 'AUCTIONING'}
                  </div>
                  <div
                    className="task-state-badge"
                    style={{ backgroundColor: statusBg, color: statusColor, borderColor: `${statusColor}40` }}
                  >
                    {statusLabel}
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

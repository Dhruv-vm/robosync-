import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Layers, ArrowRight, CheckCircle2, Clock } from 'lucide-react';

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
    <div className="simulation-panel-card">
      <div className="sim-panel-header">
        <div className="sim-panel-title">
          <Layers size={15} color="var(--accent-cyan)" />
          <span>Decentralized Task Auction Pool</span>
        </div>
        <div className="sim-panel-badge">
          {tasks.length} Missions
        </div>
      </div>

      <div className="task-auction-container">
        {tasks.length === 0 ? (
          <div className="empty-panel-state">No active logistics tasks in pool</div>
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
              <div key={t.task_id} className="task-order-item">
                <div className="task-left-meta">
                  <div className="task-id-badge">{t.task_id}</div>
                  <div className="task-route-desc">
                    <span>Pickup {t.pickup_zone} {t.pickup_pos ? `(${t.pickup_pos.join(',')})` : ''}</span>
                    <ArrowRight size={11} className="route-arrow" />
                    <span>Drop {t.dropoff_zone} {t.dropoff_pos ? `(${t.dropoff_pos.join(',')})` : ''}</span>
                  </div>
                </div>

                <div className="task-right-meta">
                  <div className="assigned-bidder" style={{ color: assignedColor }}>
                    {t.assigned_to ? `Winner: ${t.assigned_to}` : 'AUCTIONING'}
                  </div>
                  <div
                    className="task-status-pill"
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

import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { X, Cpu, Navigation, Activity, Battery, MapPin, Compass, ShieldCheck } from 'lucide-react';

const AMR_THEME = {
  'AMR-1': '#38bdf8',
  'AMR-2': '#f87171',
  'AMR-3': '#4ade80',
  'AMR-4': '#facc15',
  'AMR-5': '#c084fc',
  'AMR-6': '#2dd4bf',
};

export default function AmrInspectorDrawer() {
  const { selectedAmrId, selectedAmr, setSelectedAmrId } = useSimulation();

  if (!selectedAmrId || !selectedAmr) return null;

  const color = AMR_THEME[selectedAmr.robot_id] || '#38bdf8';
  const astar = selectedAmr.astar_metrics || {};
  const isFailed = selectedAmr.status === 'FAILED';

  return (
    <div className="amr-inspector-backdrop" onClick={() => setSelectedAmrId(null)}>
      <div className="amr-inspector-drawer" onClick={(e) => e.stopPropagation()}>
        {/* Drawer Header */}
        <div className="drawer-header">
          <div className="drawer-title-group">
            <span className="drawer-dot" style={{ backgroundColor: color }} />
            <h3 style={{ color }} className="mono">{selectedAmr.robot_id} // DEEP TELEMETRY</h3>
          </div>
          <button className="drawer-close-btn" onClick={() => setSelectedAmrId(null)} aria-label="Close Inspector">
            <X size={15} />
          </button>
        </div>

        {/* Status & Mission Section */}
        <div className="drawer-section">
          <div className="drawer-section-heading">OPERATIONAL STATE</div>
          <div className="drawer-row">
            <span className="drawer-key">STATUS</span>
            <span className="drawer-val mono" style={{ color: isFailed ? '#ef4444' : color }}>
              {selectedAmr.status}
            </span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">ACTIVE MISSION</span>
            <span className="drawer-val mono">{selectedAmr.task_id || 'STANDBY / IDLE'}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">GRID COORD</span>
            <span className="drawer-val mono">({selectedAmr.grid_pos?.[0]}, {selectedAmr.grid_pos?.[1]})</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">WORLD XYZ</span>
            <span className="drawer-val mono">
              ({selectedAmr.world_pos?.[0]?.toFixed(2)}, {selectedAmr.world_pos?.[1]?.toFixed(2)})
            </span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">HEADING (YAW)</span>
            <span className="drawer-val mono">{selectedAmr.yaw?.toFixed(3)} rad</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">TARGET GOAL</span>
            <span className="drawer-val mono">{selectedAmr.goal_desc || '-'}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">BATTERY SOC</span>
            <span className="drawer-val mono" style={{ color: '#10b981' }}>{selectedAmr.battery}%</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">COMPLETED MISSIONS</span>
            <span className="drawer-val mono">{selectedAmr.completed_tasks || 0}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">ODOMETRY</span>
            <span className="drawer-val mono">{selectedAmr.total_distance?.toFixed(1)} m</span>
          </div>
        </div>

        {/* Onboard A* Planner Telemetry */}
        <div className="drawer-section">
          <div className="drawer-section-heading">
            <Cpu size={12} color="var(--accent-cyan)" />
            <span>ONBOARD A* PATH PLANNER</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">PLANNER STATE</span>
            <span className="drawer-val mono">{astar.planning_status || 'Ready'}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">COMPUTE TIME</span>
            <span className="drawer-val mono cyan">
              {astar.planning_time_ms || 0} ms
            </span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">NODES EXPLORED</span>
            <span className="drawer-val mono purple">
              {astar.nodes_explored || 0} nodes
            </span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">WAYPOINTS</span>
            <span className="drawer-val mono">{astar.path_length || selectedAmr.path_length || 0} steps</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">PATH COST</span>
            <span className="drawer-val mono cyan">{astar.path_cost || 0}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">LIFETIME RE-ROUTES</span>
            <span className="drawer-val mono yellow">{astar.replan_count || 0}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

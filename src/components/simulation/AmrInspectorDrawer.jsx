import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { X, Cpu, Navigation, Activity, Battery, MapPin, Compass } from 'lucide-react';

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

  return (
    <div className="amr-inspector-backdrop" onClick={() => setSelectedAmrId(null)}>
      <div className="amr-inspector-drawer" onClick={(e) => e.stopPropagation()}>
        {/* Drawer Header */}
        <div className="drawer-header">
          <div className="drawer-title-group">
            <span className="drawer-dot" style={{ backgroundColor: color }} />
            <h3 style={{ color }}>{selectedAmr.robot_id} TELEMETRY</h3>
          </div>
          <button className="drawer-close-btn" onClick={() => setSelectedAmrId(null)}>
            <X size={16} />
          </button>
        </div>

        {/* Status & Mission Section */}
        <div className="drawer-section">
          <div className="drawer-row">
            <span className="drawer-key">Mission Status</span>
            <span className="drawer-val" style={{ color }}>{selectedAmr.status}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">Active Task ID</span>
            <span className="drawer-val mono">{selectedAmr.task_id || 'IDLE'}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">Grid Coordinates</span>
            <span className="drawer-val mono">({selectedAmr.grid_pos?.[0]}, {selectedAmr.grid_pos?.[1]})</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">World Coordinates</span>
            <span className="drawer-val mono">
              ({selectedAmr.world_pos?.[0]?.toFixed(2)}, {selectedAmr.world_pos?.[1]?.toFixed(2)})
            </span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">Heading (Yaw)</span>
            <span className="drawer-val mono">{selectedAmr.yaw?.toFixed(3)} rad</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">Target Destination</span>
            <span className="drawer-val mono">{selectedAmr.goal_desc || '-'}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">Battery Level</span>
            <span className="drawer-val" style={{ color: '#10b981' }}>{selectedAmr.battery}%</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">Completed Missions</span>
            <span className="drawer-val">{selectedAmr.completed_tasks || 0}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">Total Distance</span>
            <span className="drawer-val mono">{selectedAmr.total_distance?.toFixed(1)} m</span>
          </div>
        </div>

        {/* Onboard A* Planner Telemetry */}
        <div className="drawer-subsection-title">
          <Cpu size={14} color="var(--accent-cyan)" />
          <span>Onboard A* Path Planner</span>
        </div>

        <div className="drawer-section">
          <div className="drawer-row">
            <span className="drawer-key">Planning State</span>
            <span className="drawer-val">{astar.planning_status || 'Ready'}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">Computation Time</span>
            <span className="drawer-val" style={{ color: 'var(--accent-cyan)' }}>
              {astar.planning_time_ms || 0} ms
            </span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">Nodes Explored</span>
            <span className="drawer-val" style={{ color: '#c084fc' }}>
              {astar.nodes_explored || 0} nodes
            </span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">Computed Path Length</span>
            <span className="drawer-val">{astar.path_length || selectedAmr.path_length || 0} steps</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">Path Travel Cost</span>
            <span className="drawer-val" style={{ color: '#38bdf8' }}>{astar.path_cost || 0}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">Lifetime Dynamic Replans</span>
            <span className="drawer-val" style={{ color: '#f59e0b' }}>{astar.replan_count || 0}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

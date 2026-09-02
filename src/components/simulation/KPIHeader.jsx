import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Bot, Navigation, CheckCircle2, RefreshCw, ShieldAlert, ShieldCheck, Route, Clock } from 'lucide-react';

export default function KPIHeader() {
  const { simulationData } = useSimulation();
  const sys = simulationData?.system || {};

  return (
    <div className="kpi-metrics-grid">
      {/* 1. Active AMRs */}
      <div className="kpi-metric-card">
        <div className="kpi-title">Active AMRs</div>
        <div className="kpi-value cyan">{sys.active_amrs || 0} / 6</div>
        <div className="kpi-sub">Autonomous Agents</div>
      </div>

      {/* 2. A* Planners */}
      <div className="kpi-metric-card">
        <div className="kpi-title">A* Planners</div>
        <div className="kpi-value green">{sys.active_planners || 0} Active</div>
        <div className="kpi-sub">Decentralized Onboard</div>
      </div>

      {/* 3. Active Tasks */}
      <div className="kpi-metric-card">
        <div className="kpi-title">Active Tasks</div>
        <div className="kpi-value blue">{sys.tasks_active !== undefined ? sys.tasks_active : 0}</div>
        <div className="kpi-sub">In Mission Lifecycle</div>
      </div>

      {/* 4. Completed Tasks */}
      <div className="kpi-metric-card">
        <div className="kpi-title">Completed Tasks</div>
        <div className="kpi-value emerald">{sys.tasks_completed || 0}</div>
        <div className="kpi-sub">Delivered Cargo</div>
      </div>

      {/* 5. A* Replans */}
      <div className="kpi-metric-card">
        <div className="kpi-title">A* Replans</div>
        <div className="kpi-value purple">{sys.autonomous_replans || 0}</div>
        <div className="kpi-sub">Dynamic Reroutes</div>
      </div>

      {/* 6. Conflicts & Deadlocks */}
      <div className="kpi-metric-card">
        <div className="kpi-title">Conflicts &amp; Deadlocks</div>
        <div className="kpi-value yellow">{sys.conflicts_resolved || 0}</div>
        <div className="kpi-sub">{sys.deadlocks_resolved || 0} Deadlocks Resolved</div>
      </div>

      {/* 7. Safety Collisions */}
      <div className="kpi-metric-card">
        <div className="kpi-title">Safety Collisions</div>
        <div className="kpi-value green">{sys.collision_count || 0}</div>
        <div className="kpi-sub">0 Penetrations (SIL-3)</div>
      </div>

      {/* 8. Fleet Distance & Sim Time */}
      <div className="kpi-metric-card">
        <div className="kpi-title">Fleet Distance</div>
        <div className="kpi-value">{sys.total_distance?.toFixed(1) || '0.0'} m</div>
        <div className="kpi-sub">
          Time: {sys.sim_time?.toFixed(1) || '0.0'}s ({sys.sim_speed || 1.0}x)
        </div>
      </div>
    </div>
  );
}

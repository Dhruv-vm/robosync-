import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Bot, Navigation, CheckCircle2, RefreshCw, ShieldCheck, Route, Clock, Zap } from 'lucide-react';

export default function KPIHeader() {
  const { simulationData } = useSimulation();
  const sys = simulationData?.system || {};

  return (
    <div className="ops-telemetry-panel">
      <div className="telemetry-panel-left">
        <div className="telemetry-readout-item">
          <span className="telemetry-k">ONBOARD PLANNERS</span>
          <span className="telemetry-v cyan mono">{sys.active_planners || 0} ACTIVE</span>
        </div>

        <div className="telemetry-item-divider" />

        <div className="telemetry-readout-item">
          <span className="telemetry-k">DELIVERIES</span>
          <span className="telemetry-v emerald mono">{sys.tasks_completed || 0} COMPLETED</span>
        </div>

        <div className="telemetry-item-divider" />

        <div className="telemetry-readout-item">
          <span className="telemetry-k">A* RE-ROUTES</span>
          <span className="telemetry-v purple mono">{sys.autonomous_replans || 0} DYNAMIC</span>
        </div>

        <div className="telemetry-item-divider" />

        <div className="telemetry-readout-item">
          <span className="telemetry-k">DEADLOCKS RESOLVED</span>
          <span className="telemetry-v yellow mono">{sys.deadlocks_resolved || 0} (0 ACTIVE)</span>
        </div>
      </div>

      <div className="telemetry-panel-right">
        <div className="telemetry-readout-item">
          <span className="telemetry-k">FLEET ODOMETRY</span>
          <span className="telemetry-v mono">{sys.total_distance?.toFixed(1) || '0.0'} m</span>
        </div>

        <div className="telemetry-item-divider" />

        <div className="telemetry-readout-item">
          <span className="telemetry-k">RATE</span>
          <span className="telemetry-v cyan mono">{sys.sim_speed || 1.0}x CLOCK</span>
        </div>
      </div>
    </div>
  );
}

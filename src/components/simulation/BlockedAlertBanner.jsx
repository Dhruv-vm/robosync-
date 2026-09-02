import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { AlertTriangle, ArrowRight, Activity } from 'lucide-react';

export default function BlockedAlertBanner() {
  const { simulationData } = useSimulation();
  const alert = simulationData?.blocked_alert;

  if (!alert || !alert.active) return null;

  const obsStr = alert.obstacle_pos ? `(${alert.obstacle_pos.join(', ')})` : '(11, 13)';
  const stage = alert.stage || 'PATH_BLOCKED';

  return (
    <div className="ops-alert-ticker">
      <div className="alert-ticker-left">
        <div className="alert-hazard-tag">
          <AlertTriangle size={13} />
          <span>DYNAMIC HAZARD DETECTED</span>
        </div>
        <div className="alert-detail-txt">
          LOCATION: <strong className="mono">{obsStr}</strong> &bull; DETECTING AGENT: <strong className="mono">{alert.affected_amr || 'AMR-3'}</strong>
        </div>
      </div>

      <div className="alert-stage-stepper">
        <div className={`ops-stepper-pill ${stage === 'PATH_BLOCKED' ? 'active' : 'passed'}`}>
          PATH BLOCKED
        </div>
        <ArrowRight size={11} className="stepper-arrow" />
        <div className={`ops-stepper-pill ${stage === 'A*_REPLANNING' ? 'active' : stage === 'ALTERNATE_PATH_FOUND' || stage === 'RESUMED' ? 'passed' : ''}`}>
          A* REPLANNING
        </div>
        <ArrowRight size={11} className="stepper-arrow" />
        <div className={`ops-stepper-pill ${stage === 'ALTERNATE_PATH_FOUND' ? 'active' : stage === 'RESUMED' ? 'passed' : ''}`}>
          DETOUR COMPUTED
        </div>
        <ArrowRight size={11} className="stepper-arrow" />
        <div className={`ops-stepper-pill ${stage === 'RESUMED' ? 'active' : ''}`}>
          ROUTE RESUMED
        </div>
      </div>
    </div>
  );
}

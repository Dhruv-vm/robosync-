import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { AlertTriangle, ArrowRight } from 'lucide-react';

export default function BlockedAlertBanner() {
  const { simulationData } = useSimulation();
  const alert = simulationData?.blocked_alert;

  if (!alert || !alert.active) return null;

  const obsStr = alert.obstacle_pos ? `(${alert.obstacle_pos.join(', ')})` : '(11, 13)';
  const stage = alert.stage || 'PATH_BLOCKED';

  return (
    <div className="dynamic-alert-banner">
      <div className="alert-left-meta">
        <div className="alert-badge-tag">
          <AlertTriangle size={13} />
          <span>ALERT</span>
        </div>
        <div>
          <div className="alert-title-text">DYNAMIC OBSTACLE DETECTED IN AISLE</div>
          <div className="alert-sub-text">
            Location: <strong>{obsStr}</strong> &bull; Affected Vehicle: <strong>{alert.affected_amr || 'AMR-3'}</strong>
          </div>
        </div>
      </div>

      <div className="alert-pipeline-steps">
        <div className={`pipeline-pill ${stage === 'PATH_BLOCKED' ? 'active' : 'passed'}`}>
          PATH BLOCKED
        </div>
        <ArrowRight size={12} className="pipeline-arrow" />
        <div className={`pipeline-pill ${stage === 'A*_REPLANNING' ? 'active' : stage === 'ALTERNATE_PATH_FOUND' || stage === 'RESUMED' ? 'passed' : ''}`}>
          A* REPLANNING
        </div>
        <ArrowRight size={12} className="pipeline-arrow" />
        <div className={`pipeline-pill ${stage === 'ALTERNATE_PATH_FOUND' ? 'active' : stage === 'RESUMED' ? 'passed' : ''}`}>
          ALTERNATE PATH FOUND
        </div>
        <ArrowRight size={12} className="pipeline-arrow" />
        <div className={`pipeline-pill ${stage === 'RESUMED' ? 'active' : ''}`}>
          RESUMED
        </div>
      </div>
    </div>
  );
}

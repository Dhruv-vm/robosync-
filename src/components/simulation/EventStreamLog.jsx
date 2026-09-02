import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Terminal, Radio } from 'lucide-react';

const AMR_THEME = {
  'AMR-1': '#38bdf8',
  'AMR-2': '#f87171',
  'AMR-3': '#4ade80',
  'AMR-4': '#facc15',
  'AMR-5': '#c084fc',
  'AMR-6': '#2dd4bf',
  'System': '#94a3b8',
  'Task Manager': '#34d399',
  'Distributed Auction': '#c084fc',
};

export default function EventStreamLog() {
  const { simulationData } = useSimulation();
  const events = simulationData?.recent_events || [];

  return (
    <div className="ops-panel-section">
      <div className="ops-panel-header">
        <div className="ops-panel-title-wrap">
          <Terminal size={14} color="var(--accent-cyan)" />
          <span className="ops-panel-title">LIVE COORDINATION // P2P MESH EVENT BUS</span>
        </div>
        <div className="ops-bus-status">
          <span className="bus-active-dot" />
          <span>BROADCAST ACTIVE</span>
        </div>
      </div>

      <div className="ops-event-terminal">
        {events.length === 0 ? (
          <div className="ops-empty-log">Listening on local wireless ad-hoc RF mesh...</div>
        ) : (
          events
            .slice()
            .reverse()
            .map((e, idx) => {
              const tagColor = AMR_THEME[e.tag] || '#94a3b8';
              return (
                <div key={`${e.timestamp}-${idx}`} className="terminal-log-row">
                  <span className="log-time-col mono">{e.timestamp}</span>
                  <span className="log-tag-col mono" style={{ color: tagColor }}>
                    [{e.tag}]
                  </span>
                  <span className="log-msg-col">{e.message}</span>
                </div>
              );
            })
        )}
      </div>
    </div>
  );
}

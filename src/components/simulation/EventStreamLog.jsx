import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Terminal } from 'lucide-react';

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
    <div className="simulation-panel-card">
      <div className="sim-panel-header">
        <div className="sim-panel-title">
          <Terminal size={15} color="var(--accent-cyan)" />
          <span>Real-Time Coordination Event Stream</span>
        </div>
        <div className="sim-panel-badge">
          Live Mesh Bus
        </div>
      </div>

      <div className="event-stream-container">
        {events.length === 0 ? (
          <div className="empty-panel-state">Waiting for real-time events from P2P network...</div>
        ) : (
          events
            .slice()
            .reverse()
            .map((e, idx) => {
              const tagColor = AMR_THEME[e.tag] || '#94a3b8';
              return (
                <div key={`${e.timestamp}-${idx}`} className="event-log-entry">
                  <span className="log-timestamp">{e.timestamp}</span>
                  <span className="log-tag" style={{ color: tagColor }}>
                    [{e.tag}]
                  </span>
                  <span className="log-message">{e.message}</span>
                </div>
              );
            })
        )}
      </div>
    </div>
  );
}

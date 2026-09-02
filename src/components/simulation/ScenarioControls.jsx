import React, { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Play, Pause, RotateCcw, AlertOctagon, Sliders, Zap } from 'lucide-react';

const SCENARIOS = [
  { id: 'normal', name: 'NORMAL RUN', desc: 'Run normal multi-AMR operations' },
  { id: 'deadlock', name: 'DEADLOCK DEMO', desc: 'Demonstrate decentralized deadlock detection and resolution' },
  { id: 'intersection', name: 'INTERSECTION DEMO', desc: 'Demonstrate collision-free intersection coordination' },
  { id: 'reservation', name: 'RESERVATION DEMO', desc: 'Demonstrate spatial-temporal cell reservations' },
  { id: 'blocked', name: 'BLOCKED AISLE DEMO', desc: 'Demonstrate dynamic obstacle detection and local A* replanning' },
  { id: 'reset', name: 'RESET SIMULATION', desc: 'Reset the simulation to its initial state' },
];

const SPEEDS = [0.25, 0.5, 1.0, 2.0, 5.0, 10.0];

export default function ScenarioControls() {
  const { simulationData, sendControl } = useSimulation();
  const [localPendingDemo, setLocalPendingDemo] = useState(null);
  const [isActionPending, setIsActionPending] = useState(false);

  const sys = simulationData?.system || {};
  const isPaused = sys.is_paused;
  const currentSpeed = sys.sim_speed || 1.0;
  const currentScenario = (sys.scenario || 'normal').toLowerCase();
  const activeDemo = localPendingDemo || currentScenario;

  const handleSelectScenario = async (scenarioId, desc) => {
    setLocalPendingDemo(scenarioId);
    setIsActionPending(true);

    try {
      if (scenarioId === 'reset') {
        await sendControl('reset');
      } else {
        await sendControl('set_scenario', { scenario: scenarioId });
      }
    } catch (err) {
      console.error(`Failed to switch to scenario ${scenarioId}:`, err);
    } finally {
      setIsActionPending(false);
      setTimeout(() => setLocalPendingDemo(null), 600);
    }
  };

  const handleTogglePause = async () => {
    setIsActionPending(true);
    try {
      await sendControl('toggle_pause');
    } catch (err) {
      console.error('Failed to toggle pause:', err);
    } finally {
      setIsActionPending(false);
    }
  };

  const handleStart = async () => {
    setIsActionPending(true);
    try {
      await sendControl('resume');
    } catch (err) {
      console.error('Failed to start/resume:', err);
    } finally {
      setIsActionPending(false);
    }
  };

  const handleReset = async () => {
    setIsActionPending(true);
    try {
      await sendControl('reset');
    } catch (err) {
      console.error('Failed to reset:', err);
    } finally {
      setIsActionPending(false);
    }
  };

  const handleInjectObstacle = async () => {
    setIsActionPending(true);
    try {
      await sendControl('inject_obstacle', { cell: [11, 13] });
    } catch (err) {
      console.error('Failed to inject obstacle:', err);
    } finally {
      setIsActionPending(false);
    }
  };

  const handleSetSpeed = async (spd) => {
    try {
      await sendControl('set_speed', { speed: spd });
    } catch (err) {
      console.error(`Failed to set speed to ${spd}:`, err);
    }
  };

  return (
    <div className="scenario-controls-panel">
      {/* Top Controls Toolbar */}
      <div className="controls-top-bar">
        <div className="controls-brand-meta">
          <Sliders size={15} color="var(--accent-cyan)" />
          <span className="controls-brand-name">SIH DEMONSTRATION CONTROLS</span>
          <span className={`sim-state-badge ${isPaused ? 'paused' : 'running'}`}>
            <span className="state-pulse-dot" />
            <span>{isPaused ? 'PAUSED' : 'RUNNING'}</span>
          </span>
        </div>

        <div className="playback-actions-group">
          <button
            className="ctrl-action-btn primary"
            onClick={handleStart}
            disabled={isActionPending}
            title="Start / Resume simulation"
          >
            <Play size={13} />
            <span>Start</span>
          </button>

          <button
            className={`ctrl-action-btn ${isPaused ? 'paused-btn' : 'warning'}`}
            onClick={handleTogglePause}
            disabled={isActionPending}
            title="Pause / Resume simulation"
          >
            <Pause size={13} />
            <span>{isPaused ? 'Resume' : 'Pause'}</span>
          </button>

          <button
            className="ctrl-action-btn"
            onClick={handleReset}
            disabled={isActionPending}
            title="Reset simulation"
          >
            <RotateCcw size={13} />
            <span>Reset</span>
          </button>

          <button
            className="ctrl-action-btn hazard"
            onClick={handleInjectObstacle}
            disabled={isActionPending}
            title="Inject dynamic obstacle at (11, 13)"
          >
            <AlertOctagon size={13} />
            <span>Obstacle (11, 13)</span>
          </button>

          {/* Speed Selector */}
          <div className="speed-pills-bar">
            {SPEEDS.map((spd) => (
              <button
                key={spd}
                className={`speed-pill-btn ${Math.abs(currentSpeed - spd) < 0.05 ? 'active' : ''}`}
                onClick={() => handleSetSpeed(spd)}
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Scenario Demo Grid */}
      <div className="scenarios-grid">
        {SCENARIOS.map((scen) => {
          const isSelected = activeDemo === scen.id;
          return (
            <button
              key={scen.id}
              className={`scenario-card-btn ${isSelected && scen.id !== 'reset' ? 'selected' : ''}`}
              onClick={() => handleSelectScenario(scen.id, scen.desc)}
              disabled={isActionPending}
            >
              <div className="scen-card-title">{scen.name}</div>
              <div className="scen-card-desc">{scen.desc}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

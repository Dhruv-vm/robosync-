import React, { useState } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { Play, Pause, RotateCcw, AlertOctagon, Sliders, Zap, Shield, GitCommit } from 'lucide-react';

const SCENARIOS = [
  { id: 'normal', name: 'NORMAL RUN', desc: 'Standard parallel task bidding & dispatch' },
  { id: 'deadlock', name: 'DEADLOCK DEMO', desc: 'Decentralized priority scoring & cycle resolution' },
  { id: 'intersection', name: 'INTERSECTION DEMO', desc: 'Bottleneck mutual exclusion & yield locks' },
  { id: 'reservation', name: 'RESERVATION DEMO', desc: 'Spatial-temporal cell lookahead reservations' },
  { id: 'blocked', name: 'BLOCKED AISLE DEMO', desc: 'Obstacle detection & dynamic local A* replanning' },
  { id: 'reset', name: 'RESET SIMULATION', desc: 'Restore fleet to docks & clear task queue' },
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
    <div className="ops-control-console">
      {/* Console Top Toolbar */}
      <div className="console-top-row">
        <div className="console-brand-tag">
          <div className="console-tag-dot" />
          <span className="console-tag-title">MISSION CONTROL // BENCHMARKS &amp; DISPATCH</span>
          <span className={`console-state-pill ${isPaused ? 'paused' : 'running'}`}>
            <span className="state-pulse-dot" />
            <span>{isPaused ? 'SIMULATION PAUSED' : 'PHYSICS RUNNING'}</span>
          </span>
        </div>

        <div className="console-playback-actions">
          <button
            className="btn-console-action primary"
            onClick={handleStart}
            disabled={isActionPending}
            title="Start / Resume physics loop"
          >
            <Play size={12} fill="currentColor" />
            <span>START</span>
          </button>

          <button
            className={`btn-console-action ${isPaused ? 'active-pause' : 'warning'}`}
            onClick={handleTogglePause}
            disabled={isActionPending}
            title="Pause / Resume physics loop"
          >
            <Pause size={12} fill="currentColor" />
            <span>{isPaused ? 'RESUME' : 'PAUSE'}</span>
          </button>

          <button
            className="btn-console-action secondary"
            onClick={handleReset}
            disabled={isActionPending}
            title="Reset fleet & tasks"
          >
            <RotateCcw size={12} />
            <span>RESET</span>
          </button>

          <button
            className="btn-console-action hazard"
            onClick={handleInjectObstacle}
            disabled={isActionPending}
            title="Inject dynamic blockage at corridor (11, 13)"
          >
            <AlertOctagon size={12} />
            <span>INJECT OBSTACLE (11, 13)</span>
          </button>

          {/* Precision Clock Multipliers */}
          <div className="console-speed-dial">
            <span className="speed-dial-label">SPEED:</span>
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

      {/* Scenario Benchmark Grid */}
      <div className="console-scenarios-strip">
        {SCENARIOS.map((scen) => {
          const isSelected = activeDemo === scen.id;
          return (
            <button
              key={scen.id}
              className={`scenario-tactical-tab ${isSelected && scen.id !== 'reset' ? 'selected' : ''}`}
              onClick={() => handleSelectScenario(scen.id, scen.desc)}
              disabled={isActionPending}
            >
              <div className="scen-tab-header">
                <span className="scen-tab-id">{scen.name}</span>
                {isSelected && scen.id !== 'reset' && (
                  <span className="scen-active-indicator" />
                )}
              </div>
              <div className="scen-tab-desc">{scen.desc}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

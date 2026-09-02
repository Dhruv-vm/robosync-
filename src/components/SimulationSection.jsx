import React from 'react';
import { useSimulation, ViewMode } from '../context/SimulationContext';
import ViewLayoutSelector from './simulation/ViewLayoutSelector';
import KPIHeader from './simulation/KPIHeader';
import BlockedAlertBanner from './simulation/BlockedAlertBanner';
import ScenarioControls from './simulation/ScenarioControls';
import Warehouse2DMap from './simulation/Warehouse2DMap';
import FleetTable from './simulation/FleetTable';
import TaskAuctionPool from './simulation/TaskAuctionPool';
import EventStreamLog from './simulation/EventStreamLog';
import AmrInspectorDrawer from './simulation/AmrInspectorDrawer';
import { Cpu, Terminal } from 'lucide-react';

export default function SimulationSection() {
  const { activeView, splitLeftView, splitRightView } = useSimulation();

  // Helper to render individual view component
  const renderSingleView = (viewType) => {
    switch (viewType) {
      case ViewMode.MAP_2D:
        return <Warehouse2DMap />;
      case ViewMode.FLEET_MATRIX:
        return <FleetTable />;
      case ViewMode.TASKS_AUCTIONS:
        return <TaskAuctionPool />;
      case ViewMode.EVENT_STREAM:
        return <EventStreamLog />;
      case ViewMode.SCENARIO_CONTROLS:
        return <ScenarioControls />;
      default:
        return <Warehouse2DMap />;
    }
  };

  return (
    <div className="tab-transition-wrapper simulation-workspace-wrapper">
      {/* Simulation View Header */}
      <div className="view-header">
        <div className="view-badge">
          <Cpu size={14} color="var(--cyan-bright)" />
          <span>AUTONOMOUS FLEET CONTROL CENTER // DECENTRALIZED P2P</span>
        </div>
        <h2 className="view-title">Real-Time Autonomous AMR Simulation</h2>
        <p className="view-subtitle">
          Decentralized multi-agent coordination, spatial-temporal deadlock avoidance, and dynamic obstacle replanning.
        </p>
      </div>

      {/* Dynamic Multi-System View Switcher & Host Connection Bar */}
      <ViewLayoutSelector />

      {/* Dynamic Obstacle Re-Routing Pipeline Alert */}
      <BlockedAlertBanner />

      {/* Dynamic View Mount Stage */}
      <div className="simulation-dynamic-stage" id="simulation-viewport">
        {/* MODE 1: COMMAND HUB (Comprehensive Overview) */}
        {activeView === ViewMode.COMMAND_HUB && (
          <div className="command-hub-layout">
            <KPIHeader />
            <ScenarioControls />
            <div className="hub-main-workspace-grid">
              <div className="hub-map-column">
                <Warehouse2DMap />
              </div>
              <div className="hub-fleet-column">
                <FleetTable />
              </div>
            </div>
            <div className="hub-secondary-grid">
              <TaskAuctionPool />
              <EventStreamLog />
            </div>
          </div>
        )}

        {/* MODE 2: DEDICATED 2D MAP */}
        {activeView === ViewMode.MAP_2D && (
          <div className="dedicated-view-wrapper">
            <Warehouse2DMap />
          </div>
        )}

        {/* MODE 3: DEDICATED FLEET MATRIX */}
        {activeView === ViewMode.FLEET_MATRIX && (
          <div className="dedicated-view-wrapper">
            <KPIHeader />
            <FleetTable />
          </div>
        )}

        {/* MODE 4: DEDICATED TASK AUCTIONS */}
        {activeView === ViewMode.TASKS_AUCTIONS && (
          <div className="dedicated-view-wrapper">
            <TaskAuctionPool />
          </div>
        )}

        {/* MODE 5: DEDICATED EVENT STREAM */}
        {activeView === ViewMode.EVENT_STREAM && (
          <div className="dedicated-view-wrapper">
            <EventStreamLog />
          </div>
        )}

        {/* MODE 6: DEDICATED SCENARIO CONTROLS */}
        {activeView === ViewMode.SCENARIO_CONTROLS && (
          <div className="dedicated-view-wrapper">
            <KPIHeader />
            <ScenarioControls />
          </div>
        )}

        {/* MODE 7: SPLIT VIEW (Custom 2-Panel Layout) */}
        {activeView === ViewMode.SPLIT_VIEW && (
          <div className="split-view-container">
            <div className="split-view-panel left-panel">
              {renderSingleView(splitLeftView)}
            </div>
            <div className="split-view-panel right-panel">
              {renderSingleView(splitRightView)}
            </div>
          </div>
        )}
      </div>

      {/* Selected AMR Deep Telemetry Drawer */}
      <AmrInspectorDrawer />
    </div>
  );
}

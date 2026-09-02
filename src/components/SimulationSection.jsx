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
    <div className="tab-transition-wrapper ops-stage-wrapper">
      {/* 1. Top Industrial Command Bar (Branding, Live Stats, View Switcher, Settings) */}
      <ViewLayoutSelector />

      {/* 2. Dynamic Obstacle Hazard Alert Ticker */}
      <BlockedAlertBanner />

      {/* 3. Primary Operations Workspace Stage */}
      <div className="ops-workspace-stage" id="simulation-viewport">
        {/* MODE 1: COMMAND HUB (Industrial Master Workstation) */}
        {activeView === ViewMode.COMMAND_HUB && (
          <div className="ops-hub-layout">
            {/* Primary Row: Map (65-70% Dominance) + Fleet Matrix (30-35%) */}
            <div className="ops-hero-row">
              <div className="ops-map-hero-column">
                <Warehouse2DMap />
              </div>
              <div className="ops-fleet-column">
                <FleetTable />
              </div>
            </div>

            {/* Mission Control & Benchmarks Strip */}
            <ScenarioControls />

            {/* Secondary Operational Strip: KPIs */}
            <KPIHeader />

            {/* Logistics Manifest & P2P Event Stream Grid */}
            <div className="ops-manifest-grid">
              <TaskAuctionPool />
              <EventStreamLog />
            </div>
          </div>
        )}

        {/* MODE 2: DEDICATED FULLSCREEN 2D MAP */}
        {activeView === ViewMode.MAP_2D && (
          <div className="ops-fullscreen-wrapper">
            <Warehouse2DMap />
          </div>
        )}

        {/* MODE 3: DEDICATED FLEET MATRIX */}
        {activeView === ViewMode.FLEET_MATRIX && (
          <div className="ops-fullscreen-wrapper">
            <KPIHeader />
            <FleetTable />
          </div>
        )}

        {/* MODE 4: DEDICATED TASK AUCTIONS */}
        {activeView === ViewMode.TASKS_AUCTIONS && (
          <div className="ops-fullscreen-wrapper">
            <TaskAuctionPool />
          </div>
        )}

        {/* MODE 5: DEDICATED EVENT STREAM */}
        {activeView === ViewMode.EVENT_STREAM && (
          <div className="ops-fullscreen-wrapper">
            <EventStreamLog />
          </div>
        )}

        {/* MODE 6: DEDICATED SCENARIO CONTROLS */}
        {activeView === ViewMode.SCENARIO_CONTROLS && (
          <div className="ops-fullscreen-wrapper">
            <KPIHeader />
            <ScenarioControls />
          </div>
        )}

        {/* MODE 7: SPLIT WORKSPACE (Custom 2-Panel Layout) */}
        {activeView === ViewMode.SPLIT_VIEW && (
          <div className="ops-split-workspace">
            <div className="ops-split-panel left-panel">
              {renderSingleView(splitLeftView)}
            </div>
            <div className="ops-split-panel right-panel">
              {renderSingleView(splitRightView)}
            </div>
          </div>
        )}
      </div>

      {/* Selected AMR Deep Telemetry Slide-Out Drawer */}
      <AmrInspectorDrawer />
    </div>
  );
}

import React from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { X, Cpu, Navigation, Activity, Battery, MapPin, Compass, ShieldCheck, Radio } from 'lucide-react';

const AMR_THEME = {
  'AMR-1': '#38bdf8',
  'AMR-2': '#f87171',
  'AMR-3': '#4ade80',
  'AMR-4': '#facc15',
  'AMR-5': '#c084fc',
  'AMR-6': '#2dd4bf',
};

export default function AmrInspectorDrawer() {
  const { selectedAmrId, selectedAmr, setSelectedAmrId, simulationData } = useSimulation();

  if (!selectedAmrId || !selectedAmr) return null;

  const color = AMR_THEME[selectedAmr.robot_id] || '#38bdf8';
  const astar = selectedAmr.astar_metrics || {};
  const isFailed = selectedAmr.status === 'FAILED';

  // Extract active peers from selectedAmr.peer_states, selectedAmr.connected_peers, or simulationData.fleet
  const fleet = simulationData?.fleet || [];
  const rawPeers = selectedAmr.connected_peers || (selectedAmr.peer_states ? Object.keys(selectedAmr.peer_states) : []);

  const peerList = rawPeers.length > 0
    ? rawPeers.map((pid) => {
        const stateObj = selectedAmr.peer_states?.[pid];
        const fleetObj = fleet.find((a) => a.robot_id === pid);
        return {
          robot_id: pid,
          status: stateObj?.status || fleetObj?.status || 'CONNECTED',
          grid_pos: stateObj?.grid_pos || fleetObj?.grid_pos || null,
          battery: stateObj?.battery ?? fleetObj?.battery,
          active_mission: stateObj?.active_mission || fleetObj?.task_id || 'IDLE',
          priority: stateObj?.priority
        };
      })
    : fleet.filter((a) => a.robot_id !== selectedAmr.robot_id).map((a) => ({
        robot_id: a.robot_id,
        status: a.status || 'CONNECTED',
        grid_pos: a.grid_pos || null,
        battery: a.battery,
        active_mission: a.task_id || 'IDLE',
        priority: null
      }));

  return (
    <div className="amr-inspector-backdrop" onClick={() => setSelectedAmrId(null)}>
      <div className="amr-inspector-drawer" onClick={(e) => e.stopPropagation()}>
        {/* Drawer Header */}
        <div className="drawer-header">
          <div className="drawer-title-group">
            <span className="drawer-dot" style={{ backgroundColor: color }} />
            <h3 style={{ color }} className="mono">{selectedAmr.robot_id} // DEEP TELEMETRY</h3>
          </div>
          <button className="drawer-close-btn" onClick={() => setSelectedAmrId(null)} aria-label="Close Inspector">
            <X size={15} />
          </button>
        </div>

        {/* Status & Mission Section */}
        <div className="drawer-section">
          <div className="drawer-section-heading">OPERATIONAL STATE</div>
          <div className="drawer-row">
            <span className="drawer-key">STATUS</span>
            <span className="drawer-val mono" style={{ color: isFailed ? '#ef4444' : color }}>
              {selectedAmr.status}
            </span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">ACTIVE MISSION</span>
            <span className="drawer-val mono">{selectedAmr.task_id || 'STANDBY / IDLE'}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">GRID COORD</span>
            <span className="drawer-val mono">({selectedAmr.grid_pos?.[0]}, {selectedAmr.grid_pos?.[1]})</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">WORLD XYZ</span>
            <span className="drawer-val mono">
              ({selectedAmr.world_pos?.[0]?.toFixed(2)}, {selectedAmr.world_pos?.[1]?.toFixed(2)})
            </span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">HEADING (YAW)</span>
            <span className="drawer-val mono">{selectedAmr.yaw?.toFixed(3)} rad</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">TARGET GOAL</span>
            <span className="drawer-val mono">{selectedAmr.goal_desc || '-'}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">BATTERY SOC</span>
            <span className="drawer-val mono" style={{ color: '#10b981' }}>{selectedAmr.battery}%</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">COMPLETED MISSIONS</span>
            <span className="drawer-val mono">{selectedAmr.completed_tasks || 0}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">ODOMETRY</span>
            <span className="drawer-val mono">{selectedAmr.total_distance?.toFixed(1)} m</span>
          </div>
        </div>

        {/* P2P Mesh Network Telemetry */}
        <div className="drawer-section">
          <div className="drawer-section-heading">
            <Radio size={12} color="var(--accent-cyan)" />
            <span>P2P MESH // PEER CONNECTIONS</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">TRANSCEIVER</span>
            <span className="drawer-val mono" style={{ color: '#10b981' }}>
              ● MESH CONNECTED
            </span>
          </div>
          {selectedAmr.conflicting_peer && (
            <div className="drawer-conflict-banner mono">
              <span className="conflict-tag">CONFLICT PEER:</span>
              <strong style={{ color: '#ef4444' }}>{selectedAmr.conflicting_peer}</strong>
              {selectedAmr.conflict_cell && (
                <span className="conflict-cell">@ ({selectedAmr.conflict_cell.join(',')})</span>
              )}
            </div>
          )}
          <div className="drawer-p2p-peers-container">
            <div className="drawer-p2p-peers-header">
              <span className="drawer-key">ACTIVE PEERS ({peerList.length})</span>
            </div>
            <div className="drawer-p2p-peers-list">
              {peerList.length > 0 ? (
                peerList.map((peer) => {
                  const peerColor = AMR_THEME[peer.robot_id] || '#38bdf8';
                  const isConflict = selectedAmr.conflicting_peer === peer.robot_id;
                  const isPeerWaiting = String(peer.status).includes('WAITING') || String(peer.status).includes('YIELDING');
                  const statusColor = isConflict
                    ? '#ef4444'
                    : isPeerWaiting
                    ? '#f59e0b'
                    : peer.status === 'IDLE'
                    ? 'var(--text-muted)'
                    : '#10b981';

                  return (
                    <div
                      key={peer.robot_id}
                      className={`drawer-p2p-peer-card ${isConflict ? 'is-conflict' : ''}`}
                      onClick={() => setSelectedAmrId(peer.robot_id)}
                      title={`Click to inspect ${peer.robot_id}`}
                    >
                      <div className="peer-card-top">
                        <div className="peer-id-wrap">
                          <span className="peer-beacon-dot" style={{ backgroundColor: peerColor }} />
                          <span className="peer-name mono" style={{ color: peerColor }}>
                            {peer.robot_id}
                          </span>
                        </div>
                        <span className="peer-status-pill mono" style={{ color: statusColor }}>
                          {peer.status}
                        </span>
                      </div>
                      <div className="peer-card-bottom mono">
                        <span className="peer-coord">
                          {peer.grid_pos ? `POS: (${peer.grid_pos[0]}, ${peer.grid_pos[1]})` : 'POS: -'}
                        </span>
                        {peer.active_mission && peer.active_mission !== 'IDLE' && (
                          <span className="peer-mission">{peer.active_mission}</span>
                        )}
                        {peer.battery !== undefined && (
                          <span className="peer-batt">{peer.battery}%</span>
                        )}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="drawer-val mono" style={{ color: 'var(--text-muted)', padding: '0.4rem 0' }}>
                  NO ACTIVE PEER DATA
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Onboard A* Planner Telemetry */}
        <div className="drawer-section">
          <div className="drawer-section-heading">
            <Cpu size={12} color="var(--accent-cyan)" />
            <span>ONBOARD A* PATH PLANNER</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">PLANNER STATE</span>
            <span className="drawer-val mono">{astar.planning_status || 'Ready'}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">COMPUTE TIME</span>
            <span className="drawer-val mono cyan">
              {astar.planning_time_ms || 0} ms
            </span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">NODES EXPLORED</span>
            <span className="drawer-val mono purple">
              {astar.nodes_explored || 0} nodes
            </span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">WAYPOINTS</span>
            <span className="drawer-val mono">{astar.path_length || selectedAmr.path_length || 0} steps</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">PATH COST</span>
            <span className="drawer-val mono cyan">{astar.path_cost || 0}</span>
          </div>
          <div className="drawer-row">
            <span className="drawer-key">LIFETIME RE-ROUTES</span>
            <span className="drawer-val mono yellow">{astar.replan_count || 0}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

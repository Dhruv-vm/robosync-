import React, { useRef, useEffect, useState, useCallback } from 'react';
import { useSimulation } from '../../context/SimulationContext';
import { AlertCircle, Plus, Check, X, Trash2, Crosshair, Box, Target } from 'lucide-react';

const AMR_THEME = {
  'AMR-1': { color: '#38bdf8', fill: 'rgba(56, 189, 248, 0.2)' },
  'AMR-2': { color: '#f87171', fill: 'rgba(248, 113, 113, 0.2)' },
  'AMR-3': { color: '#4ade80', fill: 'rgba(74, 222, 128, 0.2)' },
  'AMR-4': { color: '#facc15', fill: 'rgba(250, 204, 21, 0.2)' },
  'AMR-5': { color: '#c084fc', fill: 'rgba(192, 132, 252, 0.2)' },
  'AMR-6': { color: '#2dd4bf', fill: 'rgba(45, 212, 191, 0.2)' },
};

const SHELF_BLOCKS = [
  { x: [5, 10], y: [3, 4] },
  { x: [5, 10], y: [8, 9] },
  { x: [5, 10], y: [11, 12] },
  { x: [14, 19], y: [3, 4] },
  { x: [14, 19], y: [8, 9] },
  { x: [14, 19], y: [11, 12] },
];

const CHARGING_DOCKS = [
  [1, 2], [22, 2], [1, 13], [22, 13], [1, 7], [22, 7]
];

export default function Warehouse2DMap({ onSelectAmr }) {
  const { simulationData, sendControl, selectedAmrId, setSelectedAmrId } = useSimulation();

  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  // Interactive Modes
  const [taskCreationMode, setTaskCreationMode] = useState(false);
  const [obstacleEditMode, setObstacleEditMode] = useState(false);
  const [taskStep, setTaskStep] = useState('PICKUP'); // 'PICKUP' | 'DROPOFF'
  const [selectedPickup, setSelectedPickup] = useState(null);
  const [selectedDropoff, setSelectedDropoff] = useState(null);
  const [taskPriority, setTaskPriority] = useState(1.0);
  const [hoveredCell, setHoveredCell] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const customTaskCounterRef = useRef(1);

  const isCellWalkableFloor = useCallback((gx, gy) => {
    if (gx <= 0 || gx >= 23 || gy <= 0 || gy >= 15) return false;
    for (const shelf of SHELF_BLOCKS) {
      if (gx >= shelf.x[0] && gx <= shelf.x[1] && gy >= shelf.y[0] && gy <= shelf.y[1]) {
        return false;
      }
    }
    for (const dock of CHARGING_DOCKS) {
      if (dock[0] === gx && dock[1] === gy) return false;
    }
    return true;
  }, []);

  const isCellValidForTaskStep = useCallback((gx, gy, step) => {
    if (!isCellWalkableFloor(gx, gy)) return false;
    if (step === 'DROPOFF' && selectedPickup) {
      if (selectedPickup[0] === gx && selectedPickup[1] === gy) return false;
    }
    return true;
  }, [isCellWalkableFloor, selectedPickup]);

  // Toggle Obstacle Editor
  const toggleObstacleEditMode = () => {
    setObstacleEditMode((prev) => !prev);
    if (!obstacleEditMode && taskCreationMode) {
      setTaskCreationMode(false);
      resetTaskForm();
    }
  };

  // Toggle Task Creation
  const toggleTaskCreationMode = () => {
    setTaskCreationMode((prev) => !prev);
    if (!taskCreationMode && obstacleEditMode) {
      setObstacleEditMode(false);
    }
    if (taskCreationMode) {
      resetTaskForm();
    } else {
      setTaskStep('PICKUP');
    }
  };

  const resetTaskForm = () => {
    setSelectedPickup(null);
    setSelectedDropoff(null);
    setTaskStep('PICKUP');
    setHoveredCell(null);
  };

  // Dispatch Custom Task to Backend
  const handleAssignTask = async () => {
    if (!selectedPickup || !selectedDropoff || isSubmitting) return;

    setIsSubmitting(true);
    const customTaskId = `BLOCK-${String(customTaskCounterRef.current).padStart(2, '0')}`;
    customTaskCounterRef.current += 1;

    try {
      await sendControl('create_custom_task', {
        pickup: selectedPickup,
        dropoff: selectedDropoff,
        priority: taskPriority,
        task_id: customTaskId,
      });

      resetTaskForm();
      setTaskCreationMode(false);
    } catch (err) {
      console.error('Failed to dispatch custom task:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Clear Obstacles
  const handleClearObstacles = async () => {
    try {
      await sendControl('clear_obstacles');
    } catch (err) {
      console.error('Failed to clear obstacles:', err);
    }
  };

  // Canvas Drawing
  const drawMap = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const rect = container.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const targetWidth = Math.round(rect.width);
    const targetHeight = Math.round(rect.height);

    if (canvas.width !== targetWidth * dpr || canvas.height !== targetHeight * dpr) {
      canvas.width = targetWidth * dpr;
      canvas.height = targetHeight * dpr;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.save();
    ctx.scale(dpr, dpr);

    const width = targetWidth;
    const height = targetHeight;
    ctx.clearRect(0, 0, width, height);

    const gridW = 24;
    const gridH = 16;
    const cellW = width / gridW;
    const cellH = height / gridH;
    const cellR = Math.min(cellW, cellH);

    // 1. Grid Background & Subtle Grid Lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
    ctx.lineWidth = 1;
    for (let x = 0; x <= gridW; x++) {
      ctx.beginPath();
      ctx.moveTo(x * cellW, 0);
      ctx.lineTo(x * cellW, height);
      ctx.stroke();
    }
    for (let y = 0; y <= gridH; y++) {
      ctx.beginPath();
      ctx.moveTo(0, y * cellH);
      ctx.lineTo(width, y * cellH);
      ctx.stroke();
    }

    const layout = simulationData?.layout || {};

    // 2. Shelf Blocks
    (layout.shelf_blocks || SHELF_BLOCKS.map((s) => [s.x[0], s.x[1], s.y[0], s.y[1]])).forEach((b) => {
      const [xs, xe, ys, ye] = b;
      const bx = xs * cellW;
      const by = (gridH - 1 - ye) * cellH;
      const bw = (xe - xs + 1) * cellW;
      const bh = (ye - ys + 1) * cellH;

      ctx.fillStyle = '#0f172a';
      ctx.fillRect(bx, by, bw, bh);
      ctx.strokeStyle = '#334155';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(bx, by, bw, bh);

      // Shelf Dividers
      ctx.strokeStyle = '#1e293b';
      for (let sx = xs; sx <= xe; sx++) {
        ctx.beginPath();
        ctx.moveTo(sx * cellW, by);
        ctx.lineTo(sx * cellW, by + bh);
        ctx.stroke();
      }
    });

    // 3. Pickup Zones (P1-P4)
    const pickups = layout.pickup_zones || { P1: [3, 14], P2: [8, 14], P3: [15, 14], P4: [20, 14] };
    for (const [pname, pos] of Object.entries(pickups)) {
      const px = pos[0] * cellW;
      const py = (gridH - 1 - pos[1]) * cellH;
      ctx.fillStyle = 'rgba(2, 132, 199, 0.25)';
      ctx.fillRect(px, py, cellW, cellH);
      ctx.strokeStyle = '#0284c7';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(px, py, cellW, cellH);

      ctx.fillStyle = '#38bdf8';
      ctx.font = 'bold 11px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(pname, px + cellW / 2, py + cellH / 2);
    }

    // 4. Dropoff Zones (D1-D4)
    const dropoffs = layout.dropoff_zones || { D1: [3, 1], D2: [8, 1], D3: [15, 1], D4: [20, 1] };
    for (const [dname, pos] of Object.entries(dropoffs)) {
      const dx = pos[0] * cellW;
      const dy = (gridH - 1 - pos[1]) * cellH;
      ctx.fillStyle = 'rgba(5, 150, 105, 0.25)';
      ctx.fillRect(dx, dy, cellW, cellH);
      ctx.strokeStyle = '#059669';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(dx, dy, cellW, cellH);

      ctx.fillStyle = '#34d399';
      ctx.font = 'bold 11px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(dname, dx + cellW / 2, dy + cellH / 2);
    }

    // 5. Charging Docks
    const docks = layout.charging_docks || {
      'AMR-1': [1, 2], 'AMR-2': [22, 2], 'AMR-3': [1, 13],
      'AMR-4': [22, 13], 'AMR-5': [1, 7], 'AMR-6': [22, 7],
    };
    for (const [dname, pos] of Object.entries(docks)) {
      const kx = pos[0] * cellW;
      const ky = (gridH - 1 - pos[1]) * cellH;
      ctx.fillStyle = 'rgba(217, 119, 6, 0.18)';
      ctx.fillRect(kx, ky, cellW, cellH);
      ctx.strokeStyle = '#d97706';
      ctx.lineWidth = 1;
      ctx.strokeRect(kx, ky, cellW, cellH);

      ctx.fillStyle = '#fbbf24';
      ctx.font = 'bold 9px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(dname.replace('AMR-', 'D'), kx + cellW / 2, ky + cellH / 2);
    }

    // 6. Active Tasks / Packages (B and TD)
    (simulationData?.tasks || []).forEach((t) => {
      if (t.status !== 'COMPLETED') {
        const isPickedUp = t.status === 'IN_PROGRESS' || t.status === 'PICKED_UP';
        if (!isPickedUp && t.pickup_pos) {
          const px = t.pickup_pos[0] * cellW;
          const py = (gridH - 1 - t.pickup_pos[1]) * cellH;

          ctx.fillStyle = 'rgba(245, 158, 11, 0.25)';
          ctx.beginPath();
          ctx.arc(px + cellW / 2, py + cellH / 2, cellR * 0.45, 0, Math.PI * 2);
          ctx.fill();

          ctx.fillStyle = '#b45309';
          ctx.fillRect(px + cellW * 0.15, py + cellH * 0.15, cellW * 0.7, cellH * 0.7);
          ctx.strokeStyle = '#fcd34d';
          ctx.lineWidth = 1.5;
          ctx.strokeRect(px + cellW * 0.15, py + cellH * 0.15, cellW * 0.7, cellH * 0.7);

          ctx.fillStyle = '#fff';
          ctx.font = 'bold 11px monospace';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText('B', px + cellW / 2, py + cellH / 2);
        }

        if (t.dropoff_pos) {
          const dx = t.dropoff_pos[0] * cellW;
          const dy = (gridH - 1 - t.dropoff_pos[1]) * cellH;

          ctx.strokeStyle = 'rgba(192, 132, 252, 0.8)';
          ctx.lineWidth = 1.5;
          ctx.setLineDash([2, 2]);
          ctx.beginPath();
          ctx.arc(dx + cellW / 2, dy + cellH / 2, cellR * 0.42, 0, Math.PI * 2);
          ctx.stroke();
          ctx.setLineDash([]);

          ctx.fillStyle = '#c084fc';
          ctx.font = 'bold 10px monospace';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText('TD', dx + cellW / 2, dy + cellH / 2);
        }
      }
    });

    // 7. Interactive Selected Pickup & Dropoff Markers
    if (selectedPickup) {
      const spx = selectedPickup[0] * cellW;
      const spy = (gridH - 1 - selectedPickup[1]) * cellH;

      ctx.fillStyle = '#0284c7';
      ctx.fillRect(spx + cellW * 0.15, spy + cellH * 0.15, cellW * 0.7, cellH * 0.7);
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2;
      ctx.strokeRect(spx + cellW * 0.15, spy + cellH * 0.15, cellW * 0.7, cellH * 0.7);

      ctx.fillStyle = '#fff';
      ctx.font = 'bold 12px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('B', spx + cellW / 2, spy + cellH / 2);
    }

    if (selectedDropoff) {
      const sdx = selectedDropoff[0] * cellW;
      const sdy = (gridH - 1 - selectedDropoff[1]) * cellH;

      ctx.strokeStyle = '#c084fc';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(sdx + cellW / 2, sdy + cellH / 2, cellR * 0.4, 0, Math.PI * 2);
      ctx.stroke();

      ctx.fillStyle = '#fff';
      ctx.font = 'bold 11px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('TD', sdx + cellW / 2, sdy + cellH / 2);
    }

    // 8. Hover Reticle during Modes
    if (taskCreationMode && hoveredCell) {
      const hx = hoveredCell[0] * cellW;
      const hy = (gridH - 1 - hoveredCell[1]) * cellH;
      const isValid = isCellValidForTaskStep(hoveredCell[0], hoveredCell[1], taskStep);

      ctx.fillStyle = isValid
        ? taskStep === 'PICKUP' ? 'rgba(56, 189, 248, 0.25)' : 'rgba(192, 132, 252, 0.25)'
        : 'rgba(239, 68, 68, 0.25)';
      ctx.fillRect(hx, hy, cellW, cellH);
      ctx.strokeStyle = isValid
        ? taskStep === 'PICKUP' ? '#38bdf8' : '#c084fc'
        : '#ef4444';
      ctx.lineWidth = 2;
      ctx.strokeRect(hx + 1, hy + 1, cellW - 2, cellH - 2);

      ctx.fillStyle = '#fff';
      ctx.font = 'bold 11px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(taskStep === 'PICKUP' ? 'B' : 'TD', hx + cellW / 2, hy + cellH / 2);
    }

    if (obstacleEditMode && hoveredCell) {
      const hx = hoveredCell[0] * cellW;
      const hy = (gridH - 1 - hoveredCell[1]) * cellH;
      const gx = hoveredCell[0];
      const gy = hoveredCell[1];
      const isExistingObs = (simulationData?.dynamic_obstacles || []).some((o) => o[0] === gx && o[1] === gy);
      const isAmrOnCell = (simulationData?.fleet || []).some((a) => a.grid_pos[0] === gx && a.grid_pos[1] === gy);
      const isWalkable = isCellWalkableFloor(gx, gy);

      if (isExistingObs) {
        ctx.fillStyle = 'rgba(239, 68, 68, 0.35)';
        ctx.fillRect(hx, hy, cellW, cellH);
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.strokeRect(hx + 1, hy + 1, cellW - 2, cellH - 2);

        ctx.fillStyle = '#fff';
        ctx.font = 'bold 10px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('REMOVE', hx + cellW / 2, hy + cellH / 2);
      } else if (isAmrOnCell) {
        ctx.fillStyle = 'rgba(239, 68, 68, 0.2)';
        ctx.fillRect(hx, hy, cellW, cellH);
        ctx.strokeStyle = '#ef4444';
        ctx.setLineDash([2, 2]);
        ctx.strokeRect(hx + 1, hy + 1, cellW - 2, cellH - 2);
        ctx.setLineDash([]);
      } else if (isWalkable) {
        ctx.fillStyle = 'rgba(249, 115, 22, 0.3)';
        ctx.fillRect(hx, hy, cellW, cellH);
        ctx.strokeStyle = '#f97316';
        ctx.lineWidth = 2;
        ctx.strokeRect(hx + 1, hy + 1, cellW - 2, cellH - 2);

        ctx.fillStyle = '#fed7aa';
        ctx.font = 'bold 10px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('+ BLOCK', hx + cellW / 2, hy + cellH / 2);
      }
    }

    // 9. Dynamic Obstacles
    (simulationData?.dynamic_obstacles || []).forEach((obs) => {
      const ox = obs[0] * cellW;
      const oy = (gridH - 1 - obs[1]) * cellH;

      ctx.fillStyle = 'rgba(239, 68, 68, 0.28)';
      ctx.fillRect(ox + 1, oy + 1, cellW - 2, cellH - 2);
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 2;
      ctx.strokeRect(ox + 1, oy + 1, cellW - 2, cellH - 2);

      ctx.fillStyle = '#ef4444';
      ctx.font = 'bold 14px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('B', ox + cellW / 2, oy + cellH / 2);
    });

    // 10. Old Blocked Path Trails (Red Dotted Lines)
    (simulationData?.fleet || []).forEach((amr) => {
      const replan = amr.last_replan;
      if (replan && replan.old_path && replan.old_path.length > 1) {
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.55)';
        ctx.lineWidth = 2;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        replan.old_path.forEach((pt, i) => {
          const wx = (pt[0] + 0.5) * cellW;
          const wy = (gridH - 1 - pt[1] + 0.5) * cellH;
          if (i === 0) ctx.moveTo(wx, wy);
          else ctx.lineTo(wx, wy);
        });
        ctx.stroke();
        ctx.setLineDash([]);
      }
    });

    // 11. Active AMR Routes
    (simulationData?.fleet || []).forEach((amr) => {
      const path = amr.full_path || [];
      if (path.length > 1) {
        const theme = AMR_THEME[amr.robot_id] || { color: '#38bdf8' };
        ctx.strokeStyle = theme.color;
        ctx.lineWidth = selectedAmrId === amr.robot_id ? 3.5 : 1.8;
        ctx.setLineDash([4, 3]);

        ctx.beginPath();
        path.forEach((pt, i) => {
          const wx = (pt[0] + 0.5) * cellW;
          const wy = (gridH - 1 - pt[1] + 0.5) * cellH;
          if (i === 0) ctx.moveTo(wx, wy);
          else ctx.lineTo(wx, wy);
        });
        ctx.stroke();
        ctx.setLineDash([]);

        path.forEach((pt, i) => {
          if (i > 0) {
            const wx = (pt[0] + 0.5) * cellW;
            const wy = (gridH - 1 - pt[1] + 0.5) * cellH;
            ctx.fillStyle = theme.color;
            ctx.beginPath();
            ctx.arc(wx, wy, 2.5, 0, Math.PI * 2);
            ctx.fill();
          }
        });
      }
    });

    // 12. AMRs, Chassis, Heading, and Payload Box
    (simulationData?.fleet || []).forEach((amr) => {
      const theme = AMR_THEME[amr.robot_id] || { color: '#38bdf8' };
      const cx = (amr.grid_pos[0] + 0.5) * cellW;
      const cy = (gridH - 1 - amr.grid_pos[1] + 0.5) * cellH;
      const isSelected = selectedAmrId === amr.robot_id;

      if (isSelected) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.arc(cx, cy, cellR * 0.52, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Outer Ring
      ctx.fillStyle = theme.color;
      ctx.beginPath();
      ctx.arc(cx, cy, cellR * 0.4, 0, Math.PI * 2);
      ctx.fill();

      // Inner Core
      ctx.fillStyle = '#0b0e14';
      ctx.beginPath();
      ctx.arc(cx, cy, cellR * 0.28, 0, Math.PI * 2);
      ctx.fill();

      // Heading Vector Pointer
      if (amr.yaw !== undefined) {
        const arrowLen = cellR * 0.45;
        const hx = cx + Math.cos(-amr.yaw) * arrowLen;
        const hy = cy + Math.sin(-amr.yaw) * arrowLen;
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(hx, hy);
        ctx.stroke();
      }

      // Payload on Top
      if (amr.is_carrying_payload) {
        const bw = cellR * 0.44;
        const bh = cellR * 0.44;
        ctx.fillStyle = '#b45309';
        ctx.fillRect(cx - bw / 2, cy - bh / 2, bw, bh);
        ctx.strokeStyle = '#fcd34d';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(cx - bw / 2, cy - bh / 2, bw, bh);

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 9px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('B', cx, cy);
      } else {
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 9px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(amr.robot_id.replace('AMR-', ''), cx, cy);
      }
    });

    ctx.restore();
  }, [simulationData, selectedAmrId, taskCreationMode, obstacleEditMode, taskStep, selectedPickup, selectedDropoff, hoveredCell, isCellValidForTaskStep, isCellWalkableFloor]);

  useEffect(() => {
    drawMap();
  }, [drawMap]);

  // Handle Canvas Mouse Interaction
  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const gridW = 24;
    const gridH = 16;
    const cellW = rect.width / gridW;
    const cellH = rect.height / gridH;

    const gx = Math.floor(clickX / cellW);
    const gy = gridH - 1 - Math.floor(clickY / cellH);

    if (!hoveredCell || hoveredCell[0] !== gx || hoveredCell[1] !== gy) {
      setHoveredCell([gx, gy]);
    }
  };

  const handleMouseLeave = () => {
    setHoveredCell(null);
  };

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const gridW = 24;
    const gridH = 16;
    const cellW = rect.width / gridW;
    const cellH = rect.height / gridH;

    const gx = Math.floor(clickX / cellW);
    const gy = gridH - 1 - Math.floor(clickY / cellH);

    // 1. Obstacle Edit Mode Click
    if (obstacleEditMode) {
      const isExistingObs = (simulationData?.dynamic_obstacles || []).some((o) => o[0] === gx && o[1] === gy);
      const isAmrOnCell = (simulationData?.fleet || []).some((a) => a.grid_pos[0] === gx && a.grid_pos[1] === gy);

      if (isExistingObs) {
        sendControl('remove_obstacle', { cell: [gx, gy] });
      } else if (!isAmrOnCell && isCellWalkableFloor(gx, gy)) {
        sendControl('add_obstacle', { cell: [gx, gy] });
      }
      return;
    }

    // 2. Task Creation Mode Click
    if (taskCreationMode) {
      if (taskStep === 'PICKUP') {
        if (isCellValidForTaskStep(gx, gy, 'PICKUP')) {
          setSelectedPickup([gx, gy]);
          setTaskStep('DROPOFF');
        }
      } else if (taskStep === 'DROPOFF') {
        if (isCellValidForTaskStep(gx, gy, 'DROPOFF')) {
          setSelectedDropoff([gx, gy]);
        }
      }
      return;
    }

    // 3. Normal AMR Selection Click
    const clickedAmr = (simulationData?.fleet || []).find((a) => a.grid_pos[0] === gx && a.grid_pos[1] === gy);
    if (clickedAmr) {
      setSelectedAmrId(clickedAmr.robot_id);
      if (onSelectAmr) onSelectAmr(clickedAmr.robot_id);
    }
  };

  return (
    <div className="warehouse-2d-map-card">
      {/* Map Header & Mode Bar */}
      <div className="map-card-header">
        <div className="map-card-title">
          <Crosshair size={15} color="var(--accent-cyan)" />
          <span>2D Interactive Warehouse Grid &amp; A* Trajectory Map</span>
        </div>

        <div className="map-controls-cluster">
          <button
            className={`map-tool-btn ${obstacleEditMode ? 'active-hazard' : ''}`}
            onClick={toggleObstacleEditMode}
            title="Inject or remove obstacle blocks"
          >
            <AlertCircle size={13} />
            <span>{obstacleEditMode ? 'Exit Obstacle Editor' : '+ / - Blocked Cell Editor'}</span>
          </button>

          <button
            className="map-tool-btn"
            onClick={handleClearObstacles}
            title="Clear all dynamic obstacles"
          >
            <Trash2 size={13} />
            <span>Clear Obstacles</span>
          </button>

          <button
            className={`map-tool-btn ${taskCreationMode ? 'active-task' : 'primary'}`}
            onClick={toggleTaskCreationMode}
          >
            <Plus size={13} />
            <span>{taskCreationMode ? 'Cancel Task' : '+ Create Task'}</span>
          </button>
        </div>
      </div>

      {/* Interactive Task Creation Panel */}
      {taskCreationMode && (
        <div className="task-creator-subpanel">
          <div className="task-creator-row">
            <div className="task-step-indicators">
              <button
                className={`task-step-pill ${taskStep === 'PICKUP' ? 'active' : selectedPickup ? 'completed' : ''}`}
                onClick={() => setTaskStep('PICKUP')}
              >
                <Box size={12} />
                <span>Step 1: Place Source Box (B)</span>
              </button>
              <span className="step-arrow">&rarr;</span>
              <button
                className={`task-step-pill ${taskStep === 'DROPOFF' ? 'active' : selectedDropoff ? 'completed' : ''}`}
                onClick={() => setTaskStep('DROPOFF')}
              >
                <Target size={12} />
                <span>Step 2: Place Target (TD)</span>
              </button>
            </div>

            <div className="task-form-actions">
              <div className="coord-badge">
                Source: <strong>{selectedPickup ? `(${selectedPickup.join(', ')})` : 'Click Floor'}</strong>
              </div>
              <div className="coord-badge">
                Destination: <strong>{selectedDropoff ? `(${selectedDropoff.join(', ')})` : 'Click Floor'}</strong>
              </div>

              <select
                className="task-priority-select"
                value={taskPriority}
                onChange={(e) => setTaskPriority(parseFloat(e.target.value))}
              >
                <option value={1.0}>Priority: Normal (1.0)</option>
                <option value={1.5}>Priority: High (1.5)</option>
                <option value={2.0}>Priority: Urgent (2.0)</option>
              </select>

              <button
                className="btn-dispatch-task"
                disabled={!selectedPickup || !selectedDropoff || isSubmitting}
                onClick={handleAssignTask}
              >
                <Check size={13} />
                <span>{isSubmitting ? 'Dispatching...' : 'Assign & Dispatch'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Obstacle Editor Banner */}
      {obstacleEditMode && (
        <div className="obstacle-editor-banner">
          <AlertCircle size={14} color="#fca5a5" />
          <span>
            <strong>Obstacle Editor Active:</strong> Click any walkable floor aisle cell to place a dynamic blockage (<span style={{ color: '#ef4444', fontWeight: 800 }}>B</span>), or click an existing obstacle to remove it. AMRs will detect it and replan dynamically!
          </span>
        </div>
      )}

      {/* 2D Grid Canvas Container */}
      <div className="map-canvas-container" ref={containerRef}>
        <canvas
          ref={canvasRef}
          className="warehouse-canvas-element"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          onClick={handleCanvasClick}
        />
      </div>

      {/* Map Legend */}
      <div className="map-legend-strip">
        <div className="legend-item"><div className="legend-chip shelf" /> Shelf Racks</div>
        <div className="legend-item"><div className="legend-chip pickup" /> Pickup (P1-P4)</div>
        <div className="legend-item"><div className="legend-chip dropoff" /> Dropoff (D1-D4)</div>
        <div className="legend-item"><div className="legend-chip dock" /> Charging Docks</div>
        <div className="legend-item"><div className="legend-chip obstacle">B</div> Dynamic Obstacle (B)</div>
        <div className="legend-item"><div className="legend-chip route" /> Active A* Route</div>
        <div className="legend-item"><div className="legend-chip replan" /> Re-routing Trail</div>
        <div className="legend-item"><div className="legend-chip target">TD</div> Target Destination</div>
      </div>
    </div>
  );
}

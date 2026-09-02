import React from 'react';
import { Cpu, Terminal, Activity, Layers, Bot, Maximize2 } from 'lucide-react';

export default function SimulationSection() {
  return (
    <div className="tab-transition-wrapper">
      {/* View Header */}
      <div className="view-header">
        <div className="view-badge">
          <Cpu size={14} color="var(--cyan-bright)" />
          <span>SIMULATION ENGINE // LIVE MOUNT PORTAL</span>
        </div>
        <h2 className="view-title">Autonomous Warehouse Simulation</h2>
        <p className="view-subtitle">
          Interactive simulation workspace for 3D multi-agent fleet trajectory modeling and real-time warehouse dynamics.
        </p>
      </div>

      {/* Clean Simulation Stage / Integration Container */}
      <div
        className="simulation-integration-mount"
        id="simulation-viewport"
        style={{
          position: 'relative',
          width: '100%',
          minHeight: '600px',
          background: 'radial-gradient(circle at 50% 50%, rgba(10, 16, 26, 0.95), rgba(4, 7, 12, 1))',
          border: '1px solid var(--border-medium)',
          borderRadius: '14px',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6), inset 0 0 40px rgba(56, 189, 248, 0.03)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          padding: '2rem',
        }}
      >
        {/* Subtle high-tech grid overlay */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundImage: `
              linear-gradient(rgba(56, 189, 248, 0.05) 1px, transparent 1px),
              linear-gradient(90deg, rgba(56, 189, 248, 0.05) 1px, transparent 1px)
            `,
            backgroundSize: '40px 40px',
            pointerEvents: 'none',
          }}
        />

        {/* Corner Brackets */}
        <div className="corner-bracket top-left" />
        <div className="corner-bracket top-right" />
        <div className="corner-bracket bottom-left" />
        <div className="corner-bracket bottom-right" />

        {/* Top Simulation HUD Bar */}
        <div
          style={{
            position: 'absolute',
            top: '1.5rem',
            left: '1.5rem',
            right: '1.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            zIndex: 10,
          }}
        >
          <div className="slide-hud-badge">
            <span className="hud-pulse-dot" style={{ backgroundColor: 'var(--green-online)' }} />
            <span>SIMULATION ENVIRONMENT READY</span>
          </div>

          <div
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <Activity size={13} color="var(--cyan-primary)" />
            <span>PORT // 8080</span>
          </div>
        </div>

        {/* Center Mount Placeholder (Friend's simulation attaches here) */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            gap: '1.25rem',
            maxWidth: '550px',
            zIndex: 10,
          }}
        >
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '16px',
              background: 'rgba(56, 189, 248, 0.1)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 25px rgba(56, 189, 248, 0.15)',
            }}
          >
            <Bot size={32} color="var(--cyan-bright)" />
          </div>

          <div>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffffff', marginBottom: '0.5rem' }}>
              Simulation Module Container
            </h3>
            <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              Attach your live 3D warehouse simulation, Three.js canvas, or ROS2 digital twin component here.
            </p>
          </div>

          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.6rem',
              padding: '0.5rem 1rem',
              background: 'rgba(10, 15, 24, 0.8)',
              border: '1px dashed rgba(56, 189, 248, 0.3)',
              borderRadius: '6px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              color: 'var(--cyan-primary)',
            }}
          >
            <Terminal size={13} />
            <span>MOUNT POINT: #simulation-viewport</span>
          </div>
        </div>
      </div>
    </div>
  );
}

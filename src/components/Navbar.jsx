import React from 'react';
import { Layers, Cpu, Activity } from 'lucide-react';

export default function Navbar({ isVisible, activeTab, onTabChange }) {
  return (
    <nav className={`site-navbar ${isVisible ? 'navbar-visible' : 'navbar-hidden'}`}>
      <div className="navbar-inner">
        {/* Left: Branding with Geometric SVG Logo & Status Indicator */}
        <div className="navbar-left" onClick={() => onTabChange('features')}>
          <div className="nav-brand-group">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="brand-logo-icon">
              <path d="M12 2L3 7V17L12 22L21 17V7L12 2Z" stroke="#38bdf8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M12 6L7.5 8.5V13.5L12 16L16.5 13.5V8.5L12 6Z" fill="rgba(56, 189, 248, 0.18)" stroke="#60a5fa" strokeWidth="1.4" />
              <circle cx="12" cy="11" r="2" fill="#38bdf8" />
            </svg>
            <span className="nav-brand-title">ROBOSYNC</span>
          </div>
          <div className="nav-status-pill">
            <span className="nav-status-dot" />
            <span>ONLINE</span>
          </div>
        </div>

        {/* Center: Primary Navigation Tabs */}
        <div className="navbar-tabs">
          <button
            className={`nav-tab-btn ${activeTab === 'features' ? 'active' : ''}`}
            onClick={() => onTabChange('features')}
          >
            <Layers size={14} />
            <span>FEATURES</span>
          </button>
          <button
            className={`nav-tab-btn ${activeTab === 'simulation' ? 'active' : ''}`}
            onClick={() => onTabChange('simulation')}
          >
            <Cpu size={14} />
            <span>SIMULATION</span>
          </button>
        </div>

        {/* Right: Live Telemetry Indicator */}
        <div className="navbar-right">
          <div className="telemetry-counter">
            <Activity size={13} color="var(--accent-cyan)" />
            <span>FLEET:</span>
            <span className="telemetry-counter-val">14 AMRs ACTIVE</span>
          </div>
        </div>
      </div>
    </nav>
  );
}

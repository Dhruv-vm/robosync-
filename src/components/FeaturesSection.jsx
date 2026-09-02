import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Play,
  Pause,
  Maximize2,
  Radio,
  Compass,
  Radar,
  ShieldCheck,
  Zap,
  Activity,
  Cpu,
  Terminal,
  Layers,
  ArrowRight
} from 'lucide-react';

const CAROUSEL_FEATURES = [
  {
    id: 'p2p-coordination',
    num: '01',
    title: 'Peer-to-Peer (P2P) Mesh Swarm Coordination',
    tag: 'DECENTRALIZED AGENT COMMUNICATION',
    description:
      'Decentralized peer-to-peer communication enables Autonomous Mobile Robots (AMRs) to broadcast spatial telemetry, negotiate high-traffic aisle intersections, and coordinate material transit directly without relying on a central point of failure.',
    image: '/frames/frame-1.png',
    icon: Radio,
    stats: [
      { label: 'MESH PROTOCOL', val: '5G NR / Wi-Fi 6' },
      { label: 'PEER LATENCY', val: '< 4 ms' },
      { label: 'SWARM COHESION', val: '99.98%' },
      { label: 'CENTRAL OVERHEAD', val: '0% Bottleneck' },
    ],
    highlightColor: '#38bdf8',
  },
  {
    id: 'deadlock-elimination',
    num: '02',
    title: 'Dynamic Spacetime Deadlock Elimination',
    tag: '4D CONFLICT DETECTION & RESOLUTION',
    description:
      'Advanced time-space path reservation algorithms project robot velocity and heading vectors into 4D spacetime coordinates, proactively detecting topological grid deadlocks and resolving intersection contention before vehicles meet.',
    image: '/frames/frame-7.png',
    icon: Compass,
    stats: [
      { label: 'PATHFINDING', val: '4D Spacetime A*' },
      { label: 'ACTIVE DEADLOCKS', val: '0 (Guaranteed)' },
      { label: 'PREDICTION HORIZON', val: '60 Seconds' },
      { label: 'RESERVATION TYPE', val: 'Voxel Lock Array' },
    ],
    highlightColor: '#60a5fa',
  },
  {
    id: 'blocked-aisle-rerouting',
    num: '03',
    title: 'Blocked Aisle Real-Time Re-Routing',
    tag: 'ADAPTIVE OBSTACLE EVASION & CORRIDOR BYPASS',
    description:
      'When aisles are obstructed by fallen cargo, maintenance activity, or stationary pallets, onboard 360° LiDAR instantly detects the barrier and calculates dynamic alternative bypass routes across adjacent corridors in under 15ms.',
    image: '/frames/frame-14.png',
    icon: Radar,
    stats: [
      { label: 'REROUTE CALCULATION', val: '< 15 ms' },
      { label: 'OBSTACLE SENSING', val: '360° LiDAR + AI' },
      { label: 'THROUGHPUT RETENTION', val: '98.6%' },
      { label: 'DISPATCH NOTIFY', val: 'Instant Fleetwide' },
    ],
    highlightColor: '#f59e0b',
  },
];

const SUBSYSTEM_SPECS = [
  {
    title: 'P2P Gossip & Consensus Protocol',
    icon: Radio,
    desc: 'AMR nodes exchange localized velocity, priority weights, and target destination packets via ultra-fast UDP multicast broadcast.',
    badge: 'DECENTRALIZED',
  },
  {
    title: 'Spacetime Voxel Conflict Engine',
    icon: Compass,
    desc: 'Each physical movement reservations locks a 1.2m³ spacetime bounding box, preventing two robots from ever requiring the same physical tile.',
    badge: 'ZERO DEADLOCKS',
  },
  {
    title: 'Real-Time Aisle Obstacle Evader',
    icon: Radar,
    desc: 'Dense point-cloud clustering identifies static obstructions versus moving obstacles, dynamically re-weighting navigation costmaps.',
    badge: 'DYNAMIC BYPASS',
  },
];

export default function FeaturesSection() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [selectedSpec, setSelectedSpec] = useState(0);
  const [isZoomed, setIsZoomed] = useState(false);
  const autoPlayRef = useRef(null);

  const currentFeature = CAROUSEL_FEATURES[currentIndex];
  const IconComponent = currentFeature.icon;

  const nextSlide = () => {
    setCurrentIndex((prev) => (prev + 1) % CAROUSEL_FEATURES.length);
  };

  const prevSlide = () => {
    setCurrentIndex((prev) => (prev - 1 + CAROUSEL_FEATURES.length) % CAROUSEL_FEATURES.length);
  };

  // Autoplay Timer
  useEffect(() => {
    if (!isPlaying) {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
      return;
    }

    autoPlayRef.current = setInterval(() => {
      nextSlide();
    }, 5000);

    return () => {
      if (autoPlayRef.current) clearInterval(autoPlayRef.current);
    };
  }, [isPlaying, currentIndex]);

  // Keyboard Navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowRight') nextSlide();
      if (e.key === 'ArrowLeft') prevSlide();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="tab-transition-wrapper">
      {/* Header */}
      <div className="view-header">
        <div className="view-badge">
          <Sparkles size={14} color="var(--cyan-bright)" />
          <span>CYBER-PHYSICAL INTELLIGENCE // 3 CORE CAPABILITIES</span>
        </div>
        <h2 className="view-title">Autonomous Fleet Navigation Capabilities</h2>
        <p className="view-subtitle">
          Explore RoboSync's 3 primary autonomous pillars: Peer-to-Peer Swarm Coordination, Dynamic Spacetime Deadlock Elimination, and Instant Blocked-Aisle Re-routing.
        </p>
      </div>

      {/* =========================================================
          IMAGE CAROUSEL (CLEAN IMAGE STAGE - ZERO TEXT OVERLAY)
          ========================================================= */}
      <div className="carousel-master-wrapper">
        {/* 1. Clean Unobstructed Image Stage */}
        <div className="carousel-stage-container">
          <div className="carousel-image-viewport">
            <img
              src={currentFeature.image}
              alt={currentFeature.title}
              className={`carousel-display-img ${isZoomed ? 'zoomed' : ''}`}
            />
            {/* Subtle high-tech accents */}
            <div className="carousel-scanline-overlay" />
            <div className="corner-bracket top-left" />
            <div className="corner-bracket top-right" />
            <div className="corner-bracket bottom-left" />
            <div className="corner-bracket bottom-right" />

            {/* Top Minimal HUD Controls */}
            <div className="carousel-slide-hud-top">
              <div className="slide-hud-badge">
                <span className="hud-pulse-dot" style={{ backgroundColor: currentFeature.highlightColor }} />
                <span>FEATURE {currentFeature.num} / 03</span>
              </div>
              <div className="slide-hud-controls">
                <button
                  className="carousel-icon-btn"
                  onClick={() => setIsPlaying(!isPlaying)}
                  title={isPlaying ? 'Pause Auto-Advance' : 'Resume Auto-Advance'}
                >
                  {isPlaying ? <Pause size={14} /> : <Play size={14} />}
                </button>
                <button
                  className="carousel-icon-btn"
                  onClick={() => setIsZoomed(!isZoomed)}
                  title={isZoomed ? 'Reset View' : 'Inspect Details'}
                >
                  <Maximize2 size={14} />
                </button>
              </div>
            </div>
          </div>

          {/* Carousel Arrow Buttons */}
          <button className="carousel-arrow-btn left" onClick={prevSlide} aria-label="Previous Feature">
            <ChevronLeft size={24} />
          </button>
          <button className="carousel-arrow-btn right" onClick={nextSlide} aria-label="Next Feature">
            <ChevronRight size={24} />
          </button>
        </div>

        {/* 2. Feature Information Display Box (Placed CLEANLY BELOW the image) */}
        <div className="carousel-info-panel-below">
          <div className="info-panel-header">
            <div className="slide-tag" style={{ color: currentFeature.highlightColor }}>
              <IconComponent size={16} />
              <span>{currentFeature.tag}</span>
            </div>
            <div className="info-panel-index-badge">
              MODULE {currentFeature.num}
            </div>
          </div>

          <h3 className="info-panel-title">{currentFeature.title}</h3>
          <p className="info-panel-description">{currentFeature.description}</p>

          {/* 4 Metric Spec Cards */}
          <div className="info-panel-stats-grid">
            {currentFeature.stats.map((stat, idx) => (
              <div key={idx} className="info-stat-card">
                <span className="info-stat-label">{stat.label}</span>
                <span className="info-stat-value" style={{ color: currentFeature.highlightColor }}>
                  {stat.val}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 3. 3-Feature Interactive Selector Filmstrip */}
        <div className="carousel-filmstrip">
          {CAROUSEL_FEATURES.map((item, idx) => {
            const ItemIcon = item.icon;
            const isActive = idx === currentIndex;
            return (
              <div
                key={item.id}
                className={`filmstrip-card ${isActive ? 'active' : ''}`}
                onClick={() => {
                  setCurrentIndex(idx);
                  setIsPlaying(false);
                }}
              >
                <div className="filmstrip-thumb-wrap">
                  <img src={item.image} alt={item.title} className="filmstrip-thumb-img" />
                  <div className="filmstrip-thumb-overlay" />
                  <div className="filmstrip-thumb-icon">
                    <ItemIcon size={14} color={isActive ? item.highlightColor : '#94a3b8'} />
                  </div>
                </div>
                <div className="filmstrip-info">
                  <span className="filmstrip-num">0{idx + 1} // CAPABILITY</span>
                  <span className="filmstrip-name">{item.title}</span>
                </div>
                {isActive && (
                  <div className="filmstrip-active-bar" style={{ backgroundColor: item.highlightColor }} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* =========================================================
          DEEP DIVE SUBSYSTEM SPECS MATRIX
          ========================================================= */}
      <div className="features-deepdive-section">
        <div className="section-title-wrap">
          <div className="view-badge">
            <Terminal size={14} />
            <span>TECHNICAL BENCHMARKS</span>
          </div>
          <h3 className="section-subheading">Autonomous Core Subsystem Breakdown</h3>
        </div>

        {/* 3 Subsystem Deep Dive Cards */}
        <div className="architecture-grid">
          {SUBSYSTEM_SPECS.map((layer, idx) => {
            const LayerIcon = layer.icon;
            const isSelected = idx === selectedSpec;
            return (
              <div
                key={idx}
                className={`arch-card ${isSelected ? 'selected' : ''}`}
                onClick={() => setSelectedSpec(idx)}
              >
                <div className="arch-card-header">
                  <div className="arch-icon-bubble">
                    <LayerIcon size={20} color="var(--cyan-primary)" />
                  </div>
                  <span className="arch-badge">{layer.badge}</span>
                </div>
                <h4 className="arch-title">{layer.title}</h4>
                <p className="arch-desc">{layer.desc}</p>
                <div className="arch-glow-line" />
              </div>
            );
          })}
        </div>

        {/* Live System Specification & Capability Banner */}
        <div className="capability-specs-banner">
          <div className="spec-banner-column">
            <div className="spec-banner-icon">
              <Radio size={24} color="var(--cyan-bright)" />
            </div>
            <div>
              <div className="spec-banner-title">P2P Peer Broadcast</div>
              <div className="spec-banner-sub">Decentralized mesh gossip without single point of failure</div>
            </div>
          </div>

          <div className="spec-banner-column">
            <div className="spec-banner-icon">
              <ShieldCheck size={24} color="var(--green-online)" />
            </div>
            <div>
              <div className="spec-banner-title">Zero Deadlock Guarantee</div>
              <div className="spec-banner-sub">Time-space voxel reservations eliminate cross-traffic gridlocks</div>
            </div>
          </div>

          <div className="spec-banner-column">
            <div className="spec-banner-icon">
              <Zap size={24} color="var(--amber-warning)" />
            </div>
            <div>
              <div className="spec-banner-title">&lt; 15ms Blocked Aisle Bypass</div>
              <div className="spec-banner-sub">Dynamic costmap re-routing around static/moving barriers</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

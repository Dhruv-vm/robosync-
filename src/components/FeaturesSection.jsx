import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Radio,
  Radar,
  Compass,
  Sparkles,
} from 'lucide-react';

const CAPABILITIES = [
  {
    id: 'p2p-mesh',
    number: '01',
    category: 'SWARM COORDINATION',
    tag: 'SYSTEM 01 // P2P SWARM PROTOCOL',
    title: 'Peer-to-Peer (P2P) Mesh Swarm Coordination',
    shortTitle: 'P2P Swarm Coordination',
    description:
      'AMRs communicate directly through decentralized ad-hoc mesh networking, exchanging spatial telemetry and velocity vectors without relying on a central controller or single point of failure.',
    image: '/features/p2p-mesh.jpeg',
    accentColor: '#38bdf8',
    icon: Radio,
    telemetry: [
      { label: 'TOPOLOGY', val: 'DECENTRALIZED P2P' },
      { label: 'LATENCY', val: '< 3.5 MS' },
      { label: 'FAULT TOLERANCE', val: '100% NO SPOF' },
    ],
  },
  {
    id: 'blocked-aisle',
    number: '02',
    category: 'DYNAMIC ROUTING',
    tag: 'SYSTEM 02 // DYNAMIC OBSTACLE EVASION',
    title: 'Blocked Aisle Real-Time Re-Routing',
    shortTitle: 'Blocked Aisle Re-Routing',
    description:
      'Onboard 360° perception instantly detects unexpected obstructions, dynamically re-weights grid costmaps, and calculates collision-free local A* bypass routes in under 12ms.',
    image: '/features/blocked-aisle.jpeg',
    accentColor: '#f87171',
    icon: Radar,
    telemetry: [
      { label: 'REPLAN TIME', val: '< 12 MS' },
      { label: 'PERCEPTION', val: '360° MULTI-SENSOR' },
      { label: 'THROUGHPUT', val: '99.2% RETENTION' },
    ],
  },
  {
    id: 'deadlock',
    number: '03',
    category: 'DEADLOCK RESOLUTION',
    tag: 'SYSTEM 03 // 4D TIME-SPACE MUTEX',
    title: 'Spatiotemporal Deadlock Elimination',
    shortTitle: 'Deadlock Elimination',
    description:
      'High-density multi-AMR intersection bottlenecks are resolved through forward 4D space-time reservations and decentralized priority bidding, guaranteeing zero deadlock cycles.',
    image: '/features/deadlock.jpeg',
    accentColor: '#38bdf8',
    icon: Compass,
    telemetry: [
      { label: 'LOCK ARRAY', val: '4D TIME-SPACE MUTEX' },
      { label: 'DEADLOCK RISK', val: '0.00% GUARANTEED' },
      { label: 'LOOKAHEAD', val: '60S PREDICTION' },
    ],
  },
];

export default function FeaturesSection() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [slideDirection, setSlideDirection] = useState('next');
  const touchStartXRef = useRef(null);
  const touchEndXRef = useRef(null);

  const currentSlide = CAPABILITIES[currentIndex];
  const IconComponent = currentSlide.icon;

  const handleNext = useCallback(() => {
    if (isTransitioning) return;
    setSlideDirection('next');
    setIsTransitioning(true);
    setCurrentIndex((prev) => (prev + 1) % CAPABILITIES.length);
    setTimeout(() => setIsTransitioning(false), 450);
  }, [isTransitioning]);

  const handlePrev = useCallback(() => {
    if (isTransitioning) return;
    setSlideDirection('prev');
    setIsTransitioning(true);
    setCurrentIndex((prev) => (prev - 1 + CAPABILITIES.length) % CAPABILITIES.length);
    setTimeout(() => setIsTransitioning(false), 450);
  }, [isTransitioning]);

  const handleGoTo = (idx) => {
    if (idx === currentIndex || isTransitioning) return;
    setSlideDirection(idx > currentIndex ? 'next' : 'prev');
    setIsTransitioning(true);
    setCurrentIndex(idx);
    setTimeout(() => setIsTransitioning(false), 450);
  };

  // Keyboard navigation (ArrowLeft / ArrowRight)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowRight') handleNext();
      if (e.key === 'ArrowLeft') handlePrev();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleNext, handlePrev]);

  // Touch / Swipe Navigation on Mobile
  const handleTouchStart = (e) => {
    touchStartXRef.current = e.targetTouches[0].clientX;
  };

  const handleTouchMove = (e) => {
    touchEndXRef.current = e.targetTouches[0].clientX;
  };

  const handleTouchEnd = () => {
    if (!touchStartXRef.current || !touchEndXRef.current) return;
    const distance = touchStartXRef.current - touchEndXRef.current;
    const minSwipeDistance = 45;
    if (distance > minSwipeDistance) {
      handleNext();
    } else if (distance < -minSwipeDistance) {
      handlePrev();
    }
    touchStartXRef.current = null;
    touchEndXRef.current = null;
  };

  return (
    <div className="tab-transition-wrapper cinematic-features-section">
      {/* 1. Technical Section Header */}
      <div className="features-technical-header">
        <div className="features-eyebrow-badge">
          <Sparkles size={13} color="var(--accent-cyan)" />
          <span>CYBER-PHYSICAL INTELLIGENCE // 3 CORE CAPABILITIES</span>
        </div>
        <h2 className="features-main-heading">Autonomous Fleet Navigation Capabilities</h2>
        <p className="features-main-subtitle">
          Explore RoboSync's 3 primary autonomous pillars: Peer-to-Peer Swarm Coordination, Blocked-Aisle Real-Time Re-routing, and Spatiotemporal Deadlock Elimination.
        </p>
      </div>

      {/* 2. Spacious Split Showcase Card */}
      <div
        className="capability-showcase-frame"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Left Column: Dedicated Information Briefing & Controls */}
        <div className="capability-briefing-col">
          <div className="briefing-header-row">
            <div className="briefing-counter-chip mono">
              <span className="counter-current">{currentSlide.number}</span>
              <span className="counter-sep">/</span>
              <span className="counter-total">03</span>
            </div>
            <div
              className="briefing-category-chip mono"
              style={{
                borderColor: `${currentSlide.accentColor}40`,
                color: currentSlide.accentColor,
                background: `${currentSlide.accentColor}12`,
              }}
            >
              <IconComponent size={12} />
              <span>{currentSlide.category}</span>
            </div>
          </div>

          <div className="briefing-text-block">
            <h3 className="briefing-title">{currentSlide.title}</h3>
            <p className="briefing-desc">{currentSlide.description}</p>
          </div>

          {/* 3 Compact Technical Metric Chips */}
          <div className="briefing-metrics-grid">
            {currentSlide.telemetry.map((t, idx) => (
              <div key={idx} className="metric-chip-card">
                <span className="metric-chip-label mono">{t.label}</span>
                <span
                  className="metric-chip-val mono"
                  style={{ color: currentSlide.accentColor }}
                >
                  {t.val}
                </span>
              </div>
            ))}
          </div>

          {/* Navigation Controls Row */}
          <div className="briefing-controls-row">
            <div className="briefing-nav-arrows">
              <button
                className="btn-briefing-arrow"
                onClick={handlePrev}
                aria-label="Previous Capability"
                title="Previous (Arrow Left)"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                className="btn-briefing-arrow"
                onClick={handleNext}
                aria-label="Next Capability"
                title="Next (Arrow Right)"
              >
                <ChevronRight size={16} />
              </button>
            </div>

            {/* Segmented Progress Track */}
            <div className="briefing-progress-track">
              {CAPABILITIES.map((cap, idx) => {
                const isActive = idx === currentIndex;
                return (
                  <button
                    key={cap.id}
                    className={`briefing-segment-btn ${isActive ? 'active' : ''}`}
                    onClick={() => handleGoTo(idx)}
                    aria-label={`Jump to ${cap.shortTitle}`}
                    title={cap.shortTitle}
                  >
                    <div
                      className="segment-bar-line"
                      style={{
                        backgroundColor: isActive ? cap.accentColor : undefined,
                      }}
                    />
                    <span className="segment-bar-label mono">
                      {cap.number} {cap.shortTitle}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Clean Unobstructed Cinematic Image Panel */}
        <div className="capability-image-col">
          <div className="image-panel-container">
            {/* Technical Corner Bracket Ticks */}
            <div className="panel-corner-tick top-left" />
            <div className="panel-corner-tick top-right" />
            <div className="panel-corner-tick bottom-left" />
            <div className="panel-corner-tick bottom-right" />

            {/* Minimal Floating System Tag */}
            <div className="image-panel-tag-top mono">
              <span
                className="panel-tag-dot"
                style={{ backgroundColor: currentSlide.accentColor }}
              />
              <span>{currentSlide.tag}</span>
            </div>

            {/* Image Viewport (Clean, Uncluttered, No Overlapping Text) */}
            <div className="image-panel-viewport">
              <img
                key={currentSlide.id}
                src={currentSlide.image}
                alt={currentSlide.title}
                className={`showcase-panel-img ${isTransitioning ? `fade-${slideDirection}` : 'active'}`}
                loading="eager"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import React, { useState, useCallback } from 'react';
import WarehouseFrameScroll from '../components/WarehouseFrameScroll';
import Navbar from '../components/Navbar';
import FeaturesSection from '../components/FeaturesSection';
import SimulationSection from '../components/SimulationSection';
import Footer from '../components/Footer';

export default function Home() {
  const [activeTab, setActiveTab] = useState('features');
  const [navbarVisible, setNavbarVisible] = useState(false);

  const handleHeroComplete = useCallback((completed) => {
    setNavbarVisible((prev) => (prev !== completed ? completed : prev));
  }, []);

  const handleTabChange = useCallback((tab) => {
    setActiveTab(tab);
    const contentEl = document.getElementById('interactive-dashboard');
    if (contentEl && window.scrollY < window.innerHeight) {
      contentEl.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  return (
    <div className="app-wrapper">
      {/* 1. Main Hero: Cinematic Warehouse Scroll Sequence */}
      <WarehouseFrameScroll onHeroComplete={handleHeroComplete} />

      {/* 2. Sticky Navbar (Revealed after Hero sequence) */}
      <Navbar
        isVisible={navbarVisible}
        activeTab={activeTab}
        onTabChange={handleTabChange}
      />

      {/* 3. Interactive Views (Features & Simulation) */}
      <main className="main-view-container" id="interactive-dashboard">
        {activeTab === 'features' ? (
          <FeaturesSection />
        ) : (
          <SimulationSection />
        )}
      </main>

      {/* 4. Footer */}
      <Footer />
    </div>
  );
}

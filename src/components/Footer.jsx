import React from 'react';

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-left">
          <div className="footer-brand">ROBOSYNC</div>
          <div className="footer-meta">
            Autonomous Cyber-Physical Warehouse System &bull; SIH Edition
          </div>
        </div>

        <div className="footer-right">
          <div>COORDINATES: LAT 28.6139° N, LONG 77.2090° E</div>
          <div>STATUS: SLAM CORE OPERATIONAL // VERSION 2.4.0</div>
        </div>
      </div>
    </footer>
  );
}

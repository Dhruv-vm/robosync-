import React, { useEffect, useRef, useState, useCallback, memo } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ChevronDown } from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

function WarehouseFrameScroll({ onHeroComplete }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const progressLineRef = useRef(null);
  const scrollCueRef = useRef(null);

  const imagesRef = useRef([]);
  const lastDrawnFrameRef = useRef(-1);
  const lastHeroStateRef = useRef(false);
  const drawRectRef = useRef({ offsetX: 0, offsetY: 0, drawWidth: 0, drawHeight: 0 });

  const [isReady, setIsReady] = useState(false);

  // Synchronous direct-to-canvas GPU paint (0ms latency, zero queue build-up)
  const drawFrameSync = useCallback((frameIndex) => {
    if (frameIndex === lastDrawnFrameRef.current) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;

    let img = imagesRef.current[frameIndex];
    if (!img || !img.complete || img.naturalWidth === 0) {
      img = imagesRef.current[lastDrawnFrameRef.current] || imagesRef.current[0];
    }
    if (!img || !img.complete || img.naturalWidth === 0) return;

    const { offsetX, offsetY, drawWidth, drawHeight } = drawRectRef.current;
    ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);
    lastDrawnFrameRef.current = frameIndex;
  }, []);

  // Recalculate canvas size & aspect-ratio cover metrics ONLY on window resize
  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const newWidth = Math.round(rect.width * dpr);
    const newHeight = Math.round(rect.height * dpr);

    if (canvas.width !== newWidth || canvas.height !== newHeight) {
      canvas.width = newWidth;
      canvas.height = newHeight;
    }

    const refImg = imagesRef.current[0] || imagesRef.current[lastDrawnFrameRef.current];
    const naturalW = refImg?.naturalWidth || 1680;
    const naturalH = refImg?.naturalHeight || 936;
    const imgRatio = naturalW / naturalH;
    const canvasRatio = newWidth / newHeight;

    let drawWidth, drawHeight, offsetX, offsetY;
    if (canvasRatio > imgRatio) {
      drawWidth = newWidth;
      drawHeight = newWidth / imgRatio;
      offsetX = 0;
      offsetY = (newHeight - drawHeight) / 2;
    } else {
      drawHeight = newHeight;
      drawWidth = newHeight * imgRatio;
      offsetX = (newWidth - drawWidth) / 2;
      offsetY = 0;
    }

    drawRectRef.current = { offsetX, offsetY, drawWidth, drawHeight };

    // Force immediate redraw of current frame with updated geometry
    const curFrame = Math.max(0, lastDrawnFrameRef.current);
    lastDrawnFrameRef.current = -1;
    drawFrameSync(curFrame);
  }, [drawFrameSync]);

  // Dynamically discover, load, and GPU-decode ALL available sequential frames
  useEffect(() => {
    let isCancelled = false;

    const loadAllAvailableFrames = async () => {
      const MAX_PROBE_FRAMES = 60; // Probes up to 60 frames in parallel
      const probePromises = Array.from({ length: MAX_PROBE_FRAMES }, (_, i) => {
        const idx = i + 1;
        return new Promise((resolve) => {
          const img = new Image();
          img.src = `/frames/frame-${idx}.png`;

          img.onload = async () => {
            if (img.decode) {
              try {
                await img.decode();
              } catch {
                // Decode fallback
              }
            }
            resolve({ index: idx, img, valid: true });
          };

          img.onerror = () => {
            resolve({ index: idx, img: null, valid: false });
          };
        });
      });

      const results = await Promise.all(probePromises);

      // Collect all continuous valid frames in strict numerical order (1, 2, 3...)
      const validFrames = [];
      for (let i = 0; i < results.length; i++) {
        const match = results.find((r) => r.index === i + 1);
        if (match && match.valid) {
          validFrames.push(match.img);
        } else {
          break; // Stop at end of sequential set
        }
      }

      if (!isCancelled && validFrames.length > 0) {
        imagesRef.current = validFrames;
        setIsReady(true);
      }
    };

    loadAllAvailableFrames();

    return () => {
      isCancelled = true;
    };
  }, []);

  // Initialize ScrollTrigger with direct 1-to-1 physical wheel synchronization
  useEffect(() => {
    if (!isReady || !containerRef.current || !canvasRef.current || imagesRef.current.length === 0) return;

    resizeCanvas();
    drawFrameSync(0);

    const handleResize = () => {
      resizeCanvas();
      ScrollTrigger.refresh();
    };

    window.addEventListener('resize', handleResize);

    const totalFrames = imagesRef.current.length;
    const scrollDistance = Math.max(2200, totalFrames * 105);

    const ctx = gsap.context(() => {
      ScrollTrigger.create({
        trigger: containerRef.current,
        start: 'top top',
        end: `+=${scrollDistance}`, // Calibrated for smooth, tactile mouse-wheel travel
        pin: true,
        scrub: true, // Direct 1-to-1 coupling (0ms lag)
        onUpdate: (self) => {
          const p = self.progress;

          // Continuous mapping: 0.0 -> 0.92 across all discovered frames, holding final frame at [0.92, 1.00]
          const normalized = p >= 0.92 ? 1 : p / 0.92;
          const targetFrame = Math.min(
            totalFrames - 1,
            Math.max(0, Math.round(normalized * (totalFrames - 1)))
          );

          // Direct synchronous GPU draw
          drawFrameSync(targetFrame);

          // Direct DOM visual indicator updates
          if (progressLineRef.current) {
            progressLineRef.current.style.width = `${p * 100}%`;
          }
          if (scrollCueRef.current) {
            const cueOpacity = p > 0.08 ? 0 : Math.max(0, 1 - p * 12);
            scrollCueRef.current.style.opacity = cueOpacity;
            scrollCueRef.current.style.pointerEvents = p > 0.05 ? 'none' : 'auto';
          }

          // State transition for sticky navbar
          const isComplete = p >= 0.88;
          if (lastHeroStateRef.current !== isComplete) {
            lastHeroStateRef.current = isComplete;
            if (onHeroComplete) {
              onHeroComplete(isComplete);
            }
          }
        },
      });
    }, containerRef);

    return () => {
      window.removeEventListener('resize', handleResize);
      ctx.revert();
    };
  }, [isReady, resizeCanvas, drawFrameSync, onHeroComplete]);

  return (
    <div className="hero-scroll-container" id="hero-experience">
      <div ref={containerRef} className="hero-pinned-viewport">
        {/* High-Performance Canvas */}
        <canvas ref={canvasRef} className="hero-canvas" />

        {/* Minimal Preloader (shown only briefly before interaction starts) */}
        {!isReady && (
          <div className="hero-preloader">
            <div className="preloader-glow" />
            <div className="preloader-spinner" />
            <div className="preloader-title">ROBOSYNC</div>
            <div className="preloader-status">INITIALIZING CINEMATIC ENVIRONMENT</div>
          </div>
        )}

        {/* Pure Cinematic Overlays - ZERO Frame Numbers */}
        {isReady && (
          <>
            {/* Top Left: Ultra-Crisp Frosted Glass Capsule */}
            <div className="hero-overlay-top-left">
              <div className="brand-wordmark">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="brand-logo-icon">
                  <path d="M12 2L3 7V17L12 22L21 17V7L12 2Z" stroke="#38bdf8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M12 6L7.5 8.5V13.5L12 16L16.5 13.5V8.5L12 6Z" fill="rgba(56, 189, 248, 0.25)" stroke="#60a5fa" strokeWidth="1.4" />
                  <circle cx="12" cy="11" r="2" fill="#38bdf8" />
                </svg>
                <span>ROBOSYNC</span>
                <div className="brand-status-chip">
                  <span className="brand-dot" />
                  <span>LIVE</span>
                </div>
              </div>
              <div className="brand-system-tag">
                AUTONOMOUS WAREHOUSE INTELLIGENCE
              </div>
            </div>

            {/* Bottom Center: Minimal Scroll Hint */}
            <div ref={scrollCueRef} className="hero-overlay-bottom-center">
              <span className="scroll-cue-text">SCROLL TO ENTER THE SYSTEM</span>
              <ChevronDown size={18} className="scroll-cue-arrow" />
            </div>

            {/* Bottom Linear Scroll Progress Indicator (Pure visual line) */}
            <div className="hero-progress-line-container">
              <div ref={progressLineRef} className="hero-progress-line-bar" style={{ width: '0%' }} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default memo(WarehouseFrameScroll);

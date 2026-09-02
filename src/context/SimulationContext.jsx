import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import simulationApi from '../services/simulationApi';

export const ConnectionStatus = {
  CONNECTING: 'CONNECTING',
  CONNECTED: 'CONNECTED',
  DISCONNECTED: 'DISCONNECTED',
  ERROR: 'ERROR',
};

export const ViewMode = {
  COMMAND_HUB: 'COMMAND_HUB',
  MAP_2D: 'MAP_2D',
  FLEET_MATRIX: 'FLEET_MATRIX',
  TASKS_AUCTIONS: 'TASKS_AUCTIONS',
  EVENT_STREAM: 'EVENT_STREAM',
  SCENARIO_CONTROLS: 'SCENARIO_CONTROLS',
  SPLIT_VIEW: 'SPLIT_VIEW',
};

const SimulationContext = createContext(null);

export function SimulationProvider({ children }) {
  const [apiUrl, setApiUrlState] = useState(() => simulationApi.getApiUrl());
  const [connectionStatus, setConnectionStatus] = useState(ConnectionStatus.CONNECTING);
  const [errorMessage, setErrorMessage] = useState(null);
  const [simulationData, setSimulationData] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Selected AMR for deep telemetry inspector drawer
  const [selectedAmrId, setSelectedAmrId] = useState(null);

  // Dynamic View & Multi-System Layout configuration
  const [activeView, setActiveView] = useState(() => {
    try {
      return localStorage.getItem('robosync_active_view') || ViewMode.COMMAND_HUB;
    } catch {
      return ViewMode.COMMAND_HUB;
    }
  });

  const [splitLeftView, setSplitLeftView] = useState(ViewMode.MAP_2D);
  const [splitRightView, setSplitRightView] = useState(ViewMode.FLEET_MATRIX);

  const isPollingRef = useRef(false);
  const consecutiveErrorsRef = useRef(0);

  // Change view and persist locally for this display/browser session
  const setView = useCallback((view) => {
    setActiveView(view);
    try {
      localStorage.setItem('robosync_active_view', view);
    } catch {
      // Ignore
    }
  }, []);

  // Update backend URL at runtime without rebuilding
  const updateApiUrl = useCallback((newUrl) => {
    simulationApi.setApiUrl(newUrl);
    setApiUrlState(simulationApi.getApiUrl());
    setConnectionStatus(ConnectionStatus.CONNECTING);
    setErrorMessage(null);
    consecutiveErrorsRef.current = 0;
  }, []);

  const resetApiUrl = useCallback(() => {
    simulationApi.resetApiUrl();
    setApiUrlState(simulationApi.getApiUrl());
    setConnectionStatus(ConnectionStatus.CONNECTING);
    setErrorMessage(null);
    consecutiveErrorsRef.current = 0;
  }, []);

  // Fetch state tick
  const pollState = useCallback(async () => {
    if (isPollingRef.current) return;
    isPollingRef.current = true;

    try {
      const data = await simulationApi.getState(2000);
      setSimulationData(data);
      setLastUpdated(Date.now());
      setConnectionStatus(ConnectionStatus.CONNECTED);
      setErrorMessage(null);
      consecutiveErrorsRef.current = 0;
    } catch (err) {
      consecutiveErrorsRef.current += 1;
      if (consecutiveErrorsRef.current >= 2) {
        setConnectionStatus(
          err.name === 'AbortError' ? ConnectionStatus.ERROR : ConnectionStatus.DISCONNECTED
        );
        setErrorMessage(err.message || 'Connection to simulation host failed');
      }
    } finally {
      isPollingRef.current = false;
    }
  }, []);

  // Control dispatch
  const sendControl = useCallback(async (action, params = {}) => {
    try {
      const result = await simulationApi.sendControl(action, params);
      // Immediately trigger state fetch to reflect changes with 0 delay
      await pollState();
      return result;
    } catch (err) {
      console.error(`Control action "${action}" failed:`, err);
      throw err;
    }
  }, [pollState]);

  // Main polling loop (100ms standard refresh matching backend clock)
  useEffect(() => {
    let timerId = null;
    let isActive = true;

    const runLoop = async () => {
      if (!isActive) return;
      await pollState();
      if (isActive) {
        // Poll every 100ms when connected, back off to 1000ms when disconnected to avoid flooding network
        const delay = consecutiveErrorsRef.current >= 3 ? 1000 : 100;
        timerId = setTimeout(runLoop, delay);
      }
    };

    runLoop();

    return () => {
      isActive = false;
      if (timerId) clearTimeout(timerId);
    };
  }, [pollState, apiUrl]);

  // Derive selected AMR telemetry object
  const selectedAmr = simulationData?.fleet?.find((a) => a.robot_id === selectedAmrId) || null;

  const value = {
    apiUrl,
    updateApiUrl,
    resetApiUrl,
    connectionStatus,
    errorMessage,
    simulationData,
    lastUpdated,
    selectedAmrId,
    setSelectedAmrId,
    selectedAmr,
    activeView,
    setActiveView: setView,
    splitLeftView,
    setSplitLeftView,
    splitRightView,
    setSplitRightView,
    sendControl,
    pollState,
  };

  return (
    <SimulationContext.Provider value={value}>
      {children}
    </SimulationContext.Provider>
  );
}

export function useSimulation() {
  const context = useContext(SimulationContext);
  if (!context) {
    throw new Error('useSimulation must be used within a SimulationProvider');
  }
  return context;
}

/**
 * Simulation API Service
 * Handles REST communication with the Python Autonomous Warehouse backend.
 * Supports configurable runtime endpoint with localStorage persistence.
 */

const STORAGE_KEY = 'robosync_simulation_api_url';

export const getDefaultHostUrl = () => {
  if (import.meta.env.VITE_SIMULATION_API_URL) {
    return import.meta.env.VITE_SIMULATION_API_URL.replace(/\/+$/, '');
  }
  // In browser context: dynamically resolve to the host IP serving the frontend
  if (typeof window !== 'undefined' && window.location && window.location.hostname) {
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
    const host = window.location.hostname;
    return `${protocol}//${host}:8080`;
  }
  return 'http://localhost:8080';
};

class SimulationApiService {
  constructor() {
    this.apiUrl = this._loadInitialUrl();
  }

  _loadInitialUrl() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved && saved.trim()) {
        return saved.trim().replace(/\/+$/, '');
      }
    } catch {
      // LocalStorage fallback for non-browser/restricted environments
    }
    return getDefaultHostUrl();
  }

  getApiUrl() {
    return this.apiUrl;
  }

  setApiUrl(newUrl) {
    if (!newUrl || typeof newUrl !== 'string') return;
    const sanitized = newUrl.trim().replace(/\/+$/, '');
    this.apiUrl = sanitized;
    try {
      localStorage.setItem(STORAGE_KEY, sanitized);
    } catch {
      // Ignore storage errors
    }
  }

  resetApiUrl() {
    this.apiUrl = getDefaultHostUrl();
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore
    }
  }

  /**
   * Fetch complete real simulation snapshot from backend
   */
  async getState(timeoutMs = 2500) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const res = await fetch(`${this.apiUrl}/api/state`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timer);

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      return await res.json();
    } catch (err) {
      clearTimeout(timer);
      throw err;
    }
  }

  /**
   * Submit thread-safe control command to Python simulation engine
   */
  async sendControl(action, params = {}, timeoutMs = 3000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const res = await fetch(`${this.apiUrl}/api/control`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          action,
          params: params || {},
        }),
        signal: controller.signal,
      });

      clearTimeout(timer);

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      return await res.json();
    } catch (err) {
      clearTimeout(timer);
      throw err;
    }
  }
}

export const simulationApi = new SimulationApiService();
export default simulationApi;

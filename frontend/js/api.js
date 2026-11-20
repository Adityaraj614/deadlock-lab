/**
 * API Service for Deadlock Lab Frontend
 * 
 * Provides a reusable wrapper around the FastAPI backend endpoints.
 * Handles loading states, error handling, and connection status.
 */

const API_BASE = new URLSearchParams(window.location.search).get('api') || 'http://127.0.0.1:8000';
let connectionStatus = 'disconnected';
let lastError = null;

/**
 * Check if the backend is reachable.
 */
export async function checkConnection() {
    let errorMessage = 'Unknown error';
    try {
        const response = await fetch(`${API_BASE}/health`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            cache: 'no-cache',
        });
        
        if (response.ok) {
            connectionStatus = 'connected';
            lastError = null;
            return true;
        }
    } catch (error) {
        errorMessage = error instanceof Error ? error.message : errorMessage;
    }
    
    connectionStatus = 'disconnected';
    lastError = errorMessage;
    return false;
}

/**
 * Get the current connection status.
 */
export function getConnectionStatus() {
    return connectionStatus;
}

/**
 * Get the last error message.
 */
export function getLastError() {
    return lastError;
}

/**
 * Generic fetch handler with error handling.
 */
async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
    };
    
    const response = await fetch(url, {
        ...options,
        headers,
        cache: 'no-cache',
    });
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        lastError = errorData.detail || `HTTP ${response.status}`;
        connectionStatus = 'error';
        throw new Error(lastError);
    }
    
    connectionStatus = 'connected';
    lastError = null;
    return response.json();
}

/**
 * --- Health Endpoint ---
 */

/**
 * Check if the backend is healthy.
 */
export function healthCheck() {
    return apiFetch('/health');
}

/** --- Scenario Endpoints --- */

/**
 * List all available warehouse scenarios.
 */
export function listScenarios() {
    return apiFetch('/api/scenarios');
}

/**
 * Get a specific scenario by name.
 */
export function getScenario(name) {
    return apiFetch(`/api/scenarios/${name}`);
}

/** --- Simulation Lifecycle Endpoints --- */

/**
 * Load a warehouse scenario.
 * Returns a SimulationState with agents, obstacles, goals, and grid dimensions.
 */
export function loadScenario(name, strategy = 'full', maxSteps = 100) {
    return apiFetch(`/api/scenario/load/${name}`, {
        method: 'POST',
        body: JSON.stringify({ strategy, max_steps: maxSteps }),
    });
}

/**
 * Advance the simulation by one timestep.
 * actions should be a list of Action objects, one per agent.
 */
export function simulateStep(actions = [], strategy = 'full') {
    return apiFetch('/api/simulate/step', {
        method: 'POST',
        body: JSON.stringify({ actions, strategy }),
    });
}

/**
 * Run the simulation until the step limit is reached.
 */
export function simulateRun(maxSteps = 100, strategy = 'full') {
    return apiFetch('/api/simulate/run', {
        method: 'POST',
        body: JSON.stringify({ max_steps: maxSteps, strategy }),
    });
}

/**
 * Reset the simulation to its initial state.
 */
export function simulateReset() {
    return apiFetch('/api/simulate/reset', { method: 'POST' });
}

export function simulatePause() {
    return apiFetch('/api/simulate/pause', { method: 'POST' });
}

export function simulateResume() {
    return apiFetch('/api/simulate/resume', { method: 'POST' });
}

/** --- Experiment Endpoints --- */

/** Run all four coordination strategies against one scenario. */
export function runExperimentComparison(scenarioName, maxSteps = 100) {
    return apiFetch('/api/experiment/compare', {
        method: 'POST',
        body: JSON.stringify({ scenario_name: scenarioName, max_steps: maxSteps }),
    });
}

/** Load session-level experiment history. */
export function listExperimentResults() {
    return apiFetch('/api/experiment/results');
}

/** --- Metrics Endpoint --- */

/**
 * Get current simulation metrics.
 */
export function getMetrics() {
    return apiFetch('/api/metrics');
}

/** --- Utility --- */

/**
 * Format a number with commas if needed.
 */
export function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Format a timestamp or step count.
 */
export function formatStep(step) {
    return `${formatNumber(step)} step${step !== 1 ? 's' : ''}`;
}

/**
 * Debounce a function - wait for it to be called n milliseconds 
 * without it being called again, then execute it.
 */
export function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

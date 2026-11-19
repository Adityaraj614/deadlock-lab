/**
 * Deadlock Lab Warehouse JavaScript
 * Handles grid visualization, simulation controls, and metrics.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize modules
    initNavigation();
    initAPI();
    initEventListeners();
    
    // Check backend connection
    checkBackendStatus();
    
    // Initialize with no scenario loaded
    clearWorkspace();
});

/**
 * Initialize API service and connection checking.
 */
function initAPI() {
    // Check connection status interval
    setInterval(() => {
        checkBackendStatus();
    }, 3000);
}

/**
 * Initialize event listeners for the warehouse lab.
 */
function initEventListeners() {
    // Scenario select change
    const scenarioSelect = document.getElementById('scenario-select');
    if (scenarioSelect) {
        scenarioSelect.addEventListener('change', handleScenarioChange);
    }
    
    // Control buttons
    const loadBtn = document.getElementById('load-scenario');
    if (loadBtn) {
        loadBtn.addEventListener('click', handleLoadScenario);
    }
    
    const runBtn = document.getElementById('run-simulation');
    if (runBtn) {
        runBtn.addEventListener('click', handleRunSimulation);
    }
    
    const stepBtn = document.getElementById('step-simulation');
    if (stepBtn) {
        stepBtn.addEventListener('click', handleStepSimulation);
    }
    
    const resetBtn = document.getElementById('reset-simulation');
    if (resetBtn) {
        resetBtn.addEventListener('click', handleResetSimulation);
    }
}

/**
 * Initialize navigation highlighting.
 */
function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        });
    });
}

/**
 * Check backend connection status.
 */
function checkBackendStatus() {
    fetch('http://127.0.0.1:8000/health')
        .then(response => {
            if (response.ok) {
                document.getElementById('api-status').textContent = 'Connected';
                document.getElementById('api-status').className = 'api-status connected';
            }
        })
        .catch(() => {
            document.getElementById('api-status').textContent = 'Disconnected';
            document.getElementById('api-status').className = 'api-status disconnected';
        });
}

/**
 * Handle scenario selection change.
 */
async function handleScenarioChange() {
    const select = this;
    const name = select.value;
    const statusDiv = document.getElementById('scenario-status');
    
    if (!name) {
        clearWorkspace();
        return;
    }
    
    showLoading();
    disableControls(false);
    
    try {
        // Load the scenario state
        const state = await fetch(`http://127.0.0.1:8000/api/scenario/load/${name}`)
            .then(res => res.json());
        
        displayScenarioState(state);
        
        // Update metrics
        updateMetrics(state);
        
    } catch (error) {
        console.error('Error loading scenario:', error);
        showError('Failed to load scenario. The backend may not have the scenario configured.');
    } finally {
        hideLoading();
        disableControls(true);
    }
}

/**
 * Display the scenario state in the grid and UI.
 */
function displayScenarioState(state) {
    const gridDiv = document.getElementById('warehouse-grid');
    const detailDiv = document.getElementById('scenario-details');
    
    if (!gridDiv || !detailDiv) return;
    
    // Clear previous grid
    gridDiv.innerHTML = '';
    
    const gridWidth = state.grid_width || 10;
    const gridHeight = state.grid_height || 10;
    const agents = state.agents || [];
    const obstacles = state.obstacles || [];
    const goals = state.goals || [];
    
    // Update details
    detailDiv.innerHTML = `
        <div class="metric-card">
            <strong>Grid:</strong> ${gridWidth}x${gridHeight}
        </div>
        <div class="metric-card">
            <strong>Agents:</strong> ${agents.length}
        </div>
        <div class="metric-card">
            <strong>Obstacles:</strong> ${obstacles.length}
        </div>
        <div class="metric-card">
            <strong>Goals:</strong> ${goals.length}
        </div>
    `;
    
    // Draw grid on canvas
    const canvas = document.getElementById('warehouseCanvas');
    if (!canvas) return;
    
    const canvasCtx = canvas.getContext('2d');
    if (!canvasCtx) return;
    
    // Set canvas size
    const cellSize = 40;
    canvas.width = gridWidth * cellSize;
    canvas.height = gridHeight * cellSize;
    
    // Clear canvas
    canvasCtx.fillStyle = '#0d1117';
    canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw obstacles
    canvasCtx.fillStyle = '#f472b6'; // purple for obstacles
    obstacles.forEach(obs => {
        const x = obs.position.x * cellSize + cellSize * 0.1;
        const y = obs.position.y * cellSize + cellSize * 0.1;
        const size = cellSize * 0.8;
        canvasCtx.fillRect(x, y, size, size);
    });
    
    // Draw goals
    canvasCtx.fillStyle = '#22c55e'; // green for goals
    goals.forEach(goal => {
        const x = goal.position.x * cellSize + cellSize * 0.1;
        const y = goal.position.y * cellSize + cellSize * 0.1;
        const size = cellSize * 0.8;
        canvasCtx.fillRect(x, y, size, size);
        // Add "G" text
        canvasCtx.fillStyle = '#ffffff';
        canvasCtx.font = 'bold 16px sans-serif';
        canvasCtx.textAlign = 'center';
        canvasCtx.textBaseline = 'middle';
        canvasCtx.fillText('G', x + cellSize * 0.4, y + cellSize * 0.4);
    });
    
    // Draw agents
    canvasCtx.fillStyle = '#3b82f6'; // blue for agents
    agents.forEach(agent => {
        const x = agent.position.x * cellSize + cellSize * 0.1;
        const y = agent.position.y * cellSize + cellSize * 0.1;
        const size = cellSize * 0.8;
        
        // Draw circle for agent
        canvasCtx.beginPath();
        canvasCtx.arc(x + cellSize * 0.4, y + cellSize * 0.4, cellSize * 0.35, 0, Math.PI * 2);
        canvasCtx.fill();
        
        // Add "R" text
        canvasCtx.fillStyle = '#ffffff';
        canvasCtx.font = 'bold 16px sans-serif';
        canvasCtx.textAlign = 'center';
        canvasCtx.textBaseline = 'middle';
        canvasCtx.fillText('R', x + cellSize * 0.4, y + cellSize * 0.4);
        
        // Draw path (if moving)
        if (agent.status === 'moving' || agent.status === 'MOVING') {
            canvasCtx.strokeStyle = '#fbbf24';
            canvasCtx.lineWidth = 2;
            canvasCtx.beginPath();
            canvasCtx.moveTo(x + cellSize * 0.4, y + cellSize * 0.4);
            // Simple: draw toward goal
            const gx = agent.goal.position.x * cellSize + cellSize * 0.4;
            const gy = agent.goal.position.y * cellSize + cellSize * 0.4;
            canvasCtx.lineTo(gx, gy);
            canvasCtx.stroke();
        }
    });
    
    // Draw grid lines
    canvasCtx.strokeStyle = var(--border-color);
    canvasCtx.lineWidth = 1;
    for (let i = 0; i <= gridWidth; i++) {
        canvasCtx.beginPath();
        canvasCtx.moveTo(i * cellSize, 0);
        canvasCtx.lineTo(i * cellSize, canvas.height);
        canvasCtx.stroke();
    }
    for (let i = 0; i <= gridHeight; i++) {
        canvasCtx.beginPath();
        canvasCtx.moveTo(0, i * cellSize);
        canvasCtx.lineTo(canvas.width, i * cellSize);
        canvasCtx.stroke();
    }
}

/**
 * Update metrics display.
 */
function updateMetrics(state) {
    const metricsDiv = document.getElementById('metrics-panel');
    if (!metricsDiv) return;
    
    const agents = state.agents || [];
    const totalSteps = state.current_step || 0;
    
    let html = `
        <div class="metric-value" id="total-steps">${formatStep(totalSteps)}</div>
        <div class="metric-label">Steps</div>
    `;
    
    if (agents.length > 0) {
        const completed = agents.filter(a => a.status === 'completed' || a.status === 'COMPLETED').length;
        const waiting = agents.filter(a => a.status === 'waiting' || a.status === 'WAITING').length;
        const blocked = agents.filter(a => a.status === 'blocked' || a.status === 'BLOCKED').length;
        
        html += `
            <div class="metric-item">
                <div class="metric-value" id="completed-agents">${completed}</div>
                <div class="metric-label">Completed</div>
            </div>
            <div class="metric-item">
                <div class="metric-value" id="waiting-agents">${waiting}</div>
                <div class="metric-label">Waiting</div>
            </div>
            <div class="metric-item">
                <div class="metric-value" id="blocked-agents">${blocked}</div>
                <div class="metric-label">Blocked</div>
            </div>
        `;
    }
    
    metricsDiv.innerHTML = html;
}

/** --- Simulation Controls --- */

async function handleLoadScenario() {
    const select = document.getElementById('scenario-select');
    const name = select.value;
    
    if (!name) return;
    
    showLoading();
    disableControls(false);
    
    try {
        const state = await fetch(`http://127.0.0.1:8000/api/scenario/load/${name}`)
            .then(res => res.json());
        
        displayScenarioState(state);
        updateMetrics(state);
    } catch (error) {
        showError('Failed to load scenario');
    } finally {
        hideLoading();
        disableControls(true);
    }
}

async function handleRunSimulation() {
    const maxSteps = 100; // default
    
    showLoading();
    disableControls(false);
    
    try {
        const result = await fetch(`http://127.0.0.1:8000/api/simulate/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_steps: maxSteps })
        }).then(res => res.json());
        
        updateMetricsFromRun(result);
    } catch (error) {
        showError('Failed to run simulation');
    } finally {
        hideLoading();
        disableControls(true);
    }
}

async function handleStepSimulation() {
    // Get actions - for step, we'll use wait actions (no movement)
    const actions = []; // Empty actions = all agents wait
    
    showLoading();
    disableControls(false);
    
    try {
        const state = await fetch(`http://127.0.0.1:8000/api/simulate/step`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ actions })
        }).then(res => res.json());
        
        displayScenarioState(state);
        updateMetrics(state);
    } catch (error) {
        showError('Failed to step simulation');
    } finally {
        hideLoading();
        disableControls(true);
    }
}

function handleResetSimulation() {
    showLoading();
    disableControls(false);
    
    try {
        const state = fetch(`http://127.0.0.1:8000/api/simulate/reset`)
            .then(res => res.json());
        
        // Reset the canvas and UI
        const canvas = document.getElementById('warehouseCanvas');
        if (canvas) {
            canvas.width = canvas.width; // reset
        }
        
        const detailDiv = document.getElementById('scenario-details');
        if (detailDiv) {
            detailDiv.innerHTML = '';
        }
        
        const metricsDiv = document.getElementById('metrics-panel');
        if (metricsDiv) {
            metricsDiv.innerHTML = '<div class="metric-value">0</div><div class="metric-label">Steps</div>';
        }
    } catch (error) {
        showError('Failed to reset simulation');
    } finally {
        hideLoading();
        disableControls(true);
    }
}

/** --- UI Helper Functions --- */

function showLoading() {
    const loadDiv = document.getElementById('loading-state');
    if (loadDiv) loadDiv.style.display = 'block';
}

function hideLoading() {
    const loadDiv = document.getElementById('loading-state');
    if (loadDiv) loadDiv.style.display = 'none';
}

function disableControls(disabled) {
    const buttons = document.querySelectorAll('.btn-action:not(:disabled)');
    buttons.forEach(btn => {
        if (disabled) {
            btn.disabled = true;
        } else {
            btn.disabled = false;
        }
    });
}

function showError(message) {
    const statusDiv = document.getElementById('scenario-status');
    if (statusDiv) {
        statusDiv.textContent = `Error: ${message}`;
        statusDiv.className = 'status-error';
    }
}

function showLoading() {
    const loadDiv = document.getElementById('loading-state');
    if (loadDiv) loadDiv.style.display = 'block';
}

/** --- Initialization --- */

function clearWorkspace() {
    // Clear the canvas
    const canvas = document.getElementById('warehouseCanvas');
    if (canvas) {
        canvas.width = canvas.width;
    }
    
    // Clear details
    const detailDiv = document.getElementById('scenario-details');
    if (detailDiv) detailDiv.innerHTML = '';
    
    // Clear metrics
    const metricsDiv = document.getElementById('metrics-panel');
    if (metricsDiv) {
        metricsDiv.innerHTML = '<div class="metric-value">0</div><div class="metric-label">Steps</div>';
    }
}
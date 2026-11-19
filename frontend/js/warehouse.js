import {
    checkConnection,
    loadScenario,
    simulateStep,
    simulateRun,
    simulateReset,
    simulatePause,
    simulateResume,
    formatStep,
} from './api.js?v=3';
import { navigateBackHome } from './navigation.js';

let currentState = null;

document.addEventListener('DOMContentLoaded', () => {
    window.navigateBackHome = navigateBackHome;
    document.getElementById('scenario-select')?.addEventListener('change', handleLoadScenario);
    document.getElementById('load-scenario')?.addEventListener('click', handleLoadScenario);
    document.getElementById('run-simulation')?.addEventListener('click', handleRunSimulation);
    document.getElementById('step-simulation')?.addEventListener('click', handleStepSimulation);
    document.getElementById('pause-simulation')?.addEventListener('click', handlePauseSimulation);
    document.getElementById('resume-simulation')?.addEventListener('click', handleResumeSimulation);
    document.getElementById('reset-simulation')?.addEventListener('click', handleResetSimulation);
    checkBackendStatus();
    window.setInterval(checkBackendStatus, 5000);
});

function selectedStrategy() {
    return document.getElementById('strategy-select')?.value || 'full';
}

function selectedScenario() {
    return document.getElementById('scenario-select')?.value || '';
}

async function checkBackendStatus() {
    const connected = await checkConnection();
    const dot = document.getElementById('api-status');
    const text = document.querySelector('.status-text');
    if (dot) dot.className = `status-dot ${connected ? 'connected' : 'disconnected'}`;
    if (text) text.textContent = connected ? 'Connected' : 'Disconnected';
}

async function handleLoadScenario() {
    const name = selectedScenario();
    if (!name) return;
    await request(async () => loadScenario(name, selectedStrategy()), 'Scenario loaded');
}

async function handleRunSimulation() {
    await request(async () => simulateRun(100, selectedStrategy()), 'Simulation run completed');
}

async function handleStepSimulation() {
    await request(async () => simulateStep([], selectedStrategy()), 'Simulation stepped');
}

async function handlePauseSimulation() {
    await request(simulatePause, 'Simulation paused');
}

async function handleResumeSimulation() {
    await request(simulateResume, 'Simulation resumed');
}

async function handleResetSimulation() {
    await request(simulateReset, 'Simulation reset');
}

async function request(operation, message) {
    setBusy(true);
    try {
        const state = await operation();
        currentState = state;
        renderState(state);
        addEvent(`${message} at step ${state.current_step}`);
    } catch (error) {
        addEvent(`Error: ${error.message}`);
    } finally {
        setBusy(false);
    }
}

function setBusy(busy) {
    document.querySelectorAll('.btn-action').forEach(button => {
        button.disabled = busy || (!currentState && button.id !== 'reset-simulation');
    });
}

function renderState(state) {
    const width = state.grid_width || 10;
    const height = state.grid_height || 10;
    const canvas = document.getElementById('warehouseCanvas');
    const context = canvas?.getContext('2d');
    if (!canvas || !context) return;

    const cell = Math.max(28, Math.min(48, Math.floor(640 / Math.max(width, height))));
    canvas.width = width * cell;
    canvas.height = height * cell;
    context.fillStyle = '#090909';
    context.fillRect(0, 0, canvas.width, canvas.height);

    drawCells(context, state.obstacles || [], cell, '#6b5260', '');
    drawCells(context, state.goals || [], cell, '#2f7d5a', 'G');
    (state.agents || []).forEach(agent => {
        const centerX = agent.position.x * cell + cell / 2;
        const centerY = agent.position.y * cell + cell / 2;
        context.beginPath();
        context.fillStyle = agent.status === 'completed' ? '#10b981' : '#c6a15b';
        context.arc(centerX, centerY, cell * 0.3, 0, Math.PI * 2);
        context.fill();
        context.fillStyle = '#090909';
        context.font = `bold ${Math.max(11, cell * 0.28)}px sans-serif`;
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(agent.id.slice(-1), centerX, centerY);
    });

    context.strokeStyle = '#303030';
    context.lineWidth = 1;
    for (let x = 0; x <= width; x += 1) {
        context.beginPath(); context.moveTo(x * cell, 0); context.lineTo(x * cell, canvas.height); context.stroke();
    }
    for (let y = 0; y <= height; y += 1) {
        context.beginPath(); context.moveTo(0, y * cell); context.lineTo(canvas.width, y * cell); context.stroke();
    }

    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('scenario-name').textContent = state.scenario || 'Warehouse';
    document.getElementById('grid-dimensions').textContent = `${width}x${height} Grid`;
    document.getElementById('simulation-state').textContent = state.status || 'ready';
    document.getElementById('info-scenario-details').innerHTML = `<p>${width}x${height} grid<br>${state.agents.length} robots<br>${state.obstacles.length} obstacles<br>${state.goals.length} goals</p>`;
    document.getElementById('info-agents-content').innerHTML = state.agents.map(agent => `<p>${agent.id}: (${agent.position.x}, ${agent.position.y}) → (${agent.goal.x}, ${agent.goal.y})<br><small>${agent.status}</small></p>`).join('');
    updateMetrics(state.metrics || {});
}

function drawCells(context, items, cell, color, label) {
    items.forEach(item => {
        const x = item.position.x * cell + cell * 0.12;
        const y = item.position.y * cell + cell * 0.12;
        context.fillStyle = color;
        context.fillRect(x, y, cell * 0.76, cell * 0.76);
        if (label) {
            context.fillStyle = '#ffffff';
            context.font = `bold ${Math.max(11, cell * 0.3)}px sans-serif`;
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.fillText(label, x + cell * 0.38, y + cell * 0.38);
        }
    });
}

function updateMetrics(metrics) {
    const values = {
        'total-steps': formatStep(metrics.total_steps || 0),
        'completed-agents': metrics.completed_agents || 0,
        'waiting-agents': metrics.waiting_agents || 0,
        'blocked-agents': metrics.blocked_agents || 0,
        deadlocks: metrics.deadlock_incidents ?? metrics.deadlocks_detected ?? 0,
        collisions: metrics.collisions_prevented || 0,
        'path-length': metrics.total_path_length || 0,
        recoveries: `${metrics.successful_recoveries || 0}/${metrics.deadlock_recovery_attempts || 0}`,
    };
    Object.entries(values).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    });
}

function addEvent(message) {
    const log = document.getElementById('event-log-body');
    if (!log) return;
    const entry = document.createElement('div');
    entry.textContent = message;
    log.prepend(entry);
}

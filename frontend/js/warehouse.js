import {
    checkConnection,
    loadScenario,
    simulateStep,
    simulateRun,
    simulateReset,
    simulatePause,
    simulateResume,
    runExperimentComparison,
    listExperimentResults,
    formatStep,
} from './api.js?v=3';
import { navigateBackHome } from './navigation.js';

let currentState = null;
let experimentRunning = false;
const experimentStrategies = ['full', 'priority', 'reservation', 'deadlock'];
const experimentMetricDefinitions = [
    { key: 'completed_agents', label: 'Robots completed', direction: 'max', format: value => value },
    { key: 'current_step', label: 'Simulation steps', direction: 'min', format: value => value },
    { key: 'total_path_length', label: 'Path length', direction: 'min', format: value => value },
    { key: 'waiting_steps', label: 'Waiting time', direction: 'min', format: value => value },
    { key: 'blocked_steps', label: 'Blocked movements', direction: 'min', format: value => value },
    { key: 'deadlocks_detected', label: 'Deadlocks detected', direction: 'min', format: value => value },
    { key: 'successful_recoveries', label: 'Successful recoveries', direction: null, format: value => value },
    { key: 'collisions_prevented', label: 'Collisions prevented', direction: null, format: value => value },
];

document.addEventListener('DOMContentLoaded', () => {
    window.navigateBackHome = navigateBackHome;
    document.getElementById('scenario-select')?.addEventListener('change', handleLoadScenario);
    document.getElementById('load-scenario')?.addEventListener('click', handleLoadScenario);
    document.getElementById('run-simulation')?.addEventListener('click', handleRunSimulation);
    document.getElementById('step-simulation')?.addEventListener('click', handleStepSimulation);
    document.getElementById('pause-simulation')?.addEventListener('click', handlePauseSimulation);
    document.getElementById('resume-simulation')?.addEventListener('click', handleResumeSimulation);
    document.getElementById('reset-simulation')?.addEventListener('click', handleResetSimulation);
    document.querySelectorAll('.nav-item[data-view]').forEach(item => {
        item.addEventListener('click', () => showView(item.dataset.view));
    });
    document.getElementById('run-comparison')?.addEventListener('click', handleRunComparison);
    loadExperimentHistory();
    checkBackendStatus();
    window.setInterval(checkBackendStatus, 5000);
});

function showView(view) {
    const experiments = view === 'experiments';
    document.getElementById('simulation-view')?.classList.toggle('hidden', experiments);
    document.getElementById('experiments-view')?.classList.toggle('hidden', !experiments);
    document.querySelector('.side-panel')?.classList.toggle('hidden', experiments);
    document.querySelectorAll('.nav-item[data-view]').forEach(item => {
        item.classList.toggle('active', item.dataset.view === view);
    });
    const status = document.getElementById('info-status-text');
    if (!experiments && status) status.innerHTML = '<p>Simulation stopped</p>';
}

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

async function handleRunComparison() {
    if (experimentRunning) return;
    const scenario = document.getElementById('experiment-scenario')?.value;
    if (!scenario) return;

    experimentRunning = true;
    setExperimentBusy(true);
    setExperimentProgress('Running FULL, PRIORITY, RESERVATION and DEADLOCK independently…', true);
    try {
        const results = await runExperimentComparison(scenario, 100);
        renderExperimentResults(results, scenario);
        setExperimentProgress('Comparison complete. Results loaded from the backend.', false);
        await loadExperimentHistory();
    } catch (error) {
        setExperimentProgress(`Comparison failed: ${error.message}`, false, true);
    } finally {
        experimentRunning = false;
        setExperimentBusy(false);
    }
}

function setExperimentBusy(busy) {
    const button = document.getElementById('run-comparison');
    if (button) {
        button.disabled = busy;
        button.textContent = busy ? 'Running…' : 'Run Comparison';
    }
    const selector = document.getElementById('experiment-scenario');
    if (selector) selector.disabled = busy;
}

function setExperimentProgress(message, running, error = false) {
    const copy = document.getElementById('experiment-progress-copy');
    const bar = document.getElementById('experiment-progress-bar');
    if (copy) copy.textContent = message;
    if (copy) copy.classList.toggle('progress-error', error);
    if (bar) bar.classList.toggle('is-running', running);
}

function orderedExperimentResults(results) {
    return experimentStrategies
        .filter(strategy => results?.[strategy])
        .map(strategy => ({ strategy, ...results[strategy] }));
}

function bestValue(results, definition) {
    if (!definition.direction || !results.length) return null;
    const values = results.map(result => Number(result[definition.key] ?? 0));
    return definition.direction === 'min' ? Math.min(...values) : Math.max(...values);
}

function comparisonDefinition(definition, results) {
    if (definition.key === 'successful_recoveries' && !results.some(result => Number(result.deadlocks_detected ?? 0) > 0)) {
        return { ...definition, direction: null };
    }
    return definition;
}

function comparisonStatus(results, definition) {
    const comparable = comparisonDefinition(definition, results);
    if (!comparable.direction || !results.length) return 'N/A';
    const values = results.map(result => Number(result[definition.key] ?? 0));
    const best = bestValue(results, comparable);
    if (values.every(value => value === values[0])) return 'SAME';
    return values.filter(value => value === best).length > 1 ? 'JOINT BEST' : 'BEST';
}

function formatMetricValue(result, definition) {
    const value = Number(result[definition.key] ?? 0);
    if (definition.key === 'completed_agents') {
        return `${value}/${result.total_agents ?? 0}`;
    }
    return definition.format(value);
}

function renderExperimentResults(results, scenario) {
    const ordered = orderedExperimentResults(results);
    const summary = document.getElementById('experiment-summary');
    if (summary) {
        summary.innerHTML = experimentMetricDefinitions.map(definition => {
            const comparable = comparisonDefinition(definition, ordered);
            const status = comparisonStatus(ordered, definition);
            const best = bestValue(ordered, comparable);
            const values = ordered.map(result => Number(result[definition.key] ?? 0));
            const representative = comparable.direction === 'max' ? Math.max(...values) : Math.min(...values);
            const winner = ordered.find(result => Number(result[definition.key] ?? 0) === representative);
            return `<div class="metric-card experiment-metric-card">
                <div class="metric-value">${definition.format(representative)}</div>
                <div class="metric-label">${definition.label}</div>
                <div class="metric-caption">${status}${best === null || status === 'SAME' || status === 'N/A' ? '' : ` · ${winner ? winner.strategy.toUpperCase() : '—'}`}</div>
            </div>`;
        }).join('');
    }

    const table = document.querySelector('#experiment-table tbody');
    if (table) {
        table.innerHTML = experimentMetricDefinitions.map(definition => {
            const comparable = comparisonDefinition(definition, ordered);
            const status = comparisonStatus(ordered, definition);
            const best = bestValue(ordered, comparable);
            const cells = experimentStrategies.map(strategy => {
                const result = results?.[strategy];
                if (!result) return '<td>—</td>';
                const value = Number(result[definition.key] ?? 0);
                const isBest = (status === 'BEST' || status === 'JOINT BEST') && best !== null && value === best;
                return `<td class="${isBest ? 'best-value' : ''}">${formatMetricValue(result, definition)}</td>`;
            }).join('');
            return `<tr><th scope="row"><span>${definition.label}</span><small class="metric-status">${status}</small></th>${cells}</tr>`;
        }).join('');
    }

    const charts = document.getElementById('experiment-charts');
    if (charts) {
        const chartDefinitions = [
            { key: 'current_step', label: 'Simulation steps', direction: 'min' },
            { key: 'total_path_length', label: 'Total path length', direction: 'min' },
            { key: 'deadlocks_detected', label: 'Deadlocks detected', direction: 'min' },
            { key: 'successful_recoveries', label: 'Successful recoveries', direction: null },
        ];
        charts.innerHTML = chartDefinitions.map(definition => {
            const max = Math.max(...ordered.map(result => Number(result[definition.key] ?? 0)), 1);
            const comparable = comparisonDefinition(definition, ordered);
            const status = comparisonStatus(ordered, definition);
            const best = bestValue(ordered, comparable);
            const bars = ordered.map(result => {
                const value = Number(result[definition.key] ?? 0);
                const width = Math.max(2, (value / max) * 100);
                const isBest = (status === 'BEST' || status === 'JOINT BEST') && best !== null && value === best;
                return `<div class="chart-row"><span class="strategy-label">${result.strategy.toUpperCase()}</span><div class="chart-track"><div class="chart-bar strategy-${result.strategy} ${isBest ? 'best-bar' : ''}" style="width:${width}%"></div></div><strong>${value}</strong></div>`;
            }).join('');
            return `<div class="mini-chart"><div class="mini-chart-title"><span>${definition.label}</span><small>${status}</small></div>${bars}</div>`;
        }).join('');
    }
}

async function loadExperimentHistory() {
    try {
        const data = await listExperimentResults();
        const history = document.getElementById('experiment-history-list');
        if (!history) return;
        const results = (data.results || []).slice(-8).reverse();
        history.innerHTML = results.length ? results.map(result => `<div class="history-row"><span>${result.scenario.replaceAll('_', ' ')}</span><span>${result.strategy.toUpperCase()}</span><span>${result.completed_agents}/${result.total_agents} complete</span><span>${result.current_step} steps</span></div>`).join('') : '<span class="table-empty">No experiment runs yet.</span>';
    } catch (error) {
        const history = document.getElementById('experiment-history-list');
        if (history) history.innerHTML = `<span class="table-empty">History unavailable: ${error.message}</span>`;
    }
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

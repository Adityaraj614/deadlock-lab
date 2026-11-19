/**
 * Deadlock Lab Frontend - Navigation & Global State
 * Manages homepage module cards, Warehouse Lab page display,
 * and API connection status across both pages.
 * Note: Connection status is shown only in homepage header;
 * warehouse page manages its own status display.
 */

import { checkConnection, getConnectionStatus, getLastError } from './api.js';

// Module definitions
const MODULES = {
    WAREHOUSE: 'warehouse',
    DRONE: 'drone',
    HOSPITALITY: 'hospitality',
    DEPLOYMENT: 'deployment',
};

/**
 * Current active module.
 */
let activeModule = MODULES.WAREHOUSE;

/**
 * Initialize the navigation system.
 * Sets up event listeners and sets the initial active module.
 */
export function init() {
    // Set up homepage card click handlers
    setupCardHandlers();

    // Check backend connection
    checkConnection();

    // Update UI based on connection status
    updateConnectionStatus();

    // Set up online/offline event listeners
    window.addEventListener('online', updateConnectionStatus);
    window.addEventListener('offline', updateConnectionStatus);

    // Initialize the current page based on pathname
    const path = window.location.pathname;
    if (path.includes('warehouse')) {
        activeModule = MODULES.WAREHOUSE;
        showWarehouseLab();
    } else {
        activeModule = MODULES.WAREHOUSE; // Default for demo
        showPage('home');
    }

    // Update active state
    updateActiveModule();
}

/**
 * Set up event handlers for homepage module cards.
 */
function setupCardHandlers() {
    // Warehouse Lab card - always active/functional
    const warehouseCard = document.getElementById('warehouse-card');
    if (warehouseCard) {
        warehouseCard.addEventListener('click', (e) => {
            e.preventDefault();
            navigateToWarehouse();
        });
    }

    // Other cards - show coming soon modal
    ['drone', 'hospitality', 'deployment'].forEach(moduleId => {
        const card = document.getElementById(`${moduleId}-card`);
        if (card) {
            card.addEventListener('click', (e) => {
                e.preventDefault();
                showComingSoon(moduleId);
            });
        }
    });
}

/**
 * Navigate to the Warehouse Lab workspace.
 * Shows the warehouse page (navigates to pages/warehouse.html).
 */
export function navigateToWarehouse() {
    activeModule = MODULES.WAREHOUSE;
    updateActiveModule();
    window.location.href = 'pages/warehouse.html';
}

/**
 * Show the Coming Soon modal for a module.
 */
function showComingSoon(moduleId) {
    const moduleNames = {
        drone: 'Drone Studio',
        hospitality: 'Hospitality Lab',
        deployment: 'Deployment Lab',
    };

    const moduleName = moduleNames[moduleId] || moduleId;
    const modal = `
        <div class="coming-soon-modal">
            <div class="modal-content">
                <h3>Coming Soon</h3>
                <p>${moduleName} is under development.</p>
                <p>This module will be available in a future update.</p>
                <button class="modal-close">OK</button>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existing = document.querySelector('.coming-soon-modal');
    if (existing) existing.remove();

    const modalEl = document.createElement('div');
    modalEl.className = 'coming-soon-modal';
    modalEl.innerHTML = modal;
    document.body.appendChild(modalEl);

    // Add close button handler
    modalEl.querySelector('.modal-close').addEventListener('click', () => {
        modalEl.remove();
    });

    // Close on outside click
    modalEl.addEventListener('click', (e) => {
        if (e.target === modalEl) {
            modalEl.remove();
        }
    });
}

/**
 * Update the active module UI state on the homepage.
 */
function updateActiveModule() {
    const cards = document.querySelectorAll('.module-card');
    cards.forEach(card => {
        const moduleId = card.getAttribute('data-module');
        if (moduleId === activeModule) {
            card.classList.add('active');
            card.setAttribute('aria-pressed', 'true');
        } else {
            card.classList.remove('active');
            card.setAttribute('aria-pressed', 'false');
        }
    });
}

/**
 * Update the connection status indicator in the UI.
 * Updates the single status indicator on the homepage.
 * Warehouse page manages its own status display.
 */
function updateConnectionStatus() {
    const statusIndicator = document.querySelector('.api-status');
    if (!statusIndicator) return;

    if (getConnectionStatus() === 'connected') {
        statusIndicator.classList.remove('disconnected');
        statusIndicator.classList.add('connected');
        statusIndicator.textContent = 'Connected';
    } else {
        statusIndicator.classList.remove('connected');
        statusIndicator.classList.add('disconnected');
        statusIndicator.textContent = 'Disconnected';
    }
}

/**
 * Navigate to a specific page.
 * In a single-page application, this would use history.pushState.
 * For this demo, we show/hide page sections.
 */
export function showPage(pageId) {
    // Hide all pages
    const pages = document.querySelectorAll('.page-content');
    pages.forEach(page => {
        page.style.display = 'none';
    });

    // Show the requested page
    const page = document.getElementById(pageId);
    if (page) {
        page.style.display = 'block';
    }
}

/**
 * Get the current active module.
 */
export function getActiveModule() {
    return activeModule;
}

/**
 * Navigate back to home from any page.
 */
export function navigateBackHome() {
    activeModule = MODULES.WAREHOUSE;
    updateActiveModule();
    showPage('home');
    showWarehouseLabOverlay(false);
}

/**
 * Show the Warehouse Lab page.
 * Hides the homepage and shows the warehouse workspace.
 */
export function showWarehouseLab() {
    // Hide home page
    const homePage = document.getElementById('home-page');
    if (homePage) {
        homePage.style.display = 'none';
    }

    // Show warehouse page
    const warehousePage = document.getElementById('warehouse-page');
    if (warehousePage) {
        warehousePage.style.display = 'block';
    }

    // Initialize warehouse lab
    initWarehouseLab();
}

/**
 * Show/hide the warehouse lab overlay (for homepage interaction).
 */
function showWarehouseLabOverlay(show) {
    const overlay = document.getElementById('warehouse-overlay');
    if (overlay) {
        if (show) {
            overlay.style.display = 'block';
        } else {
            overlay.style.display = 'none';
        }
    }
}
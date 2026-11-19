/**
 * Deadlock Lab Homepage JavaScript
 * Handles module card interactions and backend connection.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize navigation (module cards, connection status, page display)
    import('./navigation.js').then(navModule => {
        navModule.init();
    }).catch(err => {
        console.error('Failed to initialize navigation:', err);
    });
});
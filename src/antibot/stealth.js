// Anti-detection JavaScript for Playwright stealth mode
// Override navigator.webdriver property
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

// Override the plugins property to use a fake value
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Override the languages property to use a fake value
Object.defineProperty(navigator, 'languages', {
    get: () => ['fr-FR', 'fr', 'en-US', 'en'],
});

// Override chrome runtime
Object.defineProperty(window, 'chrome', {
    value: { runtime: {} },
});

// Mock permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// Add additional stealth measures
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 4,
});

Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8,
});

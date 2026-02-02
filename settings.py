"""Playwright browser settings to avoid automation detection."""

from fake_useragent import UserAgent


BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
    "--disable-extensions",
    "--incognito",
    "--disable-setuid-sandbox",
    "--disable-accelerated-2d-canvas",
    "--no-first-run",
    "--no-zygote",
    "--disable-gpu",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-features=TranslateUI,VizDisplayCompositor",
    "--disable-ipc-flooding-protection",
    "--disable-web-security",
    "--disable-features=VizDisplayCompositor",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-translate",
    "--hide-scrollbars",
    "--mute-audio",
    "--no-default-browser-check",
    "--no-pings",
    "--single-process",
    "--disable-logging",
    "--disable-gpu-logging",
    "--silent",
    "--log-level=3",
]

CONTEXT_KWARGS = {
    "viewport": {"width": 1366, "height": 768},
    "user_agent": UserAgent(
        browsers=["Chrome"], os=["Windows", "Linux"]
    ).random,
    "locale": "ru-RU",
    "timezone_id": "Europe/Moscow",
    "permissions": ["geolocation"],
    "geolocation": {"longitude": 37.6173, "latitude": 55.7558},
    "color_scheme": "light",
    "reduced_motion": "no-preference",
    "forced_colors": "none",
    "extra_http_headers": {
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa: E501
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "max-age=0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    },
}


INIT_SCRIPT = """
// Remove webdriver property
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

// Mock chrome runtime
window.chrome = {
    runtime: {},
};

// Mock plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Set languages
Object.defineProperty(navigator, "languages", {
    get: () => ["ru-RU", "ru", "en-US", "en"],
});

// Override the `plugins` property to use a custom getter.
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Overwrite the `permissions` property to use a custom getter.
Object.defineProperty(navigator, 'permissions', {
    get: () => ({
        query: () => Promise.resolve({state: 'granted'}),
    }),
});

// Mock hardware concurrency
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 4,
});

// Mock device memory
Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8,
});

// Mock platform
Object.defineProperty(navigator, 'platform', {
    get: () => 'Win32',
});

// Add some realistic screen properties
Object.defineProperty(screen, 'colorDepth', {
    get: () => 24,
});

Object.defineProperty(screen, 'pixelDepth', {
    get: () => 24,
});

// Mock WebGL vendor and renderer
const getParameter = WebGLRenderingContext.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
        return 'Intel Inc.';
    }
    if (parameter === 37446) {
        return 'Intel(R) Iris(TM) Graphics 6100';
    }
    return getParameter(parameter);
};

// Remove automation-related window properties
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

// Add mouse and keyboard event listeners to simulate user activity
document.addEventListener('DOMContentLoaded', () => {
    // Simulate random mouse movements
    setTimeout(() => {
        const event = new MouseEvent('mousemove', {
            clientX: Math.random() * window.innerWidth,
            clientY: Math.random() * window.innerHeight
        });
        document.dispatchEvent(event);
    }, Math.random() * 1000);
});
"""

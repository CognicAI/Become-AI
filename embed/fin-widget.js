(function() {
    // --- Configuration ---
    // In production, this should be your CDN or hosted URL
    const DEFAULT_WIDGET_URL = 'http://localhost:3000/widget.html';
    
    // Get script element to read configuration
    const scriptTag = document.currentScript || document.querySelector('script[src*="fin-widget.js"]');
    const WIDGET_URL = scriptTag ? (scriptTag.getAttribute('data-widget-url') || DEFAULT_WIDGET_URL) : DEFAULT_WIDGET_URL;
    const API_URL = scriptTag ? (scriptTag.getAttribute('data-api-url') || 'http://localhost:8000') : 'http://localhost:8000';
    const SITE_URL = scriptTag ? (scriptTag.getAttribute('data-site-url') || 'https://example.com') : 'https://example.com';
    
    // --- State ---
    let isOpen = false;
    let isLoaded = false;
    let iframe = null;
    let launcher = null;

    // --- Helper Utilities ---
    function createElementWithAttrs(tag, attrs = {}, styles = {}) {
        const el = document.createElement(tag);
        Object.keys(attrs).forEach(key => el.setAttribute(key, attrs[key]));
        Object.keys(styles).forEach(key => el.style[key] = styles[key]);
        return el;
    }

    function ensureSingleInstance() {
        if (document.getElementById('fin-chat-root')) {
            console.warn('Fin Widget is already loaded.');
            return false;
        }
        return true;
    }

    function safePostMessage(message) {
        if (iframe && iframe.contentWindow) {
            // SECURITY: In production, replace '*' with the specific origin of your widget
            // const targetOrigin = new URL(WIDGET_URL).origin;
            iframe.contentWindow.postMessage(message, '*');
        }
    }

    // --- UI Construction ---
    function init() {
        if (!ensureSingleInstance()) return;

        const root = document.createElement('div');
        root.id = 'fin-chat-root';
        document.body.appendChild(root);

        // 1. Create Launcher
        launcher = createElementWithAttrs('button', {
            'aria-label': 'Open Chat',
            'aria-expanded': 'false'
        }, {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            backgroundColor: '#C41E3A', // Anurag Red
            color: '#fff',
            border: 'none',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            zIndex: '999999',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'transform 0.2s'
        });

        // Launcher Icon (Chat bubble with dots)
        launcher.innerHTML = `<svg width="34" height="34" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" d="M20 2H4C2.9 2 2 2.9 2 4V16C2 17.1 2.9 18 4 18H18L22 22V4C22 2.9 21.1 2 20 2ZM8 11C8.55 11 9 10.55 9 10C9 9.45 8.55 9 8 9C7.45 9 7 9.45 7 10C7 10.55 7.45 11 8 11ZM12 11C12.55 11 13 10.55 13 10C13 9.45 12.55 9 12 9C11.45 9 11 9.45 11 10C11 10.55 11.45 11 12 11ZM16 11C16.55 11 17 10.55 17 10C17 9.45 16.55 9 16 9C15.45 9 15 9.45 15 10C15 10.55 15.45 11 16 11Z"/></svg>`;

        launcher.addEventListener('click', toggleChat);
        root.appendChild(launcher);

        // 2. Create Iframe Container (Hidden)
        iframe = createElementWithAttrs('iframe', {
            'title': 'Chat Widget',
            'frameborder': '0'
        }, {
            position: 'fixed',
            bottom: '100px',
            right: '20px',
            width: '380px',
            height: '600px',
            maxHeight: 'calc(100vh - 120px)',
            maxWidth: 'calc(100vw - 40px)',
            borderRadius: '16px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
            zIndex: '999999',
            opacity: '0',
            pointerEvents: 'none',
            transition: 'opacity 0.3s, transform 0.3s',
            transform: 'translateY(20px)',
            backgroundColor: '#fff' // Prevent transparency during load
        });

        root.appendChild(iframe);

        // --- Event Listeners ---
        window.addEventListener('message', handleMessage);
        
        // Keyboard accessibility
        launcher.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleChat();
            }
        });
    }

    // --- Logic ---
    function toggleChat() {
        isOpen = !isOpen;
        launcher.setAttribute('aria-expanded', isOpen);

        if (isOpen) {
            // Lazy load on first open
            if (!isLoaded) {
                // Handle relative URLs by providing a base (current page origin)
                // If WIDGET_URL is absolute, the base is ignored.
                const url = new URL(WIDGET_URL, window.location.origin);
                url.searchParams.append('apiUrl', API_URL);
                url.searchParams.append('siteUrl', SITE_URL);
                iframe.src = url.toString();
                isLoaded = true;
            }

            // Show iframe
            iframe.style.opacity = '1';
            iframe.style.pointerEvents = 'all';
            iframe.style.transform = 'translateY(0)';
            
            // Change launcher icon to 'X'
            launcher.innerHTML = `<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;
            launcher.setAttribute('aria-label', 'Close Chat');
        } else {
            // Hide iframe
            iframe.style.opacity = '0';
            iframe.style.pointerEvents = 'none';
            iframe.style.transform = 'translateY(20px)';

            // Change launcher icon back
            launcher.innerHTML = `<svg width="34" height="34" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" d="M20 2H4C2.9 2 2 2.9 2 4V16C2 17.1 2.9 18 4 18H18L22 22V4C22 2.9 21.1 2 20 2ZM8 11C8.55 11 9 10.55 9 10C9 9.45 8.55 9 8 9C7.45 9 7 9.45 7 10C7 10.55 7.45 11 8 11ZM12 11C12.55 11 13 10.55 13 10C13 9.45 12.55 9 12 9C11.45 9 11 9.45 11 10C11 10.55 11.45 11 12 11ZM16 11C16.55 11 17 10.55 17 10C17 9.45 16.55 9 16 9C15.45 9 15 9.45 15 10C15 10.55 15.45 11 16 11Z"/></svg>`;
            launcher.setAttribute('aria-label', 'Open Chat');
        }
    }

    function handleMessage(event) {
        // SECURITY: Validate origin
        // const expectedOrigin = new URL(WIDGET_URL).origin;
        // if (event.origin !== expectedOrigin) return;

        const data = event.data;
        if (!data || !data.type) return;

        if (data.type === 'widget.ready') {
            // Dispatch CustomEvent for the host page
            window.dispatchEvent(new CustomEvent('finChat.ready', { detail: { loaded: true } }));
        } else if (data.type === 'chat.message_sent') {
            window.dispatchEvent(new CustomEvent('finChat.message', { detail: { text: data.text } }));
        }
    }

    // --- Public API ---
    window.finChat = {
        open: () => {
            if (!isOpen) toggleChat();
        },
        close: () => {
            if (isOpen) toggleChat();
        },
        send: (text) => {
            if (!isOpen) toggleChat(); // Ensure open
            safePostMessage({ type: 'widget.add_message', who: 'user', text });
        },
        setTheme: (theme) => {
            safePostMessage({ type: 'widget.set_theme', theme });
        }
    };

    // Initialize
    if (document.readyState === 'complete') {
        init();
    } else {
        window.addEventListener('load', init);
    }

})();
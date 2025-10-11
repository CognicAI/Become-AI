// Configuration and Constants
export const CONFIG = {
  API_BASE: 'http://localhost:8000',
  WS_BASE: 'ws://localhost:8000',
  
  // UI Settings
  MAX_MESSAGE_LENGTH: 2000,
  TYPING_DELAY: 1000,
  AUTO_SCROLL_THRESHOLD: 100,
  
  // API Endpoints
  ENDPOINTS: {
    QUERY_STREAM: '/query/stream',
    SCRAPE: '/scrape',
    SCRAPE_STATUS: '/scrape/status'
  },
  
  // Default values
  DEFAULTS: {
    LLM_SOURCE: 'local',
    MODEL_NAME: 'deepseek-ai/DeepSeek-V3-0324',
    SITE_URL: 'https://example.com'
  },
  
  // Theme settings
  THEMES: {
    DARK: 'dark',
    LIGHT: 'light',
    AUTO: 'auto'
  },
  
  // Local storage keys
  STORAGE_KEYS: {
    THEME: 'rag_theme',
    LLM_SOURCE: 'rag_llm_source',
    MODEL_NAME: 'rag_model_name',
    SITE_URL: 'rag_site_url',
    CHAT_HISTORY: 'rag_chat_history'
  }
};

// Event names for custom events
export const EVENTS = {
  MESSAGE_SENT: 'message:sent',
  MESSAGE_RECEIVED: 'message:received',
  TYPING_START: 'typing:start',
  TYPING_STOP: 'typing:stop',
  CONNECTION_STATUS: 'connection:status',
  ERROR: 'error',
  THEME_CHANGED: 'theme:changed'
};

// Error messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection.',
  API_ERROR: 'API error. Please try again.',
  INVALID_URL: 'Please enter a valid URL.',
  EMPTY_MESSAGE: 'Please enter a message.',
  RATE_LIMITED: 'Too many requests. Please wait a moment.',
  SERVER_ERROR: 'Server error. Please try again later.'
};
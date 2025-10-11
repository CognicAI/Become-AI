// Main application entry point
import { CONFIG, EVENTS } from './modules/config.js';
import { Utils } from './modules/utils.js';
import { chatManager } from './modules/chat.js';
import { apiService } from './modules/api.js';
import { ChatUI } from './components/ChatUI.js';
import { ConfigPanel } from './components/ConfigPanel.js';
import { ChatInput } from './components/ChatInput.js';

class BecomeAIApp {
  constructor() {
    this.chatUI = null;
    this.configPanel = null;
    this.chatInput = null;
    this.isInitialized = false;
    
    this.init();
  }

  /**
   * Initialize the application
   */
  async init() {
    try {
      console.log('Initializing Become AI RAG System...');
      
      // Wait for DOM to be ready
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.initializeComponents());
      } else {
        this.initializeComponents();
      }
      
    } catch (error) {
      console.error('Failed to initialize app:', error);
      this.showFatalError(error);
    }
  }

  /**
   * Initialize UI components
   */
  initializeComponents() {
    try {
      // Get container elements
      const chatContainer = document.getElementById('chat-container');
      const configContainer = document.getElementById('config-container');
      const inputContainer = document.getElementById('input-container');

      if (!chatContainer || !configContainer || !inputContainer) {
        throw new Error('Required DOM elements not found');
      }

      // Initialize components
      this.configPanel = new ConfigPanel(configContainer);
      this.chatUI = new ChatUI(chatContainer);
      this.chatInput = new ChatInput(inputContainer);

      // Setup event listeners
      this.setupEventListeners();

      // Initialize theme
      this.initializeTheme();

      // Check API health
      this.checkApiHealth();

      // Load draft message
      this.chatInput.loadDraft();

      this.isInitialized = true;
      console.log('App initialized successfully');

    } catch (error) {
      console.error('Failed to initialize components:', error);
      this.showFatalError(error);
    }
  }

  /**
   * Setup application event listeners
   */
  setupEventListeners() {
    // Chat events
    chatManager.addEventListener(EVENTS.MESSAGE_SENT, (event) => {
      const { message } = event.detail;
      this.chatUI.addMessage(message);
    });

    chatManager.addEventListener(EVENTS.MESSAGE_RECEIVED, (event) => {
      const { message, type } = event.detail;
      
      if (type === 'update') {
        this.chatUI.updateMessage(message.id, message);
      } else {
        this.chatUI.addMessage(message);
      }
    });

    chatManager.addEventListener(EVENTS.TYPING_START, () => {
      this.chatUI.showTyping();
      this.chatInput.showTyping(true);
    });

    chatManager.addEventListener(EVENTS.TYPING_STOP, () => {
      this.chatUI.hideTyping();
      this.chatInput.showTyping(false);
    });

    // API events
    apiService.addEventListener(EVENTS.CONNECTION_STATUS, (event) => {
      const { connected } = event.detail;
      this.chatUI.updateConnectionStatus(connected);
    });

    apiService.addEventListener(EVENTS.ERROR, (event) => {
      const { message, type } = event.detail;
      this.showError(message, type);
    });

    // UI component events
    this.chatInput.container.addEventListener('message:send', async (event) => {
      await this.handleMessageSend(event.detail.message);
    });

    this.configPanel.container.addEventListener('config:change', (event) => {
      this.handleConfigChange(event.detail.settings);
    });

    this.chatUI.container.addEventListener('message:delete', (event) => {
      chatManager.deleteMessage(event.detail.messageId);
    });

    // Global keyboard shortcuts
    document.addEventListener('keydown', (event) => {
      this.handleGlobalKeyboard(event);
    });

    // Window events
    window.addEventListener('beforeunload', () => {
      this.cleanup();
    });

    // Theme change detection
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      this.updateTheme();
    });
  }

  /**
   * Handle message sending
   */
  async handleMessageSend(message) {
    try {
      // Get configuration
      const config = this.configPanel.getFormData();
      
      // Send message through chat manager
      await chatManager.sendMessage(message, config.siteUrl, {
        llmSource: config.llmSource,
        modelName: config.modelName
      });

    } catch (error) {
      console.error('Failed to send message:', error);
      this.showError(error.message, 'send');
    }
  }

  /**
   * Handle configuration changes
   */
  handleConfigChange(settings) {
    console.log('Configuration changed:', settings);
    
    // Update input placeholder if needed
    if (settings.siteUrl) {
      this.chatInput.setPlaceholder(`Ask me anything about ${settings.siteUrl}...`);
    }
  }

  /**
   * Handle global keyboard shortcuts
   */
  handleGlobalKeyboard(event) {
    // Ctrl+K or Cmd+K to focus input
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
      event.preventDefault();
      this.chatInput.focus();
      return;
    }

    // Ctrl+Shift+C or Cmd+Shift+C to clear chat
    if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'C') {
      event.preventDefault();
      this.clearChat();
      return;
    }

    // Escape to cancel current operation
    if (event.key === 'Escape') {
      this.cancelCurrentOperation();
      return;
    }
  }

  /**
   * Initialize theme system
   */
  initializeTheme() {
    const savedTheme = Utils.storage.get(CONFIG.STORAGE_KEYS.THEME, CONFIG.THEMES.AUTO);
    this.setTheme(savedTheme);
  }

  /**
   * Set application theme
   */
  setTheme(theme) {
    const root = document.documentElement;
    
    if (theme === CONFIG.THEMES.AUTO) {
      const systemTheme = Utils.getSystemTheme();
      root.setAttribute('data-theme', systemTheme);
    } else {
      root.setAttribute('data-theme', theme);
    }
    
    Utils.storage.set(CONFIG.STORAGE_KEYS.THEME, theme);
  }

  /**
   * Update theme based on system preferences
   */
  updateTheme() {
    const currentTheme = Utils.storage.get(CONFIG.STORAGE_KEYS.THEME);
    if (currentTheme === CONFIG.THEMES.AUTO) {
      this.setTheme(CONFIG.THEMES.AUTO);
    }
  }

  /**
   * Check API health on startup
   */
  async checkApiHealth() {
    try {
      await apiService.healthCheck();
    } catch (error) {
      console.warn('API health check failed:', error);
    }
  }

  /**
   * Clear chat messages
   */
  clearChat() {
    if (confirm('Are you sure you want to clear all messages?')) {
      chatManager.clearMessages();
      this.chatUI.clearMessages();
      this.showNotification('Chat cleared', 'info');
    }
  }

  /**
   * Cancel current operation
   */
  cancelCurrentOperation() {
    if (chatManager.isTyping) {
      apiService.cancel();
      chatManager.cancel();
      this.showNotification('Operation cancelled', 'info');
    }
  }

  /**
   * Show error message
   */
  showError(message, type = 'general') {
    console.error(`Error (${type}):`, message);
    
    // Show in UI
    this.showNotification(message, 'error');
  }

  /**
   * Show notification
   */
  showNotification(message, type = 'info', duration = 3000) {
    // Remove existing notifications
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
      <div class="notification-content">
        <span class="notification-message">${Utils.escapeHtml(message)}</span>
        <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    notification.style.transform = 'translateY(-100%)';
    notification.style.opacity = '0';
    
    requestAnimationFrame(() => {
      notification.style.transform = 'translateY(0)';
      notification.style.opacity = '1';
    });
    
    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        if (notification.parentNode) {
          notification.style.transform = 'translateY(-100%)';
          notification.style.opacity = '0';
          setTimeout(() => notification.remove(), 300);
        }
      }, duration);
    }
  }

  /**
   * Show fatal error
   */
  showFatalError(error) {
    document.body.innerHTML = `
      <div class="error-container">
        <div class="error-content">
          <h1>Application Error</h1>
          <p>Sorry, the application failed to initialize.</p>
          <pre class="error-details">${Utils.escapeHtml(error.toString())}</pre>
          <button onclick="window.location.reload()" class="btn btn-primary">
            Reload Application
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    console.log('Cleaning up application...');
    
    // Cancel any pending operations
    if (apiService) {
      apiService.cancel();
    }
    
    // Save current state
    if (chatManager) {
      chatManager.saveChatHistory();
    }
    
    // Destroy components
    if (this.chatUI) {
      this.chatUI.destroy();
    }
    
    if (this.configPanel) {
      this.configPanel.destroy();
    }
    
    if (this.chatInput) {
      this.chatInput.destroy();
    }
  }

  /**
   * Get application status
   */
  getStatus() {
    return {
      initialized: this.isInitialized,
      chatStats: chatManager?.getStats(),
      apiConnected: apiService?.isConnected,
      theme: document.documentElement.getAttribute('data-theme')
    };
  }
}

// Initialize the application when the script loads
const app = new BecomeAIApp();

// Export for debugging
window.BecomeAI = {
  app,
  chatManager,
  apiService,
  CONFIG,
  Utils
};
// Configuration Panel Component - handles LLM and site settings
import { CONFIG } from '../modules/config.js';
import { Utils } from '../modules/utils.js';

export class ConfigPanel {
  constructor(container) {
    this.container = container;
    this.isCollapsed = false;
    this.settings = this.loadSettings();
    
    this.init();
  }

  /**
   * Initialize the configuration panel
   */
  init() {
    this.render();
    this.setupEventListeners();
    this.restoreSettings();
  }

  /**
   * Load settings from localStorage
   */
  loadSettings() {
    return {
      llmSource: Utils.storage.get(CONFIG.STORAGE_KEYS.LLM_SOURCE, CONFIG.DEFAULTS.LLM_SOURCE),
      modelName: Utils.storage.get(CONFIG.STORAGE_KEYS.MODEL_NAME, CONFIG.DEFAULTS.MODEL_NAME),
      siteUrl: Utils.storage.get(CONFIG.STORAGE_KEYS.SITE_URL, CONFIG.DEFAULTS.SITE_URL)
    };
  }

  /**
   * Save settings to localStorage
   */
  saveSettings() {
    Utils.storage.set(CONFIG.STORAGE_KEYS.LLM_SOURCE, this.settings.llmSource);
    Utils.storage.set(CONFIG.STORAGE_KEYS.MODEL_NAME, this.settings.modelName);
    Utils.storage.set(CONFIG.STORAGE_KEYS.SITE_URL, this.settings.siteUrl);
  }

  /**
   * Render the configuration panel
   */
  render() {
    this.container.innerHTML = `
      <div class="config-panel" id="config-panel">
        <div class="config-header">
          <h3 class="config-title">Settings</h3>
          <button class="config-toggle" id="config-toggle" title="Toggle settings">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M6 9l6 6 6-6"/>
            </svg>
          </button>
        </div>
        <div class="config-content" id="config-content">
          <div class="form-group">
            <label class="form-label" for="site-url">Website URL</label>
            <input 
              type="url" 
              id="site-url" 
              class="form-input" 
              placeholder="https://example.com"
              value="${this.settings.siteUrl}"
              required
            />
            <small class="form-help">The website you want to ask questions about</small>
          </div>

          <div class="config-row">
            <div class="form-group">
              <label class="form-label" for="llm-source">LLM Source</label>
              <select id="llm-source" class="form-select">
                <option value="local">Local LLM (LM Studio)</option>
                <option value="cloud">Cloud LLM (Hugging Face)</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label" for="model-name">Cloud Model</label>
              <input 
                type="text" 
                id="model-name" 
                class="form-input" 
                placeholder="deepseek-ai/DeepSeek-V3-0324"
                value="${this.settings.modelName}"
              />
              <small class="form-help">Only for cloud LLM</small>
            </div>
          </div>

          <div class="config-actions">
            <button type="button" class="btn btn-secondary btn-sm" id="reset-settings">
              Reset to Defaults
            </button>
            <button type="button" class="btn btn-primary btn-sm" id="test-connection">
              Test Connection
            </button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    const toggleBtn = this.container.querySelector('#config-toggle');
    const content = this.container.querySelector('#config-content');
    const siteUrlInput = this.container.querySelector('#site-url');
    const llmSourceSelect = this.container.querySelector('#llm-source');
    const modelNameInput = this.container.querySelector('#model-name');
    const resetBtn = this.container.querySelector('#reset-settings');
    const testBtn = this.container.querySelector('#test-connection');

    // Toggle panel
    toggleBtn.addEventListener('click', () => {
      this.togglePanel();
    });

    // Site URL changes
    siteUrlInput.addEventListener('input', Utils.debounce((e) => {
      this.settings.siteUrl = e.target.value;
      this.saveSettings();
      this.validateUrl(e.target);
    }, 500));

    siteUrlInput.addEventListener('blur', (e) => {
      this.validateUrl(e.target);
    });

    // LLM source changes
    llmSourceSelect.addEventListener('change', (e) => {
      this.settings.llmSource = e.target.value;
      this.saveSettings();
      this.updateModelNameVisibility();
      this.emitConfigChange();
    });

    // Model name changes
    modelNameInput.addEventListener('input', Utils.debounce((e) => {
      this.settings.modelName = e.target.value;
      this.saveSettings();
      this.emitConfigChange();
    }, 500));

    // Reset settings
    resetBtn.addEventListener('click', () => {
      this.resetSettings();
    });

    // Test connection
    testBtn.addEventListener('click', () => {
      this.testConnection();
    });
  }

  /**
   * Restore settings to form
   */
  restoreSettings() {
    const siteUrlInput = this.container.querySelector('#site-url');
    const llmSourceSelect = this.container.querySelector('#llm-source');
    const modelNameInput = this.container.querySelector('#model-name');

    siteUrlInput.value = this.settings.siteUrl;
    llmSourceSelect.value = this.settings.llmSource;
    modelNameInput.value = this.settings.modelName;

    this.updateModelNameVisibility();
  }

  /**
   * Toggle panel collapse/expand
   */
  togglePanel() {
    const content = this.container.querySelector('#config-content');
    const toggle = this.container.querySelector('#config-toggle');
    
    this.isCollapsed = !this.isCollapsed;
    
    if (this.isCollapsed) {
      content.style.display = 'none';
      toggle.style.transform = 'rotate(-90deg)';
    } else {
      content.style.display = 'grid';
      toggle.style.transform = 'rotate(0deg)';
    }
  }

  /**
   * Update model name input visibility based on LLM source
   */
  updateModelNameVisibility() {
    const modelNameGroup = this.container.querySelector('#model-name').closest('.form-group');
    const isCloud = this.settings.llmSource === 'cloud';
    
    modelNameGroup.style.opacity = isCloud ? '1' : '0.5';
    modelNameGroup.querySelector('#model-name').disabled = !isCloud;
  }

  /**
   * Validate URL input
   */
  validateUrl(input) {
    const isValid = Utils.isValidUrl(input.value);
    
    input.classList.toggle('error', !isValid && input.value.trim() !== '');
    
    if (!isValid && input.value.trim() !== '') {
      this.showInputError(input, 'Please enter a valid URL');
    } else {
      this.clearInputError(input);
    }
    
    return isValid;
  }

  /**
   * Show input error
   */
  showInputError(input, message) {
    // Remove existing error
    this.clearInputError(input);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'form-error';
    errorDiv.textContent = message;
    
    input.parentNode.appendChild(errorDiv);
    input.classList.add('error');
  }

  /**
   * Clear input error
   */
  clearInputError(input) {
    const errorDiv = input.parentNode.querySelector('.form-error');
    if (errorDiv) {
      errorDiv.remove();
    }
    input.classList.remove('error');
  }

  /**
   * Reset settings to defaults
   */
  resetSettings() {
    if (confirm('Reset all settings to defaults?')) {
      this.settings = {
        llmSource: CONFIG.DEFAULTS.LLM_SOURCE,
        modelName: CONFIG.DEFAULTS.MODEL_NAME,
        siteUrl: CONFIG.DEFAULTS.SITE_URL
      };
      
      this.saveSettings();
      this.restoreSettings();
      this.emitConfigChange();
      
      this.showNotification('Settings reset to defaults', 'success');
    }
  }

  /**
   * Test connection to API
   */
  async testConnection() {
    const testBtn = this.container.querySelector('#test-connection');
    const originalText = testBtn.textContent;
    
    testBtn.textContent = 'Testing...';
    testBtn.disabled = true;
    testBtn.classList.add('btn-loading');
    
    try {
      // Import api service dynamically to avoid circular dependency
      const { apiService } = await import('../modules/api.js');
      const isHealthy = await apiService.healthCheck();
      
      if (isHealthy) {
        this.showNotification('Connection successful!', 'success');
      } else {
        this.showNotification('Connection failed. Check API server.', 'error');
      }
      
    } catch (error) {
      console.error('Connection test failed:', error);
      this.showNotification('Connection test failed', 'error');
    } finally {
      testBtn.textContent = originalText;
      testBtn.disabled = false;
      testBtn.classList.remove('btn-loading');
    }
  }

  /**
   * Show notification
   */
  showNotification(message, type = 'info') {
    // Remove existing notifications
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
      notification.remove();
    }, 3000);
  }

  /**
   * Emit configuration change event
   */
  emitConfigChange() {
    this.container.dispatchEvent(new CustomEvent('config:change', {
      detail: { settings: this.getSettings() }
    }));
  }

  /**
   * Get current settings
   */
  getSettings() {
    return { ...this.settings };
  }

  /**
   * Update settings programmatically
   */
  updateSettings(newSettings) {
    Object.assign(this.settings, newSettings);
    this.saveSettings();
    this.restoreSettings();
    this.emitConfigChange();
  }

  /**
   * Validate current settings
   */
  validateSettings() {
    const errors = [];
    
    if (!Utils.isValidUrl(this.settings.siteUrl)) {
      errors.push('Invalid website URL');
    }
    
    if (this.settings.llmSource === 'cloud' && !this.settings.modelName.trim()) {
      errors.push('Cloud model name is required');
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * Get form data for API calls
   */
  getFormData() {
    const validation = this.validateSettings();
    if (!validation.isValid) {
      throw new Error(`Configuration errors: ${validation.errors.join(', ')}`);
    }
    
    return {
      siteUrl: this.settings.siteUrl,
      llmSource: this.settings.llmSource,
      modelName: this.settings.llmSource === 'cloud' ? this.settings.modelName : null
    };
  }

  /**
   * Destroy the configuration panel
   */
  destroy() {
    this.container.innerHTML = '';
  }
}
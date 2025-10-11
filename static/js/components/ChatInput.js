// Chat Input Component - handles message input and sending
import { CONFIG } from '../modules/config.js';
import { Utils } from '../modules/utils.js';

export class ChatInput {
  constructor(container) {
    this.container = container;
    this.isDisabled = false;
    this.currentInput = '';
    
    this.init();
  }

  /**
   * Initialize the chat input
   */
  init() {
    this.render();
    this.setupEventListeners();
  }

  /**
   * Render the chat input component
   */
  render() {
    this.container.innerHTML = `
      <div class="chat-input-container">
        <form class="chat-input-form" id="chat-form">
          <div class="chat-input-main">
            <div class="chat-input-row">
              <textarea 
                id="chat-input" 
                class="chat-input" 
                placeholder="Ask me anything about the configured website..."
                rows="1"
                maxlength="${CONFIG.MAX_MESSAGE_LENGTH}"
              ></textarea>
              <button type="submit" class="btn-send" id="send-button" disabled>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22,2 15,22 11,13 2,9"></polygon>
                </svg>
              </button>
            </div>
          </div>
        </form>
        <div class="input-footer">
          <div class="input-info">
            <span class="char-count">0/${CONFIG.MAX_MESSAGE_LENGTH}</span>
          </div>
          <div class="input-actions">
            <button type="button" class="btn btn-ghost btn-sm" id="clear-input" title="Clear input">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
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
    const form = this.container.querySelector('#chat-form');
    const input = this.container.querySelector('#chat-input');
    const sendButton = this.container.querySelector('#send-button');
    const clearButton = this.container.querySelector('#clear-input');
    const charCount = this.container.querySelector('.char-count');

    // Form submission
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      this.handleSubmit();
    });

    // Input changes
    input.addEventListener('input', (e) => {
      this.handleInputChange(e);
      this.updateCharCount();
      this.adjustTextareaHeight();
    });

    // Keyboard shortcuts
    input.addEventListener('keydown', (e) => {
      this.handleKeyDown(e);
    });

    // Auto-resize on paste
    input.addEventListener('paste', () => {
      setTimeout(() => {
        this.adjustTextareaHeight();
        this.updateCharCount();
      }, 0);
    });

    // Clear input
    clearButton.addEventListener('click', () => {
      this.clearInput();
    });

    // Focus management
    input.addEventListener('focus', () => {
      this.container.classList.add('focused');
    });

    input.addEventListener('blur', () => {
      this.container.classList.remove('focused');
    });

    // Send button hover effect
    sendButton.addEventListener('mouseenter', () => {
      if (!sendButton.disabled) {
        sendButton.style.transform = 'scale(1.05)';
      }
    });

    sendButton.addEventListener('mouseleave', () => {
      sendButton.style.transform = 'scale(1)';
    });
  }

  /**
   * Handle form submission
   */
  handleSubmit() {
    const input = this.container.querySelector('#chat-input');
    const message = input.value.trim();
    
    if (!message || this.isDisabled) {
      return;
    }

    // Emit message send event
    this.container.dispatchEvent(new CustomEvent('message:send', {
      detail: { message }
    }));

    // Clear input after sending
    this.clearInput();
  }

  /**
   * Handle input changes
   */
  handleInputChange(e) {
    this.currentInput = e.target.value;
    this.updateSendButton();
    
    // Save draft to localStorage
    Utils.storage.set('chat_draft', this.currentInput);
  }

  /**
   * Handle keyboard shortcuts
   */
  handleKeyDown(e) {
    // Enter to send (without shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this.handleSubmit();
      return;
    }

    // Ctrl+Enter to add new line
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      const input = e.target;
      const start = input.selectionStart;
      const end = input.selectionEnd;
      
      input.value = input.value.substring(0, start) + '\\n' + input.value.substring(end);
      input.selectionStart = input.selectionEnd = start + 1;
      
      this.adjustTextareaHeight();
      this.updateCharCount();
      return;
    }

    // Escape to clear
    if (e.key === 'Escape') {
      this.clearInput();
      return;
    }

    // Ctrl+A to select all
    if (e.key === 'a' && e.ctrlKey) {
      e.target.select();
      return;
    }
  }

  /**
   * Update send button state
   */
  updateSendButton() {
    const sendButton = this.container.querySelector('#send-button');
    const hasContent = this.currentInput.trim().length > 0;
    const isValid = hasContent && !this.isDisabled;
    
    sendButton.disabled = !isValid;
    sendButton.classList.toggle('btn-primary', isValid);
    sendButton.classList.toggle('btn-secondary', !isValid);
  }

  /**
   * Update character count
   */
  updateCharCount() {
    const charCount = this.container.querySelector('.char-count');
    const length = this.currentInput.length;
    const max = CONFIG.MAX_MESSAGE_LENGTH;
    
    charCount.textContent = `${length}/${max}`;
    charCount.classList.toggle('error', length > max);
  }

  /**
   * Auto-adjust textarea height
   */
  adjustTextareaHeight() {
    const input = this.container.querySelector('#chat-input');
    
    // Reset height to auto to get the natural height
    input.style.height = 'auto';
    
    // Set height based on scroll height, with min and max constraints
    const minHeight = 44; // 1 row
    const maxHeight = 120; // ~3 rows
    const newHeight = Math.min(Math.max(input.scrollHeight, minHeight), maxHeight);
    
    input.style.height = newHeight + 'px';
  }

  /**
   * Clear input
   */
  clearInput() {
    const input = this.container.querySelector('#chat-input');
    input.value = '';
    this.currentInput = '';
    this.adjustTextareaHeight();
    this.updateCharCount();
    this.updateSendButton();
    
    // Clear draft from storage
    Utils.storage.remove('chat_draft');
    
    // Focus input
    input.focus();
  }

  /**
   * Set input value programmatically
   */
  setValue(value) {
    const input = this.container.querySelector('#chat-input');
    input.value = value;
    this.currentInput = value;
    this.adjustTextareaHeight();
    this.updateCharCount();
    this.updateSendButton();
  }

  /**
   * Get current input value
   */
  getValue() {
    return this.currentInput;
  }

  /**
   * Enable/disable input
   */
  setDisabled(disabled) {
    this.isDisabled = disabled;
    const input = this.container.querySelector('#chat-input');
    const sendButton = this.container.querySelector('#send-button');
    
    input.disabled = disabled;
    this.updateSendButton();
    
    if (disabled) {
      this.container.classList.add('disabled');
      input.placeholder = 'Please wait...';
    } else {
      this.container.classList.remove('disabled');
      input.placeholder = 'Ask me anything about the configured website...';
      input.focus();
    }
  }

  /**
   * Focus input
   */
  focus() {
    const input = this.container.querySelector('#chat-input');
    input.focus();
  }

  /**
   * Show typing indicator in input
   */
  showTyping(show = true) {
    if (show) {
      this.setDisabled(true);
    } else {
      this.setDisabled(false);
    }
  }

  /**
   * Load draft from storage
   */
  loadDraft() {
    const draft = Utils.storage.get('chat_draft', '');
    if (draft) {
      this.setValue(draft);
    }
  }

  /**
   * Insert text at cursor position
   */
  insertText(text) {
    const input = this.container.querySelector('#chat-input');
    const start = input.selectionStart;
    const end = input.selectionEnd;
    
    const newValue = this.currentInput.substring(0, start) + text + this.currentInput.substring(end);
    this.setValue(newValue);
    
    // Set cursor position after inserted text
    const newPosition = start + text.length;
    input.setSelectionRange(newPosition, newPosition);
  }

  /**
   * Set placeholder text
   */
  setPlaceholder(text) {
    const input = this.container.querySelector('#chat-input');
    input.placeholder = text;
  }

  /**
   * Destroy the chat input
   */
  destroy() {
    // Save current draft
    if (this.currentInput.trim()) {
      Utils.storage.set('chat_draft', this.currentInput);
    }
    
    this.container.innerHTML = '';
  }
}
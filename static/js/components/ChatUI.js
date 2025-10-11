// Chat UI Component - handles the visual representation of the chat
import { CONFIG, EVENTS } from '../modules/config.js';
import { Utils } from '../modules/utils.js';

export class ChatUI {
  constructor(container) {
    this.container = container;
    this.messagesContainer = null;
    this.typingIndicator = null;
    this.shouldAutoScroll = true;
    
    this.init();
  }

  /**
   * Initialize the chat UI
   */
  init() {
    this.render();
    this.setupEventListeners();
  }

  /**
   * Render the chat UI structure
   */
  render() {
    this.container.innerHTML = `
      <div class="chat-container">
        <div class="chat-header">
          <h2>AI Assistant</h2>
          <div class="chat-status">
            <div class="status-indicator" id="connection-status"></div>
            <span id="status-text">Connected</span>
          </div>
        </div>
        <div class="chat-messages" id="chat-messages">
          <div class="message assistant">
            <div class="message-content">
              👋 Hello! I'm your AI assistant. Ask me anything about the websites you've configured.
            </div>
            <div class="message-meta">
              <span class="message-time">${Utils.formatTime()}</span>
            </div>
          </div>
        </div>
        <div class="typing-indicator hidden" id="typing-indicator">
          <div class="typing-dots">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
          </div>
          <span>AI is thinking...</span>
        </div>
      </div>
    `;

    this.messagesContainer = this.container.querySelector('#chat-messages');
    this.typingIndicator = this.container.querySelector('#typing-indicator');
    this.statusIndicator = this.container.querySelector('#connection-status');
    this.statusText = this.container.querySelector('#status-text');
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Handle scroll behavior for auto-scroll
    this.messagesContainer.addEventListener('scroll', Utils.throttle(() => {
      this.shouldAutoScroll = Utils.isScrolledToBottom(this.messagesContainer);
    }, 100));

    // Handle window resize
    window.addEventListener('resize', Utils.debounce(() => {
      if (this.shouldAutoScroll) {
        this.scrollToBottom();
      }
    }, 250));
  }

  /**
   * Add a message to the chat UI
   */
  addMessage(message) {
    const messageElement = this.createMessageElement(message);
    
    // Insert before typing indicator if it exists
    if (this.typingIndicator.parentNode === this.messagesContainer) {
      this.messagesContainer.insertBefore(messageElement, this.typingIndicator);
    } else {
      this.messagesContainer.appendChild(messageElement);
    }

    // Auto-scroll if needed
    if (this.shouldAutoScroll) {
      this.scrollToBottom();
    }

    return messageElement;
  }

  /**
   * Update an existing message
   */
  updateMessage(messageId, updates) {
    const messageElement = this.messagesContainer.querySelector(`[data-message-id="${messageId}"]`);
    if (!messageElement) return null;

    const contentElement = messageElement.querySelector('.message-content');
    const metaElement = messageElement.querySelector('.message-meta');

    if (updates.content !== undefined) {
      // Format the content with proper line breaks and styling
      const formattedContent = this.formatMessageContent(updates.content);
      contentElement.innerHTML = formattedContent;
    }

    if (updates.isStreaming !== undefined) {
      messageElement.classList.toggle('streaming', updates.isStreaming);
    }

    if (updates.metadata) {
      this.updateMessageMetadata(messageElement, updates.metadata);
    }

    // Auto-scroll if this was the last message and we should auto-scroll
    if (this.shouldAutoScroll && this.isLastMessage(messageElement)) {
      this.scrollToBottom();
    }

    return messageElement;
  }

  /**
   * Format message content with proper styling and line breaks
   */
  formatMessageContent(content) {
    if (!content) return '';
    
    // Escape HTML first
    let formatted = Utils.escapeHtml(content);
    
    // Handle markdown-style formatting
    formatted = formatted
      // Bold text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Italic text  
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      // Headers
      .replace(/^### (.*$)/gm, '<h3>$1</h3>')
      .replace(/^## (.*$)/gm, '<h2>$1</h2>')
      .replace(/^# (.*$)/gm, '<h1>$1</h1>')
      // Line breaks for better readability
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>')
      // Wrap in paragraph if not already formatted
      .replace(/^(?!<[hpu])/gm, '<p>')
      .replace(/(?<![>])$/gm, '</p>')
      // Clean up empty paragraphs
      .replace(/<p><\/p>/g, '')
      .replace(/<p><br><\/p>/g, '<br>')
      // Lists (basic support)
      .replace(/^\- (.*$)/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    return formatted;
  }

  /**
   * Create a message element
   */
  createMessageElement(message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${message.role}`;
    messageDiv.setAttribute('data-message-id', message.id);
    
    if (message.isStreaming) {
      messageDiv.classList.add('streaming');
    }

    if (message.type === 'error') {
      messageDiv.classList.add('error');
    }

    // Format the content properly
    const formattedContent = this.formatMessageContent(message.content);

    messageDiv.innerHTML = `
      <div class="message-content">${formattedContent}</div>
      <div class="message-meta">
        <span class="message-time">${Utils.formatTime(message.timestamp)}</span>
        <div class="message-actions">
          ${this.createMessageActions(message)}
        </div>
      </div>
    `;

    // Add metadata if present
    if (message.metadata) {
      this.updateMessageMetadata(messageDiv, message.metadata);
    }

    // Add event listeners for actions
    this.attachMessageEventListeners(messageDiv, message);

    return messageDiv;
  }

  /**
   * Create message action buttons
   */
  createMessageActions(message) {
    const actions = [];
    
    if (message.role === 'assistant' && message.content.trim()) {
      actions.push(`
        <button class="message-action" data-action="copy" title="Copy message">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        </button>
      `);
    }

    if (message.role === 'user') {
      actions.push(`
        <button class="message-action" data-action="edit" title="Edit message">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
            <path d="m18.5 2.5 a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
          </svg>
        </button>
      `);
    }

    actions.push(`
      <button class="message-action" data-action="delete" title="Delete message">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3,6 5,6 21,6"></polyline>
          <path d="m19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"></path>
        </svg>
      </button>
    `);

    return actions.join('');
  }

  /**
   * Attach event listeners to message elements
   */
  attachMessageEventListeners(messageElement, message) {
    const actions = messageElement.querySelectorAll('.message-action');
    
    actions.forEach(action => {
      action.addEventListener('click', (e) => {
        e.stopPropagation();
        this.handleMessageAction(action.dataset.action, message, messageElement);
      });
    });
  }

  /**
   * Handle message action clicks
   */
  async handleMessageAction(action, message, messageElement) {
    switch (action) {
      case 'copy':
        const success = await Utils.copyToClipboard(message.content);
        if (success) {
          this.showTooltip(messageElement, 'Copied!');
        }
        break;
        
      case 'edit':
        this.editMessage(message, messageElement);
        break;
        
      case 'delete':
        this.deleteMessage(message, messageElement);
        break;
    }
  }

  /**
   * Show typing indicator
   */
  showTyping() {
    this.typingIndicator.classList.remove('hidden');
    this.messagesContainer.appendChild(this.typingIndicator);
    
    if (this.shouldAutoScroll) {
      this.scrollToBottom();
    }
  }

  /**
   * Hide typing indicator
   */
  hideTyping() {
    this.typingIndicator.classList.add('hidden');
    if (this.typingIndicator.parentNode) {
      this.typingIndicator.parentNode.removeChild(this.typingIndicator);
    }
  }

  /**
   * Update connection status
   */
  updateConnectionStatus(connected) {
    this.statusIndicator.className = `status-indicator ${connected ? '' : 'error'}`;
    this.statusText.textContent = connected ? 'Connected' : 'Disconnected';
  }

  /**
   * Update message metadata (sources, chunks, etc.)
   */
  updateMessageMetadata(messageElement, metadata) {
    if (metadata.chunks) {
      const metaElement = messageElement.querySelector('.message-meta');
      
      // Remove existing sources
      const existingSources = metaElement.querySelector('.message-sources');
      if (existingSources) {
        existingSources.remove();
      }

      // Add sources
      const sourcesDiv = document.createElement('div');
      sourcesDiv.className = 'message-sources';
      sourcesDiv.innerHTML = `
        <div class="sources-label">Sources (${metadata.chunks.length}):</div>
        ${metadata.chunks.map((chunk, index) => `
          <a href="${chunk.url}" target="_blank" class="source-link" title="${Utils.escapeHtml(chunk.title)}">
            ${index + 1}
          </a>
        `).join('')}
      `;
      
      metaElement.appendChild(sourcesDiv);
    }
  }

  /**
   * Show tooltip
   */
  showTooltip(element, text) {
    // Remove existing tooltips
    document.querySelectorAll('.tooltip').forEach(t => t.remove());
    
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    document.body.appendChild(tooltip);
    
    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) + 'px';
    tooltip.style.top = (rect.top - tooltip.offsetHeight - 8) + 'px';
    
    setTimeout(() => tooltip.remove(), 2000);
  }

  /**
   * Clear all messages
   */
  clearMessages() {
    // Keep the welcome message and clear the rest
    const messages = this.messagesContainer.querySelectorAll('.message:not(:first-child)');
    messages.forEach(message => message.remove());
    
    this.hideTyping();
  }

  /**
   * Scroll to bottom
   */
  scrollToBottom(behavior = 'smooth') {
    Utils.scrollToBottom(this.messagesContainer, behavior);
  }

  /**
   * Check if message is the last one
   */
  isLastMessage(messageElement) {
    const messages = this.messagesContainer.querySelectorAll('.message');
    return messages[messages.length - 1] === messageElement;
  }

  /**
   * Get message element by ID
   */
  getMessageElement(messageId) {
    return this.messagesContainer.querySelector(`[data-message-id="${messageId}"]`);
  }

  /**
   * Edit message (placeholder for future implementation)
   */
  editMessage(message, messageElement) {
    // TODO: Implement message editing
    console.log('Edit message:', message);
  }

  /**
   * Delete message
   */
  deleteMessage(message, messageElement) {
    if (confirm('Are you sure you want to delete this message?')) {
      messageElement.remove();
      // Emit event for chat manager to handle
      this.container.dispatchEvent(new CustomEvent('message:delete', {
        detail: { messageId: message.id }
      }));
    }
  }

  /**
   * Destroy the chat UI
   */
  destroy() {
    // Remove event listeners
    window.removeEventListener('resize', this.resizeHandler);
    
    // Clear container
    this.container.innerHTML = '';
  }
}
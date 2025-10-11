// Chat management and message handling
import { CONFIG, EVENTS } from './config.js';
import { Utils } from './utils.js';
import { apiService } from './api.js';

export class ChatManager {
  constructor() {
    this.messages = [];
    this.isTyping = false;
    this.currentStreamingMessage = null;
    this.eventTarget = new EventTarget();
    
    // Load chat history from storage
    this.loadChatHistory();
    
    // Listen to API events
    this.setupApiListeners();
  }

  /**
   * Add event listener for chat events
   */
  addEventListener(event, callback) {
    this.eventTarget.addEventListener(event, callback);
  }

  /**
   * Remove event listener
   */
  removeEventListener(event, callback) {
    this.eventTarget.removeEventListener(event, callback);
  }

  /**
   * Emit custom event
   */
  emit(eventName, data = {}) {
    this.eventTarget.dispatchEvent(new CustomEvent(eventName, { detail: data }));
  }

  /**
   * Setup API event listeners
   */
  setupApiListeners() {
    apiService.addEventListener(EVENTS.MESSAGE_RECEIVED, (event) => {
      this.handleApiMessage(event.detail);
    });

    apiService.addEventListener(EVENTS.TYPING_START, () => {
      this.setTyping(true);
    });

    apiService.addEventListener(EVENTS.TYPING_STOP, () => {
      this.setTyping(false);
    });

    apiService.addEventListener(EVENTS.ERROR, (event) => {
      this.handleError(event.detail);
    });
  }

  /**
   * Handle incoming API messages
   */
  handleApiMessage(data) {
    if (data.type === 'start') {
      // Start new assistant message
      this.currentStreamingMessage = this.addMessage('assistant', data.content, {
        isStreaming: true,
        timestamp: new Date()
      });
    } else if (data.type === 'token' && this.currentStreamingMessage) {
      // Append token to current message
      this.currentStreamingMessage.content += data.content;
      this.updateMessage(this.currentStreamingMessage.id, {
        content: this.currentStreamingMessage.content
      });
    } else if (data.type === 'metadata') {
      // Handle metadata (sources, etc.)
      if (this.currentStreamingMessage) {
        this.updateMessage(this.currentStreamingMessage.id, {
          metadata: data
        });
      }
    }
  }

  /**
   * Handle API errors
   */
  handleError(error) {
    // Add error message to chat
    this.addMessage('system', `Error: ${error.message}`, {
      type: 'error',
      timestamp: new Date()
    });
    
    // Stop typing if active
    this.setTyping(false);
  }

  /**
   * Add a new message to the chat
   */
  addMessage(role, content, options = {}) {
    const message = {
      id: Utils.generateId(),
      role,
      content,
      timestamp: options.timestamp || new Date(),
      isStreaming: options.isStreaming || false,
      metadata: options.metadata || null,
      type: options.type || 'message',
      ...options
    };

    this.messages.push(message);
    
    // Emit event for UI updates
    this.emit(EVENTS.MESSAGE_SENT, { message });
    
    // Save to storage
    this.saveChatHistory();
    
    return message;
  }

  /**
   * Update an existing message
   */
  updateMessage(messageId, updates) {
    const messageIndex = this.messages.findIndex(m => m.id === messageId);
    if (messageIndex === -1) return null;

    const message = this.messages[messageIndex];
    Object.assign(message, updates);
    
    // Emit event for UI updates
    this.emit(EVENTS.MESSAGE_RECEIVED, { message, type: 'update' });
    
    // Save to storage
    this.saveChatHistory();
    
    return message;
  }

  /**
   * Send a user message and get AI response
   */
  async sendMessage(content, siteUrl, llmConfig = {}) {
    try {
      // Validate input
      if (!content?.trim()) {
        throw new Error('Message cannot be empty');
      }

      if (this.isTyping) {
        throw new Error('Please wait for the current response to complete');
      }

      // Add user message
      const userMessage = this.addMessage('user', content.trim(), {
        timestamp: new Date()
      });

      // Start streaming response
      const { llmSource = 'local', modelName = null } = llmConfig;
      
      try {
        const response = await apiService.streamQuery(
          content.trim(),
          siteUrl,
          llmSource,
          modelName
        );

        // Finalize the streaming message
        if (this.currentStreamingMessage) {
          this.updateMessage(this.currentStreamingMessage.id, {
            isStreaming: false,
            completed: response.completed
          });
          this.currentStreamingMessage = null;
        }

        return response;

      } catch (error) {
        // Remove typing indicator and handle error
        this.setTyping(false);
        this.currentStreamingMessage = null;
        throw error;
      }

    } catch (error) {
      console.error('Send message error:', error);
      this.handleError({ message: error.message, type: 'send' });
      throw error;
    }
  }

  /**
   * Set typing status
   */
  setTyping(isTyping) {
    if (this.isTyping !== isTyping) {
      this.isTyping = isTyping;
      this.emit(isTyping ? EVENTS.TYPING_START : EVENTS.TYPING_STOP);
    }
  }

  /**
   * Clear all messages
   */
  clearMessages() {
    this.messages = [];
    this.currentStreamingMessage = null;
    this.setTyping(false);
    
    // Clear storage
    this.saveChatHistory();
    
    // Emit event
    this.emit('messages:cleared');
  }

  /**
   * Get all messages
   */
  getMessages() {
    return [...this.messages];
  }

  /**
   * Get message by ID
   */
  getMessage(id) {
    return this.messages.find(m => m.id === id);
  }

  /**
   * Delete a message
   */
  deleteMessage(id) {
    const index = this.messages.findIndex(m => m.id === id);
    if (index === -1) return false;

    const message = this.messages[index];
    this.messages.splice(index, 1);
    
    // Save to storage
    this.saveChatHistory();
    
    // Emit event
    this.emit('message:deleted', { message });
    
    return true;
  }

  /**
   * Export chat history
   */
  exportChat(format = 'json') {
    const data = {
      messages: this.messages,
      exportedAt: new Date().toISOString(),
      version: '1.0'
    };

    if (format === 'json') {
      return JSON.stringify(data, null, 2);
    } else if (format === 'text') {
      return this.messages
        .map(m => `[${Utils.formatTime(m.timestamp)}] ${m.role}: ${m.content}`)
        .join('\\n');
    }
    
    return data;
  }

  /**
   * Import chat history
   */
  importChat(data, merge = false) {
    try {
      const imported = typeof data === 'string' ? JSON.parse(data) : data;
      
      if (!imported.messages || !Array.isArray(imported.messages)) {
        throw new Error('Invalid chat data format');
      }

      if (!merge) {
        this.clearMessages();
      }

      imported.messages.forEach(message => {
        // Ensure required fields
        if (message.role && message.content) {
          this.addMessage(message.role, message.content, {
            timestamp: new Date(message.timestamp || Date.now()),
            metadata: message.metadata,
            type: message.type
          });
        }
      });

      return true;

    } catch (error) {
      console.error('Import chat error:', error);
      return false;
    }
  }

  /**
   * Save chat history to local storage
   */
  saveChatHistory() {
    const dataToSave = {
      messages: this.messages.slice(-100), // Keep last 100 messages
      lastSaved: new Date().toISOString()
    };
    
    Utils.storage.set(CONFIG.STORAGE_KEYS.CHAT_HISTORY, dataToSave);
  }

  /**
   * Load chat history from local storage
   */
  loadChatHistory() {
    const data = Utils.storage.get(CONFIG.STORAGE_KEYS.CHAT_HISTORY);
    
    if (data?.messages) {
      this.messages = data.messages.map(message => ({
        ...message,
        timestamp: new Date(message.timestamp)
      }));
    }
  }

  /**
   * Cancel current operation
   */
  cancel() {
    apiService.cancel();
    this.setTyping(false);
    this.currentStreamingMessage = null;
  }

  /**
   * Get chat statistics
   */
  getStats() {
    const userMessages = this.messages.filter(m => m.role === 'user');
    const assistantMessages = this.messages.filter(m => m.role === 'assistant');
    
    return {
      totalMessages: this.messages.length,
      userMessages: userMessages.length,
      assistantMessages: assistantMessages.length,
      firstMessage: this.messages[0]?.timestamp,
      lastMessage: this.messages[this.messages.length - 1]?.timestamp,
      isTyping: this.isTyping
    };
  }
}

// Create singleton instance
export const chatManager = new ChatManager();
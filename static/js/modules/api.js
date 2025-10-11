// API service for handling HTTP requests and streaming
import { CONFIG, EVENTS, ERROR_MESSAGES } from './config.js';
import { Utils } from './utils.js';

export class ApiService {
  constructor() {
    this.abortController = null;
    this.isConnected = true;
    this.eventTarget = new EventTarget();
  }

  /**
   * Add event listener for API events
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
   * Handle network errors
   */
  handleNetworkError(error) {
    console.error('Network error:', error);
    this.isConnected = false;
    this.emit(EVENTS.CONNECTION_STATUS, { connected: false });
    this.emit(EVENTS.ERROR, { 
      message: ERROR_MESSAGES.NETWORK_ERROR,
      type: 'network',
      error 
    });
  }

  /**
   * Handle API errors
   */
  handleApiError(response, message = ERROR_MESSAGES.API_ERROR) {
    console.error('API error:', response.status, response.statusText);
    this.emit(EVENTS.ERROR, {
      message: `${message} (${response.status})`,
      type: 'api',
      status: response.status,
      statusText: response.statusText
    });
  }

  /**
   * Create AbortController for cancelling requests
   */
  createAbortController() {
    if (this.abortController) {
      this.abortController.abort();
    }
    this.abortController = new AbortController();
    return this.abortController;
  }

  /**
   * Send query with streaming response
   */
  async streamQuery(question, siteUrl, llmSource = 'local', modelName = null) {
    try {
      // Validate inputs
      if (!question?.trim()) {
        throw new Error(ERROR_MESSAGES.EMPTY_MESSAGE);
      }

      if (!Utils.isValidUrl(siteUrl)) {
        throw new Error(ERROR_MESSAGES.INVALID_URL);
      }

      // Create abort controller for this request
      const controller = this.createAbortController();

      // Build query parameters
      const params = new URLSearchParams({
        question: question.trim(),
        site_base_url: siteUrl,
        llm_source: llmSource
      });

      if (llmSource === 'cloud' && modelName) {
        params.append('llm_model_name', modelName);
      }

      // Construct URL
      const url = `${CONFIG.API_BASE}${CONFIG.ENDPOINTS.QUERY_STREAM}?${params}`;

      console.log('Starting stream query:', { question, siteUrl, llmSource, modelName });

      // Create EventSource for streaming
      const eventSource = new EventSource(url);
      
      // Track connection status
      this.isConnected = true;
      this.emit(EVENTS.CONNECTION_STATUS, { connected: true });

      // Return a promise that resolves when streaming is complete
      return new Promise((resolve, reject) => {
        let assistantMessage = '';
        let hasStarted = false;

        eventSource.onopen = () => {
          console.log('Stream connection opened');
          this.emit(EVENTS.TYPING_START);
        };

        eventSource.onmessage = (event) => {
          try {
            // Handle completion signal
            if (event.data === '[DONE]') {
              eventSource.close();
              this.emit(EVENTS.TYPING_STOP);
              resolve({ content: assistantMessage, completed: true });
              return;
            }

            // Parse JSON data
            let payload;
            try {
              payload = JSON.parse(event.data);
            } catch (parseError) {
              console.warn('Failed to parse SSE data:', event.data);
              return; // Skip malformed messages
            }

            // Handle token data
            if (payload.token) {
              if (!hasStarted) {
                hasStarted = true;
                this.emit(EVENTS.MESSAGE_RECEIVED, { 
                  type: 'start',
                  content: payload.token,
                  isStreaming: true
                });
              } else {
                this.emit(EVENTS.MESSAGE_RECEIVED, { 
                  type: 'token',
                  content: payload.token,
                  isStreaming: true
                });
              }
              assistantMessage += payload.token;
            }

            // Handle metadata (chunk info, sources, etc.)
            if (payload.chunks) {
              this.emit(EVENTS.MESSAGE_RECEIVED, {
                type: 'metadata',
                chunks: payload.chunks,
                isStreaming: true
              });
            }

          } catch (error) {
            console.error('Error processing stream message:', error);
          }
        };

        eventSource.onerror = (error) => {
          console.error('Stream error:', error);
          eventSource.close();
          this.emit(EVENTS.TYPING_STOP);
          
          if (!hasStarted) {
            // Connection failed before receiving any data
            this.handleNetworkError(error);
            reject(new Error(ERROR_MESSAGES.NETWORK_ERROR));
          } else {
            // Stream was interrupted but we have partial data
            resolve({ content: assistantMessage, completed: false });
          }
        };

        // Handle abort signal
        controller.signal.addEventListener('abort', () => {
          eventSource.close();
          this.emit(EVENTS.TYPING_STOP);
          reject(new Error('Request cancelled'));
        });
      });

    } catch (error) {
      console.error('Query error:', error);
      this.emit(EVENTS.ERROR, {
        message: error.message || ERROR_MESSAGES.API_ERROR,
        type: 'query',
        error
      });
      throw error;
    }
  }

  /**
   * Start scraping a website
   */
  async startScraping(siteName, baseUrl, description = '') {
    try {
      if (!Utils.isValidUrl(baseUrl)) {
        throw new Error(ERROR_MESSAGES.INVALID_URL);
      }

      const response = await fetch(`${CONFIG.API_BASE}${CONFIG.ENDPOINTS.SCRAPE}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          site_name: siteName,
          base_url: baseUrl,
          description: description
        }),
        signal: this.createAbortController().signal
      });

      if (!response.ok) {
        this.handleApiError(response, 'Failed to start scraping');
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data; // Should contain job_id

    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('Request cancelled');
      }
      
      if (error instanceof TypeError && error.message.includes('fetch')) {
        this.handleNetworkError(error);
      }
      
      throw error;
    }
  }

  /**
   * Check scraping status
   */
  async checkScrapingStatus(jobId) {
    try {
      const response = await fetch(
        `${CONFIG.API_BASE}${CONFIG.ENDPOINTS.SCRAPE_STATUS}/${jobId}`,
        { signal: this.createAbortController().signal }
      );

      if (!response.ok) {
        this.handleApiError(response, 'Failed to check scraping status');
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();

    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('Request cancelled');
      }
      
      if (error instanceof TypeError && error.message.includes('fetch')) {
        this.handleNetworkError(error);
      }
      
      throw error;
    }
  }

  /**
   * Cancel current request
   */
  cancel() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  /**
   * Check API health
   */
  async healthCheck() {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

      const response = await fetch(`${CONFIG.API_BASE}/health`, {
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        this.isConnected = true;
        this.emit(EVENTS.CONNECTION_STATUS, { connected: true });
        return true;
      } else {
        this.isConnected = false;
        this.emit(EVENTS.CONNECTION_STATUS, { connected: false });
        return false;
      }

    } catch (error) {
      this.isConnected = false;
      this.emit(EVENTS.CONNECTION_STATUS, { connected: false });
      return false;
    }
  }
}

// Create singleton instance
export const apiService = new ApiService();
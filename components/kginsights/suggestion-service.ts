/**
 * SuggestionService - Service for handling query suggestions
 * Manages requesting and processing suggestions from the WebSocket API
 */

import { WebSocketService } from "./websocket-service";

export interface SuggestionOptions {
  maxSuggestions?: number;
  debounceTime?: number;
}

export class SuggestionService {
  private debounceTimer: NodeJS.Timeout | null = null;
  private options: SuggestionOptions;
  private suggestionCallbacks: Map<string, (suggestions: string[]) => void> = new Map();
  
  constructor(
    private webSocketService: WebSocketService,
    options: SuggestionOptions = {}
  ) {
    this.options = {
      maxSuggestions: 10,
      debounceTime: 300,
      ...options
    };
    
    // Register handlers for suggestion responses
    this.webSocketService.registerHandler('suggestions', this.handleSuggestions.bind(this));
    this.webSocketService.registerHandler('suggestions_error', this.handleSuggestionsError.bind(this));
  }
  
  /**
   * Get query suggestions based on the current text and cursor position
   * @param query The current query text
   * @param cursorPosition The current cursor position
   * @param callback Function to call with the suggestions
   */
  getSuggestions(
    query: string, 
    cursorPosition: number,
    callback: (suggestions: string[]) => void
  ): void {
    // Clear any existing timer
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    
    // Set a new timer to debounce the request
    this.debounceTimer = setTimeout(() => {
      if (!query.trim()) {
        callback([]);
        return;
      }
      
      // Generate a unique request ID
      const requestId = `suggest-${Date.now()}`;
      
      // Store the callback for later
      this.suggestionCallbacks.set(requestId, callback);
      
      // Send the suggestion request
      this.webSocketService.sendMessage('suggest', {
        query,
        cursor_position: cursorPosition,
        request_id: requestId
      });
    }, this.options.debounceTime);
  }
  
  /**
   * Handle a suggestions response from the WebSocket
   * @param content The response content
   */
  private handleSuggestions(content: any): void {
    const { request_id, suggestions } = content;
    
    if (request_id && this.suggestionCallbacks.has(request_id)) {
      const callback = this.suggestionCallbacks.get(request_id);
      if (callback) {
        // Limit the number of suggestions
        const limitedSuggestions = (suggestions || []).slice(0, this.options.maxSuggestions);
        callback(limitedSuggestions);
      }
      
      // Clean up the callback
      this.suggestionCallbacks.delete(request_id);
    }
  }
  
  /**
   * Handle a suggestions error from the WebSocket
   * @param content The error content
   */
  private handleSuggestionsError(content: any): void {
    const { request_id, error } = content;
    
    if (request_id && this.suggestionCallbacks.has(request_id)) {
      const callback = this.suggestionCallbacks.get(request_id);
      if (callback) {
        console.error('Suggestion error:', error);
        callback([]);
      }
      
      // Clean up the callback
      this.suggestionCallbacks.delete(request_id);
    }
  }
  
  /**
   * Clean up the service
   */
  destroy(): void {
    // Unregister handlers
    this.webSocketService.unregisterHandler('suggestions', this.handleSuggestions.bind(this));
    this.webSocketService.unregisterHandler('suggestions_error', this.handleSuggestionsError.bind(this));
    
    // Clear any pending timers
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    
    // Clear all callbacks
    this.suggestionCallbacks.clear();
  }
}

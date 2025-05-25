/**
 * AutocompleteService - Service for handling autocomplete suggestions
 * Manages requesting and processing autocomplete suggestions from the WebSocket API
 */

import { WebSocketService } from "./websocket-service";

export interface AutocompleteSuggestion {
  text: string;
  description?: string | null;
}

export interface AutocompleteOptions {
  debounceTime?: number;
  maxSuggestions?: number;
}

export class AutocompleteService {
  private debounceTimer: NodeJS.Timeout | null = null;
  private options: AutocompleteOptions;
  private autocompleteCallbacks: Map<string, (suggestions: AutocompleteSuggestion[]) => void> = new Map();
  
  constructor(
    private webSocketService: WebSocketService,
    options: AutocompleteOptions = {}
  ) {
    this.options = {
      debounceTime: 150, // Shorter debounce time for autocomplete (more responsive)
      maxSuggestions: 5,
      ...options
    };
    
    // Register handlers for autocomplete responses
    this.webSocketService.registerHandler('autocomplete_suggestions', this.handleAutocompleteSuggestions.bind(this));
    this.webSocketService.registerHandler('autocomplete_error', this.handleAutocompleteError.bind(this));
  }
  
  /**
   * Get autocomplete suggestions based on the current text and cursor position
   * @param text The current input text
   * @param cursorPosition The current cursor position
   * @param callback Function to call with the suggestions
   */
  getAutocompleteSuggestions(
    text: string,
    cursorPosition: number,
    callback: (suggestions: AutocompleteSuggestion[]) => void
  ): void {
    // Clear any existing timer
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    
    // Set a new timer to debounce the request
    this.debounceTimer = setTimeout(() => {
      if (!text.trim()) {
        callback([]);
        return;
      }
      
      // Generate a unique request ID
      const requestId = `autocomplete-${Date.now()}`;
      
      // Store the callback for later
      this.autocompleteCallbacks.set(requestId, callback);
      
      // Send the autocomplete request
      this.webSocketService.sendMessage('autocomplete', {
        text,
        cursor_position: cursorPosition,
        request_id: requestId
      });
    }, this.options.debounceTime);
  }
  
  /**
   * Handle an autocomplete suggestions response from the WebSocket
   * @param content The response content
   */
  private handleAutocompleteSuggestions(content: any): void {
    const { request_id, suggestions } = content;
    
    if (request_id && this.autocompleteCallbacks.has(request_id)) {
      const callback = this.autocompleteCallbacks.get(request_id);
      if (callback) {
        // Format suggestions if needed
        const formattedSuggestions = (suggestions || []).map((suggestion: any) => {
          if (typeof suggestion === 'string') {
            return { text: suggestion, description: null };
          } else if (suggestion && typeof suggestion === 'object' && 'text' in suggestion) {
            return {
              text: suggestion.text,
              description: suggestion.description || null
            };
          }
          return { text: String(suggestion), description: null };
        });
        
        // Limit the number of suggestions
        const limitedSuggestions = formattedSuggestions.slice(0, this.options.maxSuggestions);
        callback(limitedSuggestions);
      }
      
      // Clean up the callback
      this.autocompleteCallbacks.delete(request_id);
    }
  }
  
  /**
   * Handle an autocomplete error from the WebSocket
   * @param content The error content
   */
  private handleAutocompleteError(content: any): void {
    const { request_id, error } = content;
    
    if (request_id && this.autocompleteCallbacks.has(request_id)) {
      const callback = this.autocompleteCallbacks.get(request_id);
      if (callback) {
        console.error('Autocomplete error:', error);
        callback([]);
      }
      
      // Clean up the callback
      this.autocompleteCallbacks.delete(request_id);
    }
  }
  
  /**
   * Clean up the service
   */
  destroy(): void {
    // Unregister handlers
    this.webSocketService.unregisterHandler('autocomplete_suggestions', this.handleAutocompleteSuggestions.bind(this));
    this.webSocketService.unregisterHandler('autocomplete_error', this.handleAutocompleteError.bind(this));
    
    // Clear any pending timers
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    
    // Clear all callbacks
    this.autocompleteCallbacks.clear();
  }
}

/**
 * Autocomplete Service for KG Insights
 * Provides autocomplete suggestions for Neo4j database nodes and relationships
 */

import { WebSocketService } from './websocket-service';

export interface AutocompleteSuggestion {
  text: string;
  description?: string | null;
  type?: string;
  offset?: number;
  errorLength?: number;
}

export interface AutocompleteServiceOptions {
  debounceTime?: number;
  maxSuggestions?: number;
  includeLinguistic?: boolean;
}

export type AutocompleteCallback = (suggestions: AutocompleteSuggestion[]) => void;

export class AutocompleteService {
  private webSocketService: WebSocketService;
  private debounceTime: number;
  private maxSuggestions: number;
  private includeLinguistic: boolean;
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private linguisticDebounceTimer: ReturnType<typeof setTimeout> | null = null;
  private callbacks: AutocompleteCallback[] = [];
  private currentSuggestions: AutocompleteSuggestion[] = [];

  constructor(webSocketService: WebSocketService, options: AutocompleteServiceOptions = {}) {
    this.webSocketService = webSocketService;
    this.debounceTime = options.debounceTime || 300;
    this.maxSuggestions = options.maxSuggestions || 5;
    this.includeLinguistic = options.includeLinguistic !== undefined ? options.includeLinguistic : true;

    // Register handler for autocomplete suggestions from WebSocket
    this.webSocketService.registerHandler('autocomplete_suggestions', this.handleAutocompleteSuggestions);
    
    // Register handler for linguistic suggestions from WebSocket
    this.webSocketService.registerHandler('linguistic_suggestions', this.handleLinguisticSuggestions);
  }

  /**
   * Get autocomplete suggestions for the given query
   * @param query The query text
   * @param cursorPosition The cursor position in the query
   */
  public getSuggestions(query: string, cursorPosition: number): void {
    // Clear any pending debounce timer
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    // Debounce the request
    this.debounceTimer = setTimeout(() => {
      // Only send request if WebSocket is connected
      if (this.webSocketService.isConnected()) {
        this.webSocketService.send({
          type: 'get_autocomplete_suggestions',
          query,
          cursorPosition,
          maxSuggestions: this.maxSuggestions,
          includeLinguistic: this.includeLinguistic
        });
      } else {
        console.warn('WebSocket is not connected, cannot get autocomplete suggestions');
        this.notifyCallbacks([]);
      }
    }, this.debounceTime);
  }

  /**
   * Register a callback for autocomplete suggestions
   * @param callback The callback function
   */
  public onSuggestions(callback: AutocompleteCallback): void {
    this.callbacks.push(callback);
    // Immediately call with current suggestions
    callback(this.currentSuggestions);
  }

  /**
   * Unregister a callback
   * @param callback The callback to remove
   */
  public offSuggestions(callback: AutocompleteCallback): void {
    this.callbacks = this.callbacks.filter(cb => cb !== callback);
  }

  /**
   * Get the current suggestions
   */
  public getCurrentSuggestions(): AutocompleteSuggestion[] {
    return this.currentSuggestions;
  }

  /**
   * Handle autocomplete suggestions from WebSocket
   */
  private handleAutocompleteSuggestions = (data: any): void => {
    console.log('Received autocomplete suggestions:', data);
    if (data && Array.isArray(data.suggestions)) {
      this.currentSuggestions = data.suggestions;
      console.log('Setting current suggestions:', this.currentSuggestions);
      this.notifyCallbacks(this.currentSuggestions);
    } else {
      console.warn('Received invalid autocomplete suggestions format:', data);
    }
  };

  /**
   * Notify all callbacks with the given suggestions
   * @param suggestions The suggestions to send
   */
  private notifyCallbacks(suggestions: AutocompleteSuggestion[]): void {
    this.callbacks.forEach(callback => callback(suggestions));
  }

  /**
   * Request linguistic checks for the given text
   * @param text The text to check for linguistic errors
   */
  public checkLinguistic(text: string): void {
    // Clear any pending linguistic debounce timer
    if (this.linguisticDebounceTimer) {
      clearTimeout(this.linguisticDebounceTimer);
    }

    // Debounce the request with a longer delay for linguistic checks
    this.linguisticDebounceTimer = setTimeout(() => {
      // Only send request if WebSocket is connected
      if (this.webSocketService.isConnected()) {
        this.webSocketService.send({
          type: 'check_linguistic',
          text
        });
      }
    }, this.debounceTime * 2); // Use longer debounce time for linguistic checks
  }

  /**
   * Handle linguistic suggestions from WebSocket
   */
  private handleLinguisticSuggestions = (data: any): void => {
    console.log('Received linguistic suggestions:', data);
    if (data && Array.isArray(data.suggestions)) {
      // Merge with current suggestions or handle separately as needed
      const linguisticSuggestions = data.suggestions;
      this.notifyCallbacks(linguisticSuggestions);
    }
  };

  /**
   * Clean up resources
   */
  public destroy(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    if (this.linguisticDebounceTimer) {
      clearTimeout(this.linguisticDebounceTimer);
    }
    
    // Unregister WebSocket handlers
    this.webSocketService.unregisterHandler('autocomplete_suggestions', this.handleAutocompleteSuggestions);
    this.webSocketService.unregisterHandler('linguistic_suggestions', this.handleLinguisticSuggestions);
    
    // Clear callbacks
    this.callbacks = [];
  }
}

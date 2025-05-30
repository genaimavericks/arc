/**
 * SuggestionService - Service for handling query suggestions and linguistic improvements
 * Manages requesting and processing suggestions from the WebSocket API
 */

import { WebSocketService } from "./websocket-service";

export interface SuggestionOptions {
  maxSuggestions?: number;
  debounceTime?: number;
  includeLinguisticSuggestions?: boolean;
  includeRelatedQueries?: boolean;
}

export interface LinguisticError {
  category: string;
  message: string;
  position: number;
  length: number;
  matched_text: string;
  suggestion: string;
  rule_id?: string;
}

export interface QueryQualityAnalysis {
  quality_score: number;
  error_count: number;
  error_categories: Record<string, number>;
  improvement_suggestions: string[];
}

export interface RelatedQuerySuggestions {
  broader: string[];
  narrower: string[];
}

export class SuggestionService {
  private debounceTimer: NodeJS.Timeout | null = null;
  private linguisticCheckTimer: NodeJS.Timeout | null = null;
  private relatedQueriesTimer: NodeJS.Timeout | null = null;
  private options: SuggestionOptions;
  private suggestionCallbacks: Map<string, (suggestions: string[]) => void> = new Map();
  private linguisticCallbacks: Map<string, (errors: LinguisticError[], analysis: QueryQualityAnalysis | null) => void> = new Map();
  private relatedQueryCallbacks: Map<string, (related: RelatedQuerySuggestions) => void> = new Map();
  
  constructor(
    private webSocketService: WebSocketService,
    options: SuggestionOptions = {}
  ) {
    this.options = {
      maxSuggestions: 10,
      debounceTime: 300,
      includeLinguisticSuggestions: true,
      includeRelatedQueries: true,
      ...options
    };
    
    // Register handlers for suggestion responses
    this.webSocketService.registerHandler('suggestions', this.handleSuggestions.bind(this));
    this.webSocketService.registerHandler('suggestions_error', this.handleSuggestionsError.bind(this));
    
    // Register handlers for related queries responses
    this.webSocketService.registerHandler('related_queries', this.handleRelatedQueries.bind(this));
    this.webSocketService.registerHandler('related_queries_error', this.handleRelatedQueriesError.bind(this));
  }
  
  /**
   * Get query suggestions based on the current text and cursor position
   * @param query The current query text
   * @param cursorPosition The current cursor position
   * @param callback Function to call with the suggestions
   */
  // Store a unified list of suggestions with metadata for prioritization
  private allSuggestions: Array<{
    text: string;
    type: 'query' | 'linguistic' | 'broader' | 'narrower';
    priority: number;
    timestamp: number;
  }> = [];
  private currentCallback: ((suggestions: string[]) => void) | null = null;
  
  // Method to update suggestions in the UI - optimized for performance
  private updateSuggestionsUI(): void {
    if (!this.currentCallback) {
      console.log('[SuggestionService] No callback available to update UI');
      return;
    }
    
    // Sort suggestions by priority (higher first) then by timestamp (newer first)
    const sortedSuggestions = [...this.allSuggestions].sort((a, b) => {
      if (a.priority !== b.priority) {
        return b.priority - a.priority; // Higher priority first
      }
      return b.timestamp - a.timestamp; // Newer first
    });
    
    // Format the suggestions for display
    const formattedSuggestions = sortedSuggestions.map(s => {
      // Linguistic suggestions (💡) and query suggestions are already formatted
      if (s.type === 'linguistic' || s.type === 'query') {
        return s.text;
      }
      // Format broader and narrower suggestions
      else if (s.type === 'broader') {
        return `↑ Broader: ${s.text}`;
      }
      else if (s.type === 'narrower') {
        return `↓ Narrower: ${s.text}`;
      }
      return s.text;
    });
    
    console.log('[SuggestionService] Combined suggestions:', formattedSuggestions);
    
    // Remove duplicates (keeping the first occurrence)
    const uniqueSuggestions = Array.from(new Set(formattedSuggestions));
    
    // Limit to max suggestions if needed
    const limitedSuggestions = this.options.maxSuggestions 
      ? uniqueSuggestions.slice(0, this.options.maxSuggestions)
      : uniqueSuggestions;
    
    // Call the callback with combined suggestions
    this.currentCallback(limitedSuggestions);
    console.log('[SuggestionService] Updated UI with suggestions');
  }
  
  // Add a suggestion to the unified list
  private addSuggestion(text: string, type: 'query' | 'linguistic' | 'broader' | 'narrower', priority: number = 1): void {
    // Add the suggestion with metadata
    this.allSuggestions.push({
      text,
      type,
      priority,
      timestamp: Date.now()
    });
    
    // Update the UI to show the new suggestion
    this.updateSuggestionsUI();
  }
  
  // Add multiple suggestions of the same type
  private addSuggestions(texts: string[], type: 'query' | 'linguistic' | 'broader' | 'narrower', priority: number = 1): void {
    // Skip empty arrays
    if (!texts || texts.length === 0) return;
    
    // Add timestamp once for all suggestions in batch
    const timestamp = Date.now();
    
    // Add all suggestions with metadata
    const newSuggestions = texts.map(text => ({
      text,
      type,
      priority,
      timestamp
    }));
    
    this.allSuggestions.push(...newSuggestions);
    
    // Update the UI to show the new suggestions
    this.updateSuggestionsUI();
  }
  
  // Clear suggestions of a specific type or all suggestions
  private clearSuggestions(type?: 'query' | 'linguistic' | 'broader' | 'narrower'): void {
    if (type) {
      // Filter out suggestions of the specified type
      this.allSuggestions = this.allSuggestions.filter(s => s.type !== type);
    } else {
      // Clear all suggestions
      this.allSuggestions = [];
    }
    
    // Update the UI
    this.updateSuggestionsUI();
  }
  
  getSuggestions(
    query: string, 
    cursorPosition: number,
    callback: (suggestions: string[]) => void
  ): void {
    console.log('[SuggestionService] getSuggestions called with:', { query, cursorPosition });
    
    // Save the callback for later use
    this.currentCallback = callback;
    
    // Clear previous suggestions but keep linguistic ones for a while
    this.clearSuggestions('query');
    this.clearSuggestions('broader');
    this.clearSuggestions('narrower');
    
    // Keep linguistic suggestions for a longer time but eventually expire them
    // This ensures they don't linger forever if they become irrelevant
    const LINGUISTIC_EXPIRY_MS = 10000; // 10 seconds
    const now = Date.now();
    this.allSuggestions = this.allSuggestions.filter(s => {
      if (s.type === 'linguistic') {
        return (now - s.timestamp) < LINGUISTIC_EXPIRY_MS;
      }
      return true;
    });
    
    // Also trigger linguistic checks to add language suggestions
    if (this.options.includeLinguisticSuggestions) {
      console.log('[SuggestionService] Linguistic suggestions enabled, checking for errors');
      
      // Check for linguistic errors and add them to suggestions
      this.checkLinguisticErrors(query, cursorPosition, (errors) => {
        console.log('[SuggestionService] Got linguistic errors:', errors);
        
        if (errors && errors.length > 0) {
          // Convert the errors to suggestions with higher priority
          const linguisticSuggestions = errors.map(error => {
            return `💡 ${error.suggestion} (${error.message})`;
          });
          
          console.log('[SuggestionService] Created linguistic suggestions:', linguisticSuggestions);
          
          // Add linguistic suggestions with higher priority (3)
          this.addSuggestions(linguisticSuggestions, 'linguistic', 3);
        } else {
          console.log('[SuggestionService] No linguistic errors found');
        }
      });
    } else {
      console.log('[SuggestionService] Linguistic suggestions disabled');
    }
    
    // Get related queries to help with data exploration
    if (this.options.includeRelatedQueries && query.trim().length > 3) {
      console.log('[SuggestionService] Related queries enabled, requesting suggestions');
      
      // Request related queries for broader and narrower analysis
      this.getRelatedQueries(query, (related) => {
        console.log('[SuggestionService] Got related queries:', related);
        
        if (related) {
          // Add broader suggestions with medium priority (2)
          this.addSuggestions(related.broader.slice(0, 2), 'broader', 2);
          
          // Add narrower suggestions with medium priority (2)
          this.addSuggestions(related.narrower.slice(0, 2), 'narrower', 2);
        } else {
          console.log('[SuggestionService] No related queries found');
        }
      });
    } else {
      console.log('[SuggestionService] Related queries disabled or query too short');
    }
    // Clear any existing timer
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    
    // Debounce the suggestion request
    this.debounceTimer = setTimeout(() => {
      // Generate a unique ID for this request
      const requestId = `suggestions-${Date.now()}`;
      
      // Store the callback for when we get a response
      this.suggestionCallbacks.set(requestId, (suggestions) => {
        // Add query suggestions with normal priority (1)
        this.addSuggestions(suggestions, 'query', 1);
        console.log('[SuggestionService] Added query suggestions:', suggestions);
      });
      
      // Send the request to the WebSocket server
      this.webSocketService.sendMessage('suggestions', {
        query,
        cursor_position: cursorPosition,
        request_id: requestId
      });
      
      // The server sends regular suggestions through this event
      // Using existing handlers that match the server implementation
      this.webSocketService.registerHandler('suggestions_results', this.handleSuggestions.bind(this));
      this.webSocketService.registerHandler('suggestions_error', this.handleSuggestionsError.bind(this));
      
      // Set a timeout to clean up if we don't get a response
      setTimeout(() => {
        if (this.suggestionCallbacks.has(requestId)) {
          const cb = this.suggestionCallbacks.get(requestId);
          this.suggestionCallbacks.delete(requestId);
          if (cb) {
            cb([]);
          }
        }
      }, 5000); // 5 second timeout
    }, this.options.debounceTime || 300);
  }
  
  /**
   * Handle a suggestions response from the WebSocket
   * @param content The response content
   */
  private handleSuggestions(content: any): void {
    const { request_id, suggestions, suggestion_type } = content;
    
    console.log(`[SuggestionService] Received suggestions with type: ${suggestion_type || 'query'}`);
    
    if (request_id && this.suggestionCallbacks.has(request_id)) {
      const callback = this.suggestionCallbacks.get(request_id);
      if (callback) {
        // Process suggestions based on type
        let allSuggestions: string[] = [];
        if (suggestions && Array.isArray(suggestions)) {
          allSuggestions = suggestions;
        }
        
        // Pass suggestions to the callback
        callback(allSuggestions);
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
    console.error(`[SuggestionService] Error getting suggestions: ${error}`);
    
    if (request_id && this.suggestionCallbacks.has(request_id)) {
      const callback = this.suggestionCallbacks.get(request_id);
      if (callback) {
        callback([]);
      }
      
      // Clean up the callback
      this.suggestionCallbacks.delete(request_id);
    }
  }
  
  /**
   * Get related queries to help broaden or narrow analysis
   * @param query The current query text
   * @param callback Function to call with the related queries
   */
  getRelatedQueries(
    query: string,
    callback: (related: RelatedQuerySuggestions) => void
  ): void {
    console.log('[SuggestionService] getRelatedQueries called with:', { query });
    
    // Clear any existing timer
    if (this.relatedQueriesTimer) {
      clearTimeout(this.relatedQueriesTimer);
    }
    
    // Debounce the related queries request
    this.relatedQueriesTimer = setTimeout(() => {
      // Generate a unique ID for this request
      const requestId = `related-${Date.now()}`;
      
      // Store the callback for when we get a response
      this.relatedQueryCallbacks.set(requestId, callback);
      
      // Send the request to the WebSocket server
      this.webSocketService.sendMessage('related_queries', {
        query,
        request_id: requestId
      });
      
      // Set a timeout to clean up if we don't get a response
      setTimeout(() => {
        if (this.relatedQueryCallbacks.has(requestId)) {
          const cb = this.relatedQueryCallbacks.get(requestId);
          this.relatedQueryCallbacks.delete(requestId);
          if (cb) {
            cb({ broader: [], narrower: [] });
          }
        }
      }, 5000); // 5 second timeout
    }, this.options.debounceTime || 300);
  }
  
  /**
   * Handle a related queries response from the WebSocket
   * @param content The response content
   */
  private handleRelatedQueries(content: any): void {
    const { request_id, broader, narrower } = content;
    
    if (request_id && this.relatedQueryCallbacks.has(request_id)) {
      const callback = this.relatedQueryCallbacks.get(request_id);
      if (callback) {
        // Provide the broader and narrower suggestions
        callback({
          broader: Array.isArray(broader) ? broader : [],
          narrower: Array.isArray(narrower) ? narrower : []
        });
      }
      
      // Clean up the callback
      this.relatedQueryCallbacks.delete(requestId);
    }
  }
  
  /**
   * Handle a related queries error from the WebSocket
   * @param content The error content
   */
  private handleRelatedQueriesError(content: any): void {
    const { request_id, error } = content;
    console.error(`[SuggestionService] Error getting related queries: ${error}`);
    
    if (request_id && this.relatedQueryCallbacks.has(request_id)) {
      const callback = this.relatedQueryCallbacks.get(request_id);
      if (callback) {
        callback({ broader: [], narrower: [] });
      }
      
      // Clean up the callback
      this.relatedQueryCallbacks.delete(requestId);
    }
  }
  
  /**
   * Clean up the service
   */
  /**
   * Check for linguistic errors in the query text using the WebSocket service
   * @param query The query text to check
   * @param cursorPosition The current cursor position in the text
   * @param callback Function to call with the results
   */
  checkLinguisticErrors(
    query: string,
    cursorPosition: number,
    callback: (errors: LinguisticError[], analysis?: QueryQualityAnalysis | null) => void
  ): void {
    console.log('[SuggestionService] checkLinguisticErrors called with:', { query, cursorPosition });
    
    if (!query || query.trim() === '') {
      console.log('[SuggestionService] Empty query, returning empty results');
      callback([], null);
      return;
    }
    
    // Clear any existing timer for linguistic checks
    if (this.linguisticCheckTimer) {
      clearTimeout(this.linguisticCheckTimer);
      console.log('[SuggestionService] Cleared existing linguistic check timer');
    }
    
    // Debounce the linguistic check request with shorter delay for faster feedback
    this.linguisticCheckTimer = setTimeout(() => {
      // Generate a unique ID for this request
      const requestId = `linguistic-${Date.now()}`;
      
      // Store the callback for when we get a response
      this.linguisticCallbacks.set(requestId, callback);
      
      // Send the request to the WebSocket server - simplified for performance
      try {
        this.webSocketService.sendMessage('linguistic_check', {
          query,
          cursor_position: cursorPosition,
          request_id: requestId
        });
      } catch (error) {
        callback([], null);
        return;
      }
      
      // Register handler for the response if not already registered
      this.webSocketService.registerHandler('linguistic_check_results', this.handleLinguisticCheckResults.bind(this));
      this.webSocketService.registerHandler('linguistic_check_error', this.handleLinguisticCheckError.bind(this));
      
      // Use a shorter timeout for better performance
      setTimeout(() => {
        if (this.linguisticCallbacks.has(requestId)) {
          const cb = this.linguisticCallbacks.get(requestId);
          this.linguisticCallbacks.delete(requestId);
          if (cb) {
            cb([], null);
          }
        }
      }, 3000); // 3 second timeout is sufficient and improves responsiveness
    }, 150); // Reduced debounce time for more responsive suggestions
  }
  
  /**
   * Handle linguistic check results from the WebSocket service
   */
  private handleLinguisticCheckResults(response: any): void {
    console.log('[SuggestionService] Received linguistic_check_results:', response);
    
    // Extract errors directly - for direct processing of received messages
    const errors = response.errors || response.content?.errors;
    if (errors && errors.length > 0) {
      // Convert directly to suggestions - this ensures they appear immediately
      this.convertLinguisticErrorsToSuggestions(errors);
    }
    
    // Extract the request ID from the response
    const request_id = response.request_id || response.content?.request_id;
    console.log('[SuggestionService] Processing response for request ID:', request_id);
    
    // Handle case where request ID isn't found
    if (!request_id) {
      console.log('[SuggestionService] No request ID in response');
      // Fall back to using most recent callback if available
      if (this.linguisticCallbacks.size > 0) {
        const lastCallback = Array.from(this.linguisticCallbacks.entries())[this.linguisticCallbacks.size - 1];
        console.log('[SuggestionService] Using most recent callback as fallback');
        this.processLinguisticResults(lastCallback[0], response);
      }
      return;
    }
    
    // Check if we have a callback for this request ID
    if (!this.linguisticCallbacks.has(request_id)) {
      console.log('[SuggestionService] No matching callback found for request ID:', request_id);
      return;
    }
    
    // Process the results using a helper method
    this.processLinguisticResults(request_id, response);
  }
  
  /**
   * Process linguistic check results and call the appropriate callback
   * Optimized for performance with less logging
   */
  private processLinguisticResults(requestId: string, response: any): void {
    // Get the callback for this request
    const callback = this.linguisticCallbacks.get(requestId)!;
    this.linguisticCallbacks.delete(requestId);
    
    // Extract the errors and analysis
    const errors = response.errors || response.content?.errors || [];
    const analysis = response.quality_analysis || response.content?.quality_analysis || null;
    
    // Call the callback
    callback(errors, analysis);
    
    // Also convert errors to suggestions and add them to regular suggestions
    if (errors.length > 0 && this.options.includeLinguisticSuggestions) {
      this.convertLinguisticErrorsToSuggestions(errors);
    }
  }
  
  /**
   * Handle linguistic check errors from the WebSocket service
   */
  private handleLinguisticCheckError(response: any): void {
    console.log('[SuggestionService] Received linguistic_check_error:', response);
    
    // Extract the request ID from the response
    const request_id = response.request_id || response.content?.request_id;
    console.log('[SuggestionService] Processing error for request ID:', request_id);
    
    // Handle case where request ID isn't found
    if (!request_id) {
      console.log('[SuggestionService] No request ID in error response');
      // Fall back to using most recent callback if available
      if (this.linguisticCallbacks.size > 0) {
        const lastCallback = Array.from(this.linguisticCallbacks.entries())[this.linguisticCallbacks.size - 1];
        console.log('[SuggestionService] Using most recent callback as fallback for error');
        
        // Get the callback and remove it
        const callback = this.linguisticCallbacks.get(lastCallback[0])!;
        this.linguisticCallbacks.delete(lastCallback[0]);
        
        // Call the callback with empty results
        console.log('[SuggestionService] Calling callback with empty results due to error');
        callback([], null);
      }
      return;
    }
    
    // Check if we have a callback for this request ID
    if (!this.linguisticCallbacks.has(request_id)) {
      console.log('[SuggestionService] No matching callback found for error with request ID:', request_id);
      return;
    }
    
    console.log('[SuggestionService] Found callback for error with request ID:', request_id);
    
    // Get the callback for this request
    const callback = this.linguisticCallbacks.get(requestId)!;
    this.linguisticCallbacks.delete(requestId);
    
    // Call the callback with empty results
    console.log('[SuggestionService] Calling callback with empty results due to error');
    callback([], null);
  }
  
  /**
   * Convert linguistic errors to regular suggestions and add them to the suggestions list
   * This method adds the linguistic suggestions directly to the current suggestions list
   * and updates the UI through the current callback
   * Optimized for performance
   */
  private convertLinguisticErrorsToSuggestions(errors: LinguisticError[]): void {
    if (!errors || errors.length === 0) {
      return;
    }
    
    // Convert errors to suggestions
    const linguisticSuggestions = errors.map(error => {
      // Create a suggestion with the corrected text and explanation
      return `💡 ${error.suggestion} (${error.message})`;
    });
    
    console.log('[SuggestionService] Created linguistic suggestions:', linguisticSuggestions);
    
    // Add linguistic suggestions with high priority
    this.addSuggestions(linguisticSuggestions, 'linguistic', 3);
    
    console.log('[SuggestionService] Updated UI with combined suggestions');
  }
  
  destroy(): void {
    // Unregister handlers
    this.webSocketService.unregisterHandler('suggestions', this.handleSuggestions.bind(this));
    this.webSocketService.unregisterHandler('suggestions_error', this.handleSuggestionsError.bind(this));
    this.webSocketService.unregisterHandler('linguistic_check_results', this.handleLinguisticCheckResults.bind(this));
    this.webSocketService.unregisterHandler('linguistic_check_error', this.handleLinguisticCheckError.bind(this));
    
    // Clear any pending timers
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    
    if (this.linguisticCheckTimer) {
      clearTimeout(this.linguisticCheckTimer);
    }
    
    // Clear all callbacks
    this.suggestionCallbacks.clear();
    this.linguisticCallbacks.clear();
  }
}

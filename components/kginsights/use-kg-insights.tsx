/**
 * useKGInsights - React hook for using KG Insights services
 * Provides a unified interface for WebSocket, Suggestions, and Autocomplete services
 */

import { useState, useEffect, useRef } from 'react';
import { WebSocketService, ConnectionStatus } from './websocket-service';
import { SuggestionService, SuggestionOptions, LinguisticError, QueryQualityAnalysis } from './suggestion-service';
import { AutocompleteService, AutocompleteSuggestion, AutocompleteOptions } from './autocomplete-service';

export interface KGInsightsHookOptions {
  baseUrl?: string;
  autoReconnect?: boolean;
  suggestionOptions?: SuggestionOptions;
  autocompleteOptions?: AutocompleteOptions;
}

export interface KGInsightsHookResult {
  connected: boolean;
  connectionStatus: ConnectionStatus;
  loading: boolean;
  error: string | null;
  suggestions: string[];
  autocompleteSuggestions: AutocompleteSuggestion[];
  linguisticErrors: LinguisticError[];
  queryQualityAnalysis: QueryQualityAnalysis | null;
  getSuggestions: (query: string, cursorPosition: number) => void;
  getAutocompleteSuggestions: (text: string, cursorPosition: number) => void;
  checkLinguisticErrors: (query: string, cursorPosition: number) => void;
  sendQuery: (query: string) => void;
  validateQuery: (query: string) => void;
  disconnect: () => void;
  registerQueryResultHandler: (handler: (content: any) => void) => void;
  unregisterQueryResultHandler: (handler: (content: any) => void) => void;
}

/**
 * Hook for using KG Insights services in React components
 * @param schemaId The schema ID to connect to
 * @param token Authentication token
 * @param options Configuration options
 * @returns Functions and state for interacting with KG Insights
 */
export function useKGInsights(
  schemaId: string,
  token: string,
  options: KGInsightsHookOptions = {}
): KGInsightsHookResult {
  // Service refs
  const webSocketServiceRef = useRef<WebSocketService | null>(null);
  const suggestionServiceRef = useRef<SuggestionService | null>(null);
  const autocompleteServiceRef = useRef<AutocompleteService | null>(null);
  
  // State
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState<AutocompleteSuggestion[]>([]);
  const [linguisticErrors, setLinguisticErrors] = useState<LinguisticError[]>([]);
  const [queryQualityAnalysis, setQueryQualityAnalysis] = useState<QueryQualityAnalysis | null>(null);
  
  // Initialize services
  useEffect(() => {
    const baseUrl = options.baseUrl || window.location.origin;
    
    // Create service instances if they don't exist
    if (!webSocketServiceRef.current) {
      webSocketServiceRef.current = new WebSocketService(baseUrl, options.autoReconnect ?? true);
    }
    
    if (!suggestionServiceRef.current && webSocketServiceRef.current) {
      suggestionServiceRef.current = new SuggestionService(
        webSocketServiceRef.current,
        options.suggestionOptions
      );
    }
    
    if (!autocompleteServiceRef.current && webSocketServiceRef.current) {
      autocompleteServiceRef.current = new AutocompleteService(
        webSocketServiceRef.current,
        options.autocompleteOptions
      );
    }
    
    // Connect to WebSocket
    const connectWebSocket = async () => {
      if (!webSocketServiceRef.current) return;
      
      setLoading(true);
      setError(null);
      
      try {
        await webSocketServiceRef.current.connect(schemaId, token);
        setConnectionStatus('connected');
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : String(err);
        setError(`Failed to connect: ${errorMessage}`);
        setConnectionStatus('disconnected');
      } finally {
        setLoading(false);
      }
    };
    
    // Connect
    connectWebSocket();
    
    // Polling to update connection status
    const statusInterval = setInterval(() => {
      if (webSocketServiceRef.current) {
        setConnectionStatus(webSocketServiceRef.current.getConnectionStatus());
      }
    }, 1000);
    
    // Cleanup on unmount
    return () => {
      clearInterval(statusInterval);
      
      if (suggestionServiceRef.current) {
        suggestionServiceRef.current.destroy();
      }
      
      if (autocompleteServiceRef.current) {
        autocompleteServiceRef.current.destroy();
      }
      
      if (webSocketServiceRef.current) {
        webSocketServiceRef.current.disconnect();
      }
    };
  }, [schemaId, token, options.baseUrl, options.autoReconnect]);
  
  // Function to get suggestions
  const getSuggestions = (query: string, cursorPosition: number) => {
    if (!suggestionServiceRef.current) return;
    
    suggestionServiceRef.current.getSuggestions(
      query,
      cursorPosition,
      (newSuggestions) => {
        setSuggestions(newSuggestions);
      }
    );
  };
  
  // Function to get autocomplete suggestions
  const getAutocompleteSuggestions = (text: string, cursorPosition: number) => {
    if (!autocompleteServiceRef.current) return;
    
    autocompleteServiceRef.current.getAutocompleteSuggestions(
      text,
      cursorPosition,
      (newSuggestions) => {
        setAutocompleteSuggestions(newSuggestions);
      }
    );
  };
  
  // Function to check for linguistic errors
  const checkLinguisticErrors = (query: string, cursorPosition: number) => {
    if (!suggestionServiceRef.current) return;
    
    suggestionServiceRef.current.checkLinguisticErrors(
      query,
      cursorPosition,
      (errors, analysis) => {
        setLinguisticErrors(errors || []);
        setQueryQualityAnalysis(analysis || null);
      }
    );
  };
  
  // Function to send a query
  const sendQuery = (query: string) => {
    if (!webSocketServiceRef.current) return;
    
    webSocketServiceRef.current.sendMessage('query', {
      query,
      query_id: `query-${Date.now()}`
    });
  };
  
  // Function to register a query result handler
  const registerQueryResultHandler = (handler: (content: any) => void) => {
    if (!webSocketServiceRef.current) return;
    webSocketServiceRef.current.registerHandler('query_result', handler);
  };
  
  // Function to unregister a query result handler
  const unregisterQueryResultHandler = (handler: (content: any) => void) => {
    if (!webSocketServiceRef.current) return;
    webSocketServiceRef.current.unregisterHandler('query_result', handler);
  };
  
  // Function to validate a query
  const validateQuery = (query: string) => {
    if (!webSocketServiceRef.current) return;
    
    webSocketServiceRef.current.sendMessage('validate', {
      query,
      request_id: `validate-${Date.now()}`
    });
  };
  
  // Function to disconnect
  const disconnect = () => {
    if (!webSocketServiceRef.current) return;
    
    webSocketServiceRef.current.disconnect();
    setConnectionStatus('disconnected');
  };
  
  return {
    connected: connectionStatus === 'connected',
    connectionStatus,
    loading,
    error,
    suggestions,
    autocompleteSuggestions,
    linguisticErrors,
    queryQualityAnalysis,
    getSuggestions,
    getAutocompleteSuggestions,
    checkLinguisticErrors,
    sendQuery,
    validateQuery,
    disconnect,
    registerQueryResultHandler,
    unregisterQueryResultHandler
  };
}

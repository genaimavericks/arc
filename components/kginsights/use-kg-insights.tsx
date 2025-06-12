/**
 * useKGInsights - React hook for using KG Insights services
 * Provides a simplified interface for Neo4j database node and relationship labels
 * using WebSocket and Autocomplete services
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { WebSocketService, ConnectionStatus } from './websocket-service';
import { AutocompleteService, AutocompleteSuggestion } from './autocomplete-service';

// Re-export AutocompleteSuggestion for consumers of this hook
export type { AutocompleteSuggestion };

export interface KGInsightsHookOptions {
  baseUrl?: string;
  autoReconnect?: boolean;
  autocompleteOptions?: {
    maxSuggestions?: number;
    debounceTime?: number;
  };
}

export interface KGInsightsHookResult {
  connected: boolean;
  connectionStatus: string;
  loading: boolean;
  error: string | null;
  suggestions: string[];
  autocompleteSuggestions: AutocompleteSuggestion[];
  getAutocompleteSuggestions: (text: string, cursorPosition: number) => void;
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
  // State
  const [connectionStatus, setConnectionStatus] = useState<string>(ConnectionStatus.DISCONNECTED);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions] = useState<string[]>([]);
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState<AutocompleteSuggestion[]>([]);
  
  // Refs to store service instances
  const webSocketServiceRef = useRef<WebSocketService | null>(null);
  const autocompleteServiceRef = useRef<AutocompleteService | null>(null);
  
  // Initialize WebSocket service
  useEffect(() => {
    // Skip if no schema ID or token
    if (!schemaId || !token) {
      setError('Schema ID and token are required');
      return;
    }

    const baseUrl = options.baseUrl || window.location.origin;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${baseUrl.replace(/^https?:\/\//, '')}/api/kginsights/${schemaId}/ws?token=${token}`;
    
    // Create WebSocket service
    const webSocketService = new WebSocketService({
      url: wsUrl,
      autoReconnect: options.autoReconnect !== false,
    });
    
    // Create Autocomplete service
    const autocompleteService = new AutocompleteService(webSocketService, {
      debounceTime: options.autocompleteOptions?.debounceTime,
      maxSuggestions: options.autocompleteOptions?.maxSuggestions,
    });
    
    // Store services in refs
    webSocketServiceRef.current = webSocketService;
    autocompleteServiceRef.current = autocompleteService;
    
    // Handle connection status changes
    webSocketService.onStatusChange((status) => {
      setConnectionStatus(status);
    });
    
    // Handle autocomplete suggestions
    autocompleteService.onSuggestions((suggestions) => {
      setAutocompleteSuggestions(suggestions);
    });
    
    // Connect to WebSocket
    setLoading(true);
    webSocketService.connect()
      .then(() => {
        setLoading(false);
        setError(null);
      })
      .catch((err) => {
        setLoading(false);
        setError(`Failed to connect: ${err.message}`);
      });
    
    // Cleanup on unmount
    return () => {
      if (autocompleteServiceRef.current) {
        autocompleteServiceRef.current.destroy();
      }
      if (webSocketServiceRef.current) {
        webSocketServiceRef.current.disconnect();
      }
    };
  }, [schemaId, token, options.baseUrl, options.autoReconnect, options.autocompleteOptions?.debounceTime, options.autocompleteOptions?.maxSuggestions]);
  
  // Function to get autocomplete suggestions for Neo4j nodes and relationships
  const getAutocompleteSuggestions = useCallback((text: string, cursorPosition: number) => {
    if (autocompleteServiceRef.current) {
      autocompleteServiceRef.current.getSuggestions(text, cursorPosition);
    }
  }, []);
  
  // Function to send a query via WebSocket
  const sendQuery = useCallback((query: string) => {
    if (webSocketServiceRef.current && webSocketServiceRef.current.isConnected()) {
      webSocketServiceRef.current.send({
        type: 'query',
        query
      });
    } else {
      setError('WebSocket is not connected');
    }
  }, []);
  
  // Function to register a handler for query results
  const registerQueryResultHandler = useCallback((handler: (content: any) => void) => {
    if (webSocketServiceRef.current) {
      webSocketServiceRef.current.registerHandler('query_result', handler);
    }
  }, []);
  
  // Function to unregister a handler for query results
  const unregisterQueryResultHandler = useCallback((handler: (content: any) => void) => {
    if (webSocketServiceRef.current) {
      webSocketServiceRef.current.unregisterHandler('query_result', handler);
    }
  }, []);
  
  // Function to validate a query
  const validateQuery = useCallback((query: string) => {
    if (webSocketServiceRef.current && webSocketServiceRef.current.isConnected()) {
      webSocketServiceRef.current.send({
        type: 'validate_query',
        query
      });
    } else {
      setError('WebSocket is not connected');
    }
  }, []);
  
  // Function to disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (webSocketServiceRef.current) {
      webSocketServiceRef.current.disconnect();
    }
  }, []);
  
  return {
    connected: connectionStatus === ConnectionStatus.CONNECTED,
    connectionStatus,
    loading,
    error,
    suggestions,
    autocompleteSuggestions,
    getAutocompleteSuggestions,
    sendQuery,
    validateQuery,
    disconnect,
    registerQueryResultHandler,
    unregisterQueryResultHandler
  };
}

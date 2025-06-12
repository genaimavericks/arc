"use client"

import React, { useState, useRef, useEffect } from 'react';
import { useKGInsights, AutocompleteSuggestion } from './use-kg-insights';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Send, AlertTriangle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ExampleChatComponentProps {
  schemaId: string;
  token: string;
}

/**
 * Example chat component that uses the KG Insights services
 * This demonstrates how to integrate the WebSocket, Suggestions, and Autocomplete services
 */
export function ExampleChatComponent({ schemaId, token }: ExampleChatComponentProps) {
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<{role: 'user' | 'assistant', content: string}[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Use our custom hook
  const {
    connected,
    connectionStatus,
    loading,
    error,
    suggestions,
    autocompleteSuggestions,
    getAutocompleteSuggestions,
    sendQuery,
    registerQueryResultHandler,
    unregisterQueryResultHandler
  } = useKGInsights(schemaId, token, {
    // Configure the services
    baseUrl: window.location.origin,
    autoReconnect: true,
    autocompleteOptions: {
      maxSuggestions: 5,
      debounceTime: 150
    }
  });
  
  // Set up WebSocket message handler for query responses
  useEffect(() => {
    // This would normally be handled within the useKGInsights hook
    // But for this example, we're showing how you could add custom handlers
    
    const handleQueryResponse = (content: any) => {
      const { result } = content;
      if (result) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: result
        }]);
      }
    };
    
    // In a real implementation, you would register this handler with the WebSocketService
    // For example:
    // webSocketService.registerHandler('query_result', handleQueryResponse);
    
    return () => {
      // And unregister it when done:
      // webSocketService.unregisterHandler('query_result', handleQueryResponse);
    };
  }, []);
  
  // Handle input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInputValue(value);
    
    // Get cursor position
    const cursorPosition = e.target.selectionStart || value.length;
    
    // Get suggestions if the input is not empty
    if (value.trim()) {
      getAutocompleteSuggestions(value, cursorPosition);
      setShowSuggestions(true);
      setShowAutocomplete(true);
    } else {
      setShowSuggestions(false);
      setShowAutocomplete(false);
    }
  };
  
  // Handle sending a message
  const handleSendMessage = () => {
    if (!inputValue.trim() || !connected) return;
    
    // Add user message to the chat
    setMessages(prev => [...prev, {
      role: 'user',
      content: inputValue
    }]);
    
    // Send the query
    sendQuery(inputValue);
    
    // Clear the input
    setInputValue('');
    setShowSuggestions(false);
    setShowAutocomplete(false);
  };
  
  // Handle selecting a suggestion
  const handleSelectSuggestion = (suggestion: string) => {
    setInputValue(suggestion);
    setShowSuggestions(false);
    setShowAutocomplete(false);
    inputRef.current?.focus();
  };
  
  // Handle selecting an autocomplete suggestion
  const handleSelectAutocompleteSuggestion = (suggestion: AutocompleteSuggestion) => {
    setInputValue(suggestion.text);
    setShowSuggestions(false);
    setShowAutocomplete(false);
    inputRef.current?.focus();
  };
  
  // Handle keyboard events
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      setShowAutocomplete(false);
    }
  };
  
  return (
    <div className="flex flex-col h-full">
      {/* Connection status */}
      <div className="px-4 py-2 bg-secondary">
        <div className="flex items-center">
          <div 
            className={cn(
              "w-2 h-2 rounded-full mr-2",
              connected ? "bg-green-500" : "bg-red-500"
            )}
          />
          <span className="text-sm">
            {loading ? 'Connecting...' : (connected ? 'Connected' : 'Disconnected')}
          </span>
        </div>
      </div>
      
      {/* Error message */}
      {error && (
        <div className="px-4 py-2 bg-destructive text-destructive-foreground">
          <div className="flex items-center">
            <AlertTriangle className="mr-2 h-4 w-4" />
            <span className="text-sm">{error}</span>
          </div>
        </div>
      )}
      
      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div 
            key={index}
            className={cn(
              "p-3 rounded-lg max-w-[80%]",
              message.role === 'user' 
                ? "bg-primary text-primary-foreground ml-auto" 
                : "bg-muted mr-auto"
            )}
          >
            {message.content}
          </div>
        ))}
      </div>
      
      {/* Suggestions */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="border border-border rounded-md mx-4 mb-2 overflow-hidden">
          <div className="p-2 bg-secondary text-secondary-foreground text-sm font-medium">
            Suggested Queries
          </div>
          <div className="divide-y divide-border">
            {suggestions.map((suggestion, index) => (
              <div 
                key={index}
                className="p-2 hover:bg-accent cursor-pointer text-sm"
                onClick={() => handleSelectSuggestion(suggestion)}
              >
                {suggestion}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Autocomplete suggestions */}
      {showAutocomplete && autocompleteSuggestions.length > 0 && (
        <div className="border border-border rounded-md mx-4 mb-2 overflow-hidden">
          <div className="p-2 bg-secondary text-secondary-foreground text-sm font-medium">
            Autocomplete
          </div>
          <div className="divide-y divide-border">
            {autocompleteSuggestions.map((suggestion, index) => (
              <div 
                key={index}
                className="p-2 hover:bg-accent cursor-pointer"
                onClick={() => handleSelectAutocompleteSuggestion(suggestion)}
              >
                <div className="font-medium">{suggestion.text}</div>
                {suggestion.description && (
                  <div className="text-xs text-muted-foreground">{suggestion.description}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Input */}
      <div className="p-4 border-t border-border">
        <div className="flex space-x-2">
          <Input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Type your query..."
            disabled={!connected || loading}
            className="flex-1"
          />
          <Button
            onClick={handleSendMessage}
            disabled={!connected || loading || !inputValue.trim()}
            size="icon"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}

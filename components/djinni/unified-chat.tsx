"use client"

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Loader2, Trash2, Bot, User, Sparkles, Network, ChevronLeft, ChevronRight } from 'lucide-react'
import { motion } from "framer-motion"
import { useKGInsights, AutocompleteSuggestion } from '../kginsights/use-kg-insights'
import { KGInsightsSidebar } from './kg-insights-sidebar'
import { useDjinniStore } from '@/lib/djinni/store'
import MessageVisualization from './message-visualization'
import { getApiBaseUrl } from '@/lib/config'
import { fetchWithAuth } from '@/lib/auth-utils'

// Helper function to format timestamp
const formatTime = (date: Date) => {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// PredefinedQuery interface
export interface PredefinedQuery {
  id: string
  query: string
  category: string
}

// HistoryItem interface
export interface HistoryItem {
  id: string
  query: string
  result: string
  timestamp: Date
}

// Unified message type
export interface UnifiedChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  timestamp: Date
  source: "kginsights" | "astro" | "system" | "factory_astro" | "churn_astro"
  metadata?: {
    type?: "text" | "visualization"
    data?: any
  }
  predictionData?: any;
  userQuery?: string;
}

export function UnifiedChatInterface() {
  const [messages, setMessages] = useState<UnifiedChatMessage[]>([])
  const [input, setInput] = useState("")
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [cursorPosition, setCursorPosition] = useState(0)
  const [loading, setLoading] = useState(false)
  const [showSidebar, setShowSidebar] = useState(true)
  const [sidebarWidth, setSidebarWidth] = useState(320)
  const [isResizing, setIsResizing] = useState(false)
  const [factoryAstroSuggestions, setFactoryAstroSuggestions] = useState<any[]>([])
  const [combinedSuggestions, setCombinedSuggestions] = useState<any[]>([])
  const [isLoadingFactorySuggestions, setIsLoadingFactorySuggestions] = useState(false)
  const resizeRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const { clearSessionMessages } = useDjinniStore()
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') || "" : ""
  const apiBaseUrl = getApiBaseUrl()

  const [predefinedQueries, setPredefinedQueries] = useState<PredefinedQuery[]>([])
  const [astroExamples, setAstroExamples] = useState<PredefinedQuery[]>([])
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [sourceId, setSourceId] = useState<string | null>(null)
  const [availableSources, setAvailableSources] = useState<string[]>([])
  const schemaIdMap = useRef<Record<string, number>>({})
  
  const { 
    connected: kgConnected,
    autocompleteSuggestions,
    getAutocompleteSuggestions,
    loading: kgLoading,
    error: kgError
  } = useKGInsights(sourceId ?? '', token, { 
    baseUrl: apiBaseUrl,
    autoReconnect: true,
    autocompleteOptions: {
      maxSuggestions: 5,
      debounceTime: 150
    } 
  });
  
  // Debug WebSocket connection status with detailed information
  useEffect(() => {
    console.log('KG WebSocket status update:', { 
      sourceId, 
      connected: kgConnected, 
      loading: kgLoading, 
      error: kgError, 
      suggestions: autocompleteSuggestions?.length,
      apiBaseUrl,
      token: token ? `${token.substring(0, 10)}...` : 'none',
      availableSources,
      schemaIdMap: Object.keys(schemaIdMap.current).length
    });
    
    // If we have a source ID but no connection, provide troubleshooting info
    if (sourceId && !kgConnected && !kgLoading) {
      console.error('WebSocket connection failed. Troubleshooting info:', {
        wsUrl: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${apiBaseUrl.replace(/^https?:\/\//, '')}/api/kginsights/${sourceId}/ws?token=${token ? token.substring(0, 10) + '...' : 'none'}`,
        browser: navigator.userAgent,
        timeStamp: new Date().toISOString()
      });
    }
    
    // If we're connected, log it clearly
    if (kgConnected) {
      console.log('✅ WebSocket connected successfully to source:', sourceId);
    }
  }, [sourceId, kgConnected, kgLoading, kgError, autocompleteSuggestions?.length, apiBaseUrl, token, availableSources]);

  const fetchKnowledgeGraphSources = useCallback(async () => {
    try {
      setLoading(true);
      
      // First try the kginsights/sources endpoint
      try {
        const response = await fetch(`${apiBaseUrl}/api/kginsights/sources`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('Fetched KG sources from /api/kginsights/sources:', data);
          
          setAvailableSources(data.sources || []);
          schemaIdMap.current = data.schemaIdMap || {};
          
          if (data.sources && data.sources.length > 0) {
            console.log('Setting sourceId to first available source:', data.sources[0]);
            setSourceId(data.sources[0]);
            return; // Successfully got sources, exit early
          }
        } else {
          console.warn(`kginsights/sources endpoint not available: ${response.status} ${response.statusText}`);
        }
      } catch (err) {
        console.warn('Error accessing kginsights/sources endpoint:', err);
      }
      
      // Fallback: Try the graph/schema endpoint used by KG Insights
      try {
        console.log('Trying fallback graph/schema endpoint');
        const response = await fetch(`${apiBaseUrl}/api/graph/schema`, {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        
        if (!response.ok) {
          throw new Error(`Failed to fetch graph schemas: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Fetched graph schemas:', data);

        if (data.schemas && data.schemas.length > 0 && data.schemas[0].id !== -100) {
          const schemaNames = data.schemas.map((s: { name: string }) => s.name);
          const newSchemaIdMap: Record<string, number> = {};
          
          data.schemas.forEach((s: { id: number, name: string }) => {
            newSchemaIdMap[s.name] = s.id;
          });
          
          console.log('Found schemas:', schemaNames, 'with IDs:', newSchemaIdMap);
          schemaIdMap.current = newSchemaIdMap;
          setAvailableSources(schemaNames);
          
          if (schemaNames.length > 0) {
            console.log('Setting sourceId to:', schemaNames[0]);
            setSourceId(schemaNames[0]);
          }
        } else {
          // Last resort: use hardcoded 'default' schema as a fallback
          console.log('Using default schema as fallback');
          setAvailableSources(['default']);
          schemaIdMap.current = { 'default': -1 };
          setSourceId('default');
        }
      } catch (error) {
        console.error('Error in fallback graph schema fetch:', error);
        
        // Emergency fallback - set a default source ID to at least try to establish WebSocket connection
        console.log('Setting emergency default source ID');
        setAvailableSources(['default']);
        schemaIdMap.current = { 'default': -1 };
        setSourceId('default');
      }
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, token]);

  const fetchAstroExamples = useCallback(async () => {
    try {
      const data = await fetchWithAuth(`/api/djinni/astro-examples`);
      
      // Convert examples to PredefinedQuery format
      const formattedExamples = data.examples.map((example: string, index: number) => ({
        id: `astro-example-${index}`,
        query: example,
        category: `${data.active_astro === 'churn_astro' ? 'Churn' : 'Factory'} Astro`
      }));
      
      setAstroExamples(formattedExamples);
    } catch (error) {
      console.error('Error fetching Astro examples:', error);
      setAstroExamples([]);
    }
  }, [token]);

  const fetchPredefinedQueries = useCallback(async (currentSourceId: string) => {
    const schemaId = schemaIdMap.current[currentSourceId];
    if (!schemaId) return;
    try {
      const data = await fetchWithAuth(`/api/datainsights/${schemaId}/query/canned`);
      setPredefinedQueries(data.queries || []);
    } catch (error) {
      console.error("Failed to fetch predefined queries:", error);
    }
  }, [token]);

  const fetchQueryHistory = useCallback(async (currentSourceId: string) => {
    const schemaId = schemaIdMap.current[currentSourceId];
    if (!schemaId) return;
    setLoadingHistory(true);
    try {
      const response = await fetch(`/api/datainsights/${schemaId}/history`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Failed to fetch history');
      const data = await response.json();
      setHistoryItems(data.queries.map((item: any) => ({ ...item, timestamp: new Date(item.timestamp) })));
    } catch (error) {
      console.error("Failed to fetch history:", error);
      setHistoryItems([]);
    } finally {
      setLoadingHistory(false);
    }
  }, [token]);

  useEffect(() => {
    fetchKnowledgeGraphSources();
    
    // Set default sourceId if available sources and none is selected
    if (!sourceId && availableSources.length > 0) {
      console.log('Setting default sourceId to:', availableSources[0]);
      setSourceId(availableSources[0]);
    }
  }, [availableSources.length]);

  useEffect(() => {
    fetchAstroExamples()
  }, [fetchKnowledgeGraphSources]);

  useEffect(() => {
    if (sourceId) {
      fetchPredefinedQueries(sourceId);
      fetchQueryHistory(sourceId);
    }
  }, [sourceId, fetchPredefinedQueries, fetchQueryHistory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const handlePredefinedQuery = (query: string) => {
    setInput(query)
    handleSendMessage(query)
  }

  const loadHistoryItem = (item: HistoryItem) => {
    let resultData: any;
    let assistantContent: string;
    let predictionData: any = null;

    try {
      resultData = JSON.parse(item.result);
      assistantContent = resultData.text || "Could not load result.";
      predictionData = resultData.visualization || null;
    } catch (e) {
      assistantContent = item.result;
    }

    const userMessage: UnifiedChatMessage = {
      id: `history-user-${item.id}`,
      role: 'user',
      content: item.query,
      timestamp: new Date(item.timestamp),
      source: 'kginsights'
    };

    const assistantMessage: UnifiedChatMessage = {
      id: `history-assistant-${item.id}`,
      role: 'assistant',
      content: assistantContent,
      timestamp: new Date(item.timestamp),
      source: 'kginsights',
      predictionData: predictionData
    };

    setMessages([userMessage, assistantMessage]);
    if (showSidebar) {
      toggleSidebar();
    }
    scrollToBottom();
  }
  
  const toggleSidebar = () => setShowSidebar(!showSidebar)
  
  const startResizing = useCallback((mouseDownEvent: React.MouseEvent) => {
    mouseDownEvent.preventDefault()
    setIsResizing(true)
  }, [])

  const stopResizing = useCallback(() => {
    setIsResizing(false)
  }, [])

  const resize = useCallback(
    (mouseMoveEvent: MouseEvent) => {
      if (isResizing) {
        const containerRect = document.querySelector('.flex.h-full')?.getBoundingClientRect()
        if (!containerRect) return

        // Calculate new width based on mouse position
        const totalWidth = containerRect.width
        const chatAreaMinWidth = 300 // Minimum width for the chat area
        const newSidebarWidth = totalWidth - mouseMoveEvent.clientX + containerRect.left
        
        // Apply constraints to ensure sidebar width is reasonable
        if (newSidebarWidth > 200 && newSidebarWidth < (totalWidth - chatAreaMinWidth)) {
          setSidebarWidth(newSidebarWidth)
        }
      }
    },
    [isResizing]
  )

  const deleteHistoryItem = async (id: string) => {
    if (!sourceId) return;
    const schemaId = schemaIdMap.current[sourceId];
    if (!schemaId) return;
    try {
      await fetchWithAuth(`/api/datainsights/${schemaId}/history/${id}`, {
        method: 'DELETE'
      });
      fetchQueryHistory(sourceId);
    } catch (error) {
      console.error("Error deleting history item:", error);
    }
  };

  const deleteAllHistory = async () => {
    if (!sourceId) return;
    const schemaId = schemaIdMap.current[sourceId];
    if (!schemaId) return;
    try {
      await fetchWithAuth(`/api/datainsights/${schemaId}/history`, {
        method: 'DELETE'
      });
      fetchQueryHistory(sourceId);
    } catch (error) {
      console.error("Error deleting all history:", error);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    clearSessionMessages?.();
  };

  const handleSendMessage = async (messageText: string) => {
    if (!messageText.trim()) return

    const newMessage: UnifiedChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: messageText,
      timestamp: new Date(),
      source: "system"
    }

    setMessages(prev => [...prev, newMessage])
    setLoading(true)
    setInput("")

    try {
      const classification = await fetchWithAuth(`${apiBaseUrl}/api/djinni/classify-query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: messageText, source_id: sourceId }),
      });
      const queryType = classification.query_type;

      setMessages(prev => prev.map(msg => msg.id === newMessage.id ? { ...msg, source: queryType } : msg));

      if (queryType.includes('astro')) {
        await handleAstroMessage(messageText, queryType);
      } else if (queryType === 'kginsights') {
        await handleKgInsightsMessage(messageText);
      } else {
        throw new Error(`Unknown query type: ${queryType}`);
      }
    } catch (error) {
      const errorMessage: UnifiedChatMessage = {
        id: `error-${Date.now()}`,
        role: 'system',
        content: `Error: ${error instanceof Error ? error.message : String(error)}`,
        timestamp: new Date(),
        source: 'system'
      }
      setMessages(prev => [...prev, errorMessage])
      setLoading(false)
    }
  }

  const handleKgInsightsMessage = async (message: string) => {
    if (!kgConnected || !sourceId) {
        const errorContent = !sourceId ? "Knowledge graph source not selected." : "Not connected to KG Insights.";
        throw new Error(errorContent);
    }
    const schemaId = schemaIdMap.current[sourceId];
    if (!schemaId) {
        throw new Error("Schema ID not found for the selected source.");
    }

    try {
        const result = await fetchWithAuth(`/api/datainsights/${schemaId}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: message }),
        });
        const assistantMessage: UnifiedChatMessage = {
            id: `kg-response-${Date.now()}`,
            role: "assistant",
            content: result.result || "Here is the result.",
            timestamp: new Date(),
            source: "kginsights",
            predictionData: result.visualization || result.data || null,
        };
        setMessages(prev => [...prev, assistantMessage]);
        fetchQueryHistory(sourceId);
    } finally {
        setLoading(false);
    }
  }

  const handleAstroMessage = async (message: string, astroType: string) => {
    try {
      const result = await fetchWithAuth(`${apiBaseUrl}/api/djinni/astro-query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: message, astro_type: astroType }),
      });

      if (!astroResponse.ok) {
        const errorData = await astroResponse.json().catch(() => ({ detail: 'Astro query failed' }));
        throw new Error(errorData.detail);
      }

      const result = await astroResponse.json();
      
      // Check for error status in the response
      if (result.status === 'error') {
        const errorMessage = result.summary || result.message || 'An error occurred with the prediction';
        const assistantMessage: UnifiedChatMessage = {
          id: `astro-error-${Date.now()}`,
          role: 'assistant',
          content: errorMessage,
          timestamp: new Date(),
          source: astroType === 'churn_astro' ? 'churn_astro' : 'factory_astro',
          userQuery: message,
        };
        setMessages(prev => [...prev, assistantMessage]);
        return;
      }
      
      // Process successful response
      let predictionData = null;
      if (astroType === 'churn_astro') {
        predictionData = result.data;
      } else if (astroType === 'factory_astro') {
        predictionData = result.data?.Predicted_data;
      }

      const assistantMessage: UnifiedChatMessage = {
        id: `astro-response-${Date.now()}`,
        role: 'assistant',
        content: result.summary || "I have processed your query, but no detailed results are available.",
        timestamp: new Date(),
        source: astroType === 'churn_astro' ? 'churn_astro' : 'factory_astro',
        predictionData: predictionData,
        userQuery: message,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      // Handle any exceptions that occur during the API call
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      const assistantMessage: UnifiedChatMessage = {
        id: `astro-error-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${errorMessage}`,
        timestamp: new Date(),
        source: astroType === 'churn_astro' ? 'churn_astro' : 'factory_astro',
        userQuery: message,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(input)
    }
  }

  const handleSourceChange = (value: string) => {
    setSourceId(value)
    setShowSuggestions(false) // Reset suggestions when source changes
  }

  const handleSelectSuggestion = (suggestion: AutocompleteSuggestion) => {
    setInput(suggestion.text)
    setShowSuggestions(false)
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }

  // Fetch Factory Astro autocomplete suggestions
  const fetchFactoryAstroSuggestions = async (text: string, cursorPos: number) => {
    try {
      setIsLoadingFactorySuggestions(true);
      const response = await fetch(`${apiBaseUrl}/api/factory-astro/autocomplete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          partial_text: text,
          cursor_position: cursorPos,
          max_suggestions: 5
        })
      });

      if (!response.ok) {
        console.warn('Failed to fetch Factory Astro suggestions:', response.status, response.statusText);
        setFactoryAstroSuggestions([]);
        return;
      }

      const data = await response.json();
      console.log('Factory Astro suggestions:', data.suggestions);
      setFactoryAstroSuggestions(data.suggestions || []);
    } catch (error) {
      console.error('Error fetching Factory Astro suggestions:', error);
      setFactoryAstroSuggestions([]);
    } finally {
      setIsLoadingFactorySuggestions(false);
    }
  };
  
  // Combine KGInsights and Factory Astro suggestions
  useEffect(() => {
    // Merge suggestions from both sources and deduplicate
    const allSuggestions = [...(autocompleteSuggestions || []), ...factoryAstroSuggestions];
    
    // Remove any duplicates (based on text)
    const uniqueSuggestions = allSuggestions.filter((suggestion, index, self) => 
      index === self.findIndex((s) => s.text === suggestion.text)
    );
    
    setCombinedSuggestions(uniqueSuggestions);
  }, [autocompleteSuggestions, factoryAstroSuggestions]);

  // Handle input change with debounce for autocomplete
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInput(value);
    
    // Update cursor position for autocomplete suggestions
    const cursorPos = e.target.selectionStart || value.length;
    
    // Only show suggestions if there's input and it's at least 2 characters
    if (value.trim().length >= 2) {
      // Fetch suggestions from both sources
      // Get KGInsights suggestions if WebSocket is connected
      if (kgConnected) {
        console.log('Requesting KGInsights autocomplete suggestions:', { query: value, cursorPos });
        getAutocompleteSuggestions(value, cursorPos);
      } else {
        console.warn('Cannot get KGInsights suggestions - WebSocket not connected');
      }
      
      // Also fetch Factory Astro suggestions for predictive queries
      if (value.toLowerCase().includes('what will') || value.toLowerCase().startsWith('what')) {
        console.log('Requesting Factory Astro autocomplete suggestions:', { query: value, cursorPos });
        fetchFactoryAstroSuggestions(value, cursorPos);
      }
      
      setShowSuggestions(true);
    } else {
      setShowSuggestions(false);
      setFactoryAstroSuggestions([]);
    }
  }

  useEffect(() => {
    window.addEventListener('mousemove', resize)
    window.addEventListener('mouseup', stopResizing)
    return () => {
      window.removeEventListener('mousemove', resize)
      window.removeEventListener('mouseup', stopResizing)
    }
  }, [resize, stopResizing])

  return (
    <div className="flex h-full bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
      {/* Chat interface moved to the left side */}
      <div className="flex-1 flex flex-col relative min-w-[300px]">
        <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
          <Button variant="ghost" size="icon" onClick={handleClearChat}>
            <Trash2 className="h-5 w-5" />
          </Button>
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white">Djinni Unified Chat</h2>
          <Button variant="ghost" size="icon" onClick={toggleSidebar}>
            {showSidebar ? <ChevronLeft className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
          </Button>
        </div>
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            {messages.map((msg, index) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
                className={`flex items-start gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}
              >
                {msg.role !== 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
                    {msg.source.includes('astro') ? <Sparkles className="w-5 h-5 text-purple-500" /> : <Bot className="w-5 h-5 text-blue-500" />}
                  </div>
                )}
                <div className={`max-w-lg p-3 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
                }`}>
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  {msg.predictionData && (
                    <div className="mt-2">
                      <MessageVisualization
                        message={msg}
                      />
                    </div>
                  )}
                  <p className="text-xs text-right mt-1 opacity-70">{formatTime(msg.timestamp)}</p>
                </div>
                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
                    <User className="w-5 h-5 text-gray-500" />
                  </div>
                )}
              </motion.div>
            ))}
            {loading && (
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-blue-500" />
                </div>
                <div className="max-w-lg p-3 rounded-lg bg-gray-100 dark:bg-gray-700">
                  <Loader2 className="w-5 h-5 animate-spin text-gray-500" />
                </div>
              </div>
            )}
          </div>
          <div ref={messagesEndRef} />
        </ScrollArea>
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="relative">
            <div className="relative flex-1">
              <Textarea
                ref={inputRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    handleSendMessage(input)
                  } else if (e.key === "Escape") {
                    setShowSuggestions(false)
                  }
                }}
                onBlur={() => {
                  // Delay hiding suggestions to allow for click events
                  setTimeout(() => setShowSuggestions(false), 200)
                }}
                placeholder="Ask me anything..."
                className="min-h-[60px] flex-1 resize-none overflow-auto rounded-md border border-input bg-transparent px-3 py-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 w-full"
                disabled={loading}
              />
              
              {/* WebSocket Status Indicator (always visible for debugging) */}
              <div className="absolute top-full right-0 mt-1 text-xs flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${kgConnected ? 'bg-green-500' : kgLoading ? 'bg-yellow-500' : 'bg-red-500'}`}></span>
                <span className="text-muted-foreground">{kgConnected ? 'Connected' : kgLoading ? 'Connecting...' : 'Disconnected'}</span>
                <span className="text-muted-foreground">| Source: {sourceId || 'None'}</span>
              </div>
              
              {/* Autocomplete suggestions */}
              {showSuggestions && combinedSuggestions && combinedSuggestions.length > 0 && (
                <div className="absolute bottom-full left-0 w-full mb-1 border border-border rounded-md shadow-md overflow-hidden bg-card/95 backdrop-blur-sm z-50">
                  <div className="p-2 bg-secondary/50 text-secondary-foreground text-xs font-medium">
                    Autocomplete Suggestions ({combinedSuggestions.length})
                  </div>
                  <div className="divide-y divide-border/50 max-h-[200px] overflow-y-auto">
                    {combinedSuggestions.map((suggestion, index) => (
                      <div 
                        key={index}
                        className="p-2 hover:bg-primary/10 cursor-pointer transition-colors duration-200"
                        onClick={() => handleSelectSuggestion(suggestion)}
                      >
                        <div className="font-medium">{suggestion.text}</div>
                        {suggestion.description && (
                          <div className="text-xs text-muted-foreground">{suggestion.description}</div>
                        )}
                        {suggestion.source && (
                          <div className="text-[10px] text-muted-foreground mt-1">
                            Source: {suggestion.source === 'factory_astro' ? 'Factory Astro' : 'KGInsights'}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Show debug info when there are no suggestions but we should have them */}
              {showSuggestions && (!combinedSuggestions || combinedSuggestions.length === 0) && input.trim().length > 2 && (
                <div className="absolute bottom-full left-0 w-full mb-1 border border-border rounded-md shadow-md overflow-hidden bg-card/95 backdrop-blur-sm z-50">
                  <div className="p-2 bg-secondary/50 text-secondary-foreground text-xs font-medium">
                    No Suggestions Available
                  </div>
                  <div className="p-2 text-xs text-muted-foreground">
                    <div><strong>Troubleshooting Information:</strong></div>
                    <div>• KGInsights Connection: {kgConnected ? '✅ Connected' : '❌ Disconnected'}</div>
                    <div>• Source ID: {sourceId || 'None'}</div>
                    <div>• Available sources: {availableSources.length ? availableSources.join(', ') : 'None'}</div>
                    {kgError && <div>• Error: {kgError}</div>}
                    <div>• Factory Astro Status: {isLoadingFactorySuggestions ? '⏳ Loading...' : factoryAstroSuggestions.length > 0 ? '✅ Available' : '❌ No results'}</div>
                    <div>• API Base URL: {apiBaseUrl}</div>
                    <div className="mt-1 text-[10px]">If Neo4j is unavailable, KGInsights suggestions cannot be generated. Factory Astro suggestions should still work.</div>
                  </div>
                </div>
              )}
            </div>
            <Button
              type="submit"
              size="icon"
              className="absolute top-1/2 right-2 -translate-y-1/2"
              onClick={() => handleSendMessage(input)}
              disabled={loading || !input.trim()}
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
            </Button>
          </div>
        </div>
      </div>
      {/* Resize handle */}
      {showSidebar && (
        <div
          className="w-1 cursor-col-resize bg-gray-300 dark:bg-gray-600 hover:bg-blue-400 dark:hover:bg-blue-500 active:bg-blue-500 dark:active:bg-blue-600 transition-colors"
          onMouseDown={startResizing}
          ref={resizeRef}
        />
      )}
      
      {/* Queries section moved to the right side - now resizable */}
      {showSidebar && (
        <div 
          style={{ width: `${sidebarWidth}px`, minWidth: '200px', maxWidth: '600px' }}
          className={`${isResizing ? 'select-none' : ''} transition-width duration-150 ease-in-out`}
        >
          <KGInsightsSidebar
            predefinedQueries={[...predefinedQueries, ...astroExamples]}
            onPredefinedQuery={handlePredefinedQuery}
            historyItems={historyItems}
            loadHistoryItem={loadHistoryItem}
            deleteHistoryItem={deleteHistoryItem}
            deleteAllHistory={deleteAllHistory}
            loadingHistory={loadingHistory}
            availableSources={availableSources}
            sourceId={sourceId}
            setSourceId={setSourceId}
          />
        </div>
      )}
    </div>
  )
}
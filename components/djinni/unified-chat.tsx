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
  const [loading, setLoading] = useState(false)
  const [showSidebar, setShowSidebar] = useState(true)
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
  
  const { connected: kgConnected } = useKGInsights(sourceId ?? '', token, { autoReconnect: true });

  const fetchKnowledgeGraphSources = useCallback(async () => {
    try {
      const response = await fetch(`/api/graph/schema`, {
        headers: { 'Authorization': `Bearer ${token}` },
      })
      if (!response.ok) throw new Error("Failed to fetch graph schemas")
      const data = await response.json()

      if (data.schemas && data.schemas.length > 0 && data.schemas[0].id !== -100) {
        const schemaNames = data.schemas.map((s: { name: string }) => s.name)
        const newSchemaIdMap: Record<string, number> = {}
        data.schemas.forEach((s: { id: number, name: string }) => {
          newSchemaIdMap[s.name] = s.id
        })
        schemaIdMap.current = newSchemaIdMap
        setAvailableSources(schemaNames)
        if (!sourceId && schemaNames.length > 0) {
            setSourceId(schemaNames[0]);
        }
      } else {
        setAvailableSources([])
        setSourceId(null);
      }
    } catch (error) {
      console.error("Error fetching graph sources:", error)
      setAvailableSources([])
      setSourceId(null);
    }
  }, [token, sourceId])

  const fetchAstroExamples = useCallback(async () => {
    try {
      const response = await fetch(`/api/djinni/astro-examples`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to fetch Astro examples');
      const data = await response.json();
      
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
      const response = await fetch(`/api/datainsights/${schemaId}/query/canned`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to fetch predefined queries');
      const data = await response.json();
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
        headers: { 'Authorization': `Bearer ${token}` }
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
    fetchKnowledgeGraphSources()
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

  const deleteHistoryItem = async (id: string) => {
    if (!sourceId) return;
    const schemaId = schemaIdMap.current[sourceId];
    if (!schemaId) return;
    try {
      await fetch(`/api/datainsights/${schemaId}/history/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
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
      await fetch(`/api/datainsights/${schemaId}/history`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
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
      const classifyResponse = await fetch(`${apiBaseUrl}/api/djinni/classify-query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ query: messageText, source_id: sourceId }),
      });

      if (!classifyResponse.ok) {
        throw new Error(await classifyResponse.text());
      }

      const classification = await classifyResponse.json();
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
        const response = await fetch(`/api/datainsights/${schemaId}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ query: message }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to get query result');
        }

        const result = await response.json();
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
      const astroResponse = await fetch(`${apiBaseUrl}/api/djinni/astro-query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ query: message, astro_type: astroType }),
      });

      if (!astroResponse.ok) {
        const errorData = await astroResponse.json().catch(() => ({ detail: 'Astro query failed' }));
        throw new Error(errorData.detail);
      }

      const result = await astroResponse.json();
      let predictionData = null;
      if (astroType === 'churn_astro') {
        predictionData = result.data;
      } else if (astroType === 'factory_astro') {
        predictionData = result.data?.Predicted_data;
      }

      const assistantMessage: UnifiedChatMessage = {
        id: `astro-response-${Date.now()}`,
        role: 'assistant',
        content: result.summary || "I have processed your query.",
        timestamp: new Date(),
        source: astroType === 'churn_astro' ? 'churn_astro' : 'factory_astro',
        predictionData: predictionData,
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

  return (
    <div className="flex h-full bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
      {showSidebar && (
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
      )}
      <div className="flex-1 flex flex-col relative">
        <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
          <Button variant="ghost" size="icon" onClick={toggleSidebar}>
            {showSidebar ? <ChevronLeft className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
          </Button>
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white">Djinni Unified Chat</h2>
          <Button variant="ghost" size="icon" onClick={handleClearChat}>
            <Trash2 className="h-5 w-5" />
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
            <Textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask Djinni anything..."
              className="w-full pr-12 resize-none"
              rows={1}
            />
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
    </div>
  )
}
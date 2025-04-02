"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { 
  ChevronRight, 
  Send, 
  PanelRightClose, 
  PanelRightOpen, 
  Sparkles,
  History,
  Settings,
  Database,
  BotMessageSquare
} from "lucide-react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useToast } from "@/components/ui/use-toast"
import { InsightsChatSidebar } from "@/components/kginsights/insights/sidebar"
import { InsightsChatMessages } from "@/components/kginsights/insights/messages"
import { InsightsChatInput } from "@/components/kginsights/insights/input"
import { ThemeConfig } from "@/components/kginsights/insights/theme-config"
import { ChartTheme } from "@/components/kginsights/insights/chart-visualization"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

// Message type for chat history
export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  timestamp: Date
  sourceId?: string
  metadata?: {
    type?: "text" | "graph" | "image" | "table"
    data?: any
  }
  visualization?: {
    type: "bar" | "pie" | "line" | "histogram" | "heatmap" | "none"
    title: string
    description?: string
    x_axis?: {label: string, values: any[]}
    y_axis?: {label: string, values: any[]}
    labels?: string[]
    values?: number[]
    series?: any[]
    raw_data?: any
  }
}

// Predefined query type
export interface PredefinedQuery {
  id: string
  query: string
  category: string
  description?: string
}

export default function InsightsChat() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [sourceId, setSourceId] = useState("default")
  const [availableSources, setAvailableSources] = useState<string[]>([])
  const [loadingSources, setLoadingSources] = useState(false)
  const [predefinedQueries, setPredefinedQueries] = useState<PredefinedQuery[]>([])
  const [chartTheme, setChartTheme] = useState<ChartTheme>({
    colors: ["#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#eab308", "#22c55e", "#06b6d4"],
    backgroundColor: "transparent",
    textColor: "#64748b", 
    gridColor: "#e2e8f0"
  })
  const { toast } = useToast()
  // Use correct type for the reference to avoid type errors
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  
  // Initialize component
  useEffect(() => {
    // Initialize with a welcome message if messages is empty
    if (messages.length === 0) {
      setMessages([
        {
          id: "welcome",
          role: "system",
          content: "Welcome to Knowledge Graph Insights! Ask me anything about your knowledge graph.",
          timestamp: new Date(),
        }
      ])
    }
    
    // Load predefined queries
    fetchPredefinedQueries()
    
    // Load chat history
    fetchChatHistory()
    
    // Load available knowledge graph sources
    fetchKnowledgeGraphSources()
    
    // Cleanup function to ensure state is preserved
    return () => {
      // Component cleanup
    }
  }, [sourceId])

  // Scroll to bottom of messages when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  // Fetch available knowledge graph sources from API
  const fetchKnowledgeGraphSources = async () => {
    setLoadingSources(true)
    try {
      // Get the token from localStorage
      const token = localStorage.getItem("token")
      if (!token) {
        console.warn("No authentication token found in localStorage")
      }
      
      // Fetch available knowledge graph sources
      const response = await fetch(`/api/graph/db`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
        }
      })
      
      if (!response.ok) {
        console.warn(`Graph sources API returned ${response.status}. Using default.`)
        throw new Error(`Failed with status ${response.status}`)
      }
      
      const data = await response.json()
      
      if (data.databases && data.databases.length > 0) {
        setAvailableSources(data.databases)
        
        // If sourceId is not in the list, set it to the first available source
        if (!data.databases.includes(sourceId) && data.databases.length > 0) {
          setSourceId(data.databases[0])
        }
      } else {
        // Fallback to default if no sources available
        setAvailableSources(['default'])
      }
    } catch (error) {
      console.error("Error fetching knowledge graph sources:", error)
      setAvailableSources(['default'])
    } finally {
      setLoadingSources(false)
    }
  }

  // Fetch predefined queries from API with retry logic
  const fetchPredefinedQueries = async () => {
    try {
      // Get the token from localStorage
      const token = localStorage.getItem("token")
      if (!token) {
        console.warn("No authentication token found in localStorage")
      }
      
      // Try the API endpoint with proper authorization header
      const response = await fetch(`/api/datainsights/${sourceId}/query/canned`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
        }
      })
      
      if (!response.ok) {
        console.warn(`Predefined queries API returned ${response.status}. Using defaults.`)
        throw new Error(`Failed with status ${response.status}`)
      }
      
      const data = await response.json()
      setPredefinedQueries(data.queries || [])
    } catch (error) {
      console.error("Error fetching predefined queries:", error)
      // Silently fail for predefined queries, not critical for chat functionality
      // Add some default queries to use if API fails
      setPredefinedQueries([
        { id: "default1", query: "What insights can you provide about this data?", category: "general" },
        { id: "default2", query: "What are the main entities in this knowledge graph?", category: "general" },
        { id: "default3", query: "Show me a visualization of the key data points", category: "visualization" }
      ])
    }
  }

  // Fetch chat history from API with retry logic
  const fetchChatHistory = async () => {
    try {
      // Get the token from localStorage
      const token = localStorage.getItem("token")
      if (!token) {
        console.warn("No authentication token found in localStorage")
      }
      
      // Try the API endpoint with proper authorization header
      const response = await fetch(`/api/datainsights/${sourceId}/query/history?limit=20`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
        }
      })
      
      if (!response.ok) {
        console.warn(`Chat history API returned ${response.status}. Using empty history.`)
        throw new Error(`Failed with status ${response.status}`)
      }
      
      const data = await response.json()
      
      // Convert history to ChatMessage format
      if (data.queries && data.queries.length > 0) {
        const historyMessages: ChatMessage[] = []
        
        data.queries.forEach((query: any) => {
          // Add user message
          historyMessages.push({
            id: `user-${query.id}`,
            role: "user",
            content: query.query,
            timestamp: new Date(query.timestamp),
            sourceId: query.source_id
          })
          
          // Add assistant response
          historyMessages.push({
            id: `assistant-${query.id}`,
            role: "assistant",
            content: query.result,
            timestamp: new Date(query.timestamp),
            sourceId: query.source_id,
            metadata: query.intermediate_steps
          })
        })
        
        // Add history messages to state with welcome message
        setMessages(prev => {
          // Get welcome message if it exists
          const welcomeMessage = prev.find(m => m.role === "system") || {
            id: "welcome",
            role: "system",
            content: "Welcome to Knowledge Graph Insights! Ask me anything about your knowledge graph.",
            timestamp: new Date(),
          };
          
          return [welcomeMessage, ...historyMessages];
        })
      }
    } catch (error) {
      console.error("Error fetching chat history:", error)
      // Don't show error toast for history as it's not critical
    }
  }

  // Handle sending a message
  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return
    
    // Create a new user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: message,
      timestamp: new Date(),
      sourceId
    }
    
    // Update messages with user message
    setMessages((prevMessages) => [...prevMessages, userMessage])
    
    // Show loading state
    setLoading(true)
    
    try {
      // Get the token from localStorage
      const token = localStorage.getItem("token")
      if (!token) {
        console.warn("No authentication token found in localStorage")
      }
      
      // Send request to API with proper authorization header
      const response = await fetch(`/api/datainsights/${sourceId}/query`, {
        method: "POST",
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
        },
        body: JSON.stringify({ query: message }),
      })
      
      if (!response.ok) {
        throw new Error("Failed to get response from Knowledge Graph")
      }
      
      const data = await response.json()
      
      // Create assistant message from response
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: data.result,
        timestamp: new Date(),
        sourceId: data.source_id,
        metadata: data.intermediate_steps,
        visualization: data.visualization  // Add visualization data from API response
      }
      
      // Update messages with assistant response
      setMessages((prevMessages) => [...prevMessages, assistantMessage])
    } catch (error) {
      console.error("Error sending message:", error)
      toast({
        title: "Error",
        description: "Failed to get a response. Please try again.",
        variant: "destructive",
      })
      
      // Add error message
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "system",
        content: "Sorry, I encountered an error processing your request. Please try again.",
        timestamp: new Date(),
      }
      
      setMessages((prevMessages) => [...prevMessages, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  // Handle using a predefined query
  const handlePredefinedQuery = (query: string) => {
    handleSendMessage(query)
  }

  // Clear chat
  const handleClearChat = () => {
    setMessages([
      {
        id: "welcome",
        role: "system",
        content: "Welcome to Knowledge Graph Insights! Ask me anything about your knowledge graph.",
        timestamp: new Date(),
      }
    ])
  }

  return (
    <div className="flex h-full rounded-lg border bg-card shadow-sm">
      {/* Main chat area */}
      <div className="flex flex-col flex-grow h-full">
        {/* Chat messages */}
        <div className="flex-grow overflow-hidden">
          <InsightsChatMessages 
            messages={messages} 
            loading={loading} 
            messagesEndRef={messagesEndRef}
            chartTheme={chartTheme}
          />
        </div>
        
        {/* Chat input */}
        <div className="p-4 border-t">
          <InsightsChatInput 
            onSendMessage={handleSendMessage} 
            loading={loading}
            sourceId={sourceId}
          />
        </div>
      </div>
      
      {/* Collapsible sidebar */}
      <div className={cn(
        "border-l bg-card/50 transition-all duration-300",
        sidebarOpen ? "w-80" : "w-10"
      )}>
        {sidebarOpen ? (
          <div className="h-full flex flex-col">
            <div className="p-4 border-b flex justify-between items-center">
              <h3 className="font-semibold text-lg">KGraph Assistant</h3>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSidebarOpen(false)}
              >
                <PanelRightClose className="h-5 w-5" />
              </Button>
            </div>
            
            <Tabs defaultValue="suggestions" className="flex-grow flex flex-col">
              <TabsList className="grid grid-cols-3 mx-4 mt-2">
                <TabsTrigger value="suggestions">
                  <Sparkles className="h-4 w-4 mr-2" />
                  <span className="hidden sm:inline">Suggestions</span>
                </TabsTrigger>
                <TabsTrigger value="history">
                  <History className="h-4 w-4 mr-2" />
                  <span className="hidden sm:inline">History</span>
                </TabsTrigger>
                <TabsTrigger value="settings">
                  <Settings className="h-4 w-4 mr-2" />
                  <span className="hidden sm:inline">Settings</span>
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="suggestions" className="flex-grow px-2 pt-2 overflow-hidden">
                <InsightsChatSidebar 
                  predefinedQueries={predefinedQueries}
                  onSelectQuery={handlePredefinedQuery}
                />
              </TabsContent>
              
              <TabsContent value="history" className="flex-grow p-2 overflow-hidden">
                <div className="space-y-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={fetchChatHistory}
                    className="w-full"
                  >
                    <History className="h-4 w-4 mr-2" />
                    Refresh History
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={handleClearChat}
                    className="w-full"
                  >
                    <History className="h-4 w-4 mr-2" />
                    Clear Chat
                  </Button>
                </div>
              </TabsContent>
              
              <TabsContent value="settings" className="flex-grow p-2 overflow-hidden">
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium">Knowledge Graph Source</label>
                    <div className="flex mt-1">
                      <Select
                        value={sourceId}
                        onValueChange={(value) => setSourceId(value)}
                        disabled={loadingSources}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select knowledge graph" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            <SelectLabel>Available Knowledge Graphs</SelectLabel>
                            {availableSources.length === 0 && (
                              <SelectItem value="default">Default</SelectItem>
                            )}
                            {availableSources.map((source) => (
                              <SelectItem key={source} value={source}>
                                {source}
                              </SelectItem>
                            ))}
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                      <Button 
                        variant="ghost" 
                        size="icon"
                        onClick={fetchKnowledgeGraphSources}
                        className="ml-2"
                        disabled={loadingSources}
                      >
                        <Database className={`h-4 w-4 ${loadingSources ? 'animate-spin' : ''}`} />
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Select a knowledge graph source to query
                    </p>
                  </div>
                  
                  {/* Chart Theme Configuration */}
                  <ThemeConfig onThemeChange={setChartTheme} />
                </div>
              </TabsContent>
            </Tabs>
          </div>
        ) : (
          <button
            onClick={() => setSidebarOpen(true)}
            className="flex items-center justify-center h-full w-full text-muted-foreground hover:text-foreground transition-colors"
          >
            <PanelRightOpen className="h-5 w-5" />
          </button>
        )}
      </div>
    </div>
  )
}

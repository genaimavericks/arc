"use client"

import { useState, useRef, useEffect, useMemo } from "react"
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
  // Update ref type to match the component interface
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
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
    // Use multiple timeouts with increasing delays to ensure scrolling works
    const scrollTimers = [
      setTimeout(() => scrollToBottom(), 50),
      setTimeout(() => scrollToBottom(), 150),
      setTimeout(() => scrollToBottom(), 300),
      setTimeout(() => scrollToBottom(), 500),
      setTimeout(() => scrollToBottom(), 1000)
    ]
    
    return () => {
      scrollTimers.forEach(timer => clearTimeout(timer))
    }
  }, [messages])

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: "auto",
        block: "end" 
      })
    }
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

  const [input, setInput] = useState("")

  // Sort messages by timestamp to ensure chronological order
  const sortedMessages = useMemo(() => {
    return [...messages].sort((a, b) => {
      return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
    });
  }, [messages]);

  return (
    <div className="flex h-full">
      {/* Sidebar with predefined queries and history */}
      {sidebarOpen && (
        <div className="w-72 border-r bg-card/50 p-4 flex flex-col h-full">
          <Tabs defaultValue="queries" className="w-full">
            <TabsList className="grid w-full grid-cols-3 mb-4">
              <TabsTrigger value="queries">
                <Sparkles className="h-4 w-4 mr-1" />
                <span className="text-xs">Queries</span>
              </TabsTrigger>
              <TabsTrigger value="history">
                <History className="h-4 w-4 mr-1" />
                <span className="text-xs">History</span>
              </TabsTrigger>
              <TabsTrigger value="settings">
                <Settings className="h-4 w-4 mr-1" />
                <span className="text-xs">Settings</span>
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="queries" className="space-y-4 mt-0">
              <div className="space-y-2">
                <div className="text-sm font-medium">Suggested Queries</div>
                <div className="space-y-2">
                  {predefinedQueries
                    .filter(q => q.category === "general")
                    .slice(0, 5)
                    .map(query => (
                      <button
                        key={query.id}
                        className="w-full text-left text-xs p-2 bg-accent/50 hover:bg-accent rounded-md flex items-start"
                        onClick={() => handlePredefinedQuery(query.query)}
                      >
                        <ChevronRight className="h-3 w-3 mr-1 mt-0.5 flex-shrink-0" />
                        <span>{query.query}</span>
                      </button>
                    ))}
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="text-sm font-medium">Relationship Queries</div>
                <div className="space-y-2">
                  {predefinedQueries
                    .filter(q => q.category === "relationships")
                    .slice(0, 5)
                    .map(query => (
                      <button
                        key={query.id}
                        className="w-full text-left text-xs p-2 bg-accent/50 hover:bg-accent rounded-md flex items-start"
                        onClick={() => handlePredefinedQuery(query.query)}
                      >
                        <ChevronRight className="h-3 w-3 mr-1 mt-0.5 flex-shrink-0" />
                        <span>{query.query}</span>
                      </button>
                    ))}
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="text-sm font-medium">Domain Queries</div>
                <div className="space-y-2">
                  {predefinedQueries
                    .filter(q => q.category === "domain")
                    .slice(0, 5)
                    .map(query => (
                      <button
                        key={query.id}
                        className="w-full text-left text-xs p-2 bg-accent/50 hover:bg-accent rounded-md flex items-start"
                        onClick={() => handlePredefinedQuery(query.query)}
                      >
                        <ChevronRight className="h-3 w-3 mr-1 mt-0.5 flex-shrink-0" />
                        <span>{query.query}</span>
                      </button>
                    ))}
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="history" className="mt-0">
              <div className="space-y-2">
                <div className="text-sm font-medium">Recent Conversations</div>
                <div className="space-y-2">
                  {/* Placeholder for chat history */}
                  <div className="text-xs text-muted-foreground">
                    Your conversation history will appear here.
                  </div>
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="settings" className="mt-0">
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="text-sm font-medium">Knowledge Graph Source</div>
                  <Select 
                    value={sourceId} 
                    onValueChange={setSourceId}
                    disabled={loadingSources}
                  >
                    <SelectTrigger className="w-full text-xs h-8">
                      <SelectValue placeholder="Select a knowledge graph" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectLabel>Available Sources</SelectLabel>
                        {availableSources.map(source => (
                          <SelectItem key={source} value={source} className="text-xs">
                            {source}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <div className="text-sm font-medium">Chart Theme</div>
                  <ThemeConfig 
                    onThemeChange={setChartTheme} 
                  />
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      )}
      
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Chat messages */}
        <div className="flex-1 overflow-hidden relative">
          <InsightsChatMessages 
            messages={sortedMessages} 
            loading={loading} 
            messagesEndRef={messagesEndRef}
            chartTheme={chartTheme}
          />
        </div>
        
        {/* Input area */}
        <div className="p-3 border-t bg-background/80 backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              title={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
            >
              {sidebarOpen ? (
                <PanelRightClose className="h-4 w-4" />
              ) : (
                <PanelRightOpen className="h-4 w-4" />
              )}
            </Button>
            
            <div className="flex-1 flex items-center gap-2 relative">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSendMessage(input)
                  }
                }}
                placeholder="Ask a question about your knowledge graph..."
                className="flex-1 h-9 text-sm"
              />
              
              <Button 
                onClick={() => handleSendMessage(input)} 
                size="sm" 
                className="h-9 px-3"
                disabled={loading || !input.trim()}
              >
                <Send className="h-4 w-4 mr-1" />
                Send
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

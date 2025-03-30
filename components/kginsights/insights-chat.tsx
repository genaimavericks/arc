"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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

  // Fetch predefined queries from API
  const fetchPredefinedQueries = async () => {
    try {
      const response = await fetch(`/api/datainsights/${sourceId}/query/canned`)
      if (!response.ok) {
        throw new Error("Failed to fetch predefined queries")
      }
      const data = await response.json()
      setPredefinedQueries(data.queries || [])
    } catch (error) {
      console.error("Error fetching predefined queries:", error)
      toast({
        title: "Error",
        description: "Failed to load predefined queries",
        variant: "destructive",
      })
    }
  }

  // Fetch chat history from API
  const fetchChatHistory = async () => {
    try {
      const response = await fetch(`/api/datainsights/${sourceId}/query/history?limit=20`)
      if (!response.ok) {
        throw new Error("Failed to fetch chat history")
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
      // Send request to API
      const response = await fetch(`/api/datainsights/${sourceId}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
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
        metadata: data.intermediate_steps
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
                      <Input
                        value={sourceId}
                        onChange={(e) => setSourceId(e.target.value)}
                        placeholder="Enter source ID"
                      />
                      <Button 
                        variant="ghost" 
                        size="icon"
                        onClick={fetchPredefinedQueries}
                        className="ml-2"
                      >
                        <Database className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      ID of the knowledge graph source to query
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

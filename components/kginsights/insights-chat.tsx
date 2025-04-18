"use client"

import { useState, useRef, useEffect, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

// Extend Window interface to include our schema mapping
declare global {
  interface Window {
    schemaIdMap: Record<string, number>;
  }
}
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
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
  BotMessageSquare,
  User,
  X,
  Trash2,
  Loader2
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
import { motion } from "framer-motion"
import { SparklesCore } from "@/components/sparkles"
import { FloatingChart } from "@/components/floating-chart"

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
  const [activeTab, setActiveTab] = useState("suggested") // For the first tab system in the UI
  const [historyItems, setHistoryItems] = useState<{id: string, query: string, result: string, timestamp: Date}[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [input, setInput] = useState("")
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
    // Load available knowledge graph sources first, as it will set the welcome message
    fetchKnowledgeGraphSources()
    
    // Load predefined queries
    fetchPredefinedQueries()
    
    // Cleanup function to ensure state is preserved
    return () => {
      // Component cleanup
    }
  }, [sourceId])
  
  // Effect to load history when the history tab is clicked
  useEffect(() => {
    if (activeTab === "history") {
      fetchQueryHistory()
    }
  }, [activeTab, sourceId])
  
  // Direct function to load history data
  const loadHistoryData = () => {
    fetchQueryHistory()
  }

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
      
      // Fetch available knowledge graph sources from schemas with db_loaded='yes'
      const response = await fetch(`/api/graph/schema`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
        }
      })
      
      if (!response.ok) {
        console.warn(`Schema sources API returned ${response.status}. Using default.`)
        throw new Error(`Failed with status ${response.status}`)
      }
      
      const data = await response.json()
      
      // Create a global map to store schema IDs keyed by schema name
      window.schemaIdMap = {} as Record<string, number>
      
      if (data.schemas && data.schemas.length > 0) {
        // Check if we only have the empty placeholder
        if (data.schemas.length === 1 && data.schemas[0].id === -100) {
          // No valid graphs available - set empty message
          setAvailableSources([])
          setMessages([
            {
              id: "welcome",
              role: "system",
              content: "Welcome to Knowledge Graph Insights! Knowledge graph is not created and loaded with data. Generate Graph with appropriate data to use Insights agent",
              timestamp: new Date(),
            }
          ])
        } else {
          // We have real schemas
          const schemaNames = data.schemas.map((schema: { id: number, name: string }) => schema.name)
          setAvailableSources(schemaNames)
          
          // Build schema ID lookup map
          data.schemas.forEach((schema: { id: number, name: string }) => {
            window.schemaIdMap[schema.name] = schema.id
          })
          
          // If sourceId is not in the list, set it to the first available source
          if (!schemaNames.includes(sourceId) && schemaNames.length > 0) {
            setSourceId(schemaNames[0])
          }
          
          // Set standard welcome message if messages is empty
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
        }
      } else {
        // Fallback to empty case
        setAvailableSources([])
        setMessages([
          {
            id: "welcome",
            role: "system",
            content: "Welcome to Knowledge Graph Insights! Knowledge graph is not created and loaded with data. Generate Graph with appropriate data to use Insights agent",
            timestamp: new Date(),
          }
        ])
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
      
      const schemaId = window.schemaIdMap?.[sourceId] || -1
      // Try the API endpoint with proper authorization header
      const response = await fetch(`/api/datainsights/${schemaId}/query/canned`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
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

  // Fetch query history from API with retry logic
  const fetchQueryHistory = async () => {
    if (!sourceId) return
    
    setLoadingHistory(true)
    console.log("Starting to fetch history for sourceId:", sourceId)
    
    try {
      // Get the token from localStorage
      const token = localStorage.getItem("token")
      if (!token) {
        console.warn("No authentication token found in localStorage")
      }
      
      const schemaId = window.schemaIdMap?.[sourceId] || -1
      // Try the API endpoint with proper authorization header
      const apiUrl = `/api/datainsights/${schemaId}/query/history?limit=50`
      console.log("Fetching from:", apiUrl)
      
      const response = await fetch(apiUrl, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
        }
      })
      
      console.log("API Response status:", response.status)
      
      if (!response.ok) {
        console.warn(`Query history API returned ${response.status}`)
        throw new Error(`Failed with status ${response.status}`)
      }
      
      const data = await response.json()
      console.log("History data received:", data)
      
      // Transform the data to the format we need
      const historyData = data.queries.map((item: any) => ({
        id: item.id,
        query: item.query,
        result: item.result,
        timestamp: new Date(item.timestamp)
      }))
      
      console.log("Processed history items:", historyData.length)
      setHistoryItems(historyData)
    } catch (error) {
      console.error("Error fetching query history:", error)
      toast({
        title: "Error",
        description: "Failed to load query history. Please try again later.",
        variant: "destructive"
      })
    } finally {
      setLoadingHistory(false)
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
      
      // Get schema ID from the source name
      const schemaId = window.schemaIdMap?.[sourceId] || -1
      
      // Send request to API with proper authorization header
      const response = await fetch(`/api/datainsights/${schemaId}/query`, {
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
  
  // Format date display
  const formatDate = (date: Date) => {
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
  
  // Delete a single history item
  const deleteHistoryItem = async (id: string) => {
    if (!sourceId) return
    
    try {
      // Get the token from localStorage
      const token = localStorage.getItem("token")
      if (!token) {
        console.warn("No authentication token found in localStorage")
      }
      
      const schemaId = window.schemaIdMap?.[sourceId] || -1
      const response = await fetch(`/api/datainsights/${schemaId}/query/history/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })
      
      if (!response.ok) {
        throw new Error(`Failed to delete history item: ${response.status}`)
      }
      
      // Update the UI by removing the deleted item
      setHistoryItems(historyItems.filter(item => item.id !== id))
      
      toast({
        title: "Success",
        description: "History item deleted successfully.",
      })
    } catch (error) {
      console.error("Error deleting history item:", error)
      toast({
        title: "Error",
        description: "Failed to delete history item. Please try again.",
        variant: "destructive"
      })
    }
  }
  
  // Delete all history
  const deleteAllHistory = async () => {
    if (!sourceId) return
    
    try {
      // Get the token from localStorage
      const token = localStorage.getItem("token")
      if (!token) {
        console.warn("No authentication token found in localStorage")
      }
      
      const schemaId = window.schemaIdMap?.[sourceId] || -1
      const response = await fetch(`/api/datainsights/${schemaId}/query/history`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })
      
      if (!response.ok) {
        throw new Error(`Failed to delete all history: ${response.status}`)
      }
      
      // Clear the history items
      setHistoryItems([])
      setDeleteDialogOpen(false)
      
      toast({
        title: "Success",
        description: "All history items deleted successfully.",
      })
    } catch (error) {
      console.error("Error deleting all history:", error)
      toast({
        title: "Error",
        description: "Failed to delete history. Please try again.",
        variant: "destructive"
      })
    }
  }
  
  // Load a history item into the chat
  const loadHistoryItem = (query: string) => {
    setInput(query)
    handleSendMessage(query)
    // Change to suggested tab without using click() which causes TypeScript errors
    setActiveTab("suggested")
  }

  

  // Sort messages by timestamp to ensure chronological order
  const sortedMessages = useMemo(() => {
    return [...messages].sort((a, b) => {
      return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
    });
  }, [messages]);

  return (
    <div className="flex h-full bg-gradient-to-b from-background to-background/95">
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 opacity-10 pointer-events-none">
        <SparklesCore
          id="insightsparkles"
          background="transparent"
          minSize={0.4}
          maxSize={1.5}
          particleDensity={15}
          className="w-full h-full"
          particleColor="#888"
        />
      </div>
      
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
        <FloatingChart count={3} avoidRightSide={true} zIndex={0} />
      </div>

      {/* Sidebar with predefined queries and history */}
      {sidebarOpen && (
        <div className="w-72 border-r bg-card/50 p-4 flex flex-col h-full max-h-full">
          <Tabs defaultValue="queries" className="w-full h-full flex flex-col" onValueChange={(value) => {
              if (value === "history") {
                loadHistoryData()
              }
            }}>
            <TabsList className="grid w-full grid-cols-3 mb-4">
              <TabsTrigger value="queries">
                <Sparkles className="h-4 w-4 mr-1" />
                <span className="text-xs">Queries</span>
              </TabsTrigger>
              <TabsTrigger value="history" onClick={loadHistoryData}>
                <History className="h-4 w-4 mr-1" />
                <span className="text-xs">History</span>
              </TabsTrigger>
              <TabsTrigger value="settings">
                <Settings className="h-4 w-4 mr-1" />
                <span className="text-xs">Settings</span>
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="queries" className="mt-0 flex-1 overflow-hidden">
              <div className="p-3 h-full overflow-auto">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="text-sm font-medium">Suggested Queries</div>
                    <div className="space-y-2">
                      {predefinedQueries
                        .filter(q => q.category === "general")
                        .slice(0, 10)
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
                        .slice(0, 10)
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
                        .slice(0, 10)
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
                </div>
              </div>
            </TabsContent>
            
            <TabsContent 
              value="history" 
              className="mt-0 flex-1 overflow-hidden"
            >
              <div className="p-3 h-full overflow-auto">
                <div className="flex justify-between items-center mb-3">
                <div className="text-sm font-medium">Recent Conversations</div>
                
                <div className="flex gap-2">
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-7 px-2 text-xs"
                    onClick={() => fetchQueryHistory()}
                    title="Refresh History"
                  >
                    <Loader2 className="h-3.5 w-3.5 mr-1" />
                    Refresh
                  </Button>
                
                  <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                  <AlertDialogTrigger asChild>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-7 px-2 text-xs"
                      disabled={historyItems.length === 0}
                    >
                      <Trash2 className="h-3.5 w-3.5 mr-1" />
                      Clear All
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete All History</AlertDialogTitle>
                      <AlertDialogDescription>
                        Are you sure you want to delete all conversation history? This action cannot be undone.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction onClick={deleteAllHistory}>Delete All</AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
                </div>
              </div>
              
              <div className="flex-1 overflow-hidden flex flex-col">
                <ScrollArea className="flex-1 h-full overflow-auto relative">
                  <div className="space-y-3 pr-2">
                  {loadingHistory ? (
                    <div className="flex items-center justify-center p-4">
                      <Loader2 className="h-5 w-5 animate-spin mr-2" />
                      <span className="text-xs">Loading history...</span>
                    </div>
                  ) : historyItems.length === 0 ? (
                    <div className="text-xs text-muted-foreground p-1">
                      No conversation history available.
                    </div>
                  ) : (
                    historyItems.map((item) => (
                      <div key={item.id} className="border rounded-lg overflow-hidden bg-background hover:border-primary/50 transition-colors">
                        {/* Query (User message) */}
                        <div className="flex items-start p-2 border-b group">
                          <div className="flex items-center mr-2">
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button 
                                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-muted rounded mr-1"
                                    onClick={() => deleteHistoryItem(item.id)}
                                  >
                                    <X className="h-3 w-3" />
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent side="right">
                                  <p className="text-xs">Delete this conversation</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                            <div className="rounded-full bg-primary p-1.5 flex items-center justify-center shrink-0">
                              <User className="h-3 w-3 text-primary-foreground" />
                            </div>
                          </div>
                          <div className="flex-1 overflow-x-auto">
                            <div 
                              className="text-xs cursor-pointer hover:text-primary whitespace-normal"
                              onClick={() => loadHistoryItem(item.query)}
                              title={item.query}
                            >
                              {item.query}
                            </div>
                          </div>
                        </div>
                        
                        {/* Response (Bot message) */}
                        <div className="flex items-start p-2">
                          <div className="rounded-full bg-primary/10 p-1.5 flex items-center justify-center mr-2 mt-0.5 shrink-0">
                            <BotMessageSquare className="h-3 w-3 text-primary" />
                          </div>
                          <div className="flex-1 overflow-x-auto">
                            <div className="text-xs whitespace-normal text-muted-foreground" title={item.result}>
                              {item.result}
                            </div>
                            <div className="text-[10px] mt-1 text-muted-foreground">
                              {formatDate(item.timestamp)}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                  </div>
                </ScrollArea>
              </div>
              </div>
            </TabsContent>
            
            <TabsContent 
              value="settings" 
              className="mt-0 flex-1 overflow-hidden"
            >
              <div className="p-3 h-full overflow-auto">
                <div className="space-y-4">
                  {/* Settings content at the top */}
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
              </div>
            </TabsContent>
          </Tabs>
        </div>
      )}
      
      {/* Main chat area */}
      <div className="flex-1 flex flex-col relative z-10">
        {/* Chat messages */}
        <div className="flex-1 overflow-hidden relative">
          <InsightsChatMessages 
            messages={sortedMessages} 
            loading={loading} 
            messagesEndRef={messagesEndRef as React.RefObject<HTMLDivElement>}
            chartTheme={chartTheme}
          />
        </div>
        
        {/* Input area */}
        <motion.div 
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="p-3 border-t border-primary/10 bg-background/90 backdrop-blur-md shadow-lg"
        >
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-full text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors duration-300"
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
                    if (input.trim()) {
                      handleSendMessage(input)
                      setInput("")
                    }
                  }
                }}
                placeholder="Ask a question about your knowledge graph..."
                className="flex-1 h-9 text-sm bg-card/50 backdrop-blur-sm border-primary/20 shadow-sm focus-visible:ring-primary pl-4 pr-10 transition-all duration-300"
              />
              
              <Button 
                onClick={() => {
                  if (input.trim()) {
                    handleSendMessage(input)
                    setInput("")
                  }
                }}
                size="sm" 
                className="h-9 px-3 absolute right-0 rounded-l-none bg-primary hover:bg-primary/90 text-primary-foreground transition-all duration-300 hover:shadow"
                disabled={loading || !input.trim()}
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
          
          <div className="flex justify-center mt-1">
            <div className="text-xs text-muted-foreground flex items-center gap-2">
              <div className="text-center flex items-center">
                <Sparkles className="h-3 w-3 mr-1 text-primary/60" />
                <span>Powered by Knowledge Graph AI</span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

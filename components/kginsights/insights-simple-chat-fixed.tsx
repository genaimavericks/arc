"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { Send, Loader2, Sparkles, AlertCircle, CheckCircle2, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/components/ui/use-toast"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { AutocompleteSuggestions } from "./autocomplete-suggestions"
import { AutocompleteSuggestion } from "./autocomplete-service"

// Add TypeScript declaration for window.autocompleteTimer
declare global {
  interface Window {
    autocompleteTimer: ReturnType<typeof setTimeout> | null;
    schemaIdMap: Record<string, number>;
  }
}

// Using the imported AutocompleteSuggestion interface

// Simple message type for chat history
interface ChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  timestamp: Date
  visualization?: {
    type: string
    title: string
    description?: string
    x_axis?: { label: string, values: any[] }
    y_axis?: { label: string, values: any[] }
    labels?: string[]
    values?: number[]
  }
}

// Validation error type
interface ValidationError {
  type: "error" | "warning"
  message: string
  position: { start: number, end: number }
}

// WebSocket message types
type WebSocketMessageType = 
  | "query" | "query_result" | "query_error"
  | "autocomplete" | "autocomplete_suggestions" | "autocomplete_error"
  | "validate" | "validation_result" | "validation_error"
  | "suggest" | "suggestions" | "suggestions_error"
  | "ping" | "pong" | "connection_status" | "error"

export function InsightsSimpleChat() {
  // State management
  const [messages, setMessages] = useState<ChatMessage[]>([{
    id: "welcome",
    role: "system",
    content: "Welcome to the simplified Knowledge Graph Insights! Ask me anything about your knowledge graph.",
    timestamp: new Date(),
  }])
  const [loading, setLoading] = useState(false)
  const [input, setInput] = useState("")
  const [availableSources, setAvailableSources] = useState<string[]>([])
  const [sourceId, setSourceId] = useState("")
  const [loadingSources, setLoadingSources] = useState(false)
  
  // WebSocket state
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  
  // Real-time features state
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState<AutocompleteSuggestion[]>([])
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([])
  const [showAutocomplete, setShowAutocomplete] = useState(false)
  const [cursorPosition, setCursorPosition] = useState(0)
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const { toast } = useToast()

  // Initialize component
  useEffect(() => {
    fetchKnowledgeGraphSources()
  }, [])
  
  // Setup WebSocket connection when sourceId changes
  useEffect(() => {
    if (!sourceId) return
    
    // Close existing connection
    if (socketRef.current) {
      socketRef.current.close()
    }

    // Get token from localStorage
    const token = localStorage.getItem("token") || "";
    
    // Determine if we're using secure WebSocket based on the current protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Use the direct WebSocket endpoint with the schema ID
    const wsUrl = `${protocol}//${window.location.host}/api/kgdatainsights/ws/direct/${sourceId}?token=${token}`;
    
    try {
      // Create new WebSocket connection
      const newSocket = new WebSocket(wsUrl);
      socketRef.current = newSocket;
      
      // Setup event handlers
      newSocket.onopen = () => {
        setIsConnected(true);
        setConnectionError(null);
        console.log(`WebSocket connected to ${sourceId}`);
      };
      
      newSocket.onclose = () => {
        setIsConnected(false);
        console.log(`WebSocket disconnected from ${sourceId}`);
      };
      
      newSocket.onerror = (error) => {
        setConnectionError("WebSocket connection error. Please try again.");
        console.error("WebSocket error:", error);
      };
      
      newSocket.onmessage = (event) => {
        handleWebSocketMessage(event);
      };
      
      setSocket(newSocket);
    } catch (error) {
      console.error("Error creating WebSocket:", error);
      setConnectionError(`Failed to connect: ${error}`);
    }
    
    // Cleanup function
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    }
  }, [sourceId])
  
  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data)
      console.log('Received WebSocket message:', data)
      
      const { type, content } = data
      
      switch (type) {
        case 'connection_status':
          // Handle connection status
          break
          
        case 'pong':
          // Handle pong response
          console.log('Received pong response')
          break
          
        case 'query_result':
          // Handle query result
          handleQueryResult(content)
          break
          
        case 'query_error':
          // Handle query error
          handleQueryError(content)
          break
          
        case 'autocomplete_suggestions':
          // Handle autocomplete suggestions
          if (content.suggestions && Array.isArray(content.suggestions)) {
            // Convert suggestions to the correct format if needed
            const formattedSuggestions = content.suggestions.map((suggestion: any) => {
              if (typeof suggestion === 'string') {
                return { text: suggestion, description: null }
              } else if (suggestion && typeof suggestion === 'object' && 'text' in suggestion) {
                return {
                  text: suggestion.text,
                  description: suggestion.description || null
                }
              }
              return { text: String(suggestion), description: null }
            })
            
            setAutocompleteSuggestions(formattedSuggestions)
            setShowAutocomplete(formattedSuggestions.length > 0)
          } else {
            setAutocompleteSuggestions([])
            setShowAutocomplete(false)
          }
          break
          
        case 'validation_result':
          // Handle validation result
          setValidationErrors(content.errors || [])
          break
          
        case 'suggestions':
          // Handle query suggestions
          setSuggestions(content.suggestions || [])
          break
          
        case 'error':
          // Handle general error
          toast({
            title: "Error",
            description: content.error,
            variant: "destructive"
          })
          break
          
        default:
          console.log(`Unknown message type: ${type}`)
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error)
    }
  }, [toast])
  
  // Send WebSocket message helper
  const sendWebSocketMessage = (socket: WebSocket | null, type: WebSocketMessageType, content: any) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected')
      return
    }
    
    const message = {
      type,
      content,
      timestamp: new Date().toISOString()
    }
    
    socket.send(JSON.stringify(message))
  }
  
  // Handle query result from WebSocket
  const handleQueryResult = (content: any) => {
    const assistantMessage: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: content.result,
      timestamp: new Date(),
      visualization: content.visualization
    }
    
    setMessages(prevMessages => [...prevMessages, assistantMessage])
    setLoading(false)
  }
  
  // Handle query error from WebSocket
  const handleQueryError = (content: any) => {
    const errorMessage: ChatMessage = {
      id: `error-${Date.now()}`,
      role: "system",
      content: `Error: ${content.error}`,
      timestamp: new Date()
    }
    
    setMessages(prevMessages => [...prevMessages, errorMessage])
    setLoading(false)
    
    toast({
      title: "Error",
      description: content.error,
      variant: "destructive"
    })
  }

  // Scroll to bottom of messages when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: "smooth",
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
      
      // Fetch available knowledge graph sources
      const response = await fetch(`/api/graph/schema`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json',
        }
      })
      
      if (!response.ok) {
        console.warn(`Schema sources API returned ${response.status}. Using default.`)
        setAvailableSources(['default'])
        setSourceId('default')
        return
      }
      
      const data = await response.json()
      
      // Create a global map to store schema IDs keyed by schema name
      window.schemaIdMap = {} as Record<string, number>
      
      if (data.schemas && data.schemas.length > 0) {
        // Filter out the empty placeholder if present
        const validSchemas = data.schemas.filter((schema: { id: number }) => schema.id !== -100)
        
        if (validSchemas.length > 0) {
          const schemaNames = validSchemas.map((schema: { name: string }) => schema.name)
          setAvailableSources(schemaNames)
          setSourceId(schemaNames[0])
          
          // Build schema ID lookup map
          validSchemas.forEach((schema: { id: number, name: string }) => {
            window.schemaIdMap[schema.name] = schema.id
          })
        } else {
          // No valid schemas
          setAvailableSources(['default'])
          setSourceId('default')
        }
      } else {
        // Fallback to default
        setAvailableSources(['default'])
        setSourceId('default')
      }
    } catch (error) {
      console.error("Error fetching knowledge graph sources:", error)
      setAvailableSources(['default'])
      setSourceId('default')
    } finally {
      setLoadingSources(false)
    }
  }

  // Handle sending a message
  const handleSendMessage = async (message: string) => {
    if (!message.trim() || loading) return
    
    // Create a new user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: message,
      timestamp: new Date(),
    }
    
    // Update messages with user message
    setMessages((prevMessages) => [...prevMessages, userMessage])
    
    // Clear input and show loading state
    setInput("")
    setLoading(true)
    
    // Clear suggestions and validation errors
    setSuggestions([])
    setValidationErrors([])
    setAutocompleteSuggestions([])
    setShowAutocomplete(false)
    
    // Try to use WebSocket if connected
    if (isConnected && socket && socket.readyState === WebSocket.OPEN) {
      // Send query via WebSocket
      sendWebSocketMessage(socket, 'query', {
        query: message,
        query_id: `query-${Date.now()}`
      })
      return
    }
    
    // Fallback to REST API if WebSocket is not available
    try {
      // Get the token from localStorage
      const token = localStorage.getItem("token")
      
      // Get schema ID from the source name
      const schemaId = window.schemaIdMap?.[sourceId] || -1
      
      // Send request to API with proper authorization header
      const response = await fetch(`/api/datainsights/${schemaId}/query`, {
        method: "POST",
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json',
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
        content: data.result || data.response || "I processed your request but couldn't generate a proper response.",
        timestamp: new Date(),
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
  
  // Handle input changes with real-time features
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    setInput(value)
    
    // Store cursor position
    if (inputRef.current) {
      setCursorPosition(inputRef.current.selectionStart || value.length)
    }
    
    // Skip real-time features if not connected
    if (!isConnected || !socket || socket.readyState !== WebSocket.OPEN) {
      return
    }
    
    // Request validation if input is not empty
    if (value.trim()) {
      sendWebSocketMessage(socket, 'validate', {
        query: value,
        request_id: `validate-${Date.now()}`
      })
    } else {
      setValidationErrors([])
    }
    
    // Debounce autocomplete requests to avoid excessive API calls
    if (window.autocompleteTimer) {
      clearTimeout(window.autocompleteTimer)
    }
    
    window.autocompleteTimer = setTimeout(() => {
      // Request autocomplete at cursor position
      sendWebSocketMessage(socket, 'autocomplete', {
        text: value,
        cursor_position: inputRef.current?.selectionStart || value.length,
        request_id: `autocomplete-${Date.now()}`
      })
    }, 300) // 300ms debounce delay
    
    // Request suggestions if input is not empty
    if (value.trim()) {
      sendWebSocketMessage(socket, 'suggest', {
        query: value,
        request_id: `suggest-${Date.now()}`
      })
    } else {
      setSuggestions([])
    }
  }
  
  // Handle selecting an autocomplete suggestion
  const handleSelectSuggestion = (suggestion: string) => {
    if (!inputRef.current) return
    
    const currentValue = input
    const textBeforeCursor = currentValue.substring(0, cursorPosition)
    const textAfterCursor = currentValue.substring(cursorPosition)
    
    // Find the word being completed
    const lastSpacePos = textBeforeCursor.lastIndexOf(" ")
    const wordStart = lastSpacePos >= 0 ? lastSpacePos + 1 : 0
    
    // Replace the current word with the suggestion
    const newValue = 
      currentValue.substring(0, wordStart) + 
      suggestion + 
      (textAfterCursor.startsWith(" ") ? "" : " ") + 
      textAfterCursor
    
    setInput(newValue)
    setShowAutocomplete(false)
    
    // Focus the input and set cursor position after the inserted suggestion
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus()
        const newCursorPos = wordStart + suggestion.length + 1
        inputRef.current.setSelectionRange(newCursorPos, newCursorPos)
        setCursorPosition(newCursorPos)
      }
    }, 0)
  }
  
  // Handle using a suggestion
  const handleUseSuggestion = (suggestion: string) => {
    setInput(suggestion)
    setShowAutocomplete(false)
    setSuggestions([])
    
    // Focus the input
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus()
      }
    }, 0)
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

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <h1 className="text-xl font-semibold">Knowledge Graph Insights (Simple)</h1>
          </div>
          <div className="w-64">
            <Select 
              value={sourceId} 
              onValueChange={setSourceId}
              disabled={loadingSources}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a knowledge graph" />
              </SelectTrigger>
              <SelectContent>
                {availableSources.map(source => (
                  <SelectItem key={source} value={source}>
                    {source}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
      
      {/* Chat messages */}
      <div className="flex-1 overflow-auto p-4">
        <div className="space-y-4">
          {messages.map(message => (
            <div 
              key={message.id} 
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div 
                className={`max-w-[80%] rounded-lg p-4 ${
                  message.role === 'user' 
                    ? 'bg-primary text-primary-foreground' 
                    : message.role === 'system' 
                      ? 'bg-muted/80 text-muted-foreground' 
                      : 'bg-card border'
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>
                <div className="text-xs mt-2 opacity-70">
                  {formatDate(message.timestamp)}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>
      
      {/* WebSocket connection status */}
      {connectionError && (
        <div className="p-2 bg-destructive/10 border border-destructive/30 text-destructive text-sm rounded-md mx-4 mb-2 flex items-center">
          <AlertCircle className="h-4 w-4 mr-2" />
          WebSocket error: {connectionError}
        </div>
      )}
      
      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="px-4 pb-2">
          <div className="text-xs text-muted-foreground mb-1">Suggested queries:</div>
          <div className="flex flex-wrap gap-1">
            {suggestions.map((suggestion, index) => (
              <Badge 
                key={index} 
                variant="outline" 
                className="cursor-pointer hover:bg-primary/10 transition-colors"
                onClick={() => handleUseSuggestion(suggestion)}
              >
                {suggestion}
              </Badge>
            ))}
          </div>
        </div>
      )}
      
      {/* Input area */}
      <div className="p-4 border-t relative">
        {/* Autocomplete suggestions */}
        {inputRef && (
          <AutocompleteSuggestions
            suggestions={autocompleteSuggestions}
            visible={showAutocomplete}
            onSelect={handleSelectSuggestion}
            inputRef={inputRef}
          />
        )}
        
        {/* Validation errors */}
        {validationErrors.length > 0 && (
          <div className="absolute -top-10 left-0 right-0 bg-card border rounded-md p-2 shadow-md z-10">
            {validationErrors.map((error, index) => (
              <div 
                key={index} 
                className={`flex items-start text-xs ${error.type === 'error' ? 'text-destructive' : 'text-amber-500'}`}
              >
                {error.type === 'error' ? (
                  <AlertCircle className="h-3 w-3 mr-1 mt-0.5 flex-shrink-0" />
                ) : (
                  <AlertCircle className="h-3 w-3 mr-1 mt-0.5 flex-shrink-0" />
                )}
                <span>{error.message}</span>
              </div>
            ))}
          </div>
        )}
        
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSendMessage(input)
                } else if (e.key === 'Tab' && showAutocomplete && autocompleteSuggestions.length > 0) {
                  e.preventDefault()
                  handleSelectSuggestion(autocompleteSuggestions[0].text)
                }
              }}
              onBlur={() => {
                // Delay hiding autocomplete to allow clicking on suggestions
                setTimeout(() => setShowAutocomplete(false), 200)
              }}
              placeholder="Ask a question about your knowledge graph..."
              className="min-h-[60px] flex-1 pr-8"
              disabled={loading}
            />
            
            {/* Connection status indicator */}
            <div className="absolute right-2 top-2">
              {isConnected ? (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>WebSocket connected</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              ) : (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <X className="h-4 w-4 text-destructive" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>WebSocket disconnected</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
          </div>
          
          <Button 
            onClick={() => handleSendMessage(input)}
            disabled={!input.trim() || loading}
            size="icon"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
        
        <div className="flex justify-between text-xs text-muted-foreground mt-2">
          <div>Press Enter to send, Shift+Enter for new line</div>
          <div>Tab to autocomplete</div>
        </div>
      </div>
    </div>
  )
}

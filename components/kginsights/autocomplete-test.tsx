"use client"

import { useState, useRef, useEffect } from "react"
import { Send, Loader2, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/components/ui/use-toast"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

// Autocomplete suggestion type
interface AutocompleteSuggestion {
  text: string
  description?: string | null
}

// AutocompleteSuggestions component
interface AutocompleteSuggestionsProps {
  suggestions: AutocompleteSuggestion[]
  visible: boolean
  onSelect: (suggestion: string) => void
  inputRef: React.RefObject<HTMLTextAreaElement>
}

const AutocompleteSuggestions = ({ suggestions, visible, onSelect, inputRef }: AutocompleteSuggestionsProps) => {
  const [activeIndex, setActiveIndex] = useState(-1)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  
  // Reset active index when suggestions change
  useEffect(() => {
    setActiveIndex(-1)
  }, [suggestions])
  
  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!visible || suggestions.length === 0) return
      
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setActiveIndex(prev => (prev + 1) % suggestions.length)
          break
        case 'ArrowUp':
          e.preventDefault()
          setActiveIndex(prev => (prev - 1 + suggestions.length) % suggestions.length)
          break
        case 'Enter':
          if (activeIndex >= 0 && activeIndex < suggestions.length) {
            e.preventDefault()
            onSelect(suggestions[activeIndex].text)
          }
          break
        case 'Escape':
          e.preventDefault()
          // Close suggestions
          return
        case 'Tab':
          if (activeIndex >= 0 && activeIndex < suggestions.length) {
            e.preventDefault()
            onSelect(suggestions[activeIndex].text)
          } else if (suggestions.length > 0) {
            e.preventDefault()
            onSelect(suggestions[0].text)
          }
          break
      }
    }
    
    // Add event listener to the input element
    const inputElement = inputRef.current
    if (inputElement) {
      inputElement.addEventListener('keydown', handleKeyDown)
    }
    
    return () => {
      if (inputElement) {
        inputElement.removeEventListener('keydown', handleKeyDown)
      }
    }
  }, [visible, suggestions, activeIndex, onSelect, inputRef])
  
  // Scroll active item into view
  useEffect(() => {
    if (activeIndex >= 0 && suggestionsRef.current) {
      const activeElement = suggestionsRef.current.children[activeIndex] as HTMLElement
      if (activeElement) {
        activeElement.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [activeIndex])
  
  if (!visible || suggestions.length === 0) return null
  
  return (
    <div 
      className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md bg-card border shadow-lg"
      ref={suggestionsRef}
    >
      <div className="py-1 text-sm">
        {suggestions.map((suggestion, index) => (
          <div
            key={`${suggestion.text}-${index}`}
            className={`px-3 py-2 cursor-pointer ${index === activeIndex ? 'bg-primary/10 text-primary' : 'hover:bg-muted'}`}
            onClick={() => onSelect(suggestion.text)}
          >
            <div className="font-medium">{suggestion.text}</div>
            {suggestion.description && (
              <div className="text-xs text-muted-foreground">{suggestion.description}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// Declare global type for window.autocompleteTimer
declare global {
  interface Window {
    autocompleteTimer: ReturnType<typeof setTimeout> | null;
    schemaIdMap: Record<string, number>;
  }
}

export function AutocompleteTest() {
  // State management
  const [input, setInput] = useState("")
  const [availableSources, setAvailableSources] = useState<string[]>([])
  const [sourceId, setSourceId] = useState("")
  const [loadingSources, setLoadingSources] = useState(false)
  
  // WebSocket state
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  
  // Autocomplete state
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState<AutocompleteSuggestion[]>([])
  const [showAutocomplete, setShowAutocomplete] = useState(false)
  const [cursorPosition, setCursorPosition] = useState(0)
  
  // Refs
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
    const token = localStorage.getItem("token") || ""
    
    // Determine if we're using secure WebSocket based on the current protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    // Use the direct WebSocket endpoint with the schema ID
    const wsUrl = `${protocol}//${window.location.host}/api/kgdatainsights/ws/direct/${sourceId}?token=${token}`
    
    try {
      // Create new WebSocket connection
      const newSocket = new WebSocket(wsUrl)
      socketRef.current = newSocket
      
      // Setup event handlers
      newSocket.onopen = () => {
        setIsConnected(true)
        setConnectionError(null)
        console.log(`WebSocket connected to ${sourceId}`)
      }
      
      newSocket.onclose = () => {
        setIsConnected(false)
        console.log(`WebSocket disconnected from ${sourceId}`)
      }
      
      newSocket.onerror = (error) => {
        setConnectionError("WebSocket connection error. Please try again.")
        console.error("WebSocket error:", error)
      }
      
      newSocket.onmessage = (event) => {
        handleWebSocketMessage(event)
      }
      
      setSocket(newSocket)
    } catch (error) {
      console.error("Error creating WebSocket:", error)
      setConnectionError(`Failed to connect: ${error}`)
    }
    
    // Cleanup function
    return () => {
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [sourceId])
  
  // Handle WebSocket messages
  const handleWebSocketMessage = (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data)
      console.log('Received WebSocket message:', data)
      
      const { type, content } = data
      
      switch (type) {
        case 'connection_status':
          // Handle connection status
          break
          
        case 'autocomplete_suggestions':
          // Handle autocomplete suggestions
          if (content.suggestions && Array.isArray(content.suggestions)) {
            // Convert suggestions to the correct format if needed
            const formattedSuggestions = content.suggestions.map((suggestion: any) => {
              if (typeof suggestion === 'string') {
                return { text: suggestion }
              } else if (suggestion && typeof suggestion === 'object' && 'text' in suggestion) {
                return suggestion
              }
              return { text: String(suggestion) }
            })
            
            setAutocompleteSuggestions(formattedSuggestions)
            setShowAutocomplete(formattedSuggestions.length > 0)
          } else {
            setAutocompleteSuggestions([])
            setShowAutocomplete(false)
          }
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
  }
  
  // Send WebSocket message helper
  const sendWebSocketMessage = (socket: WebSocket | null, type: string, content: any) => {
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

  return (
    <div className="flex flex-col h-full bg-background p-4">
      <h1 className="text-2xl font-bold mb-4">Autocomplete Test</h1>
      
      {/* Schema selector */}
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Select Knowledge Graph Schema</label>
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
      
      {/* Connection status */}
      <div className="mb-4">
        <div className="flex items-center">
          <div className={`w-3 h-3 rounded-full mr-2 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className="text-sm">{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
        
        {connectionError && (
          <div className="mt-2 p-2 bg-destructive/10 border border-destructive/30 text-destructive text-sm rounded-md flex items-center">
            <AlertCircle className="h-4 w-4 mr-2" />
            {connectionError}
          </div>
        )}
      </div>
      
      {/* Input area with autocomplete */}
      <div className="relative">
        <label className="block text-sm font-medium mb-2">Type to test autocomplete</label>
        
        {/* Autocomplete suggestions */}
        <AutocompleteSuggestions
          suggestions={autocompleteSuggestions}
          visible={showAutocomplete}
          onSelect={handleSelectSuggestion}
          inputRef={inputRef}
        />
        
        <Textarea
          ref={inputRef}
          placeholder="Type to test autocomplete..."
          className="min-h-[120px] resize-none"
          value={input}
          onChange={handleInputChange}
          disabled={!sourceId || !isConnected}
        />
        
        <div className="mt-2 text-xs text-muted-foreground">
          <p>Cursor position: {cursorPosition}</p>
          <p>Connected to schema: {sourceId}</p>
          <p>Suggestions: {autocompleteSuggestions.length}</p>
        </div>
      </div>
      
      <div className="mt-4 text-sm">
        <h2 className="font-medium mb-2">Instructions:</h2>
        <ul className="list-disc pl-5 space-y-1">
          <li>Select a knowledge graph schema from the dropdown</li>
          <li>Type in the text area to see autocomplete suggestions</li>
          <li>Use arrow keys to navigate suggestions</li>
          <li>Press Tab or Enter to accept a suggestion</li>
          <li>Try typing "Show me all" to see node label suggestions</li>
          <li>Try typing a node label to see property suggestions</li>
        </ul>
      </div>
    </div>
  )
}

"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send, Loader2 } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import { useKGInsights } from "../use-kg-insights"
import { AutocompleteSuggestion } from "../autocomplete-service"

interface InsightsChatInputProps {
  onSendMessage: (message: string) => Promise<void>
  loading: boolean
  sourceId: string
  token: string
}

export function InsightsChatInput({ 
  onSendMessage, 
  loading,
  sourceId,
  token
}: InsightsChatInputProps) {
  const [message, setMessage] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { toast } = useToast()
  
  // State for suggestions and autocomplete
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [showAutocomplete, setShowAutocomplete] = useState(false)
  
  // Use our KG Insights hook
  const {
    connected,
    suggestions,
    autocompleteSuggestions,
    getSuggestions,
    getAutocompleteSuggestions
  } = useKGInsights(sourceId, token, {
    suggestionOptions: {
      maxSuggestions: 5,
      debounceTime: 300
    },
    autocompleteOptions: {
      maxSuggestions: 5,
      debounceTime: 150
    }
  })
  
  // Handle auto-resize of textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = "auto"
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [message])
  
  // Handle sending message
  const handleSendMessage = async () => {
    if (!message.trim() || loading) return
    
    try {
      await onSendMessage(message)
      setMessage("")
    } catch (error) {
      console.error("Error sending message:", error)
      toast({
        title: "Error",
        description: "Failed to send message. Please try again.",
        variant: "destructive",
      })
    }
  }
  
  // Handle input changes with suggestions and autocomplete
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    setMessage(value)
    
    // Auto-resize the textarea
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = "auto"
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
    
    // Get cursor position
    const cursorPosition = e.target.selectionStart || value.length
    
    // Get suggestions if the input is not empty
    if (value.trim()) {
      getSuggestions(value, cursorPosition)
      getAutocompleteSuggestions(value, cursorPosition)
      setShowSuggestions(true)
      setShowAutocomplete(true)
    } else {
      setShowSuggestions(false)
      setShowAutocomplete(false)
    }
  }
  
  // Handle selecting a suggestion
  const handleSelectSuggestion = (suggestion: string) => {
    setMessage(suggestion)
    setShowSuggestions(false)
    setShowAutocomplete(false)
    textareaRef.current?.focus()
  }
  
  // Handle selecting an autocomplete suggestion
  const handleSelectAutocompleteSuggestion = (suggestion: AutocompleteSuggestion) => {
    setMessage(suggestion.text)
    setShowSuggestions(false)
    setShowAutocomplete(false)
    textareaRef.current?.focus()
  }
  
  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    } else if (e.key === "Escape") {
      setShowSuggestions(false)
      setShowAutocomplete(false)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Suggestions */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="border border-border rounded-md mb-2 overflow-hidden">
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
        <div className="border border-border rounded-md mb-2 overflow-hidden">
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
      
      <div className="flex items-end gap-2">
        <div className="relative flex-grow">
          <div className="absolute right-3 bottom-3 text-xs text-muted-foreground pointer-events-none bg-background/80 px-1 rounded">
            Shift+Enter for new line
          </div>
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your knowledge graph..."
            className="flex-grow resize-none min-h-[60px] max-h-[200px] overflow-y-auto"
            disabled={loading}
          />
        </div>
        <Button
          className="flex-shrink-0"
          onClick={handleSendMessage}
          disabled={!message.trim() || loading}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          <span className="ml-2 hidden md:inline">Send</span>
        </Button>
      </div>
    </div>
  )
}

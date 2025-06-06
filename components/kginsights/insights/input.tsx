"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ChevronLeft, ChevronRight, Loader2, Send, Trash2 } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import { useKGInsights } from "../use-kg-insights"
import { AutocompleteSuggestion } from "../autocomplete-service"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface InsightsChatInputProps {
  onSendMessage: (message: string) => void
  loading: boolean
  sourceId: string
  token: string
  onClearChat?: () => void
  sidebarToggle?: {
    isOpen: boolean
    onToggle: () => void
  }
}

export function InsightsChatInput({ 
  onSendMessage, 
  loading,
  sourceId,
  token,
  onClearChat,
  sidebarToggle
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
        <div className="border border-border rounded-xl shadow-sm mb-2 overflow-hidden bg-card/95 backdrop-blur-sm">
          <div className="p-3 bg-secondary/50 text-secondary-foreground text-xs font-medium">
            Suggested Queries
          </div>
          <div className="divide-y divide-border/50">
            {suggestions.map((suggestion, index) => (
              <div 
                key={index}
                className="p-3 hover:bg-primary/10 cursor-pointer text-sm transition-colors duration-200"
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
        <div className="border border-border rounded-xl shadow-sm mb-2 overflow-hidden bg-card/95 backdrop-blur-sm">
          <div className="p-3 bg-secondary/50 text-secondary-foreground text-xs font-medium">
            Autocomplete
          </div>
          <div className="divide-y divide-border/50">
            {autocompleteSuggestions.map((suggestion, index) => (
              <div 
                key={index}
                className="p-3 hover:bg-primary/10 cursor-pointer transition-colors duration-200"
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
      
      <div className="relative">
        <div className="relative">
          <div className="absolute left-3 bottom-3 text-xs text-muted-foreground pointer-events-none bg-card/80 px-2 py-1 rounded-md z-10">
            Shift+Enter for new line
          </div>
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your factory performance..."
            className="w-full resize-none min-h-[60px] max-h-[200px] overflow-y-auto rounded-2xl border-primary/20 shadow-sm focus-visible:ring-primary bg-card/50 backdrop-blur-sm px-4 py-3 pr-[120px] transition-all duration-300"
            disabled={loading}
          />
        </div>
        <div className="absolute right-2 bottom-2 flex items-center gap-2">
          {onClearChat && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    onClick={onClearChat}
                    size="icon" 
                    variant="ghost"
                    className="flex-shrink-0 rounded-full h-10 w-10 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all duration-300"
                  >
                    <Trash2 className="h-5 w-5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Clear chat</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          <Button
            className="flex-shrink-0 rounded-full h-10 w-10 p-0"
            onClick={handleSendMessage}
            disabled={!message.trim() || loading}
            variant="default"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </Button>
          {sidebarToggle && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="flex-shrink-0 rounded-full h-10 w-10 p-0 text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors duration-300"
                    onClick={sidebarToggle.onToggle}
                  >
                    {sidebarToggle.isOpen ? (
                      <ChevronRight className="h-5 w-5" />
                    ) : (
                      <ChevronLeft className="h-5 w-5" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{sidebarToggle.isOpen ? "Hide sidebar" : "Show sidebar"}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      </div>
    </div>
  )
}

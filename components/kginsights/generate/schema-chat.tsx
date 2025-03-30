"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send, Loader2, BotMessageSquare, User } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

// Message type for chat history
export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  timestamp: Date
  metadata?: {
    schema?: any
    cypher?: string
  }
}

interface SchemaChatProps {
  selectedSource: string
  selectedSourceName: string
  onSchemaGenerated: (schema: any, cypher: string) => void
  loading: boolean
  setLoading: (loading: boolean) => void
}

export function SchemaChat({ 
  selectedSource, 
  selectedSourceName,
  onSchemaGenerated,
  loading,
  setLoading
}: SchemaChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [message, setMessage] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const { toast } = useToast()
  
  // Initialize component
  useEffect(() => {
    // Initialize with a welcome message if messages is empty
    if (messages.length === 0) {
      setMessages([
        {
          id: "welcome",
          role: "assistant",
          content: "How can I help with your schema design?",
          timestamp: new Date(),
        }
      ])
    }
  }, [])

  // Scroll to bottom of messages when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Handle auto-resize of textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = "auto"
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [message])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }
  
  // Format timestamps
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  // Handle sending message
  const handleSendMessage = async () => {
    if (!message.trim() || loading) return
    
    if (!selectedSource) {
      toast({
        title: "Error",
        description: "Please select a data source first",
        variant: "destructive",
      })
      return
    }

    // Create a new user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: message,
      timestamp: new Date()
    }
    
    // Update messages with user message
    setMessages((prevMessages) => [...prevMessages, userMessage])
    
    // Clear the input
    setMessage("")
    
    // Show loading state
    setLoading(true)
    
    try {
      // Send request to API
      const response = await fetch("/api/graphschema/build-schema-from-source", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          source_id: selectedSource,
          metadata: message
        }),
      })
      
      if (!response.ok) {
        throw new Error(`Failed to generate schema: ${response.status}`)
      }
      
      const data = await response.json()
      
      // Create assistant message from response
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: `Based on your data, I recommend a schema for ${selectedSourceName}. You can see the visualization and details on the right.`,
        timestamp: new Date(),
        metadata: {
          schema: data.schema,
          cypher: data.cypher
        }
      }
      
      // Update messages with assistant response
      setMessages((prevMessages) => [...prevMessages, assistantMessage])
      
      // Call the callback to update the parent component
      onSchemaGenerated(data.schema, data.cypher)
      
      toast({
        title: "Success",
        description: "Schema generated successfully!",
      })
    } catch (error) {
      console.error("Error generating schema:", error)
      
      // Add error message
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "system",
        content: "Sorry, I encountered an error generating the schema. Please try again.",
        timestamp: new Date(),
      }
      
      setMessages((prevMessages) => [...prevMessages, errorMessage])
      
      toast({
        title: "Error",
        description: "Failed to generate schema. Please try again.",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }
  
  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Chat messages */}
      <ScrollArea className="flex-grow pr-4">
        <div className="space-y-4 p-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex flex-col",
                message.role === "user" ? "items-end" : "items-start"
              )}
            >
              <div className="flex items-end gap-2">
                {message.role !== "user" && (
                  <div className="rounded-full bg-primary/10 p-2 flex items-center justify-center">
                    {message.role === "assistant" ? (
                      <BotMessageSquare className="h-4 w-4 text-primary" />
                    ) : (
                      <BotMessageSquare className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                )}
                
                <Card
                  className={cn(
                    "px-4 py-3 max-w-[80%]",
                    message.role === "user" 
                      ? "bg-primary text-primary-foreground" 
                      : message.role === "system"
                      ? "bg-secondary/50"
                      : "bg-card"
                  )}
                >
                  <div className="space-y-2">
                    <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                      {message.content}
                    </div>
                  </div>
                </Card>
                
                {message.role === "user" && (
                  <div className="rounded-full bg-primary p-2 flex items-center justify-center">
                    <User className="h-4 w-4 text-primary-foreground" />
                  </div>
                )}
              </div>
              
              <span className="text-xs text-muted-foreground mt-1 px-2">
                {formatTime(message.timestamp)}
              </span>
            </div>
          ))}
          
          {/* Loading indicator */}
          {loading && (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          )}
          
          {/* Reference for auto-scrolling */}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
      
      {/* Chat input */}
      <div className="p-4 border-t">
        <div className="flex items-end gap-2">
          <Textarea
            id="schema-chat-input"
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about schema..."
            className="flex-grow resize-none min-h-[60px] max-h-[200px] overflow-y-auto"
            disabled={loading || !selectedSource}
          />
          <Button
            className="flex-shrink-0"
            onClick={handleSendMessage}
            disabled={!message.trim() || loading || !selectedSource}
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span className="ml-2 hidden md:inline">Generate</span>
          </Button>
        </div>
      </div>
    </div>
  )
}

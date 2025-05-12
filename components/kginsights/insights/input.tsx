"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send, Loader2 } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
// No need for external AI completion library

interface InsightsChatInputProps {
  onSendMessage: (message: string) => Promise<void>
  loading: boolean
  sourceId: string
}

export function InsightsChatInput({ 
  onSendMessage, 
  loading,
  sourceId
}: InsightsChatInputProps) {
  const [message, setMessage] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { toast } = useToast()
  
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
  
  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="flex items-end gap-2">
      <div className="relative flex-grow">
        <div className="absolute right-3 bottom-3 text-xs text-muted-foreground pointer-events-none bg-background/80 px-1 rounded">
          Shift+Enter for new line
        </div>
        <Textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
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
  )
}

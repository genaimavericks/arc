"use client"

import { useState, useRef, useEffect } from 'react'
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { Bot, Loader2, Send, Wand2, Plus, Minus, Edit } from "lucide-react"

// Define the message type
export type Message = {
  id?: string
  role: string
  content: string
  timestamp: Date
  metadata?: any
}

// Define step type for rendering
type TransformationStep = {
  order: number
  operation: string
  description: string
  parameters: Record<string, any>
}

interface TransformationChatProps {
  onCreatePlan?: (finalInstructions: string) => void
  onInstructionsUpdate?: (instructions: string) => void
  initialInstructions?: string
  isCreatingPlan?: boolean
  className?: string
  profileSessionId?: string
  planId?: string
  sourceId?: string
}

export function TransformationChat({
  onCreatePlan,
  onInstructionsUpdate,
  initialInstructions = '',
  isCreatingPlan = false,
  className,
  profileSessionId,
  planId,
  sourceId
}: TransformationChatProps) {
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'system',
      content: 'Welcome to the AI Transformation assistant. I\'ll help you create a transformation plan for your data. Describe what transformations you need, and when you\'re ready, click "Create Plan".',
      timestamp: new Date()
    }
  ])
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Add initial instructions as a message if provided
  useEffect(() => {
    if (initialInstructions && messages.length === 1) {
      setMessages(prev => [
        ...prev,
        {
          role: 'user',
          content: initialInstructions,
          timestamp: new Date()
        },
        {
          role: 'assistant',
          content: 'I\'ve noted your instructions. Please provide any additional details about how you want to transform your data, or click "Create Plan" to proceed with these instructions.',
          timestamp: new Date()
        }
      ])
    }
  }, [initialInstructions])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Handle send message
  const handleSendMessage = async () => {
    if (!input.trim()) return
    
    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsSending(true)
    
    try {
      // Get auth token from localStorage
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('Authentication token not found')
      }
      
      // Prepare request payload
      const payload = {
        content: input,
        role: 'user'
      }
      
      // Add either planId or profileSessionId
      if (planId) {
        Object.assign(payload, { plan_id: planId })
      } else if (profileSessionId) {
        Object.assign(payload, { profile_session_id: profileSessionId })
      }
      
      // Make API request
      const response = await fetch('/api/datapuur-ai/transformation-messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }
      
      const data = await response.json()
      
      // Add assistant response to messages
      console.log('API Response:', data);
      console.log('Message metadata:', data.message.metadata);
      
      const assistantMessage: Message = {
        id: data.message.id,
        role: 'assistant',
        content: data.message.content,
        timestamp: new Date(data.message.timestamp),
        metadata: data.message.metadata
      }
      
      console.log('Assistant message with metadata:', assistantMessage);
      
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      
      // Add error message
      setMessages(prev => [
        ...prev,
        {
          role: 'system',
          content: 'Failed to send message. Please try again.',
          timestamp: new Date()
        }
      ])
    } finally {
      setIsSending(false)
    }
  }

  // Handle enter press to send message
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Handle create plan
  const handleCreatePlan = () => {
    // Collect all user messages to form the final instructions
    const userInstructions = messages
      .filter(msg => msg.role === 'user')
      .map(msg => msg.content)
      .join('\n\n')
    
    // Add a final system message summarizing the plan
    setMessages(prev => [
      ...prev,
      {
        role: 'system',
        content: 'Creating transformation plan based on provided instructions...',
        timestamp: new Date()
      }
    ])
    
    // Call the parent handlers with the compiled instructions
    if (onCreatePlan) {
      onCreatePlan(userInstructions)
    }
    
    // Also update instructions for the create tab if the callback exists
    if (onInstructionsUpdate) {
      onInstructionsUpdate(userInstructions)
    }
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      <ScrollArea className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-4">
          {messages.map((message, index) => (
            <div 
              key={index}
              className={cn(
                "flex items-start gap-3 rounded-lg p-3",
                message.role === 'user' 
                  ? "bg-muted/50 ml-auto max-w-[80%]" 
                  : message.role === 'system' 
                    ? "bg-secondary/20 max-w-[90%]"
                    : "bg-primary/10 max-w-[80%]"
              )}
            >
              {message.role !== 'user' && (
                <Avatar className="h-8 w-8">
                  <AvatarFallback>AI</AvatarFallback>
                  <AvatarFallback className="bg-primary/10">
                    <Bot className="h-4 w-4 text-primary" />
                  </AvatarFallback>
                </Avatar>
              )}
              <div className="flex flex-col gap-1">
                <div className="text-sm">{message.content}</div>
                
                {/* Display plan changes if they exist in message metadata */}
                {message.role === 'assistant' && message.metadata && message.metadata.changes && (
                  <div className="mt-3">
                    <h4 className="text-sm font-medium mb-2">Plan Changes:</h4>
                    
                    {/* Added steps */}
                    {message.metadata.changes.added && message.metadata.changes.added.length > 0 ? (
                      <div className="mb-2">
                        <h5 className="text-xs font-medium flex items-center gap-1">
                          <Plus className="h-3 w-3 text-green-500" /> Added Steps:
                        </h5>
                        <div className="space-y-1 mt-1">
                          {message.metadata.changes.added.map((step: TransformationStep, idx: number) => (
                            <Card key={`added-${idx}`} className="p-2 bg-green-50 border-green-200 text-xs">
                              <div className="flex justify-between">
                                <Badge variant="outline" className="bg-green-100 text-green-800">
                                  Step {step.order}
                                </Badge>
                                <Badge variant="secondary">{step.operation}</Badge>
                              </div>
                              <div className="mt-1">{step.description}</div>
                            </Card>
                          ))}
                        </div>
                      </div>
                    ) : null}
                    
                    {/* Modified steps */}
                    {message.metadata.changes.modified && message.metadata.changes.modified.length > 0 ? (
                      <div className="mb-2">
                        <h5 className="text-xs font-medium flex items-center gap-1">
                          <Edit className="h-3 w-3 text-blue-500" /> Modified Steps:
                        </h5>
                        <div className="space-y-1 mt-1">
                          {message.metadata.changes.modified.map((change: {previous: TransformationStep, current: TransformationStep}, idx: number) => (
                            <Card key={`modified-${idx}`} className="p-2 bg-blue-50 border-blue-200 text-xs">
                              <div className="flex justify-between">
                                <Badge variant="outline" className="bg-blue-100 text-blue-800">
                                  Step {change.current.order}
                                </Badge>
                                <Badge variant="secondary">{change.current.operation}</Badge>
                              </div>
                              <div className="mt-1 flex flex-col gap-1">
                                <div className="line-through text-gray-500">{change.previous.description}</div>
                                <div className="text-blue-700">{change.current.description}</div>
                              </div>
                            </Card>
                          ))}
                        </div>
                      </div>
                    ) : null}
                    
                    {/* Removed steps */}
                    {message.metadata.changes.removed && message.metadata.changes.removed.length > 0 ? (
                      <div className="mb-2">
                        <h5 className="text-xs font-medium flex items-center gap-1">
                          <Minus className="h-3 w-3 text-red-500" /> Removed Steps:
                        </h5>
                        <div className="space-y-1 mt-1">
                          {message.metadata.changes.removed.map((step: TransformationStep, idx: number) => (
                            <Card key={`removed-${idx}`} className="p-2 bg-red-50 border-red-200 text-xs line-through">
                              <div className="flex justify-between">
                                <Badge variant="outline" className="bg-red-100 text-red-800">
                                  Step {step.order}
                                </Badge>
                                <Badge variant="secondary">{step.operation}</Badge>
                              </div>
                              <div className="mt-1">{step.description}</div>
                            </Card>
                          ))}
                        </div>
                      </div>
                    ) : null}
                    
                    {/* Show a message if no changes were detected */}
                    {(!message.metadata.changes.added || message.metadata.changes.added.length === 0) && 
                     (!message.metadata.changes.modified || message.metadata.changes.modified.length === 0) && 
                     (!message.metadata.changes.removed || message.metadata.changes.removed.length === 0) && (
                      <div className="text-xs text-muted-foreground">
                        No changes detected in the transformation plan.
                      </div>
                    )}
                  </div>
                )}
                
                <div className="text-xs text-muted-foreground">
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
      
      <div className="border-t p-4 flex flex-col gap-3">
        <Textarea
          ref={textareaRef}
          placeholder="Type your transformation instructions..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="min-h-[80px]"
          disabled={isSending || isCreatingPlan}
        />
        <div className="flex justify-end">
          <Button
            onClick={handleSendMessage}
            disabled={!input.trim() || isSending || isCreatingPlan}
            variant="secondary"
          >
            {isSending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Updating...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" /> Update Plan
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}

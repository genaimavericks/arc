"use client"

import React, { useState, useEffect, useRef } from "react"
import { X, Minimize2, Maximize2, Send, Bot, MessageSquare, ChevronLeft, ChevronRight, Sparkles, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { useDjinni } from "@/lib/djinni-context"
import { motion, AnimatePresence } from "framer-motion"

interface Message {
  id: string
  content: string
  sender: "user" | "assistant"
  timestamp: Date
  isLoading?: boolean
}

export function DjinniChatColumn() {
  const { isOpen, setIsOpen, isCollapsed, setIsCollapsed, width, setWidth } = useDjinni()
  const [isMinimized, setIsMinimized] = useState(false)
  const [inputMessage, setInputMessage] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const [isResizing, setIsResizing] = useState(false)
  const resizeRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content: "Hello! I'm Djinni, your AI assistant. How can I help you today?",
      sender: "assistant",
      timestamp: new Date()
    }
  ])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Handle resize functionality
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return
      
      // Use requestAnimationFrame for smoother resizing
      requestAnimationFrame(() => {
        // Calculate new width based on mouse position
        // We're resizing from right to left, so we subtract the mouse X position from the window width
        // Limit maximum width to 80% of viewport width to prevent overflow issues
        const maxWidth = Math.min(600, window.innerWidth * 0.8)
        const newWidth = Math.max(280, Math.min(maxWidth, window.innerWidth - e.clientX))
        setWidth(newWidth)
      })
    }

    const handleMouseUp = () => {
      setIsResizing(false)
      document.body.style.cursor = 'default'
      document.body.style.userSelect = 'auto'
      document.body.style.pointerEvents = 'auto'
    }

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ew-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'default'
      document.body.style.userSelect = 'auto'
    }
  }, [isResizing])
  
  // Width is now managed by the context

  const toggleOpen = () => {
    setIsOpen(!isOpen)
    setIsMinimized(false)
  }

  const toggleMinimize = () => {
    setIsMinimized(!isMinimized)
  }
  
  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed)
    // Dispatch a custom event to notify other components about the change
    window.dispatchEvent(new Event('djinniStateChange'))
  }

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!inputMessage.trim()) return
    
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage,
      sender: "user",
      timestamp: new Date()
    }
    
    setMessages([...messages, userMessage])
    setInputMessage("")
    setIsTyping(true)
    
    // Simulate assistant response
    setTimeout(() => {
      setIsTyping(false)
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "I'm analyzing your request. This is a placeholder response as the actual AI integration will be implemented in the future.",
        sender: "assistant",
        timestamp: new Date()
      }
      setMessages(prev => [...prev, assistantMessage])
    }, 1500)
  }

  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsResizing(true)
    // Set a high priority event capture to ensure smooth dragging
    document.body.style.pointerEvents = 'none'
  }

  return (
    <div className="fixed right-0 top-0 bottom-0 z-[100] flex flex-col items-end pointer-events-none h-full">
      {/* Collapse/Expand Button */}
      <AnimatePresence>
        {!isCollapsed && (
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.2 }}
            className="absolute left-[-40px] top-1/2 transform -translate-y-1/2 z-50 flex items-center pointer-events-auto"
          >
            <button
              onClick={toggleCollapse}
              className="relative bg-primary text-primary-foreground rounded-l-lg p-3 shadow-xl hover:bg-primary/90 transition-all h-20 w-12 flex items-center justify-center border-l border-t border-b border-primary/40"
              aria-label="Collapse chat"
            >
              <div className="flex flex-col items-center justify-center gap-2">
                <ChevronRight size={24} />
                <span className="text-xs font-medium rotate-90">Djinni</span>
              </div>
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Collapsed State Indicator */}
      <AnimatePresence>
        {isCollapsed && (
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="absolute left-[-40px] top-1/2 transform -translate-y-1/2 z-50 flex items-center pointer-events-auto"
          >
            <button
              onClick={toggleCollapse}
              className="relative bg-primary text-primary-foreground rounded-l-lg p-3 shadow-xl hover:bg-primary/90 transition-all h-20 w-12 flex items-center justify-center border-l border-t border-b border-primary/40 group"
              aria-label="Expand chat"
            >
              <div className="absolute inset-0 bg-primary/20 rounded-l-lg animate-pulse group-hover:animate-none"></div>
              <div className="flex flex-col items-center justify-center gap-2 relative z-10">
                <ChevronLeft size={24} />
                <span className="text-xs font-medium rotate-90">Djinni</span>
              </div>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Chat Column */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ 
              width: isCollapsed ? 0 : width, 
              opacity: isCollapsed ? 0 : 1,
              height: isMinimized ? 'auto' : '100%',
              right: 0
            }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: isResizing ? 0 : 0.3, ease: "easeInOut" }}
            style={{
              width: isCollapsed ? 0 : `${width}px`,
              transition: isResizing ? 'none' : undefined
            }}
            className="h-full pointer-events-auto relative overflow-visible"
          >
            {/* Resize handle */}
            <div 
              ref={resizeRef}
              className="absolute left-0 top-0 bottom-0 w-4 cursor-ew-resize z-50 group"
              onMouseDown={handleResizeStart}
              style={{ left: '-4px' }}
            >
              <div className="h-full w-1 bg-transparent group-hover:bg-primary/50 transition-colors duration-200 absolute right-0"></div>
            </div>
            <Card className={cn(
              "h-full border-l border-border shadow-xl flex flex-col overflow-hidden",
              isMinimized ? "h-auto rounded-b-xl" : "h-full rounded-none",
              "bg-background/95 backdrop-blur-sm",
              "absolute right-0 top-0 bottom-0 w-full"
            )}>
              {/* Header */}
              <CardHeader className="p-4 py-5 border-b flex flex-row items-center justify-between space-y-0 bg-primary/10 backdrop-blur-sm">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <Bot className="h-7 w-7 text-primary" />
                    <span className="absolute -top-1 -right-1 h-3 w-3 bg-green-500 rounded-full border-2 border-background"></span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-base flex items-center gap-2">
                      Djinni Assistant
                      <Sparkles className="h-4 w-4 text-amber-500" />
                    </h3>
                    <p className="text-sm text-muted-foreground">AI-powered insights & assistance</p>
                  </div>
                </div>
                {/* Header buttons removed as requested */}
              </CardHeader>

              {/* Chat Content */}
              {!isMinimized && (
                <>
                  <CardContent className="flex-1 overflow-y-auto p-4 space-y-5 bg-card/50 scrollbar-thin scrollbar-thumb-primary/20 scrollbar-track-transparent">
                    {messages.map((message) => (
                      <motion.div 
                        key={message.id} 
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                        className={cn(
                          "flex flex-col max-w-[85%] space-y-1",
                          message.sender === "user" ? "ml-auto items-end" : "mr-auto items-start"
                        )}
                      >
                        <div className={cn(
                          "rounded-2xl px-4 py-2.5 text-sm shadow-sm",
                          message.sender === "user" 
                            ? "bg-primary text-primary-foreground rounded-tr-none" 
                            : "bg-muted/80 backdrop-blur-sm rounded-tl-none border border-border/30"
                        )}>
                          {message.content}
                        </div>
                        <span className="text-xs text-muted-foreground px-1">
                          {message.timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </span>
                      </motion.div>
                    ))}

                    {/* Typing indicator */}
                    {isTyping && (
                      <motion.div 
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex flex-col max-w-[85%] mr-auto items-start space-y-1"
                      >
                        <div className="rounded-2xl rounded-tl-none px-4 py-3 text-sm bg-muted/80 backdrop-blur-sm border border-border/30 shadow-sm flex items-center gap-2">
                          <div className="flex space-x-1">
                            <span className="h-2 w-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                            <span className="h-2 w-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                            <span className="h-2 w-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                          </div>
                          <span className="text-xs text-muted-foreground">Djinni is thinking...</span>
                        </div>
                      </motion.div>
                    )}

                    {/* Invisible element to scroll to */}
                    <div ref={messagesEndRef} />
                  </CardContent>

                  {/* Input Area */}
                  <CardFooter className="p-3 border-t bg-card/80 backdrop-blur-sm">
                    <form onSubmit={handleSendMessage} className="flex w-full gap-2 items-center">
                      <Input
                        type="text"
                        placeholder="Ask Djinni something..."
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        className="flex-1 bg-background/50 border-primary/20 focus-visible:ring-primary/30 rounded-full py-5 px-4"
                      />
                      <Button 
                        type="submit" 
                        size="icon" 
                        className="h-10 w-10 rounded-full bg-primary hover:bg-primary/90 shadow-md"
                        disabled={!inputMessage.trim() || isTyping}
                      >
                        {isTyping ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                      </Button>
                    </form>
                  </CardFooter>
                </>
              )}
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toggle Button */}
      <AnimatePresence>
        {!isOpen && (
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 500, damping: 30 }}
            className={cn(
              "fixed bottom-4 transition-all duration-300",
              isCollapsed ? "right-4" : "right-20"
            )}
          >
            <Button 
              onClick={toggleOpen}
              className="h-14 w-14 rounded-full shadow-lg bg-primary hover:bg-primary/90 flex items-center justify-center group"
            >
              <div className="absolute inset-0 bg-primary/20 rounded-full animate-ping opacity-75 group-hover:animate-none"></div>
              <MessageSquare className="h-6 w-6 relative z-10" />
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

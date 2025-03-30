"use client"

import { ScrollArea } from "@/components/ui/scroll-area"
import { Card } from "@/components/ui/card"
import { ChatMessage } from "../insights-chat"
import { Loader2, User, BotMessageSquare } from "lucide-react"
import { cn } from "@/lib/utils"
// Use simple text rendering instead of ReactMarkdown
import { useState } from "react"
import { GraphVisualization } from "./graph-visualization"
import { ChartVisualization } from "./chart-visualization"
import { ChartTheme } from "./chart-visualization"

interface InsightsChatMessagesProps {
  messages: ChatMessage[]
  loading: boolean
  messagesEndRef: React.RefObject<HTMLDivElement | null>
  chartTheme?: ChartTheme
}

export function InsightsChatMessages({ 
  messages, 
  loading, 
  messagesEndRef,
  chartTheme
}: InsightsChatMessagesProps) {
  
  // Function to format timestamps
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <ScrollArea className="h-full pr-4">
      <div className="space-y-4 p-4">
        {messages.filter(message => message && typeof message === 'object' && message.role).map((message) => (
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
                  
                  {/* Render graphs, tables, or other visualizations based on metadata */}
                  {message.metadata?.type === "graph" && message.metadata.data && (
                    <div className="mt-3">
                      <GraphVisualization 
                        data={message.metadata.data}
                        title="Knowledge Graph Visualization"
                      />
                    </div>
                  )}
                  
                  {/* Display chart visualization if available */}
                  {message.visualization && message.visualization.type !== "none" && (
                    <div className="mt-3">
                      <ChartVisualization 
                        data={message.visualization}
                        chartType={message.visualization.type}
                        title={message.visualization.title}
                        description={message.visualization.description}
                        theme={chartTheme}
                      />
                    </div>
                  )}
                  
                  {message.metadata?.type === "table" && message.metadata.data && (
                    <div className="border rounded p-2 mt-3 bg-background">
                      <p className="text-xs font-medium mb-1">Data Table</p>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm border-collapse">
                          {message.metadata.data.headers && (
                            <thead>
                              <tr className="bg-muted">
                                {message.metadata.data.headers.map((header: string, index: number) => (
                                  <th key={index} className="p-2 text-left border">{header}</th>
                                ))}
                              </tr>
                            </thead>
                          )}
                          <tbody>
                            {message.metadata.data.rows?.map((row: any[], rowIndex: number) => (
                              <tr key={rowIndex} className="even:bg-muted/30">
                                {row.map((cell, cellIndex) => (
                                  <td key={cellIndex} className="p-2 border">{String(cell)}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                  
                  <div className="text-xs opacity-70 text-right">
                    {formatTime(message.timestamp)}
                  </div>
                </div>
              </Card>
              
              {message.role === "user" && (
                <div className="rounded-full bg-primary p-2 flex items-center justify-center">
                  <User className="h-4 w-4 text-primary-foreground" />
                </div>
              )}
            </div>
          </div>
        ))}
        
        {/* Loading indicator */}
        {loading && (
          <div className="flex items-center gap-2">
            <div className="rounded-full bg-primary/10 p-2 flex items-center justify-center">
              <BotMessageSquare className="h-4 w-4 text-primary" />
            </div>
            <Card className="px-4 py-3">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Thinking...</span>
              </div>
            </Card>
          </div>
        )}
        
        {/* Empty div for scrolling to bottom */}
        <div ref={messagesEndRef} />
      </div>
    </ScrollArea>
  )
}

"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { PlusCircle, MinusCircle, Info } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"

interface ContextProviderProps {
  onApplyContext: (context: string) => void
}

export function ContextProvider({ onApplyContext }: ContextProviderProps) {
  const [context, setContext] = useState("")
  const [expanded, setExpanded] = useState(false)

  const handleApplyContext = () => {
    if (context.trim()) {
      onApplyContext(context)
    }
  }

  return (
    <Card className="w-full shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <div>
            <CardTitle className="text-sm font-medium flex items-center">
              <Info className="h-4 w-4 mr-2 text-muted-foreground" />
              Knowledge Context
            </CardTitle>
            {expanded && (
              <CardDescription className="text-xs mt-1">
                Provide additional context to improve query results
              </CardDescription>
            )}
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-8 w-8 p-0"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <MinusCircle className="h-4 w-4" />
            ) : (
              <PlusCircle className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="pt-0">
          <ScrollArea className="max-h-60">
            <Textarea
              placeholder="Enter additional context about your knowledge graph to improve query results..."
              value={context}
              onChange={(e) => setContext(e.target.value)}
              className="min-h-20 text-sm"
            />
          </ScrollArea>
          <div className="flex justify-end mt-2">
            <Button 
              size="sm" 
              onClick={handleApplyContext}
              disabled={!context.trim()}
            >
              Apply Context
            </Button>
          </div>
        </CardContent>
      )}
    </Card>
  )
}

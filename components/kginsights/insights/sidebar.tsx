"use client"

import { useState } from "react"
import { PredefinedQuery } from "../insights-chat"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  ChevronRight, 
  Search, 
  Tag,
  Sparkles
} from "lucide-react"
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface InsightsChatSidebarProps {
  predefinedQueries: PredefinedQuery[]
  onSelectQuery: (query: string) => void
}

export function InsightsChatSidebar({ 
  predefinedQueries, 
  onSelectQuery
}: InsightsChatSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  
  // Get unique categories from predefined queries
  const categories = Array.from(
    new Set(predefinedQueries.map((q) => q.category))
  ).sort()
  
  // Filter queries based on search and selected category
  const filteredQueries = predefinedQueries.filter((query) => {
    const matchesSearch = 
      !searchQuery || 
      query.query.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (query.description && query.description.toLowerCase().includes(searchQuery.toLowerCase()))
    
    const matchesCategory = !selectedCategory || query.category === selectedCategory
    
    return matchesSearch && matchesCategory
  })
  
  return (
    <div className="h-full flex flex-col">
      <div className="space-y-2 mb-2">
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search suggestions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
        
        <Select 
          value={selectedCategory || "all"} 
          onValueChange={(value) => setSelectedCategory(value === "all" ? null : value)}
        >
          <SelectTrigger>
            <div className="flex items-center">
              <Tag className="mr-2 h-4 w-4" />
              <SelectValue placeholder="All categories" />
            </div>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {categories.map((category) => (
              <SelectItem key={category} value={category}>
                {category.charAt(0).toUpperCase() + category.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      
      <div className="text-sm font-medium mb-1">Suggested Queries</div>
      
      <ScrollArea className="flex-grow">
        <div className="space-y-2 pr-2">
          {filteredQueries.length === 0 ? (
            <div className="text-center py-4 text-muted-foreground text-sm">
              No suggestions found
            </div>
          ) : (
            filteredQueries.map((query) => (
              <Button
                key={query.id}
                variant="outline"
                className="w-full justify-start text-left h-auto py-3 px-3"
                onClick={() => onSelectQuery(query.query)}
              >
                <div>
                  <div className="flex items-start">
                    <Sparkles className="h-4 w-4 mr-2 mt-0.5 text-primary" />
                    <div className="flex-grow">
                      <div className="font-medium">{query.query}</div>
                      {query.description && (
                        <div className="text-xs text-muted-foreground mt-1">
                          {query.description}
                        </div>
                      )}
                      <div className="text-xs mt-1">
                        <span className="inline-flex items-center rounded-full bg-secondary/50 px-2 py-0.5 text-xs">
                          {query.category}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </Button>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  )
}

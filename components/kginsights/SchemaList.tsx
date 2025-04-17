"use client"

import { useState } from "react"
import { useSchemaSelection } from "@/lib/schema-selection-context"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { motion } from "framer-motion"
import { Search, FileJson, RefreshCcw } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

export default function SchemaList() {
  const { schemas, selectedSchemaId, selectSchema, refreshSchemas, isLoading } = useSchemaSelection()
  const [searchTerm, setSearchTerm] = useState("")
  
  // Filter schemas based on search term
  const filteredSchemas = schemas.filter(schema => 
    schema.name.toLowerCase().includes(searchTerm.toLowerCase())
  )
  
  // Animation variants
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.05,
        delayChildren: 0.1,
      },
    },
  }
  
  const item = {
    hidden: { opacity: 0, y: 8 },
    show: { 
      opacity: 1, 
      y: 0,
      transition: {
        type: "spring",
        stiffness: 260,
        damping: 20
      }
    },
  }
  
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center mb-4 gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <Input
            placeholder="Search schemas..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 h-10 transition-all"
          />
        </div>
        <Button
          size="icon"
          variant="outline"
          onClick={() => refreshSchemas()}
          disabled={isLoading}
          title="Refresh schemas"
          className="h-10 w-10 transition-all hover:bg-primary/10"
        >
          <RefreshCcw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>
      
      <ScrollArea className="flex-1 pr-2">
        {isLoading ? (
          <div className="space-y-4 p-1">
            {[...Array(3)].map((_, i) => (
              <Card key={i} className="overflow-hidden border border-muted/60">
                <CardHeader className="p-4 pb-2 space-y-2">
                  <Skeleton className="h-5 w-3/5" />
                  <Skeleton className="h-4 w-4/5" />
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <Skeleton className="h-4 w-2/5 mt-2" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : filteredSchemas.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground bg-slate-50 dark:bg-slate-900/40 rounded-lg border border-dashed">
            {searchTerm ? (
              <>
                <Search className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                <p className="text-sm font-medium">No schemas match your search</p>
                <p className="text-xs mt-1">Try different keywords or clear the search</p>
              </>
            ) : (
              <>
                <FileJson className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                <p className="text-sm font-medium">No schemas found</p>
                <p className="text-xs mt-1">Create a new schema to get started</p>
              </>
            )}
          </div>
        ) : (
          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="space-y-3 p-1"
          >
            {filteredSchemas.map((schema) => (
              <motion.div key={schema.id} variants={item} layout>
                <Card 
                  className={`cursor-pointer transition-all hover:border-primary/60 hover:shadow-sm ${
                    selectedSchemaId === schema.id 
                      ? "border-primary bg-primary/5 shadow-sm" 
                      : "border-border bg-card"
                  }`}
                  onClick={() => selectSchema(schema.id)}
                >
                  <CardHeader className="p-4 pb-2">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-base font-medium">{schema.name}</CardTitle>
                      <FileJson className={`h-4 w-4 ${selectedSchemaId === schema.id ? 'text-primary' : 'text-muted-foreground'}`} />
                    </div>
                    <CardDescription className="text-xs">
                      Created {formatDistanceToNow(new Date(schema.created_at), { addSuffix: true })}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-4 pt-0">
                    <div className="text-xs text-muted-foreground mt-2 font-mono truncate">
                      ID: {schema.id}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        )}
      </ScrollArea>
    </div>
  )
}

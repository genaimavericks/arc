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
      },
    },
  }
  
  const item = {
    hidden: { opacity: 0, y: 10 },
    show: { opacity: 1, y: 0 },
  }
  
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center mb-4 gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search schemas..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-8"
          />
        </div>
        <Button
          size="icon"
          variant="outline"
          onClick={() => refreshSchemas()}
          disabled={isLoading}
          title="Refresh schemas"
        >
          <RefreshCcw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>
      
      <ScrollArea className="flex-1">
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <Card key={i}>
                <CardHeader className="p-4 pb-2">
                  <Skeleton className="h-5 w-1/2" />
                  <Skeleton className="h-4 w-3/4" />
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <Skeleton className="h-4 w-1/3 mt-2" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : filteredSchemas.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            {searchTerm ? "No schemas match your search" : "No schemas found"}
          </div>
        ) : (
          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="space-y-4"
          >
            {filteredSchemas.map((schema) => (
              <motion.div key={schema.id} variants={item}>
                <Card 
                  className={`cursor-pointer transition-colors hover:border-primary ${
                    selectedSchemaId === schema.id 
                      ? "border-primary bg-primary/5" 
                      : ""
                  }`}
                  onClick={() => selectSchema(schema.id)}
                >
                  <CardHeader className="p-4 pb-2">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-base">{schema.name}</CardTitle>
                      <FileJson className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <CardDescription className="text-xs">
                      Created {formatDistanceToNow(new Date(schema.created_at), { addSuffix: true })}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-4 pt-0">
                    <div className="text-xs text-muted-foreground mt-2">
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

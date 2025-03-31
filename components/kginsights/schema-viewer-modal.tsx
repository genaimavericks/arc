"use client"

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { RefreshCw } from "lucide-react"
import { useState, useEffect } from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface SchemaViewerModalProps {
  isOpen: boolean
  onClose: () => void
  datasetId: string
  datasetName: string
}

interface SchemaField {
  name: string
  type: string
  nullable: boolean
  description?: string
}

interface SchemaNode {
  label: string
  properties: { [key: string]: string }
}

interface SchemaRelationship {
  startNode: string
  endNode: string
  type: string
  properties?: { [key: string]: string }
}

interface GraphSchema {
  nodes: SchemaNode[]
  relationships: SchemaRelationship[]
  indexes?: string[]
}

export function SchemaViewerModal({ isOpen, onClose, datasetId, datasetName }: SchemaViewerModalProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [schema, setSchema] = useState<SchemaField[]>([])
  const [graphSchema, setGraphSchema] = useState<GraphSchema | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("fields")

  useEffect(() => {
    if (isOpen) {
      fetchSchemaData()
    }
  }, [isOpen, datasetId])

  const fetchSchemaData = async () => {
    try {
      setIsLoading(true)
      setError(null)

      // First try to fetch from the schema database if it's a schema ID
      try {
        const schemaResponse = await fetch(`/api/graphschema/schemas/${datasetId}`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        })

        if (schemaResponse.ok) {
          const schemaData = await schemaResponse.json()
          
          if (schemaData && schemaData.schema) {
            // Parse the schema JSON if it's a string
            const parsedSchema = typeof schemaData.schema === 'string' 
              ? JSON.parse(schemaData.schema) 
              : schemaData.schema
            
            setGraphSchema(parsedSchema)
            setActiveTab("graph")
            setIsLoading(false)
            return
          }
        }
      } catch (error) {
        console.log("Not a graph schema, trying dataset schema endpoint")
      }

      // If not a graph schema, try the dataset schema endpoint
      const response = await fetch(`/api/datapuur/ingestion-schema/${datasetId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch schema data: ${response.status}`)
      }

      const data = await response.json()

      // Extract schema from the response
      if (data && data.fields) {
        setSchema(data.fields || [])
        setActiveTab("fields")
      } else if (data && data.schema && data.schema.fields) {
        // Alternative location where schema might be stored
        setSchema(data.schema.fields || [])
        setActiveTab("fields")
      } else {
        // If no schema is found, set an empty array
        setSchema([])
      }
    } catch (error) {
      console.error("Error fetching schema data:", error)
      setError("Failed to load schema data. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const getTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case "string":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
      case "integer":
      case "number":
      case "float":
      case "double":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300"
      case "boolean":
        return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300"
      case "date":
      case "datetime":
      case "timestamp":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300"
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300"
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Schema: {datasetName}</DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <RefreshCw className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <div className="text-center text-red-500 py-4">{error}</div>
        ) : graphSchema ? (
          <ScrollArea className="h-[500px] pr-4">
            <Tabs defaultValue="nodes" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="nodes">Nodes</TabsTrigger>
                <TabsTrigger value="relationships">Relationships</TabsTrigger>
                <TabsTrigger value="indexes">Indexes</TabsTrigger>
              </TabsList>
              
              <TabsContent value="nodes" className="space-y-4 mt-4">
                <h3 className="text-lg font-medium">Node Labels</h3>
                {graphSchema.nodes.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground">No nodes defined</div>
                ) : (
                  <div className="space-y-3">
                    {graphSchema.nodes.map((node, index) => (
                      <Card key={index} className="border border-border">
                        <CardContent className="p-4">
                          <h3 className="font-medium text-foreground mb-2">{node.label}</h3>
                          <div className="space-y-2">
                            <h4 className="text-sm font-medium text-muted-foreground">Properties:</h4>
                            {Object.entries(node.properties || {}).length === 0 ? (
                              <p className="text-sm text-muted-foreground">No properties defined</p>
                            ) : (
                              <div className="grid grid-cols-2 gap-2">
                                {Object.entries(node.properties || {}).map(([key, type], idx) => (
                                  <div key={idx} className="flex items-center gap-2">
                                    <span className="text-sm font-medium">{key}:</span>
                                    <Badge className={getTypeColor(type)}>{type}</Badge>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </TabsContent>
              
              <TabsContent value="relationships" className="space-y-4 mt-4">
                <h3 className="text-lg font-medium">Relationships</h3>
                {graphSchema.relationships.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground">No relationships defined</div>
                ) : (
                  <div className="space-y-3">
                    {graphSchema.relationships.map((rel, index) => (
                      <Card key={index} className="border border-border">
                        <CardContent className="p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="font-medium">{rel.startNode}</span>
                            <span className="text-primary font-bold">-[{rel.type}]-&gt;</span>
                            <span className="font-medium">{rel.endNode}</span>
                          </div>
                          
                          {rel.properties && Object.keys(rel.properties).length > 0 && (
                            <div className="mt-2">
                              <h4 className="text-sm font-medium text-muted-foreground">Properties:</h4>
                              <div className="grid grid-cols-2 gap-2 mt-1">
                                {Object.entries(rel.properties).map(([key, type], idx) => (
                                  <div key={idx} className="flex items-center gap-2">
                                    <span className="text-sm font-medium">{key}:</span>
                                    <Badge className={getTypeColor(type as string)}>{type}</Badge>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </TabsContent>
              
              <TabsContent value="indexes" className="space-y-4 mt-4">
                <h3 className="text-lg font-medium">Indexes</h3>
                {!graphSchema.indexes || graphSchema.indexes.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground">No indexes defined</div>
                ) : (
                  <div className="space-y-2">
                    {graphSchema.indexes.map((index, idx) => (
                      <Card key={idx} className="border border-border">
                        <CardContent className="p-3">
                          <code className="text-sm">{index}</code>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </ScrollArea>
        ) : schema.length === 0 ? (
          <div className="text-center py-4 text-muted-foreground">No schema information available</div>
        ) : (
          <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-3">
              {schema.map((field, index) => (
                <Card key={index} className="border border-border">
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-medium text-foreground">{field.name}</h3>
                        {field.description && <p className="text-sm text-muted-foreground mt-1">{field.description}</p>}
                      </div>
                      <div className="flex gap-2">
                        <Badge className={getTypeColor(field.type)}>{field.type}</Badge>
                        {field.nullable && <Badge variant="outline">Nullable</Badge>}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        )}
      </DialogContent>
    </Dialog>
  )
}

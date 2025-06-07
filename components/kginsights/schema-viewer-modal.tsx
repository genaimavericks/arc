"use client"

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { RefreshCw, Database, Upload } from "lucide-react"
import { useState, useEffect, useRef } from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { useToast } from "@/components/ui/use-toast"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { 
  Dialog as NestedDialog,
  DialogContent as NestedDialogContent,
  DialogHeader as NestedDialogHeader,
  DialogTitle as NestedDialogTitle,
  DialogFooter as NestedDialogFooter,
  DialogDescription as NestedDialogDescription,
} from "@/components/ui/dialog"

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
  csv_file_path?: string
  indexes?: Array<{
    label: string
    property: string
    type: string
  }>
}

export function SchemaViewerModal({ isOpen, onClose, datasetId, datasetName }: SchemaViewerModalProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [schema, setSchema] = useState<SchemaField[]>([])
  const [graphSchema, setGraphSchema] = useState<GraphSchema | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("fields")
  const [isLoadDataDialogOpen, setIsLoadDataDialogOpen] = useState(false)
  const [isLoadingData, setIsLoadingData] = useState(false)
  const [isCleaningUp, setIsCleaningUp] = useState(false)
  const [selectedGraph, setSelectedGraph] = useState("default")
  const [dropExisting, setDropExisting] = useState(false)
  const [availableGraphs, setAvailableGraphs] = useState<string[]>(["default"])
  const [isLoadingGraphs, setIsLoadingGraphs] = useState(false)
  const [dataPath, setDataPath] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()

  useEffect(() => {
    if (isOpen) {
      fetchSchemaData()
    }
  }, [isOpen, datasetId])

  useEffect(() => {
    if (isLoadDataDialogOpen) {
      // Don't automatically load graphs - let user create and manage them
      setAvailableGraphs([])
      setSelectedGraph('')
      setIsLoadingGraphs(false)
      
      // Check if we have a CSV file path from the schema
      if (graphSchema && graphSchema.csv_file_path) {
        setDataPath(graphSchema.csv_file_path)
      }
    }
  }, [isLoadDataDialogOpen, graphSchema])

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
          
          // Parse the schema JSON if it's a string
          let parsedSchema
          try {
            parsedSchema = typeof schemaData.schema === 'string' 
              ? JSON.parse(schemaData.schema) 
              : schemaData.schema
              
            // Add the CSV file path to the graph schema if available
            if (schemaData.csv_file_path) {
              parsedSchema.csv_file_path = schemaData.csv_file_path
            }
          } catch (e) {
            console.error("Error parsing schema JSON:", e)
            parsedSchema = {}
          }
          
          // Check if it has a graph schema structure
          if (parsedSchema.nodes || parsedSchema.relationships) {
            setGraphSchema(parsedSchema)
            setActiveTab("graph")
          } else {
            // Otherwise treat it as a regular schema
            setSchema(parsedSchema.fields || [])
          }
          
          setIsLoading(false)
          return
        }
      } catch (e) {
        console.error("Error fetching schema from database:", e)
        // Continue to try other methods
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

  // No graph loading functionality - graphs are managed elsewhere

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

  const handleCleanupSchemas = async () => {
    try {
      setIsCleaningUp(true)
      
      const response = await fetch('/api/graphschema/cleanup-schemas', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to clean up schemas')
      }
      
      const result = await response.json()
      
      toast({
        title: "Cleanup Complete",
        description: `Removed ${result.removed} schemas with missing files. Preserved ${result.preserved} valid schemas.`,
      })
      
      // Refresh schema list
      fetchSchemaData()
      
    } catch (error) {
      console.error('Error cleaning up schemas:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to clean up schemas",
        variant: "destructive"
      })
    } finally {
      setIsCleaningUp(false)
    }
  }

  const validateDataPath = (path: string | undefined): boolean => {
    if (!path) return true // Empty path is valid (will use schema's default)
    
    // Basic path validation - should be a valid file path
    // Windows: C:\path\to\file.csv or C:/path/to/file.csv
    // Unix: /path/to/file.csv or ~/path/to/file.csv
    const windowsPathRegex = /^[a-zA-Z]:[\\|\/][^<>:"|?*]+$/
    const unixPathRegex = /^(\/|~\/)[^<>:"|?*]+$/
    
    return windowsPathRegex.test(path) || unixPathRegex.test(path)
  }
  
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    try {
      setIsUploading(true)
      
      // Create a FormData object to send the file
      const formData = new FormData()
      formData.append('file', file)
      
      // Upload the file
      const response = await fetch('/api/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to upload file')
      }
      
      const result = await response.json()
      
      // Set the data path to the uploaded file path
      setDataPath(result.path)
      
      toast({
        title: "Success",
        description: "File uploaded successfully",
        variant: "default"
      })
    } catch (error) {
      console.error('Error uploading file:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : 'Failed to upload file',
        variant: "destructive"
      })
    } finally {
      setIsUploading(false)
      
      // Reset the file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }
  
  const handleLoadData = async () => {
    try {
      // Check if we need a data path and don't have one
      if (!graphSchema?.csv_file_path && (!dataPath || dataPath.trim() === '')) {
        toast({
          title: "Error",
          description: "Please enter a valid data path. No default path is available for this schema.",
          variant: "destructive"
        })
        return
      }
      
      // Validate data path if provided
      if (dataPath && !validateDataPath(dataPath)) {
        toast({
          title: "Error",
          description: "Please enter a valid file path",
          variant: "destructive"
        })
        return
      }
      
      setIsLoadingData(true)
      
      // Use the direct schema-specific endpoint with query parameters
      const queryParams = new URLSearchParams()
      queryParams.append('drop_existing', dropExisting.toString())
      
      // Construct the URL with the schema ID and query parameters
      const url = `/api/graphschema/schemas/${datasetId}/load-data?${queryParams.toString()}`
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          use_source_data: true,
          data_path: dataPath || graphSchema?.csv_file_path || ''
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to load data')
      }
      
      const result = await response.json()
      
      toast({
        title: "Success",
        description: `Loaded ${result.result.nodes_created} nodes and ${result.result.relationships_created} relationships into Neo4j`,
      })
      
      setIsLoadDataDialogOpen(false)
    } catch (error) {
      console.error('Error loading data:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to load data into Neo4j",
        variant: "destructive"
      })
    } finally {
      setIsLoadingData(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Schema: {datasetName}</DialogTitle>
          {/* Buttons removed as per user request */}
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
                {graphSchema.indexes && graphSchema.indexes.length > 0 && (
                  <div>
                    <h3 className="font-semibold mb-2">Indexes</h3>
                    <div className="space-y-2">
                      {graphSchema.indexes.map((index: { label: string; property: string; type: string }, idx: number) => (
                        <Card key={idx} className="border border-border">
                          <CardContent className="p-3">
                            <code className="text-sm">{`${index.label}.${index.property} (${index.type})`}</code>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
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
      
      {/* Load Data Dialog */}
      <NestedDialog open={isLoadDataDialogOpen} onOpenChange={setIsLoadDataDialogOpen}>
        <NestedDialogContent>
          <NestedDialogHeader>
            <NestedDialogTitle>Load Data to Neo4j</NestedDialogTitle>
            <NestedDialogDescription>
              Select options for loading data
            </NestedDialogDescription>
          </NestedDialogHeader>
          
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="dataPath">Data Path {!graphSchema?.csv_file_path && <span className="text-red-500">*Required</span>}</Label>
                <div className="flex space-x-2">
                  <Input 
                    id="dataPath" 
                    placeholder="Path to CSV file" 
                    value={dataPath}
                    onChange={(e) => setDataPath(e.target.value)}
                    className="flex-1"
                  />
                  <Button 
                    variant="outline" 
                    size="icon" 
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                  >
                    <Upload className="h-4 w-4" />
                  </Button>
                  <input 
                    type="file" 
                    ref={fileInputRef} 
                    className="hidden" 
                    accept=".csv"
                    onChange={handleFileUpload}
                  />
                </div>
                {isUploading ? (
                  <p className="text-xs text-blue-500">
                    Uploading file...
                  </p>
                ) : graphSchema?.csv_file_path ? (
                  <p className="text-xs text-muted-foreground">
                    Using CSV file path from schema. You can override it if needed.
                  </p>
                ) : (
                  <p className="text-xs text-red-500">
                    No CSV file path found in schema. Please provide a path to a CSV file or upload one.
                  </p>
                )}
              </div>
              <div className="space-y-2 flex items-end">
                <div className="flex items-center space-x-2">
                  <Switch 
                    id="dropExisting" 
                    checked={dropExisting}
                    onCheckedChange={setDropExisting}
                  />
                  <Label htmlFor="dropExisting">Drop existing data</Label>
                </div>
              </div>
            </div>    
            <NestedDialogFooter>
              <Button variant="outline" onClick={() => setIsLoadDataDialogOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleLoadData} 
                disabled={isLoadingData}
              >
                {isLoadingData ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  "Load Data"
                )}
              </Button>
            </NestedDialogFooter>
          </div>
        </NestedDialogContent>
      </NestedDialog>
    </Dialog>
  )
}

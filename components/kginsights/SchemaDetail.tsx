"use client"

import { useState, useEffect } from "react"
import { useSchemaSelection } from "@/lib/schema-selection-context"
import { useKGInsightsJobs } from "@/lib/kginsights-job-context"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
import { Database, Trash, Edit, Play, FileText, FileCode, BarChart } from "lucide-react"
import { formatDistanceToNow, format } from "date-fns"

// Define schema status interface
interface SchemaStatus {
  schema_id: number
  name: string
  created_at: string
  updated_at?: string
  has_data: boolean
  was_cleaned: boolean
  node_count: number
  relationship_count: number
  last_data_update?: string
  active_jobs: Array<{
    id: string
    type: string
    status: string
    progress: number
    message: string
    created_at: string
  }>
  graph_data_stats: {
    node_counts: Record<string, number>
    relationship_counts: Record<string, number>
  }
}

export default function SchemaDetail() {
  const { selectedSchemaId, getSchemaById } = useSchemaSelection()
  const { jobs, getActiveJobsForSchema, startLoadDataJob, startCleanDataJob, refreshJobs } = useKGInsightsJobs()
  
  const [schemaStatus, setSchemaStatus] = useState<SchemaStatus | null>(null)
  const [isLoadingStatus, setIsLoadingStatus] = useState(false)
  const [activeTab, setActiveTab] = useState("overview")
  
  const selectedSchema = selectedSchemaId ? getSchemaById(selectedSchemaId) : undefined
  const activeJobs = selectedSchemaId ? getActiveJobsForSchema(selectedSchemaId) : []
  
  // Load schema status when selected schema changes
  useEffect(() => {
    if (selectedSchemaId) {
      fetchSchemaStatus(selectedSchemaId)
    } else {
      setSchemaStatus(null)
    }
  }, [selectedSchemaId])
  
  // Update when jobs change
  useEffect(() => {
    if (selectedSchemaId) {
      fetchSchemaStatus(selectedSchemaId)
      console.log("Jobs updated, active jobs:", activeJobs.length, "schema has data:", schemaStatus?.has_data)
    }
  }, [jobs])
  
  // Fetch schema status from API
  const fetchSchemaStatus = async (schemaId: number) => {
    setIsLoadingStatus(true)
    
    try {
      const token = localStorage.getItem('token') // Get token
      if (!token) {
        throw new Error('Authentication token not found.')
      }
      
      // Use the correct, new path and add Authorization header
      const response = await fetch(`/api/kginsights/schema-status/${schemaId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })
      
      if (!response.ok) {
        throw new Error(`Failed to fetch schema status: ${response.statusText}`)
      }
      
      const data = await response.json()
      console.log("Schema status data:", data)
      setSchemaStatus(data)
    } catch (error) {
      console.error("Error fetching schema status:", error)
    } finally {
      setIsLoadingStatus(false)
    }
  }
  
  // Handle load data action
  const handleLoadData = async () => {
    if (!selectedSchemaId) return
    
    await startLoadDataJob(selectedSchemaId, {
      use_source_data: true,
      drop_existing: false
    })
  }
  
  // Handle clean data action
  const handleCleanData = async () => {
    if (!selectedSchemaId) return
    
    const job = await startCleanDataJob(selectedSchemaId, {
      graph_name: "default"
    })
    
    // Force refresh the schema status and jobs after a delay
    if (job) {
      // Poll for job completion
      const checkJobCompletion = async () => {
        await refreshJobs()
        await fetchSchemaStatus(selectedSchemaId)
        
        // Check if job is still active
        const updatedJob = jobs.find(j => j.id === job.id)
        if (updatedJob && (updatedJob.status === "pending" || updatedJob.status === "running")) {
          // Continue polling
          setTimeout(checkJobCompletion, 1000)
        }
      }
      
      // Start polling
      setTimeout(checkJobCompletion, 1000)
    }
  }
  
  if (!selectedSchemaId || !selectedSchema) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Select a schema to view details
      </div>
    )
  }
  
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold">{selectedSchema.name}</h2>
          <p className="text-sm text-muted-foreground">
            Created {formatDistanceToNow(new Date(selectedSchema.created_at), { addSuffix: true })}
          </p>
        </div>
        
        <div className="flex gap-2">
          {/* Load Data Button */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex items-center gap-1"
                  onClick={handleLoadData}
                  disabled={activeJobs.length > 0}
                >
                  <Play className="h-4 w-4" />
                  Load Data
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Load data for this schema</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          
          {/* Clean Data Button - Wrapped in AlertDialog */}
          <AlertDialog>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <AlertDialogTrigger asChild> 
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex items-center gap-1"
                      disabled={activeJobs.length > 0 || !(schemaStatus?.has_data) || schemaStatus?.was_cleaned}
                    >
                      <FileText className="h-4 w-4" />
                      Clean Data
                    </Button>
                  </AlertDialogTrigger>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Clean existing data for this schema (Requires confirmation)</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Are you sure you want to clean data?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action will attempt to clean the existing data associated with the schema "{selectedSchema.name}". This might involve removing nodes, relationships, or properties based on cleaning rules (if defined). This process cannot be undone easily.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleCleanData}>Confirm Clean</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          
          {/* Edit Button */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  disabled={activeJobs.length > 0}
                >
                  <Edit className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Edit schema</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          
          {/* Delete Button - Wrapped in AlertDialog */}
          <AlertDialog>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      className="text-destructive"
                      disabled={activeJobs.length > 0}
                    >
                      <Trash className="h-4 w-4" />
                    </Button>
                  </AlertDialogTrigger>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Delete schema (Requires confirmation)</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Are you sure you want to delete this schema?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action will permanently delete the schema "{selectedSchema.name}" and any associated configuration. It may not delete the data in the graph itself unless specified. This cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                {/* TODO: Implement actual delete function call */}
                <AlertDialogAction onClick={() => console.warn('Delete schema not implemented yet')}>Confirm Delete</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
      
      {/* Status badges */}
      <div className="flex gap-2 mb-4">
        <Badge variant={schemaStatus?.has_data ? "default" : "outline"}>
          <Database className="h-3 w-3 mr-1" />
          {schemaStatus?.has_data ? "Data Loaded" : "No Data"}
        </Badge>
        
        {schemaStatus?.node_count !== undefined && schemaStatus.node_count > 0 && (
          <Badge variant="secondary">
            {schemaStatus.node_count} Nodes
          </Badge>
        )}
        
        {schemaStatus?.relationship_count !== undefined && schemaStatus.relationship_count > 0 && (
          <Badge variant="secondary">
            {schemaStatus.relationship_count} Relationships
          </Badge>
        )}
        
        {schemaStatus?.last_data_update && (
          <Badge variant="outline">
            Updated {formatDistanceToNow(new Date(schemaStatus.last_data_update), { addSuffix: true })}
          </Badge>
        )}
        
        {activeJobs.length > 0 && (
          <Badge variant="secondary" className="animate-pulse">
            Processing
          </Badge>
        )}
        
        {schemaStatus?.was_cleaned && (
          <Badge variant="secondary" className="bg-green-100 text-green-800 hover:bg-green-100">
            Data Cleaned
          </Badge>
        )}
      </div>
      
      {/* Schema details tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid grid-cols-3 w-full">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="structure">Structure</TabsTrigger>
          <TabsTrigger value="cypher">Cypher</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="mt-4">
          {isLoadingStatus ? (
            <Card>
              <CardContent className="p-4">
                <div className="space-y-2">
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-4">
                <div className="space-y-2">
                  <div>
                    <span className="text-sm font-medium">Schema ID:</span>
                    <span className="text-sm ml-2">{selectedSchemaId}</span>
                  </div>
                  
                  {selectedSchema.csv_path && (
                    <div>
                      <span className="text-sm font-medium">Source Data:</span>
                      <span className="text-sm ml-2 text-muted-foreground">{selectedSchema.csv_path}</span>
                    </div>
                  )}
                  
                  {schemaStatus && (
                    <>
                      <div className="pt-2">
                        <span className="text-sm font-medium">Data Status:</span>
                        <span className="text-sm ml-2">
                          {schemaStatus.has_data ? "Data loaded" : "No data loaded"}
                        </span>
                      </div>
                      
                      {schemaStatus.has_data && (
                        <>
                          <div>
                            <span className="text-sm font-medium">Nodes:</span>
                            <span className="text-sm ml-2">{schemaStatus.node_count}</span>
                          </div>
                          
                          <div>
                            <span className="text-sm font-medium">Relationships:</span>
                            <span className="text-sm ml-2">{schemaStatus.relationship_count}</span>
                          </div>
                          
                          {schemaStatus.last_data_update && (
                            <div>
                              <span className="text-sm font-medium">Last Updated:</span>
                              <span className="text-sm ml-2">
                                {format(new Date(schemaStatus.last_data_update), 'PPpp')}
                              </span>
                            </div>
                          )}
                        </>
                      )}
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
        
        <TabsContent value="structure" className="mt-4">
          <Card>
            <CardContent className="p-4">
              {isLoadingStatus ? (
                <div className="space-y-4">
                  <Skeleton className="h-5 w-1/4" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-1/2" />
                    <Skeleton className="h-4 w-3/5" />
                    <Skeleton className="h-4 w-2/5" />
                  </div>
                  
                  <Skeleton className="h-5 w-1/4 mt-4" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-1/2" />
                    <Skeleton className="h-4 w-3/5" />
                  </div>
                </div>
              ) : (
                <div>
                  {selectedSchema.schema_json && (
                    <>
                      <div className="mb-4">
                        <h3 className="text-sm font-medium mb-2 flex items-center">
                          <FileCode className="h-4 w-4 mr-1" />
                          Node Types
                        </h3>
                        <div className="space-y-1">
                          {(() => {
                            try {
                              const schema = typeof selectedSchema.schema_json === 'string'
                                ? JSON.parse(selectedSchema.schema_json)
                                : selectedSchema.schema_json;
                              
                              return schema.nodes?.map((node: any, index: number) => (
                                <div key={index} className="text-sm">
                                  <Badge variant="outline" className="mr-2">{node.label}</Badge>
                                  <span className="text-xs text-muted-foreground">
                                    {Object.keys(node.properties || {}).length} properties
                                  </span>
                                </div>
                              )) || <div className="text-sm text-muted-foreground">No node types defined</div>;
                            } catch (e) {
                              return <div className="text-sm text-muted-foreground">Invalid schema format</div>;
                            }
                          })()}
                        </div>
                      </div>
                      
                      <div>
                        <h3 className="text-sm font-medium mb-2 flex items-center">
                          <FileCode className="h-4 w-4 mr-1" />
                          Relationship Types
                        </h3>
                        <div className="space-y-1">
                          {(() => {
                            try {
                              const schema = typeof selectedSchema.schema_json === 'string'
                                ? JSON.parse(selectedSchema.schema_json)
                                : selectedSchema.schema_json;
                              
                              return schema.relationships?.map((rel: any, index: number) => (
                                <div key={index} className="text-sm">
                                  <span className="text-xs">{rel.startNode}</span>
                                  <Badge variant="outline" className="mx-2">{rel.type}</Badge>
                                  <span className="text-xs">{rel.endNode}</span>
                                </div>
                              )) || <div className="text-sm text-muted-foreground">No relationship types defined</div>;
                            } catch (e) {
                              return <div className="text-sm text-muted-foreground">Invalid schema format</div>;
                            }
                          })()}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="cypher" className="mt-4">
          <Card>
            <CardContent className="p-4">
              {isLoadingStatus ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ) : (
                <div>
                  <h3 className="text-sm font-medium mb-2 flex items-center">
                    <BarChart className="h-4 w-4 mr-1" />
                    Cypher Query
                  </h3>
                  
                  {selectedSchema.cypher ? (
                    <pre className="text-xs bg-secondary p-2 rounded-md overflow-x-auto">
                      {selectedSchema.cypher}
                    </pre>
                  ) : (
                    <div className="text-sm text-muted-foreground">No Cypher query available</div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

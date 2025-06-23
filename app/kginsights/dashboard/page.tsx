"use client"

import { motion } from "framer-motion"
import { Plus, Search, Eye, FileText, PlusCircle, RefreshCw, Trash2, Database, Upload, Settings, LineChart, ChevronLeft, ChevronRight, Calendar } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { useEffect, useState } from "react"
import { getKGraphDashboard } from "@/lib/api"
import LoadingSpinner from "@/components/loading-spinner"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { useToast } from "@/components/ui/use-toast"
import { useRouter } from "next/navigation"
import { DatasetPreviewModal } from "@/components/kginsights/dataset-preview-modal"
import { SchemaViewerModal } from "@/components/kginsights/schema-viewer-modal"
import { GenerateKGModal } from "@/components/kginsights/generate-kg-modal"
import { KGInsightsLayout } from "@/components/kginsights/kginsights-layout"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

// Define interfaces for our data
interface KnowledgeGraph {
  id: string
  name: string
  description: string
  created: string
  type: string
}

interface Dataset {
  id: string
  name: string
  dataset?: string
  type: string // "source" or "transformed"
  sourceType?: string
  status: string
  last_updated: string
  description?: string
}

interface Neo4jGraph {
  name: string
}

interface SelectedDataset {
  id: string
  name: string
  type: string
}

export default function KGraphDashboardPage() {
  return (
    <KGInsightsLayout>
      <KGraphDashboardContent />
    </KGInsightsLayout>
  )
}

function KGraphDashboardContent() {
  const [knowledgeGraphs, setKnowledgeGraphs] = useState<KnowledgeGraph[]>([
    {
      id: "1",
      name: "Customer Relations",
      description: "Customer-product relationships",
      created: "2025-03-05T10:30:00.000Z",
      type: "graph"
    },
    {
      id: "2",
      name: "Supply Chain",
      description: "Supply chain network",
      created: "2025-02-20T14:45:00.000Z",
      type: "graph"
    },
  ])

  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loadingDatasets, setLoadingDatasets] = useState(false)
  const [datasetsError, setDatasetsError] = useState<string | null>(null)
  
  // Dataset filter state
  const [datasetFilter, setDatasetFilter] = useState<string>("all") // "all", "source", "transformed"
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [neo4jGraphs, setNeo4jGraphs] = useState<Neo4jGraph[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage] = useState(10)
  const { toast } = useToast()
  const router = useRouter()

  // Preview modal states
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [selectedDataset, setSelectedDataset] = useState<SelectedDataset | null>(null)
  const [previewData, setPreviewData] = useState<any[]>([])
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  
  // Schema modal states
  const [schemaModalOpen, setSchemaModalOpen] = useState(false)
  const [schemaData, setSchemaData] = useState<any>({})
  const [loadingSchema, setLoadingSchema] = useState(false)
  const [schemaError, setSchemaError] = useState<string | null>(null)
  
  // KG Generation modal states
  const [generateKGModalOpen, setGenerateKGModalOpen] = useState(false)
  const [applyToNeo4jModalOpen, setApplyToNeo4jModalOpen] = useState(false)
  const [graphToApply, setGraphToApply] = useState<KnowledgeGraph | null>(null)

  // Function to fetch available datasets (source and transformed)
  const fetchDataSources = async () => {
    setLoadingDatasets(true)
    try {
      // Fetch all required datasets in parallel
      const [sourceResponse, transformedResponse] = await Promise.all([
        // Original source datasets
        fetch("/api/datapuur/sources", {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        }),
        
        // Transformed datasets
        fetch("/api/datapuur-ai/transformed-datasets", {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        })
      ])

      if (!sourceResponse.ok) {
        throw new Error(`Failed to fetch data sources: ${sourceResponse.status}`)
      }
      
      if (!transformedResponse.ok) {
        console.warn(`Failed to fetch transformed datasets: ${transformedResponse.status}`)
      }

      const sourceData = await sourceResponse.json()
      let transformedData: any[] = []
      
      try {
        transformedData = await transformedResponse.json()
      } catch (e) {
        console.warn("Error parsing transformed datasets response:", e)
      }

      // Map source datasets to our dataset format
      const availableSourceDatasets = sourceData.map((item: any) => ({
        id: item.id,
        name: item.name,
        dataset: item.dataset,
        type: "source", // Mark as source type for filtering
        sourceType: item.type.toLowerCase(),
        status: "completed",
        last_updated: item.last_updated || new Date().toISOString(),
      }))
      
      // Map transformed datasets to our dataset format
      const availableTransformedDatasets = transformedData.map((item: any) => ({
        id: item.id,
        name: item.name,
        description: item.description || '',
        dataset: item.name,
        type: "transformed", // Mark as transformed type for filtering
        sourceFileId: item.source_file_id,
        status: "completed",
        last_updated: item.updated_at || item.created_at || new Date().toISOString(),
      }))

      // Combine and sort all datasets by last updated date
      const allDatasets = [...availableSourceDatasets, ...availableTransformedDatasets]
      const sortedDatasets = allDatasets.sort((a, b) => 
        new Date(b.last_updated).getTime() - new Date(a.last_updated).getTime()
      )

      setDatasets(sortedDatasets)
      setDatasetsError(null)
    } catch (err) {
      console.error("Error fetching datasets:", err)
      setDatasetsError("Failed to load available datasets. Using fallback data.")

      // Fallback data
      setDatasets([
        { id: "1", name: "Sales Q1", type: "source", sourceType: "file", status: "completed", last_updated: new Date().toISOString() },
        { id: "2", name: "HR Data", type: "transformed", status: "completed", last_updated: new Date().toISOString() },
      ])

      toast({
        title: "Error",
        description: "Failed to load available datasets. Using fallback data.",
        variant: "destructive",
      })
    } finally {
      setLoadingDatasets(false)
    }
  }

  // Function to fetch knowledge graphs
  const fetchKnowledgeGraphs = async () => {
    try {
      // First try to fetch saved schemas
      const schemasResponse = await fetch("/api/graphschema/schemas", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (schemasResponse.ok) {
        const schemasData = await schemasResponse.json();
        
        if (schemasData && Array.isArray(schemasData)) {
          // Map schemas to knowledge graphs format
          const schemaGraphs = schemasData.map((schema: any) => ({
            id: schema.id.toString(),
            name: schema.name,
            description: schema.description || "Generated schema",
            created: schema.created_at ? schema.created_at : new Date().toISOString(),
            type: "schema"
          }));
          
          setKnowledgeGraphs(schemaGraphs);
          return;
        }
      }
      
      // Fallback to existing graphs endpoint if schemas endpoint fails
      const response = await fetch("/api/kginsights/graphs", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch knowledge graphs: ${response.status}`);
      }

      const data = await response.json();

      if (data && Array.isArray(data.graphs)) {
        setKnowledgeGraphs(
          data.graphs.map((graph: any) => ({
            id: graph.id,
            name: graph.name,
            description: graph.description || "",
            created: graph.created_at ? graph.created_at : new Date().toISOString(),
            type: "graph"
          }))
        );
      }
    } catch (err) {
      console.error("Error fetching knowledge graphs:", err);
      // Keep using the mock data
      toast({
        title: "Note",
        description: "Using demo knowledge graph data.",
        variant: "default",
      });
    }
  }

  // Function to apply knowledge graph to Neo4j
  const applyToNeo4j = async (graph: KnowledgeGraph) => {
    try {
      const response = await fetch("/api/graphschema/apply-schema", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({ 
          schema_id: parseInt(graph.id),
          graph_name: "default", // Using default graph for now
          drop_existing: false 
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`Failed to apply schema to Neo4j: ${response.status} - ${errorData.detail || 'Unknown error'}`);
      }

      toast({
        title: "Success",
        description: `Schema "${graph.name}" applied to Neo4j successfully.`,
        variant: "default",
      });
    } catch (err) {
      console.error("Error applying schema to Neo4j:", err);
      toast({
        title: "Error",
        description: `Failed to apply schema to Neo4j: ${err instanceof Error ? err.message : 'Unknown error'}`,
        variant: "destructive",
      });
    }
  }

  // Function to handle view schema
  const handleViewSchema = (datasetId: string, name: string, datasetType: string) => {
    // Logic to view dataset schema based on type (source or transformed)
    setSelectedDataset({ id: datasetId, name, type: datasetType })
    setSchemaModalOpen(true)
  }

  // Function to handle apply to Neo4j
  const handleApplyToNeo4j = (graph: KnowledgeGraph) => {
    setGraphToApply(graph)
    setApplyToNeo4jModalOpen(true)
  }

  // Function to handle dataset preview
  const handlePreview = (datasetId: string, name: string, datasetType: string) => {
    // Logic to preview dataset based on type (source or transformed)
    setSelectedDataset({ id: datasetId, name, type: datasetType })
    setPreviewModalOpen(true)
  }

  // Function to handle KG generation
  const handleGenerateKG = (datasetId: string, name: string, datasetType: string) => {
    // Logic to initiate knowledge graph generation with dataset type
    router.push(`/kginsights/generate?sourceId=${datasetId}&sourceName=${encodeURIComponent(name)}&datasetType=${datasetType}`)
  }

  // Function to handle manage schema
  const handleManageSchema = (graphId: string) => {
    router.push(`/kginsights/manage/${graphId}`)
  }

  // Function to handle insights
  const handleInsights = (graphId: string) => {
    router.push(`/kginsights/insights/`)
  }

  // Function to handle new knowledge graph
  const handleNewKnowledgeGraph = () => {
    router.push("/kginsights/generate")
  }

  // Function to handle search graphs
  const handleSearchGraphs = () => {
    router.push("/kginsights/search")
  }

  // Function to confirm apply to Neo4j
  const confirmApplyToNeo4j = async () => {
    if (graphToApply) {
      await applyToNeo4j(graphToApply)
      setApplyToNeo4jModalOpen(false)
      setGraphToApply(null)
    }
  }

  // Pagination control functions
  const goToNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1)
    }
  }

  const goToPreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1)
    }
  }

  const goToPage = (pageNumber: number) => {
    setCurrentPage(pageNumber)
  }

  // Calculate pagination values
  const indexOfLastItem = currentPage * itemsPerPage
  const indexOfFirstItem = indexOfLastItem - itemsPerPage
  const currentItems = datasets.slice(indexOfFirstItem, indexOfLastItem)
  const totalPages = Math.ceil(datasets.length / itemsPerPage)

  // Animation variants
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  }

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        // Keep the existing API call for KGraph dashboard data
        const dashboardData = await getKGraphDashboard()
        console.log("Successfully fetched KGraph dashboard data:", dashboardData)

        // Fetch knowledge graphs
        await fetchKnowledgeGraphs()

        // Fetch available datasets from sources
        await fetchDataSources()

        setError(null)
      } catch (err) {
        console.error("Error fetching KGraff dashboard data:", err)
        setError("Failed to load KGraff dashboard data. Using fallback data.")
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  // If we have an error but also have dashboard data (from fallback),
  // we'll show a warning but still render the UI
  const showErrorBanner = error

  if (loading) {
    return (
        <div className="flex-1 p-6 flex items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  return (
      <div className="flex-1 p-6 bg-gradient-to-b from-background to-background/95 w-full">


      {showErrorBanner && (
        <div className="bg-yellow-500/20 border border-yellow-500 text-yellow-700 dark:text-yellow-200 px-4 py-2 rounded-md mb-4 relative z-10">
          <p>{error} - Using demo data instead.</p>
        </div>
      )}

      <div className="w-full max-w-full relative z-10">
        <div className="flex justify-between items-center mb-4 w-full">
          <motion.h1
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-2xl font-bold tracking-tight text-foreground"
          >
            KGraff Dashboard
          </motion.h1>

          {/* Search Button */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <Button
              variant="outline"
              className="border-primary/30 text-foreground flex items-center gap-2"
              size="sm"
              onClick={handleSearchGraphs}
            >
              <Search className="w-4 h-4" />
              Search Graphs...
            </Button>
          </motion.div>
        </div>

        {/* Knowledge Graphs Section */}
        <motion.div variants={container} initial="hidden" animate="show" className="space-y-8 w-full">
          <motion.div variants={item} className="w-full">
            <Card className="bg-card/80 backdrop-blur-sm border border-border w-full min-w-full">
              <CardContent className="p-0 w-full">
                <div className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <h2 className="text-xl font-semibold text-foreground">Knowledge Graphs</h2>
                    <Button
                      className="bg-primary hover:bg-primary/90 text-primary-foreground flex items-center justify-center p-0"
                      size="icon"
                      onClick={handleNewKnowledgeGraph}
                    >
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div className="overflow-x-auto w-full">
                  <table className="w-full min-w-full table-fixed border-collapse">
                    <thead>
                      <tr className="border-t border-b border-border">
                        <th className="px-4 py-3 text-left text-foreground font-medium w-1/4">Name</th>
                        <th className="px-4 py-3 text-left text-foreground font-medium w-1/3">Description</th>
                        <th className="px-4 py-3 text-left text-foreground font-medium w-1/4">Created</th>
                        <th className="px-4 py-3 text-left text-foreground font-medium w-1/6">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {knowledgeGraphs.map((graph, index) => (
                        <motion.tr
                          key={graph.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.2 + index * 0.1 }}
                          className={cn(
                            "border-b border-border hover:bg-accent/30 transition-colors",
                            index === knowledgeGraphs.length - 1 && "border-b-0",
                          )}
                        >
                          <td className="px-4 py-3 text-foreground font-medium">{graph.name}</td>
                          <td className="px-4 py-3 text-muted-foreground">{graph.description}</td>
                          <td className="px-4 py-3">
                            <div className="flex flex-col">
                              {(() => {
                                try {
                                  // Parse the UTC date from the string
                                  const utcDate = new Date(graph.created);
                                  
                                  // Get the client's timezone offset in minutes
                                  const timezoneOffset = new Date().getTimezoneOffset();
                                  
                                  // Convert from UTC to client's local time by adjusting for timezone offset
                                  // Note: getTimezoneOffset() returns minutes WEST of UTC, so we negate it
                                  const localDate = new Date(utcDate.getTime() - (timezoneOffset * 60 * 1000));
                                  
                                  // Format the date and time
                                  return (
                                    <>
                                      <span>{formatDistanceToNow(localDate, { addSuffix: true })}</span>
                                      <span className="text-xs text-muted-foreground">
                                        {`${localDate.getFullYear()}-${String(localDate.getMonth() + 1).padStart(2, '0')}-${String(localDate.getDate()).padStart(2, '0')} ${String(localDate.getHours()).padStart(2, '0')}:${String(localDate.getMinutes()).padStart(2, '0')}:${String(localDate.getSeconds()).padStart(2, '0')}`}
                                      </span>
                                    </>
                                  );
                                } catch (error) {
                                  console.error("Error formatting date:", error, graph.created);
                                  return graph.created || "N/A";
                                }
                              })()}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              {graph.type === "schema" ? (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="text-orange-500 hover:text-orange-600 hover:bg-orange-500/10"
                                    onClick={() => handleViewSchema(graph.id, graph.name, "graph")}
                                    title="View Schema"
                                  >
                                    <FileText className="w-5 h-5" />
                                  </Button>
                                </>
                              ) : (
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="text-primary hover:text-primary/80 hover:bg-primary/10"
                                  onClick={() => handleManageSchema(graph.id)}
                                  title="Manage Schema"
                                >
                                  <Settings className="w-5 h-5" />
                                </Button>
                              )}
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-purple-500 hover:text-purple-600 hover:bg-purple-500/10"
                                onClick={() => handleInsights(graph.id)}
                                title="Insights"
                              >
                                <LineChart className="w-5 h-5" />
                              </Button>
                            </div>
                          </td>
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Available Datasets Section */}
          <motion.div variants={item} className="w-full">
            <Card className="bg-card/80 backdrop-blur-sm border border-border mt-6 w-full min-w-full">
              <CardContent className="p-0 w-full">
                <div className="p-4 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-semibold text-foreground">Available Datasets for KG Generation</h2>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={fetchDataSources}
                      disabled={loadingDatasets}
                      title="Refresh datasets"
                    >
                      <RefreshCw className={`w-4 h-4 ${loadingDatasets ? "animate-spin" : ""}`} />
                    </Button>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <label htmlFor="dataset-filter" className="text-sm mr-2">Show:</label>
                    <select
                      id="dataset-filter"
                      className="py-1 px-2 rounded border border-border bg-background text-sm"
                      value={datasetFilter}
                      onChange={(e) => setDatasetFilter(e.target.value)}
                    >
                      <option value="all">All Datasets</option>
                      <option value="source">Source Datasets</option>
                      <option value="transformed">Transformed Datasets</option>
                    </select>
                  </div>
                </div>

                <div className="overflow-x-auto w-full">
                  {loadingDatasets ? (
                    <div className="mt-6 flex justify-center items-center py-8">
                      <LoadingSpinner />
                    </div>
                  ) : datasets.length > 0 ? (
                    <>
                      <table className="w-full min-w-full table-fixed border-collapse">
                        <thead>
                          <tr className="border-t border-b border-border">
                            <th className="px-4 py-3 text-left text-foreground font-medium w-2/5">Dataset</th>
                            <th className="px-4 py-3 text-left text-foreground font-medium w-2/5">Created</th>
                            <th className="px-4 py-3 text-left text-foreground font-medium w-1/5">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {currentItems
                            // Filter datasets based on selected filter
                            .filter(dataset => datasetFilter === "all" || dataset.type === datasetFilter)
                            .map((dataset, index) => (
                            <motion.tr
                              key={dataset.id}
                              initial={{ opacity: 0, y: 10 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ delay: 0.4 + index * 0.1 }}
                              className={cn(
                                "border-b border-border hover:bg-accent/30 transition-colors",
                                index === currentItems.length - 1 && currentItems.length < itemsPerPage && "border-b-0",
                              )}
                            >
                              <td className="px-4 py-3 text-foreground font-medium">
                                <div className="flex flex-col">
                                  <span>{dataset.dataset || dataset.name}</span>
                                  <div className="flex items-center gap-1 mt-0.5">
                                    {dataset.type === "transformed" ? (
                                      <Badge variant="outline" className="bg-emerald-100 text-emerald-800 hover:bg-emerald-200 border-emerald-300">
                                        Transformed
                                      </Badge>
                                    ) : (
                                      <Badge variant="outline" className="bg-blue-100 text-blue-800 hover:bg-blue-200 border-blue-300">
                                        Source
                                      </Badge>
                                    )}
                                    {dataset.sourceType && (
                                      <span className="text-xs text-muted-foreground capitalize">{dataset.sourceType}</span>
                                    )}
                                  </div>
                                </div>
                              </td>
                              <td className="px-4 py-3">
                                <div className="flex items-center">
                                  <Calendar className="h-3 w-3 mr-1" />
                                  <div>
                                    {(() => {
                                      try {
                                        // Parse the UTC date from the ISO string
                                        const utcDate = new Date(dataset.last_updated);
                                        
                                        // Get the client's timezone offset in minutes
                                        const timezoneOffset = new Date().getTimezoneOffset();
                                        
                                        // Convert from UTC to client's local time by adjusting for timezone offset
                                        // Note: getTimezoneOffset() returns minutes WEST of UTC, so we negate it
                                        const localDate = new Date(utcDate.getTime() - (timezoneOffset * 60 * 1000));
                                        
                                        // Format the date and time
                                        return (
                                          <>
                                            <div>{formatDistanceToNow(localDate, { addSuffix: true })}</div>
                                            <div className="text-xs text-muted-foreground">
                                              {`${localDate.getFullYear()}-${String(localDate.getMonth() + 1).padStart(2, '0')}-${String(localDate.getDate()).padStart(2, '0')} ${String(localDate.getHours()).padStart(2, '0')}:${String(localDate.getMinutes()).padStart(2, '0')}:${String(localDate.getSeconds()).padStart(2, '0')}`}
                                            </div>
                                          </>
                                        );
                                      } catch (error) {
                                        console.error("Error formatting date:", error, dataset.last_updated);
                                        return dataset.last_updated || "Unknown";
                                      }
                                    })()}
                                  </div>
                                </div>
                              </td>
                              <td className="px-4 py-3">
                                <div className="flex items-center gap-2">
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="text-amber-500 hover:text-amber-600 hover:bg-amber-500/10"
                                    onClick={() => handlePreview(dataset.id, dataset.dataset || dataset.name, dataset.type)}
                                    title="Preview"
                                  >
                                    <Eye className="w-5 h-5" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="text-orange-500 hover:text-orange-600 hover:bg-orange-500/10"
                                    onClick={() => handleViewSchema(dataset.id, dataset.dataset || dataset.name, dataset.type)}
                                    title="Schema"
                                  >
                                    <FileText className="w-5 h-5" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="text-primary hover:text-primary/80 hover:bg-primary/10"
                                    onClick={() => handleGenerateKG(dataset.id, dataset.dataset || dataset.name, dataset.type)}
                                    title="Generate KG"
                                  >
                                    <PlusCircle className="w-5 h-5" />
                                  </Button>
                                </div>
                              </td>
                            </motion.tr>
                          ))}
                        </tbody>
                      </table>
                      
                      {/* Pagination Controls */}
                      {datasets.length > itemsPerPage && (
                        <div className="flex items-center justify-between p-4 border-t border-border">
                          <div className="text-sm text-muted-foreground">
                            Showing {indexOfFirstItem + 1} to {Math.min(indexOfLastItem, datasets.length)} of {datasets.length} datasets
                          </div>
                          <div className="flex items-center space-x-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={goToPreviousPage}
                              disabled={currentPage === 1}
                              className="h-8 w-8 p-0"
                            >
                              <ChevronLeft className="h-4 w-4" />
                            </Button>
                            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                              // Show pages around current page
                              let pageNum = 0;
                              if (totalPages <= 5) {
                                // If we have 5 or fewer pages, show all
                                pageNum = i + 1;
                              } else if (currentPage <= 3) {
                                // If we're near the start
                                pageNum = i + 1;
                              } else if (currentPage >= totalPages - 2) {
                                // If we're near the end
                                pageNum = totalPages - 4 + i;
                              } else {
                                // We're in the middle
                                pageNum = currentPage - 2 + i;
                              }
                              
                              return (
                                <Button
                                  key={pageNum}
                                  variant={currentPage === pageNum ? "default" : "outline"}
                                  size="sm"
                                  onClick={() => goToPage(pageNum)}
                                  className="h-8 w-8 p-0"
                                >
                                  {pageNum}
                                </Button>
                              );
                            })}
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={goToNextPage}
                              disabled={currentPage === totalPages}
                              className="h-8 w-8 p-0"
                            >
                              <ChevronRight className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="flex justify-center py-8 text-muted-foreground">
                      <p>No available datasets found. Please ingest data first.</p>
                      <Button
                        variant="link"
                        className="mt-2"
                        onClick={() => (window.location.href = "/datapuur/ingestion")}
                      >
                        Go to Data Ingestion
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </div>

      {/* Modals */}
      {previewModalOpen && selectedDataset && (
        <DatasetPreviewModal
          isOpen={previewModalOpen}
          onClose={() => setPreviewModalOpen(false)}
          datasetId={selectedDataset.id}
          datasetName={selectedDataset.name}
          datasetType={selectedDataset.type}
        />
      )}
      {schemaModalOpen && selectedDataset && (
        <SchemaViewerModal
          isOpen={schemaModalOpen}
          onClose={() => setSchemaModalOpen(false)}
          datasetId={selectedDataset.id}
          datasetName={selectedDataset.name}
          datasetType={selectedDataset.type}
        />
      )}
      {generateKGModalOpen && selectedDataset && (
        <GenerateKGModal
          isOpen={generateKGModalOpen}
          onClose={() => setGenerateKGModalOpen(false)}
          datasetId={selectedDataset.id}
          datasetName={selectedDataset.name}
          datasetType={selectedDataset.type === "transformed" ? "transformed" : "source"}
        />
      )}
    </div>
  )
}

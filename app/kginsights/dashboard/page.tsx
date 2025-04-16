"use client"

import Navbar from "@/components/navbar"
import { SparklesCore } from "@/components/sparkles"
import KGInsightsSidebar from "@/components/kginsights-sidebar"
import { motion } from "framer-motion"
import { Plus, Search, Eye, FileText, PlusCircle, RefreshCw, Trash2, Database, Upload, Settings, LineChart, ChevronLeft, ChevronRight } from "lucide-react"
import { useEffect, useState } from "react"
import { getKGraphDashboard } from "@/lib/api"
import LoadingSpinner from "@/components/loading-spinner"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { useToast } from "@/components/ui/use-toast"
import { useRouter } from "next/navigation"
import { DatasetPreviewModal } from "@/components/kginsights/dataset-preview-modal"
import { SchemaViewerModal } from "@/components/kginsights/schema-viewer-modal"
import { GenerateKGModal } from "@/components/kginsights/generate-kg-modal"
import { KGInsightsLayout } from "@/components/kginsights/kginsights-layout"
import { FloatingChart } from "@/components/floating-chart"
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
  type: string
  status: string
}

interface Neo4jGraph {
  name: string
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
      created: "2025-03-05",
      type: "graph"
    },
    {
      id: "2",
      name: "Supply Chain",
      description: "Supply chain network",
      created: "2025-02-20",
      type: "graph"
    },
  ])

  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loadingDatasets, setLoadingDatasets] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [datasetsError, setDatasetsError] = useState<string | null>(null)
  const [neo4jGraphs, setNeo4jGraphs] = useState<Neo4jGraph[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage] = useState(10)
  const { toast } = useToast()
  const router = useRouter()

  // State for modals
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [schemaModalOpen, setSchemaModalOpen] = useState(false)
  const [generateKGModalOpen, setGenerateKGModalOpen] = useState(false)
  const [selectedDataset, setSelectedDataset] = useState<{ id: string; name: string } | null>(null)
  const [applyToNeo4jModalOpen, setApplyToNeo4jModalOpen] = useState(false)
  const [graphToApply, setGraphToApply] = useState<KnowledgeGraph | null>(null)

  // Function to fetch available datasets from sources
  const fetchDataSources = async () => {
    setLoadingDatasets(true)
    try {
      // Make API call to get data sources
      const response = await fetch("/api/datapuur/sources", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch data sources: ${response.status}`)
      }

      const data = await response.json()

      // Map the data sources to our dataset format
      const availableDatasets = data.map((item: any) => ({
        id: item.id,
        name: item.name,
        type: item.type.toLowerCase(),
        status: "completed",
      }))

      // Reverse the order so newest datasets appear first
      const sortedDatasets = [...availableDatasets].reverse()

      setDatasets(sortedDatasets)
      setDatasetsError(null)
    } catch (err) {
      console.error("Error fetching data sources:", err)
      setDatasetsError("Failed to load available datasets. Using fallback data.")

      // Fallback data
      setDatasets([
        { id: "1", name: "Sales Q1", type: "file", status: "completed" },
        { id: "2", name: "HR Data", type: "file", status: "completed" },
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
            created: schema.created_at ? new Date(schema.created_at).toLocaleDateString() : "N/A",
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
            created: graph.created_at || "N/A",
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
  const handleViewSchema = (id: string, name: string) => {
    setSelectedDataset({ id, name })
    setSchemaModalOpen(true)
  }

  // Function to handle apply to Neo4j
  const handleApplyToNeo4j = (graph: KnowledgeGraph) => {
    setGraphToApply(graph)
    setApplyToNeo4jModalOpen(true)
  }

  // Function to handle dataset preview
  const handlePreview = (datasetId: string, datasetName: string) => {
    setSelectedDataset({ id: datasetId, name: datasetName })
    setPreviewModalOpen(true)
  }

  // Function to handle KG generation
  const handleGenerateKG = (datasetId: string, datasetName: string) => {
    setSelectedDataset({ id: datasetId, name: datasetName })
    setGenerateKGModalOpen(true)
  }

  // Function to handle manage schema
  const handleManageSchema = (graphId: string) => {
    router.push(`/kginsights/manage/${graphId}`)
  }

  // Function to handle insights
  const handleInsights = (graphId: string) => {
    router.push(`/kginsights/insights/${graphId}`)
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
        console.error("Error fetching KGraph dashboard data:", err)
        setError("Failed to load KGraph dashboard data. Using fallback data.")
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
      <div className="flex-1 p-8 flex items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="flex-1 p-8 bg-gradient-to-b from-background to-background/95">
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
        <FloatingChart count={3} />
      </div>

      {showErrorBanner && (
        <div className="bg-yellow-500/20 border border-yellow-500 text-yellow-700 dark:text-yellow-200 px-4 py-2 rounded-md mb-4 relative z-10">
          <p>{error} - Using demo data instead.</p>
        </div>
      )}

      <div className="max-w-6xl mx-auto relative z-10">
        <motion.h1
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-4xl font-bold text-foreground mb-6"
        >
          KGraph Dashboard
        </motion.h1>

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="flex flex-wrap gap-4 mb-8"
        >
          <Button
            className="bg-primary hover:bg-primary/90 text-primary-foreground flex items-center gap-2"
            size="lg"
            onClick={handleNewKnowledgeGraph}
          >
            <Plus className="w-5 h-5" />
            New Knowledge Graph
          </Button>

          <Button
            variant="outline"
            className="border-primary/30 text-foreground flex items-center gap-2"
            size="lg"
            onClick={handleSearchGraphs}
          >
            <Search className="w-5 h-5" />
            Search Graphs...
          </Button>
        </motion.div>

        {/* Knowledge Graphs Section */}
        <motion.div variants={container} initial="hidden" animate="show" className="space-y-8">
          <motion.div variants={item}>
            <Card className="bg-card/80 backdrop-blur-sm border border-border">
              <CardContent className="p-0">
                <div className="p-6">
                  <h2 className="text-2xl font-semibold text-foreground mb-4">Knowledge Graphs</h2>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-t border-b border-border">
                        <th className="px-6 py-3 text-left text-foreground font-medium">Name</th>
                        <th className="px-6 py-3 text-left text-foreground font-medium">Description</th>
                        <th className="px-6 py-3 text-left text-foreground font-medium">Created</th>
                        <th className="px-6 py-3 text-right text-foreground font-medium">Actions</th>
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
                          <td className="px-6 py-4 text-foreground font-medium">{graph.name}</td>
                          <td className="px-6 py-4 text-muted-foreground">{graph.description}</td>
                          <td className="px-6 py-4 text-muted-foreground">{graph.created}</td>
                          <td className="px-6 py-4">
                            <div className="flex justify-end gap-2">
                              {graph.type === "schema" ? (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="text-orange-500 hover:text-orange-600 hover:bg-orange-500/10"
                                    onClick={() => handleViewSchema(graph.id, graph.name)}
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
          <motion.div variants={item}>
            <Card className="bg-card/80 backdrop-blur-sm border border-border mt-8">
              <CardContent className="p-0">
                <div className="p-6 flex justify-between items-center">
                  <h2 className="text-2xl font-semibold text-foreground">Available Datasets for KG Generation</h2>
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

                <div className="overflow-x-auto">
                  {loadingDatasets ? (
                    <div className="flex justify-center items-center py-12">
                      <LoadingSpinner />
                    </div>
                  ) : datasets.length > 0 ? (
                    <>
                      <table className="w-full">
                        <thead>
                          <tr className="border-t border-b border-border">
                            <th className="px-6 py-3 text-left text-foreground font-medium">Dataset</th>
                            <th className="px-6 py-3 text-right text-foreground font-medium">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {currentItems.map((dataset, index) => (
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
                              <td className="px-6 py-4 text-foreground font-medium">
                                <div className="flex flex-col">
                                  <span>{dataset.name}</span>
                                  <span className="text-xs text-muted-foreground capitalize">{dataset.type}</span>
                                </div>
                              </td>
                              <td className="px-6 py-4">
                                <div className="flex justify-end gap-2">
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="text-amber-500 hover:text-amber-600 hover:bg-amber-500/10"
                                    onClick={() => handlePreview(dataset.id, dataset.name)}
                                    title="Preview"
                                  >
                                    <Eye className="w-5 h-5" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="text-orange-500 hover:text-orange-600 hover:bg-orange-500/10"
                                    onClick={() => handleViewSchema(dataset.id, dataset.name)}
                                    title="Schema"
                                  >
                                    <FileText className="w-5 h-5" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="text-primary hover:text-primary/80 hover:bg-primary/10"
                                    onClick={() => handleGenerateKG(dataset.id, dataset.name)}
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
                    <div className="text-center py-12 text-muted-foreground">
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
      {selectedDataset && (
        <>
          <DatasetPreviewModal
            isOpen={previewModalOpen}
            onClose={() => setPreviewModalOpen(false)}
            datasetId={selectedDataset.id}
            datasetName={selectedDataset.name}
          />

          <SchemaViewerModal
            isOpen={schemaModalOpen}
            onClose={() => setSchemaModalOpen(false)}
            datasetId={selectedDataset.id}
            datasetName={selectedDataset.name}
          />

          <GenerateKGModal
            isOpen={generateKGModalOpen}
            onClose={() => setGenerateKGModalOpen(false)}
            datasetId={selectedDataset.id}
            datasetName={selectedDataset.name}
          />
        </>
      )}

      {/* Apply to Neo4j Modal */}
      {applyToNeo4jModalOpen && graphToApply && (
        <AlertDialog
          open={applyToNeo4jModalOpen}
          onOpenChange={(open) => setApplyToNeo4jModalOpen(open)}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Apply Schema to Neo4j</AlertDialogTitle>
            </AlertDialogHeader>
            <AlertDialogDescription>
              Are you sure you want to apply the schema "{graphToApply.name}" to Neo4j?
            </AlertDialogDescription>
            <AlertDialogFooter>
              <AlertDialogAction onClick={confirmApplyToNeo4j}>
                Apply
              </AlertDialogAction>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  )
}

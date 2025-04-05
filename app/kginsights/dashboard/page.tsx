"use client"

import Navbar from "@/components/navbar"
import { SparklesCore } from "@/components/sparkles"
import KGInsightsSidebar from "@/components/kginsights-sidebar"
import { motion } from "framer-motion"
import { Plus, Search, Eye, FileText, PlusCircle, RefreshCw, Trash2, Database } from "lucide-react"
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
  const { toast } = useToast()
  const router = useRouter()

  // State for modals
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [schemaModalOpen, setSchemaModalOpen] = useState(false)
  const [generateKGModalOpen, setGenerateKGModalOpen] = useState(false)
  const [selectedDataset, setSelectedDataset] = useState<{ id: string; name: string } | null>(null)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [graphToDelete, setGraphToDelete] = useState<KnowledgeGraph | null>(null)
  const [applyToNeo4jModalOpen, setApplyToNeo4jModalOpen] = useState(false)
  const [graphToApply, setGraphToApply] = useState<KnowledgeGraph | null>(null)
  const [cleanDatabaseModalOpen, setCleanDatabaseModalOpen] = useState(false)

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

      setDatasets(availableDatasets)
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

  // Function to handle cleaning Neo4j database
  const handleCleanNeo4jDatabase = () => {
    setCleanDatabaseModalOpen(true)
  }

  // Function to execute Neo4j database cleanup
  const executeCleanNeo4jDatabase = async () => {
    try {
      setCleanDatabaseModalOpen(false)
      
      // First, clean up schemas with missing files
      const schemaResponse = await fetch("/api/graphschema/cleanup-schemas", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })

      if (!schemaResponse.ok) {
        throw new Error(`Failed to clean up schemas: ${schemaResponse.status}`)
      }

      const schemaData = await schemaResponse.json()
      
      // Then, clean the Neo4j database
      const neo4jResponse = await fetch("/api/graphschema/clean-neo4j-database", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      })

      if (!neo4jResponse.ok) {
        throw new Error(`Failed to clean Neo4j database: ${neo4jResponse.status}`)
      }

      const neo4jData = await neo4jResponse.json()

      // Show success message with details
      toast({
        title: "Success",
        description: `Database cleaned successfully. Removed ${schemaData.removed} schemas and ${neo4jData.details.nodes_deleted} nodes.`,
        variant: "default",
      })

      // Refresh knowledge graphs after cleanup
      await fetchKnowledgeGraphs()
    } catch (err) {
      console.error("Error cleaning Neo4j database:", err)
      toast({
        title: "Error",
        description: "Failed to clean Neo4j database.",
        variant: "destructive",
      })
    } finally {
      setCleanDatabaseModalOpen(false)
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

  // Function to handle load data to Neo4j
  const handleLoadDataToNeo4j = async (id: string, name: string) => {
    try {
      // Show loading toast
      toast({
        title: "Loading Data",
        description: `Loading data for schema "${name}"...`,
        variant: "default",
      })
      
      // Call the API to load data directly from the schema without specifying a graph
      // The backend will handle graph selection based on available configurations
      const response = await fetch(`/api/graphschema/schemas/${id}/load-data?drop_existing=false`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
          "Content-Type": "application/json",
        },
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Failed to load data: ${response.status}`)
      }
      
      const result = await response.json()
      
      // Show success toast
      toast({
        title: "Success",
        description: `Data loaded successfully for schema "${name}"`,
        variant: "default",
      })
      
    } catch (error) {
      console.error("Error loading data:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to load data",
        variant: "destructive",
      })
    }
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
    router.push("/kginsights/create")
  }

  // Function to handle search graphs
  const handleSearchGraphs = () => {
    router.push("/kginsights/search")
  }

  // Function to handle delete knowledge graph
  const handleDeleteGraph = (graph: KnowledgeGraph) => {
    setGraphToDelete(graph)
    setDeleteModalOpen(true)
  }

  // Function to confirm delete knowledge graph
  const confirmDeleteGraph = async () => {
    if (graphToDelete) {
      try {
        // Use different endpoints based on the graph type
        const endpoint = graphToDelete.type === "schema" 
          ? `/api/graphschema/${graphToDelete.id}` 
          : `/api/kginsights/graphs/${graphToDelete.id}`;
          
        const response = await fetch(endpoint, {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        })

        if (!response.ok) {
          throw new Error(`Failed to delete ${graphToDelete.type}: ${response.status}`)
        }

        setKnowledgeGraphs(knowledgeGraphs.filter((graph) => graph.id !== graphToDelete.id))
        toast({
          title: "Success",
          description: `${graphToDelete.type === "schema" ? "Schema" : "Knowledge graph"} deleted successfully.`,
          variant: "default",
        })
      } catch (err) {
        console.error(`Error deleting ${graphToDelete.type}:`, err)
        toast({
          title: "Error",
          description: `Failed to delete ${graphToDelete.type === "schema" ? "schema" : "knowledge graph"}.`,
          variant: "destructive",
        })
      } finally {
        setDeleteModalOpen(false)
        setGraphToDelete(null)
      }
    }
  }

  // Function to confirm apply to Neo4j
  const confirmApplyToNeo4j = async () => {
    if (graphToApply) {
      await applyToNeo4j(graphToApply)
      setApplyToNeo4jModalOpen(false)
      setGraphToApply(null)
    }
  }

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
    <div className="flex-1 p-8">
      {showErrorBanner && (
        <div className="bg-yellow-500/20 border border-yellow-500 text-yellow-700 dark:text-yellow-200 px-4 py-2 rounded-md mb-4">
          <p>{error} - Using demo data instead.</p>
        </div>
      )}

      <div className="max-w-6xl mx-auto">
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
            className="bg-primary hover:bg-primary/90 text-primary-foreground flex items-center gap-2"
            size="lg"
            onClick={handleCleanNeo4jDatabase}
          >
            <Database className="w-5 h-5" />
            Clean Neo4j Database
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
                        <th className="px-6 py-3 text-left text-foreground font-medium">Actions</th>
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
                            <div className="flex gap-2">
                              {graph.type === "schema" ? (
                                <>
                                  <Button
                                    variant="link"
                                    className="text-orange-500 hover:text-orange-600 hover:bg-orange-500/10"
                                    onClick={() => handleViewSchema(graph.id, graph.name)}
                                  >
                                    View Schema
                                  </Button>
                                  <span className="text-muted-foreground">|</span>
                                  <Button
                                    variant="link"
                                    className="text-blue-500 hover:text-blue-600 hover:bg-blue-500/10"
                                    onClick={() => handleApplyToNeo4j(graph)}
                                  >
                                    Apply to Neo4j
                                  </Button>
                                  <span className="text-muted-foreground">|</span>
                                  <Button
                                    variant="link"
                                    className="text-green-500 hover:text-green-600 hover:bg-green-500/10"
                                    onClick={() => handleLoadDataToNeo4j(graph.id, graph.name)}
                                  >
                                    Load Data
                                  </Button>
                                </>
                              ) : (
                                <Button
                                  variant="link"
                                  className="text-primary hover:text-primary/80 p-0 h-auto"
                                  onClick={() => handleManageSchema(graph.id)}
                                >
                                  Manage Schema
                                </Button>
                              )}
                              <span className="text-muted-foreground">|</span>
                              <Button
                                variant="link"
                                className="text-primary hover:text-primary/80 p-0 h-auto"
                                onClick={() => handleInsights(graph.id)}
                              >
                                Insights
                              </Button>
                              <span className="text-muted-foreground">|</span>
                              <Button
                                variant="link"
                                className="text-red-500 hover:text-red-600 hover:bg-red-500/10"
                                onClick={() => handleDeleteGraph(graph)}
                              >
                                Delete
                              </Button>
                              <span className="text-muted-foreground">|</span>
                              <Button
                                variant="link"
                                className="text-green-500 hover:text-green-600 hover:bg-green-500/10"
                                onClick={() => handleApplyToNeo4j(graph)}
                              >
                                Apply to Neo4j
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
                    <table className="w-full">
                      <thead>
                        <tr className="border-t border-b border-border">
                          <th className="px-6 py-3 text-left text-foreground font-medium">Dataset</th>
                          <th className="px-6 py-3 text-left text-foreground font-medium">Preview</th>
                          <th className="px-6 py-3 text-left text-foreground font-medium">Schema</th>
                          <th className="px-6 py-3 text-left text-foreground font-medium">Generate KG</th>
                        </tr>
                      </thead>
                      <tbody>
                        {datasets.map((dataset, index) => (
                          <motion.tr
                            key={dataset.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.4 + index * 0.1 }}
                            className={cn(
                              "border-b border-border hover:bg-accent/30 transition-colors",
                              index === datasets.length - 1 && "border-b-0",
                            )}
                          >
                            <td className="px-6 py-4 text-foreground font-medium">
                              <div className="flex flex-col">
                                <span>{dataset.name}</span>
                                <span className="text-xs text-muted-foreground capitalize">{dataset.type}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-amber-500 hover:text-amber-600 hover:bg-amber-500/10"
                                onClick={() => handlePreview(dataset.id, dataset.name)}
                              >
                                <Eye className="w-5 h-5" />
                              </Button>
                            </td>
                            <td className="px-6 py-4">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-orange-500 hover:text-orange-600 hover:bg-orange-500/10"
                                onClick={() => handleViewSchema(dataset.id, dataset.name)}
                              >
                                <FileText className="w-5 h-5" />
                              </Button>
                            </td>
                            <td className="px-6 py-4">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-primary hover:text-primary/80 hover:bg-primary/10"
                                onClick={() => handleGenerateKG(dataset.id, dataset.name)}
                              >
                                <PlusCircle className="w-5 h-5" />
                              </Button>
                            </td>
                          </motion.tr>
                        ))}
                      </tbody>
                    </table>
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

      {deleteModalOpen && graphToDelete && (
        <AlertDialog
          open={deleteModalOpen}
          onOpenChange={(open) => setDeleteModalOpen(open)}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Knowledge Graph</AlertDialogTitle>
            </AlertDialogHeader>
            <AlertDialogDescription>
              Are you sure you want to delete the knowledge graph "{graphToDelete.name}"?
            </AlertDialogDescription>
            <AlertDialogFooter>
              <AlertDialogAction onClick={confirmDeleteGraph}>
                Delete
              </AlertDialogAction>
              <AlertDialogCancel onClick={() => setDeleteModalOpen(false)}>
                Cancel
              </AlertDialogCancel>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

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
              Are you sure you want to apply the schema "{graphToApply.name}" to the Neo4j database?
              <p className="mt-2 text-sm text-muted-foreground">
                This will create the necessary node labels, relationships, and constraints in the Neo4j database based on the schema definition.
              </p>
            </AlertDialogDescription>
            <AlertDialogFooter>
              <AlertDialogAction onClick={confirmApplyToNeo4j}>
                Apply
              </AlertDialogAction>
              <AlertDialogCancel onClick={() => setApplyToNeo4jModalOpen(false)}>
                Cancel
              </AlertDialogCancel>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      {cleanDatabaseModalOpen && (
        <AlertDialog
          open={cleanDatabaseModalOpen}
          onOpenChange={(open) => setCleanDatabaseModalOpen(open)}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Clean Neo4j Database</AlertDialogTitle>
            </AlertDialogHeader>
            <AlertDialogDescription>
              Are you sure you want to clean the Neo4j database?
              <p className="mt-2 text-sm text-muted-foreground">
                This will remove schemas where the associated CSV files don't exist and clean up the database.
              </p>
            </AlertDialogDescription>
            <AlertDialogFooter>
              <AlertDialogAction onClick={executeCleanNeo4jDatabase}>
                Clean
              </AlertDialogAction>
              <AlertDialogCancel onClick={() => setCleanDatabaseModalOpen(false)}>
                Cancel
              </AlertDialogCancel>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  )
}

"use client"

import Navbar from "@/components/navbar"
import { SparklesCore } from "@/components/sparkles"
import KGInsightsSidebar from "@/components/kginsights-sidebar"
import { motion } from "framer-motion"
import { Plus, Search, Eye, FileText, PlusCircle, RefreshCw } from "lucide-react"
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
  const { toast } = useToast()
  const router = useRouter()

  // State for modals
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [schemaModalOpen, setSchemaModalOpen] = useState(false)
  const [generateKGModalOpen, setGenerateKGModalOpen] = useState(false)
  const [selectedDataset, setSelectedDataset] = useState<{ id: string; name: string } | null>(null)

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

  // Function to handle dataset preview
  const handlePreview = (datasetId: string, datasetName: string) => {
    setSelectedDataset({ id: datasetId, name: datasetName })
    setPreviewModalOpen(true)
  }

  // Function to handle schema view
  const handleViewSchema = (datasetId: string, datasetName: string) => {
    setSelectedDataset({ id: datasetId, name: datasetName })
    setSchemaModalOpen(true)
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

  if (loading) {
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  // If we have an error but also have dashboard data (from fallback),
  // we'll show a warning but still render the UI
  const showErrorBanner = error

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
                                <Button
                                  variant="link"
                                  className="text-orange-500 hover:text-orange-600 hover:bg-orange-500/10"
                                  onClick={() => handleViewSchema(graph.id, graph.name)}
                                >
                                  View Schema
                                </Button>
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
    </div>
  )
}

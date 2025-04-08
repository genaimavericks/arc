"use client"

import { useEffect, useState, useRef } from "react"
import { useSearchParams } from "next/navigation"
import { SparklesCore } from "@/components/sparkles"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/components/ui/use-toast"
import LoadingSpinner from "@/components/loading-spinner"
import { motion } from "framer-motion"
import { Save, Loader2, MessageSquare } from "lucide-react"
import { Separator } from "@/components/ui/separator"
import Image from "next/image"
import dynamic from 'next/dynamic'
import { KGInsightsLayout } from "@/components/kginsights/kginsights-layout"
import KGInsightsSidebar from "@/components/kginsights-sidebar"
import { FloatingChart } from "@/components/floating-chart"

// Import Cytoscape as a client component to avoid SSR issues
const CytoscapeGraph = dynamic(
  () => import('@/components/cytoscape-graph'),
  { ssr: false }
);

// Import SchemaChat component
import { SchemaChat } from "@/components/kginsights/generate/schema-chat"

// Define interfaces for our data
interface DataSource {
  id: string
  name: string
  type: string
  last_updated: string
  status: string
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

interface Schema {
  nodes: SchemaNode[]
  relationships: SchemaRelationship[]
  indexes?: string[]
  csv_file_path?: string
  name?: string
  description?: string
  source_id?: string
}

export default function GenerateGraphPage() {
  return (
    <KGInsightsLayout>
      <GenerateGraphContent />
    </KGInsightsLayout>
  )
}

function GenerateGraphContent() {
  const searchParams = useSearchParams()
  const [sources, setSources] = useState<DataSource[]>([])
  const [selectedSource, setSelectedSource] = useState<string>("")
  const [selectedSourceName, setSelectedSourceName] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const [loadingSources, setLoadingSources] = useState(true)
  const [schema, setSchema] = useState<Schema | null>(null)
  const [cypher, setCypher] = useState<string>("")
  const [kgName, setKgName] = useState<string>("")
  const [kgDescription, setKgDescription] = useState<string>("")
  const [metadata, setMetadata] = useState<string>("")
  const [showChat, setShowChat] = useState(true)
  const { toast } = useToast()

  // Fetch data sources on component mount
  useEffect(() => {
    const fetchDataSources = async () => {
      try {
        setLoadingSources(true)
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
        setSources(data)
      } catch (error) {
        console.error("Error fetching data sources:", error)
        toast({
          title: "Error",
          description: "Failed to load data sources. Please try again.",
          variant: "destructive",
        })
      } finally {
        setLoadingSources(false)
      }
    }

    fetchDataSources()

    // Check if we have query parameters
    const sourceId = searchParams.get("sourceId")
    const sourceName = searchParams.get("sourceName")
    const name = searchParams.get("kgName")
    const description = searchParams.get("kgDescription")

    if (sourceId && sourceName) {
      setSelectedSource(sourceId)
      setSelectedSourceName(sourceName)
      
      if (name) {
        setKgName(name)
      }
      
      if (description) {
        setKgDescription(description)
      }
    }
  }, [searchParams, toast])

  const handleSourceChange = (value: string) => {
    const source = sources.find(s => s.id === value)
    setSelectedSource(value)
    setSelectedSourceName(source?.name || "")
  }

  const generateSchema = async () => {
    if (!selectedSource) {
      toast({
        title: "Error",
        description: "Please select a data source",
        variant: "destructive",
      })
      return
    }

    // Focus on the chat input
    document.getElementById('schema-chat-input')?.focus()
  }

  // Handle schema generated from chat
  const handleSchemaGenerated = (generatedSchema: Schema, generatedCypher: string) => {
    setSchema(generatedSchema)
    setCypher(generatedCypher)
    
    // If the schema has a csv_file_path, make sure it's preserved
    if (generatedSchema.csv_file_path) {
      console.log("Schema has CSV file path:", generatedSchema.csv_file_path)
    }
  }

  const handleSaveSchema = async () => {
    if (!schema) {
      toast({
        title: "Error",
        description: "No schema to save. Please generate a schema first.",
        variant: "destructive",
      })
      return
    }

    // Generate a default name if none provided
    let schemaName = kgName.trim()
    if (!schemaName) {
      // Use dataset name or a timestamp if no name is provided
      schemaName = selectedSourceName 
        ? `Schema for ${selectedSourceName}` 
        : `Schema ${new Date().toISOString().split('T')[0]}`
      
      // Update the state
      setKgName(schemaName)
    }

    if (!selectedSource) {
      toast({
        title: "Error",
        description: "Please select a data source.",
        variant: "destructive",
      })
      return
    }

    try {
      // Set loading state
      setLoading(true)
      
      console.log("Saving schema:", {
        ...schema,
        name: schemaName,
        description: kgDescription,
        source_id: selectedSource,
      })

      const response = await fetch("/api/graphschema/save-schema", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          schema: {
            ...schema,
            name: schemaName,
            description: kgDescription,
            source_id: selectedSource,
            created_at: new Date().toISOString(),
          },
          csv_file_path: schema.csv_file_path || ""
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => null)
        throw new Error(
          errorData?.detail || `Failed to save schema: ${response.status}`
        )
      }

      const data = await response.json()
      console.log("Schema saved successfully:", data)
      
      toast({
        title: "Success",
        description: `Schema "${schemaName}" saved successfully!`,
      })
    } catch (error) {
      console.error("Error saving schema:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to save schema. Please try again.",
        variant: "destructive",
      })
    } finally {
      // Reset loading state
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 p-4 md:p-6 overflow-y-auto bg-gradient-to-b from-background to-background/95">
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 opacity-15 pointer-events-none">
        <SparklesCore
          id="kgsparkles"
          background="transparent"
          minSize={0.4}
          maxSize={1.5}
          particleDensity={20}
          className="w-full h-full"
          particleColor="#888"
        />
      </div>
      
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
        <FloatingChart count={3} />
      </div>

      <div className="max-w-6xl mx-auto relative z-10">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col gap-4 mb-6"
        >
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">
            Generate Knowledge Graph
          </h1>
          <p className="text-muted-foreground max-w-3xl">
            Convert your structured data into a knowledge graph. Select a data source, generate a schema using AI, and create your knowledge graph.
          </p>
          <Separator className="bg-primary/20" />
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 mb-8"
        >
          <div className="flex flex-col md:flex-row items-start md:items-end gap-4">
            <div className="w-full md:w-64">
              <Label htmlFor="dataset-select" className="mb-2 block text-primary/80 font-medium">Select Dataset:</Label>
              <Select
                value={selectedSource}
                onValueChange={handleSourceChange}
                disabled={loadingSources || loading}
              >
                <SelectTrigger id="dataset-select" className="w-full bg-card/50 backdrop-blur-sm border-primary/20 shadow-sm">
                  <SelectValue placeholder="Select a dataset" />
                </SelectTrigger>
                <SelectContent className="bg-card/95 backdrop-blur-md border-primary/20">
                  {loadingSources ? (
                    <div className="flex justify-center p-2">
                      <LoadingSpinner size="sm" />
                    </div>
                  ) : sources.length > 0 ? (
                    sources.map((source) => (
                      <SelectItem key={source.id} value={source.id}>
                        {source.name}
                      </SelectItem>
                    ))
                  ) : (
                    <div className="p-2 text-center text-muted-foreground">
                      No datasets available
                    </div>
                  )}
                </SelectContent>
              </Select>
            </div>
            
            <div className="w-full md:w-64">
              <Label htmlFor="schema-name" className="mb-2 block text-primary/80 font-medium">Schema Name:</Label>
              <Input
                id="schema-name"
                value={kgName}
                onChange={(e) => setKgName(e.target.value)}
                placeholder="Enter schema name"
                disabled={loading}
                className="w-full bg-card/50 backdrop-blur-sm border-primary/20 shadow-sm"
              />
            </div>
          </div>

          <div className="flex gap-2 self-end md:self-auto">
            <Button
              className="bg-primary hover:bg-primary/90 text-primary-foreground flex items-center gap-2 shadow-md transition-all duration-300 hover:shadow-lg hover:scale-105"
              onClick={generateSchema}
              disabled={!selectedSource || loading}
            >
              <MessageSquare className="h-4 w-4" />
              {loading ? "Generating..." : "Generate Schema"}
            </Button>
            
            <Button
              className="bg-accent hover:bg-accent/90 text-accent-foreground flex items-center gap-2 shadow-md transition-all duration-300 hover:shadow-lg hover:scale-105"
              onClick={handleSaveSchema}
              disabled={loading || (!schema && !selectedSource)}
            >
              <Save className="w-4 h-4" />
              {loading ? "Saving..." : "Save Schema"}
            </Button>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left column - Chat Interface */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Card className="bg-card/90 backdrop-blur-sm border border-primary/20 shadow-xl overflow-hidden">
              <CardContent className="p-4 md:p-6">
                <div className="flex flex-col gap-2 mb-4">
                  <h2 className="text-xl font-semibold flex items-center gap-2">
                    <MessageSquare className="h-5 w-5 text-primary" />
                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">GenAI Assistant</span>
                  </h2>
                  <Separator className="bg-primary/10" />
                </div>
                <div className="h-[600px] relative">
                  <SchemaChat 
                    selectedSource={selectedSource}
                    selectedSourceName={selectedSourceName}
                    onSchemaGenerated={handleSchemaGenerated}
                    loading={loading}
                    setLoading={setLoading}
                  />
                </div>
              </CardContent>
            </Card>
          </motion.div>
          
          {/* Right column - Schema Visualization and Details */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Card className="bg-card/90 backdrop-blur-sm border border-primary/20 shadow-xl overflow-hidden">
              <CardContent className="p-4 md:p-6">
                {loading ? (
                  <div className="flex flex-col items-center justify-center py-12 h-[600px]">
                    <motion.div
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ duration: 0.3, repeat: Infinity, repeatType: "reverse" }}
                    >
                      <LoadingSpinner size="default" />
                    </motion.div>
                    <p className="mt-4 text-muted-foreground animate-pulse">Generating schema...</p>
                  </div>
                ) : schema ? (
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.5 }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h2 className="text-xl font-semibold flex items-center gap-2">
                        <Save className="h-5 w-5 text-accent" />
                        <span className="bg-clip-text text-transparent bg-gradient-to-r from-accent to-primary">Recommended Schema</span>
                      </h2>
                    </div>
                    <Separator className="bg-accent/10 mb-4" />
                    
                    {/* Visualization Section */}
                    <div className="mb-6 relative">
                      <div className="border rounded-lg overflow-hidden shadow-md">
                        <div className="bg-muted/30 p-3 border-b border-border/40">
                          <h3 className="text-md font-medium text-primary/90">Graph Visualization</h3>
                        </div>
                        <div className="bg-background p-0">
                          <div className="h-[300px] w-full">
                            <CytoscapeGraph 
                              schema={schema} 
                              showContainer={false} 
                              showTitle={false} 
                              height="300px" 
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Schema Details Section */}
                    <div className="space-y-4">
                      {/* Nodes Card */}
                      <div className="border rounded-lg overflow-hidden shadow-md bg-background">
                        <div className="bg-muted/30 p-3 border-b border-border/40 flex justify-between items-center">
                          <h3 className="text-md font-medium text-primary/90">Nodes</h3>
                          <span className="text-xs text-muted-foreground bg-muted/50 px-2 py-1 rounded">
                            {schema.nodes.length} node{schema.nodes.length !== 1 ? 's' : ''}
                          </span>
                        </div>
                        <div className="p-4">
                          <div className="max-h-[180px] overflow-y-auto custom-scrollbar pr-2">
                            <ul className="space-y-2">
                              {schema.nodes.map((node, index) => (
                                <motion.li 
                                  key={index}
                                  initial={{ opacity: 0, x: -5 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ duration: 0.2, delay: index * 0.05 }}
                                  className="bg-muted/30 p-3 rounded-md hover:bg-muted/40 transition-colors border border-border/20"
                                >
                                  <div className="flex flex-col">
                                    <span className="font-semibold text-foreground/90 mb-1">{node.label}</span> 
                                    <div className="text-muted-foreground text-sm">
                                      {Object.entries(node.properties || {}).map(([key, type], idx) => (
                                        <span key={idx} className="inline-block mr-2 mb-1 bg-background/70 px-1.5 py-0.5 rounded border border-border/30">
                                          <span className="font-medium">{key}:</span> {type}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                </motion.li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>
                      
                      {/* Relationships Card */}
                      {schema.relationships.length > 0 && (
                        <div className="border rounded-lg overflow-hidden shadow-md bg-background">
                          <div className="bg-muted/30 p-3 border-b border-border/40 flex justify-between items-center">
                            <h3 className="text-md font-medium text-accent/90">Relationships</h3>
                            <span className="text-xs text-muted-foreground bg-muted/50 px-2 py-1 rounded">
                              {schema.relationships.length} relationship{schema.relationships.length !== 1 ? 's' : ''}
                            </span>
                          </div>
                          <div className="p-4">
                            <div className="max-h-[180px] overflow-y-auto custom-scrollbar pr-2">
                              <ul className="space-y-2">
                                {schema.relationships.map((rel, index) => (
                                  <motion.li 
                                    key={index}
                                    initial={{ opacity: 0, x: -5 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ duration: 0.2, delay: index * 0.05 }}
                                    className="bg-muted/30 p-3 rounded-md hover:bg-muted/40 transition-colors border border-border/20"
                                  >
                                    <div className="flex flex-col">
                                      <div className="flex items-center gap-1 mb-1 flex-wrap">
                                        <span className="font-medium text-foreground/90">{rel.startNode}</span> 
                                        <span className="mx-1 text-accent font-mono whitespace-nowrap">-[{rel.type}]-&gt;</span>
                                        <span className="font-medium text-foreground/90">{rel.endNode}</span>
                                      </div>
                                      {rel.properties && Object.keys(rel.properties).length > 0 && (
                                        <div className="text-muted-foreground text-sm mt-1">
                                          {Object.entries(rel.properties).map(([key, type], idx) => (
                                            <span key={idx} className="inline-block mr-2 mb-1 bg-background/70 px-1.5 py-0.5 rounded border border-border/30">
                                              <span className="font-medium">{key}:</span> {type}
                                            </span>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  </motion.li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* Indexes Card */}
                      {schema.indexes && schema.indexes.length > 0 && (
                        <div className="border rounded-lg overflow-hidden shadow-md bg-background">
                          <div className="bg-muted/30 p-3 border-b border-border/40 flex justify-between items-center">
                            <h3 className="text-md font-medium text-secondary/90">Indexes</h3>
                            <span className="text-xs text-muted-foreground bg-muted/50 px-2 py-1 rounded">
                              {schema.indexes.length} index{schema.indexes.length !== 1 ? 'es' : ''}
                            </span>
                          </div>
                          <div className="p-4">
                            <div className="max-h-[150px] overflow-y-auto custom-scrollbar pr-2">
                              <ul className="space-y-2">
                                {schema.indexes.map((index, i) => (
                                  <motion.li 
                                    key={i}
                                    initial={{ opacity: 0, x: -5 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ duration: 0.2, delay: i * 0.05 }}
                                    className="bg-muted/30 p-2 rounded-md hover:bg-muted/40 transition-colors border border-border/20"
                                  >
                                    {index}
                                  </motion.li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* Notes Card */}
                      <div className="border rounded-lg overflow-hidden shadow-md bg-background">
                        <div className="bg-muted/30 p-3 border-b border-border/40">
                          <h3 className="text-md font-medium text-secondary/90">Notes</h3>
                        </div>
                        <div className="p-4">
                          <p className="text-sm text-muted-foreground bg-muted/20 p-3 rounded-md border border-border/30">
                            This schema captures the structure of your TelecomChurn data with appropriate indexes for optimal query performance. Property types have been mapped to match the original CSV column data types.
                          </p>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ) : selectedSource ? (
                  <div className="flex flex-col items-center justify-center py-12 h-[600px]">
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5 }}
                      className="text-center"
                    >
                      <Save className="h-16 w-16 text-muted-foreground/40 mx-auto mb-4" />
                      <p className="text-muted-foreground">Use the chat to generate a recommended graph schema.</p>
                      <p className="text-sm text-muted-foreground/70 mt-2">Type your request in the chat assistant on the left.</p>
                    </motion.div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 h-[600px]">
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5 }}
                      className="text-center"
                    >
                      <Save className="h-16 w-16 text-muted-foreground/40 mx-auto mb-4" />
                      <p className="text-muted-foreground">Select a dataset to get started.</p>
                      <p className="text-sm text-muted-foreground/70 mt-2">Choose a dataset from the dropdown above.</p>
                    </motion.div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </div>
  )
}

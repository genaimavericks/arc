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
    <div className="flex-1 p-6 overflow-y-auto">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col gap-4 mb-6">
          <h1 className="text-3xl font-bold">Generate Knowledge Graph</h1>
          <p className="text-muted-foreground max-w-3xl">
            Convert your structured data into a knowledge graph. Select a data source, generate a schema using AI, and create your knowledge graph.
          </p>
        </div>

        <div className="flex justify-between items-center mb-8">
          <div className="space-y-4">
            <div className="w-64">
              <Label htmlFor="dataset-select" className="mb-2 block">Select Dataset:</Label>
              <Select
                value={selectedSource}
                onValueChange={handleSourceChange}
                disabled={loadingSources || loading}
              >
                <SelectTrigger id="dataset-select" className="w-full">
                  <SelectValue placeholder="Select a dataset" />
                </SelectTrigger>
                <SelectContent>
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
            
            <div className="w-64">
              <Label htmlFor="schema-name" className="mb-2 block">Schema Name:</Label>
              <Input
                id="schema-name"
                value={kgName}
                onChange={(e) => setKgName(e.target.value)}
                placeholder="Enter schema name"
                disabled={loading}
                className="w-full"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              className="bg-primary hover:bg-primary/90 text-primary-foreground flex items-center gap-2"
              onClick={generateSchema}
              disabled={!selectedSource || loading}
            >
              <MessageSquare className="h-4 w-4" />
              {loading ? "Generating..." : "Generate Schema"}
            </Button>
            
            <Button
              className="bg-primary hover:bg-primary/90 text-primary-foreground flex items-center gap-2"
              onClick={handleSaveSchema}
              disabled={loading || (!schema && !selectedSource)}
            >
              <Save className="w-4 h-4" />
              {loading ? "Saving..." : "Save Schema Version"}
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left column - Chat Interface */}
          <Card className="bg-card/80 backdrop-blur-sm border border-border">
            <CardContent className="p-6">
              <div className="flex flex-col gap-2 mb-4">
                <h2 className="text-xl font-semibold">GenAI Bot</h2>
              </div>
              <div className="h-[600px]">
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
          
          {/* Right column - Schema Visualization and Details */}
          <Card className="bg-card/80 backdrop-blur-sm border border-border">
            <CardContent className="p-6">
              {loading ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <LoadingSpinner />
                  <p className="mt-4 text-muted-foreground">Generating schema...</p>
                </div>
              ) : schema ? (
                <div className="space-y-6">
                  <h2 className="text-xl font-semibold">Recommended Schema:</h2>
                  
                  <div className="space-y-6">
                    {/* Graph Visualization */}
                    <div className="border rounded-md p-4 bg-background/50">
                      <CytoscapeGraph schema={schema} />
                    </div>
                    
                    {/* Schema Details */}
                    <div className="space-y-4">
                      <div>
                        <h3 className="text-lg font-medium mb-2">Nodes:</h3>
                        <ul className="list-disc pl-5 space-y-1">
                          {schema.nodes.map((node, index) => (
                            <li key={index}>
                              <span className="font-medium">{node.label}</span> 
                              ({Object.entries(node.properties || {}).map(([key, type]) => `${key}: ${type}`).join(", ")})
                            </li>
                          ))}
                        </ul>
                      </div>
                      
                      <div>
                        <h3 className="text-lg font-medium mb-2">Relationships:</h3>
                        <ul className="list-disc pl-5 space-y-1">
                          {schema.relationships.map((rel, index) => (
                            <li key={index}>
                              <span className="font-medium">{rel.startNode}</span> 
                              <span className="mx-1">-[{rel.type}]-&gt;</span>
                              <span className="font-medium">{rel.endNode}</span>
                              {rel.properties && Object.keys(rel.properties).length > 0 && (
                                <span className="ml-2">
                                  ({Object.entries(rel.properties).map(([key, type]) => `${key}: ${type}`).join(", ")})
                                </span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                      
                      {schema.indexes && schema.indexes.length > 0 && (
                        <div>
                          <h3 className="text-lg font-medium mb-2">Indexes:</h3>
                          <ul className="list-disc pl-5 space-y-1">
                            {schema.indexes.map((index, i) => (
                              <li key={i}>{index}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      <div>
                        <h3 className="text-lg font-medium mb-2">Justification:</h3>
                        <p className="text-muted-foreground">
                          This schema captures the relationships between the entities in your data 
                          while maintaining appropriate properties and constraints for optimal graph traversal.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              ) : selectedSource ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <p className="text-muted-foreground">Use the chat to generate a recommended graph schema.</p>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12">
                  <p className="text-muted-foreground">Select a dataset to get started.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

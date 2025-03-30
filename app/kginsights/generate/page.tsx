"use client"

import { useEffect, useState, useRef } from "react"
import { useSearchParams } from "next/navigation"
import Navbar from "@/components/navbar"
import { SparklesCore } from "@/components/sparkles"
import KGInsightsSidebar from "@/components/kginsights-sidebar"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/components/ui/use-toast"
import LoadingSpinner from "@/components/loading-spinner"
import ProtectedRoute from "@/components/protected-route"
import { motion } from "framer-motion"
import { Save, Loader2 } from "lucide-react"
import { Separator } from "@/components/ui/separator"
import Image from "next/image"
import dynamic from 'next/dynamic'

// Import Cytoscape as a client component to avoid SSR issues
const CytoscapeGraph = dynamic(
  () => import('@/components/cytoscape-graph'),
  { ssr: false }
);

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
}

export default function GenerateGraphPage() {
  return (
    <ProtectedRoute requiredPermission="kginsights:read">
      <GenerateGraphContent />
    </ProtectedRoute>
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

    try {
      setLoading(true)
      setSchema(null)
      setCypher("")

      const response = await fetch("/api/graphschema/build-schema-from-source", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          source_id: selectedSource,
          metadata: metadata
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to generate schema: ${response.status}`)
      }

      const data = await response.json()
      setSchema(data.schema)
      setCypher(data.cypher)

      toast({
        title: "Success",
        description: "Schema generated successfully!",
      })
    } catch (error) {
      console.error("Error generating schema:", error)
      toast({
        title: "Error",
        description: "Failed to generate schema. Please try again.",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
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

    if (!kgName.trim()) {
      toast({
        title: "Error",
        description: "Please provide a name for the schema.",
        variant: "destructive",
      })
      return
    }

    try {
      const response = await fetch("/api/graphschema/save-schema", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          schema: {
            ...schema,
            name: kgName,
            description: kgDescription,
            source_id: selectedSource,
            created_at: new Date().toISOString(),
          }
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to save schema: ${response.status}`)
      }

      const data = await response.json()
      toast({
        title: "Success",
        description: `Schema "${kgName}" saved successfully!`,
      })
    } catch (error) {
      console.error("Error saving schema:", error)
      toast({
        title: "Error",
        description: "Failed to save schema. Please try again.",
        variant: "destructive",
      })
    }
  }

  return (
    <main className="min-h-screen bg-background antialiased relative overflow-hidden">
      {/* Ambient background with moving particles */}
      <div className="h-full w-full absolute inset-0 z-0">
        <SparklesCore
          id="tsparticlesfullpage"
          background="transparent"
          minSize={0.6}
          maxSize={1.4}
          particleDensity={100}
          className="w-full h-full"
          particleColor="var(--foreground)"
        />
      </div>

      <div className="relative z-10">
        <Navbar />

        <div className="flex">
          <KGInsightsSidebar />

          <div className="flex-1 p-8">
            <div className="max-w-7xl mx-auto">
              <motion.h1
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="text-4xl font-bold text-foreground mb-6"
              >
                Generate Graph
              </motion.h1>

              <div className="flex justify-between items-center mb-8">
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

                <div className="w-full mb-4">
                  <Label htmlFor="metadata-input" className="mb-2 block">META:</Label>
                  <Textarea
                    id="metadata-input"
                    placeholder="Meta data about data, like which data it is, which business function it belongs to."
                    className="w-full"
                    value={metadata}
                    onChange={(e) => setMetadata(e.target.value)}
                    disabled={loading}
                  />
                </div>

                <div className="flex gap-2">
                  <Button
                    className="bg-primary hover:bg-primary/90 text-primary-foreground"
                    onClick={generateSchema}
                    disabled={!selectedSource || loading}
                  >
                    {loading ? (
                      <>
                        <LoadingSpinner size="sm" />
                        <span className="ml-2">Generating...</span>
                      </>
                    ) : (
                      "Generate Schema"
                    )}
                  </Button>
                  
                  <Button
                    className="bg-primary hover:bg-primary/90 text-primary-foreground flex items-center gap-2"
                    onClick={handleSaveSchema}
                    disabled={!schema || loading}
                  >
                    <Save className="w-4 h-4" />
                    Save Schema Version
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-6">
                {/* Schema Visualization and Details */}
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
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                              <h3 className="text-lg font-medium mb-2">Cypher Script:</h3>
                              <pre className="bg-gray-100 p-4 rounded-md overflow-auto max-h-96">
                                {cypher}
                              </pre>
                            </div>
                          </div>
                          
                          {/* Graph Visualization */}
                          <div>
                            <CytoscapeGraph schema={schema} />
                          </div>
                        </div>
                      </div>
                    ) : selectedSource ? (
                      <div className="flex flex-col items-center justify-center py-12">
                        <p className="text-muted-foreground">Click "Generate Schema" to create a recommended graph schema.</p>
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
        </div>
      </div>
    </main>
  )
}

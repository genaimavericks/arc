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
import { Save, Loader2, MessageSquare, CheckCircle, AlertTriangle, XCircle } from "lucide-react"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import Image from "next/image"
import dynamic from 'next/dynamic'
import { KGInsightsLayout } from "@/components/kginsights/kginsights-layout"
import KGInsightsSidebar from "@/components/kginsights-sidebar"
import { FloatingChart } from "@/components/floating-chart"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { SchemaChat } from "@/components/kginsights/generate/schema-chat"

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
  const [domain, setDomain] = useState<string>("")
  const [metadata, setMetadata] = useState<string>("")
  const [showChat, setShowChat] = useState(true)
  const [savingStatus, setSavingStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle')
  const [showSuccessMessage, setShowSuccessMessage] = useState(false)
  const [savedSchemaInfo, setSavedSchemaInfo] = useState<{name: string, path: string}>({name: "", path: ""})
  const [showErrorDialog, setShowErrorDialog] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const successMessageTimeoutRef = useRef<NodeJS.Timeout | null>(null)
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
      // Set loading and saving status
      setLoading(true)
      setSavingStatus('saving')
      
      // Show toast to indicate saving is in progress
      toast({
        title: "Saving Schema",
        description: "Please wait while your schema is being saved...",
      })
      
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
        console.log('Error response:', response.status, errorData)
        
        // Handle specific error for duplicate schema name (409 Conflict)
        if (response.status === 409) {
          const errorMsg = `A schema with the name "${schemaName}" already exists. Please use a different name.`;
          
          // Set error message and show error dialog
          setErrorMessage(errorMsg);
          setShowErrorDialog(true);
          
          throw new Error(errorMsg);
        }
        else {
          const errorMsg = `Error occured while saving schema. Please try after some time.`;
          
          // Set error message and show error dialog
          setErrorMessage(errorMsg);
          setShowErrorDialog(true);
          
          throw new Error(errorMsg);

        }
        
        // Extract error message from response if available
        const errorMessage = errorData?.detail || `Failed to save schema: ${response.status}`
        throw new Error(errorMessage)
      }

      const data = await response.json()
      console.log("Schema saved successfully:", data)
      
      // Set success status
      setSavingStatus('success')
      
      // Set saved schema info for the success message
      const schemaInfo = {
        name: schemaName,
        path: data.file_path || ""
      };
      console.log("Setting saved schema info:", schemaInfo);
      setSavedSchemaInfo(schemaInfo);
      
      // Show success message
      console.log("Opening success message");
      setShowSuccessMessage(true);
      
      // Clear any existing timeout
      if (successMessageTimeoutRef.current) {
        clearTimeout(successMessageTimeoutRef.current);
      }
      
      toast({
        title: "Success",
        description: `Schema "${schemaName}" saved successfully!`,
      })
      
      // Reset success status after 3 seconds
      setTimeout(() => {
        setSavingStatus('idle')
      }, 3000)
      
    } catch (error) {
      console.error("Error saving schema:", error)
      
      // Set error status
      setSavingStatus('error')
      
      // Get error message
      const errorMessage = error instanceof Error ? error.message : "Failed to save schema. Please try again."
      console.log('Displaying error toast with message:', errorMessage)
      
      // Show prominent error toast with longer duration
      toast({
        title: "Schema Save Error",
        description: errorMessage,
        variant: "destructive",
        duration: 6000, // Show for 6 seconds for better visibility
      })
      
      // Reset error status after 3 seconds
      setTimeout(() => {
        setSavingStatus('idle')
      }, 3000)
      
    } finally {
      // Reset loading state
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 p-4 md:p-6 overflow-y-auto bg-gradient-to-b from-background to-background/95">
      {/* Enhanced animated background with particles and floating elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 opacity-20 pointer-events-none">
        <SparklesCore
          id="kgsparkles"
          background="transparent"
          minSize={0.6}
          maxSize={1.8}
          particleDensity={120}
          className="w-full h-full"
          particleColor="var(--primary)"
        />
      </div>
      
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
        <FloatingChart count={5} />
      </div>

      <div className="max-w-7xl mx-auto relative z-10 min-h-[calc(100vh-120px)] flex flex-col">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="flex flex-col gap-4 mb-6"
        >
          <h1 className="text-4xl font-bold text-foreground">
            Generate Knowledge Graph
          </h1>
          <p className="text-foreground max-w-3xl text-lg">
            Transform your structured data into an interactive knowledge graph. Select a dataset, generate a schema using AI, and visualize your data relationships.
          </p>
          <Separator className="bg-primary/20 h-0.5 rounded-full" />
        </motion.div>

        {/* Improved control panel with animated transitions */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1, ease: "easeOut" }}
          className="bg-card/80 backdrop-blur-md border border-primary/20 rounded-xl p-6 mb-10 shadow-lg"
        >
          <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-6">
            <div className="flex flex-col md:flex-row items-start md:items-end gap-6 flex-wrap">
              <div className="w-full md:w-64">
                <Label htmlFor="dataset-select" className="mb-2 block text-foreground font-medium text-base">Select Dataset</Label>
                <Select
                  value={selectedSource}
                  onValueChange={handleSourceChange}
                  disabled={loadingSources || loading}
                >
                  <SelectTrigger id="dataset-select" className="w-full bg-background/70 backdrop-blur-sm border-primary/30 shadow-sm transition-all duration-300 hover:border-primary/50 h-11">
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
                <Label htmlFor="schema-name" className="mb-2 block text-foreground font-medium text-base">Schema Name</Label>
                <Input
                  id="schema-name"
                  value={kgName}
                  onChange={(e) => setKgName(e.target.value)}
                  placeholder="Enter schema name"
                  disabled={loading}
                  className="w-full bg-background/70 backdrop-blur-sm border-primary/30 shadow-sm transition-all duration-300 hover:border-primary/50 h-11"
                />
              </div>
            </div>

            <div className="flex gap-3 self-end md:self-auto">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
                <Button
                  className="bg-primary hover:bg-primary/90 text-primary-foreground flex items-center gap-2 shadow-md transition-all duration-300 hover:shadow-lg px-6 py-6 h-11 font-medium"
                  onClick={generateSchema}
                  disabled={!selectedSource || loading}
                >
                  <MessageSquare className="h-5 w-5" />
                  {loading ? "Generating..." : "Generate Schema"}
                </Button>
              </motion.div>
              
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
                <Button
                  className={`flex items-center gap-2 shadow-md transition-all duration-300 hover:shadow-lg px-6 h-11 font-medium
                    ${savingStatus === 'error' ? 'bg-red-500 hover:bg-red-600 text-white' : 
                      savingStatus === 'success' ? 'bg-green-500 hover:bg-green-600 text-white' : 
                      'bg-accent hover:bg-accent/90 text-accent-foreground'}`}
                  onClick={handleSaveSchema}
                  disabled={loading || (!schema && !selectedSource) || savingStatus === 'saving'}
                >
                  {savingStatus === 'saving' ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Saving Schema...
                    </>
                  ) : savingStatus === 'success' ? (
                    <>
                      <CheckCircle className="w-5 h-5" />
                      Saved!
                    </>
                  ) : savingStatus === 'error' ? (
                    <>
                      <XCircle className="w-5 h-5" />
                      Failed
                    </>
                  ) : (
                    <>
                      <Save className="w-5 h-5" />
                      Save Schema
                    </>
                  )}
                </Button>
              </motion.div>
            </div>
            
            <div className="w-full md:w-64">
              <Label htmlFor="domain-select" className="mb-2 block text-primary/80 font-medium">Data Domain:</Label>
              <Select
                value={domain}
                onValueChange={setDomain}
                disabled={loading}
              >
                <SelectTrigger id="domain-select" className="w-full bg-card/50 backdrop-blur-sm border-primary/20 shadow-sm">
                  <SelectValue placeholder="Select domain" />
                </SelectTrigger>
                <SelectContent className="bg-card/95 backdrop-blur-md border-primary/20">
                  <SelectItem value="telecom_churn">Telecom Churn</SelectItem>
                  <SelectItem value="foam_factory">Foam Factory</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 flex-1">
          {/* Left column - Chat Interface */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2, ease: "easeOut" }}
          >
            <Card className="bg-card/90 backdrop-blur-sm border border-primary/20 shadow-xl overflow-hidden rounded-xl h-full">
              <CardContent className="p-6">
                <div className="flex flex-col gap-3 mb-5">
                  <h2 className="text-xl font-semibold flex items-center gap-2 text-foreground">
                    <MessageSquare className="h-5 w-5 text-foreground" />
                    <span>AI Assistant</span>
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    Describe the knowledge graph you want to create from your dataset. The AI will help you generate an optimal schema.
                  </p>
                  <Separator className="bg-primary/10" />
                </div>
                <div className="h-[calc(100vh-280px)] relative bg-background/40 rounded-lg border border-primary/10">
                  <SchemaChat 
                    selectedSource={selectedSource}
                    selectedSourceName={selectedSourceName}
                    domain={domain}
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
            transition={{ duration: 0.6, delay: 0.3, ease: "easeOut" }}
          >
            <Card className="bg-card/90 backdrop-blur-sm border border-primary/20 shadow-xl overflow-hidden rounded-xl h-full">
              <CardContent className="p-6">
                {loading ? (
                  <div className="flex flex-col items-center justify-center py-12 h-[calc(100vh-280px)] bg-background/40 rounded-lg border border-primary/10">
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5 }}
                      className="text-center"
                    >
                      <div className="relative w-32 h-32 mx-auto mb-6">
                        <motion.div
                          animate={{ 
                            scale: [1, 1.05, 1],
                            opacity: [0.7, 1, 0.7]
                          }}
                          transition={{ 
                            duration: 3,
                            repeat: Infinity,
                            ease: "easeInOut"
                          }}
                          className="absolute inset-0 bg-primary/5 rounded-full"
                        />
                        <motion.div
                          animate={{ 
                            scale: [1, 1.1, 1],
                            opacity: [0.5, 0.8, 0.5]
                          }}
                          transition={{ 
                            duration: 4,
                            repeat: Infinity,
                            ease: "easeInOut",
                            delay: 0.5
                          }}
                          className="absolute inset-0 bg-primary/5 rounded-full"
                        />
                        <LoadingSpinner size="default" />
                      </div>
                      <p className="mt-6 text-foreground font-medium">Generating Schema</p>
                      <p className="text-sm text-muted-foreground">Please wait while we analyze your data...</p>
                    </motion.div>
                  </div>
                ) : schema ? (
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.5 }}
                    className="space-y-6"
                  >
                    <div className="flex items-center justify-between">
                      <h2 className="text-xl font-semibold flex items-center gap-2 text-foreground">
                        <Save className="h-5 w-5 text-foreground" />
                        <span>Knowledge Graph Schema</span>
                      </h2>
                    </div>
                    <Separator className="bg-primary/10" />
                    
                    {/* Enhanced Visualization Section */}
                    <motion.div 
                      initial={{ y: 20, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      transition={{ duration: 0.4 }}
                      className="mb-6 relative"
                    >
                      <div className="border rounded-xl overflow-hidden shadow-lg border-primary/20 bg-background/40">
                        <div className="bg-primary/10 p-3 border-b border-primary/20 flex justify-between items-center">
                          <h3 className="text-md font-medium text-foreground">Graph Visualization</h3>
                          <Badge variant="outline" className="bg-background/70 text-foreground border-primary/20">
                            {schema.nodes.length} nodes • {schema.relationships.length} relationships
                          </Badge>
                        </div>
                        <div className="bg-background/20 p-0">
                          <div className="h-[320px] w-full">
                            <CytoscapeGraph 
                              schema={schema} 
                              showContainer={false} 
                              showTitle={false} 
                              height="320px" 
                            />
                          </div>
                        </div>
                      </div>
                    </motion.div>
                    
                    {/* Tabs for Schema Details */}
                    <div className="space-y-5">
                      <div className="flex flex-wrap gap-4">
                        <motion.div 
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          className="flex-1 min-w-[250px]"
                        >
                          <div className="border rounded-xl overflow-hidden shadow-md bg-background/40 border-primary/20 h-full">
                            <div className="bg-primary/10 p-3 border-b border-primary/20 flex justify-between items-center">
                              <h3 className="text-md font-medium text-foreground">Nodes</h3>
                              <Badge variant="outline" className="bg-background/70 text-foreground border-primary/20">
                                {schema.nodes.length}
                              </Badge>
                            </div>
                            <div className="p-4">
                              <div className="max-h-[200px] overflow-y-auto custom-scrollbar pr-2">
                                <ul className="space-y-3">
                                  {schema.nodes.map((node, index) => (
                                    <motion.li 
                                      key={index}
                                      initial={{ opacity: 0, y: 5 }}
                                      animate={{ opacity: 1, y: 0 }}
                                      transition={{ duration: 0.2, delay: index * 0.05 }}
                                      className="bg-card/80 p-3 rounded-lg hover:bg-card/90 transition-all duration-300 border border-primary/10 hover:border-primary/30 hover:shadow-md"
                                    >
                                      <div className="flex flex-col">
                                        <span className="font-semibold text-foreground mb-2">{node.label}</span> 
                                        <div className="text-muted-foreground text-sm">
                                          {Object.entries(node.properties || {}).map(([key, type], idx) => (
                                            <span key={idx} className="inline-block mr-2 mb-2 bg-background/70 px-2 py-1 rounded-md border border-primary/10 text-xs">
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
                        </motion.div>
                        
                        {schema.relationships.length > 0 && (
                          <motion.div 
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className="flex-1 min-w-[250px]"
                          >
                            <div className="border rounded-xl overflow-hidden shadow-md bg-background/40 border-primary/20 h-full">
                              <div className="bg-primary/10 p-3 border-b border-primary/20 flex justify-between items-center">
                                <h3 className="text-md font-medium text-foreground">Relationships</h3>
                                <Badge variant="outline" className="bg-background/70 text-foreground border-primary/20">
                                  {schema.relationships.length}
                                </Badge>
                              </div>
                              <div className="p-4">
                                <div className="max-h-[200px] overflow-y-auto custom-scrollbar pr-2">
                                  <ul className="space-y-3">
                                    {schema.relationships.map((rel, index) => (
                                      <motion.li 
                                        key={index}
                                        initial={{ opacity: 0, y: 5 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.2, delay: index * 0.05 }}
                                        className="bg-card/80 p-3 rounded-lg hover:bg-card/90 transition-all duration-300 border border-primary/10 hover:border-primary/30 hover:shadow-md"
                                      >
                                        <div className="flex flex-col">
                                          <div className="flex items-center gap-1 mb-2 flex-wrap">
                                            <span className="font-medium text-foreground">{rel.startNode}</span> 
                                            <span className="mx-1 text-primary font-mono whitespace-nowrap">-[{rel.type}]-&gt;</span>
                                            <span className="font-medium text-foreground">{rel.endNode}</span>
                                          </div>
                                          {rel.properties && Object.keys(rel.properties).length > 0 && (
                                            <div className="text-muted-foreground text-sm mt-1">
                                              {Object.entries(rel.properties).map(([key, type], idx) => (
                                                <span key={idx} className="inline-block mr-2 mb-2 bg-background/70 px-2 py-1 rounded-md border border-primary/10 text-xs">
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
                          </motion.div>
                        )}
                      </div>
                      
                      {/* Indexes and Notes in a single row */}
                      <div className="flex flex-wrap gap-4">
                        {schema.indexes && schema.indexes.length > 0 && (
                          <motion.div 
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className="flex-1 min-w-[250px]"
                          >
                            <div className="border rounded-xl overflow-hidden shadow-md bg-background/40 border-primary/20 h-full">
                              <div className="bg-primary/10 p-3 border-b border-primary/20 flex justify-between items-center">
                                <h3 className="text-md font-medium text-foreground">Indexes</h3>
                                <Badge variant="outline" className="bg-background/70 text-foreground border-primary/20">
                                  {schema.indexes.length}
                                </Badge>
                              </div>
                              <div className="p-4">
                                <div className="max-h-[150px] overflow-y-auto custom-scrollbar pr-2">
                                  <ul className="space-y-3">
                                    {schema.indexes.map((index, i) => (
                                      <motion.li 
                                        key={i}
                                        initial={{ opacity: 0, y: 5 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.2, delay: i * 0.05 }}
                                        className="bg-card/80 p-3 rounded-lg hover:bg-card/90 transition-all duration-300 border border-primary/10 hover:border-primary/30"
                                      >
                                        <code className="text-sm text-foreground">{index}</code>
                                      </motion.li>
                                    ))}
                                  </ul>
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        )}
                        
                        <motion.div 
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          className="flex-1 min-w-[250px]"
                        >
                          <div className="border rounded-xl overflow-hidden shadow-md bg-background/40 border-primary/20 h-full">
                            <div className="bg-primary/10 p-3 border-b border-primary/20">
                              <h3 className="text-md font-medium text-foreground">Notes</h3>
                            </div>
                            <div className="p-4">
                              <p className="text-sm text-muted-foreground bg-card/60 p-3 rounded-lg border border-primary/10">
                                This schema captures the structure of your data with appropriate indexes for optimal query performance. Property types have been mapped to match the original data types.
                              </p>
                            </div>
                          </div>
                        </motion.div>
                      </div>
                    </div>
                  </motion.div>
                ) : selectedSource ? (
                  <div className="flex flex-col items-center justify-center py-12 h-[calc(100vh-280px)] bg-background/40 rounded-lg border border-primary/10">
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5 }}
                      className="text-center"
                    >
                      <div className="relative w-32 h-32 mx-auto mb-6">
                        <motion.div
                          animate={{ 
                            scale: [1, 1.05, 1],
                            opacity: [0.7, 1, 0.7]
                          }}
                          transition={{ 
                            duration: 3,
                            repeat: Infinity,
                            ease: "easeInOut"
                          }}
                          className="absolute inset-0 bg-primary/5 rounded-full"
                        />
                        <motion.div
                          animate={{ 
                            scale: [1, 1.1, 1],
                            opacity: [0.5, 0.8, 0.5]
                          }}
                          transition={{ 
                            duration: 4,
                            repeat: Infinity,
                            ease: "easeInOut",
                            delay: 0.5
                          }}
                          className="absolute inset-0 bg-primary/5 rounded-full"
                        />
                        <MessageSquare className="h-16 w-16 text-foreground/40 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                      </div>
                      <h3 className="text-xl font-medium text-foreground mb-2">Ready to Generate</h3>
                      <p className="text-foreground">Use the chat to generate a recommended graph schema</p>
                      <p className="text-sm text-muted-foreground mt-2">Type your request in the chat assistant on the left</p>
                      
                      <motion.div 
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5, duration: 0.5 }}
                        className="mt-8"
                      >
                        <div className="inline-flex items-center gap-2 bg-primary/10 text-foreground px-4 py-2 rounded-lg border border-primary/20">
                          <span className="text-sm">Try asking:</span>
                          <span className="text-xs bg-background/70 px-2 py-1 rounded-md">"Create a schema for my dataset"</span>
                        </div>
                      </motion.div>
                    </motion.div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 h-[calc(100vh-280px)] bg-background/40 rounded-lg border border-primary/10">
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.5 }}
                      className="text-center"
                    >
                      <div className="relative w-32 h-32 mx-auto mb-6">
                        <motion.div
                          animate={{ 
                            rotate: 360,
                            scale: [1, 1.1, 1]
                          }}
                          transition={{ 
                            rotate: {
                              duration: 20,
                              repeat: Infinity,
                              ease: "linear"
                            },
                            scale: {
                              duration: 3,
                              repeat: Infinity,
                              ease: "easeInOut"
                            }
                          }}
                          className="absolute inset-0 border-2 border-dashed border-primary/20 rounded-full"
                        />
                        <Save className="h-16 w-16 text-foreground/40 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                      </div>
                      <h3 className="text-xl font-medium text-foreground mb-2">Select a Dataset</h3>
                      <p className="text-foreground">Choose a dataset from the dropdown above to get started</p>
                      
                      <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5, duration: 0.5 }}
                        className="mt-8 flex justify-center"
                      >
                        <motion.div
                          animate={{ y: [0, -5, 0] }}
                          transition={{ 
                            duration: 2,
                            repeat: Infinity,
                            ease: "easeInOut"
                          }}
                          className="text-primary"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M12 5v14M19 12l-7 7-7-7"/>
                          </svg>
                        </motion.div>
                      </motion.div>
                    </motion.div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>
      
      {/* Error Dialog for duplicate schema name */}
      <Dialog open={showErrorDialog} onOpenChange={setShowErrorDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Schema Save Error
            </DialogTitle>
            <DialogDescription>
              {errorMessage}
            </DialogDescription>
          </DialogHeader>
          
          <DialogFooter className="sm:justify-center mt-4">
            <Button
              variant="default"
              onClick={() => setShowErrorDialog(false)}
              className="w-full sm:w-auto"
            >
              OK
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Success Dialog for schema save */}
      <Dialog open={showSuccessMessage} onOpenChange={setShowSuccessMessage}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-primary">
              <CheckCircle className="h-5 w-5 text-primary" />
              Schema Saved Successfully
            </DialogTitle>
            <DialogDescription>
              Your schema "{savedSchemaInfo.name}" has been saved successfully.
            </DialogDescription>
          </DialogHeader>
          
          <DialogFooter className="sm:justify-center mt-4">
            <Button
              variant="default"
              onClick={() => setShowSuccessMessage(false)}
              className="w-full sm:w-auto"
            >
              OK
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  </div>
  )
}

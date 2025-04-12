"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from "react"
import { useToast } from "@/components/ui/use-toast"
import { useSchemaSelection } from "./schema-selection-context"

// Graph data types
export interface GraphNode {
  id: string
  label: string // This field now holds the node type name from the backend
  properties: Record<string, any>
  metadata?: { // Added optional metadata
    type: string // e.g., "node_type"
    db_id?: number // Optional: Original database ID 
  }
  x?: number
  y?: number
  color?: string // Optional styling
  size?: number // Optional styling
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  label: string // This field holds the relationship type name from the backend
  properties: Record<string, any>
  metadata?: { // Added optional metadata
    type: string // e.g., "relationship_type"
    db_id?: number // Optional: Original database ID
  }
  color?: string // Optional styling
  width?: number // Optional styling
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// Visualization settings type
export interface VisualizationSettings {
  layout: "force" | "radial" | "hierarchical"
  nodeSize: number
  labelVisible: boolean
  theme: "light" | "dark" | "system"
  edgeArrows: boolean
  filterNodeTypes: string[]
  filterEdgeTypes: string[]
}

// Context state type
interface GraphVisualizationContextType {
  // State
  graphData: GraphData | null
  isLoading: boolean
  error: string | null
  settings: VisualizationSettings
  selectedNode: GraphNode | null
  selectedEdge: GraphEdge | null
  
  // Actions
  loadGraphData: (schemaId: number) => Promise<void>
  updateSettings: (settings: Partial<VisualizationSettings>) => void
  selectNode: (nodeId: string | null) => void
  selectEdge: (edgeId: string | null) => void
  filterByNodeType: (nodeType: string, include: boolean) => void
  filterByEdgeType: (edgeType: string, include: boolean) => void
  resetFilters: () => void
  getNodeTypes: () => string[]
  getEdgeTypes: () => string[]
}

// Default visualization settings
const defaultSettings: VisualizationSettings = {
  layout: "force",
  nodeSize: 8,
  labelVisible: true,
  theme: "system",
  edgeArrows: true,
  filterNodeTypes: [],
  filterEdgeTypes: []
}

// Create context
const GraphVisualizationContext = createContext<GraphVisualizationContextType | undefined>(undefined)

// Provider component
export function GraphVisualizationProvider({ children }: { children: ReactNode }) {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [settings, setSettings] = useState<VisualizationSettings>(defaultSettings)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null)
  
  const { selectedSchemaId } = useSchemaSelection()
  const { toast } = useToast()

  // Load graph data when selected schema changes
  useEffect(() => {
    if (selectedSchemaId) {
      loadGraphData(selectedSchemaId)
    } else {
      setGraphData(null)
    }
  }, [selectedSchemaId])

  // Function to fetch graph data from API
  const fetchGraphData = async (schemaId: number) => {
    setIsLoading(true)
    setError(null)
    
    try {
      const token = localStorage.getItem('token') // Get token
      if (!token) {
        throw new Error('Authentication token not found.')
      }
      
      // Use the correct, new path and add Authorization header
      const response = await fetch(`/api/kginsights/graph-visualization/${schemaId}?limit=100`, { // Added limit param example
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })
      
      if (!response.ok) {
        throw new Error(`Failed to fetch graph data: ${response.statusText}`)
      }
      
      const data = await response.json()
      setGraphData(data)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error fetching graph data'
      setError(errorMessage)
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  // Load graph data from API
  const loadGraphData = async (schemaId: number) => {
    setSelectedNode(null)
    setSelectedEdge(null)
    
    await fetchGraphData(schemaId)
  }

  // Update visualization settings
  const updateSettings = (newSettings: Partial<VisualizationSettings>) => {
    setSettings(prev => ({
      ...prev,
      ...newSettings
    }))
  }

  // Select a node by ID
  const selectNode = (nodeId: string | null) => {
    if (!nodeId || !graphData) {
      setSelectedNode(null)
      return
    }
    
    const node = graphData.nodes.find(n => n.id === nodeId)
    setSelectedNode(node || null)
    
    // Deselect edge when node is selected
    setSelectedEdge(null)
  }

  // Select an edge by ID
  const selectEdge = (edgeId: string | null) => {
    if (!edgeId || !graphData) {
      setSelectedEdge(null)
      return
    }
    
    const edge = graphData.edges.find(e => e.id === edgeId)
    setSelectedEdge(edge || null)
    
    // Deselect node when edge is selected
    setSelectedNode(null)
  }

  // Filter by node type
  const filterByNodeType = (nodeType: string, include: boolean) => {
    setSettings(prev => {
      const filterNodeTypes = [...prev.filterNodeTypes]
      
      if (include && !filterNodeTypes.includes(nodeType)) {
        filterNodeTypes.push(nodeType)
      } else if (!include) {
        const index = filterNodeTypes.indexOf(nodeType)
        if (index !== -1) {
          filterNodeTypes.splice(index, 1)
        }
      }
      
      return {
        ...prev,
        filterNodeTypes
      }
    })
  }

  // Filter by edge type
  const filterByEdgeType = (edgeType: string, include: boolean) => {
    setSettings(prev => {
      const filterEdgeTypes = [...prev.filterEdgeTypes]
      
      if (include && !filterEdgeTypes.includes(edgeType)) {
        filterEdgeTypes.push(edgeType)
      } else if (!include) {
        const index = filterEdgeTypes.indexOf(edgeType)
        if (index !== -1) {
          filterEdgeTypes.splice(index, 1)
        }
      }
      
      return {
        ...prev,
        filterEdgeTypes
      }
    })
  }

  // Reset all filters
  const resetFilters = () => {
    setSettings(prev => ({
      ...prev,
      filterNodeTypes: [],
      filterEdgeTypes: []
    }))
  }

  // Get all unique node types
  const getNodeTypes = () => {
    if (!graphData) return []
    
    const types = new Set<string>()
    graphData.nodes.forEach(node => {
      types.add(node.label)
    })
    
    return Array.from(types)
  }

  // Get all unique edge types
  const getEdgeTypes = () => {
    if (!graphData) return []
    
    const types = new Set<string>()
    graphData.edges.forEach(edge => {
      types.add(edge.label)
    })
    
    return Array.from(types)
  }

  // Context value
  const value = {
    graphData,
    isLoading,
    error,
    settings,
    selectedNode,
    selectedEdge,
    loadGraphData,
    updateSettings,
    selectNode,
    selectEdge,
    filterByNodeType,
    filterByEdgeType,
    resetFilters,
    getNodeTypes,
    getEdgeTypes
  }

  return (
    <GraphVisualizationContext.Provider value={value}>
      {children}
    </GraphVisualizationContext.Provider>
  )
}

// Custom hook to use the graph visualization context
export function useGraphVisualization() {
  const context = useContext(GraphVisualizationContext)
  
  if (context === undefined) {
    throw new Error("useGraphVisualization must be used within a GraphVisualizationProvider")
  }
  
  return context
}

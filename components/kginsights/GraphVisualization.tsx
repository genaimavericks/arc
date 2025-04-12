"use client"

import { useEffect, useRef, useState } from "react"
import { useGraphVisualization } from "@/lib/graph-visualization-context"
import { Skeleton } from "@/components/ui/skeleton"
import { motion } from "framer-motion"
import CytoscapeGraph from "@/components/cytoscape-graph"

// Custom hook to replace usehooks-ts
const useResizeObserver = ({ ref }: { ref: React.RefObject<HTMLDivElement | null> }) => {
  const [size, setSize] = useState({ width: 0, height: 0 });
  
  useEffect(() => {
    if (!ref.current) return;
    
    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setSize({ width, height });
      }
    });
    
    observer.observe(ref.current);
    
    return () => {
      observer.disconnect();
    };
  }, [ref]);
  
  return size;
};

export default function GraphVisualization() {
  const { 
    graphData, 
    isLoading, 
    error, 
    settings, 
    selectedNode,
    selectedEdge,
    selectNode,
    selectEdge
  } = useGraphVisualization()
  
  const containerRef = useRef<HTMLDivElement | null>(null)
  const { width, height } = useResizeObserver({ ref: containerRef })
  const [isInitialized, setIsInitialized] = useState(false)
  
  // Initialize the visualization after first render
  useEffect(() => {
    setIsInitialized(true)
  }, [])
  
  // Convert GraphData to Schema format for CytoscapeGraph
  const convertToSchema = () => {
    if (!graphData) return { nodes: [], relationships: [] }
    
    // Create a map of node IDs to node objects for easier lookup
    const nodeMap = new Map();
    graphData.nodes.forEach(node => {
      nodeMap.set(node.id, node);
    });
    
    return {
      // Use the node ID as the label to ensure edges can connect correctly
      nodes: graphData.nodes.map(node => ({
        label: node.id, // Use ID as label for Cytoscape (important for edge connections)
        properties: {
          ...node.properties || {},
          // Add display label as a property so it's visible in the UI
          displayLabel: node.label
        }
      })),
      relationships: graphData.edges.map(edge => ({
        startNode: edge.source, // These should match the node IDs from the backend
        endNode: edge.target,   // These should match the node IDs from the backend
        type: edge.label,
        properties: edge.properties || {}
      })),
      indexes: []
    }
  }
  
  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-destructive">
          <p>Error loading graph visualization</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    )
  }
  
  if (isLoading || !isInitialized) {
    return (
      <div className="h-full p-4">
        <Skeleton className="h-full w-full rounded-lg" />
      </div>
    )
  }
  
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-muted-foreground">
          <p>No graph data available</p>
          <p className="text-sm">Select a schema with data to visualize</p>
        </div>
      </div>
    )
  }
  
  return (
    <motion.div 
      ref={containerRef}
      className="h-full w-full"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <CytoscapeGraph
        schema={convertToSchema()}
        showContainer={false}
        showTitle={false}
        height="100%"
        customTitle="Schema Visualization"
      />
    </motion.div>
  )
}

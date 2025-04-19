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
    const timer = setTimeout(() => {
      setIsInitialized(true)
    }, 100); // Small delay to help with smoother transitions
    
    return () => clearTimeout(timer);
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
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center max-w-md p-8 bg-red-50 dark:bg-red-950/20 rounded-lg border border-red-200 dark:border-red-800">
          <div className="mx-auto w-14 h-14 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-red-500" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-red-800 dark:text-red-300 mb-2">Error loading graph visualization</h3>
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      </div>
    )
  }
  
  if (isLoading || !isInitialized) {
    return (
      <div className="h-full p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="relative h-24 w-24 mx-auto mb-4">
            <Skeleton className="h-full w-full rounded-full absolute animate-pulse" />
            <Skeleton className="h-4/5 w-4/5 rounded-full absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 animate-pulse delay-75" />
            <Skeleton className="h-3/5 w-3/5 rounded-full absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 animate-pulse delay-150" />
          </div>
          <Skeleton className="h-4 w-40 mx-auto mb-2" />
          <Skeleton className="h-3 w-60 mx-auto" />
        </div>
      </div>
    )
  }
  
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center max-w-md">
          <div className="mx-auto w-16 h-16 rounded-full bg-muted/20 flex items-center justify-center mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-muted-foreground/50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="8" r="5" />
              <path d="M12 8v3M12 13h4M4 17a8 8 0 0 1 16 0M5 19h14" />
            </svg>
          </div>
          <h3 className="text-lg font-medium mb-2">No Graph Data Available</h3>
          <p className="text-sm text-muted-foreground mb-6">Select a schema with data to visualize the knowledge graph.</p>
          <div className="px-6 py-3 bg-muted/20 rounded-lg text-xs text-muted-foreground">
            <p>Try these steps:</p>
            <ol className="text-left list-decimal pl-5 mt-2 space-y-1">
              <li>Select a schema from the list</li>
              <li>Click "Load Data" if no data is loaded</li>
              <li>Wait for processing to complete</li>
            </ol>
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <motion.div 
      ref={containerRef}
      className="h-full w-full flex items-center justify-center min-h-[400px] p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeInOut" }}
      style={{ flex: '1 1 auto' }}
    >
      <div className="w-full h-full flex-1">
        <CytoscapeGraph
          schema={convertToSchema()}
          showContainer={false}
          showTitle={false}
          height="100%"
          customTitle="Schema Visualization"
        />
      </div>
    </motion.div>
  )
}

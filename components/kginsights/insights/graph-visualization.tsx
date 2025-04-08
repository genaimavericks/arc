"use client"

import { useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2 } from "lucide-react"
import CytoscapeGraph from "@/components/cytoscape-graph"

interface GraphVisualizationProps {
  data: any
  title?: string
}

export function GraphVisualization({ data, title = "Knowledge Graph Visualization" }: GraphVisualizationProps) {
  // Convert data to the format expected by CytoscapeGraph
  const schemaData = {
    nodes: Array.isArray(data.nodes) 
      ? data.nodes.map((node: any) => ({
          label: node.label || node.id || 'Node',
          properties: node.properties || {}
        })) 
      : [],
    relationships: Array.isArray(data.edges) 
      ? data.edges.map((edge: any) => ({
          startNode: edge.source || '',
          endNode: edge.target || '',
          type: edge.label || 'RELATES_TO',
          properties: edge.properties || {}
        }))
      : [],
    indexes: []
  }

  // Check if we have a valid graph to display
  const hasValidGraph = schemaData.nodes.length > 0

  return (
    <Card className="w-full bg-background border shadow-sm">
      <CardHeader className="py-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-2">
        {!hasValidGraph ? (
          <div className="flex items-center justify-center h-60 bg-muted/30 rounded-md">
            <div className="text-center text-muted-foreground">
              <p>No graph data available</p>
            </div>
          </div>
        ) : (
          <div className="h-60 border rounded-md overflow-hidden">
            <div className="w-full h-full">
              <CytoscapeGraph
                schema={schemaData}
                showContainer={false}
                showTitle={false}
                height="100%"
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

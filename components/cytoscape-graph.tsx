'use client';

import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';

interface SchemaNode {
  label: string;
  properties: { [key: string]: string };
}

interface SchemaRelationship {
  startNode: string;
  endNode: string;
  type: string;
  properties?: { [key: string]: string };
}

interface Schema {
  nodes: SchemaNode[];
  relationships: SchemaRelationship[];
  indexes?: string[];
}

interface CytoscapeGraphProps {
  schema: Schema;
  showContainer?: boolean;
  showTitle?: boolean;
  height?: string;
  customTitle?: string;
}

export default function CytoscapeGraph({ 
  schema, 
  showContainer = true, 
  showTitle = true, 
  height = '500px',
  customTitle = 'Graph Visualization'
}: CytoscapeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current || !schema) return;
    
    // Convert schema to Cytoscape elements
    const elements: any[] = [];
    
    // Add nodes
    schema.nodes.forEach(node => {
      elements.push({
        data: { 
          id: node.label, 
          // Use displayLabel property if available, otherwise fall back to label
          label: node.properties.displayLabel || node.label,
          properties: Object.entries(node.properties || {})
            .filter(([key]) => key !== 'displayLabel') // Don't show displayLabel in properties list
            .map(([key, type]) => `${key}: ${type}`)
            .join(", ")
        }
      });
    });
    
    // Add edges
    schema.relationships.forEach((rel, index) => {
      elements.push({
        data: {
          id: `edge-${index}`,
          source: rel.startNode,
          target: rel.endNode,
          label: rel.type,
          properties: rel.properties ? Object.entries(rel.properties)
            .map(([key, type]) => `${key}: ${type}`)
            .join(", ") : ''
        }
      });
    });
    
    // Initialize Cytoscape
    try {
      const cy = cytoscape({
        container: containerRef.current,
        elements: elements,
        style: [
          {
            selector: 'node',
            style: {
              'background-color': '#6366F1',
              'label': 'data(label)',
              'color': '#fff',
              'text-valign': 'center',
              'text-halign': 'center',
              'font-weight': 'bold',
              'width': 80,
              'height': 80
            }
          },
          {
            selector: 'edge',
            style: {
              'width': 2,
              'line-color': '#888',
              'target-arrow-color': '#888',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              'label': 'data(label)',
              'font-size': '10px',
              'text-rotation': 'autorotate'
            }
          }
        ],
        layout: {
          name: 'circle',
          padding: 50
        }
      });
      
      cyRef.current = cy;
      
      // Apply layout
      cy.layout({ name: 'circle' }).run();
      
      return () => {
        if (cyRef.current) {
          cyRef.current.destroy();
        }
      };
    } catch (error) {
      console.error("Error initializing Cytoscape:", error);
    }
  }, [schema]);

  // Render the graph with or without container based on props
  const graphContent = (
    <div 
      ref={containerRef} 
      style={{ 
        width: '100%', 
        height: height, 
        border: showContainer ? '1px solid #e5e7eb' : 'none', 
        borderRadius: showContainer ? '0.375rem' : '0' 
      }}
    />
  );

  if (showContainer) {
    return (
      <div className="border rounded-md p-4 bg-white">
        {showTitle && <h3 className="text-lg font-medium mb-2">{customTitle}</h3>}
        {graphContent}
      </div>
    );
  }

  return graphContent;
}

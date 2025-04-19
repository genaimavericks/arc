"use client"

import { KGInsightsLayout } from "@/components/kginsights/kginsights-layout"
import { SchemaSelectionProvider } from "@/lib/schema-selection-context"
import { GraphVisualizationProvider } from "@/lib/graph-visualization-context"
import ClientSideJobProvider from "@/components/kginsights/ClientSideJobProvider" 
import SchemaList from "@/components/kginsights/SchemaList"
import SchemaDetail from "@/components/kginsights/SchemaDetail"
import GraphVisualization from "@/components/kginsights/GraphVisualization"
import GraphControlPanel from "@/components/kginsights/GraphControlPanel"
import FloatingKGJobCard from "@/components/kginsights/FloatingKGJobCard"

export default function ManageKGraphPage() {
  return (
    <KGInsightsLayout requiredPermission="kginsights:manage">
      <SchemaSelectionProvider>
        <ClientSideJobProvider>
          <GraphVisualizationProvider>
            <ManageKGraphContent />
            <FloatingKGJobCard />
          </GraphVisualizationProvider>
        </ClientSideJobProvider>
      </SchemaSelectionProvider>
    </KGInsightsLayout>
  )
}

function ManageKGraphContent() {
  return (
    <div className="flex flex-col h-full w-full overflow-hidden">
      <header className="p-4 border-b">
        <h1 className="text-2xl font-bold">Manage Knowledge Graphs</h1>
        <p className="text-muted-foreground">
          View and manage your knowledge graph schemas, visualize data, and run data operations
        </p>
      </header>
      
      <main className="flex flex-1 overflow-hidden">
        {/* Left sidebar for schema list */}
        <aside className="w-80 border-r overflow-hidden flex flex-col">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold mb-2">Schema List</h2>
          </div>
          <div className="p-4 flex-1 overflow-hidden">
            <SchemaList />
          </div>
        </aside>
        
        {/* Main content area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Selected schema details and actions */}
          <div className="p-4 border-b">
            <SchemaDetail />
          </div>
          
          {/* Graph visualization - with flex-grow to take available space */}
          <div className="flex-1 relative overflow-hidden flex flex-col min-h-[400px]">
            <GraphVisualization />
            <GraphControlPanel />
          </div>
        </div>
      </main>
    </div>
  )
}

"use client"

import { useState, useEffect } from "react"
import { KGInsightsLayout } from "@/components/kginsights/kginsights-layout"
import { SchemaSelectionProvider } from "@/lib/schema-selection-context"
import { GraphVisualizationProvider } from "@/lib/graph-visualization-context"
import ClientSideJobProvider from "@/components/kginsights/ClientSideJobProvider" 
import SchemaList from "@/components/kginsights/SchemaList"
import SchemaDetail from "@/components/kginsights/SchemaDetail"
import GraphVisualization from "@/components/kginsights/GraphVisualization"
import GraphControlPanel from "@/components/kginsights/GraphControlPanel"
import FloatingKGJobCard from "@/components/kginsights/FloatingKGJobCard"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export default function ManageKGraphPage() {
  return (
    <KGInsightsLayout requiredPermission="kginsights:read">
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // Initialize collapsed state from localStorage on component mount
  useEffect(() => {
    const savedState = localStorage.getItem('kginsights-schemalist-collapsed');
    if (savedState) {
      setSidebarCollapsed(savedState === 'true');
    }
  }, []);
  
  // Toggle sidebar collapsed state and save to localStorage
  const toggleSidebar = () => {
    const newState = !sidebarCollapsed;
    setSidebarCollapsed(newState);
    localStorage.setItem('kginsights-schemalist-collapsed', String(newState));
  };
  
  return (
    <div className="flex flex-col h-full w-full overflow-hidden relative">
      {/* KG Assist style button positioned in front of the Overview panel */}
      {sidebarCollapsed && (
        <div 
          className="absolute z-[9999] pointer-events-auto" 
          style={{ 
            left: '10px', /* Small offset from the edge */
            top: '160px',
            marginLeft: '0',
            marginRight: '0'
          }}
        >
          <button
            onClick={toggleSidebar}
            className="relative bg-primary text-primary-foreground rounded-r-lg p-3 shadow-xl hover:bg-primary/90 transition-all h-20 w-12 flex items-center justify-center border-r border-t border-b border-primary/40 group"
            aria-label="Expand Schema List"
          >
            <div className="absolute inset-0 bg-primary/20 rounded-r-lg animate-pulse group-hover:animate-none"></div>
            <div className="flex flex-col items-center justify-center gap-2 relative z-10">
              <ChevronRight className="w-4 h-4" />
              <span className="text-xs font-medium rotate-90">Schema List</span>
            </div>
          </button>
        </div>
      )}
      
      <header className="p-4 border-b">
        <h1 className="text-2xl font-bold tracking-tight">Manage Knowledge Graphs</h1>
      </header>
      
      <main className="flex flex-1 overflow-hidden">
        {/* Conditional rendering of either the full sidebar or just the expand button */}
        {sidebarCollapsed ? (
          /* When collapsed, show only the expand button */
          <div className="h-full w-[10px] flex-shrink-0"></div>
        ) : (
          /* When expanded, show the full sidebar */
          <aside className="w-80 border-r overflow-hidden flex flex-col flex-shrink-0 transition-all duration-300 ease-in-out">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold">Schema List</h2>
              <Button
                onClick={toggleSidebar}
                variant="ghost"
                size="sm"
                className="ml-auto h-8 w-8 p-0"
                aria-label="Collapse Schema List"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </div>
            <div className="p-4 flex-1 overflow-hidden">
              <SchemaList />
            </div>
          </aside>
        )}
        
        {/* Main content area - will automatically adjust width */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
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

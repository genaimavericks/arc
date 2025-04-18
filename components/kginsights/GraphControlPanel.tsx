"use client"

import { useState } from "react"
import { useGraphVisualization } from "@/lib/graph-visualization-context"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ZoomIn, ZoomOut, Maximize, Search, PanelLeftClose, PanelLeftOpen, Settings, LayoutGrid, Download, RefreshCw } from "lucide-react"

export default function GraphControlPanel() {
  const { 
    graphData, 
    settings, 
    updateSettings, 
    selectedNode, 
    selectedEdge, 
    getNodeTypes,
    getEdgeTypes,
    resetFilters
  } = useGraphVisualization()
  
  const [isExpanded, setIsExpanded] = useState(false)
  const nodeTypes = getNodeTypes()
  const edgeTypes = getEdgeTypes()
  
  // Handle type filtering
  const handleNodeTypeFilter = (nodeType: string, checked: boolean) => {
    updateSettings({
      filterNodeTypes: checked 
        ? settings.filterNodeTypes.filter(t => t !== nodeType)
        : [...settings.filterNodeTypes, nodeType]
    })
  }
  
  const handleEdgeTypeFilter = (edgeType: string, checked: boolean) => {
    updateSettings({
      filterEdgeTypes: checked 
        ? settings.filterEdgeTypes.filter(t => t !== edgeType) 
        : [...settings.filterEdgeTypes, edgeType]
    })
  }
  
  return (
    <div className={`absolute right-4 top-4 z-10 transition-all duration-300 ease-in-out ${isExpanded ? 'w-80' : 'w-auto'}`}>
      <div className="flex flex-col gap-2">
        <Card className="shadow-md border-border/80 backdrop-blur-sm bg-background/95">
          <CardContent className="p-2 flex flex-wrap gap-1.5">
            <Button variant="outline" size="icon" title="Zoom In" className="h-9 w-9 hover:bg-primary/10 transition-colors">
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" title="Zoom Out" className="h-9 w-9 hover:bg-primary/10 transition-colors">
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" title="Reset View" className="h-9 w-9 hover:bg-primary/10 transition-colors">
              <Maximize className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" title="Refresh Layout" className="h-9 w-9 hover:bg-primary/10 transition-colors">
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" title="Save Image" className="h-9 w-9 hover:bg-primary/10 transition-colors">
              <Download className="h-4 w-4" />
            </Button>
            <Button
              variant={isExpanded ? "default" : "outline"}
              size="icon"
              title={isExpanded ? "Collapse Panel" : "Expand Panel"}
              onClick={() => setIsExpanded(!isExpanded)}
              className={`h-9 w-9 transition-all ${isExpanded ? "" : "hover:bg-primary/10"}`}
            >
              {isExpanded ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
            </Button>
          </CardContent>
        </Card>
        
        {isExpanded && (
          <Card className="shadow-md border-border/80 animate-in fade-in-50 slide-in-from-right-5 duration-300 backdrop-blur-sm bg-background/95">
            <CardContent className="p-4">
              <Tabs defaultValue="filters" className="w-full">
                <TabsList className="grid w-full grid-cols-3 mb-2">
                  <TabsTrigger value="filters" className="text-xs transition-colors">Filters</TabsTrigger>
                  <TabsTrigger value="layout" className="text-xs transition-colors">Layout</TabsTrigger>
                  <TabsTrigger value="style" className="text-xs transition-colors">Style</TabsTrigger>
                </TabsList>
                
                <TabsContent value="filters" className="space-y-4 pt-4 animate-in fade-in-50 duration-200">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-medium">Node Types</h3>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-7 text-xs hover:bg-primary/10 transition-colors"
                        onClick={resetFilters}
                      >
                        Reset Filters
                      </Button>
                    </div>
                    <div className="space-y-2 max-h-[150px] overflow-y-auto pr-1 scrollbar-thin">
                      {nodeTypes.map(type => (
                        <div key={type} className="flex items-center space-x-2 py-0.5">
                          <Checkbox 
                            id={`node-${type}`} 
                            checked={!settings.filterNodeTypes.includes(type)}
                            onCheckedChange={(checked) => handleNodeTypeFilter(type, checked as boolean)}
                            className="data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground transition-colors"
                          />
                          <Label htmlFor={`node-${type}`} className="text-sm cursor-pointer truncate">
                            {type}
                          </Label>
                        </div>
                      ))}
                      {nodeTypes.length === 0 && (
                        <div className="text-xs text-muted-foreground py-2 px-3 bg-muted/20 rounded-md">No node types found</div>
                      )}
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium mb-3">Relationship Types</h3>
                    <div className="space-y-2 max-h-[150px] overflow-y-auto pr-1 scrollbar-thin">
                      {edgeTypes.map(type => (
                        <div key={type} className="flex items-center space-x-2 py-0.5">
                          <Checkbox 
                            id={`edge-${type}`} 
                            checked={!settings.filterEdgeTypes.includes(type)}
                            onCheckedChange={(checked) => handleEdgeTypeFilter(type, checked as boolean)}
                            className="data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground transition-colors"
                          />
                          <Label htmlFor={`edge-${type}`} className="text-sm cursor-pointer truncate">
                            {type}
                          </Label>
                        </div>
                      ))}
                      {edgeTypes.length === 0 && (
                        <div className="text-xs text-muted-foreground py-2 px-3 bg-muted/20 rounded-md">No relationship types found</div>
                      )}
                    </div>
                  </div>
                </TabsContent>
                
                <TabsContent value="layout" className="space-y-4 pt-4 animate-in fade-in-50 duration-200">
                  <div>
                    <h3 className="text-sm font-medium mb-3">Layout Type</h3>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant={settings.layout === "force" ? "default" : "outline"}
                        size="sm"
                        className={`text-xs transition-all ${settings.layout !== "force" ? "hover:bg-primary/10" : ""}`}
                        onClick={() => updateSettings({ layout: "force" })}
                      >
                        Force
                      </Button>
                      <Button
                        variant={settings.layout === "radial" ? "default" : "outline"}
                        size="sm"
                        className={`text-xs transition-all ${settings.layout !== "radial" ? "hover:bg-primary/10" : ""}`}
                        onClick={() => updateSettings({ layout: "radial" })}
                      >
                        Radial
                      </Button>
                      <Button
                        variant={settings.layout === "hierarchical" ? "default" : "outline"}
                        size="sm"
                        className={`text-xs transition-all ${settings.layout !== "hierarchical" ? "hover:bg-primary/10" : ""}`}
                        onClick={() => updateSettings({ layout: "hierarchical" })}
                      >
                        Hierarchical
                      </Button>
                    </div>
                  </div>
                </TabsContent>
                
                <TabsContent value="style" className="space-y-4 pt-4 animate-in fade-in-50 duration-200">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-medium">Node Size</h3>
                      <span className="text-xs text-muted-foreground px-2 py-0.5 bg-muted/20 rounded-full">{settings.nodeSize}</span>
                    </div>
                    <Slider
                      value={[settings.nodeSize]}
                      min={1}
                      max={20}
                      step={1}
                      onValueChange={(value) => updateSettings({ nodeSize: value[0] })}
                      className="py-1"
                    />
                  </div>
                  
                  <div className="flex items-center justify-between p-3 border border-border/50 rounded-md bg-muted/5">
                    <div className="flex flex-col gap-1">
                      <Label htmlFor="show-labels" className="text-sm font-medium">Show Labels</Label>
                      <span className="text-xs text-muted-foreground">Display node names</span>
                    </div>
                    <Switch
                      id="show-labels"
                      checked={settings.labelVisible}
                      onCheckedChange={(checked) => updateSettings({ labelVisible: checked })}
                      className="data-[state=checked]:bg-primary"
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex flex-col gap-1">
                      <Label htmlFor="show-arrows" className="text-sm font-medium">Show Arrows</Label>
                      <span className="text-xs text-muted-foreground">Display relationship direction</span>
                    </div>
                    <Switch
                      id="show-arrows"
                      checked={settings.edgeArrows}
                      onCheckedChange={(checked) => updateSettings({ edgeArrows: checked })}
                      className="data-[state=checked]:bg-primary"
                    />
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        )}
        
        {/* Node/Edge details panel */}
        {(selectedNode || selectedEdge) && isExpanded && (
          <Card className="shadow-md border-border/80 animate-in fade-in-50 slide-in-from-right-5 duration-300 backdrop-blur-sm bg-background/95">
            <CardContent className="p-4">
              {selectedNode && (
                <div>
                  <h3 className="text-sm font-bold flex items-center gap-2 mb-2">
                    <Badge>{selectedNode.type}</Badge>
                    <span>{selectedNode.label}</span>
                  </h3>
                  
                  <div className="text-xs space-y-1 mt-4">
                    <h4 className="font-medium">Properties:</h4>
                    {Object.entries(selectedNode.properties).map(([key, value]) => (
                      <div key={key} className="flex">
                        <span className="font-medium min-w-[80px]">{key}:</span>
                        <span className="text-muted-foreground">
                          {value?.toString() || ""}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {selectedEdge && (
                <div>
                  <h3 className="text-sm font-bold flex items-center gap-2 mb-2">
                    <Badge>{selectedEdge.label}</Badge>
                    <span>Relationship</span>
                  </h3>
                  
                  <div className="text-xs mt-2">
                    <div className="flex">
                      <span className="font-medium min-w-[80px]">From:</span>
                      <span className="text-muted-foreground">{selectedEdge.source}</span>
                    </div>
                    <div className="flex">
                      <span className="font-medium min-w-[80px]">To:</span>
                      <span className="text-muted-foreground">{selectedEdge.target}</span>
                    </div>
                  </div>
                  
                  {Object.keys(selectedEdge.properties).length > 0 && (
                    <div className="text-xs space-y-1 mt-4">
                      <h4 className="font-medium">Properties:</h4>
                      {Object.entries(selectedEdge.properties).map(([key, value]) => (
                        <div key={key} className="flex">
                          <span className="font-medium min-w-[80px]">{key}:</span>
                          <span className="text-muted-foreground">
                            {value?.toString() || ""}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

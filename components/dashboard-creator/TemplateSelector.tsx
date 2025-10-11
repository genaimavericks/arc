"use client"

import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { LayoutDashboard, Eye, Sparkles, CheckCircle } from 'lucide-react'

interface Template {
  id: string
  name: string
  description: string
  layout?: {
    grid_columns: number
    responsive_breakpoints: string[]
  }
  widgets?: Array<{
    id: string
    type: string
    title: string
    position: { x: number, y: number, w: number, h: number }
  }>
  theme?: {
    primary_color: string
    background: string
  }
  filters?: Array<{
    type: string
    field: string
    label: string
  }>
}

interface TemplateSelectorProps {
  templates: Template[]
  onTemplateSelect: (template: Template) => void
  selectedTemplateId?: string
  loading?: boolean
}

export const TemplateSelector: React.FC<TemplateSelectorProps> = ({
  templates,
  onTemplateSelect,
  selectedTemplateId,
  loading = false
}) => {
  const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null)

  if (loading) {
    return (
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5" />
            Generating Templates...
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center p-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!templates.length) {
    return null
  }

  const getChartTypeIcon = (chartType: string) => {
    const icons: Record<string, string> = {
      'bar_chart': '📊',
      'line_chart': '📈',
      'pie_chart': '🥧',
      'scatter_plot': '⚪',
      'area_chart': '📈',
      'heatmap': '🔥',
      'treemap': '🗺️',
      'radar_chart': '🕸️'
    }
    return icons[chartType] || '📊'
  }

  const renderTemplatePreview = (template: Template) => {
    return (
      <div className="bg-muted/30 rounded-lg p-4 mt-4">
        <div className="grid grid-cols-12 gap-2 min-h-[200px]">
          {template.widgets?.map((widget, index) => (
            <div
              key={widget.id}
              className="bg-card border rounded flex items-center justify-center text-xs"
              style={{
                gridColumn: `span ${Math.min(widget.position.w || 6, 12)}`,
                gridRow: `span ${widget.position.h || 4}`,
                minHeight: '60px'
              }}
            >
              <div className="text-center p-2">
                <div className="text-lg mb-1">
                  {getChartTypeIcon(widget.type)}
                </div>
                <div className="font-medium">{widget.title}</div>
                <div className="text-muted-foreground capitalize">
                  {widget.type.replace('_', ' ')}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <LayoutDashboard className="w-5 h-5" />
          Choose Your Dashboard Template
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Select a template that best fits your needs. Each template is customized for your selected datasets.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4">
          {templates.map((template, index) => (
            <Card 
              key={template.id}
              className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                selectedTemplateId === template.id ? 'ring-2 ring-primary' : ''
              }`}
              onClick={() => onTemplateSelect(template)}
            >
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-semibold text-lg">{template.name}</h3>
                      {selectedTemplateId === template.id && (
                        <CheckCircle className="w-5 h-5 text-green-600" />
                      )}
                      <Badge variant="outline">
                        Template {index + 1}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mb-3">
                      {template.description}
                    </p>
                    
                    {/* Template Features */}
                    <div className="flex flex-wrap gap-2 mb-3">
                      {template.widgets && (
                        <Badge variant="secondary" className="text-xs">
                          {template.widgets.length} Charts
                        </Badge>
                      )}
                      {template.filters && template.filters.length > 0 && (
                        <Badge variant="secondary" className="text-xs">
                          {template.filters.length} Filters
                        </Badge>
                      )}
                      <Badge variant="secondary" className="text-xs">
                        Responsive
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        Interactive
                      </Badge>
                    </div>

                    {/* Chart Types Preview */}
                    {template.widgets && (
                      <div className="flex items-center gap-1 mb-3">
                        <span className="text-xs text-muted-foreground">Charts:</span>
                        {template.widgets.slice(0, 5).map((widget, widgetIndex) => (
                          <span key={widgetIndex} className="text-sm" title={widget.title}>
                            {getChartTypeIcon(widget.type)}
                          </span>
                        ))}
                        {template.widgets.length > 5 && (
                          <span className="text-xs text-muted-foreground">
                            +{template.widgets.length - 5} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex flex-col gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        setPreviewTemplate(previewTemplate?.id === template.id ? null : template)
                      }}
                    >
                      <Eye className="w-4 h-4 mr-1" />
                      Preview
                    </Button>
                    
                    <Button
                      variant={selectedTemplateId === template.id ? "default" : "outline"}
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        onTemplateSelect(template)
                      }}
                    >
                      {selectedTemplateId === template.id ? "Selected" : "Select"}
                    </Button>
                  </div>
                </div>

                {/* Template Preview */}
                {previewTemplate?.id === template.id && renderTemplatePreview(template)}
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Template Selection Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-blue-900">Template Features:</p>
              <ul className="text-blue-700 mt-1 space-y-1 text-xs">
                <li>• All templates use your actual dataset fields - no dummy data</li>
                <li>• Responsive design that works on all screen sizes</li>
                <li>• Interactive charts with hover, filter, and drill-down capabilities</li>
                <li>• Consistent with your app's theme and design system</li>
                <li>• Fully customizable after creation</li>
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

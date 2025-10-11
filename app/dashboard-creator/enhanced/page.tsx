"use client"

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { MainLayout } from "@/components/main-layout"
import ProtectedRoute from "@/components/protected-route"
import { EnhancedDatasetSelectionPanel } from '@/components/dashboard-creator/EnhancedDatasetSelection'
import { AIChatInterface } from '@/components/dashboard-creator/AIChatInterface'
import { TemplateSelector } from '@/components/dashboard-creator/TemplateSelector'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Wand2, ArrowRight, Sparkles, ArrowLeft } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

export default function EnhancedDashboardCreatorPage() {
  const router = useRouter()
  
  // State management
  const [step, setStep] = useState<'select' | 'generate' | 'customize' | 'create'>('select')
  const [selectedDatasets, setSelectedDatasets] = useState<{source_ids: string[], transformed_ids: string[]}>({
    source_ids: [],
    transformed_ids: []
  })
  const [validation, setValidation] = useState<any>(null)
  const [generatedTemplates, setGeneratedTemplates] = useState<any[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<any>(null)
  const [dashboardName, setDashboardName] = useState('')
  const [dashboardDescription, setDashboardDescription] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [chatHistory, setChatHistory] = useState<Array<{role: string, content: string}>>([])

  const handleDatasetSelectionChange = (selection: {source_ids: string[], transformed_ids: string[]}) => {
    setSelectedDatasets(selection)
  }

  const handleValidationChange = (validationResult: any) => {
    setValidation(validationResult)
  }

  const handleTemplatesGenerated = (templates: any[]) => {
    setGeneratedTemplates(templates)
    setStep('generate')
  }

  const handleTemplateSelect = (template: any) => {
    setSelectedTemplate(template)
    setStep('customize')
    // Auto-generate dashboard name based on template
    if (!dashboardName) {
      setDashboardName(template.name)
    }
  }

  const handleCreateDashboard = async () => {
    if (!selectedTemplate || !dashboardName.trim()) return
    
    setIsCreating(true)
    
    try {
      const response = await fetch('/api/dashboards/create-static', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dashboard_name: dashboardName,
          description: dashboardDescription,
          template_id: selectedTemplate.id,
          dataset_selection: selectedDatasets,
          dashboard_config: selectedTemplate,
          ai_chat_history: chatHistory
        })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const result = await response.json()
      
      // Redirect to build status page
      router.push(`/dashboards/${result.id}?building=true`)
      
    } catch (error) {
      console.error('Dashboard creation failed:', error)
      // Handle error - could show toast notification
    } finally {
      setIsCreating(false)
    }
  }

  const getStepIndicator = () => {
    const steps = [
      { id: 'select', label: 'Select Data', active: step === 'select' },
      { id: 'generate', label: 'AI Generation', active: step === 'generate' },
      { id: 'customize', label: 'Customize', active: step === 'customize' },
      { id: 'create', label: 'Create', active: step === 'create' }
    ]
    
    return (
      <div className="flex items-center justify-center space-x-4 mb-8">
        {steps.map((stepItem, index) => (
          <div key={stepItem.id} className="flex items-center">
            <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
              stepItem.active ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
            }`}>
              {index + 1}
            </div>
            <span className={`ml-2 text-sm ${stepItem.active ? 'font-medium' : 'text-muted-foreground'}`}>
              {stepItem.label}
            </span>
            {index < steps.length - 1 && (
              <ArrowRight className="w-4 h-4 mx-4 text-muted-foreground" />
            )}
          </div>
        ))}
      </div>
    )
  }

  return (
    <ProtectedRoute requiredPermission="dashboard:write">
      <MainLayout>
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => router.push('/dashboard-creator')}
                  className="p-1"
                >
                  <ArrowLeft className="w-4 h-4" />
                </Button>
                <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                  <Wand2 className="w-7 h-7" />
                  Enhanced Dashboard Creator
                </h2>
              </div>
              <p className="text-muted-foreground">
                Create modern, interactive dashboards using AI and your real data
              </p>
            </div>
            <Badge variant="outline" className="gap-1">
              <Sparkles className="w-3 h-3" />
              AI-Powered
            </Badge>
          </div>

          {/* Step Indicator */}
          {getStepIndicator()}

          {/* Step 1: Dataset Selection */}
          <EnhancedDatasetSelectionPanel 
            onSelectionChange={handleDatasetSelectionChange}
            onValidationChange={handleValidationChange}
          />

          {/* Step 2: AI Chat Interface */}
          <AIChatInterface
            onTemplatesGenerated={handleTemplatesGenerated}
            selectedDatasets={selectedDatasets}
            validation={validation}
          />

          {/* Step 3: Template Selection */}
          {generatedTemplates.length > 0 && (
            <TemplateSelector
              templates={generatedTemplates}
              onTemplateSelect={handleTemplateSelect}
              selectedTemplateId={selectedTemplate?.id}
            />
          )}

          {/* Step 4: Dashboard Customization */}
          {selectedTemplate && step === 'customize' && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Customize Your Dashboard</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Give your dashboard a name and description, then create it
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Dashboard Name</label>
                    <Input
                      placeholder="Enter dashboard name..."
                      value={dashboardName}
                      onChange={(e) => setDashboardName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Description (Optional)</label>
                    <Textarea
                      placeholder="Describe what this dashboard shows..."
                      value={dashboardDescription}
                      onChange={(e) => setDashboardDescription(e.target.value)}
                      className="resize-none"
                      rows={3}
                    />
                  </div>
                </div>

                {/* Selected Template Preview */}
                <div className="bg-muted/30 rounded-lg p-4">
                  <h4 className="font-medium mb-2">Selected Template: {selectedTemplate.name}</h4>
                  <p className="text-sm text-muted-foreground mb-3">{selectedTemplate.description}</p>
                  
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">
                      {selectedTemplate.widgets?.length || 0} Charts
                    </Badge>
                    <Badge variant="secondary">
                      {validation?.total_records?.toLocaleString() || 0} Records
                    </Badge>
                    <Badge variant="secondary">
                      Interactive
                    </Badge>
                    <Badge variant="secondary">
                      Responsive
                    </Badge>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4">
                  <Button 
                    variant="outline" 
                    onClick={() => setStep('generate')}
                  >
                    Back to Templates
                  </Button>
                  
                  <Button 
                    onClick={handleCreateDashboard}
                    disabled={!dashboardName.trim() || isCreating}
                    className="gap-2"
                  >
                    {isCreating ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        Creating Dashboard...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        Create Dashboard
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}

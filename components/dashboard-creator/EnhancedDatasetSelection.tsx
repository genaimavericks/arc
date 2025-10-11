"use client"

import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Upload, Database, FileText, Zap, CheckCircle, AlertTriangle } from 'lucide-react'

// API hooks reusing existing endpoints
const useSourceDatasets = () => {
  return useQuery({
    queryKey: ['source-datasets'],
    queryFn: async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) {
          console.warn('No authentication token found')
          return []
        }
        
        const response = await fetch('/api/datapuur/sources', {
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        })
        if (!response.ok) {
          console.error('Failed to fetch datasets:', response.status, response.statusText)
          return []
        }
        const data = await response.json()
        console.log('Source datasets response:', data)
        
        // Handle different response formats
        const datasets = Array.isArray(data) ? data : (data.datasets || data.data || [])
        console.log('Raw datasets before filter:', datasets)
        
        // Debug: Log all status values to see what we're actually getting
        datasets.forEach((dataset, index) => {
          console.log(`Dataset ${index}:`, {
            name: dataset.name,
            status: dataset.status,
            type: dataset.type,
            id: dataset.id
          })
        })
        
        // More permissive filter - accept any reasonable status
        const filtered = datasets.filter(dataset => {
          const status = dataset.status?.toLowerCase() || ''
          // Accept completed, active, available, ready, or any non-empty status
          const validStatuses = ['completed', 'active', 'available', 'ready', 'success', 'ok']
          const isValid = validStatuses.includes(status) || (dataset.status && dataset.status.length > 0)
          console.log(`Dataset "${dataset.name}" status "${dataset.status}" -> ${isValid ? 'INCLUDED' : 'EXCLUDED'}`)
          return isValid
        })
        console.log('Filtered datasets:', filtered)
        return filtered
      } catch (error) {
        console.error('Error fetching source datasets:', error)
        return []
      }
    },
    retry: 1,
    staleTime: 30000
  })
}

const useTransformedDatasets = () => {
  return useQuery({
    queryKey: ['transformed-datasets'], 
    queryFn: async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) {
          console.warn('No authentication token found for transformed datasets')
          return []
        }
        
        const response = await fetch('/api/datapuur-ai/transformed-datasets', {
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        })
        if (!response.ok) {
          console.warn('Transformed datasets API not available:', response.status)
          return []
        }
        const data = await response.json()
        console.log('Transformed datasets response:', data)
        
        // Handle different response formats
        const datasets = Array.isArray(data) ? data : (data.datasets || data.data || [])
        console.log('Raw transformed datasets before filter:', datasets)
        
        // Debug: Log transformed dataset details
        datasets.forEach((dataset, index) => {
          console.log(`Transformed Dataset ${index}:`, {
            name: dataset.name,
            status: dataset.status,
            type: dataset.type,
            id: dataset.id
          })
        })
        
        // More permissive filter for transformed datasets
        const filtered = datasets.filter(dataset => {
          const status = dataset.status?.toLowerCase() || ''
          const validStatuses = ['completed', 'active', 'available', 'ready', 'success', 'transformed']
          const isValid = validStatuses.includes(status) || (dataset.status && dataset.status.length > 0)
          console.log(`Transformed Dataset "${dataset.name}" status "${dataset.status}" -> ${isValid ? 'INCLUDED' : 'EXCLUDED'}`)
          return isValid
        })
        console.log('Filtered transformed datasets:', filtered)
        return filtered
      } catch (error) {
        console.warn('Transformed datasets not available:', error)
        return []
      }
    },
    retry: 1,
    staleTime: 30000
  })
}

interface DatasetSelectionProps {
  onSelectionChange?: (selection: {source_ids: string[], transformed_ids: string[]}) => void
  onValidationChange?: (validation: any) => void
}

export const EnhancedDatasetSelectionPanel: React.FC<DatasetSelectionProps> = ({
  onSelectionChange,
  onValidationChange
}) => {
  const { data: sourceDatasets, isLoading: sourceLoading } = useSourceDatasets()
  const { data: transformedDatasets, isLoading: transformedLoading } = useTransformedDatasets()
  
  const [selectedDatasets, setSelectedDatasets] = useState({
    source_ids: [] as string[],
    transformed_ids: [] as string[]
  })

  // Real-time validation using existing dataset data (no API calls needed)
  const { data: validation, isLoading: validating } = useQuery({
    queryKey: ['dataset-validation', selectedDatasets, sourceDatasets, transformedDatasets],
    queryFn: async () => {
      if (selectedDatasets.source_ids.length === 0 && selectedDatasets.transformed_ids.length === 0) {
        return null
      }
      
      // Validate using data we already have from the sources list
      const validation_results = [
        ...selectedDatasets.source_ids.map((id) => {
          const dataset = sourceDatasets?.find(d => d.id === id)
          if (!dataset) {
            console.error('Selected dataset not found in sources list:', id)
            return { id, type: 'source', valid: false, error: 'Dataset not found' }
          }
          
          const recordCount = dataset.row_count || dataset.record_count || 0
          console.log(`Validating source dataset "${dataset.name}": ${recordCount} records`)
          
          return {
            id,
            type: 'source',
            valid: recordCount > 0,
            name: dataset.name,
            record_count: recordCount,
            status: dataset.status
          }
        }),
        ...selectedDatasets.transformed_ids.map((id) => {
          const dataset = transformedDatasets?.find(d => d.id === id)
          if (!dataset) {
            console.error('Selected transformed dataset not found:', id)
            return { id, type: 'transformed', valid: false, error: 'Dataset not found' }
          }
          
          const recordCount = dataset.row_count || dataset.record_count || 0
          console.log(`Validating transformed dataset "${dataset.name}": ${recordCount} records`)
          
          return {
            id,
            type: 'transformed',
            valid: recordCount > 0,
            name: dataset.name,
            record_count: recordCount,
            status: dataset.status || 'completed'
          }
        })
      ]
      
      const all_valid = validation_results.every(result => result.valid)
      const total_records = validation_results.reduce((sum, result) => sum + (result.record_count || 0), 0)
      
      return {
        all_valid,
        total_records,
        results: validation_results,
        can_create_dashboard: all_valid && total_records > 0
      }
    },
    enabled: selectedDatasets.source_ids.length > 0 || selectedDatasets.transformed_ids.length > 0
  })

  // Notify parent components of changes
  useEffect(() => {
    onSelectionChange?.(selectedDatasets)
  }, [selectedDatasets, onSelectionChange])

  useEffect(() => {
    onValidationChange?.(validation)
  }, [validation, onValidationChange])

  const handleDatasetToggle = (datasetId: string, type: 'source' | 'transformed', dataset: any) => {
    // Allow selection of both completed and active datasets
    const validStatuses = ['completed', 'active']
    if (!validStatuses.includes(dataset.status?.toLowerCase())) return
    
    setSelectedDatasets(prev => {
      if (type === 'source') {
        const isSelected = prev.source_ids.includes(datasetId)
        return {
          ...prev,
          source_ids: isSelected 
            ? prev.source_ids.filter(id => id !== datasetId)
            : [...prev.source_ids, datasetId]
        }
      } else {
        const isSelected = prev.transformed_ids.includes(datasetId)
        return {
          ...prev,
          transformed_ids: isSelected
            ? prev.transformed_ids.filter(id => id !== datasetId) 
            : [...prev.transformed_ids, datasetId]
        }
      }
    })
  }

  const getStatusBadge = (status: string) => {
    const statusMap = {
      'completed': { variant: 'default' as const, label: 'Ready' },
      'processing': { variant: 'secondary' as const, label: 'Processing' },
      'failed': { variant: 'destructive' as const, label: 'Failed' },
      'running': { variant: 'secondary' as const, label: 'Running' }
    }
    return statusMap[status] || { variant: 'outline' as const, label: status }
  }

  const renderDatasetCard = (dataset: any, type: 'source' | 'transformed') => {
    const isSelected = type === 'source' 
      ? selectedDatasets.source_ids.includes(dataset.id)
      : selectedDatasets.transformed_ids.includes(dataset.id)
    
    // Allow selection of both completed and active datasets
    const validStatuses = ['completed', 'active']
    const canSelect = validStatuses.includes(dataset.status?.toLowerCase())

    return (
      <Card 
        key={dataset.id}
        className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
          isSelected ? 'ring-2 ring-primary' : ''
        } ${!canSelect ? 'opacity-50 cursor-not-allowed' : ''}`}
        onClick={() => canSelect && handleDatasetToggle(dataset.id, type, dataset)}
      >
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              {type === 'source' ? <FileText className="w-4 h-4" /> : <Zap className="w-4 h-4" />}
              <div>
                <h4 className="font-medium">{dataset.filename || dataset.name}</h4>
                <p className="text-sm text-muted-foreground">
                  {dataset.row_count?.toLocaleString() || 0} records
                </p>
              </div>
            </div>
            <Badge {...getStatusBadge(dataset.status)}>
              {getStatusBadge(dataset.status).label}
            </Badge>
          </div>
          
          {dataset.type && (
            <p className="text-xs text-muted-foreground mt-2">
              Format: {dataset.type.toUpperCase()}
            </p>
          )}
          
          {type === 'transformed' && dataset.transformation_type && (
            <p className="text-xs text-muted-foreground">
              Transform: {dataset.transformation_type}
            </p>
          )}
          
          <p className="text-xs text-muted-foreground">
            {new Date(dataset.uploaded_at || dataset.created_at).toLocaleDateString()}
          </p>
        </CardContent>
      </Card>
    )
  }

  const EmptyStateDisplay = ({ type, title, description, actionButton }: {
    type: string
    title: string
    description: string
    actionButton?: { label: string, onClick: () => void }
  }) => (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
        {type === 'no-datasets' ? <Database className="w-6 h-6" /> : <FileText className="w-6 h-6" />}
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-md mb-4">{description}</p>
      {actionButton && (
        <Button variant="outline" onClick={actionButton.onClick}>
          {actionButton.label}
        </Button>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-6">
        {/* Source Datasets Section */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Database className="w-5 h-5" />
                Source Datasets
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Uploaded via DataPuur ingestion system
              </p>
            </div>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => window.open('/datapuur/ingestion', '_blank')}
            >
              <Upload className="w-4 h-4 mr-2" />
              Upload Data
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {sourceLoading ? (
              <div className="flex items-center justify-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : !sourceDatasets?.length ? (
              <EmptyStateDisplay
                type="no-datasets"
                title="No Source Datasets"
                description="Upload CSV, JSON, or Parquet files through the DataPuur ingestion system."
                actionButton={{
                  label: "Go to Data Upload",
                  onClick: () => window.open('/datapuur/ingestion', '_blank')
                }}
              />
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {sourceDatasets
                  .filter((dataset: any) => dataset.status?.toLowerCase() === 'completed' || dataset.status?.toLowerCase() === 'active') // Show completed or active datasets
                  .map((dataset: any) => renderDatasetCard(dataset, 'source'))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Transformed Datasets Section */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Zap className="w-5 h-5" />
                Transformed Datasets
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                AI-processed and enhanced datasets
              </p>
            </div>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => window.open('/datapuur/ai-transformation', '_blank')}
            >
              <Zap className="w-4 h-4 mr-2" />
              Transform Data
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {transformedLoading ? (
              <div className="flex items-center justify-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : !transformedDatasets?.length ? (
              <EmptyStateDisplay
                type="no-data"
                title="No Transformed Datasets"
                description="Transform your source datasets using AI to create enhanced data for dashboards."
                actionButton={{
                  label: "Transform Data",
                  onClick: () => window.open('/datapuur/ai-transformation', '_blank')
                }}
              />
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {transformedDatasets.map((dataset: any) => renderDatasetCard(dataset, 'transformed'))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Validation Status Display */}
      {validation && <ValidationStatusCard validation={validation} validating={validating} />}
    </div>
  )
}

// Validation Status Component
const ValidationStatusCard: React.FC<{validation: any, validating: boolean}> = ({ 
  validation, 
  validating 
}) => {
  if (validating) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
            <span className="text-sm">Validating selected datasets...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!validation?.can_create_dashboard) {
    return (
      <Card className="border-destructive">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="w-4 h-4" />
            <span className="font-medium">Cannot create dashboard</span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {validation?.total_records === 0 
              ? "Selected datasets contain no data records"
              : "Some selected datasets are invalid or empty"
            }
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-green-200 bg-green-50">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 text-green-700">
          <CheckCircle className="w-4 h-4" />
          <span className="font-medium">Ready to create dashboard</span>
        </div>
        <p className="text-sm text-green-600 mt-1">
          {validation.results?.length || 0} dataset(s) selected with {validation.total_records?.toLocaleString() || 0} total records
        </p>
      </CardContent>
    </Card>
  )
}

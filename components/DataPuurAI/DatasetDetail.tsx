"use client"

import { useState, useEffect } from 'react'
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardFooter, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card'
import { 
  Tabs, 
  TabsContent, 
  TabsList, 
  TabsTrigger 
} from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Label } from '@/components/ui/label'
import { useToast } from '@/components/ui/use-toast'
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import * as z from "zod"
import { formatBytes, formatDate } from '@/lib/utils'
import { Loader2, Save, FileSpreadsheet, Database, GitBranch } from 'lucide-react'
import { TransformedDataset } from '@/lib/datapuur-types'

interface DatasetDetailProps {
  dataset: TransformedDataset
}

// Form schema for metadata update
const metadataFormSchema = z.object({
  description: z.string().optional(),
  metadata: z.record(z.string(), z.any()).optional(),
  columnMetadata: z.record(z.string(), z.any()).optional()
})

export function DatasetDetail({ dataset }: DatasetDetailProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const { toast } = useToast()
  
  // Initialize form with dataset values
  const form = useForm<z.infer<typeof metadataFormSchema>>({
    resolver: zodResolver(metadataFormSchema),
    defaultValues: {
      description: dataset.description || '',
      metadata: dataset.dataset_metadata || {},
      columnMetadata: dataset.column_metadata || {}
    }
  })
  
  const onSubmit = async (values: z.infer<typeof metadataFormSchema>) => {
    try {
      setIsLoading(true)
      
      // Get authentication token from localStorage
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('Authentication token not found')
      }
      
      const response = await fetch(`/api/datapuur-ai/transformed-datasets/${dataset.id}/metadata`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          description: values.description,
          metadata: values.metadata,
          column_metadata: values.columnMetadata
        })
      })
      
      if (!response.ok) {
        throw new Error('Failed to update dataset metadata')
      }
      
      toast({
        title: "Success",
        description: "Dataset metadata has been updated successfully.",
      })
      
    } catch (error) {
      console.error('Error updating dataset metadata:', error)
      toast({
        title: "Error",
        description: "Failed to update dataset metadata. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }
  
  const handleDownload = async () => {
    try {
      // Using the new API endpoint that takes dataset ID directly
      window.open(`/api/datapuur-ai/download/${dataset.id}`, '_blank')
    } catch (error) {
      toast({
        title: "Download Error",
        description: "Failed to download the dataset file.",
        variant: "destructive"
      })
    }
  }
  
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-2xl">{dataset.name}</CardTitle>
        <CardDescription>
          Created on {formatDate(new Date(dataset.created_at))}
        </CardDescription>
      </CardHeader>
      
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <div className="flex justify-between items-center mb-4 mx-6">
          <TabsList className="grid grid-cols-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="metadata">Metadata</TabsTrigger>
            <TabsTrigger value="lineage">Lineage</TabsTrigger>
          </TabsList>
          
          {activeTab === 'metadata' && (
            <Button 
              type="submit" 
              disabled={isLoading}
              onClick={form.handleSubmit(onSubmit)}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save Metadata
                </>
              )}
            </Button>
          )}
        </div>
        
        <TabsContent value="overview" className="px-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div>
              <h3 className="text-lg font-medium mb-2">Dataset Information</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Rows:</span>
                  <span>{dataset.row_count?.toLocaleString() || 'Unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Columns:</span>
                  <span>{dataset.column_count || 'Unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Size:</span>
                  <span>{dataset.file_size_bytes ? formatBytes(dataset.file_size_bytes) : 'Unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created By:</span>
                  <span>{dataset.created_by}</span>
                </div>
              </div>
            </div>
            
            <div>
              <h3 className="text-lg font-medium mb-2">Source Information</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Source:</span>
                  <span className="truncate max-w-[250px]" title={dataset.source_file_path}>
                    {dataset.name.replace('transformed_', '')}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Transformation Plan:</span>
                  <span className="truncate max-w-[250px]" title={dataset.transformation_plan_id}>
                    {dataset.transformation_plan_id || 'Not available'}
                  </span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="mb-6">
            <h3 className="text-lg font-medium mb-2">Description</h3>
            <p className="text-muted-foreground">
              {dataset.description || 'No description available'}
            </p>
          </div>
          

        </TabsContent>
        
        <TabsContent value="metadata" className="px-6">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Dataset Description</FormLabel>
                    <FormControl>
                      <Textarea 
                        placeholder="Enter a description for this dataset..." 
                        className="min-h-[100px]" 
                        {...field} 
                      />
                    </FormControl>
                    <FormDescription>
                      Provide a clear description of what this dataset contains and how it was transformed.
                    </FormDescription>
                  </FormItem>
                )}
              />
              
              <div>
                <h3 className="text-lg font-medium mb-4">Dataset Metadata</h3>
                <div className="grid grid-cols-1 gap-4 mb-4">
                  {Object.entries(dataset.dataset_metadata || {}).map(([key, value], idx) => (
                    <div key={idx} className="grid grid-cols-3 gap-4 items-center">
                      <Label htmlFor={`metadata-${key}`}>{key}</Label>
                      <Input 
                        id={`metadata-${key}`} 
                        value={typeof value === 'object' ? JSON.stringify(value) : String(value)} 
                        className="col-span-2"
                        readOnly
                      />
                    </div>
                  ))}
                </div>
              </div>
              
              <div>
                <h3 className="text-lg font-medium mb-4">Column Metadata</h3>
                <div className="grid grid-cols-1 gap-4 mb-4">
                  {Object.entries(dataset.column_metadata || {}).length > 0 ? (
                    Object.entries(dataset.column_metadata || {}).map(([col, colMeta]: [string, any], idx) => (
                      <Card key={idx} className="p-4">
                        <div className="flex justify-between items-center mb-4">
                          <h4 className="font-medium text-lg">{col}</h4>
                          <span className="px-2 py-1 bg-slate-100 text-slate-700 rounded text-xs">{colMeta.type}</span>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Left side: Statistics */}
                          <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-md">
                            <h5 className="text-sm font-medium mb-3 border-b dark:border-slate-700 pb-2">Statistics</h5>
                            <div className="space-y-2">
                              <div className="flex justify-between">
                                <span className="text-muted-foreground dark:text-slate-400">Missing Values:</span> 
                                <span className="font-medium dark:text-slate-200">{colMeta.missing_count} ({colMeta.missing_percentage?.toFixed(2)}%)</span>
                              </div>
                              
                              {colMeta.stats && Object.entries(colMeta.stats).map(([statKey, statValue]: [string, any], i) => (
                                <div key={i} className="flex justify-between">
                                  <span className="text-muted-foreground dark:text-slate-400">{statKey.replace(/_/g, ' ')}:</span> 
                                  <span className="font-medium dark:text-slate-200">
                                    {typeof statValue === 'number' ? 
                                      Number(statValue).toLocaleString(undefined, {maximumFractionDigits: 2}) : 
                                      String(statValue)}
                                  </span>
                                </div>
                              ))}
                              
                              {colMeta.sample_data && (
                                <div className="mt-3 pt-2 border-t dark:border-slate-700">
                                  <h6 className="text-xs font-medium mb-1 dark:text-slate-300">Sample Data</h6>
                                  <p className="text-xs text-muted-foreground dark:text-slate-400 font-mono break-all">{colMeta.sample_data}</p>
                                </div>
                              )}
                            </div>
                          </div>
                          
                          {/* Right side: Description */}
                          <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-md">
                            <h5 className="text-sm font-medium mb-3 border-b dark:border-slate-700 pb-2">Description</h5>
                            <FormField
                              control={form.control}
                              name={`columnMetadata.${col}.description`}
                              render={({ field }) => (
                                <FormItem className="space-y-1">
                                  <FormControl>
                                    <Textarea 
                                      placeholder={`Enter a description for ${col}...`}
                                      className="resize-none h-[calc(100%-24px)] min-h-[120px] bg-white dark:bg-slate-900 dark:text-slate-200 dark:border-slate-700"
                                      {...field}
                                    />
                                  </FormControl>
                                </FormItem>
                              )}
                            />
                          </div>
                        </div>
                      </Card>
                    ))
                  ) : (
                    <p className="text-muted-foreground">No column metadata available</p>
                  )}
                </div>
              </div>
              
              {/* Save Metadata button moved to below the tabs bar */}
            </form>
          </Form>
        </TabsContent>
        
        <TabsContent value="lineage" className="px-6">
          <div className="mb-6">
            <h3 className="text-lg font-medium mb-4">Data Lineage</h3>
            
            <div className="relative p-6 border rounded-md bg-slate-50 dark:bg-slate-900">
              <div className="flex items-center justify-center mb-8">
                <Database className="h-12 w-12 text-primary" />
                <div className="mx-4 text-center">
                  <div className="font-medium">{dataset.name.replace('transformed_', '')}</div>
                  <div className="text-sm text-muted-foreground">Source Dataset</div>
                </div>
              </div>
              
              <div className="absolute left-1/2 top-[110px] -translate-x-1/2 h-12 flex items-center justify-center">
                <GitBranch className="h-8 w-8 -rotate-90 text-muted-foreground" />
              </div>
              
              <div className="border-t border-dashed pt-8">
                <div className="flex items-center justify-center mt-4">
                  <FileSpreadsheet className="h-12 w-12 text-primary" />
                  <div className="mx-4 text-center">
                    <div className="font-medium">{dataset.name}</div>
                    <div className="text-sm text-muted-foreground">Transformed Dataset</div>
                  </div>
                </div>
              </div>
              
              <div className="mt-8 p-4 border rounded-md bg-white dark:bg-slate-800">
                <h4 className="font-medium mb-2">Transformation Details</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Transformation Date:</span>
                    <span>{formatDate(new Date(dataset.created_at))}</span>
                  </div>
                  {dataset.job_id && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Job ID:</span>
                      <span className="font-mono text-sm">{dataset.job_id}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </Card>
  )
}

"use client"

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/components/ui/use-toast'
import { DataSourcesList } from '@/components/DataPuurAI/DataSourcesList'
import { TransformationPlansList } from '@/components/DataPuurAI/TransformationPlansList'
import { CreateTransformationTab } from '@/components/DataPuurAI/CreateTransformationTab'

// Client component that safely uses useSearchParams inside Suspense boundary
export default function AITransformationContent() {
  const { toast } = useToast()
  const router = useRouter()
  const searchParams = useSearchParams()
  const tabParam = searchParams.get('tab')
  const [activeTab, setActiveTab] = useState(
    tabParam === 'plans' ? 'plans' : 
    tabParam === 'create' ? 'create' : 'datasources'
  )
  
  // Get any passed data source ID from the URL
  const dataSourceId = searchParams.get('file_id')
  const dataSourceName = searchParams.get('file_name')
  const draftPlanId = searchParams.get('draft_plan_id')

  // Update the URL when the tab changes
  const handleTabChange = (tab: string) => {
    setActiveTab(tab)
    const url = new URL(window.location.href)
    url.searchParams.set('tab', tab)
    window.history.pushState({}, '', url)
  }

  // Handle browser back/forward navigation
  useEffect(() => {
    const handlePopState = () => {
      const newTabParam = new URLSearchParams(window.location.search).get('tab')
      setActiveTab(
        newTabParam === 'plans' ? 'plans' : 
        newTabParam === 'create' ? 'create' : 'datasources'
      )
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  return (
    <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-4">
      <TabsList>
        <TabsTrigger value="datasources">Data Sources</TabsTrigger>
        <TabsTrigger value="plans">Transformation Plans</TabsTrigger>
      </TabsList>
      
      <TabsContent value="datasources">
        <Card>
          <CardHeader>
            <CardTitle>Available Data Sources</CardTitle>
            <CardDescription>
              Select a data source to create a new AI-powered transformation plan
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DataSourcesList />
          </CardContent>
        </Card>
      </TabsContent>
      
      <TabsContent value="plans">
        <Card>
          <CardHeader>
            <CardTitle>Transformation Plans</CardTitle>
            <CardDescription>
              View and manage your transformation plans
            </CardDescription>
          </CardHeader>
          <CardContent>
            <TransformationPlansList />
          </CardContent>
        </Card>
      </TabsContent>
      
      <TabsContent value="create">
        <Card>
          <CardHeader>
          </CardHeader>
          <CardContent>
            <CreateTransformationTab 
              initialPlanId={draftPlanId || undefined}
              dataSourceId={dataSourceId || undefined}
              dataSourceName={dataSourceName || undefined}
            />
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  )
}

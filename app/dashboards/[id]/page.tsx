"use client"

import React, { useState, useEffect, Suspense } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { MainLayout } from "@/components/main-layout"
import ProtectedRoute from "@/components/protected-route"
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, RefreshCw, Download, Settings, AlertCircle, CheckCircle } from 'lucide-react'

function DashboardViewContent() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const dashboardId = params.id as string
  const isBuilding = searchParams.get('building') === 'true'
  
  const [dashboard, setDashboard] = useState<any>(null)
  const [buildStatus, setBuildStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (dashboardId) {
      fetchDashboard()
      if (isBuilding) {
        // Start polling for build status
        const interval = setInterval(checkBuildStatus, 3000)
        return () => clearInterval(interval)
      }
    }
  }, [dashboardId, isBuilding])

  const fetchDashboard = async () => {
    try {
      const response = await fetch(`/api/dashboards/${dashboardId}`)
      if (response.ok) {
        const data = await response.json()
        setDashboard(data)
        
        // If dashboard is ready and we have a static path, redirect to it
        if (data.build_status === 'ready' && data.static_path && !isBuilding) {
          // For now, show the dashboard info instead of redirecting
          // Later we can implement static dashboard loading
        }
      } else if (response.status === 404) {
        setError('Dashboard not found')
      } else {
        setError('Failed to load dashboard')
      }
    } catch (err) {
      setError('Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }

  const checkBuildStatus = async () => {
    try {
      const response = await fetch(`/api/dashboards/${dashboardId}/build-status`)
      if (response.ok) {
        const status = await response.json()
        setBuildStatus(status)
        
        if (status.build_status === 'ready') {
          // Build completed successfully
          setDashboard((prev: any) => ({ ...prev, build_status: 'ready' }))
          // Stop polling
          return true
        } else if (status.build_status === 'failed') {
          // Build failed
          setDashboard((prev: any) => ({ ...prev, build_status: 'failed' }))
          return true
        }
      }
    } catch (err) {
      console.error('Failed to check build status:', err)
    }
    return false
  }

  const renderBuildStatus = () => {
    if (!dashboard) return null

    switch (dashboard.build_status) {
      case 'building':
        return (
          <Card className="border-blue-200 bg-blue-50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                <div>
                  <h3 className="font-semibold text-blue-900">Building Your Dashboard</h3>
                  <p className="text-sm text-blue-700">
                    We're generating your interactive dashboard with real data. This usually takes 2-5 minutes.
                  </p>
                </div>
              </div>
              
              {buildStatus && (
                <div className="mt-4 text-xs text-blue-600">
                  Started: {new Date(buildStatus.build_started_at).toLocaleString()}
                </div>
              )}
            </CardContent>
          </Card>
        )
      
      case 'ready':
        return (
          <Card className="border-green-200 bg-green-50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-6 h-6 text-green-600" />
                  <div>
                    <h3 className="font-semibold text-green-900">Dashboard Ready!</h3>
                    <p className="text-sm text-green-700">
                      Your interactive dashboard has been successfully generated.
                    </p>
                  </div>
                </div>
                <Button 
                  onClick={() => loadStaticDashboard()}
                  className="bg-green-600 hover:bg-green-700"
                >
                  View Dashboard
                </Button>
              </div>
              
              {buildStatus && (
                <div className="mt-4 text-xs text-green-600">
                  Completed: {new Date(buildStatus.build_completed_at).toLocaleString()}
                </div>
              )}
            </CardContent>
          </Card>
        )
      
      case 'failed':
        return (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-6 h-6 text-red-600" />
                <div>
                  <h3 className="font-semibold text-red-900">Build Failed</h3>
                  <p className="text-sm text-red-700">
                    There was an error generating your dashboard. Please try creating it again.
                  </p>
                  {buildStatus?.error_message && (
                    <p className="text-xs text-red-600 mt-2">
                      Error: {buildStatus.error_message}
                    </p>
                  )}
                </div>
              </div>
              
              <div className="mt-4 flex gap-2">
                <Button 
                  variant="outline"
                  onClick={() => router.push('/dashboard-creator/enhanced')}
                  className="text-red-700 border-red-300"
                >
                  Create New Dashboard
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => window.location.reload()}
                  className="text-red-700 border-red-300"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Retry
                </Button>
              </div>
            </CardContent>
          </Card>
        )
      
      default:
        return null
    }
  }

  const loadStaticDashboard = () => {
    if (dashboard?.static_path) {
      // For now, show an alert - later we can implement iframe loading or redirect
      alert(`Dashboard ready at: ${dashboard.static_path}`)
      // window.open(dashboard.static_path, '_blank')
    }
  }

  if (loading) {
    return (
      <ProtectedRoute requiredPermission="dashboard:read">
        <MainLayout>
          <div className="flex items-center justify-center min-h-screen">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
          </div>
        </MainLayout>
      </ProtectedRoute>
    )
  }

  if (error) {
    return (
      <ProtectedRoute requiredPermission="dashboard:read">
        <MainLayout>
          <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
            <div className="flex items-center gap-4 mb-6">
              <Button 
                variant="ghost" 
                onClick={() => router.push('/dashboards')}
                className="p-2"
              >
                <ArrowLeft className="w-4 h-4" />
              </Button>
              <h1 className="text-2xl font-bold">Dashboard Error</h1>
            </div>
            
            <Card className="border-red-200 bg-red-50">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <AlertCircle className="w-6 h-6 text-red-600" />
                  <div>
                    <h3 className="font-semibold text-red-900">Error</h3>
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
                
                <Button 
                  className="mt-4"
                  onClick={() => router.push('/dashboards')}
                >
                  Back to Dashboards
                </Button>
              </CardContent>
            </Card>
          </div>
        </MainLayout>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute requiredPermission="dashboard:read">
      <MainLayout>
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button 
                variant="ghost" 
                onClick={() => router.push('/dashboards')}
                className="p-2"
              >
                <ArrowLeft className="w-4 h-4" />
              </Button>
              <div>
                <h1 className="text-2xl font-bold">{dashboard?.dashboard_name}</h1>
                <p className="text-muted-foreground">
                  {dashboard?.description || 'AI-generated dashboard'}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Badge variant={
                dashboard?.build_status === 'ready' ? 'default' :
                dashboard?.build_status === 'building' ? 'secondary' :
                dashboard?.build_status === 'failed' ? 'destructive' : 'outline'
              }>
                {dashboard?.build_status === 'building' && '🔄 '}
                {dashboard?.build_status === 'ready' && '✅ '}
                {dashboard?.build_status === 'failed' && '❌ '}
                {dashboard?.build_status?.charAt(0).toUpperCase() + dashboard?.build_status?.slice(1)}
              </Badge>
              
              {dashboard?.build_status === 'ready' && (
                <>
                  <Button variant="outline" size="sm">
                    <Settings className="w-4 h-4 mr-2" />
                    Settings
                  </Button>
                  <Button variant="outline" size="sm">
                    <Download className="w-4 h-4 mr-2" />
                    Export
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Build Status */}
          {renderBuildStatus()}

          {/* Dashboard Info */}
          {dashboard && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Dashboard Info</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Created</label>
                    <p className="text-sm">{new Date(dashboard.created_at).toLocaleDateString()}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Last Updated</label>
                    <p className="text-sm">{new Date(dashboard.updated_at).toLocaleDateString()}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Status</label>
                    <p className="text-sm capitalize">{dashboard.build_status}</p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Data Sources</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {dashboard.source_dataset_ids?.length > 0 && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Source Datasets</label>
                      <p className="text-sm">{dashboard.source_dataset_ids.length} dataset(s)</p>
                    </div>
                  )}
                  {dashboard.transformed_dataset_ids?.length > 0 && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Transformed Datasets</label>
                      <p className="text-sm">{dashboard.transformed_dataset_ids.length} dataset(s)</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {dashboard.build_status === 'ready' && (
                    <Button onClick={loadStaticDashboard} className="w-full">
                      View Dashboard
                    </Button>
                  )}
                  <Button 
                    variant="outline" 
                    className="w-full"
                    onClick={() => router.push('/dashboard-creator/enhanced')}
                  >
                    Create New Dashboard
                  </Button>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}

export default function DashboardViewPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    }>
      <DashboardViewContent />
    </Suspense>
  )
}

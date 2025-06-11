'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { TransformationPlan } from '@/components/DataPuurAI/TransformationPlan'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function ClientDynamicTransformationPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [planData, setPlanData] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [transformationId, setTransformationId] = useState<string | null>(null)
  
  useEffect(() => {
    // Get the transformation ID from localStorage
    const storedId = localStorage.getItem('current_transformation_id')
    
    if (!storedId) {
      setError('No transformation plan ID found')
      setLoading(false)
      return
    }
    
    setTransformationId(storedId)
    
    const fetchTransformationPlan = async () => {
      try {
        console.log(`Fetching transformation plan: ${storedId}`)
        const response = await fetch(`/api/datapuur-ai/transformations/${storedId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })

        if (!response.ok) {
          throw new Error('Failed to fetch transformation plan')
        }

        const data = await response.json()
        setPlanData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred')
      } finally {
        setLoading(false)
      }
    }

    fetchTransformationPlan()
  }, [])

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex items-center justify-center h-[60vh]">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      </div>
    )
  }

  if (error || !planData) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardHeader>
            <CardTitle>Error Loading Transformation</CardTitle>
          </CardHeader>
          <CardContent>
            <Alert variant="destructive">
              <AlertDescription>
                {error || 'Transformation plan not found'}
              </AlertDescription>
            </Alert>
            <Button
              className="mt-4"
              variant="outline"
              onClick={() => router.push('/datapuur/ai-profile')}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to AI Profile
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-6">
      <div className="mb-6">
        <Button
          variant="ghost"
          onClick={() => router.push('/datapuur/ai-profile')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to AI Profile
        </Button>
      </div>
      
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">AI Transformation</h1>
          <p className="text-muted-foreground mt-2">
            Transform your data with AI-powered recommendations
          </p>
        </div>
        
        <TransformationPlan
          transformationPlan={planData}
          sessionId={planData.profile_session_id}
        />
      </div>
    </div>
  )
}

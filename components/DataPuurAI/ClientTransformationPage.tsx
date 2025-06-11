'use client'

import React, { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { TransformationPlan } from '@/components/DataPuurAI/TransformationPlan'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function ClientTransformationPage() {
  const params = useParams()
  const router = useRouter()
  const transformationId = params.id as string
  const [loading, setLoading] = useState(true)
  const [planData, setPlanData] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Check if we have a valid ID (not the placeholder from static export)
    if (!transformationId || transformationId === 'catch-all') {
      setError('Invalid transformation plan ID')
      setLoading(false)
      return
    }
    
    const fetchTransformationPlan = async () => {
      try {
        console.log(`Fetching transformation plan: ${transformationId}`)
        const response = await fetch(`/api/datapuur-ai/transformations/${transformationId}`, {
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
  }, [transformationId])

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

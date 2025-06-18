'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { TransformationPlan } from '@/components/DataPuurAI/TransformationPlan';
import ProtectedRoute from '@/components/protected-route';

// Simple client component that handles transformation plans with localStorage
function DynamicTransformationPageContent() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [planData, setPlanData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [transformationId, setTransformationId] = useState<string | null>(null);
  const [originPath, setOriginPath] = useState<string>('/datapuur/ai-profile'); // Default fallback
  
  useEffect(() => {
    console.log('[Transform] Dynamic page mounted, checking for transformation plan ID');
    
    // Get the transformation ID from localStorage
    const storedId = localStorage.getItem('current_transformation_id');
    console.log(`[Transform] Retrieved ID from localStorage: ${storedId || 'NOT FOUND'}`);
    
    // Extract origin path from URL query parameters
    try {
      const searchParams = new URLSearchParams(window.location.search);
      const fromParam = searchParams.get('from');
      if (fromParam) {
        console.log(`[Transform] Origin path found in URL: ${fromParam}`);
        setOriginPath(fromParam);
      } else {
        console.log('[Transform] No origin path in URL, using default: /datapuur/ai-profile');
      }
    } catch (err) {
      console.error('[Transform] Error parsing URL parameters:', err);
    }
    
    if (!storedId) {
      console.error('[Transform] No transformation plan ID in localStorage');
      setError('No transformation plan ID found');
      setLoading(false);
      return;
    }
    
    // Validate the ID format
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(storedId)) {
      console.error(`[Transform] Invalid transformation plan ID format: ${storedId}`);
      setError(`Invalid transformation plan ID format: ${storedId}`);
      setLoading(false);
      return;
    }
    
    setTransformationId(storedId);
    
    const fetchTransformationPlan = async () => {
      try {
        const token = localStorage.getItem('token');
        console.log(`[Transform] Fetching plan ${storedId} with token: ${token ? 'Present' : 'Missing'}`);
        
        const apiUrl = `/api/datapuur-ai/transformations/${storedId}`;
        console.log(`[Transform] API URL: ${apiUrl}`);
        
        const response = await fetch(apiUrl, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        console.log(`[Transform] API response status: ${response.status}`);
        if (response.headers) {
          console.log("[Transform] Response headers:", Object.fromEntries([...response.headers.entries()]));
        }
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error(`[Transform] Error response (${response.status}):`, errorText);
          throw new Error(`Failed to fetch plan: ${response.status} - ${errorText || 'No error details'}`); 
        }

        const data = await response.json();
        console.log("[Transform] Plan data retrieved successfully:", data);
        setPlanData(data);
      } catch (err) {
        console.error("[Transform] Error in fetchTransformationPlan:", err);
        setError(err instanceof Error ? err.message : 'An error occurred while loading the transformation plan');
      } finally {
        setLoading(false);
      }
    };

    fetchTransformationPlan();
  }, []);

  if (loading) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex items-center justify-center h-[60vh]">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      </div>
    );
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
              onClick={() => router.push(originPath)}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6">
      <div className="mb-6">
        <Button
          variant="ghost"
          onClick={() => router.push(originPath)}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
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
  );
}

// Wrap the component with ProtectedRoute to ensure proper permission protection
export default function DynamicTransformationPage() {
  return (
    <ProtectedRoute requiredPermission="datapuur:read">
      <DynamicTransformationPageContent />
    </ProtectedRoute>
  );
}

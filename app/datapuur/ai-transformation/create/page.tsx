"use client"

import { Suspense } from 'react'
import { Loader2 } from 'lucide-react'

/**
 * Main page component that uses Suspense for proper handling of client components
 */
export default function Page() {
  return (
    <Suspense fallback={
      <div className="flex flex-col items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="mt-4 text-sm text-muted-foreground">Loading...</p>
      </div>
    }>
      <RedirectComponent />
    </Suspense>
  )
}

/**
 * Client component that handles the actual redirect logic
 * This is wrapped in Suspense in the parent to properly handle useSearchParams
 */
function RedirectComponent() {
  // Import these hooks inside the component that's wrapped in Suspense
  const { useRouter, useSearchParams } = require('next/navigation')
  const router = useRouter()
  const searchParams = useSearchParams()
  
  // Use React.useEffect to avoid the import at the top level
  const React = require('react')
  React.useEffect(() => {
    // Get any query params from the current URL
    const fileId = searchParams.get('file_id') || ''
    const fileName = searchParams.get('file_name') || ''
    const filePath = searchParams.get('file_path') || ''
    
    // Build query string for the new URL
    const queryParams = new URLSearchParams()
    queryParams.set('tab', 'create')
    
    if (fileId) queryParams.set('file_id', fileId)
    if (fileName) queryParams.set('file_name', fileName)
    if (filePath) queryParams.set('file_path', filePath)
    
    // Redirect to the new tab-based URL
    router.push(`/datapuur/ai-transformation?${queryParams.toString()}`)
  }, [router, searchParams])
  
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <p className="mt-4 text-sm text-muted-foreground">Redirecting to Create Plan tab...</p>
    </div>
  )
}

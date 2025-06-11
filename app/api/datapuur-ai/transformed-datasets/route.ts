import { NextResponse } from 'next/server'
import { getApiBaseUrl } from '@/lib/config'

// For static export compatibility
export const dynamic = "force-static"

/**
 * GET handler for transformed datasets
 * - At build time: Returns empty array for static export compatibility
 * - At runtime: Fetches real transformed datasets from backend API
 */
export async function GET(request: Request) {
  // For static export, return empty datasets
  if (process.env.NODE_ENV === 'development' || process.env.NEXT_PHASE === 'phase-production-build') {
    return NextResponse.json([], {
      status: 200,
      headers: { 'X-Static-Export': 'true' }
    })
  }
  
  // For runtime requests, get authorization header and fetch from backend
  try {
    const authorization = request.headers.get('authorization')
    
    if (!authorization) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    
    // Extract pagination parameters from URL
    const url = new URL(request.url)
    const page = url.searchParams.get('page') || '1'
    const limit = url.searchParams.get('limit') || '10'
    
    // Call backend API
    const apiBaseUrl = getApiBaseUrl()
    const response = await fetch(
      `${apiBaseUrl}/api/datapuur-ai/transformed-datasets?page=${page}&limit=${limit}`,
      {
        headers: {
          Authorization: authorization,
          'Content-Type': 'application/json'
        },
      }
    )
    
    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching transformed datasets:', error)
    return NextResponse.json(
      { error: 'Failed to fetch transformed datasets', details: (error as Error).message },
      { status: 500 }
    )
  }
}

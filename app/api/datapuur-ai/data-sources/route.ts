import { NextResponse } from 'next/server'
import { getApiBaseUrl } from '@/lib/config'

// For static export compatibility
export const dynamic = "force-static"

/**
 * GET handler for data sources
 * - At build time: Returns empty array for static export compatibility
 * - At runtime: Forwards to the backend API with authorization
 */
export async function GET(request: Request) {
  // For static export or build time, return empty array
  if (process.env.NODE_ENV === 'development' || process.env.NEXT_PHASE === 'phase-production-build') {
    return NextResponse.json([], { 
      status: 200, 
      headers: { 'X-Static-Export': 'true' } 
    })
  }

  try {
    // Get authorization header from request
    const authorization = request.headers.get('authorization')
    if (!authorization) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Get pagination parameters
    const url = new URL(request.url)
    const page = url.searchParams.get('page') || '1'
    const limit = url.searchParams.get('limit') || '10'
    
    // Call the backend API with authorization header
    const apiBaseUrl = getApiBaseUrl()
    const response = await fetch(
      `${apiBaseUrl}/api/datapuur-ai/datasources?page=${page}&limit=${limit}`,
      { headers: { Authorization: authorization, 'Content-Type': 'application/json' } }
    )

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status} ${response.statusText}`)
    }

    // Return the data from the backend
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('Error fetching data sources:', error)
    return NextResponse.json(
      { error: 'Failed to fetch data sources', details: error.message },
      { status: 500 }
    )
  }
}

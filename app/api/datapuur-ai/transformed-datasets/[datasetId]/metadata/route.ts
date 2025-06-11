import { NextRequest, NextResponse } from 'next/server'
import { createStaticApiHandler } from '@/lib/api-helpers'

// Setup for static export compatibility
export const dynamic = "force-static"

// Define static params for build-time route generation
export function generateStaticParams() {
  return [{ datasetId: 'placeholder' }]
}

// Helper function to check if the request has a valid token with required permission
async function checkPermission(req: NextRequest, permission: string): Promise<{authorized: boolean, message?: string}> {
  // Get token from authorization header
  const authHeader = req.headers.get('authorization')
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return { authorized: false, message: 'Unauthorized: Missing or invalid token' }
  }
  
  // In a real implementation, you would validate the token and check permissions
  // For now, we'll assume the token is valid and has the required permission
  const token = authHeader.split(' ')[1]
  
  // This would normally check against your backend
  return { authorized: true }
}

// Create a mock dataset response for static build
const mockDatasetMetadata = {
  id: 'placeholder',
  name: 'Static Dataset',
  dataset_metadata: {
    columns: [
      { name: 'product_id', type: 'string', description: 'Unique product identifier' },
      { name: 'price', type: 'number', description: 'Product price in USD' },
      { name: 'category', type: 'string', description: 'Product category' },
      { name: 'in_stock', type: 'boolean', description: 'Whether the product is in stock' }
    ],
    row_count: 1250,
    created_at: new Date().toISOString(),
    description: 'Static placeholder for transformed dataset'
  }
}

// Use our static API handler for Next.js static export mode
const staticHandler = createStaticApiHandler(mockDatasetMetadata)

// GET handler that works with static export
export async function GET(request: NextRequest, { params }: { params: { datasetId: string } }) {
  try {
    // For static export build, this will never actually be called at runtime
    // But we need it defined for Next.js build process
    return NextResponse.json(mockDatasetMetadata);
  } catch (error: any) {
    return NextResponse.json({ error: error.message || 'Failed to fetch dataset metadata' }, { status: 500 });
  }
}

export async function PUT(
  req: NextRequest,
  { params }: { params: { datasetId: string } }
): Promise<NextResponse> {
  try {
    // Check permission - require write permission for metadata updates
    const permissionCheck = await checkPermission(req, 'datapuur:write')
    if (!permissionCheck.authorized) {
      return NextResponse.json({ error: permissionCheck.message || 'Forbidden: Insufficient permissions' }, { status: 403 })
    }
    
    const { datasetId } = params
    const body = await req.json()
    
    const authHeader = req.headers.get('authorization')
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/datapuur-ai/transformed-datasets/${datasetId}/metadata`, {
      method: 'PUT',
      headers: {
        'Authorization': authHeader || '',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    })
    
    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to update dataset metadata' }, 
        { status: response.status }
      )
    }
    
    const data = await response.json()
    return NextResponse.json(data)
    
  } catch (error: any) {
    console.error('Error updating dataset metadata:', error)
    return NextResponse.json(
      { error: 'Internal server error' }, 
      { status: 500 }
    )
  }
}

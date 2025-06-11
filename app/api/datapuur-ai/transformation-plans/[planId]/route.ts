import { NextRequest, NextResponse } from 'next/server'

// Use force-static for static export compatibility
export const dynamic = "force-static"

// Define static params for build-time route generation
export function generateStaticParams() {
  return [{ planId: 'placeholder' }]
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

export async function GET(
  req: NextRequest,
  { params }: { params: { planId: string } }
): Promise<NextResponse> {
  try {
    // Check permission
    const permissionCheck = await checkPermission(req, 'datapuur:read')
    if (!permissionCheck.authorized) {
      return NextResponse.json({ error: permissionCheck.message || 'Forbidden: Insufficient permissions' }, { status: 403 })
    }
    
    const { planId } = params
    
    const authHeader = req.headers.get('authorization')
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/datapuur-ai/transformation-plans/${planId}`, {
      headers: {
        'Authorization': authHeader || '',
        'Content-Type': 'application/json'
      }
    })
    
    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch transformation plan' }, 
        { status: response.status }
      )
    }
    
    const data = await response.json()
    return NextResponse.json(data)
    
  } catch (error) {
    console.error('Error fetching transformation plan:', error)
    return NextResponse.json(
      { error: 'Internal server error' }, 
      { status: 500 }
    )
  }
}

export async function PUT(
  req: NextRequest,
  { params }: { params: { planId: string } }
): Promise<NextResponse> {
  try {
    // Check permission
    const permissionCheck = await checkPermission(req, 'datapuur:write')
    if (!permissionCheck.authorized) {
      return NextResponse.json({ error: permissionCheck.message || 'Forbidden: Insufficient permissions' }, { status: 403 })
    }
    
    const { planId } = params
    const body = await req.json()
    
    const authHeader = req.headers.get('authorization')
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/datapuur-ai/transformation-plans/${planId}`, {
      method: 'PUT',
      headers: {
        'Authorization': authHeader || '',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    })
    
    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to update transformation plan' }, 
        { status: response.status }
      )
    }
    
    const data = await response.json()
    return NextResponse.json(data)
    
  } catch (error) {
    console.error('Error updating transformation plan:', error)
    return NextResponse.json(
      { error: 'Internal server error' }, 
      { status: 500 }
    )
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: { planId: string } }
): Promise<NextResponse> {
  try {
    // Check permission - require manage permission for deletion
    const permissionCheck = await checkPermission(req, 'datapuur:manage')
    if (!permissionCheck.authorized) {
      return NextResponse.json({ error: permissionCheck.message || 'Forbidden: Insufficient permissions' }, { status: 403 })
    }
    
    const { planId } = params
    
    const authHeader = req.headers.get('authorization')
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/datapuur-ai/transformation-plans/${planId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': authHeader || '',
        'Content-Type': 'application/json'
      }
    })
    
    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to delete transformation plan' }, 
        { status: response.status }
      )
    }
    
    return NextResponse.json({ success: true })
    
  } catch (error) {
    console.error('Error deleting transformation plan:', error)
    return NextResponse.json(
      { error: 'Internal server error' }, 
      { status: 500 }
    )
  }
}

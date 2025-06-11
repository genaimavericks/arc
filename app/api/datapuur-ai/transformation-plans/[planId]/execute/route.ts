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

export async function POST(
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
    
    const authHeader = req.headers.get('authorization')
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/datapuur-ai/transformation-plans/${planId}/execute`, {
      method: 'POST',
      headers: {
        'Authorization': authHeader || '',
        'Content-Type': 'application/json'
      }
    })
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      return NextResponse.json(
        { error: 'Failed to execute transformation plan', details: errorData }, 
        { status: response.status }
      )
    }
    
    const data = await response.json()
    return NextResponse.json(data)
    
  } catch (error: any) {
    console.error('Error executing transformation plan:', error)
    return NextResponse.json(
      { error: 'Internal server error' }, 
      { status: 500 }
    )
  }
}

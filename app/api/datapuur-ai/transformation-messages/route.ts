import { NextResponse, NextRequest } from "next/server";
import { getApiBaseUrl } from "@/lib/config";

export const dynamic = "force-static";
export const revalidate = 0; // This ensures the route is revalidated on every request

// POST /api/datapuur-ai/transformation-messages
export async function POST(request: Request) {
  // During static export build time, return a mock response
  const isStaticBuild = process.env.NODE_ENV === 'production' && process.env.NEXT_PHASE === 'phase-export';
  
  if (isStaticBuild) {
    return NextResponse.json({
      message: {
        id: 'mock-id',
        role: 'assistant',
        content: 'This is a mock AI response for static export.',
        timestamp: new Date().toISOString(),
        metadata: {}
      },
      plan_status: 'draft',
      transformation_steps: null,
      generated_script: null
    }, {
      status: 200,
      headers: {
        'X-Static-Export': 'true'
      }
    });
  }
  
  try {
    const body = await request.json();
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Authorization required' },
        { status: 401 }
      );
    }
    
    const apiBaseUrl = getApiBaseUrl();
    const response = await fetch(`${apiBaseUrl}/api/datapuur-ai/transformation-messages`, {
      method: 'POST',
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      return NextResponse.json(
        data,
        { status: response.status }
      );
    }
    
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error posting transformation message:', error);
    return NextResponse.json(
      { error: 'Failed to create transformation message' },
      { status: 500 }
    );
  }
}

// GET /api/datapuur-ai/transformation-messages?planId={planId}
export async function GET(request: NextRequest) {
  // During static export build time, return a mock response
  const isStaticBuild = process.env.NODE_ENV === 'production' && process.env.NEXT_PHASE === 'phase-export';
  
  if (isStaticBuild) {
    return NextResponse.json([
      {
        id: 'mock-id-1',
        role: 'system',
        content: 'Welcome to the transformation plan chat!',
        timestamp: new Date().toISOString(),
        metadata: {}
      }
    ], {
      status: 200,
      headers: {
        'X-Static-Export': 'true'
      }
    });
  }
  
  try {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Authorization required' },
        { status: 401 }
      );
    }
    
    const url = new URL(request.url);
    const planId = url.searchParams.get('planId');
    
    if (!planId) {
      return NextResponse.json(
        { error: 'planId is required' },
        { status: 400 }
      );
    }
    
    const apiBaseUrl = getApiBaseUrl();
    const response = await fetch(`${apiBaseUrl}/api/datapuur-ai/transformation-plans/${planId}/messages`, {
      method: 'GET',
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      return NextResponse.json(
        data,
        { status: response.status }
      );
    }
    
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching transformation messages:', error);
    return NextResponse.json(
      { error: 'Failed to fetch transformation messages' },
      { status: 500 }
    );
  }
}

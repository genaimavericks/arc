import { NextResponse } from 'next/server'

// Use force-static for static export compatibility
export const dynamic = "force-static"

// Mock transformation plans for static export
const MOCK_TRANSFORMATION_PLANS = [
  {
    id: '1',
    name: 'Sales Data Cleanup',
    description: 'Transformation plan for cleaning and normalizing sales data',
    status: 'completed',
    created_at: '2025-05-01T09:15:00Z',
    updated_at: '2025-05-01T10:30:00Z',
    transformation_steps: [
      {
        order: 1,
        operation: 'remove_duplicates',
        description: 'Remove duplicate sales entries',
        parameters: { columns: ['transaction_id'] }
      },
      {
        order: 2,
        operation: 'format_dates',
        description: 'Standardize date formats',
        parameters: { columns: ['sale_date'], format: 'YYYY-MM-DD' }
      }
    ],
    output_file_path: '/data/transformed/sales_clean.csv'
  },
  {
    id: '2',
    name: 'Customer Segmentation',
    description: 'Group customers by purchase behavior',
    status: 'in_progress',
    created_at: '2025-05-03T14:20:00Z',
    updated_at: '2025-05-03T15:45:00Z',
    transformation_steps: [
      {
        order: 1,
        operation: 'calculate_metrics',
        description: 'Calculate customer lifetime value',
        parameters: { metrics: ['total_spent', 'frequency', 'recency'] }
      },
      {
        order: 2,
        operation: 'cluster',
        description: 'Create customer segments using k-means',
        parameters: { num_clusters: 4, columns: ['total_spent', 'frequency', 'recency'] }
      }
    ],
    output_file_path: null
  }
]

// Static GET handler with no dependencies on request.headers
export async function GET(request: Request) {
  // During static export build time, this will be called without proper headers
  const isStaticBuild = process.env.NODE_ENV === 'production' && process.env.NEXT_PHASE === 'phase-export';
  
  // For static export or if no authorization header, return mock data
  if (isStaticBuild || !request.headers.get('Authorization')) {
    // Return mock data with the correct key structure expected by the frontend
    return NextResponse.json({ plans: MOCK_TRANSFORMATION_PLANS }, {
      status: 200,
      headers: {
        'X-Static-Export': 'true'
      }
    });
  }
  
  // During runtime, forward the request to the backend transformations endpoint
  try {
    // Get auth header
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Authorization required' },
        { status: 401 }
      );
    }
    
    // Get search parameters
    const url = new URL(request.url);
    const page = url.searchParams.get('page') || '1';
    const limit = url.searchParams.get('limit') || '10';
    
    // Import getApiBaseUrl on-demand to avoid issues during static build
    const { getApiBaseUrl } = await import('@/lib/config');
    
    // Forward to the correct backend endpoint
    const apiBaseUrl = getApiBaseUrl();
    const response = await fetch(`${apiBaseUrl}/api/datapuur-ai/transformations?page=${page}&limit=${limit}`, {
      method: 'GET',
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch transformation plans' }, 
        { status: response.status }
      );
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Error fetching transformation plans:', error);
    return NextResponse.json({ error: 'Failed to fetch transformation plans' }, { status: 500 });
  }
}

// POST method to create a new transformation plan
export async function POST(request: Request) {
  // During static export build time, return a mock response
  const isStaticBuild = process.env.NODE_ENV === 'production' && process.env.NEXT_PHASE === 'phase-export';
  
  if (isStaticBuild) {
    return NextResponse.json({ id: 'mock-id', name: 'New Transformation Plan' }, {
      status: 201,
      headers: {
        'X-Static-Export': 'true'
      }
    });
  }
  
  try {
    // Import getApiBaseUrl on-demand to avoid issues during static build
    const { getApiBaseUrl } = await import('@/lib/config');
    
    const body = await request.json();
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Authorization required' },
        { status: 401 }
      );
    }
    
    // Use the correct backend endpoint with proper base URL
    const apiBaseUrl = getApiBaseUrl();
    const response = await fetch(`${apiBaseUrl}/api/datapuur-ai/transformations`, {
      method: 'POST',
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to create transformation plan' }, 
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error creating transformation plan:', error);
    return NextResponse.json(
      { error: 'Internal server error' }, 
      { status: 500 }
    );
  }
}

import { NextResponse } from 'next/server'

// For static export compatibility
export const dynamic = "force-static"

// Mock data sources for static export (matches DataSource interface from frontend)
const MOCK_DATA_SOURCES = [
  { 
    id: '1', 
    name: 'Customer Database', 
    file_path: '/data/customer_data.csv',
    file_size: 1258291,
    row_count: 5000,
    column_count: 15,
    created_at: '2025-05-01T08:30:00Z',
    updated_at: null,
    data_type: 'CSV',
    has_profile: true
  },
  { 
    id: '2', 
    name: 'Product Catalog', 
    file_path: '/data/products.csv',
    file_size: 450000,
    row_count: 2500,
    column_count: 8,
    created_at: '2025-05-02T10:15:00Z',
    updated_at: null,
    data_type: 'CSV',
    has_profile: false
  },
  { 
    id: '3', 
    name: 'Marketing Analytics', 
    file_path: '/data/marketing_data.json',
    file_size: 780000,
    row_count: 3200,
    column_count: 12,
    created_at: '2025-05-03T14:20:00Z',
    updated_at: null,
    data_type: 'JSON',
    has_profile: true
  }
]

// Static GET handler with no dependencies on request.headers
export async function GET() {
  // For static export, just return the mock datasets
  // This will be called at build time and the output will be included in the static export
  return NextResponse.json(MOCK_DATA_SOURCES, {
    status: 200,
    headers: {
      // Add a header to indicate this is a static export response
      'X-Static-Export': 'true'
    }
  });
}

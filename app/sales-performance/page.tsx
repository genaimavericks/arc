"use client"

import React, { useEffect } from "react"
import { useRouter } from "next/navigation"
import { MainLayout } from "@/components/main-layout"
import { useAuth } from "@/lib/auth-context"
import { BarChart2, PlusCircle, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

// Mock data for the sales vs target chart
const salesData = {
  months: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
  sales: [250000, 310000, 380000, 340000, 360000, 410000],
  targets: [230000, 280000, 350000, 380000, 370000, 400000]
}

// Mock data for the customer segments
const customerSegments = [
  { name: "Enterprise", count: 24, revenue: 463222, growth: 8.7 },
  { name: "Mid-Market", count: 109, revenue: 289145, growth: 5.4 },
  { name: "SMB", count: 743, revenue: 97463, growth: 12.5 }
]

// Mock data for the product performance
const productPerformance = [
  { name: "Memory Foam Pillows", count: 2180, revenue: 8470, growth: 15.3 },
  { name: "Latex Hybrid", count: 1740, revenue: 9580, growth: 12.2 },
  { name: "PillowPerfect Basic", count: 3780, revenue: 4290, growth: 9.8 },
  { name: "Specialty/Team", count: 940, revenue: 5670, growth: 14.1 }
]

// Mock data for sales representatives
const salesRepresentatives = [
  { name: "Peter Jacobs", closed: 17, averageValue: 16340, conversion: 74.9 },
  { name: "Maria Cuellar", closed: 23, averageValue: 12450, conversion: 63.7 },
  { name: "Ethan Shaw", closed: 16, averageValue: 18190, conversion: 54.6 },
  { name: "Samantha Riley", closed: 19, averageValue: 14590, conversion: 68.5 },
]

export default function SalesPerformancePage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  
  // Redirect to login page if user is not authenticated
  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login')
    }
  }, [user, isLoading, router])
  
  // Don't render the dashboard until we know the user's authentication status
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    )
  }
  
  // If user is not authenticated, don't render anything (we're redirecting)
  if (!user) {
    return null
  }
  
  // Function to render the chart
  const renderChart = () => {
    return (
      <div className="relative h-[300px] w-full">
        {/* This is a simplified visual representation of the chart */}
        <div className="flex justify-between h-full relative">
          {salesData.months.map((month, index) => (
            <div key={month} className="flex flex-col items-center justify-end h-full relative" style={{ width: `${100 / salesData.months.length}%` }}>
              
              {/* Sales Bar */}
              <div 
                className="w-16 bg-[#a970ff] rounded-t-md" 
                style={{ height: `${(salesData.sales[index] / 500000) * 100}%` }}
              />
              
              {/* Target Bar (slightly narrower) */}
              <div 
                className="w-12 bg-[#29b6af]/70 rounded-t-md absolute" 
                style={{ 
                  height: `${(salesData.targets[index] / 500000) * 100}%`,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  zIndex: 10
                }}
              />
              
              {/* Month label */}
              <div className="mt-2 text-xs text-muted-foreground">{month}</div>
            </div>
          ))}
          
          {/* Simulated line for the chart */}
          <svg className="absolute top-0 left-0 w-full h-full pointer-events-none" style={{ zIndex: 20 }}>
            <path
              d={`M40,${280 - (salesData.sales[0] / 500000) * 280} ${salesData.months.map((_, i) => 
                `L${40 + (i * (100 / salesData.months.length) * 14)},${280 - (salesData.sales[i] / 500000) * 280}`
              ).join(' ')}`}
              fill="none"
              stroke="#29b6af"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <path
              d={`M40,${280 - (salesData.targets[0] / 500000) * 280} ${salesData.months.map((_, i) => 
                `L${40 + (i * (100 / salesData.months.length) * 14)},${280 - (salesData.targets[i] / 500000) * 280}`
              ).join(' ')}`}
              fill="none"
              stroke="#6366f1" 
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray="5,5"
            />
          </svg>
        </div>
        
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-muted-foreground">
          <span>500000</span>
          <span>400000</span>
          <span>300000</span>
          <span>200000</span>
          <span>100000</span>
          <span>0</span>
        </div>
      </div>
    )
  }

  return (
    <MainLayout>
      <div className="bg-[#0e111a] min-h-screen p-4 md:p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Sales Performance Deep Dive</h1>
            <p className="text-sm text-gray-400">
              Complete analysis of sales trends, customer segments, and performance across different dimensions
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="border-gray-700 text-gray-300 hover:bg-gray-800">
              Last Month
            </Button>
            <Button variant="outline" size="sm" className="border-gray-700 text-gray-300 hover:bg-gray-800">
              All Products
            </Button>
            <Button variant="outline" size="sm" className="border-gray-700 text-gray-300 hover:bg-gray-800">
              All Regions
            </Button>
            <Button size="sm" className="bg-[#3730a3] hover:bg-[#4338ca] text-white">
              Export Report
            </Button>
          </div>
        </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-[#121725] rounded-lg p-4 border border-[#1e293b]">
          <div className="flex items-center justify-between mb-2">
            <div>
              <div className="text-sm font-medium text-gray-400">Sales Growth</div>
              <div className="text-xs text-gray-500">Month over month</div>
            </div>
            <div className="bg-blue-900/30 p-2 rounded-md">
              <BarChart2 className="h-4 w-4 text-blue-400" />
            </div>
          </div>
          <div className="text-xl font-bold text-emerald-400">+18.7%</div>
          <div className="text-xs text-gray-500 mt-1">
            +4.5% from last month
          </div>
        </div>
        
        <div className="bg-[#121725] rounded-lg p-4 border border-[#1e293b]">
          <div className="flex items-center justify-between mb-2">
            <div>
              <div className="text-sm font-medium text-gray-400">Active Customers</div>
              <div className="text-xs text-gray-500">Across all segments</div>
            </div>
            <div className="bg-green-900/30 p-2 rounded-md">
              <PlusCircle className="h-4 w-4 text-green-400" />
            </div>
          </div>
          <div className="text-xl font-bold text-white">1,573</div>
          <div className="text-xs text-gray-500 mt-1">
            +120 from last month
          </div>
        </div>
        
        <div className="bg-[#121725] rounded-lg p-4 border border-[#1e293b]">
          <div className="flex items-center justify-between mb-2">
            <div>
              <div className="text-sm font-medium text-gray-400">Time to Close</div>
              <div className="text-xs text-gray-500">Average sales cycle</div>
            </div>
            <div className="bg-purple-900/30 p-2 rounded-md">
              <ChevronRight className="h-4 w-4 text-purple-400" />
            </div>
          </div>
          <div className="text-xl font-bold text-white">28 days</div>
          <div className="text-xs text-gray-500 mt-1">
            -2.5 days from previous quarter
          </div>
        </div>
      </div>

      {/* Main Chart */}
      <div className="bg-[#121725] rounded-lg p-6 border border-[#1e293b] mb-6">
        <div className="mb-3">
          <h3 className="text-lg font-medium text-white">Sales vs Target Performance</h3>
          <p className="text-sm text-gray-500">Monthly revenue and target comparison over past 6 months</p>
        </div>
        {renderChart()}
      </div>

      {/* Two-column layout for Customer and Product Segments */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Customer Segments */}
        <div className="bg-[#121725] rounded-lg p-6 border border-[#1e293b]">
          <div className="mb-3">
            <h3 className="text-lg font-medium text-white">Customer Segment Performance</h3>
            <p className="text-sm text-gray-500">Revenue and growth rate by customer segment</p>
          </div>
          <div className="space-y-4">
            {customerSegments.map((segment) => (
              <div key={segment.name} className="border border-[#2d3748] rounded-lg p-4 space-y-2 bg-[#1a202c]/50">
                <div className="flex justify-between items-center">
                  <div>
                    <h4 className="font-medium text-gray-200">{segment.name}</h4>
                    <p className="text-sm text-gray-400">
                      {segment.count} customers
                    </p>
                  </div>
                  <div className={`px-2 py-1 rounded text-xs font-medium ${segment.growth > 8 ? 'bg-emerald-900/50 text-emerald-400' : 'bg-gray-700 text-gray-300'}`}>
                    {segment.growth > 0 ? "+" : ""}{segment.growth}%
                  </div>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Avg Sales (YTD)</p>
                  <p className="font-medium text-gray-300">${segment.revenue.toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Product Performance */}
        <div className="bg-[#121725] rounded-lg p-6 border border-[#1e293b]">
          <div className="mb-3">
            <h3 className="text-lg font-medium text-white">Product Performance</h3>
            <p className="text-sm text-gray-500">Sales volume and revenue by product category</p>
          </div>
          <div className="space-y-4">
            {productPerformance.map((product) => (
              <div key={product.name} className="border border-[#2d3748] rounded-lg p-4 space-y-2 bg-[#1a202c]/50">
                <div className="flex justify-between items-center">
                  <div>
                    <h4 className="font-medium text-gray-200">{product.name}</h4>
                    <p className="text-sm text-gray-400">
                      {product.count} units
                    </p>
                  </div>
                  <div className={`px-2 py-1 rounded text-xs font-medium ${product.growth > 10 ? 'bg-emerald-900/50 text-emerald-400' : 'bg-gray-700 text-gray-300'}`}>
                    {product.growth > 0 ? "+" : ""}{product.growth}%
                  </div>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Unit Sales (YTD)</p>
                  <p className="font-medium text-gray-300">${product.revenue.toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sales Representatives Table */}
      <div className="bg-[#121725] rounded-lg p-6 border border-[#1e293b]">
        <div className="mb-4">
          <h3 className="text-lg font-medium text-white">Sales Representative Performance</h3>
          <p className="text-sm text-gray-500">Individual performance metrics for sales team</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-[#2d3748]">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">Sales Rep</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">Deals Closed</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">Average Value</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">Conversion Rate</th>
              </tr>
            </thead>
            <tbody>
              {salesRepresentatives.map((rep) => (
                <tr key={rep.name} className="border-b border-[#2d3748]">
                  <td className="py-3 px-4 text-sm font-medium text-gray-300">{rep.name}</td>
                  <td className="py-3 px-4 text-sm text-right text-gray-300">{rep.closed}</td>
                  <td className="py-3 px-4 text-sm text-right text-gray-300">${rep.averageValue.toLocaleString()}</td>
                  <td className="py-3 px-4 text-sm text-right">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${rep.conversion > 65 ? 'bg-emerald-900/50 text-emerald-400' : rep.conversion > 50 ? 'bg-gray-700 text-gray-300' : 'bg-red-900/50 text-red-400'}`}>
                      {rep.conversion}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    </MainLayout>
  )
}

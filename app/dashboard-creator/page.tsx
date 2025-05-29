"use client"

import { MainLayout } from "@/components/main-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useState } from "react"
import { BarChart, PieChart, LineChart } from "@/components/ui/charts"
import ProtectedRoute from "@/components/protected-route"

export default function DashboardCreator() {
  const [selectedWidgets, setSelectedWidgets] = useState<string[]>([])

  const availableWidgets = [
    { id: "kpi", name: "KPI Card", icon: "📊" },
    { id: "bar-chart", name: "Bar Chart", icon: "📊" },
    { id: "pie-chart", name: "Pie Chart", icon: "🥧" },
    { id: "line-chart", name: "Line Chart", icon: "📈" },
    { id: "table", name: "Data Table", icon: "🗃️" },
    { id: "trend-indicator", name: "Trend Indicator", icon: "📉" }
  ]

  return (
    <ProtectedRoute requiredPermission="dashboard:read">
      <MainLayout>
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
          <Tabs defaultValue="creation" className="space-y-4">
            <div className="flex items-center gap-4">
              <h2 className="text-2xl font-bold tracking-tight">Dashboard Creator</h2>
              <TabsList>
                <TabsTrigger value="creation">Creation</TabsTrigger>
                <TabsTrigger value="templates">Templates</TabsTrigger>
                <TabsTrigger value="saved">Saved</TabsTrigger>
              </TabsList>
            </div>
            
            <TabsContent value="creation" className="space-y-4">
              <Card>
                <CardHeader className="border-b pb-3">
                  <CardTitle className="flex gap-2 items-center">
                    <div className="bg-primary/10 p-1 rounded text-primary">✨</div>
                    Guided Dashboard Creation
                  </CardTitle>
                  <CardDescription>Follow the steps to build a custom dashboard, or use a template to get started quickly.</CardDescription>
                </CardHeader>
                
                <CardContent className="pt-5">
                  <div className="grid gap-8 md:grid-cols-3">
                    {/* Left side - Widget 1 */}
                    <Card className="col-span-1 border-2 border-primary/40 bg-primary/5">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base">Website Velocity Analysis</CardTitle>
                        <CardDescription className="text-xs">Track and optimize conversion rates, and identify bottlenecks in sales funnels</CardDescription>
                      </CardHeader>
                      <CardContent className="pb-2">
                        <div className="text-xs text-muted-foreground">Last 14 days</div>
                        <div className="h-32 flex items-center justify-center">
                          <LineChart 
                            data={[
                              { name: 'Mon', value: 65 },
                              { name: 'Tue', value: 59 },
                              { name: 'Wed', value: 80 },
                              { name: 'Thu', value: 81 },
                              { name: 'Fri', value: 56 },
                              { name: 'Sat', value: 55 },
                              { name: 'Sun', value: 40 },
                            ]}
                            height={100}
                          />
                        </div>
                      </CardContent>
                      <div className="px-6 pb-4">
                        <Button className="w-full" variant="outline">View Dashboard</Button>
                      </div>
                    </Card>
                    
                    {/* Middle - Widget 2 */}
                    <Card className="col-span-1">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base">Customer Acquisition Cost Dashboard</CardTitle>
                        <CardDescription className="text-xs">Monitor CAC metrics, and track conversion efficiency, with ROI analysis</CardDescription>
                      </CardHeader>
                      <CardContent className="pb-2">
                        <div className="text-xs text-muted-foreground">Last 30 days</div>
                        <div className="h-32 flex items-center justify-center">
                          <BarChart 
                            data={[
                              { name: 'Org', value: 65 },
                              { name: 'Soc', value: 59 },
                              { name: 'Paid', value: 80 },
                              { name: 'Email', value: 81 },
                            ]}
                            height={100}
                          />
                        </div>
                      </CardContent>
                      <div className="px-6 pb-4">
                        <Button className="w-full" variant="outline">View Dashboard</Button>
                      </div>
                    </Card>
                    
                    {/* Right side - Widget 3 */}
                    <Card className="col-span-1">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base">Territory Performance Comparison</CardTitle>
                        <CardDescription className="text-xs">Compare sales performance across regions, territories, and set targets</CardDescription>
                      </CardHeader>
                      <CardContent className="pb-2">
                        <div className="text-xs text-muted-foreground">Q2 Review</div>
                        <div className="h-32 flex items-center justify-center">
                          <BarChart 
                            data={[
                              { name: 'North', value: 65 },
                              { name: 'South', value: 59 },
                              { name: 'East', value: 80 },
                              { name: 'West', value: 81 },
                            ]}
                            height={100}
                          />
                        </div>
                      </CardContent>
                      <div className="px-6 pb-4">
                        <Button className="w-full" variant="outline">View Dashboard</Button>
                      </div>
                    </Card>
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle>Available Widgets</CardTitle>
                  <CardDescription>Customize your dashboard with these widgets</CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-3 md:grid-cols-6 gap-4">
                  {availableWidgets.map((widget) => (
                    <Card key={widget.id} className="p-4 cursor-pointer hover:border-primary transition-colors flex flex-col items-center justify-center text-center">
                      <div className="text-3xl mb-2">{widget.icon}</div>
                      <p className="text-sm font-medium">{widget.name}</p>
                      <p className="text-xs text-muted-foreground">Standard</p>
                    </Card>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="templates" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Dashboard Templates</CardTitle>
                  <CardDescription>Start with a pre-built dashboard</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card className="p-4">
                      <CardTitle className="text-base">Sales Performance</CardTitle>
                      <CardDescription className="text-xs mb-4">Track sales KPIs and performance metrics</CardDescription>
                      <Button>Use Template</Button>
                    </Card>
                    <Card className="p-4">
                      <CardTitle className="text-base">Customer Analytics</CardTitle>
                      <CardDescription className="text-xs mb-4">Monitor customer behavior and demographics</CardDescription>
                      <Button>Use Template</Button>
                    </Card>
                    <Card className="p-4">
                      <CardTitle className="text-base">Inventory Overview</CardTitle>
                      <CardDescription className="text-xs mb-4">Track stock levels and product performance</CardDescription>
                      <Button>Use Template</Button>
                    </Card>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="saved" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Recent Dashboards</CardTitle>
                  <CardDescription>Your previously created and saved dashboards</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center border-b border-border pb-4">
                      <div className="flex items-center gap-4">
                        <div className="w-8 h-8 bg-primary/20 rounded-full flex items-center justify-center text-primary">
                          📊
                        </div>
                        <div>
                          <h3 className="font-medium">Q3 Sales Performance Analysis</h3>
                          <p className="text-sm text-muted-foreground">Created 3 days ago</p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm">Edit</Button>
                        <Button variant="outline" size="sm" className="bg-primary text-primary-foreground">View</Button>
                      </div>
                    </div>
                    
                    <div className="flex justify-between items-center border-b border-border pb-4">
                      <div className="flex items-center gap-4">
                        <div className="w-8 h-8 bg-amber-500/20 rounded-full flex items-center justify-center text-amber-500">
                          📈
                        </div>
                        <div>
                          <h3 className="font-medium">Customer Acquisition Trends</h3>
                          <p className="text-sm text-muted-foreground">Last edited 2 weeks ago</p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm">Edit</Button>
                        <Button variant="outline" size="sm" className="bg-primary text-primary-foreground">View</Button>
                      </div>
                    </div>
                    
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-4">
                        <div className="w-8 h-8 bg-green-500/20 rounded-full flex items-center justify-center text-green-500">
                          🌎
                        </div>
                        <div>
                          <h3 className="font-medium">Territory-Revenue Comparison</h3>
                          <p className="text-sm text-muted-foreground">Last edited 3 days ago</p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm">Edit</Button>
                        <Button variant="outline" size="sm" className="bg-primary text-primary-foreground">View</Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}

"use client"

import { MainLayout } from "@/components/main-layout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AreaChart, BarChart, PieChart } from "@/components/ui/charts"
import ProtectedRoute from "@/components/protected-route"
import { Badge } from "@/components/ui/badge"

export default function FinancialDashboard() {
  return (
    <ProtectedRoute requiredPermission="command:read">
      <MainLayout>
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold tracking-tight">Revenue Deep Dive</h2>
            <p className="text-sm text-muted-foreground">Detailed revenue analysis by product line, customer segments, and geographic regions</p>
          </div>

          <Tabs defaultValue="all-metrics" className="space-y-4">
            <div className="flex items-center justify-between">
              <TabsList>
                <TabsTrigger value="all-metrics">All Metrics</TabsTrigger>
                <TabsTrigger value="us-&-canada">US & Canada</TabsTrigger>
                <TabsTrigger value="all-regions">All Regions</TabsTrigger>
              </TabsList>
            </div>
            
            <TabsContent value="all-metrics" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">$6.0M</div>
                    <p className="text-xs text-muted-foreground">
                      <span className="text-emerald-500">+14.2%</span> vs last period
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Active Users</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">8,650</div>
                    <p className="text-xs text-muted-foreground">
                      <span className="text-muted-foreground">average revenue per user</span>
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Top Region</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">N. America</div>
                    <p className="text-xs text-muted-foreground">
                      <span className="text-muted-foreground">38% of total revenue</span>
                    </p>
                  </CardContent>
                </Card>
              </div>
              
              <Card className="col-span-4">
                <CardHeader>
                  <CardTitle>Revenue Composition Trends</CardTitle>
                </CardHeader>
                <CardContent className="h-80">
                  <AreaChart
                    data={[
                      { 
                        name: 'Jan', 
                        enterprise: 20000, 
                        midMarket: 15000, 
                        smb: 10000,
                        startup: 5000
                      },
                      { 
                        name: 'Feb', 
                        enterprise: 22000, 
                        midMarket: 16000, 
                        smb: 11000,
                        startup: 6000
                      },
                      { 
                        name: 'Mar', 
                        enterprise: 25000, 
                        midMarket: 18000, 
                        smb: 12000,
                        startup: 7000
                      },
                      { 
                        name: 'Apr', 
                        enterprise: 27000, 
                        midMarket: 20000, 
                        smb: 13000,
                        startup: 8000
                      },
                      { 
                        name: 'May', 
                        enterprise: 30000, 
                        midMarket: 22000, 
                        smb: 14000,
                        startup: 9000
                      },
                      { 
                        name: 'Jun', 
                        enterprise: 32000, 
                        midMarket: 24000, 
                        smb: 15000,
                        startup: 10000
                      }
                    ]}
                    categories={['enterprise', 'midMarket', 'smb', 'startup']}
                    colors={['#22c55e', '#3b82f6', '#8b5cf6', '#f43f5e']}
                    height={350}
                  />
                </CardContent>
              </Card>
              
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Customer Segment Revenue</CardTitle>
                    <CardDescription>Ranked by revenue generated by customer segments</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {/* Enterprise */}
                      <div className="flex items-center justify-between border-b pb-4">
                        <div>
                          <div className="text-sm font-medium">Enterprise</div>
                          <div className="text-xs text-muted-foreground">41 customers</div>
                        </div>
                        <div className="space-y-1 text-right">
                          <div className="text-sm font-medium">$452,233</div>
                          <div className="flex gap-1 items-center justify-end">
                            <Badge variant="outline" className="bg-green-500/10 text-green-500 hover:bg-green-500/20 border-0">+9.5%</Badge>
                            <Badge variant="outline" className="hover:bg-muted/80 border-0">Details</Badge>
                          </div>
                        </div>
                      </div>
                      
                      {/* Mid-Market */}
                      <div className="flex items-center justify-between border-b pb-4">
                        <div>
                          <div className="text-sm font-medium">Mid-Market</div>
                          <div className="text-xs text-muted-foreground">128 customers</div>
                        </div>
                        <div className="space-y-1 text-right">
                          <div className="text-sm font-medium">$336,800</div>
                          <div className="flex gap-1 items-center justify-end">
                            <Badge variant="outline" className="bg-green-500/10 text-green-500 hover:bg-green-500/20 border-0">+10.7%</Badge>
                            <Badge variant="outline" className="hover:bg-muted/80 border-0">Details</Badge>
                          </div>
                        </div>
                      </div>
                      
                      {/* SMB */}
                      <div className="flex items-center justify-between border-b pb-4">
                        <div>
                          <div className="text-sm font-medium">SMB</div>
                          <div className="text-xs text-muted-foreground">332 customers</div>
                        </div>
                        <div className="space-y-1 text-right">
                          <div className="text-sm font-medium">$214,660</div>
                          <div className="flex gap-1 items-center justify-end">
                            <Badge variant="outline" className="bg-green-500/10 text-green-500 hover:bg-green-500/20 border-0">+8.2%</Badge>
                            <Badge variant="outline" className="hover:bg-muted/80 border-0">Details</Badge>
                          </div>
                        </div>
                      </div>
                      
                      {/* Startup */}
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-medium">Startup</div>
                          <div className="text-xs text-muted-foreground">541 customers</div>
                        </div>
                        <div className="space-y-1 text-right">
                          <div className="text-sm font-medium">$96,307</div>
                          <div className="flex gap-1 items-center justify-end">
                            <Badge variant="outline" className="bg-green-500/10 text-green-500 hover:bg-green-500/20 border-0">+15.4%</Badge>
                            <Badge variant="outline" className="hover:bg-muted/80 border-0">Details</Badge>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle>Geographic Revenue Distribution</CardTitle>
                    <CardDescription>Revenue breakdown by region</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px] flex items-center justify-center">
                      <PieChart
                        data={[
                          { name: 'North America', value: 2.73, fill: '#8884d8' },
                          { name: 'Europe', value: 1.92, fill: '#82ca9d' },
                          { name: 'Asia Pacific', value: 0.83, fill: '#ffc658' },
                          { name: 'Other', value: 0.52, fill: '#ff8042' },
                        ]}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                      <div className="space-y-1">
                        <div className="flex items-center">
                          <div className="w-3 h-3 rounded-full bg-[#8884d8] mr-2"></div>
                          <div className="text-sm">North America</div>
                        </div>
                        <div className="text-sm font-bold">$2.73M</div>
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center">
                          <div className="w-3 h-3 rounded-full bg-[#82ca9d] mr-2"></div>
                          <div className="text-sm">Europe</div>
                        </div>
                        <div className="text-sm font-bold">$1.92M</div>
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center">
                          <div className="w-3 h-3 rounded-full bg-[#ffc658] mr-2"></div>
                          <div className="text-sm">Asia Pacific</div>
                        </div>
                        <div className="text-sm font-bold">$0.83M</div>
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center">
                          <div className="w-3 h-3 rounded-full bg-[#ff8042] mr-2"></div>
                          <div className="text-sm">Other</div>
                        </div>
                        <div className="text-sm font-bold">$0.52M</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}

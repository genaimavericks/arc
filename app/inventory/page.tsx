"use client"

import { MainLayout } from "@/components/main-layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { BarChart } from "@/components/ui/charts"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"

export default function InventoryDashboard() {
  return (
    <MainLayout>
      <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
        <Tabs defaultValue="all-products" className="space-y-4">
          <div className="flex items-center justify-between">
            <TabsList>
              <TabsTrigger value="all-products">All Products</TabsTrigger>
              <TabsTrigger value="categories">Categories</TabsTrigger>
              <TabsTrigger value="low-in-stock">Low In Stock</TabsTrigger>
            </TabsList>
          </div>
          
          <TabsContent value="all-products" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total In Stock</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">727,000</div>
                  <p className="text-xs text-muted-foreground">
                    <span className="text-muted-foreground">across warehouses</span>
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Critical Items</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">143</div>
                  <p className="text-xs text-muted-foreground">
                    <span className="text-rose-500">requires immediate action</span>
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Avg Turnover Rate</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">2.5x</div>
                  <p className="text-xs text-muted-foreground">
                    <span className="text-muted-foreground">per year</span>
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Current Locations</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">24</div>
                  <p className="text-xs text-muted-foreground">
                    <span className="text-muted-foreground">stocking locations</span>
                  </p>
                </CardContent>
              </Card>
            </div>
            
            <Card>
              <CardHeader>
                <CardTitle>Stock Levels by Location</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-8">
                  {/* Warehouse A */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <p className="text-sm font-medium leading-none">Warehouse A</p>
                        <p className="text-sm text-muted-foreground">STOCK 313,000</p>
                      </div>
                      <div className="text-sm text-muted-foreground">70% filled</div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <Progress value={70} className="h-2" />
                      </div>
                      <div className="flex space-x-2">
                        <Button size="sm" variant="outline">Restock Order</Button>
                        <Button size="sm" variant="outline" className="bg-primary text-primary-foreground">View Inventory</Button>
                      </div>
                    </div>
                  </div>
                  
                  {/* Factory Shop */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <p className="text-sm font-medium leading-none">Factory Shop</p>
                        <p className="text-sm text-muted-foreground">STOCK 122,000</p>
                      </div>
                      <div className="text-sm text-muted-foreground">30% filled</div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <Progress value={30} className="h-2" />
                      </div>
                      <div className="flex space-x-2">
                        <Button size="sm" variant="outline">Restock Order</Button>
                        <Button size="sm" variant="outline" className="bg-primary text-primary-foreground">View Inventory</Button>
                      </div>
                    </div>
                  </div>
                  
                  {/* Distribution Center */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <p className="text-sm font-medium leading-none">Distribution Center</p>
                        <p className="text-sm text-muted-foreground">STOCK 192,000</p>
                      </div>
                      <div className="text-sm text-muted-foreground">85% filled</div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <Progress value={85} className="h-2" />
                      </div>
                      <div className="flex space-x-2">
                        <Button size="sm" variant="outline">Restock Order</Button>
                        <Button size="sm" variant="outline" className="bg-primary text-primary-foreground">View Inventory</Button>
                      </div>
                    </div>
                  </div>
                  
                  {/* Retail Stores */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <p className="text-sm font-medium leading-none">Retail Stores</p>
                        <p className="text-sm text-muted-foreground">STOCK 100,000</p>
                      </div>
                      <div className="text-sm text-muted-foreground">60% filled</div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <Progress value={60} className="h-2" />
                      </div>
                      <div className="flex space-x-2">
                        <Button size="sm" variant="outline">Restock Order</Button>
                        <Button size="sm" variant="outline" className="bg-primary text-primary-foreground">View Inventory</Button>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle>Inventory Movement Trends</CardTitle>
              </CardHeader>
              <CardContent>
                <BarChart
                  data={[
                    { name: 'Jan', value: 5000 },
                    { name: 'Feb', value: 8000 },
                    { name: 'Mar', value: 6000 },
                    { name: 'Apr', value: 7500 },
                    { name: 'May', value: 9000 },
                    { name: 'Jun', value: 7000 },
                    { name: 'Jul', value: 8500 },
                    { name: 'Aug', value: 7800 },
                  ]}
                  color="#f43f5e"
                  height={250}
                />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  )
}

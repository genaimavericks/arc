"use client"

import React, { useEffect } from "react"
import { Bot } from "lucide-react"
import { DjinniLayout } from "@/components/djinni/djinni-layout"
import { FactoryAstro } from "@/components/djinni/factory-astro"
import { useDjinniStore } from "@/lib/djinni/store"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function FactoryAstroPage() {
  const { setActiveModel } = useDjinniStore()
  
  // Set active model to factory_astro when this page loads
  useEffect(() => {
    setActiveModel("factory_astro")
    localStorage.setItem('djinni_active_model', 'factory_astro')
  }, [setActiveModel])
  
  return (
    <DjinniLayout>
      <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
        {/* Header */}
        <div className="flex flex-col">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot className="h-6 w-6 text-primary" />
              <h2 className="text-2xl font-bold tracking-tight">Factory Astro</h2>
            </div>
          </div>
          <p className="text-sm text-muted-foreground mt-1">AI-powered factory performance analysis and predictions</p>
        </div>
        
        {/* Factory Astro Card */}
        <Card>
          <CardHeader>
            <CardTitle>Ask Me About Your Factory Data</CardTitle>
            <CardDescription>Get insights and predictions about your factory performance</CardDescription>
          </CardHeader>
          <CardContent>
            <FactoryAstro />
          </CardContent>
        </Card>
      </div>
    </DjinniLayout>
  )
}

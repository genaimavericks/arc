"use client"

import React, { useEffect } from "react"
import { Bot } from "lucide-react"
import { DjinniLayout } from "@/components/djinni/djinni-layout"
import { ChurnAstro } from "@/components/djinni/churn-astro"
import { useDjinniStore } from "@/lib/djinni/store"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function ChurnAstroPage() {
  const { setActiveModel } = useDjinniStore()
  
  // Set active model to churn_astro when this page loads
  useEffect(() => {
    setActiveModel("churn_astro")
    localStorage.setItem('djinni_active_model', 'churn_astro')
  }, [setActiveModel])
  
  return (
    <DjinniLayout>
      <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
        {/* Header */}
        <div className="flex flex-col">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot className="h-6 w-6 text-primary" />
              <h2 className="text-2xl font-bold tracking-tight">Churn Astro</h2>
            </div>
          </div>
          <p className="text-sm text-muted-foreground mt-1">AI-powered customer churn analysis and retention strategies</p>
        </div>
        
        {/* Churn Astro Card */}
        <Card>
          <CardHeader>
            <CardTitle>Ask Me About Your Churn Data</CardTitle>
            <CardDescription>Analyze customer churn risk and retention strategies</CardDescription>
          </CardHeader>
          <CardContent>
            <ChurnAstro />
          </CardContent>
        </Card>
      </div>
    </DjinniLayout>
  )
}

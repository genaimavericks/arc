"use client"

import { DataPuurLayout } from "@/components/datapuur/datapuur-layout"

export default function TestProfilePage() {
  return (
    <DataPuurLayout>
      <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
        <h2 className="text-3xl font-bold tracking-tight">Data Profiles Test Page</h2>
        <p>This is a test page to verify routing is working correctly.</p>
      </div>
    </DataPuurLayout>
  )
}

import { DataDashboard } from "@/components/datapuur/data-dashboard"
import { DataPuurLayout } from "@/components/datapuur/datapuur-layout"
import { Search } from "lucide-react"
import { Input } from "@/components/ui/input"

export default function DataPuurPage() {
  return (
    <DataPuurLayout>
      <div className="flex-1 p-0">
        <DataDashboard />
      </div>
    </DataPuurLayout>
  )
}


import LoadingSpinner from "@/components/loading-spinner"
import { KGInsightsLayout } from "@/components/kginsights/kginsights-layout"

export default function Loading() {
  return (
    <KGInsightsLayout>
      <div className="flex-1 p-6 flex items-center justify-center">
        <LoadingSpinner />
      </div>
    </KGInsightsLayout>
  )
}
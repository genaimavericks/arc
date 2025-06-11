"use client"

import { DataPuurLayout } from '@/components/datapuur/datapuur-layout'
import { TransformationPlanDetail } from '@/components/DataPuurAI/TransformationPlanDetail'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'
import { useRouter } from 'next/navigation'

// Client component to handle interactive elements and client-side logic
export function TransformationPlanClient({ planId }: { planId: string }) {
  const router = useRouter()
  
  return (
    <DataPuurLayout>
      <div className="container mx-auto p-6">
        <Button 
          variant="outline" 
          className="mb-6"
          onClick={() => router.push('/datapuur/ai-transformation?tab=plans')}
        >
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Plans
        </Button>
        
        <TransformationPlanDetail planId={planId} />
      </div>
    </DataPuurLayout>
  )
}

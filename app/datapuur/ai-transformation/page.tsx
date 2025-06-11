// Server Component
import { Suspense } from 'react'
import { Loader2 } from 'lucide-react'
import { DataPuurLayout } from '@/components/datapuur/datapuur-layout'
import { Card, CardContent } from '@/components/ui/card'
import AITransformationContent from './client'

// Main page wrapper with Suspense boundary
export default function AITransformationPage() {
  return (
    <DataPuurLayout>
      <div className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">AI Transformation</h1>
        
        <Suspense fallback={
          <Card>
            <CardContent className="p-6 flex justify-center items-center">
              <Loader2 className="h-6 w-6 animate-spin mr-2" />
              <span>Loading transformation page...</span>
            </CardContent>
          </Card>
        }>
          <AITransformationContent />
        </Suspense>
      </div>
    </DataPuurLayout>
  )
}

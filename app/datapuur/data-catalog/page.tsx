"use client"

import { useState } from 'react'
import { DataPuurLayout } from '@/components/datapuur/datapuur-layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'
import { useToast } from '@/components/ui/use-toast'
import { TransformedDatasetsList } from '@/components/DataPuurAI/TransformedDatasetsList'
import { DatasetDetail } from '@/components/DataPuurAI/DatasetDetail'
import { TransformedDataset } from '@/lib/datapuur-types'

export default function DataCatalogPage() {
  const [selectedDataset, setSelectedDataset] = useState<TransformedDataset | null>(null)
  const { toast } = useToast()
  
  return (
    <DataPuurLayout>
      <div className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">Data Catalog</h1>
        
        {selectedDataset ? (
          <div>
            <Button 
              variant="outline" 
              className="mb-4" 
              onClick={() => setSelectedDataset(null)}
            >
              <ArrowLeft className="mr-2 h-4 w-4" /> Back to Catalog
            </Button>
            <DatasetDetail dataset={selectedDataset} />
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Transformed Datasets</CardTitle>
              <CardDescription>
                View and manage datasets created through AI transformations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <TransformedDatasetsList onSelectDataset={setSelectedDataset} />
            </CardContent>
          </Card>
        )}
      </div>
    </DataPuurLayout>
  )
}

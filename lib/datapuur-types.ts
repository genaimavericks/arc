export interface TransformedDataset {
  id: string
  name: string
  description: string | null
  source_file_path: string
  source_file_id: string | null
  transformed_file_path: string
  transformation_plan_id: string
  job_id: string | null
  dataset_metadata: Record<string, any> // Renamed from metadata to match backend model
  column_metadata: Record<string, any>
  row_count: number | null
  column_count: number | null
  file_size_bytes: number | null
  data_summary: Record<string, any> | null
  created_at: string
  created_by: string
  updated_at: string
}

export interface TransformationStep {
  order: number
  operation: string
  description: string
  parameters: Record<string, any>
}

export interface TransformationPlan {
  id: string
  name: string
  description: string | null
  status: string
  created_at: string
  updated_at: string
  transformation_steps: TransformationStep[]
  output_file_path: string | null
}

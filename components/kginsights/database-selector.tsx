'use client'

import { useState, useEffect } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Loader2 } from 'lucide-react'

interface DatabaseSelectorProps {
  selectedDatabase: string
  onDatabaseChange: (database: string) => void
  className?: string
}

export function DatabaseSelector({
  selectedDatabase,
  onDatabaseChange,
  className = ''
}: DatabaseSelectorProps) {
  const [databases, setDatabases] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchDatabases = async () => {
      try {
        setLoading(true)
        
        const response = await fetch('/api/graph/db', {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (!response.ok) {
          throw new Error(`Failed to fetch database configurations: ${response.status}`)
        }
        
        const data = await response.json()
        
        if (data && data.databases && Array.isArray(data.databases)) {
          setDatabases(data.databases)
          
          // Set default selection if none is selected
          if (!selectedDatabase && data.databases.length > 0) {
            onDatabaseChange(data.databases[0])
          }
        } else {
          console.warn('Unexpected API response format:', data)
          // Use fallback values
          const fallbackDatabases = ['default_graph', 'social_graph', 'ecommerce_graph']
          setDatabases(fallbackDatabases)
          
          if (!selectedDatabase && fallbackDatabases.length > 0) {
            onDatabaseChange(fallbackDatabases[0])
          }
        }
      } catch (error) {
        console.error('Error fetching database configurations:', error)
        setError(error instanceof Error ? error.message : 'Unknown error')
        
        // Use fallback values
        const fallbackDatabases = ['default_graph', 'social_graph', 'ecommerce_graph']
        setDatabases(fallbackDatabases)
        
        if (!selectedDatabase && fallbackDatabases.length > 0) {
          onDatabaseChange(fallbackDatabases[0])
        }
      } finally {
        setLoading(false)
      }
    }
    
    fetchDatabases()
  }, [selectedDatabase, onDatabaseChange])

  return (
    <div className={className}>
      {loading ? (
        <div className="flex items-center space-x-2 h-10 px-4 py-2 rounded-md border border-input">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Loading databases...</span>
        </div>
      ) : (
        <Select value={selectedDatabase} onValueChange={onDatabaseChange}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select database configuration" />
          </SelectTrigger>
          <SelectContent>
            {databases.map((database) => (
              <SelectItem key={database} value={database}>
                {database}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
      {error && (
        <p className="text-sm text-destructive mt-1">
          {error}
        </p>
      )}
    </div>
  )
}

"use client"

import { useState, ChangeEvent, FocusEvent } from "react"
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"

interface ChunkSizeConfigProps {
  chunkSize: number
  onChunkSizeChange: (size: number) => void
  disabled?: boolean
}

export function ChunkSizeConfig({ chunkSize, onChunkSizeChange, disabled = false }: ChunkSizeConfigProps) {
  const [localChunkSize, setLocalChunkSize] = useState<number>(chunkSize)

  const handleSliderChange = (value: number[]) => {
    const newValue = value[0]
    setLocalChunkSize(newValue)
    onChunkSizeChange(newValue)
  }

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const value = Number.parseInt(e.target.value)
    if (!isNaN(value)) {
      // Allow any valid input to be entered temporarily
      if (value >= 100 && value <= 10000) {
        // Only update the actual value if it's within range
        setLocalChunkSize(value)
        onChunkSizeChange(value)
      } else if (e.target.value === "" || e.target.value === "1" || e.target.value === "10") {
        // Allow typing "1", "10" on the way to typing "100" without validation
        setLocalChunkSize(parseInt(e.target.value) || 0)
      }
    }
  }

  // When input loses focus, ensure the value is within valid range
  const handleInputBlur = (e: FocusEvent<HTMLInputElement>) => {
    const value = Number.parseInt(e.target.value)
    if (isNaN(value) || value < 100) {
      setLocalChunkSize(100)
      onChunkSizeChange(100)
    } else if (value > 10000) {
      setLocalChunkSize(10000)
      onChunkSizeChange(10000)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start">
        <div className="flex-1">
          <Label htmlFor="chunkSize" className="text-foreground mb-1 block">
            Chunk Size (records per batch)
          </Label>
          <div className="text-sm text-muted-foreground mb-4">
            Adjust the number of records processed at once for optimal performance
          </div>
        </div>
        <div className="w-24">
          <Input
            id="chunkSize"
            type="number"
            min={100}
            max={10000}
            step={100}
            value={localChunkSize}
            onChange={handleInputChange}
            onBlur={handleInputBlur}
            disabled={disabled}
            className="text-right"
          />
        </div>
      </div>

      <Slider
        value={[localChunkSize]}
        min={100}
        max={10000}
        step={100}
        onValueChange={handleSliderChange}
        disabled={disabled}
        className="py-4"
      />

      <div className="flex justify-between text-xs text-muted-foreground">
        <span>100</span>
        <span>1000</span>
        <span>5000</span>
        <span>10000</span>
      </div>
    </div>
  )
}

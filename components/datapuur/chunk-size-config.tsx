"use client"

import { useState, ChangeEvent, FocusEvent, useEffect, useMemo } from "react"
import * as SliderPrimitive from "@radix-ui/react-slider"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

interface ChunkSizeConfigProps {
  chunkSize: number
  onChunkSizeChange: (size: number) => void
  disabled?: boolean
}

// Custom non-linear slider with precise positioning
const NonLinearSlider = ({ 
  value, 
  min, 
  max, 
  step, 
  onChange, 
  disabled, 
  className,
  markers = [100, 1000, 5000, 10000]
}: { 
  value: number
  min: number
  max: number
  step: number
  onChange: (value: number) => void
  disabled?: boolean
  className?: string
  markers?: number[]
}) => {
  // Calculate the position percentage for each marker
  const markerPositions = useMemo(() => {
    // Use a custom scale that ensures the markers are positioned correctly
    const positions: Record<number, number> = {};
    
    // Calculate positions based on a custom non-linear scale
    markers.forEach(marker => {
      // This formula creates a more accurate visual representation
      // It ensures 100, 1000, 5000, and 10000 are positioned correctly
      if (marker === min) {
        positions[marker] = 0;
      } else if (marker === max) {
        positions[marker] = 100;
      } else if (marker === 1000) {
        positions[marker] = 33.33; // Position 1000 at 1/3 of the slider
      } else if (marker === 5000) {
        positions[marker] = 66.67; // Position 5000 at 2/3 of the slider
      } else {
        // For any other markers, interpolate based on nearest defined markers
        const lowerMarker = [...markers].filter(m => m < marker).sort((a, b) => b - a)[0] || min;
        const upperMarker = [...markers].filter(m => m > marker).sort((a, b) => a - b)[0] || max;
        
        const lowerPos = positions[lowerMarker] || 0;
        const upperPos = positions[upperMarker] || 100;
        
        // Linear interpolation between the nearest defined markers
        const ratio = (marker - lowerMarker) / (upperMarker - lowerMarker);
        positions[marker] = lowerPos + ratio * (upperPos - lowerPos);
      }
    });
    
    return positions;
  }, [markers, min, max]);
  
  // Convert value to slider position
  const valueToPosition = (val: number): number => {
    // Find the nearest markers below and above the value
    const lowerMarker = [...markers].filter(m => m <= val).sort((a, b) => b - a)[0] || min;
    const upperMarker = [...markers].filter(m => m >= val).sort((a, b) => a - b)[0] || max;
    
    // If the value exactly matches a marker, return its position
    if (markerPositions[val] !== undefined) {
      return markerPositions[val];
    }
    
    // Linear interpolation between the nearest markers
    const lowerPos = markerPositions[lowerMarker];
    const upperPos = markerPositions[upperMarker];
    const ratio = (val - lowerMarker) / (upperMarker - lowerMarker);
    
    return lowerPos + ratio * (upperPos - lowerPos);
  };
  
  // Convert slider position to value
  const positionToValue = (pos: number): number => {
    // Find the nearest marker positions below and above the position
    const markerEntries = Object.entries(markerPositions).map(([val, position]) => ({ 
      value: parseInt(val), 
      position 
    }));
    
    const lowerEntry = [...markerEntries].filter(e => e.position <= pos).sort((a, b) => b.position - a.position)[0] 
      || { value: min, position: 0 };
    const upperEntry = [...markerEntries].filter(e => e.position >= pos).sort((a, b) => a.position - b.position)[0] 
      || { value: max, position: 100 };
    
    // If position exactly matches a marker position, return its value
    const exactMatch = markerEntries.find(e => Math.abs(e.position - pos) < 0.01);
    if (exactMatch) {
      return exactMatch.value;
    }
    
    // Linear interpolation between the nearest marker positions
    const ratio = (pos - lowerEntry.position) / (upperEntry.position - lowerEntry.position || 1);
    const interpolatedValue = lowerEntry.value + ratio * (upperEntry.value - lowerEntry.value);
    
    // Round to the nearest step
    return Math.round(interpolatedValue / step) * step;
  };
  
  // Calculate the current position for the slider
  const position = valueToPosition(value);
  
  // Handle slider change
  const handleSliderChange = (newPositions: number[]) => {
    const newValue = positionToValue(newPositions[0]);
    onChange(newValue);
  };
  
  return (
    <SliderPrimitive.Root
      className={cn(
        "relative flex w-full touch-none select-none items-center",
        className
      )}
      value={[position]}
      min={0}
      max={100}
      step={0.1}
      onValueChange={handleSliderChange}
      disabled={disabled}
    >
      <SliderPrimitive.Track className="relative h-2 w-full grow overflow-hidden rounded-full bg-secondary">
        <SliderPrimitive.Range className="absolute h-full bg-primary" />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb className="block h-5 w-5 rounded-full border-2 border-primary bg-background ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50" />
    </SliderPrimitive.Root>
  );
};

export function ChunkSizeConfig({ chunkSize, onChunkSizeChange, disabled = false }: ChunkSizeConfigProps) {
  // Use a single source of truth for the value
  const [value, setValue] = useState<number>(chunkSize)
  const [inputValue, setInputValue] = useState<string>(chunkSize.toString())

  // Update local state when prop changes
  useEffect(() => {
    setValue(chunkSize)
    setInputValue(chunkSize.toString())
  }, [chunkSize])

  const handleSliderChange = (newValue: number) => {
    setValue(newValue)
    setInputValue(newValue.toString())
    onChunkSizeChange(newValue)
  }

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    // Always update the input display value
    setInputValue(e.target.value)
    
    const newValue = Number.parseInt(e.target.value)
    if (!isNaN(newValue) && newValue >= 100 && newValue <= 10000) {
      // Only update the slider when we have a valid value
      setValue(newValue)
      onChunkSizeChange(newValue)
    }
  }

  const handleInputBlur = (e: FocusEvent<HTMLInputElement>) => {
    const inputVal = Number.parseInt(e.target.value)
    
    let validValue: number
    if (isNaN(inputVal) || inputVal < 100) {
      validValue = 100
    } else if (inputVal > 10000) {
      validValue = 10000
    } else {
      validValue = inputVal
    }
    
    // Ensure all values are synchronized
    setValue(validValue)
    setInputValue(validValue.toString())
    onChunkSizeChange(validValue)
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
            value={inputValue}
            onChange={handleInputChange}
            onBlur={handleInputBlur}
            disabled={disabled}
            className="text-right"
          />
        </div>
      </div>

      <div className="py-4">
        <NonLinearSlider
          value={value}
          min={100}
          max={10000}
          step={100}
          onChange={handleSliderChange}
          disabled={disabled}
          markers={[100, 1000, 5000, 10000]}
        />
      </div>

      <div className="flex justify-between text-xs text-muted-foreground">
        <span>100</span>
        <span>1000</span>
        <span>5000</span>
        <span>10000</span>
      </div>
    </div>
  )
}

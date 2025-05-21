"use client"

import { useState, useRef, useEffect } from "react"

// Autocomplete suggestion type
export interface AutocompleteSuggestion {
  text: string
  description?: string | null
}

// AutocompleteSuggestions component props
export interface AutocompleteSuggestionsProps {
  suggestions: AutocompleteSuggestion[]
  visible: boolean
  onSelect: (suggestion: string) => void
  inputRef: React.RefObject<HTMLTextAreaElement>
}

export const AutocompleteSuggestions = ({ suggestions, visible, onSelect, inputRef }: AutocompleteSuggestionsProps) => {
  const [activeIndex, setActiveIndex] = useState(-1)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  
  // Reset active index when suggestions change
  useEffect(() => {
    setActiveIndex(-1)
  }, [suggestions])
  
  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!visible || suggestions.length === 0) return
      
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setActiveIndex(prev => (prev + 1) % suggestions.length)
          break
        case 'ArrowUp':
          e.preventDefault()
          setActiveIndex(prev => (prev - 1 + suggestions.length) % suggestions.length)
          break
        case 'Enter':
          if (activeIndex >= 0 && activeIndex < suggestions.length) {
            e.preventDefault()
            onSelect(suggestions[activeIndex].text)
          }
          break
        case 'Escape':
          e.preventDefault()
          // Close suggestions
          return
        case 'Tab':
          if (activeIndex >= 0 && activeIndex < suggestions.length) {
            e.preventDefault()
            onSelect(suggestions[activeIndex].text)
          } else if (suggestions.length > 0) {
            e.preventDefault()
            onSelect(suggestions[0].text)
          }
          break
      }
    }
    
    // Add event listener to the input element
    const inputElement = inputRef.current
    if (inputElement) {
      inputElement.addEventListener('keydown', handleKeyDown)
    }
    
    return () => {
      if (inputElement) {
        inputElement.removeEventListener('keydown', handleKeyDown)
      }
    }
  }, [visible, suggestions, activeIndex, onSelect, inputRef])
  
  // Scroll active item into view
  useEffect(() => {
    if (activeIndex >= 0 && suggestionsRef.current) {
      const activeElement = suggestionsRef.current.children[activeIndex] as HTMLElement
      if (activeElement) {
        activeElement.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [activeIndex])
  
  if (!visible || suggestions.length === 0) return null
  
  return (
    <div 
      className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md bg-card border shadow-lg"
      ref={suggestionsRef}
    >
      <div className="py-1 text-sm">
        {suggestions.map((suggestion, index) => (
          <div
            key={`${suggestion.text}-${index}`}
            className={`px-3 py-2 cursor-pointer ${index === activeIndex ? 'bg-primary/10 text-primary' : 'hover:bg-muted'}`}
            onClick={() => onSelect(suggestion.text)}
          >
            <div className="font-medium">{suggestion.text}</div>
            {suggestion.description && suggestion.description !== null && (
              <div className="text-xs text-muted-foreground">{suggestion.description}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

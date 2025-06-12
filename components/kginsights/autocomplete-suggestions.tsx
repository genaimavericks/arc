"use client"

import React, { useState, useEffect, useRef, KeyboardEvent } from 'react';
import { AutocompleteSuggestion } from './autocomplete-service';
import { cn } from '@/lib/utils';
import { CheckCircle, AlertCircle } from 'lucide-react';

interface AutocompleteSuggestionsProps {
  suggestions: AutocompleteSuggestion[];
  visible: boolean;
  onSelect: (suggestion: string) => void;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
}

export function AutocompleteSuggestions({
  suggestions,
  visible,
  onSelect,
  inputRef
}: AutocompleteSuggestionsProps) {
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Reset selected index when suggestions change
  useEffect(() => {
    setSelectedIndex(-1);
  }, [suggestions]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent<HTMLElement>) => {
      if (!visible || suggestions.length === 0) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev => (prev + 1) % suggestions.length);
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => (prev <= 0 ? suggestions.length - 1 : prev - 1));
          break;
        case 'Tab':
        case 'Enter':
          if (selectedIndex >= 0) {
            e.preventDefault();
            onSelect(suggestions[selectedIndex].text);
          }
          break;
        case 'Escape':
          // Let the parent component handle closing
          break;
      }
    };

    // Add event listener to the input element
    const input = inputRef.current;
    if (input) {
      input.addEventListener('keydown', handleKeyDown as any);
      return () => {
        input.removeEventListener('keydown', handleKeyDown as any);
      };
    }
  }, [visible, suggestions, selectedIndex, onSelect, inputRef]);

  // Scroll selected item into view
  useEffect(() => {
    if (selectedIndex >= 0 && suggestionsRef.current) {
      const selectedElement = suggestionsRef.current.children[selectedIndex] as HTMLElement;
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex]);

  if (!visible || suggestions.length === 0) {
    return null;
  }

  return (
    <div className="absolute bottom-full left-0 w-full bg-background border rounded-md shadow-lg max-h-60 overflow-y-auto z-50">
      <div ref={suggestionsRef} className="py-1">
        {suggestions.map((suggestion, index) => (
          <div
            key={`${suggestion.text}-${index}`}
            className={cn(
              'px-4 py-2 cursor-pointer hover:bg-muted/50 flex flex-col',
              selectedIndex === index && 'bg-muted',
              suggestion.type === 'grammar' && 'border-l-2 border-amber-500',
              suggestion.type === 'spelling' && 'border-l-2 border-blue-500'
            )}
            onClick={() => onSelect(suggestion.text)}
            onMouseEnter={() => setSelectedIndex(index)}
          >
            <div className="font-medium flex items-center gap-2">
              {suggestion.type === 'grammar' && <AlertCircle className="h-4 w-4 text-amber-500" />}
              {suggestion.type === 'spelling' && <CheckCircle className="h-4 w-4 text-blue-500" />}
              {suggestion.text}
            </div>
            {suggestion.description && (
              <div className="text-xs text-muted-foreground">{suggestion.description}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export { type AutocompleteSuggestion };

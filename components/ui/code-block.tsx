"use client"

import React from 'react'
import { cn } from '@/lib/utils'

interface CodeBlockProps {
  code: string
  language?: string
  className?: string
}

export function CodeBlock({ code, language = 'plaintext', className }: CodeBlockProps) {
  return (
    <div className={cn("relative rounded-lg bg-muted", className)}>
      <div className="flex items-center justify-between px-4 py-2 border-b">
        <span className="text-xs text-muted-foreground">{language}</span>
      </div>
      <pre className="p-4 overflow-auto">
        <code className="text-sm">{code}</code>
      </pre>
    </div>
  )
}

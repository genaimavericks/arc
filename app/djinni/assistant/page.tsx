"use client"

import { DjinniAssistantWrapper } from "@/components/djinni/djinni-assistant"
import ProtectedRoute from "@/components/protected-route"

export default function DjinniAssistantPage() {
  return (
    <ProtectedRoute requiredPermission="djinni:read">
      <DjinniAssistantWrapper />
    </ProtectedRoute>
  )
}

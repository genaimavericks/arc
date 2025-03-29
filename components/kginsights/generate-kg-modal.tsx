"use client"

import type React from "react"
import { useRouter } from "next/navigation"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useState } from "react"
import { useToast } from "@/components/ui/use-toast"
import { Loader2 } from "lucide-react"

interface GenerateKGModalProps {
  isOpen: boolean
  onClose: () => void
  datasetId: string
  datasetName: string
}

export function GenerateKGModal({ isOpen, onClose, datasetId, datasetName }: GenerateKGModalProps) {
  const [kgName, setKgName] = useState("")
  const [kgDescription, setKgDescription] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { toast } = useToast()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!kgName.trim()) {
      toast({
        title: "Error",
        description: "Knowledge Graph name is required",
        variant: "destructive",
      })
      return
    }

    try {
      setIsSubmitting(true)

      // Redirect to the Generate Graph page with the dataset ID and name
      router.push(`/kginsights/generate?sourceId=${datasetId}&sourceName=${encodeURIComponent(datasetName)}&kgName=${encodeURIComponent(kgName)}&kgDescription=${encodeURIComponent(kgDescription || '')}`)
      
      // Reset form and close modal
      setKgName("")
      setKgDescription("")
      onClose()
    } catch (error) {
      console.error("Error navigating to generate graph page:", error)
      toast({
        title: "Error",
        description: "Failed to navigate to generate graph page. Please try again.",
        variant: "destructive",
      })
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Generate Knowledge Graph</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="dataset">Source Dataset</Label>
            <Input id="dataset" value={datasetName} disabled />
          </div>

          <div className="space-y-2">
            <Label htmlFor="kg-name">Knowledge Graph Name</Label>
            <Input
              id="kg-name"
              value={kgName}
              onChange={(e) => setKgName(e.target.value)}
              placeholder="Enter a name for your knowledge graph"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="kg-description">Description (Optional)</Label>
            <Textarea
              id="kg-description"
              value={kgDescription}
              onChange={(e) => setKgDescription(e.target.value)}
              placeholder="Enter a description for your knowledge graph"
              rows={3}
            />
          </div>

          <DialogFooter className="pt-4">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                "Generate Knowledge Graph"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

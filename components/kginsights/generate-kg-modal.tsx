"use client"

import type React from "react"

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

      // Call the API to generate a knowledge graph
      const response = await fetch("/api/kginsights/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          dataset_id: datasetId,
          name: kgName,
          description: kgDescription,
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to generate knowledge graph: ${response.status}`)
      }

      const data = await response.json()

      toast({
        title: "Success",
        description: `Knowledge Graph "${kgName}" is being generated. Job ID: ${data.job_id}`,
      })

      // Reset form and close modal
      setKgName("")
      setKgDescription("")
      onClose()
    } catch (error) {
      console.error("Error generating knowledge graph:", error)
      toast({
        title: "Error",
        description: "Failed to generate knowledge graph. Please try again.",
        variant: "destructive",
      })
    } finally {
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


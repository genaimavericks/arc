"use client"

import Navbar from "@/components/navbar"
import { SparklesCore } from "@/components/sparkles"
import KGInsightsSidebar from "@/components/kginsights-sidebar"
import { Button } from "@/components/ui/button"
import { Settings, Plus, Trash, Edit } from "lucide-react"
import { motion } from "framer-motion"
import { KGInsightsLayout } from "@/components/kginsights/kginsights-layout"

export default function ManageKGraphPage() {
  return (
    <KGInsightsLayout requiredPermission="kginsights:manage">
      <ManageKGraphContent />
    </KGInsightsLayout>
  )
}

function ManageKGraphContent() {
  // Animation variants
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  }

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  }

  return (
    <div className="flex-1 p-8">
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="max-w-4xl mx-auto"
      >
        <motion.h1
          variants={item}
          className="text-4xl font-bold mb-6"
        >
          Manage Knowledge Graphs
        </motion.h1>

        <motion.div variants={item} className="mb-8">
          <p className="text-muted-foreground max-w-2xl mb-4">
            Create, edit and delete your knowledge graphs. You can also view schema details and manage permissions.
          </p>
          <Button className="flex items-center gap-2">
            <Plus size={16} />
            Create New KGraph
          </Button>
        </motion.div>

        <motion.div variants={item}>
          <h2 className="text-2xl font-semibold mb-4">Your Knowledge Graphs</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Example Card 1 */}
            <div className="border rounded-lg p-4 shadow-sm bg-card">
              <div className="flex justify-between mb-2">
                <h3 className="font-medium">Customer Relations</h3>
                <div className="flex gap-2">
                  <Button variant="ghost" size="icon" title="Edit">
                    <Edit size={16} />
                  </Button>
                  <Button variant="ghost" size="icon" className="text-destructive" title="Delete">
                    <Trash size={16} />
                  </Button>
                </div>
              </div>
              <p className="text-sm text-muted-foreground mb-4">Customer relationship knowledge graph with product connections.</p>
              <div className="text-xs text-muted-foreground">Created: 2025-01-15</div>
            </div>

            {/* Example Card 2 */}
            <div className="border rounded-lg p-4 shadow-sm bg-card">
              <div className="flex justify-between mb-2">
                <h3 className="font-medium">Supply Chain</h3>
                <div className="flex gap-2">
                  <Button variant="ghost" size="icon" title="Edit">
                    <Edit size={16} />
                  </Button>
                  <Button variant="ghost" size="icon" className="text-destructive" title="Delete">
                    <Trash size={16} />
                  </Button>
                </div>
              </div>
              <p className="text-sm text-muted-foreground mb-4">Supply chain network graph showing vendor relationships.</p>
              <div className="text-xs text-muted-foreground">Created: 2025-02-20</div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}

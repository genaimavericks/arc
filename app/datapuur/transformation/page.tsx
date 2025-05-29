"use client"

import { DataPuurLayout } from "@/components/datapuur/datapuur-layout"
import { Button } from "@/components/ui/button"
import { motion } from "framer-motion"
import { Wand2, Plus } from "lucide-react"

export default function TransformationPage() {
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
    <DataPuurLayout>
      <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold tracking-tight">Data Transformation</h2>
          <p className="text-sm text-muted-foreground">Transform and clean your data for analysis</p>
        </div>
        
        <div className="space-y-4">

              <motion.div variants={container} initial="hidden" animate="show" className="space-y-8">
                <motion.div
                  variants={item}
                  className="bg-card/80 backdrop-blur-sm p-6 rounded-lg border border-border mb-8 shadow-md hover:shadow-lg transition-shadow duration-300"
                >
                  <h3 className="text-xl font-semibold text-foreground mb-4 flex items-center">
                    <Wand2 className="w-6 h-6 text-primary mr-2" />
                    Transformation Pipelines
                  </h3>
                  <div className="space-y-4">
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      className="p-4 border border-border rounded-lg flex justify-between items-center bg-gradient-to-r from-primary/5 to-secondary/5"
                    >
                      <div>
                        <h4 className="text-foreground font-medium">Customer Data Pipeline</h4>
                        <p className="text-muted-foreground text-sm">Last run: 2 hours ago</p>
                      </div>
                      <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">Run</Button>
                    </motion.div>

                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      className="p-4 border border-border rounded-lg flex justify-between items-center bg-gradient-to-r from-secondary/5 to-primary/5"
                    >
                      <div>
                        <h4 className="text-foreground font-medium">Product Data Pipeline</h4>
                        <p className="text-muted-foreground text-sm">Last run: 1 day ago</p>
                      </div>
                      <Button className="bg-secondary hover:bg-secondary/90 text-secondary-foreground">Run</Button>
                    </motion.div>
                  </div>
                </motion.div>

                <motion.div
                  variants={item}
                  className="bg-card/80 backdrop-blur-sm p-6 rounded-lg border border-border shadow-md hover:shadow-lg transition-shadow duration-300"
                >
                  <h3 className="text-xl font-semibold text-foreground mb-4">Create New Transformation</h3>
                  <p className="text-muted-foreground mb-4">Design a new data transformation pipeline</p>
                  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
                    <Button
                      variant="outline"
                      className="border-primary text-primary hover:bg-primary/10 flex items-center"
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Create Pipeline
                    </Button>
                  </motion.div>
                </motion.div>
              </motion.div>
            </div>
      </div>
    </DataPuurLayout>
  )
}


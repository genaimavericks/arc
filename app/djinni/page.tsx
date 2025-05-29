"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"
import { MessageSquare, Database, BarChart2, Zap, ArrowRight, Brain, Bot, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DjinniLayout } from "@/components/djinni/djinni-layout"

export default function DjinniPage() {
  const [question, setQuestion] = useState("")
  const [searchQuery, setSearchQuery] = useState("")
  
  // Sample recent conversations
  const recentConversations = [
    {
      title: "Get Sales Analysis",
      description: "Analyzed sales performance for Q1 2023",
      date: "2 hours ago"
    },
    {
      title: "Inventory Prediction",
      description: "Generated inventory forecast based on recent sales",
      date: "Yesterday"
    },
    {
      title: "Customer Segmentation",
      description: "Created customer segments based on purchase patterns",
      date: "3 days ago"
    }
  ]
  
  // Sample questions
  const sampleQuestions = [
    "What are our conversion rates by sales channel?",
    "Which items are most likely to stock out this quarter?",
    "How have sales patterns changed in 2023?",
    "What's our average deal close time?"
  ]
  
  // Animation variants
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }
  
  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  }
  
  return (
    <DjinniLayout>
      <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
        {/* Header */}
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-primary" />
            <h2 className="text-2xl font-bold tracking-tight">Djinni Assistant</h2>
          </div>
          <p className="text-sm text-muted-foreground mt-1">Your AI-powered virtual assistant for sales insights and automation</p>
        </div>
        
        {/* Search bar */}
        <div className="flex w-full items-center space-x-2 pb-4">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input 
            type="search" 
            placeholder="Search conversations..." 
            className="max-w-sm" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        
        {/* What can I help with section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-primary" />
              What Can I Help You With
            </CardTitle>
            <CardDescription>Choose an option below or type your question in the search bar</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <motion.div
                variants={item}
                whileHover={{ scale: 1.02 }}
                className="bg-card border border-border rounded-lg p-4 hover:border-primary/50 transition-colors"
              >
                <div className="flex gap-4">
                  <div className="bg-primary/10 p-2 rounded-md h-fit">
                    <Database className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium mb-1">Create Dashboard</h3>
                    <p className="text-sm text-muted-foreground">Build custom dashboards with AI-generated insights</p>
                  </div>
                </div>
              </motion.div>
              
              <motion.div
                variants={item}
                whileHover={{ scale: 1.02 }}
                className="bg-card border border-border rounded-lg p-4 hover:border-primary/50 transition-colors"
              >
                <div className="flex gap-4">
                  <div className="bg-primary/10 p-2 rounded-md h-fit">
                    <Brain className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium mb-1">Build Knowledge Graph</h3>
                    <p className="text-sm text-muted-foreground">Explore data relationships and connections</p>
                  </div>
                </div>
              </motion.div>
              
              <motion.div
                variants={item}
                whileHover={{ scale: 1.02 }}
                className="bg-card border border-border rounded-lg p-4 hover:border-primary/50 transition-colors"
              >
                <div className="flex gap-4">
                  <div className="bg-primary/10 p-2 rounded-md h-fit">
                    <BarChart2 className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium mb-1">Analyze Data Quality</h3>
                    <p className="text-sm text-muted-foreground">Check and improve your data quality</p>
                  </div>
                </div>
              </motion.div>
              
              <motion.div
                variants={item}
                whileHover={{ scale: 1.02 }}
                className="bg-card border border-border rounded-lg p-4 hover:border-primary/50 transition-colors"
              >
                <div className="flex gap-4">
                  <div className="bg-primary/10 p-2 rounded-md h-fit">
                    <Zap className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium mb-1">Get Insights</h3>
                    <p className="text-sm text-muted-foreground">AI-generated insights about your business data</p>
                  </div>
                </div>
              </motion.div>
            </div>
          </CardContent>
        </Card>
        
        {/* Ask me about section */}
        <Card>
          <CardHeader>
            <CardTitle>Ask Me About Your Sales Data</CardTitle>
            <CardDescription>Type your question or select from examples below</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2 mb-6">
              <Input 
                placeholder="Ask anything about your data..." 
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="flex-1"
              />
              <Button>
                Ask
              </Button>
            </div>
            
            <div className="space-y-2">
              {sampleQuestions.map((q, i) => (
                <div 
                  key={i} 
                  className="flex items-center gap-2 p-2 hover:bg-accent rounded-md cursor-pointer"
                  onClick={() => setQuestion(q)}
                >
                  <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center rounded-full bg-primary/10 text-primary text-xs">
                    Q
                  </div>
                  <p className="text-sm">{q}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        
        {/* How to work with Djinni */}
        <Card>
          <CardHeader>
            <CardTitle>How to Work with Djinni</CardTitle>
            <CardDescription>Tips for getting the most out of your AI assistant</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex flex-col items-center text-center p-4">
                <div className="bg-primary/10 p-3 rounded-full mb-3">
                  <MessageSquare className="h-5 w-5 text-primary" />
                </div>
                <h3 className="font-medium mb-1">Natural Conversation</h3>
                <p className="text-sm text-muted-foreground">Ask questions in plain English, just like you'd ask a colleague.</p>
              </div>
              
              <div className="flex flex-col items-center text-center p-4">
                <div className="bg-primary/10 p-3 rounded-full mb-3">
                  <Database className="h-5 w-5 text-primary" />
                </div>
                <h3 className="font-medium mb-1">Guided Interaction</h3>
                <p className="text-sm text-muted-foreground">Use clear, specific prompts for more focused results.</p>
              </div>
              
              <div className="flex flex-col items-center text-center p-4">
                <div className="bg-primary/10 p-3 rounded-full mb-3">
                  <Zap className="h-5 w-5 text-primary" />
                </div>
                <h3 className="font-medium mb-1">Command Mode</h3>
                <p className="text-sm text-muted-foreground">Improve your productivity with direct commands.</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        {/* Ready to get started */}
        <div className="text-center py-6">
          <h2 className="text-xl font-semibold mb-2">Ready to get started?</h2>
          <p className="text-muted-foreground mb-4">Use the assistant panel on the right to ask your first question, or select one of the options above.</p>
          <Button className="gap-2">
            Start working with Djinni
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </DjinniLayout>
  )
}

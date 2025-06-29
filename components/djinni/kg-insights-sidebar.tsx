"use client"

import { useState, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Settings, History, Database, Trash2 } from "lucide-react"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { ChevronRight } from "lucide-react"
import { PredefinedQuery, HistoryItem } from "./unified-chat"

import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "@/components/ui/select"

interface KGInsightsSidebarProps {
  predefinedQueries: PredefinedQuery[];
  historyItems: HistoryItem[];
  loadingHistory: boolean;
  onPredefinedQuery: (query: string) => void;
  loadHistoryItem: (item: HistoryItem) => void;
  deleteHistoryItem?: (id: string) => void
  deleteAllHistory?: () => void
  onClose?: () => void
  availableSources: string[]
  sourceId: string | null
  setSourceId: (id: string) => void
}

export function KGInsightsSidebar({
  predefinedQueries,
  historyItems,
  loadingHistory,
  onPredefinedQuery,
  loadHistoryItem,
  deleteHistoryItem,
  deleteAllHistory,
  onClose,
  availableSources,
  sourceId,
  setSourceId
}: KGInsightsSidebarProps) {
  const [activeTab, setActiveTab] = useState("queries")

  const groupedQueries = Array.isArray(predefinedQueries) ? predefinedQueries.reduce((acc, query) => {
    const category = query.category || 'general'
    if (!acc[category]) {
      acc[category] = []
    }
    acc[category].push(query)
    return acc
  }, {} as Record<string, PredefinedQuery[]>) : {}

  const groupedHistoryItems = useMemo(() => {
    if (!historyItems || !Array.isArray(historyItems)) return {};
    
    const groups: { [key: string]: HistoryItem[] } = {
      Today: [],
      Yesterday: [],
      'Last 7 Days': [],
      Older: [],
    };

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    historyItems.forEach((item) => {
      const itemDate = new Date(item.timestamp);
      itemDate.setHours(0, 0, 0, 0);

      if (itemDate.getTime() === today.getTime()) {
        groups.Today.push(item);
      } else if (itemDate.getTime() === yesterday.getTime()) {
        groups.Yesterday.push(item);
      } else if (itemDate > sevenDaysAgo) {
        groups['Last 7 Days'].push(item);
      } else {
        groups.Older.push(item);
      }
    });

    for (const key in groups) {
      if (groups[key].length === 0) {
        delete groups[key];
      }
    }

    return groups;
  }, [historyItems]);

  const getHistoryResultText = (result: string) => {
    try {
      const parsed = JSON.parse(result);
      return parsed.text || "No text result available.";
    } catch (e) {
      return result;
    }
  };

  return (
    <div className="flex flex-col h-full border-l bg-card/50 backdrop-blur-sm">
      <div className="p-2">
        <Tabs defaultValue="queries" value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid grid-cols-3 w-full">
            <TabsTrigger value="queries" className="flex items-center gap-1">
              <Database className="h-4 w-4" />
              <span>Queries</span>
            </TabsTrigger>
            <TabsTrigger value="history" className="flex items-center gap-1">
              <History className="h-4 w-4" />
              <span>History</span>
            </TabsTrigger>
            <TabsTrigger value="settings" className="flex items-center gap-1">
              <Settings className="h-4 w-4" />
              <span>Settings</span>
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="queries" className="mt-0 flex-1">
            <ScrollArea className="h-full">
              <div className="p-4 space-y-4">
                {Object.entries(groupedQueries).map(([category, queries]) => (
                  <div key={category}>
                    <h3 className="text-sm font-semibold mb-2 capitalize text-muted-foreground">{category.replace(/_/g, ' ')} Queries</h3>
                    <div className="space-y-2">
                      {queries.map((item) => (
                        <button
                          key={item.id}
                          className="w-full text-left p-2 rounded-md hover:bg-muted cursor-pointer text-sm flex items-start space-x-2"
                          onClick={() => onPredefinedQuery(item.query)}
                        >
                          <ChevronRight className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
                          <span>{item.query}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
                {Object.keys(groupedQueries).length === 0 && (
                  <p className="text-sm text-muted-foreground text-center p-4">No predefined queries available.</p>
                )}
              </div>
            </ScrollArea>
          </TabsContent>
          
          <TabsContent value="history" className="mt-0 flex-1">
            <ScrollArea className="h-full">
              <div className="p-4">
                {historyItems && historyItems.length > 0 ? (
                  <>
                    {deleteAllHistory && (
                      <div className="flex justify-end mb-2">
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="outline" size="sm" className="text-xs">
                              <Trash2 className="h-3 w-3 mr-1" />
                              Clear History
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                              <AlertDialogDescription>
                                This action cannot be undone. This will permanently delete all query history for this data source.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction onClick={deleteAllHistory}>Delete</AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    )}
                    <div className="space-y-4">
                      {Object.entries(groupedHistoryItems).map(([groupName, items]) => {
                        if (items.length === 0) return null;
                        return (
                          <div key={groupName}>
                            <h4 className="text-sm font-medium text-muted-foreground mb-2 px-2">{groupName}</h4>
                            <Accordion type="multiple" className="w-full space-y-1">
                              {items.map((item) => (
                                <AccordionItem key={item.id} value={item.id} className="border-b-0 bg-background rounded-md">
                                  <div className="flex items-center group w-full hover:bg-muted/50 rounded-md transition-colors">
                                    <AccordionTrigger className="flex-1 text-sm p-2 text-left font-normal break-words hover:no-underline">
                                      {item.query}
                                    </AccordionTrigger>
                                    {deleteHistoryItem && (
                                      <AlertDialog>
                                        <AlertDialogTrigger asChild>
                                          <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8 shrink-0 opacity-0 group-hover:opacity-100 mr-2"
                                            onClick={(e) => e.stopPropagation()}
                                          >
                                            <Trash2 className="h-4 w-4" />
                                          </Button>
                                        </AlertDialogTrigger>
                                        <AlertDialogContent>
                                          <AlertDialogHeader>
                                            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                                            <AlertDialogDescription>
                                              This will permanently delete this history item.
                                            </AlertDialogDescription>
                                          </AlertDialogHeader>
                                          <AlertDialogFooter>
                                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                                            <AlertDialogAction onClick={() => deleteHistoryItem(item.id)}>
                                              Delete
                                            </AlertDialogAction>
                                          </AlertDialogFooter>
                                        </AlertDialogContent>
                                      </AlertDialog>
                                    )}
                                  </div>
                                  <AccordionContent className="p-2 pl-8 pr-2 text-sm">
                                    <div className="mt-1 mb-2 pt-2 min-w-0 border-t border-muted/50">
                                      <p className="whitespace-pre-wrap break-words text-muted-foreground text-xs">{getHistoryResultText(item.result)}</p>
                                      <Button
                                        variant="link"
                                        className="p-0 h-auto mt-2 text-xs"
                                        onClick={() => loadHistoryItem(item)}
                                      >
                                        Load this query in chat
                                      </Button>
                                    </div>
                                  </AccordionContent>
                                </AccordionItem>
                              ))}
                            </Accordion>
                          </div>
                        );
                      })}
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground text-center p-4">No history yet.</p>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="settings" className="mt-0 flex-1">
            <ScrollArea className="h-full">
              <div className="p-4 space-y-4">
                <div>
                  <h3 className="font-medium text-sm mb-2">Knowledge Graph Source</h3>
                  <Select value={sourceId ?? ''} onValueChange={setSourceId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a source" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableSources.map(source => (
                        <SelectItem key={source} value={source}>{source}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>
      
      {onClose && (
        <div className="mt-auto p-2 border-t">
          <Button 
            variant="ghost" 
            size="sm" 
            className="w-full justify-center" 
            onClick={onClose}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  )
}

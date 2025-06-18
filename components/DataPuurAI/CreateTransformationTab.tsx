"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import * as z from "zod"
import { ArrowLeft, ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Loader2, MessageCircle, Send } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { TransformationChat } from '@/components/DataPuurAI/TransformationChat'
import { useRouter } from 'next/navigation'

// Form schema for transformation plan details
const transformationFormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional()
})

interface CreateTransformationTabProps {
  initialPlanId?: string;
  dataSourceId?: string;
  dataSourceName?: string;
}

export function CreateTransformationTab({ initialPlanId, dataSourceId, dataSourceName }: CreateTransformationTabProps) {
  const router = useRouter()
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [processingStage, setProcessingStage] = useState<string>("")
  const [dataSource, setDataSource] = useState<any>(null)
  const [instructions, setInstructions] = useState<string>("")
  const [finalInstructions, setFinalInstructions] = useState<string>("")
  const [planId, setPlanId] = useState<string | undefined>(initialPlanId)
  // State for collapsible details card
  const [isDetailsExpanded, setIsDetailsExpanded] = useState(true)
  
  // Initialize form with React Hook Form
  const form = useForm<z.infer<typeof transformationFormSchema>>({
    resolver: zodResolver(transformationFormSchema),
    defaultValues: {
      name: dataSourceName ? `${dataSourceName} - Transformation` : "",
      description: "AI-powered data transformation plan"
    }
  })

  // Check for plan ID in localStorage if not provided as prop
  useEffect(() => {
    const storedPlanId = localStorage.getItem('current_transformation_id');
    
    if (!initialPlanId && storedPlanId) {
      console.log(`Loading plan from localStorage: ${storedPlanId}`);
      setPlanId(storedPlanId);
      
      // Fetch plan details from the API
      fetchPlanDetails(storedPlanId);
    }
  }, [initialPlanId]);
  
  // Fetch data source details if provided
  useEffect(() => {
    if (dataSourceId) {
      fetchDataSourceDetails(dataSourceId)
    }
  }, [dataSourceId])

  // Fetch transformation plan details from API
  const fetchPlanDetails = async (id: string) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Authentication token not found');
      }
      
      const response = await fetch(`/api/datapuur-ai/transformations/${id}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch plan details: ${response.status}`);
      }
      
      const planData = await response.json();
      
      // Update form with plan data
      form.reset({
        name: planData.name || '',
        description: planData.description || ''
      });
      
      // If the plan has a source_id, fetch that source's details
      if (planData.source_id) {
        fetchDataSourceDetails(planData.source_id);
      }
      
      // If there are instructions, set them
      if (planData.input_instructions) {
        setFinalInstructions(planData.input_instructions);
      }
      
      console.log('Loaded plan details:', planData);
    } catch (error) {
      console.error('Error fetching plan details:', error);
      toast({
        title: "Error",
        description: "Failed to load transformation plan details.",
        variant: "destructive"
      });
    }
  };
  
  // Fetch data source details from API
  const fetchDataSourceDetails = async (id: string) => {
    try {
      const token = localStorage.getItem('token')
      // Use the sources list endpoint with a filter instead of trying to fetch a specific source
      const response = await fetch(`/api/datapuur/sources?id=${id}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        // The endpoint returns an array of sources, find the one with matching ID
        const sourceData = Array.isArray(data) && data.length > 0 ? 
          data.find((source: any) => source.id === id) : null
          
        if (sourceData) {
          setDataSource({
            id: id,
            ...sourceData
          })
        } else {
          // Fallback if source not found in the response
          setDataSource({
            id: id,
            name: dataSourceName || 'Transformation'
          })
        }
      } else {
        console.error('Failed to fetch data source details')
        // Use the ID as fallback if we can't get details
        setDataSource({
          id: id,
          name: dataSourceName || 'Transformation'
        })
      }
    } catch (error) {
      console.error('Error fetching data source:', error)
      // Use the ID as fallback if we can't get details
      setDataSource({
        id: id,
        name: dataSourceName || 'Transformation'
      })
    }
  }

  // Handle form submission
  const onSubmit = async (values: z.infer<typeof transformationFormSchema>) => {
    try {
      setIsSubmitting(true)
      setProcessingStage("Initializing...")
      console.log("[Transform] Starting plan creation process")
      
      // Create a new transformation plan with AI assistance
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('Authentication token not found')
      }
      
      setProcessingStage("Sending request to server...")
      console.log("[Transform] Sending transformation plan request to backend")
      console.log(`[Transform] Plan name: ${values.name}, Draft mode: ${planId ? false : true}`)
      console.log(`[Transform] Profile session ID: ${dataSource?.id || 'None'}`)
      
      // Construct request payload in the expected format
      const payload: {
        name: string;
        description: string;
        is_draft: boolean;
        profile_session_id?: string;
        input_instructions: string;
        id?: string;
      } = {
        name: values.name,
        description: values.description || "",
        is_draft: !planId, // true if no planId exists (new plan), false if editing
        profile_session_id: dataSource?.id,
        input_instructions: finalInstructions || ""
      };
      
      // Add ID only if it exists to maintain backward compatibility
      if (planId) {
        payload.id = planId;
      }
      
      console.log("[Transform] API request payload:", payload);
      
      console.log("[Transform] Initiating fetch to /api/datapuur-ai/transformations");
      const response = await fetch('/api/datapuur-ai/transformations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      
      console.log("[Transform] API response status:", response.status);
      if (response.headers) {
        console.log("[Transform] API response headers:", Object.fromEntries([...response.headers.entries()]));
      }
      
      if (!response.ok) {
        console.error("[Transform] API request failed with status:", response.status);
        const errorText = await response.text();
        console.error("[Transform] Error response:", errorText);
        throw new Error(`API request failed: ${response.status} ${errorText}`);
      }
      
      setProcessingStage("Processing response...");
      console.log("[Transform] Server response received, processing result");
      
      const data = await response.json()
      console.log(`[Transform] Full API response data:`, data)
      
      if (!data.id) {
        console.error("[Transform] Error: No plan ID in response")
        throw new Error("No plan ID returned from API")
      }
      
      setPlanId(data.id)
      
      console.log(`[Transform] Plan created successfully with ID: ${data.id}`)
      setProcessingStage("Plan created, redirecting...")
      
      toast({
        title: "Success",
        description: "Opening transformation workspace...",
      })
      
      // Store the transformation plan ID in localStorage for access in other components
      try {
        // Double check that the ID is a valid string
        if (typeof data.id !== 'string' || !data.id.trim()) {
          console.error("[Transform] Invalid plan ID detected", data.id)
          throw new Error("Invalid plan ID")
        }
        
        console.log(`[Transform] Storing plan ID in localStorage: ${data.id}`)
        localStorage.setItem('current_transformation_id', data.id)
        
        // Verify localStorage was set correctly
        const storedId = localStorage.getItem('current_transformation_id')
        console.log(`[Transform] Verified localStorage plan ID: ${storedId}`)
        
        if (storedId !== data.id) {
          console.error("[Transform] LocalStorage ID doesn't match!", {expected: data.id, actual: storedId})
        }
      } catch (e) {
        console.error("[Transform] Error storing plan ID in localStorage:", e)
      }
      
      console.log(`[Transform] Navigating to transformation workspace`)
      console.log(`[Transform] Router path: /datapuur/ai-transformation/dynamic`)
      
      // Navigate to the transformation workspace page after creating plan
      router.push('/datapuur/ai-transformation/dynamic')
    } catch (error: any) {
      console.error("[Transform] Error creating transformation plan:", error)
      
      toast({
        title: "Error",
        description: error.message || "Failed to create transformation plan",
        variant: "destructive"
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  // When chat sends instructions, save them for form submission
  const handleInstructionsUpdate = (instructions: string) => {
    setFinalInstructions(instructions)
  }
  
  return (
    <div className="flex flex-col gap-4 w-full">
      {/* Top header with title and Execute Plan button */}
      <div className="flex flex-row justify-between items-center mb-2">
        <h2 className="text-2xl font-bold">Create Transformation Plan</h2>
        <Button
          type="button"
          variant="default"
          size="lg"
          className="shadow-md px-6 py-2 font-bold flex items-center gap-2"
          disabled={isSubmitting}
          onClick={async e => {
            e.preventDefault();
            
            if (!planId) {
              toast({
                title: "Error",
                description: "Please save the plan first before executing",
                variant: "destructive"
              });
              return;
            }
              
              setIsSubmitting(true);
              setProcessingStage("Executing...");
              
              try {
                const token = localStorage.getItem('token');
                if (!token) {
                  throw new Error('Authentication token not found');
                }
                
                // Use the GET endpoint to fetch the complete plan
                const response = await fetch(`/api/datapuur-ai/transformations/${planId}`, {
                  method: 'GET',
                  headers: {
                    'Authorization': `Bearer ${token}`
                  }
                });
                
                if (!response.ok) {
                  const errorText = await response.text();
                  throw new Error(`API request failed: ${response.status} ${errorText}`);
                }
                
                const data = await response.json();
                console.log(`[Transform] Plan retrieved successfully with ID: ${data.id}`);
                
                // Store the transformation plan ID in localStorage
                localStorage.setItem('current_transformation_id', data.id);
                
                // Navigate to the transformation workspace page
                router.push('/datapuur/ai-transformation/dynamic');
                
                toast({
                  title: "Success",
                  description: "Opening transformation workspace...",
                });
              } catch (error: any) {
                toast({
                  title: "Error",
                  description: error.message || "Failed to execute transformation plan",
                  variant: "destructive"
                });
              } finally {
                setIsSubmitting(false);
                setProcessingStage("");
              }
            }}
          >
            {isSubmitting && processingStage !== "Updating..." ? (
              <><Loader2 className="mr-2 h-5 w-5 animate-spin" />Executing...</>
            ) : (
              <><Send className="mr-2 h-5 w-5" />Execute Plan</>
            )}
          </Button>
      </div>
      <div className="flex flex-col md:flex-row gap-4 w-full">
      {/* Left: Plan details form (collapsible) */}
      <div className={`transition-all duration-300 ${isDetailsExpanded ? 'md:w-[420px] w-full' : 'md:w-[56px] w-full'} flex-shrink-0`}> 
        <Card className="h-full">
          <CardHeader 
            className="cursor-pointer flex flex-row items-center"
            onClick={() => setIsDetailsExpanded(!isDetailsExpanded)}
          >
            <Button variant="ghost" size="icon" className="mr-2" onClick={e => { e.stopPropagation(); setIsDetailsExpanded(!isDetailsExpanded); }}>
              {isDetailsExpanded ? <ChevronLeft /> : <ChevronRight />}
            </Button>
            <div className={isDetailsExpanded ? '' : 'sr-only'}>
              <CardTitle>Transformation Plan Details</CardTitle>
              <CardDescription>
                {isDetailsExpanded 
                  ? "Create a new AI-powered data transformation plan" 
                  : planId 
                    ? "Plan created! Click to expand and edit details" 
                    : "Click to expand and enter plan details"}
              </CardDescription>
            </div>
          </CardHeader>
          {isDetailsExpanded && (
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Enter a name for your transformation plan" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Textarea placeholder="Enter a description for this transformation plan" className="min-h-[80px]" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="flex flex-col gap-2 pt-2">
  {/* Update Plan button (PUT) - only if planId exists */}
  {planId && (
    <Button
      type="button"
      variant="default"
      className="w-full h-10 text-base font-semibold"
      disabled={isSubmitting}
      onClick={async e => {
        e.preventDefault();
        const formValues = form.getValues();
        if (!formValues.name) {
          form.setError("name", { message: "Name is required" });
          return;
        }
        setIsSubmitting(true);
        setProcessingStage("Updating...");
        try {
          const token = localStorage.getItem('token');
          if (!token) {
            throw new Error('Authentication token not found');
          }
          const response = await fetch(`/api/datapuur-ai/transformations/${planId}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              name: formValues.name,
              description: formValues.description
            })
          });
          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API request failed: ${response.status} ${errorText}`);
          }
          toast({
            title: "Plan updated!",
            description: "Transformation plan details have been saved.",
            variant: "default"
          });
        } catch (error: any) {
          toast({
            title: "Error",
            description: error.message || "Failed to update transformation plan",
            variant: "destructive"
          });
        } finally {
          setIsSubmitting(false);
          setProcessingStage("");
        }
      }}
    >
      {isSubmitting && processingStage === "Updating..." ? (
        <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Updating...</>
      ) : (
        <>Update Plan</>
      )}
    </Button>
  )}

</div>
                </form>
              </Form>
            </CardContent>
          )}
        </Card>
      </div>
      {/* Right: AI Assistant chat */}
      <div className="flex-1 min-w-0">
        <Card className="h-full">
          <CardHeader>
            <CardTitle>AI Assistant</CardTitle>
            <CardDescription>
              Chat with the AI to refine your transformation plan
            </CardDescription>
          </CardHeader>
          <CardContent className="min-h-[350px]">
            <TransformationChat
              planId={planId}
              profileSessionId={dataSource?.id}
              onInstructionsUpdate={handleInstructionsUpdate}
              initialInstructions={finalInstructions}
              sourceId={dataSource?.id}
            />
          </CardContent>
        </Card>
      </div>
    </div>
    </div>
  )
}

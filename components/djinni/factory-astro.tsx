import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Loader2, AlertCircle, Bot, BarChart } from 'lucide-react';
import { getApiBaseUrl } from '@/lib/config';
import { useDjinniStore } from '@/lib/djinni/store';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert"

export function FactoryAstro() {
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<any>(null);
  const [error, setError] = useState('');
  
  // Use the Djinni store for persistent state
  const { chatHistory: storeChatHistory, sessionMessages, addMessage, activeModel, isNewSession, startNewSession } = useDjinniStore();
  
  // Default example questions in case API fails
  const defaultExamples = [
    "What will the revenue for factory 3 be over the next 6 months?",
    "What will the revenue over the next year for factory 3?",
    "What will the profit margin be from July to December for factory 2?",
    "What will the profit margin of factory 1 over the next quarter?",
    "What will the production volume be over the next 6 months?",
    "Get me the production volume for factory 4 from July to December.",
    "What will the revenue for factory 3 be next year?",
    "What will the revenue over the next 2 months for factory 3?",
    "What will the profit margin be in July for factory 2?",
    "What will the profit margin of factory 1?",
    "What will the production volume be over the next 2 months?",
    "Get me the production volume for factory 4 in the month of July."
  ];
  
  const [exampleQuestions, setExampleQuestions] = useState<string[]>(defaultExamples);

  useEffect(() => {
    // Fetch example questions on component mount
    const fetchExamples = async () => {
      try {
        // Get token from localStorage
        const token = localStorage.getItem('token') || '';
        const apiBaseUrl = getApiBaseUrl();
        
        const response = await fetch(`${apiBaseUrl}/api/factory-astro/examples`, {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          // Use API examples if available, otherwise keep the default examples
          if (data.examples && data.examples.length > 0) {
            setExampleQuestions(data.examples);
          }
        } else if (response.status === 401) {
          // Handle authentication error
          console.error('Authentication error: Please log in');
          // Redirect to login if needed
          window.location.href = '/login';
        }
      } catch (err) {
        console.error('Error fetching examples:', err);
      }
    };

    fetchExamples();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    // Add user message to chat history immediately for better UX
    const userMessage = question.trim();
    addMessage('factory_astro', 'user', userMessage);
    
    setIsLoading(true);
    setError('');
    setResponse(null);
    
    try {
      // Get token from localStorage
      const token = localStorage.getItem('token') || '';
      const apiBaseUrl = getApiBaseUrl();
      
      console.log('Sending question to API:', userMessage);
      const response = await fetch(`${apiBaseUrl}/api/factory-astro/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ question: userMessage }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Handle authentication error
          throw new Error('Authentication error: Please log in');
        } else {
          throw new Error(`Error: ${response.statusText}`);
        }
      }

      const data = await response.json();
      setResponse(data);
      
      // Add assistant response to chat history
      const assistantMessage = data.summary || 'I processed your request about factory performance.';
      addMessage('factory_astro', 'assistant', assistantMessage);
    } catch (err: any) {
      setError(err.message || 'Failed to get prediction. Please try again.');
      console.error(err);
      
      // Add error message to chat history
      addMessage('factory_astro', 'assistant', 
        `Sorry, I encountered an error: ${err.message || 'Something went wrong'}`
      );
      
      // Redirect to login if authentication error
      if (err.message?.includes('Authentication error')) {
        window.location.href = '/login';
      }
    } finally {
      setIsLoading(false);
      setQuestion('');
    }
  };

  const handleExampleClick = (example: string) => {
    setQuestion(example);
  };

  // Format data for chart if available
  const formatChartData = () => {
    if (!response?.data?.Predicted_data || !Array.isArray(response.data.Predicted_data)) {
      console.log('No valid prediction data found');
      return [];
    }
    
    console.log('Raw prediction data:', response.data.Predicted_data);
    
    // Check the structure of the first item to determine the format
    const firstItem = response.data.Predicted_data[0];
    
    // Handle different data structures that might come from the API
    if (firstItem && typeof firstItem === 'object') {
      // If the data is already in the expected format with Month/Date and Value properties
      if ((firstItem.Month || firstItem.Date) && (firstItem.Value !== undefined)) {
        return response.data.Predicted_data.map((item: any, index: number) => {
          // Extract date/month and ensure value is a number
          const dateLabel = item.Month || item.Date || `Month ${index + 1}`;
          const numericValue = typeof item.Value === 'string' ? parseFloat(item.Value) : 
                             (typeof item.Value === 'number' ? item.Value : 0);
          
          return {
            name: dateLabel,
            value: numericValue,
            // Keep original data for debugging
            original: item
          };
        });
      }
      // If the data is an array of values without explicit labels
      else if (Array.isArray(response.data.Predicted_data) && response.data.Predicted_data.every((item: any) => typeof item === 'number')) {
        return response.data.Predicted_data.map((value: number, index: number) => ({
          name: `Month ${index + 1}`,
          value: value
        }));
      }
    }
    
    // Fallback: create a simple data structure from whatever we have
    return response.data.Predicted_data.map((item: any, index: number) => {
      // Try to extract a meaningful value
      let value = 0;
      if (typeof item === 'number') {
        value = item;
      } else if (typeof item === 'object') {
        // Look for any property that might contain a numeric value
        const numericProps = Object.entries(item)
          .filter(([_, v]) => typeof v === 'number' || (typeof v === 'string' && !isNaN(parseFloat(v))))
          .map(([k, v]) => [k, typeof v === 'string' ? parseFloat(v) : v]);
        
        if (numericProps.length > 0) {
          // Use the first numeric property found
          value = numericProps[0][1] as number;
        }
      }
      
      return {
        name: `Month ${index + 1}`,
        value: value,
        // Keep original data for debugging
        original: item
      };
    });
  };
  
  // Debug chart data
  useEffect(() => {
    if (response?.data?.Predicted_data) {
      const formattedData = formatChartData();
      console.log('Formatted chart data:', formattedData);
    }
  }, [response]);
  
  // Debug response
  useEffect(() => {
    if (response) {
      console.log('Response received:', response);
    }
  }, [response]);

  // Start a new session when the component mounts
  useEffect(() => {
    startNewSession('factory_astro');
  }, [startNewSession]);
  
  // Get the session messages for the factory_astro model
  const modelSession = sessionMessages.find(chat => chat.model === 'factory_astro');
  const chatHistory = modelSession?.messages.map(msg => ({
    role: msg.role as 'user' | 'assistant',
    content: msg.content
  })) || [];

  return (
    <div className="flex flex-col h-full">
      {/* Chat history display */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4 max-h-[400px] pr-2">
        {chatHistory.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-4">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
              <BarChart className="h-8 w-8 text-primary" />
            </div>
            <div>
              <h3 className="font-medium text-lg">Factory Astro Assistant</h3>
              <p className="text-muted-foreground text-sm">Ask me about factory performance predictions and analytics.</p>
            </div>
          </div>
        ) : (
          chatHistory.map((message, index) => (
            <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div 
                className={`max-w-[80%] rounded-lg p-3 ${message.role === 'user' 
                  ? 'bg-primary text-primary-foreground' 
                  : 'bg-muted'}`}
              >
                <p className="text-sm">{message.content}</p>
              </div>
            </div>
          ))
        )}
        
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-lg p-3 bg-muted">
              <div className="flex items-center space-x-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <p className="text-sm">Processing...</p>
              </div>
            </div>
          </div>
        )}
        
        {/* Error message */}
        {error && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-lg p-3 bg-destructive/10 border border-destructive">
              <div className="flex items-start space-x-2">
                <AlertCircle className="h-4 w-4 text-destructive mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-destructive">Error</p>
                  <p className="text-sm text-muted-foreground">{error}</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Response visualization - only show when there's a response and no error */}
      {response && !error && (
        <Card className="mb-4 border-primary/20 bg-primary/5">
          <CardContent className="p-4">
            <div className="space-y-3">
              {/* Always show summary if available */}
              <div>
                <h3 className="text-sm font-medium mb-1">Analysis</h3>
                <p className="text-sm">{response.summary || 'No summary available'}</p>
              </div>
              
              {/* Show chart if prediction data is available */}
              {response.data?.Predicted_data && Array.isArray(response.data.Predicted_data) && response.data.Predicted_data.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium mb-2">Prediction Chart</h4>
                  <div className="h-64 w-full bg-card rounded-md p-2">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={formatChartData()}
                        margin={{
                          top: 5,
                          right: 30,
                          left: 20,
                          bottom: 5,
                        }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="name" 
                          tick={{ fill: '#888', fontSize: 12 }}
                          tickFormatter={(value) => value.toString().substring(0, 10)}
                        />
                        <YAxis 
                          tick={{ fill: '#888', fontSize: 12 }}
                          tickFormatter={(value) => value.toLocaleString()}
                        />
                        <Tooltip 
                          formatter={(value: number) => [value.toLocaleString(), 'Value']} 
                          labelFormatter={(label) => `Period: ${label}`}
                          contentStyle={{ backgroundColor: '#1a1b26', border: '1px solid #2c2d3a', borderRadius: '4px' }}
                          itemStyle={{ color: '#d0d0d0' }}
                          labelStyle={{ color: '#d0d0d0', fontWeight: 'bold' }}
                        />
                        <Legend wrapperStyle={{ paddingTop: '10px' }} />
                        <Line
                          type="monotone"
                          dataKey="value"
                          name="Prediction"
                          stroke="#8884d8"
                          strokeWidth={2}
                          dot={{ r: 4, fill: '#8884d8', strokeWidth: 1 }}
                          activeDot={{ r: 8, fill: '#8884d8', stroke: '#fff' }}
                          isAnimationActive={true}
                          animationDuration={1000}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
              
              {/* Show data details if available */}
              {response.data?.input_data && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium mb-2">Input Parameters</h4>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                    {Object.entries(response.data.input_data).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-muted-foreground">{key}:</span>
                        <span className="font-medium">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Input form */}
      <div className="mt-auto">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            placeholder="Ask about factory performance..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="flex-1"
            disabled={isLoading}
          />
          <Button type="submit" disabled={isLoading || !question.trim()}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Ask'}
          </Button>
        </form>
        
        {/* Example questions */}
        <div className="mt-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="h-5 w-5 rounded-full bg-primary/20 flex items-center justify-center">
              <span className="text-xs text-primary font-medium">?</span>
            </div>
            <h4 className="text-sm font-medium text-primary">Try asking</h4>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[180px] overflow-y-auto pr-1 pb-1">
            {exampleQuestions.map((q, i) => (
              <button
                key={i}
                className="text-xs px-4 py-2.5 bg-card border border-border hover:border-primary/30 hover:bg-primary/5 
                          transition-colors text-left rounded-md shadow-sm flex items-center gap-2 group"
                onClick={() => setQuestion(q)}
                disabled={isLoading}
                type="button"
              >
                <span className="text-muted-foreground group-hover:text-primary transition-colors">{i+1}.</span>
                <span className="line-clamp-2">{q}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

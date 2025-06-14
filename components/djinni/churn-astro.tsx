import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { getApiBaseUrl } from '@/lib/config';
import { Loader2, AlertCircle, Bot } from 'lucide-react';
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
import { Progress } from "@/components/ui/progress"
import { useDjinniStore } from '@/lib/djinni/store'

type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
};

type ChurnResponse = {
  status: string;
  summary: string;
  data?: {
    prediction?: string;
    probability?: number;
    input_data?: Record<string, any>;
    input_features?: Record<string, any>;
    feature_importance?: Array<{feature: string; importance: number}>;
  };
};

export function ChurnAstro() {
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<ChurnResponse | null>(null);
  const [error, setError] = useState('');
  
  // Use the Djinni store for persistent chat history and session management
  const { chatHistory: storeChatHistory, sessionMessages, addMessage, activeModel, isNewSession, startNewSession } = useDjinniStore();
  
  // Start a new session when the component mounts
  useEffect(() => {
    startNewSession('churn_astro');
  }, [startNewSession]);
  
  // Get the session messages for the churn_astro model
  const modelSession = sessionMessages.find(chat => chat.model === 'churn_astro');
  const chatHistory = modelSession?.messages.map(msg => ({
    role: msg.role as 'user' | 'assistant',
    content: msg.content
  })) || [];
  
  // Default example questions
  const defaultExamples = [
    "Will a customer with 12 months tenure, no online security, yes to online backup, no tech support, on a month-to-month contract, and paying $65.50 monthly likely churn?",
    "What's the churn probability for a customer who has been with us for 36 months, has online security, online backup, tech support, is on a two-year contract, and pays $105.80 monthly?",
    "Is a customer with 6 months tenure, no online security or backup, no tech support, month-to-month contract, and $70 monthly charges at risk of churning?",
    "Will a customer on a one-year contract with 18 months tenure, online security, no online backup, tech support, and $85 monthly charges stay with us?",
    "What's the likelihood of churn for a customer who's been with us for 24 months, has no internet service, and pays $45 monthly on a two-year contract?",
    "Predict if a customer will churn if they have no online security, no tech support, 9 months tenure, and $60 monthly charges on a month-to-month contract.",
    "Customer with 48 months tenure, all services enabled, two-year contract, and $120 monthly charges - will they churn?",
    "What's the churn risk for a new customer (3 months) with no services and a month-to-month contract paying $50 monthly?"
  ];
  
  const [exampleQuestions, setExampleQuestions] = useState<string[]>(defaultExamples);

  useEffect(() => {
    // Fetch example questions on component mount
    const fetchExamples = async () => {
      try {
        // Get token from localStorage
        const token = localStorage.getItem('token') || '';
        const apiBaseUrl = getApiBaseUrl();
        
        const response = await fetch(`${apiBaseUrl}/api/churn-astro/examples`, {
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
      } catch (error) {
        console.error('Error fetching example questions:', error);
        // Keep default examples on error
      }
    };
    
    fetchExamples();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    // Add user message to chat history immediately for better UX
    const userMessage = question.trim();
    addMessage('churn_astro', 'user', userMessage);
    
    setIsLoading(true);
    setError('');
    setResponse(null);

    try {
      // Get token from localStorage
      const token = localStorage.getItem('token') || '';
      const apiBaseUrl = getApiBaseUrl();
      
      const response = await fetch(`${apiBaseUrl}/api/churn-astro/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ question: userMessage })
      });

      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }

      const data = await response.json();
      setResponse(data);
      
      // Generate a humanized response based on the prediction data
      const assistantMessage = generateHumanizedResponse(data);
      addMessage('churn_astro', 'assistant', assistantMessage);
    } catch (err: any) {
      setError(err.message || 'An error occurred while processing your request');
      // Add error message to chat history
      addMessage('churn_astro', 'assistant', 
        `Sorry, I encountered an error: ${err.message || 'Something went wrong'}`
      );
    } finally {
      setIsLoading(false);
      setQuestion('');
    }
  };

  const handleExampleClick = (example: string) => {
    setQuestion(example);
  };
  
  // Format the churn probability as a percentage
  const formatProbability = (probability: number) => {
    return `${(probability * 100).toFixed(1)}%`;
  };
  
  // Determine risk level based on probability
  const getRiskLevel = (probability: number) => {
    if (probability > 0.7) return { level: 'High', color: 'text-red-500' };
    if (probability > 0.5) return { level: 'Moderate', color: 'text-amber-500' };
    return { level: 'Low', color: 'text-green-500' };
  };

  // Generate a humanized response based on the prediction data
  const generateHumanizedResponse = (data: ChurnResponse): string => {
    if (!data || !data.data) {
      return "I analyzed your request about customer churn, but I don't have enough information to make a prediction. Could you provide more details about the customer?";
    }

    const { probability, prediction } = data.data;
    const isLikelyToChurn = prediction === 'Yes' || (probability !== undefined && probability > 0.5);
    const probabilityPercentage = probability !== undefined ? Math.round(probability * 100) : null;
    
    // Get feature importance if available
    const topFactors = data.data.feature_importance?.slice(0, 3).map(item => item.feature) || [];
    
    // Extract customer details from input data
    const customerDetails = [];
    if (data.data.input_data) {
      const { tenure, MonthlyCharges, Contract, OnlineSecurity, TechSupport, OnlineBackup } = data.data.input_data;
      if (tenure) customerDetails.push(`${tenure} months tenure`);
      if (MonthlyCharges) customerDetails.push(`$${MonthlyCharges} monthly charges`);
      if (Contract) customerDetails.push(`${Contract} contract`);
      if (OnlineSecurity) customerDetails.push(`${OnlineSecurity === 'Yes' ? 'has' : 'no'} online security`);
      if (OnlineBackup) customerDetails.push(`${OnlineBackup === 'Yes' ? 'has' : 'no'} online backup`);
      if (TechSupport) customerDetails.push(`${TechSupport === 'Yes' ? 'has' : 'no'} tech support`);
    }
    
    // Build the response
    let response = '';
    
    // Start with the main prediction
    if (probabilityPercentage !== null) {
      if (isLikelyToChurn) {
        response = `Based on my analysis, this customer is likely to churn with a ${probabilityPercentage}% probability. `;
      } else {
        response = `Based on my analysis, this customer is not likely to churn (${probabilityPercentage}% probability). `;
      }
    } else {
      response = isLikelyToChurn ? 
        'Based on the information provided, this customer is likely to churn. ' : 
        'Based on the information provided, this customer is not likely to churn. ';
    }
    
    // Add customer profile summary
    if (customerDetails.length > 0) {
      response += `The customer with ${customerDetails.join(', ')} `;
      response += isLikelyToChurn ? 
        'shows several risk factors for potential churn. ' : 
        'shows positive retention indicators. ';
    }
    
    // Add key factors affecting the prediction
    if (topFactors.length > 0) {
      response += `The key factors influencing this prediction are ${topFactors.join(', ')}. `;
    }
    
    // Add recommendations based on risk level
    if (isLikelyToChurn) {
      if (probabilityPercentage && probabilityPercentage > 70) {
        response += 'I strongly recommend immediate retention actions such as offering a personalized discount, service upgrade, or reaching out with a special loyalty offer.';
      } else {
        response += 'Consider proactive retention measures like checking in with the customer about their satisfaction or offering additional services that complement their usage patterns.';
      }
    } else {
      response += 'This customer appears stable, but it\'s always good practice to continue monitoring satisfaction and engagement levels.';
    }
    
    return response;
  };

  return (
    <div className="flex flex-col h-full bg-background dark:bg-background">
      {/* Chat history display */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4 max-h-[400px] pr-2">
        {chatHistory.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-4">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
              <Bot className="h-8 w-8 text-primary" />
            </div>
            <div>
              <h3 className="font-medium text-xl">Ask Me About Your Churn Data</h3>
              <p className="text-muted-foreground">Get insights and predictions about your customer churn</p>
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
                <p className="text-sm">Thinking...</p>
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
              {response.data?.probability !== undefined && (
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <h3 className="text-sm font-medium">Churn Probability</h3>
                    <span className="text-sm font-bold">
                      {Math.round(response.data.probability * 100)}%
                    </span>
                  </div>
                  <Progress 
                    value={response.data.probability * 100} 
                    className="h-2"
                  />
                </div>
              )}
              
              {response.data?.input_data && (
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mt-2">
                  {Object.entries(response.data.input_data)
                    .filter(([key]) => !['Prediction', 'Churn Probability'].includes(key))
                    .slice(0, 6)
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-muted-foreground">{key}:</span>
                        <span className="font-medium">{String(value)}</span>
                      </div>
                    ))}
                </div>
              )}
              
              {/* Feature importance section */}
              {response.data?.feature_importance && response.data.feature_importance.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium mb-2">Key Factors</h4>
                  <div className="space-y-2">
                    {response.data.feature_importance.slice(0, 5).map(({feature, importance}) => (
                      <div key={feature} className="flex justify-between items-center text-sm">
                        <span>{feature}</span>
                        <span className="text-muted-foreground">{((importance) * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Input features */}
              {response.data?.input_features && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium mb-2">Customer Profile</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(response.data.input_features).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-center text-sm">
                        <span>{key}</span>
                        <span className="text-muted-foreground">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Input form - Factory Astro style */}
      <div className="mt-auto">
        <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
          <Input
            placeholder="Ask about customer churn..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="flex-1"
            disabled={isLoading}
          />
          <Button type="submit" disabled={isLoading || !question.trim()}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Ask'}
          </Button>
        </form>
        
        {/* Example questions - Factory Astro style grid layout */}
        <div className="mt-4">
          <p className="text-sm font-medium mb-3">Try asking</p>
          <div className="flex flex-col space-y-2">
            <div className="flex flex-col md:flex-row md:space-x-2 space-y-2 md:space-y-0">
              <button
                className="text-sm px-4 py-3 bg-primary-900/10 hover:bg-primary/20 text-left rounded-md transition-colors border border-primary/10 flex-1"
                onClick={() => setQuestion("Will a customer with 12 months tenure, no online security, yes to online backup, no tech support, on a month-to-month contract, and paying $65.50 monthly likely churn?")}
                disabled={isLoading}
                type="button"
              >
                <span className="mr-2 text-primary/70">1.</span>
                Will a customer with 12 months tenure, no online security, yes to online backup, no tech support, on a month-to-month contract, and paying $65.50 monthly likely churn?
              </button>
              <button
                className="text-sm px-4 py-3 bg-primary-900/10 hover:bg-primary/20 text-left rounded-md transition-colors border border-primary/10 flex-1"
                onClick={() => setQuestion("What's the churn probability for a customer who has been with us for 36 months, has online security, online backup, tech support, is on a two-year contract, and pays $105.80 monthly?")}
                disabled={isLoading}
                type="button"
              >
                <span className="mr-2 text-primary/70">2.</span>
                Is a customer with 36 months tenure, with online security, with online backup, tech support, on a two-year contract, and paying $105.80 monthly likely to churn?
              </button>
            </div>
            
            <div className="flex flex-col md:flex-row md:space-x-2 space-y-2 md:space-y-0">
              <button
                className="text-sm px-4 py-3 bg-primary-900/10 hover:bg-primary/20 text-left rounded-md transition-colors border border-primary/10 flex-1"
                onClick={() => setQuestion("Is a customer with 6 months tenure, no online security or backup, no tech support, month-to-month contract, and $70 monthly charges at risk of churning?")}
                disabled={isLoading}
                type="button"
              >
                <span className="mr-2 text-primary/70">3.</span>
                What's the churn prediction for a customer with 6 months tenure, no online security or backup, no tech support, month-to-month contract, and $70 monthly charges?
              </button>
              <button
                className="text-sm px-4 py-3 bg-primary-900/10 hover:bg-primary/20 text-left rounded-md transition-colors border border-primary/10 flex-1"
                onClick={() => setQuestion("Will a customer on a one-year contract with 18 months tenure, online security, no online backup, tech support, and $85 monthly charges stay with us?")}
                disabled={isLoading}
                type="button"
              >
                <span className="mr-2 text-primary/70">4.</span>
                Predict churn for a customer with 24 months tenure, with online security, no online backup, tech support, and $85 monthly charges?
              </button>
            </div>
            
            <div className="flex flex-col md:flex-row md:space-x-2 space-y-2 md:space-y-0">
              <button
                className="text-sm px-4 py-3 bg-primary-900/10 hover:bg-primary/20 text-left rounded-md transition-colors border border-primary/10 flex-1"
                onClick={() => setQuestion("What's the likelihood of churn for a customer who's been with us for 24 months, has no internet service, and pays $45 monthly on a two-year contract?")}
                disabled={isLoading}
                type="button"
              >
                <span className="mr-2 text-primary/70">5.</span>
                What's the likelihood of churn for a customer who's been with us for 24 months, has no internet service, and pays $45 monthly on a two-year contract?
              </button>
              <button
                className="text-sm px-4 py-3 bg-primary-900/10 hover:bg-primary/20 text-left rounded-md transition-colors border border-primary/10 flex-1"
                onClick={() => setQuestion("Predict if a customer will churn if they have no online security, no tech support, 9 months tenure, and $60 monthly charges on a month-to-month contract.")}
                disabled={isLoading}
                type="button"
              >
                <span className="mr-2 text-primary/70">6.</span>
                Predict if a customer will churn if they have no online security, no tech support, 9 months tenure, and $60 monthly charges on a month-to-month contract.
              </button>
            </div>
            
            <div className="flex flex-col md:flex-row md:space-x-2 space-y-2 md:space-y-0">
              <button
                className="text-sm px-4 py-3 bg-primary-900/10 hover:bg-primary/20 text-left rounded-md transition-colors border border-primary/10 flex-1"
                onClick={() => setQuestion("Customer with 48 months tenure, all services enabled, two-year contract, and $120 monthly charges - will they churn?")}
                disabled={isLoading}
                type="button"
              >
                <span className="mr-2 text-primary/70">7.</span>
                Customer with 48 months tenure, all services enabled, two-year contract, and $120 monthly charges - will they churn?
              </button>
              <button
                className="text-sm px-4 py-3 bg-primary-900/10 hover:bg-primary/20 text-left rounded-md transition-colors border border-primary/10 flex-1"
                onClick={() => setQuestion("What's the churn risk for a new customer (3 months) with no services and a month-to-month contract paying $50 monthly?")}
                disabled={isLoading}
                type="button"
              >
                <span className="mr-2 text-primary/70">8.</span>
                What's the churn risk for a new customer (3 months) with no services and a month-to-month contract paying $50 monthly?
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

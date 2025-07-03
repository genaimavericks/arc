import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, AreaChart, Area, LabelList } from 'recharts';
import { CustomTooltip, formatYAxisTick, formatDataLabel, getTooltipProps } from './chart-formatters';
import { Loader2, AlertCircle, Bot, BarChart as BarChartIcon } from 'lucide-react';
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
  const [chartType, setChartType] = useState<'line' | 'bar' | 'area'>('line'); // Default chart type
  
  // Use the Djinni store for persistent state
  const { chatHistory: storeChatHistory, sessionMessages, addMessage, activeModel, isNewSession, startNewSession } = useDjinniStore();
  
  // Default example questions in case API fails
  const defaultExamples = [
    "What will the revenue for factory 3 be over the next 4 months?",
    "What will the profit margin of factory 1 for next quarter?",
    "What will the production volume be over the next 2 months?",
    "What will the revenue over the next 2 months for factory 3?"

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
      
      // Determine and set the appropriate chart type based on data and query
      const detectedChartType = determineChartType(data, userMessage);
      setChartType(detectedChartType);
      console.log('Detected chart type:', detectedChartType);
      
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

  // Determine the appropriate chart type based on data and query
  const determineChartType = (data: any, query: string): 'line' | 'bar' | 'area' => {
    if (!data?.data?.Predicted_data || !Array.isArray(data.data.Predicted_data)) {
      return 'line'; // Default to line chart if no valid data
    }
    
    console.log('Determining chart type for query:', query);
    
    // Extract data characteristics
    const dataLength = data.data.Predicted_data.length;
    const dataPoints = data.data.Predicted_data;
    // Define a type for data points to avoid implicit any
    type DataPoint = Record<string, string | number | boolean | null | undefined>;
    const hasTimeSequence = dataPoints.some((point: DataPoint) => point.Month || point.Date || point.time || point.period);
    const isDiscrete = dataLength <= 6; // Small number of data points might be better as bar chart
    
    // Check if query contains keywords suggesting specific chart types
    const barChartKeywords = ['compare', 'comparison', 'versus', 'vs', 'difference', 'bar', 'distribution', 'breakdown'];
    const areaChartKeywords = ['trend', 'over time', 'progression', 'growth', 'decline', 'area', 'cumulative'];
    const lineChartKeywords = ['line', 'trajectory', 'forecast', 'prediction', 'project', 'future'];
    
    const isBarChartQuery = barChartKeywords.some(keyword => query.toLowerCase().includes(keyword));
    const isAreaChartQuery = areaChartKeywords.some(keyword => query.toLowerCase().includes(keyword));
    const isLineChartQuery = lineChartKeywords.some(keyword => query.toLowerCase().includes(keyword));
    
    // Check for specific metrics that are better represented by certain chart types
    const metricName = data.data.metric_name || '';
    const isComparisonMetric = ['difference', 'ratio', 'comparison', 'distribution'].some(
      term => metricName.toLowerCase().includes(term)
    );
    
    // Check if data structure suggests multiple series (multi-line chart)
    const firstItem = data.data.Predicted_data[0];
    let hasMultipleSeries = false;
    
    if (firstItem && typeof firstItem === 'object') {
      // If data has multiple numeric properties, it might be suitable for a multi-line chart
      const numericProps = Object.entries(firstItem)
        .filter(([k, v]) => typeof v === 'number' || (typeof v === 'string' && !isNaN(parseFloat(v as string))))
        .filter(([k, _]) => k !== 'Month' && k !== 'Date' && k !== 'time' && k !== 'period');
      
      hasMultipleSeries = numericProps.length > 1;
    }
    
    // Decision logic for chart type
    if (isBarChartQuery || (isDiscrete && !isLineChartQuery) || isComparisonMetric) {
      console.log('Selected bar chart based on:', { isBarChartQuery, isDiscrete, isComparisonMetric });
      return 'bar';
    }
    
    if (isAreaChartQuery || (hasTimeSequence && dataLength > 6 && !isLineChartQuery)) {
      console.log('Selected area chart based on:', { isAreaChartQuery, hasTimeSequence, dataLength });
      return 'area';
    }
    
    if (isLineChartQuery || hasMultipleSeries || (!isDiscrete && hasTimeSequence)) {
      console.log('Selected line chart based on:', { isLineChartQuery, hasMultipleSeries, isDiscrete, hasTimeSequence });
      return 'line';
    }
    
    // Default to line chart as fallback
    console.log('Defaulting to line chart');
    return 'line';
  };
  
  // Calculate optimal Y-axis domain based on data range
  const calculateYAxisDomain = (data: any[]): [number, number] => {
    if (!data || data.length === 0) return [0, 100]; // Default domain if no data
    
    // Get all values
    const values = data.map(item => item.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    
    // Calculate the range of values
    const range = max - min;
    
    // Get the order of magnitude of the values
    const avgValue = (min + max) / 2;
    const orderOfMagnitude = Math.floor(Math.log10(avgValue));
    
    console.log(`Value range: ${min} to ${max}, difference: ${range}, order of magnitude: 10^${orderOfMagnitude}`);
    
    // If range is very small compared to the values (small decimal differences)
    if (range < avgValue * 0.01) {
      // For small variations in decimal places, create a focused scale
      // Calculate a precise lower and upper bound to highlight differences
      
      // Find how many decimal places we need to consider for meaningful differences
      let decimalPrecision = 0;
      let tempRange = range;
      while (tempRange < 1 && tempRange > 0) {
        tempRange *= 10;
        decimalPrecision++;
      }
      
      // Get a scaling factor based on the decimals where variation occurs
      const scaleFactor = Math.pow(10, Math.max(0, decimalPrecision - 1));
      
      // Calculate adjusted bounds that focus on the area of variation
      const adjustedMin = Math.floor(min * scaleFactor) / scaleFactor;
      const adjustedMax = Math.ceil(max * scaleFactor) / scaleFactor;
      
      // Add some padding to ensure all points are visible
      const padding = (adjustedMax - adjustedMin) * 0.1;
      const lowerBound = Math.max(0, adjustedMin - padding);
      const upperBound = adjustedMax + padding;
      
      console.log(`Using precise Y-axis domain: [${lowerBound}, ${upperBound}] with decimal precision ${decimalPrecision}`);
      return [lowerBound, upperBound];
    }
    
    // For normal ranges, use standard scaling with some padding
    const padding = range * 0.1;
    return [Math.max(0, min - padding), max + padding];
  };
  
  // Format data for chart if available
  const formatChartData = () => {
    console.log('Response object:', response);
    
    // Check if response exists and has data
    if (!response) {
      console.log('No response available');
      return [];
    }
    
    // Use mock data for testing if needed
    if (process.env.NODE_ENV === 'development' && (!response.data || !response.data.Predicted_data)) {
      console.log('Using mock data for development');
      // Create sample data for testing
      return [
        { name: 'Jan', value: 4000 },
        { name: 'Feb', value: 3000 },
        { name: 'Mar', value: 2000 },
        { name: 'Apr', value: 2780 },
        { name: 'May', value: 1890 },
        { name: 'Jun', value: 2390 },
        { name: 'Jul', value: 3490 },
      ];
    }
    
    let predictionData;
    
    // Try to find the prediction data in various places
    if (response.data?.Predicted_data && Array.isArray(response.data.Predicted_data)) {
      predictionData = response.data.Predicted_data;
      console.log('Found prediction data in response.data.Predicted_data');
    } else if (response.Predicted_data && Array.isArray(response.Predicted_data)) {
      predictionData = response.Predicted_data;
      console.log('Found prediction data in response.Predicted_data');
    } else if (response.data && Array.isArray(response.data)) {
      predictionData = response.data;
      console.log('Found prediction data in response.data array');
    } else if (Array.isArray(response)) {
      predictionData = response;
      console.log('Response itself is the prediction data array');
    } else if (response.data) {
      // Try to find any array in the response.data object
      const possibleArrays = Object.entries(response.data)
        .filter(([_, val]) => Array.isArray(val) && val.length > 0);
      
      if (possibleArrays.length > 0) {
        predictionData = possibleArrays[0][1];
        console.log('Found array in response.data:', possibleArrays[0][0]);
      } else {
        // If no arrays found, check if response.data itself is usable
        console.log('No arrays found in response.data, trying to use response.data directly');
        predictionData = [response.data];
      }
    } else {
      console.log('No valid prediction data structure found in response');
      return [];
    }
    
    console.log('Raw prediction data:', predictionData);
    
    if (!predictionData || predictionData.length === 0) {
      console.log('Prediction data is empty');
      return [];
    }
    
    // Check the structure of the first item to determine the format
    const firstItem = predictionData[0];
    console.log('First item in prediction data:', firstItem);
    
    // Handle different data structures that might come from the API
    if (firstItem && typeof firstItem === 'object') {
      // If the data is already in the expected format with Month/Date and Value properties
      if ((firstItem.Month || firstItem.Date) && (firstItem.Value !== undefined)) {
        console.log('Using Month/Date and Value format');
        return predictionData.map((item: any, index: number) => {
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
      // If the data has numeric properties that could be values
      else {
        console.log('Looking for numeric properties in object');
        // Prioritize 'prediction' field if it exists
        const hasPrediction = 'prediction' in firstItem;
        
        // Look for numeric properties that could be values
        const numericProps = Object.entries(firstItem)
          .filter(([key, val]) => key !== 'name' && key !== 'label' && key !== 'id')
          .filter(([_, val]) => typeof val === 'number' || (typeof val === 'string' && !isNaN(parseFloat(val as string))));
        
        console.log('Found numeric properties:', numericProps);
        console.log('Has prediction field:', hasPrediction);
        
        if (hasPrediction) {
          console.log('Using prediction field for values');
          const valueKey = 'prediction';
        } else if (numericProps.length > 0) {
          // Use the first numeric property as the value
          const valueKey = numericProps[0][0];
          console.log('Using property as value:', valueKey);
          
          return predictionData.map((item: any, index: number) => {
            // Use month/year combination if available, otherwise fallback to index
            let nameValue;
            if (item.month && item.year) {
              nameValue = `${item.month}/${item.year}`;  
            } else if (item.month) {
              nameValue = `Month ${item.month}`;
            } else {
              nameValue = item.name || item.label || item.Month || item.Date || `Month ${index + 1}`;
            }
            
            // Prioritize the prediction field if it exists
            const value = hasPrediction 
              ? (typeof item.prediction === 'string' ? parseFloat(item.prediction) : item.prediction)
              : (typeof item[valueKey] === 'string' ? parseFloat(item[valueKey]) : item[valueKey]);
            
            return {
              name: nameValue,
              value: value,
              original: item
            };
          });
        }
      }
    }
    
    // If the data is an array of numbers
    if (predictionData.every((item: any) => typeof item === 'number')) {
      console.log('Using array of numbers format');
      return predictionData.map((value: number, index: number) => ({
        name: `Month ${index + 1}`,
        value: value
      }));
    }
    
    // Last resort fallback: create a simple data structure from whatever we have
    console.log('Using fallback data extraction');
    return predictionData.map((item: any, index: number) => {
      // Try to extract a meaningful value
      let value = 0;
      if (typeof item === 'number') {
        value = item;
      } else if (typeof item === 'object') {
        // Check for prediction field first
        if ('prediction' in item && (typeof item.prediction === 'number' || 
            (typeof item.prediction === 'string' && !isNaN(parseFloat(item.prediction))))) {
          value = typeof item.prediction === 'string' ? parseFloat(item.prediction) : item.prediction;
        } else {
          // Look for any property that might contain a numeric value
          const numericProps = Object.entries(item)
            .filter(([_, v]) => typeof v === 'number' || (typeof v === 'string' && !isNaN(parseFloat(v as string))))
            .map(([k, v]) => [k, typeof v === 'string' ? parseFloat(v as string) : v]);
          
          if (numericProps.length > 0) {
            // Use the first numeric property found
            value = numericProps[0][1] as number;
          }
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
  
  // Enhanced tooltip function to properly display small decimal differences
  const getEnhancedTooltip = () => {
    const yLabel = getYAxisLabel();
    return {
      formatter: (value: any) => {
        if (typeof value !== 'number') return [value, yLabel];
        
        // Determine decimal precision based on value magnitude
        let minDecimals = 2;
        let maxDecimals = 4;
        
        // For very small values or where precision matters, show more decimals
        if (Math.abs(value) < 0.01) {
          minDecimals = 4;
          maxDecimals = 6;
        } else if (Math.abs(value) < 1) {
          minDecimals = 3;
          maxDecimals = 5;
        }
        
        return [
          value.toLocaleString(undefined, { minimumFractionDigits: minDecimals, maximumFractionDigits: maxDecimals }),
          yLabel
        ];
      },
      labelFormatter: (label: string) => `Time Period: ${label}`,
      contentStyle: { 
        backgroundColor: '#fff', 
        border: '1px solid #ddd', 
        borderRadius: '4px',
        padding: '10px',
        fontSize: '12px'
      }
    };
  };
  
  // Function to render the appropriate chart based on chartType
  const renderChart = () => {
    const data = formatChartData();
    
    // Check if we have valid data
    if (!data || data.length === 0) {
      console.warn('No valid chart data available');
      return (
        <div className="flex items-center justify-center h-full w-full text-muted-foreground">
          <p>No chart data available</p>
        </div>
      );
    }
    
    console.log('Rendering chart type:', chartType, 'with data:', data);
    
    // Determine chart colors based on data values
    const getChartColors = () => {
      // Default color scheme
      const colors = {
        primary: '#8884d8',
        secondary: '#82ca9d',
        accent: '#ffc658',
        stroke: '#8884d8',
        fill: '#8884d8',
        fillOpacity: 0.3
      };
      
      // Customize colors based on data context if needed
      if (response?.data?.context?.theme === 'dark') {
        colors.primary = '#bb86fc';
        colors.secondary = '#03dac6';
        colors.accent = '#cf6679';
      }
      
      return colors;
    };
    
    const colors = getChartColors();
    
    const commonProps = {
      margin: {
        top: 20,
        right: 30,
        left: 50,  // Increased left margin for Y-axis labels
        bottom: 30, // Increased bottom margin for X-axis labels
      },
      width: 500,
      height: 300,
    };

    // Common chart components with improved styling
    const commonComponents = (
      <>
        <CartesianGrid strokeDasharray="3 3" stroke="#999" strokeOpacity={0.6} />
        <XAxis 
          dataKey="name" 
          height={40}
          tick={{ fill: '#333', fontSize: 12 }}
          tickFormatter={(value) => value.toString().substring(0, 10)}
        />
        <Legend 
          wrapperStyle={{ paddingTop: '10px' }} 
          iconType="circle"
          iconSize={8}
          layout="horizontal"
          verticalAlign="top"
        />
      </>
    );

    // Log the actual data being rendered
    console.log('Chart data being rendered:', JSON.stringify(data.slice(0, 3)));
    
    // Render appropriate chart based on chartType
    switch (chartType) {
      case 'bar':
        return (
          <BarChart data={data} {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="name" 
              label={{ value: 'Time Period', position: 'insideBottom', offset: -5 }}
            />
            <YAxis 
              label={{ value: getYAxisLabel(), angle: -90, position: 'insideLeft' }}
              domain={calculateYAxisDomain(data)}
              tickFormatter={(value) => value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
            />
            <Tooltip {...getEnhancedTooltip()} />
            <Legend />
            <Bar
              dataKey="value"
              name={getYAxisLabel()}
              fill="#8884d8"
              radius={[4, 4, 0, 0]}
            >
              <LabelList dataKey="value" position="top" />
            </Bar>
            <text x="50%" y="95%" textAnchor="middle" style={{ fontSize: '12px', fill: '#666' }}>
              Note: Chart is scaled to highlight small variations in the data
            </text>
          </BarChart>
        );
      case 'area':
        return (
          <AreaChart data={data} {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis 
              label={{ value: getYAxisLabel(), angle: -90, position: 'insideLeft' }}
              domain={calculateYAxisDomain(data)}
              tickFormatter={(value) => value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
            />
            <Tooltip {...getEnhancedTooltip()} />
            <Legend />
            <Area
              type="monotone"
              dataKey="value"
              name={getYAxisLabel()}
              stroke="#8884d8"
              fill="#8884d8"
              fillOpacity={0.3}
            />
            <text x="50%" y="95%" textAnchor="middle" style={{ fontSize: '12px', fill: '#666' }}>
              Note: Chart is scaled to highlight small variations in the data
            </text>
          </AreaChart>
        );
      case 'line':
      default:
        return (
          <LineChart data={data} {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis 
              label={{ value: getYAxisLabel(), angle: -90, position: 'insideLeft' }}
              domain={calculateYAxisDomain(data)}
              tickFormatter={(value) => value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
            />
            <Tooltip {...getEnhancedTooltip()} />
            <Legend />
            <Line
              type="monotone"
              dataKey="value"
              name={getYAxisLabel()}
              stroke="#8884d8"
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 8, fill: colors.primary, stroke: '#fff' }}
              isAnimationActive={true}
              animationDuration={1000}
              animationEasing="ease-in-out"
            />
            <text x="50%" y="95%" textAnchor="middle" style={{ fontSize: '12px', fill: '#666' }}>
              Note: Chart is scaled to highlight small variations in the data
            </text>
          </LineChart>
        );
    }
  };

  // Get appropriate Y-axis label based on data context
  const getYAxisLabel = (): string => {
    // Check if response summary contains clues about the metric
    if (response?.summary && typeof response.summary === 'string') {
      const summary = response.summary.toLowerCase();
      if (summary.includes('revenue')) return 'Revenue ($)';
      if (summary.includes('profit margin')) return 'Profit Margin (%)';
      if (summary.includes('profit')) return 'Profit ($)';
      if (summary.includes('production volume')) return 'Production Volume (units)';
      if (summary.includes('cost')) return 'Cost ($)';
    }
    
    // Try to extract metric name from response
    const metricName = response?.data?.metric_name || '';
    if (metricName) {
      return metricName.charAt(0).toUpperCase() + metricName.slice(1);
    }
    
    // Check if we can determine metric from the question
    const userQuestion = question || response?.question || '';
    const lowerQuestion = userQuestion.toLowerCase();
    
    if (lowerQuestion.includes('revenue')) return 'Revenue ($)';
    if (lowerQuestion.includes('profit margin')) return 'Profit Margin (%)';
    if (lowerQuestion.includes('profit')) return 'Profit ($)';
    if (lowerQuestion.includes('production') || lowerQuestion.includes('volume')) return 'Production Volume (units)';
    if (lowerQuestion.includes('cost')) return 'Cost ($)';
    
    // Default label
    return 'Predicted Value';
  };

  // Debug chart data and verify chart type detection
  useEffect(() => {
    if (response) {
      const formattedData = formatChartData();
      console.log('Formatted chart data:', formattedData);
      
      // Detailed logging of data structure for debugging
      if (formattedData.length > 0) {
        console.log('First data point:', JSON.stringify(formattedData[0]));
        console.log('Data sample:', JSON.stringify(formattedData.slice(0, 3)));
        console.log('Data keys in first item:', Object.keys(formattedData[0]));
        console.log('Data values in first item:', Object.values(formattedData[0]));
        
        // Check specifically for name and value properties
        const hasNameProp = formattedData.every((item: any) => item.name !== undefined);
        const hasValueProp = formattedData.every((item: any) => item.value !== undefined);
        console.log('All data items have name property:', hasNameProp);
        console.log('All data items have value property:', hasValueProp);
        
        // Log data structure for chart debugging
        console.log('Chart data structure check:');
        console.log('- Data is array:', Array.isArray(formattedData));
        console.log('- Array length:', formattedData.length);
      }
      
      // Log chart type detection details
      console.log('Chart type detection verification:');
      console.log('- Selected chart type:', chartType);
      console.log('- Query:', response.query || 'N/A');
      console.log('- Data points count:', formattedData.length);
      console.log('- Has time sequence:', formattedData.some((d: {name: string}) => 
        d.name && (typeof d.name === 'string') && 
        (d.name.includes('Month') || d.name.includes('Date'))));
      
      // Force chart type update if we have data but no chart type selected
      if (formattedData.length > 0) {
        const detectedChartType = determineChartType(response, question || '');
        console.log('Detected chart type:', detectedChartType);
        setChartType(detectedChartType); // Always update to ensure correct type
      }
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
              <BarChartIcon className="h-8 w-8 text-primary" />
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
              
              {/* Show chart if we can format data for it */}
              {response && formatChartData().length > 0 && (
                <div className="mt-4">
                  <div className="flex justify-between items-center mb-2">
                    <h4 className="text-sm font-medium">Prediction Chart</h4>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">Chart type:</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-primary/20 text-primary font-medium">
                        {chartType === 'bar' ? 'Bar Chart' : chartType === 'area' ? 'Area Chart' : 'Line Chart'}
                      </span>
                      {/* Chart type toggle buttons for testing */}
                      <div className="flex gap-1 ml-2">
                        <button 
                          onClick={() => setChartType('line')} 
                          className={`text-xs px-1.5 py-0.5 rounded ${chartType === 'line' ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-800'}`}
                          title="Switch to Line Chart"
                        >
                          Line
                        </button>
                        <button 
                          onClick={() => setChartType('bar')} 
                          className={`text-xs px-1.5 py-0.5 rounded ${chartType === 'bar' ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-800'}`}
                          title="Switch to Bar Chart"
                        >
                          Bar
                        </button>
                        <button 
                          onClick={() => setChartType('area')} 
                          className={`text-xs px-1.5 py-0.5 rounded ${chartType === 'area' ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-800'}`}
                          title="Switch to Area Chart"
                        >
                          Area
                        </button>
                      </div>
                    </div>
                  </div>
                  <div className="w-full bg-card rounded-md p-4" style={{ minHeight: '400px' }}>
                    {/* Force chart height and add debug info */}
                    <div className="text-xs text-muted-foreground mb-2">
                      Data points: {formatChartData().length} | Chart type: {chartType}
                    </div>
                    
                    {/* Basic chart for testing if regular charts don't work */}
                    {formatChartData().length > 0 && chartType === 'bar' && (
                      <div className="mb-4">
                        <div className="font-bold text-sm">Verification: Raw Data Values</div>
                        <div className="text-xs space-y-1">
                          {formatChartData().map((item: {name: string, value: number}, index: number) => (
                            <div key={index} className="grid grid-cols-2">
                              <span>{item.name || index}:</span>
                              <span>{item.value}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <div style={{ width: '100%', height: '350px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        {renderChart()}
                      </ResponsiveContainer>
                    </div>
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

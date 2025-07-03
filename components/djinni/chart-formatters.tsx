import React from 'react';
import { TooltipProps } from 'recharts';

// Custom tooltip content component for precise decimal display with special handling for small variations
export const CustomTooltip = ({ active, payload, label, yAxisLabel }: any) => {
  if (active && payload && payload.length) {
    const value = payload[0].value;
    
    // Determine decimal precision based on value magnitude and variation
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
    
    // Format the value with appropriate precision
    const formattedValue = value.toLocaleString(undefined, { 
      minimumFractionDigits: minDecimals, 
      maximumFractionDigits: maxDecimals 
    });
    
    return (
      <div className="custom-tooltip" style={{ 
        backgroundColor: '#fff', 
        border: '1px solid #ddd',
        borderRadius: '4px',
        padding: '10px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <p className="label" style={{ fontWeight: 'bold', marginBottom: '5px' }}>{`Time Period: ${label}`}</p>
        <p className="value" style={{ margin: 0 }}>
          <span style={{ fontWeight: 'bold' }}>{yAxisLabel}: </span>
          <span>{formattedValue}</span>
        </p>
      </div>
    );
  }

  return null;
};

// Format tick values for Y-axis with appropriate precision based on value range
export const formatYAxisTick = (value: number) => {
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
  
  return value.toLocaleString(undefined, { 
    minimumFractionDigits: minDecimals, 
    maximumFractionDigits: maxDecimals
  });
};

// Enhanced formatter for tooltip values with better decimal precision handling
export const getTooltipProps = (yAxisLabel: string): Partial<TooltipProps<any, any>> => {
  return {
    formatter: (value: any) => {
      // Determine decimal precision
      let minDecimals = 2;
      let maxDecimals = 4;
      
      if (typeof value === 'number') {
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
          yAxisLabel
        ];
      }
      return [value, yAxisLabel];
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

// Format data label values for improved readability
export const formatDataLabel = (value: number) => {
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
  
  return value.toLocaleString(undefined, { 
    minimumFractionDigits: minDecimals, 
    maximumFractionDigits: maxDecimals 
  });
};

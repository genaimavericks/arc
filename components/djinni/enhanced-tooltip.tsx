import { TooltipProps } from 'recharts';

// This is a custom tooltip formatter for the FactoryAstro charts
// It ensures proper decimal precision display for small value differences
export const formatTooltipValue = (value: number): string => {
  return value.toLocaleString(undefined, { 
    minimumFractionDigits: 2,
    maximumFractionDigits: 4
  });
};

// Formats the tooltip label (usually the x-axis value)
export const formatTooltipLabel = (label: string): string => {
  return `Time Period: ${label}`;
};

// Returns the complete tooltip formatter function for Recharts
export const getTooltipFormatter = (metricLabel: string) => {
  return (value: number) => [
    formatTooltipValue(value),
    metricLabel
  ];
};

import { fetchWithAuth } from '../../../lib/auth-utils';

// Interfaces for the API responses
export interface ChurnSummaryData {
  customer_profile: {
    total_customers: number;
    avg_monthly_charges: number;
    total_charges: number;
  };
  churn_profile: {
    total_churners: number;
    churn_rate: number;
    avg_monthly_charges: number;
    avg_total_charges: number;
  };
  key_insights: {
    avg_tenure_non_churners: number;
    avg_tenure_churners: number;
    most_common_contract: string;
    most_common_internet_churners: string;
  };
  demographics: {
    gender: Record<string, number>;
    contract: Record<string, number>;
    internet_service: Record<string, number>;
    tenure: Record<string, number>;
  };
}

export interface CustomerProfileData {
  stats: {
    total_customers: number;
    monthly_charges: number;
    total_charges: number;
  };
  pie_charts: {
    gender: Array<{category: string, value: number}>;
    tenure: Array<{category: string, value: number}>;
    internet_service: Array<{category: string, value: number}>;
    contract: Array<{category: string, value: number}>;
  };
  additional_stats: {
    senior_citizen_count: number;
    senior_citizen_percentage: number;
    partner_count: number;
    partner_percentage: number;
    phone_service_count: number;
    phone_service_percentage: number;
  };
  payment_methods: Array<{method: string, count: number}>;
}

export interface ChurnerProfileData {
  stats: {
    total_churners: number;
    monthly_charges: number;
    total_charges: number;
    churn_rate: number;
  };
  pie_charts: {
    gender: Array<{category: string, value: number}>;
    tenure: Array<{category: string, value: number}>;
    internet_service: Array<{category: string, value: number}>;
    contract: Array<{category: string, value: number}>;
  };
  additional_stats: {
    senior_citizen_count: number;
    senior_citizen_percentage: number;
    partner_count: number;
    partner_percentage: number;
    phone_service_count: number;
    phone_service_percentage: number;
  };
  payment_methods: Array<{method: string, count: number}>;
}

// Fetch summary data for the churn dashboard
export async function fetchChurnSummary(): Promise<ChurnSummaryData> {
  try {
    const response = await fetchWithAuth('/api/static_dashboards/churn_dashboard/summary');

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching churn summary data:', error);
    throw error;
  }
}

// Fetch customer profile data
export async function fetchCustomerProfile(): Promise<CustomerProfileData> {
  try {
    const response = await fetchWithAuth('/api/static_dashboards/churn_dashboard/customer-profile');

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching customer profile data:', error);
    throw error;
  }
}

// Fetch churner profile data
export async function fetchChurnerProfile(): Promise<ChurnerProfileData> {
  try {
    const response = await fetchWithAuth('/api/static_dashboards/churn_dashboard/churner-profile');

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching churner profile data:', error);
    throw error;
  }
}

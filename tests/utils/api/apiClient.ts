import fetch from 'node-fetch';
import { users } from '../data/testData';

/**
 * API Client for interacting with the RSW backend
 */
export class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl?: string) {
    // Use the configured API URL or default to the testing environment
    this.baseUrl = baseUrl || process.env.TEST_API_URL || 'http://127.0.0.1:9090/api';
  }

  /**
   * Get authorization header for authenticated requests
   */
  private async getAuthHeader(): Promise<HeadersInit> {
    if (!this.token) {
      await this.login();
    }
    return {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json'
    };
  }

  /**
   * Login to get authentication token
   */
  async login(username?: string, password?: string) {
    // Default to admin user if no credentials provided
    const user = username || users.admin.username;
    const pass = password || users.admin.password;

    try {
      const response = await fetch(`${this.baseUrl}/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          username: user,
          password: pass,
        }),
      });

      if (!response.ok) {
        console.error(`Login failed: ${response.status} ${response.statusText}`);
        const errorText = await response.text();
        console.error(`Error response: ${errorText}`);
        throw new Error(`Authentication failed: ${response.status}`);
      }

      const data = await response.json();
      this.token = data.access_token;
      return data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  /**
   * Get data from an API endpoint
   */
  async get(endpoint: string) {
    try {
      const headers = await this.getAuthHeader();
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: 'GET',
        headers
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error fetching ${endpoint}:`, error);
      throw error;
    }
  }

  /**
   * Post data to an API endpoint
   */
  async post(endpoint: string, data: any) {
    try {
      const headers = await this.getAuthHeader();
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data)
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error posting to ${endpoint}:`, error);
      throw error;
    }
  }

  /**
   * Health check endpoint
   */
  async healthCheck() {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      return await response.json();
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }
}

/**
 * WebSocketService - Core service for WebSocket communication
 * Handles connection management, message sending/receiving, and event handling
 */

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

export class WebSocketService {
  private socket: WebSocket | null = null;
  private messageHandlers: Map<string, Function[]> = new Map();
  private connectionStatus: ConnectionStatus = 'disconnected';
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectInterval: number = 3000; // 3 seconds
  private reconnectTimeoutId: NodeJS.Timeout | null = null;
  
  constructor(private baseUrl: string, private autoReconnect: boolean = true) {}
  
  /**
   * Connect to the WebSocket server
   * @param schemaId The schema ID to connect to
   * @param token Authentication token
   * @returns Promise that resolves when connected
   */
  connect(schemaId: string, token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Clear any existing reconnect attempts
        if (this.reconnectTimeoutId) {
          clearTimeout(this.reconnectTimeoutId);
          this.reconnectTimeoutId = null;
        }
        
        this.connectionStatus = 'connecting';
        
        // Create the WebSocket URL with schema ID and token
        const url = `${this.baseUrl}/api/kgdatainsights/ws/${schemaId}?token=${token}`;
        this.socket = new WebSocket(url);
        
        this.socket.onopen = () => {
          console.log('WebSocket connected');
          this.connectionStatus = 'connected';
          this.reconnectAttempts = 0;
          resolve();
        };
        
        this.socket.onclose = (event) => {
          console.log(`WebSocket closed: ${event.code} ${event.reason}`);
          this.connectionStatus = 'disconnected';
          
          // Attempt to reconnect if enabled
          if (this.autoReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            this.reconnectTimeoutId = setTimeout(() => {
              this.connect(schemaId, token).catch(err => {
                console.error('Reconnection failed:', err);
              });
            }, this.reconnectInterval);
          }
        };
        
        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
        
        this.socket.onmessage = (event) => {
          this.handleMessage(event.data);
        };
      } catch (error) {
        this.connectionStatus = 'disconnected';
        reject(error);
      }
    });
  }
  
  /**
   * Send a message through the WebSocket
   * @param type Message type
   * @param content Message content
   */
  sendMessage(type: string, content: any): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, cannot send message');
      return;
    }
    
    const message = {
      type,
      content,
      timestamp: new Date().toISOString()
    };
    
    try {
      this.socket.send(JSON.stringify(message));
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
    }
  }
  
  /**
   * Register a handler for a specific message type
   * @param messageType The message type to handle
   * @param handler The handler function
   */
  registerHandler(messageType: string, handler: Function): void {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, []);
    }
    
    const handlers = this.messageHandlers.get(messageType);
    if (handlers && !handlers.includes(handler)) {
      handlers.push(handler);
    }
  }
  
  /**
   * Unregister a handler for a specific message type
   * @param messageType The message type
   * @param handler The handler function to remove
   */
  unregisterHandler(messageType: string, handler: Function): void {
    if (!this.messageHandlers.has(messageType)) return;
    
    const handlers = this.messageHandlers.get(messageType) || [];
    const index = handlers.indexOf(handler);
    
    if (index !== -1) {
      handlers.splice(index, 1);
    }
  }
  
  /**
   * Handle an incoming WebSocket message
   * @param data The raw message data
   */
  private handleMessage(data: string): void {
    try {
      const message = JSON.parse(data);
      const { type, content } = message;
      
      // Call all registered handlers for this message type
      const handlers = this.messageHandlers.get(type) || [];
      handlers.forEach(handler => {
        try {
          handler(content);
        } catch (error) {
          console.error(`Error in handler for message type '${type}':`, error);
        }
      });
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }
  
  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    // Clear any reconnect attempts
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
    
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    
    this.connectionStatus = 'disconnected';
  }
  
  /**
   * Check if the WebSocket is connected
   * @returns True if connected, false otherwise
   */
  isConnected(): boolean {
    return this.connectionStatus === 'connected';
  }
  
  /**
   * Get the current connection status
   * @returns The connection status
   */
  getConnectionStatus(): ConnectionStatus {
    return this.connectionStatus;
  }
}

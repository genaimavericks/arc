/**
 * WebSocket Service for KG Insights
 * Handles WebSocket connections to the backend for real-time data
 */

export type WebSocketMessageHandler = (message: any) => void;

export interface WebSocketServiceOptions {
  url: string;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export enum ConnectionStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  RECONNECTING = 'reconnecting',
  FAILED = 'failed'
}

export class WebSocketService {
  private socket: WebSocket | null = null;
  private url: string;
  private autoReconnect: boolean;
  private reconnectInterval: number;
  private maxReconnectAttempts: number;
  private reconnectAttempts: number = 0;
  private messageHandlers: Map<string, WebSocketMessageHandler[]> = new Map();
  private statusChangeHandlers: ((status: ConnectionStatus) => void)[] = [];
  private connectionStatus: ConnectionStatus = ConnectionStatus.DISCONNECTED;

  constructor(options: WebSocketServiceOptions) {
    this.url = options.url;
    this.autoReconnect = options.autoReconnect ?? true;
    this.reconnectInterval = options.reconnectInterval ?? 3000;
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 5;
  }

  /**
   * Connect to the WebSocket server
   */
  public connect(): Promise<void> {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return Promise.resolve();
    }

    this.updateConnectionStatus(ConnectionStatus.CONNECTING);

    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(this.url);

        this.socket.onopen = () => {
          this.reconnectAttempts = 0;
          this.updateConnectionStatus(ConnectionStatus.CONNECTED);
          resolve();
        };

        this.socket.onclose = (event) => {
          this.updateConnectionStatus(ConnectionStatus.DISCONNECTED);
          if (this.autoReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.updateConnectionStatus(ConnectionStatus.RECONNECTING);
            this.reconnectAttempts++;
            setTimeout(() => this.connect(), this.reconnectInterval);
          } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.updateConnectionStatus(ConnectionStatus.FAILED);
          }
        };

        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            const { type } = data;
            
            console.log(`WebSocket received message of type: ${type}`, data);
            
            if (type && this.messageHandlers.has(type)) {
              const handlers = this.messageHandlers.get(type) || [];
              console.log(`Found ${handlers.length} handlers for message type: ${type}`);
              handlers.forEach(handler => handler(data));
            } else if (type === 'linguistic_suggestions') {
              // Special handling for linguistic suggestions if no specific handler
              if (this.messageHandlers.has('autocomplete_suggestions')) {
                const handlers = this.messageHandlers.get('autocomplete_suggestions') || [];
                console.log(`Using autocomplete handlers for linguistic suggestions`);
                handlers.forEach(handler => handler({
                  type: 'autocomplete_suggestions',
                  suggestions: data.suggestions
                }));
              } else {
                console.warn(`No handlers registered for linguistic suggestions`);
              }
            } else {
              console.warn(`No handlers registered for message type: ${type}`);
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
      } catch (error) {
        this.updateConnectionStatus(ConnectionStatus.FAILED);
        reject(error);
      }
    });
  }

  /**
   * Disconnect from the WebSocket server
   */
  public disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.updateConnectionStatus(ConnectionStatus.DISCONNECTED);
    }
  }

  /**
   * Send a message to the WebSocket server
   * @param message The message to send
   */
  public send(message: any): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      console.log('Sending WebSocket message:', message);
      this.socket.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected, cannot send message:', message);
    }
  }

  /**
   * Register a handler for a specific message type
   * @param type The message type to handle
   * @param handler The handler function
   */
  public registerHandler(type: string, handler: WebSocketMessageHandler): void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    const handlers = this.messageHandlers.get(type) || [];
    handlers.push(handler);
    this.messageHandlers.set(type, handlers);
  }

  /**
   * Unregister a handler for a specific message type
   * @param type The message type
   * @param handler The handler function to remove
   */
  public unregisterHandler(type: string, handler: WebSocketMessageHandler): void {
    if (this.messageHandlers.has(type)) {
      let handlers = this.messageHandlers.get(type) || [];
      handlers = handlers.filter(h => h !== handler);
      this.messageHandlers.set(type, handlers);
    }
  }

  /**
   * Register a handler for connection status changes
   * @param handler The handler function
   */
  public onStatusChange(handler: (status: ConnectionStatus) => void): void {
    this.statusChangeHandlers.push(handler);
    // Immediately call with current status
    handler(this.connectionStatus);
  }

  /**
   * Unregister a status change handler
   * @param handler The handler to remove
   */
  public offStatusChange(handler: (status: ConnectionStatus) => void): void {
    this.statusChangeHandlers = this.statusChangeHandlers.filter(h => h !== handler);
  }

  /**
   * Get the current connection status
   */
  public getStatus(): ConnectionStatus {
    return this.connectionStatus;
  }

  /**
   * Check if the WebSocket is connected
   */
  public isConnected(): boolean {
    return this.socket !== null && this.socket.readyState === WebSocket.OPEN;
  }

  /**
   * Update the connection status and notify handlers
   * @param status The new connection status
   */
  private updateConnectionStatus(status: ConnectionStatus): void {
    this.connectionStatus = status;
    this.statusChangeHandlers.forEach(handler => handler(status));
  }
}

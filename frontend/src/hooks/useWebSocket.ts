/**
 * React hooks for WebSocket integration
 * Provides easy-to-use hooks for different types of real-time connections
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from './useAuth';
import { 
  WebSocketClient, 
  WebSocketMessage,
  createEventWebSocket,
  createOrderWebSocket,
  createAdminWebSocket,
  createLiveEventWebSocket
} from '../lib/websocket';

// Base WebSocket hook
export function useWebSocket(
  createConnection: () => WebSocketClient,
  deps: any[] = []
) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const clientRef = useRef<WebSocketClient | null>(null);
  const handlersRef = useRef<(() => void)[]>([]);

  const connect = useCallback(async () => {
    if (clientRef.current?.isConnected()) return;

    try {
      const client = createConnection();
      clientRef.current = client;

      // Set up connection handler
      const connectionUnsubscribe = client.onConnection((connected) => {
        setIsConnected(connected);
        if (!connected) {
          setConnectionError('Connection lost');
        } else {
          setConnectionError(null);
        }
      });

      // Set up error handler
      const errorUnsubscribe = client.onError((error) => {
        console.error('WebSocket error:', error);
        setConnectionError('Connection error');
      });

      // Set up message handler for all messages
      const messageUnsubscribe = client.onMessage('*', (message) => {
        setLastMessage(message);
      });

      // Store unsubscribe functions
      handlersRef.current = [connectionUnsubscribe, errorUnsubscribe, messageUnsubscribe];

      await client.connect();
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setConnectionError(error instanceof Error ? error.message : 'Connection failed');
    }
  }, deps);

  const disconnect = useCallback(() => {
    // Clean up handlers
    handlersRef.current.forEach(unsubscribe => unsubscribe());
    handlersRef.current = [];

    if (clientRef.current) {
      clientRef.current.disconnect();
      clientRef.current = null;
    }
    
    setIsConnected(false);
    setConnectionError(null);
  }, []);

  const send = useCallback((message: any) => {
    if (clientRef.current?.isConnected()) {
      return clientRef.current.send(message);
    }
    return false;
  }, []);

  // Subscribe to specific message types
  const onMessage = useCallback((type: string, handler: (message: WebSocketMessage) => void) => {
    if (!clientRef.current) return () => {};
    return clientRef.current.onMessage(type, handler);
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, deps);

  return {
    isConnected,
    connectionError,
    lastMessage,
    connect,
    disconnect,
    send,
    onMessage,
    client: clientRef.current
  };
}

// Hook for event-specific WebSocket connection
export function useEventWebSocket(eventId: number) {
  const { token } = useAuth();

  return useWebSocket(
    () => createEventWebSocket(eventId, token || undefined),
    [eventId, token]
  );
}

// Hook for order-specific WebSocket connection
export function useOrderWebSocket(orderId: number) {
  const { token } = useAuth();

  return useWebSocket(
    () => {
      if (!token) throw new Error('Authentication required for order WebSocket');
      return createOrderWebSocket(orderId, token);
    },
    [orderId, token]
  );
}

// Hook for admin dashboard WebSocket connection
export function useAdminWebSocket() {
  const { token, user } = useAuth();

  return useWebSocket(
    () => {
      if (!token) throw new Error('Authentication required for admin WebSocket');
      if (!user || (user.role !== 'admin' && user.role !== 'organizer')) {
        throw new Error('Admin privileges required');
      }
      return createAdminWebSocket(token);
    },
    [token, user?.role]
  );
}

// Hook for live event WebSocket connection
export function useLiveEventWebSocket(eventId: number) {
  const { token } = useAuth();

  return useWebSocket(
    () => createLiveEventWebSocket(eventId, token || undefined),
    [eventId, token]
  );
}

// Hook for handling specific message types with state
export function useWebSocketMessages<T = any>(
  websocketHook: ReturnType<typeof useWebSocket>,
  messageType: string,
  initialState: T[] = []
): [T[], (message: T) => void, () => void] {
  const [messages, setMessages] = useState<T[]>(initialState);

  const addMessage = useCallback((message: T) => {
    setMessages(prev => [...prev, message]);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  useEffect(() => {
    if (!websocketHook.client) return;

    const unsubscribe = websocketHook.onMessage(messageType, (message) => {
      addMessage(message.data as T);
    });

    return unsubscribe;
  }, [websocketHook.client, messageType, addMessage]);

  return [messages, addMessage, clearMessages];
}

// Hook for real-time ticket availability
export function useTicketAvailability(eventId: number) {
  const websocket = useEventWebSocket(eventId);
  const [ticketUpdates, setTicketUpdates] = useState<any[]>([]);
  const [availability, setAvailability] = useState<Record<number, number>>({});

  useEffect(() => {
    if (!websocket.client) return;

    const unsubscribe = websocket.onMessage('ticket_sold', (message) => {
      const update = message.data;
      setTicketUpdates(prev => [update, ...prev.slice(0, 9)]); // Keep last 10 updates
      setAvailability(prev => ({
        ...prev,
        [update.ticket_type_id]: update.remaining_quantity
      }));
    });

    return unsubscribe;
  }, [websocket.client]);

  return {
    ...websocket,
    ticketUpdates,
    availability,
    getAvailability: (ticketTypeId: number) => availability[ticketTypeId]
  };
}

// Hook for real-time order status
export function useOrderStatus(orderId: number) {
  const websocket = useOrderWebSocket(orderId);
  const [orderStatus, setOrderStatus] = useState<string | null>(null);
  const [statusHistory, setStatusHistory] = useState<any[]>([]);

  useEffect(() => {
    if (!websocket.client) return;

    const unsubscribes = [
      websocket.onMessage('order_created', (message) => {
        setOrderStatus('created');
        setStatusHistory(prev => [message.data, ...prev]);
      }),
      websocket.onMessage('order_updated', (message) => {
        setOrderStatus(message.data.status);
        setStatusHistory(prev => [message.data, ...prev]);
      }),
      websocket.onMessage('order_completed', (message) => {
        setOrderStatus('completed');
        setStatusHistory(prev => [message.data, ...prev]);
      }),
      websocket.onMessage('order_cancelled', (message) => {
        setOrderStatus('cancelled');
        setStatusHistory(prev => [message.data, ...prev]);
      })
    ];

    return () => unsubscribes.forEach(unsub => unsub());
  }, [websocket.client]);

  return {
    ...websocket,
    orderStatus,
    statusHistory
  };
}

// Hook for live event statistics
export function useLiveEventStats(eventId: number) {
  const websocket = useLiveEventWebSocket(eventId);
  const [stats, setStats] = useState<any>({
    totalCheckedIn: 0,
    liveViewers: 0,
    recentActivity: []
  });

  useEffect(() => {
    if (!websocket.client) return;

    const unsubscribes = [
      websocket.onMessage('attendee_checked_in', (message) => {
        const checkinData = message.data;
        setStats(prev => ({
          ...prev,
          totalCheckedIn: checkinData.total_checked_in,
          recentActivity: [checkinData, ...prev.recentActivity.slice(0, 9)]
        }));
      }),
      websocket.onMessage('live_count_update', (message) => {
        const countData = message.data;
        setStats(prev => ({
          ...prev,
          totalCheckedIn: countData.total_checked_in,
          liveViewers: countData.live_attendees || 0
        }));
      })
    ];

    return () => unsubscribes.forEach(unsub => unsub());
  }, [websocket.client]);

  return {
    ...websocket,
    stats
  };
}

// Hook for admin notifications
export function useAdminNotifications() {
  const websocket = useAdminWebSocket();
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const markAsRead = useCallback((notificationId?: string) => {
    if (notificationId) {
      setNotifications(prev => 
        prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
      );
    } else {
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    }
  }, []);

  useEffect(() => {
    if (!websocket.client) return;

    const unsubscribes = [
      websocket.onMessage('admin_notification', (message) => {
        const notification = {
          ...message.data,
          id: Date.now().toString(),
          read: false,
          timestamp: message.timestamp
        };
        setNotifications(prev => [notification, ...prev]);
        setUnreadCount(prev => prev + 1);
      }),
      websocket.onMessage('system_alert', (message) => {
        const alert = {
          ...message.data,
          id: Date.now().toString(),
          type: 'system_alert',
          read: false,
          timestamp: message.timestamp
        };
        setNotifications(prev => [alert, ...prev]);
        setUnreadCount(prev => prev + 1);
      })
    ];

    return () => unsubscribes.forEach(unsub => unsub());
  }, [websocket.client]);

  return {
    ...websocket,
    notifications,
    unreadCount,
    markAsRead
  };
}
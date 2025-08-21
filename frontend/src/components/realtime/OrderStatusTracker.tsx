/**
 * Real-time Order Status Tracker Component
 * Shows live order status updates using WebSocket
 */

import React from 'react';
import { useOrderStatus } from '../../hooks/useWebSocket';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';

interface OrderStatusTrackerProps {
  orderId: number;
  initialStatus?: string;
  onStatusChange?: (status: string, data: any) => void;
  className?: string;
}

const statusConfig = {
  pending: {
    color: 'bg-yellow-500',
    textColor: 'text-yellow-700',
    bgColor: 'bg-yellow-50',
    label: 'Pending',
    icon: '⏳',
    description: 'Processing your order...'
  },
  processing: {
    color: 'bg-blue-500',
    textColor: 'text-blue-700',
    bgColor: 'bg-blue-50',
    label: 'Processing',
    icon: '🔄',
    description: 'Payment being processed...'
  },
  completed: {
    color: 'bg-green-500',
    textColor: 'text-green-700',
    bgColor: 'bg-green-50',
    label: 'Completed',
    icon: '✅',
    description: 'Order completed successfully!'
  },
  cancelled: {
    color: 'bg-red-500',
    textColor: 'text-red-700',
    bgColor: 'bg-red-50',
    label: 'Cancelled',
    icon: '❌',
    description: 'Order was cancelled'
  },
  failed: {
    color: 'bg-red-500',
    textColor: 'text-red-700',
    bgColor: 'bg-red-50',
    label: 'Failed',
    icon: '⚠️',
    description: 'Payment failed'
  }
};

export function OrderStatusTracker({ 
  orderId, 
  initialStatus = 'pending',
  onStatusChange,
  className = '' 
}: OrderStatusTrackerProps) {
  const { orderStatus, statusHistory, isConnected, connectionError } = useOrderStatus(orderId);

  const currentStatus = orderStatus || initialStatus;
  const config = statusConfig[currentStatus as keyof typeof statusConfig] || statusConfig.pending;

  // Notify parent of status changes
  React.useEffect(() => {
    if (onStatusChange && statusHistory.length > 0) {
      const latestStatus = statusHistory[0];
      onStatusChange(latestStatus.status, latestStatus);
    }
  }, [statusHistory, onStatusChange]);

  if (connectionError) {
    return (
      <Card className={className}>
        <CardContent className="p-4">
          <div className="flex items-center text-red-600">
            <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse mr-2"></div>
            <span className="text-sm">Unable to get live updates</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Order Status</CardTitle>
          <div className="flex items-center">
            <div 
              className={`w-2 h-2 rounded-full mr-2 ${
                isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
              }`}
            />
            <span className="text-xs text-gray-500">
              {isConnected ? 'Live' : 'Offline'}
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Current Status */}
        <div className={`p-4 rounded-lg ${config.bgColor} border border-opacity-20`}>
          <div className="flex items-center gap-3">
            <span className="text-2xl">{config.icon}</span>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className={`font-semibold ${config.textColor}`}>
                  {config.label}
                </h3>
                <Badge variant="outline" className="text-xs">
                  Order #{orderId}
                </Badge>
              </div>
              <p className="text-sm text-gray-600 mt-1">
                {config.description}
              </p>
            </div>
          </div>
        </div>

        {/* Progress Steps */}
        <div className="space-y-3">
          <h4 className="font-medium text-gray-900 text-sm">Order Progress</h4>
          
          <div className="space-y-2">
            {Object.entries(statusConfig).map(([status, statusInfo], index) => {
              const isCompleted = getStatusOrder(currentStatus) >= getStatusOrder(status);
              const isCurrent = currentStatus === status;
              const isSkipped = currentStatus === 'cancelled' && status !== 'pending' && status !== 'cancelled';

              return (
                <div key={status} className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium border-2 transition-colors ${
                    isSkipped ? 'border-gray-300 text-gray-400 bg-gray-100' :
                    isCompleted ? `${statusInfo.color} border-transparent text-white` :
                    'border-gray-300 text-gray-400 bg-white'
                  }`}>
                    {isSkipped ? '−' : isCompleted ? '✓' : index + 1}
                  </div>
                  
                  <div className="flex-1">
                    <span className={`text-sm ${
                      isSkipped ? 'text-gray-400 line-through' :
                      isCurrent ? statusInfo.textColor + ' font-medium' :
                      isCompleted ? 'text-gray-700' : 'text-gray-400'
                    }`}>
                      {statusInfo.label}
                    </span>
                  </div>

                  {isCurrent && (
                    <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Status History */}
        {statusHistory.length > 0 && (
          <div className="border-t pt-4">
            <h4 className="font-medium text-gray-900 text-sm mb-3">Status History</h4>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {statusHistory.map((status, index) => (
                <div key={index} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      statusConfig[status.status as keyof typeof statusConfig]?.color || 'bg-gray-400'
                    }`}></span>
                    <span className="text-gray-700">
                      {statusConfig[status.status as keyof typeof statusConfig]?.label || status.status}
                    </span>
                  </div>
                  <span className="text-gray-500">
                    {new Date(status.timestamp || status.updated_at).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Additional Status Info */}
        {statusHistory.length > 0 && statusHistory[0].payment_intent_id && (
          <div className="border-t pt-4">
            <div className="text-xs text-gray-500">
              Payment ID: {statusHistory[0].payment_intent_id}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Helper function to determine status order
function getStatusOrder(status: string): number {
  const order = {
    'pending': 1,
    'processing': 2,
    'completed': 3,
    'cancelled': 4,
    'failed': 4
  };
  return order[status as keyof typeof order] || 0;
}

export default OrderStatusTracker;
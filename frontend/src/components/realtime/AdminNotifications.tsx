/**
 * Admin Notifications Component
 * Displays real-time admin notifications using WebSocket
 */

import React, { useState } from 'react';
import { useAdminNotifications } from '../../hooks/useWebSocket';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Bell, X, Check, AlertTriangle, Info, CheckCircle, XCircle } from 'lucide-react';

interface AdminNotificationsProps {
  className?: string;
  maxVisible?: number;
}

const notificationIcons = {
  order_completed: CheckCircle,
  system_alert: AlertTriangle,
  security: XCircle,
  info: Info,
  default: Bell
};

const priorityConfig = {
  low: { color: 'text-gray-500', bgColor: 'bg-gray-50', borderColor: 'border-gray-200' },
  normal: { color: 'text-blue-500', bgColor: 'bg-blue-50', borderColor: 'border-blue-200' },
  high: { color: 'text-orange-500', bgColor: 'bg-orange-50', borderColor: 'border-orange-200' },
  critical: { color: 'text-red-500', bgColor: 'bg-red-50', borderColor: 'border-red-200' }
};

export function AdminNotifications({ 
  className = '', 
  maxVisible = 10 
}: AdminNotificationsProps) {
  const { 
    notifications, 
    unreadCount, 
    markAsRead, 
    isConnected, 
    connectionError 
  } = useAdminNotifications();

  const [isExpanded, setIsExpanded] = useState(false);
  const [dismissedNotifications, setDismissedNotifications] = useState<Set<string>>(new Set());

  const visibleNotifications = notifications
    .filter(n => !dismissedNotifications.has(n.id))
    .slice(0, maxVisible);

  const handleDismiss = (notificationId: string) => {
    setDismissedNotifications(prev => new Set(prev).add(notificationId));
    markAsRead(notificationId);
  };

  const handleMarkAllAsRead = () => {
    markAsRead();
  };

  const getNotificationIcon = (type: string) => {
    const IconComponent = notificationIcons[type as keyof typeof notificationIcons] || notificationIcons.default;
    return IconComponent;
  };

  const formatTimeAgo = (timestamp: string) => {
    const now = new Date();
    const time = new Date(timestamp);
    const diffInMinutes = Math.floor((now.getTime() - time.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    return time.toLocaleDateString();
  };

  if (connectionError) {
    return (
      <Card className={className}>
        <CardContent className="p-4">
          <div className="flex items-center text-red-600">
            <XCircle className="w-4 h-4 mr-2" />
            <span className="text-sm">Failed to connect to notifications</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Bell className="w-5 h-5" />
              Notifications
            </CardTitle>
            {unreadCount > 0 && (
              <Badge variant="destructive" className="text-xs">
                {unreadCount}
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2">
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

            {unreadCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleMarkAllAsRead}
                className="text-xs"
              >
                <Check className="w-3 h-3 mr-1" />
                Mark all read
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {visibleNotifications.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">No notifications</p>
          </div>
        ) : (
          <div className="space-y-0">
            {visibleNotifications.map((notification, index) => {
              const priority = notification.priority || 'normal';
              const config = priorityConfig[priority as keyof typeof priorityConfig];
              const IconComponent = getNotificationIcon(notification.type);
              const isUnread = !notification.read;

              return (
                <div 
                  key={notification.id}
                  className={`border-b last:border-b-0 transition-colors ${
                    isUnread ? 'bg-blue-50/50' : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="p-4">
                    <div className="flex items-start gap-3">
                      <div className={`p-1 rounded-full ${config.bgColor} ${config.borderColor} border`}>
                        <IconComponent className={`w-4 h-4 ${config.color}`} />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className={`text-sm font-medium ${isUnread ? 'text-gray-900' : 'text-gray-700'}`}>
                            {notification.title}
                          </h4>
                          {isUnread && (
                            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                          )}
                        </div>

                        <p className="text-sm text-gray-600 mb-2">
                          {notification.message}
                        </p>

                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs">
                              {notification.type.replace('_', ' ')}
                            </Badge>
                            {priority !== 'normal' && (
                              <Badge 
                                variant={priority === 'critical' ? 'destructive' : 'secondary'}
                                className="text-xs"
                              >
                                {priority}
                              </Badge>
                            )}
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-500">
                              {formatTimeAgo(notification.timestamp)}
                            </span>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDismiss(notification.id)}
                              className="h-6 w-6 p-0"
                            >
                              <X className="w-3 h-3" />
                            </Button>
                          </div>
                        </div>

                        {/* Additional notification data */}
                        {notification.order_id && (
                          <div className="mt-2 text-xs text-gray-500">
                            Order #{notification.order_id}
                            {notification.amount && (
                              <span className="ml-2">${notification.amount}</span>
                            )}
                          </div>
                        )}

                        {notification.affected_services && notification.affected_services.length > 0 && (
                          <div className="mt-2">
                            <div className="text-xs text-gray-500 mb-1">Affected services:</div>
                            <div className="flex flex-wrap gap-1">
                              {notification.affected_services.map((service: string, idx: number) => (
                                <Badge key={idx} variant="outline" className="text-xs">
                                  {service}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Show more button */}
            {notifications.length > maxVisible && (
              <div className="p-3 border-t bg-gray-50">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="w-full text-sm"
                >
                  {isExpanded ? 'Show less' : `Show ${notifications.length - maxVisible} more`}
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default AdminNotifications;
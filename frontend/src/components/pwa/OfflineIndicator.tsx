/**
 * Offline Indicator Component
 * Shows network status and offline capabilities
 */

import React from 'react';
import { useOffline } from '../../hooks/usePWA';
import { Badge } from '../ui/badge';
import { Card, CardContent } from '../ui/card';
import { Wifi, WifiOff, Cloud, CloudOff, RefreshCw } from 'lucide-react';

interface OfflineIndicatorProps {
  className?: string;
  variant?: 'badge' | 'banner' | 'inline';
  showReconnectMessage?: boolean;
}

export function OfflineIndicator({
  className = '',
  variant = 'badge',
  showReconnectMessage = true
}: OfflineIndicatorProps) {
  const { isOnline, wasOffline } = useOffline();

  if (variant === 'badge') {
    return (
      <Badge 
        variant={isOnline ? 'default' : 'destructive'}
        className={`${className} ${isOnline ? 'bg-green-500' : 'bg-red-500'}`}
      >
        {isOnline ? (
          <>
            <Wifi className="w-3 h-3 mr-1" />
            Online
          </>
        ) : (
          <>
            <WifiOff className="w-3 h-3 mr-1" />
            Offline
          </>
        )}
      </Badge>
    );
  }

  if (variant === 'banner' && (!isOnline || wasOffline)) {
    return (
      <div className={`fixed top-0 left-0 right-0 z-40 ${className}`}>
        <div className={`p-2 text-center text-white text-sm ${
          isOnline ? 'bg-green-500' : 'bg-red-500'
        }`}>
          <div className="flex items-center justify-center gap-2">
            {isOnline ? (
              <>
                <Wifi className="w-4 h-4" />
                <span>You're back online!</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4" />
                <span>You're offline. Some features may be limited.</span>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (variant === 'inline') {
    return (
      <Card className={`${isOnline ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'} ${className}`}>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${
              isOnline ? 'bg-green-100' : 'bg-red-100'
            }`}>
              {isOnline ? (
                <Cloud className={`w-5 h-5 ${wasOffline ? 'text-green-600' : 'text-blue-600'}`} />
              ) : (
                <CloudOff className="w-5 h-5 text-red-600" />
              )}
            </div>
            
            <div className="flex-1">
              <h3 className={`font-medium ${
                isOnline ? (wasOffline ? 'text-green-900' : 'text-blue-900') : 'text-red-900'
              }`}>
                {isOnline ? (wasOffline ? 'Connection Restored' : 'Connected') : 'No Internet Connection'}
              </h3>
              
              <p className={`text-sm mt-1 ${
                isOnline ? (wasOffline ? 'text-green-700' : 'text-blue-700') : 'text-red-700'
              }`}>
                {isOnline 
                  ? (wasOffline && showReconnectMessage 
                      ? 'Your connection has been restored. All features are now available.'
                      : 'All features are available and data will sync automatically.'
                    )
                  : 'You can still browse cached content and your changes will sync when reconnected.'
                }
              </p>
              
              {!isOnline && (
                <div className="flex items-center gap-1 mt-2">
                  <RefreshCw className="w-4 h-4 text-red-600" />
                  <span className="text-xs text-red-600">Checking connection...</span>
                </div>
              )}
            </div>
          </div>
          
          {!isOnline && (
            <div className="mt-3 p-3 bg-red-100 rounded-lg">
              <h4 className="text-sm font-medium text-red-900 mb-2">
                Available offline features:
              </h4>
              <ul className="text-xs text-red-800 space-y-1">
                <li>• Browse cached events and tickets</li>
                <li>• View your order history</li>
                <li>• Access downloaded content</li>
                <li>• Continue browsing (limited)</li>
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  return null;
}

export default OfflineIndicator;
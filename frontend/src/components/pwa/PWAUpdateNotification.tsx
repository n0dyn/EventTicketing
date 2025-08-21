/**
 * PWA Update Notification Component
 * Notifies users when a new version of the app is available
 */

import React from 'react';
import { usePWAUpdateNotification } from '../../hooks/usePWA';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { RefreshCw, X, Download } from 'lucide-react';

interface PWAUpdateNotificationProps {
  className?: string;
  variant?: 'banner' | 'toast' | 'inline';
  autoUpdate?: boolean;
}

export function PWAUpdateNotification({
  className = '',
  variant = 'banner',
  autoUpdate = false
}: PWAUpdateNotificationProps) {
  const {
    showUpdateNotification,
    dismissNotification,
    applyUpdate,
    isUpdating
  } = usePWAUpdateNotification();

  React.useEffect(() => {
    if (autoUpdate && showUpdateNotification && !isUpdating) {
      // Auto-update after 5 seconds if enabled
      const timer = setTimeout(() => {
        applyUpdate();
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [autoUpdate, showUpdateNotification, isUpdating, applyUpdate]);

  if (!showUpdateNotification) {
    return null;
  }

  if (variant === 'banner') {
    return (
      <div className={`fixed top-4 left-4 right-4 md:left-auto md:right-4 md:max-w-md z-50 ${className}`}>
        <Card className="shadow-lg border-green-200 bg-green-50">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="bg-green-100 p-2 rounded-lg flex-shrink-0">
                {isUpdating ? (
                  <RefreshCw className="w-5 h-5 text-green-600 animate-spin" />
                ) : (
                  <Download className="w-5 h-5 text-green-600" />
                )}
              </div>
              
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-green-900 text-sm">
                  {isUpdating ? 'Updating App...' : 'Update Available'}
                </h3>
                <p className="text-xs text-green-700 mt-1">
                  {isUpdating 
                    ? 'Please wait while we apply the latest updates'
                    : 'A new version of EventTicketing is ready to install'
                  }
                </p>
                
                {!isUpdating && (
                  <div className="flex gap-2 mt-3">
                    <Button
                      size="sm"
                      onClick={applyUpdate}
                      className="text-xs px-3 py-1 h-auto bg-green-600 hover:bg-green-700"
                      disabled={isUpdating}
                    >
                      <RefreshCw className="w-3 h-3 mr-1" />
                      Update Now
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={dismissNotification}
                      className="text-xs px-3 py-1 h-auto text-green-700 hover:bg-green-100"
                    >
                      Later
                    </Button>
                  </div>
                )}

                {autoUpdate && !isUpdating && (
                  <p className="text-xs text-green-600 mt-2">
                    Auto-updating in 5 seconds...
                  </p>
                )}
              </div>
              
              {!isUpdating && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={dismissNotification}
                  className="p-1 h-auto w-auto flex-shrink-0 text-green-700 hover:bg-green-100"
                >
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (variant === 'toast') {
    return (
      <div className={`fixed bottom-4 right-4 max-w-sm z-50 ${className}`}>
        <Card className="shadow-lg border-green-200 bg-green-50">
          <CardContent className="p-3">
            <div className="flex items-center gap-3">
              {isUpdating ? (
                <RefreshCw className="w-5 h-5 text-green-600 animate-spin flex-shrink-0" />
              ) : (
                <Download className="w-5 h-5 text-green-600 flex-shrink-0" />
              )}
              
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-green-900">
                  {isUpdating ? 'Updating...' : 'New version available!'}
                </p>
                
                {!isUpdating && (
                  <div className="flex gap-2 mt-2">
                    <Button
                      size="sm"
                      onClick={applyUpdate}
                      className="text-xs px-2 py-1 h-auto bg-green-600 hover:bg-green-700"
                    >
                      Update
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={dismissNotification}
                      className="text-xs px-2 py-1 h-auto text-green-700"
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Inline variant
  return (
    <Card className={`border-green-200 bg-green-50 ${className}`}>
      <CardContent className="p-4">
        <div className="flex items-center gap-4">
          <div className="bg-green-100 p-3 rounded-lg">
            {isUpdating ? (
              <RefreshCw className="w-6 h-6 text-green-600 animate-spin" />
            ) : (
              <Download className="w-6 h-6 text-green-600" />
            )}
          </div>
          
          <div className="flex-1">
            <h3 className="font-semibold text-green-900">
              {isUpdating ? 'Updating Application' : 'New Version Available'}
            </h3>
            <p className="text-sm text-green-700 mt-1">
              {isUpdating 
                ? 'Installing the latest updates. The app will reload automatically.'
                : 'A newer version with bug fixes and improvements is ready to install.'
              }
            </p>
            
            {autoUpdate && !isUpdating && (
              <p className="text-xs text-green-600 mt-2">
                Will auto-update in a few seconds...
              </p>
            )}
          </div>
          
          {!isUpdating && (
            <div className="flex flex-col gap-2">
              <Button size="sm" onClick={applyUpdate} className="bg-green-600 hover:bg-green-700">
                <RefreshCw className="w-4 h-4 mr-1" />
                Update
              </Button>
              <Button size="sm" variant="ghost" onClick={dismissNotification} className="text-green-700">
                <X className="w-4 h-4" />
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default PWAUpdateNotification;
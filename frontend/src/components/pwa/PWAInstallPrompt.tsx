/**
 * PWA Install Prompt Component
 * Provides a native-like install prompt for the Progressive Web App
 */

import React from 'react';
import { usePWAInstallPrompt } from '../../hooks/usePWA';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { X, Download, Smartphone, Monitor } from 'lucide-react';

interface PWAInstallPromptProps {
  className?: string;
  variant?: 'banner' | 'modal' | 'inline';
  showFeatures?: boolean;
}

export function PWAInstallPrompt({ 
  className = '',
  variant = 'banner',
  showFeatures = true 
}: PWAInstallPromptProps) {
  const { 
    showInstallPrompt, 
    promptInstall, 
    dismissPrompt,
    isInstallable,
    isInstalled
  } = usePWAInstallPrompt();

  // Don't show if not installable, already installed, or prompt is dismissed
  if (!showInstallPrompt || !isInstallable || isInstalled) {
    return null;
  }

  const handleInstall = async () => {
    await promptInstall();
  };

  const features = [
    { icon: <Smartphone className="w-4 h-4" />, text: 'Works offline' },
    { icon: <Monitor className="w-4 h-4" />, text: 'Native app experience' },
    { icon: <Download className="w-4 h-4" />, text: 'Instant updates' }
  ];

  if (variant === 'banner') {
    return (
      <div className={`fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:max-w-md z-50 ${className}`}>
        <Card className="shadow-lg border-blue-200">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="bg-blue-100 p-2 rounded-lg flex-shrink-0">
                <Download className="w-5 h-5 text-blue-600" />
              </div>
              
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-gray-900 text-sm">
                  Install EventTicketing
                </h3>
                <p className="text-xs text-gray-600 mt-1">
                  Get the full app experience with offline access and instant notifications
                </p>
                
                {showFeatures && (
                  <div className="flex flex-wrap gap-3 mt-2">
                    {features.map((feature, index) => (
                      <div key={index} className="flex items-center gap-1">
                        <span className="text-green-500">{feature.icon}</span>
                        <span className="text-xs text-gray-600">{feature.text}</span>
                      </div>
                    ))}
                  </div>
                )}
                
                <div className="flex gap-2 mt-3">
                  <Button
                    size="sm"
                    onClick={handleInstall}
                    className="text-xs px-3 py-1 h-auto"
                  >
                    Install App
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={dismissPrompt}
                    className="text-xs px-3 py-1 h-auto"
                  >
                    Not now
                  </Button>
                </div>
              </div>
              
              <Button
                size="sm"
                variant="ghost"
                onClick={dismissPrompt}
                className="p-1 h-auto w-auto flex-shrink-0"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (variant === 'modal') {
    return (
      <div className={`fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 ${className}`}>
        <Card className="w-full max-w-md">
          <CardContent className="p-6">
            <div className="text-center">
              <div className="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <Download className="w-8 h-8 text-blue-600" />
              </div>
              
              <h2 className="text-xl font-bold text-gray-900 mb-2">
                Install EventTicketing
              </h2>
              
              <p className="text-gray-600 mb-6">
                Get the best experience with our Progressive Web App. Install now for offline access and instant notifications.
              </p>
              
              {showFeatures && (
                <div className="space-y-3 mb-6">
                  {features.map((feature, index) => (
                    <div key={index} className="flex items-center gap-3">
                      <span className="text-green-500">{feature.icon}</span>
                      <span className="text-sm text-gray-700">{feature.text}</span>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="flex gap-3">
                <Button
                  onClick={handleInstall}
                  className="flex-1"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Install App
                </Button>
                <Button
                  variant="outline"
                  onClick={dismissPrompt}
                  className="flex-1"
                >
                  Maybe Later
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Inline variant
  return (
    <Card className={className}>
      <CardContent className="p-4">
        <div className="flex items-center gap-4">
          <div className="bg-blue-100 p-3 rounded-lg">
            <Download className="w-6 h-6 text-blue-600" />
          </div>
          
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900">
              Install EventTicketing App
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Experience faster loading and offline access
            </p>
            
            {showFeatures && (
              <div className="flex gap-4 mt-2">
                {features.map((feature, index) => (
                  <div key={index} className="flex items-center gap-1">
                    <span className="text-green-500">{feature.icon}</span>
                    <span className="text-xs text-gray-600">{feature.text}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          <div className="flex flex-col gap-2">
            <Button size="sm" onClick={handleInstall}>
              Install
            </Button>
            <Button size="sm" variant="ghost" onClick={dismissPrompt}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default PWAInstallPrompt;
/**
 * Offline Page
 * Displayed when the user is offline and requests a page that's not cached
 */

'use client';

import React from 'react';
import { useOffline } from '../../hooks/usePWA';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { WifiOff, RefreshCw, Home, Calendar, Ticket } from 'lucide-react';
import Link from 'next/link';

export default function OfflinePage() {
  const { isOnline } = useOffline();

  const handleRefresh = () => {
    window.location.reload();
  };

  const availableFeatures = [
    {
      icon: <Calendar className="w-5 h-5" />,
      title: 'Cached Events',
      description: 'Browse previously viewed events',
      href: '/events'
    },
    {
      icon: <Ticket className="w-5 h-5" />,
      title: 'My Tickets',
      description: 'View your purchased tickets',
      href: '/dashboard'
    },
    {
      icon: <Home className="w-5 h-5" />,
      title: 'Home',
      description: 'Return to the main page',
      href: '/'
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Main offline message */}
        <Card className="text-center">
          <CardHeader className="pb-4">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <WifiOff className="w-8 h-8 text-gray-400" />
            </div>
            <CardTitle className="text-xl">You're Offline</CardTitle>
          </CardHeader>
          
          <CardContent className="space-y-4">
            <p className="text-gray-600">
              It looks like you don't have an internet connection right now. 
              Don't worry, you can still access some features!
            </p>
            
            {isOnline && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                <p className="text-green-700 text-sm">
                  ✨ Great! Your connection has been restored.
                </p>
              </div>
            )}
            
            <Button 
              onClick={handleRefresh}
              className="w-full"
              disabled={!isOnline}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              {isOnline ? 'Refresh Page' : 'Checking Connection...'}
            </Button>
          </CardContent>
        </Card>

        {/* Available offline features */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Available Offline</CardTitle>
          </CardHeader>
          
          <CardContent className="space-y-3">
            {availableFeatures.map((feature, index) => (
              <Link key={index} href={feature.href}>
                <div className="flex items-center gap-3 p-3 rounded-lg border hover:bg-gray-50 transition-colors">
                  <div className="bg-blue-100 p-2 rounded-lg">
                    {feature.icon}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900">{feature.title}</h3>
                    <p className="text-sm text-gray-600">{feature.description}</p>
                  </div>
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>

        {/* Offline tips */}
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="p-4">
            <h3 className="font-medium text-blue-900 mb-2">Offline Tips</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• Your data will sync automatically when you're back online</li>
              <li>• Previously viewed content is cached for offline access</li>
              <li>• Some features may be limited without internet</li>
            </ul>
          </CardContent>
        </Card>

        {/* Connection status */}
        <div className="text-center text-sm text-gray-500">
          Status: {isOnline ? (
            <span className="text-green-600 font-medium">Online</span>
          ) : (
            <span className="text-red-600 font-medium">Offline</span>
          )}
        </div>
      </div>
    </div>
  );
}
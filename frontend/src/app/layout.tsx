'use client';

import { ReactNode, useEffect } from 'react';
import { AuthProvider } from '@/context/AuthContext';
import { Toaster } from '@/components/ui/toaster';
import PWAInstallPrompt from '@/components/pwa/PWAInstallPrompt';
import PWAUpdateNotification from '@/components/pwa/PWAUpdateNotification';
import OfflineIndicator from '@/components/pwa/OfflineIndicator';
import MobileNavigation from '@/components/mobile/MobileNavigation';
import MobileHeader from '@/components/mobile/MobileHeader';
// import { performanceOptimization } from '@/lib/performance';
// import { initWebVitals } from '@/lib/web-vitals';
import './globals.css';

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  useEffect(() => {
    // Initialize web vitals collection
    // initWebVitals();

    // Initialize performance monitoring
    // const handleWebVitals = (metric: any) => {
    //   performanceOptimization.monitor.reportWebVitals(metric);
    //   
    //   // Send to analytics in production
    //   if (process.env.NODE_ENV === 'production') {
    //     // Analytics integration would go here
    //     console.log('Web Vitals:', metric);
    //   }
    // };

    // Set up web vitals callback
    // performanceOptimization.monitor.setWebVitalsCallback(handleWebVitals);

    // Cleanup on unmount
    // return () => {
    //   performanceOptimization.monitor.disconnect();
    //   performanceOptimization.memory.cleanup();
    // };
  }, []);

  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover" />
        <meta name="theme-color" content="#3b82f6" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="EventTicketing" />
        
        {/* PWA manifest */}
        <link rel="manifest" href="/manifest.json" />
        
        {/* Icons - removed until icons are created */}
        
        {/* Splash screens removed until assets are created */}
      </head>
      <body className="min-h-screen bg-gray-50">
        <AuthProvider>
          {/* Mobile-first layout */}
          <div className="flex flex-col min-h-screen">
            {/* Mobile header - hidden on desktop */}
            <div className="lg:hidden">
              <MobileHeader />
            </div>
            
            {/* Offline status banner */}
            <OfflineIndicator variant="banner" />
            
            {/* Main content area */}
            <main className="flex-1 pb-16 lg:pb-0">
              {children}
            </main>
            
            {/* Mobile bottom navigation - hidden on desktop */}
            <div className="lg:hidden">
              <MobileNavigation />
            </div>
          </div>
          
          {/* PWA Components */}
          <PWAInstallPrompt />
          <PWAUpdateNotification />
          
          {/* Toast notifications */}
          <Toaster />
        </AuthProvider>
      </body>
    </html>
  );
} 
/**
 * PWA Provider Component
 * Initializes PWA features and provides context to the application
 */

'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { usePWA } from '../../hooks/usePWA';

interface PWAContextType {
  isInstalled: boolean;
  isInstallable: boolean;
  isOnline: boolean;
  hasUpdate: boolean;
  installApp: () => Promise<boolean>;
  updateApp: () => void;
  enableNotifications: () => Promise<boolean>;
}

const PWAContext = createContext<PWAContextType | undefined>(undefined);

export function usePWAContext() {
  const context = useContext(PWAContext);
  if (!context) {
    throw new Error('usePWAContext must be used within a PWAProvider');
  }
  return context;
}

interface PWAProviderProps {
  children: React.ReactNode;
}

export function PWAProvider({ children }: PWAProviderProps) {
  const {
    install,
    serviceWorker,
    notifications,
    offline
  } = usePWA();

  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    // Initialize PWA features when component mounts
    const initializePWA = async () => {
      try {
        // Service worker should already be registered from layout
        console.log('[PWA] Provider initialized');
        setIsInitialized(true);
      } catch (error) {
        console.error('[PWA] Initialization failed:', error);
      }
    };

    if (typeof window !== 'undefined') {
      initializePWA();
    }
  }, []);

  const installApp = async (): Promise<boolean> => {
    return install.install();
  };

  const updateApp = () => {
    serviceWorker.skipWaiting();
  };

  const enableNotifications = async (): Promise<boolean> => {
    const permission = await notifications.requestPermission();
    if (permission === 'granted') {
      const subscription = await notifications.subscribe();
      return !!subscription;
    }
    return false;
  };

  const contextValue: PWAContextType = {
    isInstalled: install.isInstalled,
    isInstallable: install.isInstallable,
    isOnline: offline.isOnline,
    hasUpdate: serviceWorker.hasUpdate,
    installApp,
    updateApp,
    enableNotifications
  };

  return (
    <PWAContext.Provider value={contextValue}>
      {children}
    </PWAContext.Provider>
  );
}

export default PWAProvider;
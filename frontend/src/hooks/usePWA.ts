/**
 * React hooks for PWA functionality
 * Provides easy-to-use hooks for service worker, installation, notifications, and offline features
 */

import { useState, useEffect, useCallback } from 'react';
import { pwaManager, PWAInstallState, ServiceWorkerState, NotificationState, OfflineState } from '../lib/pwa';

// Hook for PWA installation
export function usePWAInstall(): PWAInstallState {
  const [installState, setInstallState] = useState<PWAInstallState>(() => ({
    isInstallable: pwaManager.canInstall(),
    isInstalled: pwaManager.isInstalled(),
    installPrompt: null,
    canInstall: async () => pwaManager.canInstall(),
    install: async () => pwaManager.install()
  }));

  useEffect(() => {
    const unsubscribe = pwaManager.subscribe(() => {
      setInstallState(prev => ({
        ...prev,
        isInstallable: pwaManager.canInstall(),
        isInstalled: pwaManager.isInstalled()
      }));
    });

    return unsubscribe;
  }, []);

  const canInstall = useCallback(async () => {
    return pwaManager.canInstall();
  }, []);

  const install = useCallback(async () => {
    return pwaManager.install();
  }, []);

  return {
    ...installState,
    canInstall,
    install
  };
}

// Hook for Service Worker management
export function useServiceWorker(): ServiceWorkerState {
  const [swState, setSwState] = useState<ServiceWorkerState>({
    isRegistered: false,
    isUpdating: false,
    hasUpdate: false,
    registration: null,
    update: async () => false,
    skipWaiting: () => {}
  });

  useEffect(() => {
    let registration: ServiceWorkerRegistration | null = null;

    const initializeServiceWorker = async () => {
      try {
        registration = await pwaManager.registerServiceWorker();
        
        setSwState(prev => ({
          ...prev,
          isRegistered: !!registration,
          registration
        }));

        if (registration) {
          // Check for updates
          registration.addEventListener('updatefound', () => {
            const newWorker = registration!.installing;
            if (newWorker) {
              setSwState(prev => ({ ...prev, isUpdating: true }));
              
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  setSwState(prev => ({
                    ...prev,
                    hasUpdate: true,
                    isUpdating: false
                  }));
                }
              });
            }
          });
        }
      } catch (error) {
        console.error('Service Worker initialization failed:', error);
        setSwState(prev => ({ ...prev, isRegistered: false }));
      }
    };

    initializeServiceWorker();

    // Listen for SW messages
    const unsubscribe = pwaManager.subscribe(() => {
      setSwState(prev => ({ ...prev, hasUpdate: true }));
    });

    return unsubscribe;
  }, []);

  const update = useCallback(async () => {
    try {
      const success = await pwaManager.updateServiceWorker();
      if (success) {
        setSwState(prev => ({ ...prev, isUpdating: true }));
      }
      return success;
    } catch (error) {
      console.error('Service Worker update failed:', error);
      return false;
    }
  }, []);

  const skipWaiting = useCallback(() => {
    pwaManager.skipWaitingServiceWorker();
    setSwState(prev => ({ ...prev, hasUpdate: false }));
    
    // Reload the page after a short delay
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  }, []);

  return {
    ...swState,
    update,
    skipWaiting
  };
}

// Hook for push notifications
export function usePushNotifications(): NotificationState {
  const [notificationState, setNotificationState] = useState<NotificationState>({
    permission: 'default',
    isSupported: 'Notification' in window && 'serviceWorker' in navigator,
    subscription: null,
    requestPermission: async () => 'denied',
    subscribe: async () => null,
    unsubscribe: async () => false
  });

  useEffect(() => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      setNotificationState(prev => ({
        ...prev,
        permission: Notification.permission,
        isSupported: 'Notification' in window && 'serviceWorker' in navigator
      }));
    }
  }, []);

  const requestPermission = useCallback(async () => {
    try {
      const permission = await pwaManager.requestNotificationPermission();
      setNotificationState(prev => ({ ...prev, permission }));
      return permission;
    } catch (error) {
      console.error('Notification permission request failed:', error);
      return 'denied';
    }
  }, []);

  const subscribe = useCallback(async () => {
    try {
      const subscription = await pwaManager.subscribeToPush();
      setNotificationState(prev => ({ ...prev, subscription }));
      return subscription;
    } catch (error) {
      console.error('Push subscription failed:', error);
      return null;
    }
  }, []);

  const unsubscribe = useCallback(async () => {
    try {
      const success = await pwaManager.unsubscribeFromPush();
      if (success) {
        setNotificationState(prev => ({ ...prev, subscription: null }));
      }
      return success;
    } catch (error) {
      console.error('Push unsubscription failed:', error);
      return false;
    }
  }, []);

  return {
    ...notificationState,
    requestPermission,
    subscribe,
    unsubscribe
  };
}

// Hook for offline functionality
export function useOffline(): OfflineState {
  const [offlineState, setOfflineState] = useState<OfflineState>(() => ({
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
    wasOffline: false
  }));

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleOnline = () => {
      setOfflineState(prev => ({
        isOnline: true,
        wasOffline: !prev.isOnline
      }));
    };

    const handleOffline = () => {
      setOfflineState(prev => ({
        isOnline: false,
        wasOffline: prev.isOnline
      }));
    };

    const removeListener = pwaManager.addNetworkListener((isOnline) => {
      if (isOnline) {
        handleOnline();
      } else {
        handleOffline();
      }
    });

    return removeListener;
  }, []);

  return offlineState;
}

// Hook for offline data storage
export function useOfflineStorage() {
  const storeData = useCallback(async (key: string, data: any) => {
    return pwaManager.storeOfflineData(key, data);
  }, []);

  const getData = useCallback(async (key: string) => {
    return pwaManager.getOfflineData(key);
  }, []);

  const clearData = useCallback(async () => {
    return pwaManager.clearOfflineData();
  }, []);

  return {
    storeData,
    getData,
    clearData
  };
}

// Combined hook for all PWA features
export function usePWA() {
  const install = usePWAInstall();
  const serviceWorker = useServiceWorker();
  const notifications = usePushNotifications();
  const offline = useOffline();
  const storage = useOfflineStorage();

  return {
    install,
    serviceWorker,
    notifications,
    offline,
    storage
  };
}

// Hook for PWA update notification
export function usePWAUpdateNotification() {
  const serviceWorker = useServiceWorker();
  const [showUpdateNotification, setShowUpdateNotification] = useState(false);

  useEffect(() => {
    if (serviceWorker.hasUpdate && !showUpdateNotification) {
      setShowUpdateNotification(true);
    }
  }, [serviceWorker.hasUpdate, showUpdateNotification]);

  const dismissNotification = useCallback(() => {
    setShowUpdateNotification(false);
  }, []);

  const applyUpdate = useCallback(() => {
    serviceWorker.skipWaiting();
    setShowUpdateNotification(false);
  }, [serviceWorker]);

  return {
    showUpdateNotification,
    dismissNotification,
    applyUpdate,
    isUpdating: serviceWorker.isUpdating
  };
}

// Hook for install prompts
export function usePWAInstallPrompt() {
  const { install } = usePWAInstall();
  const [showInstallPrompt, setShowInstallPrompt] = useState(false);
  const [installDismissed, setInstallDismissed] = useState(false);

  useEffect(() => {
    // Check if user has dismissed the install prompt before
    const dismissed = localStorage.getItem('pwa-install-dismissed');
    if (dismissed) {
      setInstallDismissed(true);
    }
  }, []);

  useEffect(() => {
    if (install.isInstallable && !install.isInstalled && !installDismissed) {
      // Show install prompt after a delay
      const timer = setTimeout(() => {
        setShowInstallPrompt(true);
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [install.isInstallable, install.isInstalled, installDismissed]);

  const promptInstall = useCallback(async () => {
    const success = await install.install();
    if (success) {
      setShowInstallPrompt(false);
    }
    return success;
  }, [install]);

  const dismissPrompt = useCallback(() => {
    setShowInstallPrompt(false);
    setInstallDismissed(true);
    localStorage.setItem('pwa-install-dismissed', 'true');
  }, []);

  return {
    showInstallPrompt,
    promptInstall,
    dismissPrompt,
    isInstallable: install.isInstallable,
    isInstalled: install.isInstalled
  };
}
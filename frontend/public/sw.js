// Service Worker for EventTicketing PWA
// Provides offline functionality, caching, and push notifications

const CACHE_NAME = 'eventtickets-v1.0.0';
const OFFLINE_CACHE_NAME = 'eventtickets-offline-v1';

// Assets to cache for offline functionality
const STATIC_ASSETS = [
  '/',
  '/events',
  '/auth/login',
  '/auth/register',
  '/offline',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png'
];

// API endpoints to cache for offline access
const API_CACHE_PATTERNS = [
  '/api/v1/events/public',
  '/api/v1/auth/me'
];

// Network-first resources (always try network first)
const NETWORK_FIRST_PATTERNS = [
  '/api/v1/orders',
  '/api/v1/payments',
  '/ws/'
];

// Cache-first resources (offline-friendly)
const CACHE_FIRST_PATTERNS = [
  '/_next/static/',
  '/images/',
  '/icons/',
  '.js',
  '.css',
  '.woff2',
  '.png',
  '.jpg',
  '.jpeg',
  '.svg'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS);
    }).then(() => {
      // Skip waiting to activate immediately
      return self.skipWaiting();
    }).catch((error) => {
      console.error('[SW] Failed to cache static assets:', error);
    })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== OFFLINE_CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      // Take control of all clients immediately
      return self.clients.claim();
    })
  );
});

// Fetch event - handle requests with caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension requests
  if (url.protocol === 'chrome-extension:') {
    return;
  }

  // Handle different request types with appropriate strategies
  if (isNetworkFirst(request)) {
    event.respondWith(networkFirstStrategy(request));
  } else if (isCacheFirst(request)) {
    event.respondWith(cacheFirstStrategy(request));
  } else {
    event.respondWith(staleWhileRevalidateStrategy(request));
  }
});

// Network-first strategy (for real-time data)
async function networkFirstStrategy(request) {
  try {
    const networkResponse = await fetch(request);
    
    // Cache successful API responses
    if (networkResponse.ok && isApiRequest(request)) {
      const cache = await caches.open(CACHE_NAME);
      await cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);
    
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline');
    }
    
    throw error;
  }
}

// Cache-first strategy (for static assets)
async function cacheFirstStrategy(request) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      await cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('[SW] Cache-first strategy failed:', error);
    throw error;
  }
}

// Stale-while-revalidate strategy (for balanced approach)
async function staleWhileRevalidateStrategy(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);
  
  // Fetch from network in background
  const networkPromise = fetch(request).then((response) => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => {
    // Network failed, but we might have cached version
    return null;
  });
  
  // Return cached version immediately if available
  if (cachedResponse) {
    return cachedResponse;
  }
  
  // Wait for network if no cached version
  return networkPromise || caches.match('/offline');
}

// Helper functions
function isNetworkFirst(request) {
  return NETWORK_FIRST_PATTERNS.some(pattern => request.url.includes(pattern));
}

function isCacheFirst(request) {
  return CACHE_FIRST_PATTERNS.some(pattern => request.url.includes(pattern));
}

function isApiRequest(request) {
  return request.url.includes('/api/');
}

// Background Sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);
  
  if (event.tag === 'background-sync-orders') {
    event.waitUntil(syncPendingOrders());
  }
  
  if (event.tag === 'background-sync-analytics') {
    event.waitUntil(syncAnalyticsData());
  }
});

// Sync pending orders when back online
async function syncPendingOrders() {
  try {
    console.log('[SW] Syncing pending orders...');
    
    // Get pending orders from IndexedDB
    const db = await openIndexedDB();
    const pendingOrders = await getPendingOrders(db);
    
    for (const order of pendingOrders) {
      try {
        const response = await fetch('/api/v1/orders', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': order.authToken
          },
          body: JSON.stringify(order.data)
        });
        
        if (response.ok) {
          await removePendingOrder(db, order.id);
          console.log('[SW] Successfully synced order:', order.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync order:', order.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Background sync failed:', error);
  }
}

// Sync analytics data
async function syncAnalyticsData() {
  try {
    console.log('[SW] Syncing analytics data...');
    
    const db = await openIndexedDB();
    const analyticsEvents = await getPendingAnalytics(db);
    
    if (analyticsEvents.length > 0) {
      const response = await fetch('/api/v1/analytics/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ events: analyticsEvents })
      });
      
      if (response.ok) {
        await clearPendingAnalytics(db);
        console.log('[SW] Successfully synced analytics data');
      }
    }
  } catch (error) {
    console.error('[SW] Analytics sync failed:', error);
  }
}

// Push notifications
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');
  
  const options = {
    body: 'You have new updates!',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    vibrate: [200, 100, 200],
    tag: 'eventtickets-notification',
    actions: [
      {
        action: 'view',
        title: 'View',
        icon: '/icons/view-action.png'
      },
      {
        action: 'dismiss',
        title: 'Dismiss',
        icon: '/icons/dismiss-action.png'
      }
    ],
    data: {
      url: '/',
      timestamp: Date.now()
    }
  };
  
  if (event.data) {
    try {
      const payload = event.data.json();
      options.body = payload.body || options.body;
      options.title = payload.title;
      options.data.url = payload.url || options.data.url;
      
      if (payload.actions) {
        options.actions = payload.actions;
      }
    } catch (error) {
      console.error('[SW] Failed to parse push payload:', error);
    }
  }
  
  event.waitUntil(
    self.registration.showNotification(options.title || 'EventTicketing', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.notification.tag);
  
  event.notification.close();
  
  const action = event.action;
  const data = event.notification.data;
  
  if (action === 'dismiss') {
    return;
  }
  
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clients) => {
      // Check if app is already open
      for (const client of clients) {
        if (client.url.includes(data.url) && 'focus' in client) {
          return client.focus();
        }
      }
      
      // Open new window/tab
      if (clients.openWindow) {
        return clients.openWindow(data.url);
      }
    })
  );
});

// IndexedDB helpers for offline data storage
async function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('EventTicketsDB', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      
      if (!db.objectStoreNames.contains('pendingOrders')) {
        db.createObjectStore('pendingOrders', { keyPath: 'id' });
      }
      
      if (!db.objectStoreNames.contains('analyticsEvents')) {
        db.createObjectStore('analyticsEvents', { keyPath: 'id' });
      }
    };
  });
}

async function getPendingOrders(db) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['pendingOrders'], 'readonly');
    const store = transaction.objectStore('pendingOrders');
    const request = store.getAll();
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

async function removePendingOrder(db, orderId) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['pendingOrders'], 'readwrite');
    const store = transaction.objectStore('pendingOrders');
    const request = store.delete(orderId);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

async function getPendingAnalytics(db) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['analyticsEvents'], 'readonly');
    const store = transaction.objectStore('analyticsEvents');
    const request = store.getAll();
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

async function clearPendingAnalytics(db) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['analyticsEvents'], 'readwrite');
    const store = transaction.objectStore('analyticsEvents');
    const request = store.clear();
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

// Message handler for communication with main app
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);
  
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data.type === 'CACHE_URLS') {
    event.waitUntil(
      caches.open(CACHE_NAME).then((cache) => {
        return cache.addAll(event.data.urls);
      })
    );
  }
});
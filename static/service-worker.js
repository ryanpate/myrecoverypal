// MyRecoveryPal Service Worker
// Version 2.1 - Enhanced caching and offline support

const CACHE_VERSION = 'myrecoverypal-v13';
const CACHE_NAMES = {
  static: `${CACHE_VERSION}-static`,
  dynamic: `${CACHE_VERSION}-dynamic`,
  images: `${CACHE_VERSION}-images`
};

// Resources to cache immediately on install
const STATIC_CACHE_URLS = [
  '/',
  '/offline/',
  '/static/css/main.css',
  '/static/images/logo.svg',
  '/static/images/favicon_192.png',
  '/static/images/favicon_512.png'
];

// Maximum number of items in dynamic cache
const DYNAMIC_CACHE_LIMIT = 50;
const IMAGE_CACHE_LIMIT = 100;

// Install event - cache static resources
self.addEventListener('install', event => {
  console.log('[ServiceWorker] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAMES.static)
      .then(cache => {
        console.log('[ServiceWorker] Caching static assets');
        return cache.addAll(STATIC_CACHE_URLS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[ServiceWorker] Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(cacheName => {
            // Delete old versions of caches
            return cacheName.startsWith('myrecoverypal-') &&
                   !Object.values(CACHE_NAMES).includes(cacheName);
          })
          .map(cacheName => {
            console.log('[ServiceWorker] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          })
      );
    })
    .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache with network fallback
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip Chrome extensions and other non-http(s) requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Skip admin pages
  if (url.pathname.startsWith('/admin/')) {
    return;
  }

  event.respondWith(
    caches.match(request)
      .then(cachedResponse => {
        // Return cached response if found
        if (cachedResponse) {
          // Update cache in background for HTML pages
          if (request.destination === 'document') {
            event.waitUntil(updateCache(request));
          }
          return cachedResponse;
        }

        // Not in cache, fetch from network
        return fetch(request)
          .then(response => {
            // Don't cache if not a valid response
            if (!response || response.status !== 200 || response.type === 'error') {
              return response;
            }

            // Clone the response
            const responseToCache = response.clone();

            // Cache based on content type
            caches.open(getCacheName(request))
              .then(cache => {
                cache.put(request, responseToCache);
                // Limit cache size
                limitCacheSize(getCacheName(request), getCacheLimit(request));
              });

            return response;
          })
          .catch(error => {
            console.log('[ServiceWorker] Fetch failed:', error);
            // Return offline page for navigation requests
            if (request.destination === 'document') {
              return caches.match('/offline/');
            }
            // Return placeholder for images
            if (request.destination === 'image') {
              return caches.match('/static/images/favicon_192.png');
            }
          });
      })
  );
});

// Helper: Update cache in background
async function updateCache(request) {
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      const cache = await caches.open(CACHE_NAMES.dynamic);
      cache.put(request, response);
    }
  } catch (error) {
    console.log('[ServiceWorker] Background update failed:', error);
  }
}

// Helper: Get appropriate cache name based on request
function getCacheName(request) {
  if (request.destination === 'image') {
    return CACHE_NAMES.images;
  }
  if (STATIC_CACHE_URLS.some(url => request.url.includes(url))) {
    return CACHE_NAMES.static;
  }
  return CACHE_NAMES.dynamic;
}

// Helper: Get cache size limit based on request
function getCacheLimit(request) {
  if (request.destination === 'image') {
    return IMAGE_CACHE_LIMIT;
  }
  return DYNAMIC_CACHE_LIMIT;
}

// Helper: Limit cache size
async function limitCacheSize(cacheName, maxItems) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();

  if (keys.length > maxItems) {
    // Delete oldest items (FIFO)
    const itemsToDelete = keys.slice(0, keys.length - maxItems);
    await Promise.all(itemsToDelete.map(key => cache.delete(key)));
  }
}

// Handle messages from clients
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => caches.delete(cacheName))
        );
      })
    );
  }
});

// Background sync for offline actions (future enhancement)
self.addEventListener('sync', event => {
  console.log('[ServiceWorker] Background sync:', event.tag);
  if (event.tag === 'sync-posts') {
    event.waitUntil(syncPosts());
  }
});

// Placeholder for background sync function
async function syncPosts() {
  console.log('[ServiceWorker] Syncing posts...');
  // Implementation for syncing offline posts when back online
}

// Push notification handler with permission check
self.addEventListener('push', event => {
  console.log('[ServiceWorker] Push received');

  // Check if we have notification permission
  if (Notification.permission !== 'granted') {
    console.log('[ServiceWorker] Notification permission not granted');
    return;
  }

  let notificationTitle = 'MyRecoveryPal';
  let notificationOptions = {
    body: 'New update available',
    icon: '/static/images/favicon_192.png',
    badge: '/static/images/favicon_192.png',
    vibrate: [200, 100, 200],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'View',
        icon: '/static/images/favicon_192.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/static/images/favicon_192.png'
      }
    ]
  };

  // Parse push event data if available
  if (event.data) {
    try {
      const data = event.data.json();
      notificationTitle = data.title || notificationTitle;
      notificationOptions.body = data.body || notificationOptions.body;
      notificationOptions.data = { ...notificationOptions.data, ...data };
    } catch (e) {
      // If not JSON, use text
      notificationOptions.body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(notificationTitle, notificationOptions)
      .catch(error => {
        console.error('[ServiceWorker] Error showing notification:', error);
      })
  );
});

// Notification click handler
self.addEventListener('notificationclick', event => {
  console.log('[ServiceWorker] Notification clicked');
  event.notification.close();

  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(windowClients => {
        // Check if there's already a window open
        for (let client of windowClients) {
          if (client.url === urlToOpen && 'focus' in client) {
            return client.focus();
          }
        }
        // If no window is open, open a new one
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

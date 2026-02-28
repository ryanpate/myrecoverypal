/**
 * Capacitor Offline Mode
 * Provides IndexedDB caching, a write queue for offline mutations,
 * and network-status detection when running inside Capacitor.
 * Exits immediately in browser -- zero impact on web.
 */
(function() {
    'use strict';

    // Only run inside Capacitor native shell
    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) {
        return;
    }

    // ========================================
    // 1. IndexedDB Setup
    // ========================================
    var DB_NAME = 'mrp_offline';
    var DB_VERSION = 1;
    var _dbInstance = null;

    /**
     * Open (or return cached) IndexedDB instance.
     * Creates object stores on first open / version upgrade.
     */
    function openDB() {
        if (_dbInstance) {
            return Promise.resolve(_dbInstance);
        }
        return new Promise(function(resolve, reject) {
            var request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onupgradeneeded = function(event) {
                var db = event.target.result;
                if (!db.objectStoreNames.contains('posts')) {
                    db.createObjectStore('posts', { keyPath: 'id' });
                }
                if (!db.objectStoreNames.contains('journal')) {
                    db.createObjectStore('journal', { keyPath: 'id' });
                }
                if (!db.objectStoreNames.contains('checkins')) {
                    db.createObjectStore('checkins', { keyPath: 'id', autoIncrement: true });
                }
                if (!db.objectStoreNames.contains('write_queue')) {
                    db.createObjectStore('write_queue', { keyPath: 'id', autoIncrement: true });
                }
                if (!db.objectStoreNames.contains('meta')) {
                    db.createObjectStore('meta', { keyPath: 'key' });
                }
            };

            request.onsuccess = function(event) {
                _dbInstance = event.target.result;
                // Clear cached reference if the database is closed unexpectedly
                _dbInstance.onclose = function() { _dbInstance = null; };
                resolve(_dbInstance);
            };

            request.onerror = function(event) {
                reject(event.target.error);
            };
        });
    }

    /**
     * Helper that opens the DB, creates a transaction on `storeName`
     * with the given `mode`, calls `callback(store)`, and resolves
     * when the transaction completes.
     */
    function storeOp(storeName, mode, callback) {
        return openDB().then(function(db) {
            return new Promise(function(resolve, reject) {
                var tx = db.transaction(storeName, mode);
                var store = tx.objectStore(storeName);
                var result = callback(store);

                tx.oncomplete = function() {
                    resolve(result);
                };
                tx.onerror = function(event) {
                    reject(event.target.error);
                };
                tx.onabort = function(event) {
                    reject(event.target.error || new Error('Transaction aborted'));
                };
            });
        });
    }

    // ========================================
    // 2. Offline Detection + Banner
    // ========================================
    var offlineBanner = document.querySelector('.offline-banner');
    var _isOnline = navigator.onLine;

    function showOfflineBanner() {
        if (offlineBanner) {
            offlineBanner.textContent = "You're offline \u2014 changes will sync when connected";
            offlineBanner.style.display = 'block';
        }
        document.body.classList.add('offline');
    }

    function hideOfflineBanner() {
        if (offlineBanner) {
            offlineBanner.style.display = 'none';
        }
        document.body.classList.remove('offline');
    }

    window.addEventListener('offline', function() {
        _isOnline = false;
        showOfflineBanner();
    });

    window.addEventListener('online', function() {
        _isOnline = true;
        hideOfflineBanner();
        flushWriteQueue();
    });

    // Listen for app state changes (foreground/background)
    if (window.Capacitor.Plugins && window.Capacitor.Plugins.App) {
        window.Capacitor.Plugins.App.addListener('appStateChange', function(state) {
            if (state.isActive && navigator.onLine) {
                _isOnline = true;
                hideOfflineBanner();
                flushWriteQueue();
            }
        });
    }

    // Set initial state
    if (!navigator.onLine) {
        showOfflineBanner();
    }

    // ========================================
    // 3. Cache Social Feed Posts
    // ========================================

    /**
     * Store an array of post objects in the `posts` store.
     * Uses put() so existing posts are updated.
     */
    function cachePosts(posts) {
        if (!posts || !posts.length) return Promise.resolve();
        return storeOp('posts', 'readwrite', function(store) {
            for (var i = 0; i < posts.length; i++) {
                store.put(posts[i]);
            }
        });
    }

    /**
     * Retrieve up to `limit` posts from IndexedDB, ordered by id descending.
     */
    function getCachedPosts(limit) {
        limit = limit || 50;
        return openDB().then(function(db) {
            return new Promise(function(resolve, reject) {
                var tx = db.transaction('posts', 'readonly');
                var store = tx.objectStore('posts');
                var results = [];
                var request = store.openCursor(null, 'prev');

                request.onsuccess = function(event) {
                    var cursor = event.target.result;
                    if (cursor && results.length < limit) {
                        results.push(cursor.value);
                        cursor.continue();
                    }
                    // When cursor is null or we have enough results,
                    // oncomplete will fire and we resolve.
                };

                request.onerror = function(event) {
                    reject(event.target.error);
                };

                tx.oncomplete = function() {
                    resolve(results);
                };

                tx.onerror = function(event) {
                    reject(event.target.error);
                };
            });
        });
    }

    // ========================================
    // 4. Cache Journal Entries
    // ========================================

    /**
     * Store an array of journal entry objects. Uses put() for upsert.
     */
    function cacheJournalEntries(entries) {
        if (!entries || !entries.length) return Promise.resolve();
        return storeOp('journal', 'readwrite', function(store) {
            for (var i = 0; i < entries.length; i++) {
                store.put(entries[i]);
            }
        });
    }

    /**
     * Retrieve all cached journal entries, ordered by id descending.
     */
    function getCachedJournalEntries() {
        return openDB().then(function(db) {
            return new Promise(function(resolve, reject) {
                var tx = db.transaction('journal', 'readonly');
                var store = tx.objectStore('journal');
                var results = [];
                var request = store.openCursor(null, 'prev');

                request.onsuccess = function(event) {
                    var cursor = event.target.result;
                    if (cursor) {
                        results.push(cursor.value);
                        cursor.continue();
                    }
                };

                request.onerror = function(event) {
                    reject(event.target.error);
                };

                tx.oncomplete = function() {
                    resolve(results);
                };

                tx.onerror = function(event) {
                    reject(event.target.error);
                };
            });
        });
    }

    // ========================================
    // 5. Write Queue
    // ========================================

    /**
     * Extract CSRF token from document.cookie.
     */
    function getCSRFToken() {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.indexOf('csrftoken=') === 0) {
                return cookie.substring('csrftoken='.length);
            }
        }
        return '';
    }

    /**
     * Queue a write action for later sync.
     * @param {Object} action - { url, method, body, type }
     */
    function queueWrite(action) {
        var entry = {
            url: action.url,
            method: action.method || 'POST',
            body: action.body || null,
            type: action.type || 'unknown',
            queued_at: new Date().toISOString()
        };
        return storeOp('write_queue', 'readwrite', function(store) {
            store.add(entry);
        });
    }

    /**
     * Flush all queued writes by replaying them via fetch().
     * Successful writes are removed from the queue; failures remain.
     */
    var _flushing = false;

    function flushWriteQueue() {
        if (!navigator.onLine || _flushing) return Promise.resolve();
        _flushing = true;

        return openDB().then(function(db) {
            return new Promise(function(resolve, reject) {
                var tx = db.transaction('write_queue', 'readonly');
                var store = tx.objectStore('write_queue');
                var getAll = store.getAll();

                getAll.onsuccess = function() {
                    var items = getAll.result || [];
                    resolve(items);
                };

                getAll.onerror = function(event) {
                    reject(event.target.error);
                };
            });
        }).then(function(items) {
            if (!items.length) {
                _flushing = false;
                return;
            }

            var csrfToken = getCSRFToken();

            // Process items sequentially to preserve order
            var chain = Promise.resolve();
            items.forEach(function(item) {
                chain = chain.then(function() {
                    var fetchOptions = {
                        method: item.method,
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        credentials: 'same-origin'
                    };
                    if (item.body) {
                        fetchOptions.body = typeof item.body === 'string'
                            ? item.body
                            : JSON.stringify(item.body);
                    }

                    return _originalFetch(item.url, fetchOptions).then(function(response) {
                        if (response.ok) {
                            // Remove from queue on success
                            return storeOp('write_queue', 'readwrite', function(store) {
                                store.delete(item.id);
                            });
                        }
                        // Non-ok response -- keep in queue for retry
                    }).catch(function() {
                        // Network error -- keep in queue for retry
                    });
                });
            });

            return chain.then(function() {
                _flushing = false;
            });
        }).catch(function() {
            _flushing = false;
        });
    }

    // ========================================
    // 6. Fetch Interceptor
    // ========================================
    var _originalFetch = window.fetch;

    window.fetch = function(url, options) {
        var urlStr = typeof url === 'string' ? url : (url && url.url ? url.url : '');
        var method = (options && options.method) ? options.method.toUpperCase() : 'GET';

        // GET requests to social feed posts endpoint
        if (method === 'GET' && urlStr.indexOf('/social-feed/posts/') !== -1) {
            if (!navigator.onLine) {
                // Serve from IndexedDB when offline
                return getCachedPosts(50).then(function(posts) {
                    return new Response(JSON.stringify({ results: posts, cached: true }), {
                        status: 200,
                        headers: { 'Content-Type': 'application/json' }
                    });
                });
            }

            // Online: fetch from server, cache the response, and return it
            return _originalFetch(url, options).then(function(response) {
                // Clone so we can read the body and still return the original
                var clone = response.clone();
                clone.json().then(function(data) {
                    var posts = data.results || data;
                    if (Array.isArray(posts)) {
                        cachePosts(posts);
                    }
                }).catch(function() {
                    // Ignore JSON parse errors
                });
                return response;
            });
        }

        // Non-GET requests when offline: queue the write
        if (method !== 'GET' && !navigator.onLine) {
            var body = null;
            if (options && options.body) {
                try {
                    body = JSON.parse(options.body);
                } catch (e) {
                    body = options.body;
                }
            }
            queueWrite({
                url: urlStr,
                method: method,
                body: body,
                type: 'fetch_intercepted'
            });
            return Promise.resolve(new Response(JSON.stringify({ queued: true }), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            }));
        }

        // All other requests: pass through
        return _originalFetch(url, options);
    };

    // ========================================
    // 7. Public API
    // ========================================
    window.MRPOffline = {
        cachePosts: cachePosts,
        getCachedPosts: getCachedPosts,
        cacheJournalEntries: cacheJournalEntries,
        getCachedJournalEntries: getCachedJournalEntries,
        queueWrite: queueWrite,
        flushWriteQueue: flushWriteQueue,
        isOnline: function() { return navigator.onLine; }
    };

})();

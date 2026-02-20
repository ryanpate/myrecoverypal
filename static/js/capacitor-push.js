/**
 * Capacitor Push Notification Bridge
 * Handles push notification registration and deep linking when running inside Capacitor native app.
 * Only activates on native platforms (iOS/Android) - no-op in browser.
 */
(function() {
    'use strict';

    // Only run inside Capacitor native shell
    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) {
        return;
    }

    var PushNotifications = window.Capacitor.Plugins.PushNotifications;
    if (!PushNotifications) {
        console.warn('[CapPush] PushNotifications plugin not available');
        return;
    }

    /**
     * Get CSRF token from cookie for Django POST requests.
     */
    function getCSRFToken() {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.startsWith('csrftoken=')) {
                return cookie.substring('csrftoken='.length);
            }
        }
        return '';
    }

    /**
     * Detect platform (ios or android).
     */
    function getPlatform() {
        var info = window.Capacitor.getPlatform();
        if (info === 'ios') return 'ios';
        if (info === 'android') return 'android';
        return 'web';
    }

    /**
     * Register device token with the Django backend.
     */
    function registerTokenWithServer(token) {
        var csrfToken = getCSRFToken();
        if (!csrfToken) {
            console.warn('[CapPush] No CSRF token available, retrying in 2s');
            setTimeout(function() { registerTokenWithServer(token); }, 2000);
            return;
        }

        fetch('/accounts/api/device-token/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                token: token,
                platform: getPlatform(),
                device_name: window.Capacitor.getPlatform() + ' app'
            })
        })
        .then(function(response) {
            if (response.ok) {
                console.log('[CapPush] Token registered with server');
            } else {
                console.error('[CapPush] Token registration failed:', response.status);
            }
        })
        .catch(function(err) {
            console.error('[CapPush] Token registration error:', err);
        });
    }

    /**
     * Initialize push notifications.
     */
    function initPush() {
        // Check permission status first
        PushNotifications.checkPermissions().then(function(result) {
            if (result.receive === 'prompt') {
                PushNotifications.requestPermissions().then(function(permResult) {
                    if (permResult.receive === 'granted') {
                        registerForPush();
                    }
                });
            } else if (result.receive === 'granted') {
                registerForPush();
            }
        });
    }

    function registerForPush() {
        PushNotifications.register();

        // Token received - send to server
        PushNotifications.addListener('registration', function(token) {
            console.log('[CapPush] Token received:', token.value.substring(0, 20) + '...');
            registerTokenWithServer(token.value);
        });

        // Registration error
        PushNotifications.addListener('registrationError', function(error) {
            console.error('[CapPush] Registration error:', error);
        });

        // Notification received while app is in foreground
        PushNotifications.addListener('pushNotificationReceived', function(notification) {
            console.log('[CapPush] Foreground notification:', notification.title);
        });

        // Notification tapped - handle deep linking
        PushNotifications.addListener('pushNotificationActionPerformed', function(action) {
            var data = action.notification.data;
            if (data && data.url) {
                // Navigate to the relevant page
                window.location.href = data.url;
            } else if (data && data.type) {
                // Route based on notification type
                var routes = {
                    'follow': '/accounts/notifications/',
                    'like': '/accounts/social-feed/',
                    'comment': '/accounts/social-feed/',
                    'message': '/accounts/messages/',
                    'pal_request': '/accounts/pals/',
                    'sponsor_request': '/accounts/sponsors/',
                    'group_post': '/accounts/groups/',
                    'challenge': '/accounts/challenges/',
                    'checkin_reminder': '/accounts/daily-checkin/'
                };
                var route = routes[data.type] || '/accounts/notifications/';
                window.location.href = route;
            }
        });
    }

    // Wait for page to fully load before initializing
    if (document.readyState === 'complete') {
        initPush();
    } else {
        window.addEventListener('load', initPush);
    }
})();

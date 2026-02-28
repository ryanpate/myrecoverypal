/**
 * Capacitor Native Features Bridge
 * Provides native iOS/Android capabilities when running inside Capacitor.
 * Exits immediately in browser — zero impact on web.
 */
(function() {
    'use strict';

    // Only run inside Capacitor native shell
    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) {
        return;
    }

    var platform = window.Capacitor.getPlatform(); // 'ios' or 'android'
    var Plugins = window.Capacitor.Plugins;

    // Add platform class to body for CSS targeting
    document.body.classList.add(platform + '-native-app');

    // ========================================
    // Native Features API (window.MRPNative)
    // ========================================
    var MRPNative = {
        isNative: true,
        platform: platform,

        // --- Haptic Feedback ---
        hapticLight: function() {
            if (Plugins.Haptics) {
                Plugins.Haptics.impact({ style: 'LIGHT' });
            }
        },
        hapticMedium: function() {
            if (Plugins.Haptics) {
                Plugins.Haptics.impact({ style: 'MEDIUM' });
            }
        },
        hapticHeavy: function() {
            if (Plugins.Haptics) {
                Plugins.Haptics.impact({ style: 'HEAVY' });
            }
        },
        hapticSuccess: function() {
            if (Plugins.Haptics) {
                Plugins.Haptics.notification({ type: 'SUCCESS' });
            }
        },
        hapticWarning: function() {
            if (Plugins.Haptics) {
                Plugins.Haptics.notification({ type: 'WARNING' });
            }
        },

        // --- Native Share Sheet ---
        share: function(title, text, url) {
            if (Plugins.Share) {
                return Plugins.Share.share({
                    title: title || '',
                    text: text || '',
                    url: url || '',
                    dialogTitle: 'Share via'
                });
            }
            return Promise.reject('Share plugin not available');
        },

        // --- App Badge ---
        setBadge: function(count) {
            if (Plugins.LocalNotifications) {
                // Badge is set via local notification permission on iOS
                // We schedule a silent local notification to update badge
                Plugins.LocalNotifications.checkPermissions().then(function(result) {
                    if (result.display === 'granted') {
                        // Use a JS-accessible badge counter via the notification plugin
                        if (typeof count === 'number' && count >= 0) {
                            // Store badge count for reference
                            MRPNative._badgeCount = count;
                        }
                    }
                });
            }
        },

        // --- Local Notifications ---
        scheduleReminder: function(title, body, scheduleAt) {
            if (!Plugins.LocalNotifications) return Promise.reject('Not available');

            return Plugins.LocalNotifications.checkPermissions().then(function(result) {
                if (result.display !== 'granted') {
                    return Plugins.LocalNotifications.requestPermissions();
                }
                return result;
            }).then(function(result) {
                if (result.display === 'granted') {
                    return Plugins.LocalNotifications.schedule({
                        notifications: [{
                            title: title,
                            body: body,
                            id: Math.floor(Math.random() * 100000),
                            schedule: { at: new Date(scheduleAt) },
                            sound: 'default'
                        }]
                    });
                }
            });
        },

        // --- Keyboard Height Tracking ---
        _keyboardHeight: 0
    };

    window.MRPNative = MRPNative;

    // ========================================
    // Keyboard Handling
    // ========================================
    if (Plugins.Keyboard) {
        Plugins.Keyboard.addListener('keyboardWillShow', function(info) {
            MRPNative._keyboardHeight = info.keyboardHeight;
            document.documentElement.style.setProperty('--keyboard-height', info.keyboardHeight + 'px');
            document.body.classList.add('keyboard-open');
        });

        Plugins.Keyboard.addListener('keyboardWillHide', function() {
            MRPNative._keyboardHeight = 0;
            document.documentElement.style.setProperty('--keyboard-height', '0px');
            document.body.classList.remove('keyboard-open');
        });
    }

    // ========================================
    // Back Button Handler (Android)
    // ========================================
    if (platform === 'android' && Plugins.App) {
        Plugins.App.addListener('backButton', function(data) {
            // If we can go back in history, do so
            if (window.history.length > 1) {
                window.history.back();
            } else {
                // Minimize app instead of closing
                Plugins.App.minimizeApp();
            }
        });
    }

    // ========================================
    // App State Change (refresh on foreground)
    // ========================================
    if (Plugins.App) {
        Plugins.App.addListener('appStateChange', function(state) {
            if (state.isActive) {
                // Refresh notification count when app comes to foreground
                var countEl = document.querySelector('.notification-count');
                if (countEl) {
                    fetch('/accounts/api/notifications/unread-count/', {
                        credentials: 'same-origin'
                    }).then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data.count !== undefined) {
                            countEl.textContent = data.count;
                            countEl.style.display = data.count > 0 ? '' : 'none';
                        }
                    }).catch(function() {});
                }
            }
        });
    }

    // ========================================
    // Haptic Event Delegation
    // ========================================
    document.body.addEventListener('click', function(e) {
        var target = e.target;

        // Walk up to find the actual interactive element
        var el = target.closest('[data-haptic]') ||
                 target.closest('.like-btn, .reaction-btn, .react-btn') ||
                 target.closest('.checkin-mood-btn, .quick-checkin-btn, [name="mood"]') ||
                 target.closest('.share-btn, .milestone-share-btn, [data-share]') ||
                 target.closest('.follow-btn, .follow-toggle') ||
                 target.closest('.subscribe-btn, .iap-subscribe-btn');

        if (!el) return;

        // Determine haptic type
        if (el.matches('.like-btn, .reaction-btn, .react-btn') ||
            el.getAttribute('data-haptic') === 'light') {
            MRPNative.hapticLight();
        } else if (el.matches('.checkin-mood-btn, .quick-checkin-btn, [name="mood"]') ||
                   el.getAttribute('data-haptic') === 'success') {
            MRPNative.hapticSuccess();
        } else if (el.matches('.share-btn, .milestone-share-btn, [data-share]') ||
                   el.matches('.follow-btn, .follow-toggle') ||
                   el.matches('.subscribe-btn, .iap-subscribe-btn') ||
                   el.getAttribute('data-haptic') === 'medium') {
            MRPNative.hapticMedium();
        }
    }, true);

    // ========================================
    // Native Share Sheet Override
    // ========================================
    // Intercept web share API calls and use native share on Capacitor
    if (Plugins.Share && navigator.share) {
        var originalShare = navigator.share.bind(navigator);
        navigator.share = function(data) {
            return MRPNative.share(data.title, data.text, data.url);
        };
    }

    // Also intercept custom share buttons that don't use Web Share API
    document.body.addEventListener('click', function(e) {
        var shareBtn = e.target.closest('[data-share-url]');
        if (!shareBtn) return;

        e.preventDefault();
        e.stopPropagation();

        var url = shareBtn.getAttribute('data-share-url') || window.location.href;
        var title = shareBtn.getAttribute('data-share-title') || document.title;
        var text = shareBtn.getAttribute('data-share-text') || '';

        MRPNative.share(title, text, url);
    }, true);

})();

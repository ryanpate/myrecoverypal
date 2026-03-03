/**
 * Capacitor Widget Bridge
 * Syncs sobriety_date to native App Group UserDefaults for the iOS widget.
 * Exits immediately in browser -- zero impact on web.
 */
(function() {
    'use strict';

    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) {
        return;
    }

    var WidgetBridge = window.Capacitor.Plugins.WidgetBridge;

    function syncWidgetData() {
        var meta = document.querySelector('meta[name="sobriety-date"]');
        var sobrietyDate = meta ? meta.getAttribute('content') : '';
        if (!sobrietyDate) return;

        var nameMeta = document.querySelector('meta[name="display-name"]');
        var displayName = nameMeta ? nameMeta.getAttribute('content') : '';

        WidgetBridge.setWidgetData({
            sobrietyDate: sobrietyDate,
            displayName: displayName
        }).catch(function(err) {
            console.warn('[Widget] sync error:', err);
        });
    }

    // Sync on page load
    if (document.readyState === 'complete') {
        syncWidgetData();
    } else {
        window.addEventListener('load', syncWidgetData);
    }

    // Re-sync when app returns to foreground
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            syncWidgetData();
        }
    });

    // Expose for logout cleanup
    window.MRPWidget = {
        clear: function() {
            return WidgetBridge.clearWidgetData().catch(function() {});
        }
    };
})();

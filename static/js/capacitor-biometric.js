/**
 * Capacitor Biometric Auth Bridge
 * Provides Face ID / Touch ID support for MyRecoveryPal native app.
 * Exits immediately in browser -- zero impact on web.
 *
 * Exposes window.MRPBiometric with:
 *   - checkAvailability()
 *   - authenticate(reason)
 *   - isAppLockEnabled() / setAppLockEnabled(enabled)
 *   - isJournalLockEnabled() / setJournalLockEnabled(enabled)
 *   - setLastBackground() / shouldLockOnResume()
 */
(function() {
    'use strict';

    // Only run inside Capacitor native shell
    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) {
        return;
    }

    var Plugins = window.Capacitor.Plugins;
    var BiometricAuth = Plugins.BiometricAuth;
    var Preferences = Plugins.Preferences;

    if (!BiometricAuth) {
        console.warn('[Biometric] BiometricAuth plugin not available');
        return;
    }

    if (!Preferences) {
        console.warn('[Biometric] Preferences plugin not available');
        return;
    }

    // Preference keys
    var PREF_APP_LOCK = 'biometric_app_lock_enabled';
    var PREF_JOURNAL_LOCK = 'biometric_journal_lock_enabled';
    var PREF_LAST_BACKGROUND = 'biometric_last_background_ts';

    // Lock timeout: 5 minutes in milliseconds
    var LOCK_TIMEOUT_MS = 5 * 60 * 1000;

    // ========================================
    // MRPBiometric API
    // ========================================
    var MRPBiometric = {
        available: false,
        biometryType: 'none', // 'none', 'touchId', 'faceId', 'fingerprintAuthentication', 'irisAuthentication'

        /**
         * Check if biometric authentication is available on this device.
         * Sets `available` and `biometryType` properties.
         */
        checkAvailability: function() {
            return BiometricAuth.checkBiometry().then(function(result) {
                MRPBiometric.available = result.isAvailable;
                MRPBiometric.biometryType = result.biometryType || 'none';
                console.log('[Biometric] Available:', result.isAvailable, 'Type:', result.biometryType);
                return result;
            }).catch(function(err) {
                console.warn('[Biometric] checkBiometry error:', err);
                MRPBiometric.available = false;
                MRPBiometric.biometryType = 'none';
                return { isAvailable: false, biometryType: 'none' };
            });
        },

        /**
         * Prompt the user for biometric authentication.
         * Falls back to device passcode if biometrics fail.
         * @param {string} reason - The reason string shown to the user
         * @returns {Promise} Resolves on success, rejects on failure/cancel
         */
        authenticate: function(reason) {
            return BiometricAuth.authenticate({
                reason: reason || 'Verify your identity',
                cancelTitle: 'Cancel',
                allowDeviceCredential: true,
                iosFallbackTitle: 'Use Passcode'
            });
        },

        /**
         * Check if app-level biometric lock is enabled.
         * @returns {Promise<boolean>}
         */
        isAppLockEnabled: function() {
            return Preferences.get({ key: PREF_APP_LOCK }).then(function(result) {
                return result.value === 'true';
            }).catch(function() {
                return false;
            });
        },

        /**
         * Enable or disable app-level biometric lock.
         * @param {boolean} enabled
         * @returns {Promise}
         */
        setAppLockEnabled: function(enabled) {
            return Preferences.set({ key: PREF_APP_LOCK, value: String(!!enabled) });
        },

        /**
         * Check if journal-specific biometric lock is enabled.
         * Defaults to true when app lock is enabled and this pref has never been set.
         * @returns {Promise<boolean>}
         */
        isJournalLockEnabled: function() {
            return Preferences.get({ key: PREF_JOURNAL_LOCK }).then(function(result) {
                if (result.value === null || result.value === undefined) {
                    // Default: enabled when app lock is enabled
                    return MRPBiometric.isAppLockEnabled();
                }
                return result.value === 'true';
            }).catch(function() {
                return false;
            });
        },

        /**
         * Enable or disable journal-specific biometric lock.
         * @param {boolean} enabled
         * @returns {Promise}
         */
        setJournalLockEnabled: function(enabled) {
            return Preferences.set({ key: PREF_JOURNAL_LOCK, value: String(!!enabled) });
        },

        /**
         * Record the current timestamp as the last time the app went to background.
         * Called when appStateChange fires with isActive=false.
         */
        setLastBackground: function() {
            return Preferences.set({
                key: PREF_LAST_BACKGROUND,
                value: String(Date.now())
            });
        },

        /**
         * Determine if the app should show the lock screen on resume.
         * Returns true if app lock is enabled AND 5+ minutes have elapsed since background.
         * @returns {Promise<boolean>}
         */
        shouldLockOnResume: function() {
            return MRPBiometric.isAppLockEnabled().then(function(enabled) {
                if (!enabled) return false;

                return Preferences.get({ key: PREF_LAST_BACKGROUND }).then(function(result) {
                    if (!result.value) return false;

                    var lastBg = parseInt(result.value, 10);
                    if (isNaN(lastBg)) return false;

                    var elapsed = Date.now() - lastBg;
                    return elapsed >= LOCK_TIMEOUT_MS;
                });
            }).catch(function() {
                return false;
            });
        }
    };

    window.MRPBiometric = MRPBiometric;

    // Check availability on load
    MRPBiometric.checkAvailability();

    // ========================================
    // Journal Biometric Gate
    // ========================================
    // Requires biometric auth before accessing /journal/* pages
    (function() {
        if (window.location.pathname.indexOf('/journal') !== 0) return;

        MRPBiometric.isJournalLockEnabled().then(function(enabled) {
            if (!enabled) return;

            // Hide the page while authenticating
            document.documentElement.style.visibility = 'hidden';

            MRPBiometric.authenticate('Access your private journal').then(function() {
                // Success -- reveal the page
                document.documentElement.style.visibility = '';
                if (window.MRPNative && window.MRPNative.hapticSuccess) {
                    window.MRPNative.hapticSuccess();
                }
            }).catch(function() {
                // Failed or cancelled -- restore visibility and navigate away
                document.documentElement.style.visibility = '';
                if (window.history.length > 1) {
                    window.history.back();
                } else {
                    window.location.href = '/accounts/social-feed/';
                }
            });
        });
    })();

})();

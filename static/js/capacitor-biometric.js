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
    // @aparajita/capacitor-biometric-auth registers as 'BiometricAuthNative'
    var BiometricAuth = Plugins.BiometricAuthNative || Plugins.BiometricAuth;
    var Preferences = Plugins.Preferences;

    if (!BiometricAuth) {
        console.warn('[Biometric] BiometricAuth plugin not available');
        return;
    }

    if (!Preferences) {
        console.warn('[Biometric] Preferences plugin not available');
        return;
    }

    // Map native LABiometryType rawValue integers to readable strings
    // 0 = none, 1 = touchId, 2 = faceId, 3 = fingerprintAuthentication
    var BIOMETRY_TYPE_MAP = {
        0: 'none',
        1: 'touchId',
        2: 'faceId',
        3: 'fingerprintAuthentication',
        4: 'faceAuthentication',
        5: 'irisAuthentication'
    };

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
        biometryType: 'none', // 'none', 'touchId', 'faceId', 'fingerprintAuthentication'

        /**
         * Check if biometric authentication is available on this device.
         * Sets `available` and `biometryType` properties.
         */
        checkAvailability: function() {
            return BiometricAuth.checkBiometry().then(function(result) {
                MRPBiometric.available = result.isAvailable;
                // Native returns biometryType as integer (LABiometryType rawValue)
                var rawType = result.biometryType;
                MRPBiometric.biometryType = BIOMETRY_TYPE_MAP[rawType] || (typeof rawType === 'string' ? rawType : 'none');
                console.log('[Biometric] Available:', result.isAvailable, 'Type:', MRPBiometric.biometryType, '(raw:', rawType + ')');
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
         * Uses internalAuthenticate (the native method name exposed by
         * @aparajita/capacitor-biometric-auth on the Capacitor proxy).
         * @param {string} reason - The reason string shown to the user
         * @returns {Promise} Resolves on success, rejects on failure/cancel
         */
        authenticate: function(reason) {
            return BiometricAuth.internalAuthenticate({
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

    // ========================================
    // Biometric Settings Toggles (Edit Profile / Settings)
    // ========================================
    // Injects "Security" section with Face ID toggles on profile/settings pages
    (function() {
        var path = window.location.pathname;
        if (path.indexOf('/accounts/edit-profile/') !== 0 &&
            path.indexOf('/accounts/settings/') !== 0) {
            return;
        }

        // Wait for availability check to complete before rendering
        MRPBiometric.checkAvailability().then(function(result) {
            if (!result.isAvailable) return;

            // Determine the label based on biometry type
            var bioLabel = 'Face ID';
            if (MRPBiometric.biometryType === 'touchId') {
                bioLabel = 'Touch ID';
            } else if (MRPBiometric.biometryType === 'fingerprintAuthentication') {
                bioLabel = 'Fingerprint';
            }

            // Build the settings section HTML
            var section = document.createElement('div');
            section.className = 'form-section biometric-settings-section';
            section.innerHTML =
                '<h3><i class="fas fa-fingerprint" aria-hidden="true"></i> Security</h3>' +
                '<div class="biometric-setting-row" id="biometricAppLockRow">' +
                    '<div class="biometric-setting-info">' +
                        '<div class="biometric-setting-label">Lock App with ' + bioLabel + '</div>' +
                        '<div class="biometric-setting-desc">Require biometric auth on app launch</div>' +
                    '</div>' +
                    '<label class="biometric-switch">' +
                        '<input type="checkbox" id="biometricAppLockToggle">' +
                        '<span class="biometric-slider"></span>' +
                    '</label>' +
                '</div>' +
                '<div class="biometric-setting-row" id="biometricJournalLockRow">' +
                    '<div class="biometric-setting-info">' +
                        '<div class="biometric-setting-label">Require ' + bioLabel + ' for Journal</div>' +
                        '<div class="biometric-setting-desc">Extra protection for private entries</div>' +
                    '</div>' +
                    '<label class="biometric-switch">' +
                        '<input type="checkbox" id="biometricJournalLockToggle">' +
                        '<span class="biometric-slider"></span>' +
                    '</label>' +
                '</div>';

            // Find the insertion point -- before the Invite Friends or Danger Zone section
            var container = document.querySelector('.edit-profile-container');
            if (!container) return;

            // Insert before the form's button group or the Danger Zone
            var dangerZone = container.querySelector('.form-section:last-child');
            var form = container.querySelector('form');
            if (form) {
                // Insert as the last form-section before the btn-group inside the form
                var btnGroup = form.querySelector('.btn-group');
                if (btnGroup) {
                    form.insertBefore(section, btnGroup);
                } else {
                    form.appendChild(section);
                }
            } else if (dangerZone) {
                dangerZone.parentNode.insertBefore(section, dangerZone);
            } else {
                container.appendChild(section);
            }

            var appLockToggle = document.getElementById('biometricAppLockToggle');
            var journalLockToggle = document.getElementById('biometricJournalLockToggle');
            var journalRow = document.getElementById('biometricJournalLockRow');

            // Load current state
            MRPBiometric.isAppLockEnabled().then(function(enabled) {
                appLockToggle.checked = enabled;
                updateJournalRowState(enabled);
            });

            MRPBiometric.isJournalLockEnabled().then(function(enabled) {
                journalLockToggle.checked = enabled;
            });

            function updateJournalRowState(appLockEnabled) {
                if (appLockEnabled) {
                    journalRow.style.opacity = '1';
                    journalLockToggle.disabled = false;
                } else {
                    journalRow.style.opacity = '0.4';
                    journalLockToggle.disabled = true;
                }
            }

            // Wire up change events
            appLockToggle.addEventListener('change', function() {
                var enabled = appLockToggle.checked;

                if (enabled) {
                    // Verify biometric auth before enabling
                    MRPBiometric.authenticate('Enable ' + bioLabel + ' lock').then(function() {
                        MRPBiometric.setAppLockEnabled(true);
                        updateJournalRowState(true);
                        // Auto-enable journal lock when app lock is turned on
                        journalLockToggle.checked = true;
                        MRPBiometric.setJournalLockEnabled(true);
                        if (window.MRPNative && window.MRPNative.hapticSuccess) {
                            window.MRPNative.hapticSuccess();
                        }
                    }).catch(function() {
                        // Auth failed -- revert toggle
                        appLockToggle.checked = false;
                        if (window.MRPNative && window.MRPNative.hapticWarning) {
                            window.MRPNative.hapticWarning();
                        }
                    });
                } else {
                    MRPBiometric.setAppLockEnabled(false);
                    updateJournalRowState(false);
                    // Disable journal lock when app lock is turned off
                    journalLockToggle.checked = false;
                    MRPBiometric.setJournalLockEnabled(false);
                    if (window.MRPNative && window.MRPNative.hapticMedium) {
                        window.MRPNative.hapticMedium();
                    }
                }
            });

            journalLockToggle.addEventListener('change', function() {
                var enabled = journalLockToggle.checked;
                MRPBiometric.setJournalLockEnabled(enabled);
                if (window.MRPNative) {
                    if (enabled && window.MRPNative.hapticSuccess) {
                        window.MRPNative.hapticSuccess();
                    } else if (!enabled && window.MRPNative.hapticMedium) {
                        window.MRPNative.hapticMedium();
                    }
                }
            });
        });
    })();

})();

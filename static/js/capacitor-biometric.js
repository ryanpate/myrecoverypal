/**
 * Capacitor Biometric Auth Bridge
 * Provides Face ID / Touch ID support for MyRecoveryPal native app.
 * Exits immediately in browser -- zero impact on web.
 *
 * Exposes window.MRPBiometric with:
 *   - checkAvailability()
 *   - authenticate(reason)
 *   - isBiometricLoginEnabled() / setBiometricLoginEnabled(enabled)
 *   - saveLoginCredentials(username, password)
 *   - getLoginCredentials()
 *   - clearLoginCredentials()
 *   - isJournalLockEnabled() / setJournalLockEnabled(enabled)
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
    var PREF_BIO_LOGIN = 'biometric_login_enabled';
    var PREF_JOURNAL_LOCK = 'biometric_journal_lock_enabled';
    var PREF_LOGIN_USER = 'biometric_login_username';
    var PREF_LOGIN_PASS = 'biometric_login_password';

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
            return BiometricAuth.internalAuthenticate({
                reason: reason || 'Verify your identity',
                cancelTitle: 'Cancel',
                allowDeviceCredential: true,
                iosFallbackTitle: 'Use Passcode'
            });
        },

        /**
         * Check if biometric login is enabled.
         * @returns {Promise<boolean>}
         */
        isBiometricLoginEnabled: function() {
            return Preferences.get({ key: PREF_BIO_LOGIN }).then(function(result) {
                return result.value === 'true';
            }).catch(function() {
                return false;
            });
        },

        /**
         * Enable or disable biometric login.
         * @param {boolean} enabled
         * @returns {Promise}
         */
        setBiometricLoginEnabled: function(enabled) {
            return Preferences.set({ key: PREF_BIO_LOGIN, value: String(!!enabled) });
        },

        /**
         * Save login credentials for biometric login.
         * @param {string} username
         * @param {string} password
         * @returns {Promise}
         */
        saveLoginCredentials: function(username, password) {
            return Preferences.set({ key: PREF_LOGIN_USER, value: username }).then(function() {
                return Preferences.set({ key: PREF_LOGIN_PASS, value: password });
            });
        },

        /**
         * Get stored login credentials.
         * @returns {Promise<{username: string, password: string}|null>}
         */
        getLoginCredentials: function() {
            return Preferences.get({ key: PREF_LOGIN_USER }).then(function(userResult) {
                if (!userResult.value) return null;
                return Preferences.get({ key: PREF_LOGIN_PASS }).then(function(passResult) {
                    if (!passResult.value) return null;
                    return { username: userResult.value, password: passResult.value };
                });
            }).catch(function() {
                return null;
            });
        },

        /**
         * Clear stored login credentials.
         * @returns {Promise}
         */
        clearLoginCredentials: function() {
            return Preferences.remove({ key: PREF_LOGIN_USER }).then(function() {
                return Preferences.remove({ key: PREF_LOGIN_PASS });
            });
        },

        /**
         * Check if journal-specific biometric lock is enabled.
         * @returns {Promise<boolean>}
         */
        isJournalLockEnabled: function() {
            return Preferences.get({ key: PREF_JOURNAL_LOCK }).then(function(result) {
                if (result.value === null || result.value === undefined) {
                    return false;
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
        }
    };

    window.MRPBiometric = MRPBiometric;

    // Key for tracking if we've offered biometric setup
    var PREF_BIO_OFFERED = 'biometric_setup_offered';

    // Check availability on load
    MRPBiometric.checkAvailability().then(function(result) {
        if (!result.isAvailable) return;

        // First-launch prompt: offer to enable Face ID / Touch ID
        // Only show once per install (stored in Preferences)
        return MRPBiometric.isBiometricLoginEnabled().then(function(alreadyEnabled) {
            if (alreadyEnabled) return; // Already set up

            return Preferences.get({ key: PREF_BIO_OFFERED }).then(function(offered) {
                if (offered.value === 'true') return; // Already asked

                // Mark as offered so we only ask once
                Preferences.set({ key: PREF_BIO_OFFERED, value: 'true' });

                // Determine label
                var bioLabel = 'Face ID';
                if (MRPBiometric.biometryType === 'touchId') bioLabel = 'Touch ID';
                else if (MRPBiometric.biometryType === 'fingerprintAuthentication') bioLabel = 'Fingerprint';

                // Show native-style prompt
                var overlay = document.createElement('div');
                overlay.id = 'biometricSetupPrompt';
                overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:99999;display:flex;align-items:center;justify-content:center;padding:24px;';
                overlay.innerHTML =
                    '<div style="background:#fff;border-radius:16px;padding:28px 24px;max-width:320px;width:100%;text-align:center;box-shadow:0 8px 32px rgba(0,0,0,0.2);">' +
                        '<div style="font-size:48px;margin-bottom:12px;">' +
                            (MRPBiometric.biometryType === 'faceId' ? '<i class="fas fa-face-viewfinder" style="color:#007AFF;"></i>' : '<i class="fas fa-fingerprint" style="color:#007AFF;"></i>') +
                        '</div>' +
                        '<h3 style="margin:0 0 8px;font-size:18px;font-weight:600;color:#1c1c1e;">Sign in with ' + bioLabel + '?</h3>' +
                        '<p style="margin:0 0 20px;font-size:14px;color:#666;line-height:1.4;">Use ' + bioLabel + ' to quickly sign in to MyRecoveryPal. Your credentials will be saved securely on this device.</p>' +
                        '<button id="bioSetupEnable" style="width:100%;padding:14px;border:none;border-radius:12px;background:#007AFF;color:#fff;font-size:16px;font-weight:600;cursor:pointer;margin-bottom:8px;">Enable ' + bioLabel + '</button>' +
                        '<button id="bioSetupSkip" style="width:100%;padding:14px;border:none;border-radius:12px;background:transparent;color:#007AFF;font-size:16px;cursor:pointer;">Not Now</button>' +
                    '</div>';

                document.body.appendChild(overlay);

                document.getElementById('bioSetupEnable').addEventListener('click', function() {
                    MRPBiometric.authenticate('Enable ' + bioLabel + ' for MyRecoveryPal').then(function() {
                        MRPBiometric.setBiometricLoginEnabled(true);
                        MRPBiometric.setJournalLockEnabled(true);
                        overlay.remove();
                        if (window.MRPNative && window.MRPNative.hapticSuccess) {
                            window.MRPNative.hapticSuccess();
                        }
                    }).catch(function() {
                        overlay.remove();
                    });
                });

                document.getElementById('bioSetupSkip').addEventListener('click', function() {
                    overlay.remove();
                });
            });
        });
    });

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
                '<div class="biometric-setting-row" id="biometricLoginRow">' +
                    '<div class="biometric-setting-info">' +
                        '<div class="biometric-setting-label">Sign in with ' + bioLabel + '</div>' +
                        '<div class="biometric-setting-desc">Use biometric auth on the login page</div>' +
                    '</div>' +
                    '<label class="biometric-switch">' +
                        '<input type="checkbox" id="biometricLoginToggle">' +
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

            var loginToggle = document.getElementById('biometricLoginToggle');
            var journalLockToggle = document.getElementById('biometricJournalLockToggle');

            // Load current state
            MRPBiometric.isBiometricLoginEnabled().then(function(enabled) {
                loginToggle.checked = enabled;
            });

            MRPBiometric.isJournalLockEnabled().then(function(enabled) {
                journalLockToggle.checked = enabled;
            });

            // Wire up change events
            loginToggle.addEventListener('change', function() {
                var enabled = loginToggle.checked;

                if (enabled) {
                    // Verify biometric auth before enabling
                    MRPBiometric.authenticate('Enable ' + bioLabel + ' sign-in').then(function() {
                        MRPBiometric.setBiometricLoginEnabled(true);
                        if (window.MRPNative && window.MRPNative.hapticSuccess) {
                            window.MRPNative.hapticSuccess();
                        }
                    }).catch(function() {
                        // Auth failed -- revert toggle
                        loginToggle.checked = false;
                        if (window.MRPNative && window.MRPNative.hapticWarning) {
                            window.MRPNative.hapticWarning();
                        }
                    });
                } else {
                    MRPBiometric.setBiometricLoginEnabled(false);
                    // Clear stored credentials when disabling
                    MRPBiometric.clearLoginCredentials();
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

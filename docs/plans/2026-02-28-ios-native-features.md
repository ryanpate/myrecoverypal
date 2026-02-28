# iOS Native Features Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Face ID lock, iOS tab bar navigation, swipe gestures with native transitions, and offline mode to the Capacitor iOS app.

**Architecture:** All features guard on `window.Capacitor.isNativePlatform()` and are scoped to `.ios-native-app` / `.android-native-app` CSS classes — zero impact on web. New JS files are loaded in `base.html` alongside existing `capacitor-native.js`. Biometric auth uses the `@aparajita/capacitor-biometric-auth` plugin; everything else is pure CSS + JS.

**Tech Stack:** Capacitor 7.x, `@aparajita/capacitor-biometric-auth`, `@capacitor/preferences`, IndexedDB, View Transition API (fallback CSS), existing Django/DRF backend.

---

## Task 1: Install Biometric Auth Plugin

**Files:**
- Modify: `package.json`
- Modify: `ios/App/Podfile` (auto-updated by cap sync)

**Step 1: Install the plugin**

Run:
```bash
cd /Users/ryanpate/myrecoverypal
npm install @aparajita/capacitor-biometric-auth
npx cap sync ios
```

Expected: Plugin installs and pod syncs without errors.

**Step 2: Verify installation**

Run:
```bash
grep "aparajita" package.json
grep -i "biometric" ios/App/Podfile
```

Expected: Both commands show the biometric auth plugin.

**Step 3: Commit**

```bash
git add package.json package-lock.json ios/App/Podfile ios/App/Podfile.lock
git commit -m "feat: install @aparajita/capacitor-biometric-auth plugin"
```

---

## Task 2: Create Biometric Auth Bridge (`capacitor-biometric.js`)

**Files:**
- Create: `static/js/capacitor-biometric.js`

**Step 1: Create the biometric auth module**

```javascript
/**
 * Capacitor Biometric Auth Bridge
 * Two-layer biometric protection: app lock + journal lock.
 * Exits immediately in browser — zero impact on web.
 */
(function() {
    'use strict';

    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) {
        return;
    }

    var Plugins = window.Capacitor.Plugins;
    var Preferences = Plugins.Preferences;

    // Keys for stored preferences
    var PREF_APP_LOCK = 'biometric_app_lock_enabled';
    var PREF_JOURNAL_LOCK = 'biometric_journal_lock_enabled';
    var PREF_LAST_BACKGROUND = 'biometric_last_background';
    var LOCK_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

    var MRPBiometric = {
        available: false,
        biometryType: 'none', // 'faceId', 'touchId', 'fingerprintAuthentication', 'none'

        /**
         * Check if biometric auth is available on this device.
         */
        checkAvailability: function() {
            if (!Plugins.BiometricAuth) {
                return Promise.resolve(false);
            }
            return Plugins.BiometricAuth.checkBiometry().then(function(result) {
                MRPBiometric.available = result.isAvailable;
                MRPBiometric.biometryType = result.biometryType || 'none';
                return result.isAvailable;
            }).catch(function() {
                MRPBiometric.available = false;
                return false;
            });
        },

        /**
         * Prompt user for biometric authentication.
         * Returns a promise that resolves on success, rejects on failure.
         */
        authenticate: function(reason) {
            if (!Plugins.BiometricAuth) {
                return Promise.reject('BiometricAuth plugin not available');
            }
            return Plugins.BiometricAuth.authenticate({
                reason: reason || 'Verify your identity',
                cancelTitle: 'Cancel',
                allowDeviceCredential: true,
                iosFallbackTitle: 'Use Passcode'
            });
        },

        // --- Preference helpers ---

        isAppLockEnabled: function() {
            if (!Preferences) return Promise.resolve(false);
            return Preferences.get({ key: PREF_APP_LOCK }).then(function(r) {
                return r.value === 'true';
            });
        },

        setAppLockEnabled: function(enabled) {
            if (!Preferences) return Promise.resolve();
            return Preferences.set({ key: PREF_APP_LOCK, value: String(enabled) });
        },

        isJournalLockEnabled: function() {
            if (!Preferences) return Promise.resolve(false);
            return Preferences.get({ key: PREF_JOURNAL_LOCK }).then(function(r) {
                // Default to true when app lock is on
                if (r.value === null) return MRPBiometric.isAppLockEnabled();
                return r.value === 'true';
            });
        },

        setJournalLockEnabled: function(enabled) {
            if (!Preferences) return Promise.resolve();
            return Preferences.set({ key: PREF_JOURNAL_LOCK, value: String(enabled) });
        },

        setLastBackground: function() {
            if (!Preferences) return Promise.resolve();
            return Preferences.set({ key: PREF_LAST_BACKGROUND, value: String(Date.now()) });
        },

        shouldLockOnResume: function() {
            if (!Preferences) return Promise.resolve(false);
            return Promise.all([
                MRPBiometric.isAppLockEnabled(),
                Preferences.get({ key: PREF_LAST_BACKGROUND })
            ]).then(function(results) {
                var enabled = results[0];
                var lastBg = results[1].value;
                if (!enabled) return false;
                if (!lastBg) return true;
                var elapsed = Date.now() - parseInt(lastBg, 10);
                return elapsed >= LOCK_TIMEOUT_MS;
            });
        }
    };

    window.MRPBiometric = MRPBiometric;

    // Check availability on load
    MRPBiometric.checkAvailability();

})();
```

**Step 2: Verify file exists**

Run:
```bash
ls -la /Users/ryanpate/myrecoverypal/static/js/capacitor-biometric.js
```

Expected: File exists.

**Step 3: Commit**

```bash
git add static/js/capacitor-biometric.js
git commit -m "feat: create biometric auth bridge module"
```

---

## Task 3: Add Lock Screen Overlay and App Lock Logic

**Files:**
- Modify: `templates/base.html` — add lock overlay HTML + biometric script load
- Modify: `static/css/base-inline.css` — lock screen styles

**Step 1: Add lock overlay HTML to `base.html`**

Insert immediately after `<body>` tag (before the skip-link), inside a native-only block:

```html
<!-- Biometric Lock Screen (native app only — hidden by default) -->
<div id="biometricLockScreen" class="biometric-lock-screen" style="display: none;">
    <div class="biometric-lock-content">
        <img src="{% static 'images/logo.svg' %}" alt="MyRecoveryPal" class="biometric-lock-logo">
        <h2>MyRecoveryPal</h2>
        <p>Tap to unlock</p>
        <button id="biometricUnlockBtn" class="biometric-unlock-btn">
            <i class="fas fa-fingerprint"></i> Unlock
        </button>
    </div>
</div>
```

Add script load after the existing `capacitor-iap.js` line:

```html
<!-- Capacitor Biometric Auth (native app only) -->
<script src="{% static 'js/capacitor-biometric.js' %}"></script>
```

Add inline script after the biometric script load to wire up lock behavior:

```html
<script>
(function() {
    if (!window.MRPBiometric) return;

    var lockScreen = document.getElementById('biometricLockScreen');
    var unlockBtn = document.getElementById('biometricUnlockBtn');
    if (!lockScreen || !unlockBtn) return;

    function showLock() {
        lockScreen.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function hideLock() {
        lockScreen.style.display = 'none';
        document.body.style.overflow = '';
    }

    function attemptUnlock() {
        window.MRPBiometric.authenticate('Unlock MyRecoveryPal').then(function() {
            hideLock();
        }).catch(function() {
            // Stay locked — user can tap again
        });
    }

    unlockBtn.addEventListener('click', attemptUnlock);

    // On page load: check if we need to lock
    window.MRPBiometric.shouldLockOnResume().then(function(shouldLock) {
        if (shouldLock) {
            showLock();
            attemptUnlock();
        }
    });

    // Track background time
    if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.App) {
        window.Capacitor.Plugins.App.addListener('appStateChange', function(state) {
            if (!state.isActive) {
                window.MRPBiometric.setLastBackground();
            } else {
                window.MRPBiometric.shouldLockOnResume().then(function(shouldLock) {
                    if (shouldLock) {
                        showLock();
                        attemptUnlock();
                    }
                });
            }
        });
    }
})();
</script>
```

**Step 2: Add lock screen CSS to `base-inline.css`**

Append to the Capacitor Native App Overrides section (after the `.iap-only` rules):

```css
/* Biometric Lock Screen */
.biometric-lock-screen {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    z-index: 99999;
    background: var(--primary-dark, #1e4d8b);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
}

.biometric-lock-content {
    text-align: center;
    color: white;
}

.biometric-lock-logo {
    width: 80px;
    height: 80px;
    margin-bottom: 1.5rem;
}

.biometric-lock-content h2 {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
    color: white;
}

.biometric-lock-content p {
    opacity: 0.8;
    margin-bottom: 2rem;
    color: white;
}

.biometric-unlock-btn {
    background: rgba(255, 255, 255, 0.2);
    border: 2px solid rgba(255, 255, 255, 0.5);
    color: white;
    padding: 1rem 2.5rem;
    border-radius: 50px;
    font-size: 1.1rem;
    cursor: pointer;
    transition: background 0.2s;
}

.biometric-unlock-btn:active {
    background: rgba(255, 255, 255, 0.35);
}
```

**Step 3: Verify no syntax errors in base.html**

Run:
```bash
python3 -c "
import re
with open('/Users/ryanpate/myrecoverypal/templates/base.html') as f:
    content = f.read()
print('biometricLockScreen found:', 'biometricLockScreen' in content)
print('capacitor-biometric.js found:', 'capacitor-biometric.js' in content)
"
```

Expected: Both `True`.

**Step 4: Commit**

```bash
git add templates/base.html static/css/base-inline.css
git commit -m "feat: add Face ID lock screen overlay and CSS"
```

---

## Task 4: Add Journal Biometric Gate

**Files:**
- Modify: `static/js/capacitor-biometric.js` — add journal lock check

**Step 1: Add journal lock logic**

Append to `capacitor-biometric.js`, inside the IIFE but after `window.MRPBiometric = MRPBiometric;`:

```javascript
// ========================================
// Journal Lock — biometric gate on /journal/ pages
// ========================================
(function journalLock() {
    // Only check on journal pages
    if (window.location.pathname.indexOf('/journal/') !== 0 &&
        window.location.pathname.indexOf('/journal') !== 0) {
        return;
    }

    MRPBiometric.checkAvailability().then(function(available) {
        if (!available) return;

        return MRPBiometric.isJournalLockEnabled();
    }).then(function(enabled) {
        if (!enabled) return;

        // Hide page content until authenticated
        document.documentElement.style.visibility = 'hidden';

        return MRPBiometric.authenticate('Access your private journal');
    }).then(function() {
        // Authenticated — show content
        document.documentElement.style.visibility = '';
    }).catch(function() {
        // Denied — redirect back
        document.documentElement.style.visibility = '';
        window.history.back();
        // Fallback if no history
        setTimeout(function() {
            window.location.href = '/accounts/social-feed/';
        }, 500);
    });
})();
```

**Step 2: Verify the code was added**

Run:
```bash
grep "journalLock" /Users/ryanpate/myrecoverypal/static/js/capacitor-biometric.js
```

Expected: `function journalLock` found.

**Step 3: Commit**

```bash
git add static/js/capacitor-biometric.js
git commit -m "feat: add biometric gate for journal pages"
```

---

## Task 5: Add Biometric Settings Toggle

Users need a way to enable/disable biometric lock in settings.

**Files:**
- Modify: `templates/base.html` — add settings UI in the lock screen inline script

For the MVP, we add a simple toggle within the app's existing Settings/Edit Profile page. Since the settings page is rendered server-side, we inject a native-only settings section via JS.

**Step 1: Add biometric settings injection to `capacitor-biometric.js`**

Append to the IIFE, after the journal lock section:

```javascript
// ========================================
// Settings Page — inject biometric toggles
// ========================================
(function biometricSettings() {
    // Only run on settings/edit-profile page
    if (window.location.pathname.indexOf('/accounts/edit-profile/') === -1 &&
        window.location.pathname.indexOf('/accounts/settings/') === -1) {
        return;
    }

    MRPBiometric.checkAvailability().then(function(available) {
        if (!available) return;

        // Find the form or main content area
        var form = document.querySelector('form') || document.querySelector('main');
        if (!form) return;

        // Create settings section
        var section = document.createElement('div');
        section.className = 'biometric-settings-section';
        section.innerHTML =
            '<h3 style="margin: 2rem 0 1rem; font-size: 1.1rem; color: var(--text-dark);">' +
            '<i class="fas fa-fingerprint" style="margin-right: 0.5rem;"></i>Security</h3>' +
            '<div class="biometric-toggle-row" style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: var(--bg-lighter, #f8f9fa); border-radius: 10px; margin-bottom: 0.75rem;">' +
                '<div><strong>Lock App with Face ID</strong>' +
                '<p style="margin: 0; font-size: 0.85rem; opacity: 0.7;">Require biometric auth on app launch</p></div>' +
                '<label class="biometric-switch"><input type="checkbox" id="appLockToggle"><span class="biometric-slider"></span></label>' +
            '</div>' +
            '<div class="biometric-toggle-row" id="journalLockRow" style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: var(--bg-lighter, #f8f9fa); border-radius: 10px; margin-bottom: 0.75rem;">' +
                '<div><strong>Require Face ID for Journal</strong>' +
                '<p style="margin: 0; font-size: 0.85rem; opacity: 0.7;">Extra protection for private entries</p></div>' +
                '<label class="biometric-switch"><input type="checkbox" id="journalLockToggle"><span class="biometric-slider"></span></label>' +
            '</div>';

        form.parentNode.insertBefore(section, form);

        // Load current state
        var appToggle = document.getElementById('appLockToggle');
        var journalToggle = document.getElementById('journalLockToggle');
        var journalRow = document.getElementById('journalLockRow');

        MRPBiometric.isAppLockEnabled().then(function(enabled) {
            appToggle.checked = enabled;
            journalRow.style.opacity = enabled ? '1' : '0.5';
            journalToggle.disabled = !enabled;
        });

        MRPBiometric.isJournalLockEnabled().then(function(enabled) {
            journalToggle.checked = enabled;
        });

        // Wire up toggles
        appToggle.addEventListener('change', function() {
            MRPBiometric.setAppLockEnabled(appToggle.checked);
            journalRow.style.opacity = appToggle.checked ? '1' : '0.5';
            journalToggle.disabled = !appToggle.checked;
            if (!appToggle.checked) {
                journalToggle.checked = false;
                MRPBiometric.setJournalLockEnabled(false);
            }
            if (window.MRPNative) window.MRPNative.hapticLight();
        });

        journalToggle.addEventListener('change', function() {
            MRPBiometric.setJournalLockEnabled(journalToggle.checked);
            if (window.MRPNative) window.MRPNative.hapticLight();
        });
    });
})();
```

**Step 2: Add toggle switch CSS to `base-inline.css`**

Append to the biometric section:

```css
/* Biometric toggle switch */
.biometric-switch {
    position: relative;
    display: inline-block;
    width: 51px;
    height: 31px;
    flex-shrink: 0;
}
.biometric-switch input { opacity: 0; width: 0; height: 0; }
.biometric-slider {
    position: absolute;
    cursor: pointer;
    top: 0; left: 0; right: 0; bottom: 0;
    background: #ccc;
    border-radius: 31px;
    transition: 0.3s;
}
.biometric-slider:before {
    content: "";
    position: absolute;
    height: 27px; width: 27px;
    left: 2px; bottom: 2px;
    background: white;
    border-radius: 50%;
    transition: 0.3s;
}
.biometric-switch input:checked + .biometric-slider {
    background: var(--accent-green, #52b788);
}
.biometric-switch input:checked + .biometric-slider:before {
    transform: translateX(20px);
}
```

**Step 3: Verify**

Run:
```bash
grep "biometricSettings" /Users/ryanpate/myrecoverypal/static/js/capacitor-biometric.js
grep "biometric-switch" /Users/ryanpate/myrecoverypal/static/css/base-inline.css
```

Expected: Both found.

**Step 4: Commit**

```bash
git add static/js/capacitor-biometric.js static/css/base-inline.css
git commit -m "feat: add biometric lock settings toggles on edit profile page"
```

---

## Task 6: iOS Tab Bar Navigation — HTML

Replace the existing `mobile-bottom-nav` with a 5-tab iOS-style tab bar. Web version unchanged — all changes scoped to native.

**Files:**
- Modify: `templates/base.html`

**Step 1: Add native tab bar HTML**

Replace the existing mobile-bottom-nav section (lines ~515-549 in `base.html`) with a version that includes both the web bottom nav (unchanged) and a new native tab bar:

Find this block:
```html
<!-- Mobile Bottom Navigation Bar -->
{% if user.is_authenticated %}
<nav class="mobile-bottom-nav" id="mobileBottomNav">
```

Replace the entire authenticated and unauthenticated `mobile-bottom-nav` sections (through closing `{% endif %}` after the unauth nav) with:

```html
<!-- Mobile Bottom Navigation Bar (Web PWA) -->
{% if user.is_authenticated %}
<nav class="mobile-bottom-nav web-bottom-nav" id="mobileBottomNav">
    <a href="{% url 'accounts:social_feed' %}" class="{% if request.resolver_match.url_name == 'social_feed' %}active{% endif %}">
        <span>Circle</span>
    </a>
    <a href="{% url 'accounts:recovery_coach' %}"
        class="{% if request.resolver_match.url_name == 'recovery_coach' %}active{% endif %}">
        <span>Anchor</span>
    </a>
    <a href="{% url 'accounts:community' %}"
        class="{% if request.resolver_match.url_name == 'community' %}active{% endif %}">
        <span>Community</span>
    </a>
    <a href="{% url 'accounts:dashboard' %}"
        class="{% if request.resolver_match.url_name == 'dashboard' %}active{% endif %}">
        <span>Account</span>
    </a>
</nav>
{% else %}
<nav class="mobile-bottom-nav web-bottom-nav" id="mobileBottomNav">
    <a href="{% url 'core:index' %}" class="{% if request.resolver_match.url_name == 'index' %}active{% endif %}">
        <span>Home</span>
    </a>
    <a href="{% url 'accounts:social_feed' %}" class="{% if request.resolver_match.url_name == 'social_feed' %}active{% endif %}">
        <span>Circle</span>
    </a>
    <a href="{% url 'core:ai_recovery_coach' %}"
        class="{% if request.resolver_match.url_name == 'ai_recovery_coach' %}active{% endif %}">
        <span>Anchor</span>
    </a>
    <a href="{% url 'accounts:login' %}">
        <span>Login</span>
    </a>
</nav>
{% endif %}

<!-- Native iOS/Android Tab Bar (replaces web bottom nav in native app) -->
{% if user.is_authenticated %}
<nav class="native-tab-bar" id="nativeTabBar">
    <a href="{% url 'accounts:social_feed' %}" class="native-tab {% if request.resolver_match.url_name == 'social_feed' %}active{% endif %}" data-haptic="light">
        <i class="{% if request.resolver_match.url_name == 'social_feed' %}fas{% else %}far{% endif %} fa-newspaper"></i>
        <span>Feed</span>
    </a>
    <a href="{% url 'accounts:groups_list' %}" class="native-tab {% if 'group' in request.resolver_match.url_name %}active{% endif %}" data-haptic="light">
        <i class="{% if 'group' in request.resolver_match.url_name %}fas{% else %}far{% endif %} fa-users"></i>
        <span>Groups</span>
    </a>
    <a href="{% url 'accounts:recovery_coach' %}" class="native-tab {% if request.resolver_match.url_name == 'recovery_coach' %}active{% endif %}" data-haptic="light">
        <i class="{% if request.resolver_match.url_name == 'recovery_coach' %}fas{% else %}far{% endif %} fa-comment-dots"></i>
        <span>Coach</span>
    </a>
    <a href="{% url 'journal:entry_list' %}" class="native-tab {% if 'journal' in request.resolver_match.namespace %}active{% endif %}" data-haptic="light">
        <i class="{% if 'journal' in request.resolver_match.namespace %}fas{% else %}far{% endif %} fa-book"></i>
        <span>Journal</span>
    </a>
    <a href="#" class="native-tab {% if request.resolver_match.url_name == 'native_more' %}active{% endif %}" id="nativeMoreTab" data-haptic="light">
        <i class="fas fa-ellipsis-h"></i>
        <span>More</span>
    </a>
</nav>
{% endif %}

<!-- Native "More" Menu Overlay -->
<div class="native-more-overlay" id="nativeMoreOverlay" style="display: none;">
    <div class="native-more-menu" id="nativeMoreMenu">
        <div class="native-more-header">
            <h3>More</h3>
            <button id="nativeMoreClose" aria-label="Close">&times;</button>
        </div>
        <div class="native-more-list">
            <a href="{% url 'accounts:profile' username=user.username %}" class="native-more-item">
                <i class="fas fa-user"></i><span>Profile</span><i class="fas fa-chevron-right native-chevron"></i>
            </a>
            <a href="{% url 'accounts:milestones' %}" class="native-more-item">
                <i class="fas fa-trophy"></i><span>Milestones</span><i class="fas fa-chevron-right native-chevron"></i>
            </a>
            <a href="{% url 'accounts:community' %}" class="native-more-item">
                <i class="fas fa-users"></i><span>Community</span><i class="fas fa-chevron-right native-chevron"></i>
            </a>
            <a href="{% url 'accounts:challenges_home' %}" class="native-more-item">
                <i class="fas fa-flag-checkered"></i><span>Challenges</span><i class="fas fa-chevron-right native-chevron"></i>
            </a>
            <a href="{% url 'accounts:messages' %}" class="native-more-item">
                <i class="fas fa-envelope"></i><span>Messages</span><i class="fas fa-chevron-right native-chevron"></i>
            </a>
            <a href="{% url 'accounts:progress' %}" class="native-more-item">
                <i class="fas fa-chart-line"></i><span>My Progress</span><i class="fas fa-chevron-right native-chevron"></i>
            </a>
            <a href="{% url 'accounts:edit_profile' %}" class="native-more-item">
                <i class="fas fa-cog"></i><span>Settings</span><i class="fas fa-chevron-right native-chevron"></i>
            </a>
            <a href="{% url 'accounts:subscription_management' %}" class="native-more-item">
                <i class="fas fa-crown"></i><span>Subscription</span><i class="fas fa-chevron-right native-chevron"></i>
            </a>
        </div>
    </div>
</div>
```

**Step 2: Hide hamburger on native**

In `capacitor-native.js`, add to the platform class section (after `document.body.classList.add(platform + '-native-app');`):

```javascript
// Hide hamburger menu on native (replaced by tab bar)
var hamburger = document.getElementById('hamburgerBtn');
if (hamburger) hamburger.style.display = 'none';
```

**Step 3: Verify template renders**

Run:
```bash
grep "native-tab-bar" /Users/ryanpate/myrecoverypal/templates/base.html
grep "nativeMoreTab" /Users/ryanpate/myrecoverypal/templates/base.html
```

Expected: Both found.

**Step 4: Commit**

```bash
git add templates/base.html static/js/capacitor-native.js
git commit -m "feat: add iOS-style tab bar and More menu HTML"
```

---

## Task 7: iOS Tab Bar Navigation — CSS

**Files:**
- Modify: `static/css/base-inline.css`

**Step 1: Add native tab bar styles**

Append to the Capacitor Native App Overrides section in `base-inline.css`:

```css
/* ========================================
   Native Tab Bar (iOS/Android)
   ======================================== */

/* Hide native tab bar on web */
.native-tab-bar { display: none !important; }
.native-more-overlay { display: none !important; }

/* Show native tab bar, hide web bottom nav on native */
.ios-native-app .web-bottom-nav,
.android-native-app .web-bottom-nav { display: none !important; }

.ios-native-app .native-tab-bar,
.android-native-app .native-tab-bar {
    display: flex !important;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--bg-lighter, #ffffff);
    border-top: 0.5px solid rgba(0, 0, 0, 0.15);
    padding: 6px 0 calc(6px + var(--safe-area-inset-bottom, 0px));
    z-index: 10000;
    justify-content: space-around;
}

.native-tab {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    color: #8e8e93;
    font-size: 0.65rem;
    font-weight: 500;
    padding: 2px 0;
    flex: 1;
    -webkit-tap-highlight-color: transparent;
    transition: color 0.15s;
}

.native-tab i {
    font-size: 1.3rem;
    margin-bottom: 2px;
}

.native-tab.active {
    color: var(--primary-dark, #1e4d8b);
}

.native-tab:active {
    opacity: 0.6;
}

/* Dark mode */
[data-theme="dark"] .native-tab-bar {
    background: #1c1c1e;
    border-top-color: rgba(255, 255, 255, 0.1);
}
[data-theme="dark"] .native-tab { color: #8e8e93; }
[data-theme="dark"] .native-tab.active { color: #64d2ff; }

/* Hide hamburger on native */
.ios-native-app .hamburger,
.android-native-app .hamburger { display: none !important; }

/* Adjust body padding for native tab bar */
.ios-native-app main,
.android-native-app main {
    padding-bottom: calc(60px + var(--safe-area-inset-bottom, 0px));
}

/* ========================================
   Native "More" Menu
   ======================================== */

.ios-native-app .native-more-overlay,
.android-native-app .native-more-overlay {
    display: none; /* JS controls visibility */
}

.ios-native-app .native-more-overlay[style*="display: flex"],
.android-native-app .native-more-overlay[style*="display: flex"] {
    display: flex !important;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    z-index: 10001;
    background: rgba(0, 0, 0, 0.4);
    align-items: flex-end;
    justify-content: center;
}

.native-more-menu {
    background: var(--bg-lighter, #f2f2f7);
    border-radius: 20px 20px 0 0;
    width: 100%;
    max-height: 70vh;
    overflow-y: auto;
    padding: 0 0 calc(16px + var(--safe-area-inset-bottom, 0px));
    -webkit-overflow-scrolling: touch;
}

.native-more-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 20px 12px;
    border-bottom: 0.5px solid rgba(0, 0, 0, 0.1);
}

.native-more-header h3 {
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--text-dark);
    margin: 0;
}

.native-more-header button {
    background: none;
    border: none;
    font-size: 1.5rem;
    color: #8e8e93;
    cursor: pointer;
    padding: 4px 8px;
}

.native-more-list {
    padding: 8px 16px;
}

.native-more-item {
    display: flex;
    align-items: center;
    padding: 14px 16px;
    background: white;
    text-decoration: none;
    color: var(--text-dark);
    font-size: 1rem;
    border-bottom: 0.5px solid rgba(0, 0, 0, 0.08);
    -webkit-tap-highlight-color: transparent;
}

.native-more-item:first-child { border-radius: 12px 12px 0 0; }
.native-more-item:last-child { border-radius: 0 0 12px 12px; border-bottom: none; }

.native-more-item i:first-child {
    width: 28px;
    text-align: center;
    color: var(--primary-dark, #1e4d8b);
    margin-right: 14px;
    font-size: 1.1rem;
}

.native-more-item span {
    flex: 1;
}

.native-chevron {
    color: #c7c7cc;
    font-size: 0.8rem;
}

.native-more-item:active {
    background: #e5e5ea;
}

/* Dark mode More menu */
[data-theme="dark"] .native-more-menu { background: #1c1c1e; }
[data-theme="dark"] .native-more-item { background: #2c2c2e; color: #fff; }
[data-theme="dark"] .native-more-item:active { background: #3a3a3c; }
[data-theme="dark"] .native-chevron { color: #48484a; }

/* Hide keyboard-open for native tab bar too */
.keyboard-open .native-tab-bar { display: none !important; }
```

**Step 2: Verify CSS was added**

Run:
```bash
grep "native-tab-bar" /Users/ryanpate/myrecoverypal/static/css/base-inline.css
grep "native-more-menu" /Users/ryanpate/myrecoverypal/static/css/base-inline.css
```

Expected: Both found.

**Step 3: Commit**

```bash
git add static/css/base-inline.css
git commit -m "feat: add iOS tab bar and More menu CSS styles"
```

---

## Task 8: iOS Tab Bar — JavaScript Logic

Wire up the "More" tab and add haptic feedback on tab switches.

**Files:**
- Modify: `static/js/capacitor-native.js`

**Step 1: Add More tab and tab bar logic**

Append to `capacitor-native.js`, inside the IIFE (before the closing `})();`):

```javascript
// ========================================
// Native Tab Bar — More Menu Logic
// ========================================
var moreTab = document.getElementById('nativeMoreTab');
var moreOverlay = document.getElementById('nativeMoreOverlay');
var moreClose = document.getElementById('nativeMoreClose');

if (moreTab && moreOverlay) {
    moreTab.addEventListener('click', function(e) {
        e.preventDefault();
        moreOverlay.style.display = 'flex';
        MRPNative.hapticLight();
    });

    moreOverlay.addEventListener('click', function(e) {
        if (e.target === moreOverlay) {
            moreOverlay.style.display = 'none';
        }
    });

    if (moreClose) {
        moreClose.addEventListener('click', function() {
            moreOverlay.style.display = 'none';
        });
    }
}

// Haptic on native tab switch
var tabBar = document.getElementById('nativeTabBar');
if (tabBar) {
    tabBar.addEventListener('click', function(e) {
        var tab = e.target.closest('.native-tab');
        if (tab && tab.id !== 'nativeMoreTab') {
            MRPNative.hapticLight();
        }
    });
}
```

**Step 2: Verify**

Run:
```bash
grep "nativeMoreTab" /Users/ryanpate/myrecoverypal/static/js/capacitor-native.js
```

Expected: Found.

**Step 3: Commit**

```bash
git add static/js/capacitor-native.js
git commit -m "feat: wire up native More menu toggle and tab haptics"
```

---

## Task 9: Create Page Transitions + Swipe Gestures Module

**Files:**
- Create: `static/js/capacitor-transitions.js`

**Step 1: Create the transitions module**

```javascript
/**
 * Capacitor Page Transitions + Swipe Gestures
 * iOS-native-feeling transitions and gestures.
 * Exits immediately in browser — zero impact on web.
 */
(function() {
    'use strict';

    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) {
        return;
    }

    var TRANSITION_DURATION = 250; // ms, matches iOS UIKit
    var EDGE_ZONE = 30; // px from left edge for back swipe
    var SWIPE_THRESHOLD = 80; // px to trigger back navigation

    // ========================================
    // Edge Swipe Back Gesture
    // ========================================
    var touchStartX = 0;
    var touchStartY = 0;
    var isSwiping = false;
    var swipeIndicator = null;

    function createSwipeIndicator() {
        var el = document.createElement('div');
        el.className = 'swipe-back-indicator';
        el.innerHTML = '<i class="fas fa-chevron-left"></i>';
        document.body.appendChild(el);
        return el;
    }

    document.addEventListener('touchstart', function(e) {
        var touch = e.touches[0];
        if (touch.clientX <= EDGE_ZONE && window.history.length > 1) {
            touchStartX = touch.clientX;
            touchStartY = touch.clientY;
            isSwiping = true;

            if (!swipeIndicator) {
                swipeIndicator = createSwipeIndicator();
            }
        }
    }, { passive: true });

    document.addEventListener('touchmove', function(e) {
        if (!isSwiping) return;

        var touch = e.touches[0];
        var dx = touch.clientX - touchStartX;
        var dy = Math.abs(touch.clientY - touchStartY);

        // Cancel if vertical scroll is dominant
        if (dy > dx) {
            isSwiping = false;
            if (swipeIndicator) swipeIndicator.classList.remove('visible');
            return;
        }

        if (dx > 20 && swipeIndicator) {
            swipeIndicator.classList.add('visible');
            var progress = Math.min(dx / SWIPE_THRESHOLD, 1);
            swipeIndicator.style.opacity = progress;
            swipeIndicator.style.transform = 'translateX(' + Math.min(dx * 0.4, 30) + 'px)';
        }
    }, { passive: true });

    document.addEventListener('touchend', function(e) {
        if (!isSwiping) return;
        isSwiping = false;

        var touch = e.changedTouches[0];
        var dx = touch.clientX - touchStartX;

        if (swipeIndicator) {
            swipeIndicator.classList.remove('visible');
            swipeIndicator.style.transform = '';
            swipeIndicator.style.opacity = '';
        }

        if (dx >= SWIPE_THRESHOLD) {
            if (window.MRPNative) window.MRPNative.hapticLight();
            navigateBack();
        }
    }, { passive: true });

    // ========================================
    // Page Transitions
    // ========================================

    /**
     * Determine if a link should use native transition.
     * Only internal same-origin links, not hashes, not new tabs.
     */
    function shouldTransition(anchor) {
        if (!anchor || !anchor.href) return false;
        if (anchor.target === '_blank') return false;
        if (anchor.hasAttribute('download')) return false;
        if (anchor.href.indexOf(window.location.origin) !== 0) return false;
        if (anchor.href === window.location.href) return false;
        // Skip form submits, js: links
        if (anchor.href.indexOf('javascript:') === 0) return false;
        return true;
    }

    function navigateForward(url) {
        var main = document.querySelector('main') || document.body;

        // Try View Transition API (iOS 18+)
        if (document.startViewTransition) {
            document.startViewTransition(function() {
                window.location.href = url;
            });
            return;
        }

        // Fallback: CSS animation
        main.classList.add('page-exit-left');
        setTimeout(function() {
            window.location.href = url;
        }, TRANSITION_DURATION);
    }

    function navigateBack() {
        var main = document.querySelector('main') || document.body;

        if (document.startViewTransition) {
            document.startViewTransition(function() {
                window.history.back();
            });
            return;
        }

        main.classList.add('page-exit-right');
        setTimeout(function() {
            window.history.back();
        }, TRANSITION_DURATION);
    }

    // Intercept link clicks for transitions
    document.addEventListener('click', function(e) {
        var anchor = e.target.closest('a');
        if (!anchor || !shouldTransition(anchor)) return;

        // Don't intercept tab bar or More menu links (they have their own handling)
        if (anchor.closest('.native-tab-bar') || anchor.closest('.native-more-menu')) return;

        e.preventDefault();
        navigateForward(anchor.href);
    });

    // On page show, add entrance animation
    window.addEventListener('pageshow', function(e) {
        var main = document.querySelector('main');
        if (!main) return;

        main.classList.remove('page-exit-left', 'page-exit-right');
        main.classList.add('page-enter');

        setTimeout(function() {
            main.classList.remove('page-enter');
        }, TRANSITION_DURATION);
    });

    // ========================================
    // Enhanced Pull-to-Refresh
    // ========================================
    var pullStartY = 0;
    var isPulling = false;
    var pullIndicator = null;

    function createPullIndicator() {
        var el = document.createElement('div');
        el.className = 'pull-refresh-indicator';
        el.innerHTML = '<i class="fas fa-arrow-down"></i>';
        document.body.appendChild(el);
        return el;
    }

    document.addEventListener('touchstart', function(e) {
        if (window.scrollY === 0 && !isSwiping) {
            pullStartY = e.touches[0].clientY;
            isPulling = true;
        }
    }, { passive: true });

    document.addEventListener('touchmove', function(e) {
        if (!isPulling || window.scrollY > 0) {
            isPulling = false;
            return;
        }

        var dy = e.touches[0].clientY - pullStartY;
        if (dy > 10) {
            if (!pullIndicator) pullIndicator = createPullIndicator();

            var progress = Math.min(dy / 120, 1);
            pullIndicator.style.opacity = progress;
            pullIndicator.style.transform = 'translateY(' + Math.min(dy * 0.3, 40) + 'px) rotate(' + (progress * 180) + 'deg)';
            pullIndicator.classList.add('visible');
        }
    }, { passive: true });

    document.addEventListener('touchend', function() {
        if (!isPulling) return;
        isPulling = false;

        if (pullIndicator) {
            pullIndicator.classList.remove('visible');
            pullIndicator.style.transform = '';
            pullIndicator.style.opacity = '';
        }

        var dy = event.changedTouches[0].clientY - pullStartY;
        if (dy >= 120) {
            if (window.MRPNative) window.MRPNative.hapticMedium();
            window.location.reload();
        }
    }, { passive: true });

})();
```

**Step 2: Add transition and gesture CSS to `base-inline.css`**

Append to the Capacitor section:

```css
/* ========================================
   Page Transitions (Native Only)
   ======================================== */

.ios-native-app .page-enter,
.android-native-app .page-enter {
    animation: slideInRight 250ms ease-out;
}

.ios-native-app .page-exit-left,
.android-native-app .page-exit-left {
    animation: slideOutLeft 250ms ease-in;
}

.ios-native-app .page-exit-right,
.android-native-app .page-exit-right {
    animation: slideOutRight 250ms ease-in;
}

@keyframes slideInRight {
    from { transform: translateX(100%); opacity: 0.8; }
    to { transform: translateX(0); opacity: 1; }
}

@keyframes slideOutLeft {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(-30%); opacity: 0.5; }
}

@keyframes slideOutRight {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0.8; }
}

/* View Transition API overrides (iOS 18+) */
::view-transition-old(root) {
    animation: slideOutLeft 250ms ease-in;
}
::view-transition-new(root) {
    animation: slideInRight 250ms ease-out;
}

/* Swipe back indicator */
.swipe-back-indicator {
    position: fixed;
    left: -10px;
    top: 50%;
    transform: translateY(-50%);
    width: 30px;
    height: 30px;
    background: rgba(0, 0, 0, 0.15);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 0.8rem;
    opacity: 0;
    z-index: 99998;
    pointer-events: none;
    transition: opacity 0.1s;
}

.swipe-back-indicator.visible {
    opacity: 1;
}

/* Pull-to-refresh indicator */
.pull-refresh-indicator {
    position: fixed;
    top: calc(10px + var(--safe-area-inset-top, 0px));
    left: 50%;
    transform: translateX(-50%);
    width: 32px;
    height: 32px;
    background: var(--primary-dark, #1e4d8b);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 0.8rem;
    opacity: 0;
    z-index: 99998;
    pointer-events: none;
    transition: opacity 0.15s;
}

.pull-refresh-indicator.visible {
    opacity: 1;
}
```

**Step 3: Load the script in `base.html`**

After the `capacitor-biometric.js` script tag:

```html
<!-- Capacitor Page Transitions + Gestures (native app only) -->
<script src="{% static 'js/capacitor-transitions.js' %}"></script>
```

**Step 4: Verify**

Run:
```bash
ls -la /Users/ryanpate/myrecoverypal/static/js/capacitor-transitions.js
grep "capacitor-transitions" /Users/ryanpate/myrecoverypal/templates/base.html
grep "slideInRight" /Users/ryanpate/myrecoverypal/static/css/base-inline.css
```

Expected: All found.

**Step 5: Commit**

```bash
git add static/js/capacitor-transitions.js templates/base.html static/css/base-inline.css
git commit -m "feat: add native page transitions and swipe gestures"
```

---

## Task 10: Create Offline Mode Module

**Files:**
- Create: `static/js/capacitor-offline.js`

**Step 1: Create the offline module**

```javascript
/**
 * Capacitor Offline Mode
 * Cache-first reads, queue writes for sync.
 * Exits immediately in browser — zero impact on web.
 */
(function() {
    'use strict';

    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) {
        return;
    }

    var DB_NAME = 'mrp_offline';
    var DB_VERSION = 1;
    var STORES = {
        POSTS: 'posts',
        JOURNAL: 'journal',
        CHECKINS: 'checkins',
        WRITE_QUEUE: 'write_queue',
        META: 'meta'
    };

    var db = null;

    // ========================================
    // IndexedDB Setup
    // ========================================
    function openDB() {
        return new Promise(function(resolve, reject) {
            if (db) return resolve(db);

            var request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onupgradeneeded = function(e) {
                var d = e.target.result;
                if (!d.objectStoreNames.contains(STORES.POSTS)) {
                    d.createObjectStore(STORES.POSTS, { keyPath: 'id' });
                }
                if (!d.objectStoreNames.contains(STORES.JOURNAL)) {
                    d.createObjectStore(STORES.JOURNAL, { keyPath: 'id' });
                }
                if (!d.objectStoreNames.contains(STORES.CHECKINS)) {
                    d.createObjectStore(STORES.CHECKINS, { keyPath: 'id', autoIncrement: true });
                }
                if (!d.objectStoreNames.contains(STORES.WRITE_QUEUE)) {
                    d.createObjectStore(STORES.WRITE_QUEUE, { keyPath: 'id', autoIncrement: true });
                }
                if (!d.objectStoreNames.contains(STORES.META)) {
                    d.createObjectStore(STORES.META, { keyPath: 'key' });
                }
            };

            request.onsuccess = function(e) {
                db = e.target.result;
                resolve(db);
            };

            request.onerror = function(e) {
                reject(e.target.error);
            };
        });
    }

    // Generic store helper
    function storeOp(storeName, mode, callback) {
        return openDB().then(function(d) {
            return new Promise(function(resolve, reject) {
                var tx = d.transaction(storeName, mode);
                var store = tx.objectStore(storeName);
                var result = callback(store);
                tx.oncomplete = function() { resolve(result); };
                tx.onerror = function(e) { reject(e.target.error); };
            });
        });
    }

    // ========================================
    // Offline Detection + Banner
    // ========================================
    var offlineBanner = document.querySelector('.offline-banner');
    var isOnline = navigator.onLine;

    function updateOnlineStatus() {
        isOnline = navigator.onLine;
        if (offlineBanner) {
            if (!isOnline) {
                offlineBanner.style.display = 'block';
                offlineBanner.textContent = "You're offline — changes will sync when connected";
            } else {
                offlineBanner.style.display = 'none';
                // Flush write queue on reconnect
                flushWriteQueue();
            }
        }
    }

    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus();

    // Also flush on app foreground
    if (window.Capacitor.Plugins.App) {
        window.Capacitor.Plugins.App.addListener('appStateChange', function(state) {
            if (state.isActive && navigator.onLine) {
                flushWriteQueue();
            }
        });
    }

    // ========================================
    // Cache Social Feed Posts
    // ========================================
    function cachePosts(posts) {
        return storeOp(STORES.POSTS, 'readwrite', function(store) {
            posts.forEach(function(post) {
                store.put(post);
            });
        });
    }

    function getCachedPosts(limit) {
        limit = limit || 50;
        return storeOp(STORES.POSTS, 'readonly', function(store) {
            return new Promise(function(resolve) {
                var results = [];
                var cursor = store.openCursor(null, 'prev');
                cursor.onsuccess = function(e) {
                    var c = e.target.result;
                    if (c && results.length < limit) {
                        results.push(c.value);
                        c.continue();
                    } else {
                        resolve(results);
                    }
                };
            });
        });
    }

    // ========================================
    // Cache Journal Entries
    // ========================================
    function cacheJournalEntries(entries) {
        return storeOp(STORES.JOURNAL, 'readwrite', function(store) {
            entries.forEach(function(entry) {
                store.put(entry);
            });
        });
    }

    function getCachedJournalEntries() {
        return storeOp(STORES.JOURNAL, 'readonly', function(store) {
            return new Promise(function(resolve) {
                var results = [];
                var cursor = store.openCursor(null, 'prev');
                cursor.onsuccess = function(e) {
                    var c = e.target.result;
                    if (c) {
                        results.push(c.value);
                        c.continue();
                    } else {
                        resolve(results);
                    }
                };
            });
        });
    }

    // ========================================
    // Write Queue (offline actions)
    // ========================================
    function queueWrite(action) {
        // action = { url, method, body, type }
        action.queued_at = Date.now();
        return storeOp(STORES.WRITE_QUEUE, 'readwrite', function(store) {
            store.add(action);
        });
    }

    function flushWriteQueue() {
        if (!navigator.onLine) return Promise.resolve();

        return storeOp(STORES.WRITE_QUEUE, 'readwrite', function(store) {
            return new Promise(function(resolve) {
                var cursor = store.openCursor();
                var promises = [];

                cursor.onsuccess = function(e) {
                    var c = e.target.result;
                    if (c) {
                        var action = c.value;
                        var p = fetch(action.url, {
                            method: action.method || 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCSRFToken()
                            },
                            body: action.body ? JSON.stringify(action.body) : undefined,
                            credentials: 'same-origin'
                        }).then(function() {
                            // Delete from queue on success
                            return storeOp(STORES.WRITE_QUEUE, 'readwrite', function(s) {
                                s.delete(action.id);
                            });
                        }).catch(function() {
                            // Keep in queue if still failing
                        });

                        promises.push(p);
                        c.continue();
                    } else {
                        Promise.all(promises).then(resolve);
                    }
                };
            });
        });
    }

    function getCSRFToken() {
        var cookie = document.cookie.match(/csrftoken=([^;]+)/);
        return cookie ? cookie[1] : '';
    }

    // ========================================
    // Intercept API Fetches for Caching
    // ========================================
    var originalFetch = window.fetch;

    window.fetch = function(url, options) {
        var urlStr = typeof url === 'string' ? url : url.url || '';

        // Cache social feed responses
        if (urlStr.indexOf('/social-feed/posts/') > -1 && (!options || options.method === 'GET' || !options.method)) {
            return originalFetch.apply(this, arguments).then(function(response) {
                var cloned = response.clone();
                cloned.json().then(function(data) {
                    if (data.posts) cachePosts(data.posts);
                }).catch(function() {});
                return response;
            }).catch(function(err) {
                // Offline — serve cached
                if (!navigator.onLine) {
                    return getCachedPosts().then(function(posts) {
                        return new Response(JSON.stringify({ posts: posts, cached: true }), {
                            headers: { 'Content-Type': 'application/json' }
                        });
                    });
                }
                throw err;
            });
        }

        // Queue writes when offline
        if (!navigator.onLine && options && options.method && options.method !== 'GET') {
            queueWrite({
                url: urlStr,
                method: options.method,
                body: options.body ? JSON.parse(options.body) : null,
                type: 'api_call'
            });
            // Return a fake success response
            return Promise.resolve(new Response(JSON.stringify({ queued: true }), {
                headers: { 'Content-Type': 'application/json' }
            }));
        }

        return originalFetch.apply(this, arguments);
    };

    // ========================================
    // Public API
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
```

**Step 2: Load in `base.html`**

After the `capacitor-transitions.js` script tag:

```html
<!-- Capacitor Offline Mode (native app only) -->
<script src="{% static 'js/capacitor-offline.js' %}"></script>
```

**Step 3: Add offline banner style update to `base-inline.css`**

Append to native section:

```css
/* Offline banner for native app */
.ios-native-app .offline-banner,
.android-native-app .offline-banner {
    display: none;
    position: fixed;
    top: max(70px, calc(70px + var(--safe-area-inset-top)));
    left: 0;
    right: 0;
    background: #f59e0b;
    color: #000;
    text-align: center;
    padding: 8px 16px;
    font-size: 0.85rem;
    font-weight: 500;
    z-index: 9999;
}
```

**Step 4: Verify**

Run:
```bash
ls -la /Users/ryanpate/myrecoverypal/static/js/capacitor-offline.js
grep "capacitor-offline" /Users/ryanpate/myrecoverypal/templates/base.html
```

Expected: Both found.

**Step 5: Commit**

```bash
git add static/js/capacitor-offline.js templates/base.html static/css/base-inline.css
git commit -m "feat: add offline mode with IndexedDB cache and write queue"
```

---

## Task 11: Sync iOS Project and Verify Build

**Files:**
- Modified by sync: `ios/App/Podfile`, `ios/App/Podfile.lock`

**Step 1: Sync Capacitor**

Run:
```bash
cd /Users/ryanpate/myrecoverypal
npx cap sync ios
```

Expected: Sync completes. Biometric auth pod appears.

**Step 2: Install pods (if sync doesn't auto-run)**

Run:
```bash
cd /Users/ryanpate/myrecoverypal/ios/App
pod install
```

Expected: All pods installed.

**Step 3: Verify Xcode build**

Run:
```bash
cd /Users/ryanpate/myrecoverypal
xcodebuild -workspace ios/App/App.xcworkspace -scheme App \
  -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 16' \
  CODE_SIGNING_REQUIRED=NO CODE_SIGNING_ALLOWED=NO build 2>&1 | tail -5
```

Expected: `BUILD SUCCEEDED`.

**Step 4: Commit synced files**

```bash
git add ios/App/Podfile ios/App/Podfile.lock
git commit -m "chore: sync iOS pods after biometric auth plugin install"
```

---

## Task 12: Final Commit and Push

**Step 1: Check for any uncommitted changes**

Run:
```bash
git status
```

**Step 2: Push to remote**

Run:
```bash
git push origin main
```

---

## Files Summary

### New Files (3)
1. `static/js/capacitor-biometric.js` — biometric auth bridge + settings + journal lock
2. `static/js/capacitor-transitions.js` — page transitions + swipe gestures + pull-to-refresh
3. `static/js/capacitor-offline.js` — IndexedDB caching + write queue + offline detection

### Modified Files (4)
4. `package.json` — `@aparajita/capacitor-biometric-auth` dependency
5. `templates/base.html` — lock overlay, native tab bar, More menu, script loads
6. `static/css/base-inline.css` — lock screen, tab bar, More menu, transitions, offline styles
7. `static/js/capacitor-native.js` — hide hamburger on native, More menu toggle, tab haptics

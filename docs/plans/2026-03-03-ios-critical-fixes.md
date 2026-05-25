# iOS Critical Pre-Submission Fixes

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 5 Apple review blockers: move credentials to iOS Keychain, remove cleartext ATS exception, switch APNs to production, replace native `alert()` with toast UI, and add review notes template.

**Architecture:** Install `@aparajita/capacitor-secure-storage` (same author as biometric plugin, Capacitor 7+, uses iOS Keychain) to replace `@capacitor/preferences` for credential storage. Replace `alert()` calls in IAP code with an in-page toast component. The other 3 fixes are single-line config changes.

**Tech Stack:** Capacitor 7, `@aparajita/capacitor-secure-storage`, iOS Keychain, JavaScript (no framework)

---

### Task 1: Install `@aparajita/capacitor-secure-storage` plugin

**Files:**
- Modify: `package.json`
- Modify: `ios/App/Podfile.lock` (auto-updated by cap sync)

**Step 1: Install the plugin**

Run:
```bash
npm install @aparajita/capacitor-secure-storage
```

**Step 2: Sync iOS project**

Run:
```bash
npx cap sync ios
```

**Step 3: Verify plugin is installed**

Run:
```bash
grep "capacitor-secure-storage" package.json
```
Expected: Shows `"@aparajita/capacitor-secure-storage": "^x.x.x"` in dependencies.

**Step 4: Commit**

```bash
git add package.json package-lock.json ios/
git commit -m "chore: install @aparajita/capacitor-secure-storage for iOS Keychain credential storage"
```

---

### Task 2: Migrate credential storage from Preferences (UserDefaults) to SecureStorage (Keychain)

**Files:**
- Modify: `static/js/capacitor-biometric.js`

The `@aparajita/capacitor-secure-storage` plugin registers as `SecureStorage` in Capacitor. Its API is:
- `SecureStorage.setItem({ key, value })` → stores in iOS Keychain
- `SecureStorage.getItem({ key })` → returns `{ value }` (or `value: null` if not found)
- `SecureStorage.removeItem({ key })` → deletes from Keychain
- `SecureStorage.getSynchronize()` / `SecureStorage.setSynchronize({ flag })` → iCloud sync toggle

Only credentials (username + password) need to move to SecureStorage. The boolean preferences (biometric_login_enabled, journal_lock_enabled) are fine in Preferences — they contain no sensitive data.

**Step 1: Add SecureStorage plugin reference and migrate credential functions**

In `static/js/capacitor-biometric.js`, after the existing `var Preferences = Plugins.Preferences;` line (line 26), add:

```javascript
var SecureStorage = Plugins.SecureStorage;
```

Then update the `if (!Preferences)` guard (lines 33-36) to also warn about SecureStorage:

```javascript
if (!Preferences) {
    console.warn('[Biometric] Preferences plugin not available');
    return;
}

if (!SecureStorage) {
    console.warn('[Biometric] SecureStorage plugin not available — credentials will not be stored securely');
}
```

**Step 2: Update `saveLoginCredentials` to use SecureStorage**

Replace the current `saveLoginCredentials` method (lines 123-127):

```javascript
saveLoginCredentials: function(username, password) {
    if (!SecureStorage) {
        // Fallback to Preferences if SecureStorage unavailable
        return Preferences.set({ key: PREF_LOGIN_USER, value: username }).then(function() {
            return Preferences.set({ key: PREF_LOGIN_PASS, value: password });
        });
    }
    return SecureStorage.setItem({ key: PREF_LOGIN_USER, value: username }).then(function() {
        return SecureStorage.setItem({ key: PREF_LOGIN_PASS, value: password });
    });
},
```

**Step 3: Update `getLoginCredentials` to use SecureStorage**

Replace the current `getLoginCredentials` method (lines 133-143):

```javascript
getLoginCredentials: function() {
    if (!SecureStorage) {
        return Preferences.get({ key: PREF_LOGIN_USER }).then(function(userResult) {
            if (!userResult.value) return null;
            return Preferences.get({ key: PREF_LOGIN_PASS }).then(function(passResult) {
                if (!passResult.value) return null;
                return { username: userResult.value, password: passResult.value };
            });
        }).catch(function() {
            return null;
        });
    }
    return SecureStorage.getItem({ key: PREF_LOGIN_USER }).then(function(userResult) {
        if (!userResult.value) return null;
        return SecureStorage.getItem({ key: PREF_LOGIN_PASS }).then(function(passResult) {
            if (!passResult.value) return null;
            return { username: userResult.value, password: passResult.value };
        });
    }).catch(function() {
        return null;
    });
},
```

**Step 4: Update `clearLoginCredentials` to use SecureStorage**

Replace the current `clearLoginCredentials` method (lines 149-153):

```javascript
clearLoginCredentials: function() {
    // Clear from both stores (handles migration from old Preferences storage)
    var clearPrefs = Preferences.remove({ key: PREF_LOGIN_USER }).then(function() {
        return Preferences.remove({ key: PREF_LOGIN_PASS });
    }).catch(function() {});

    if (!SecureStorage) return clearPrefs;

    var clearSecure = SecureStorage.removeItem({ key: PREF_LOGIN_USER }).then(function() {
        return SecureStorage.removeItem({ key: PREF_LOGIN_PASS });
    }).catch(function() {});

    return Promise.all([clearPrefs, clearSecure]);
},
```

**Step 5: Add migration from old Preferences to SecureStorage on init**

Add this immediately after `MRPBiometric.checkAvailability();` (after line 183):

```javascript
// Migrate credentials from Preferences (UserDefaults) to SecureStorage (Keychain)
if (SecureStorage) {
    Preferences.get({ key: PREF_LOGIN_USER }).then(function(userResult) {
        if (!userResult.value) return; // Nothing to migrate
        Preferences.get({ key: PREF_LOGIN_PASS }).then(function(passResult) {
            if (!passResult.value) return;
            // Copy to Keychain, then remove from UserDefaults
            SecureStorage.setItem({ key: PREF_LOGIN_USER, value: userResult.value }).then(function() {
                return SecureStorage.setItem({ key: PREF_LOGIN_PASS, value: passResult.value });
            }).then(function() {
                Preferences.remove({ key: PREF_LOGIN_USER });
                Preferences.remove({ key: PREF_LOGIN_PASS });
                console.log('[Biometric] Migrated credentials to Keychain');
            });
        });
    }).catch(function() {});
}
```

**Step 6: Commit**

```bash
git add static/js/capacitor-biometric.js
git commit -m "security: move login credentials from UserDefaults to iOS Keychain

Uses @aparajita/capacitor-secure-storage for encrypted credential storage.
Includes automatic migration of existing credentials from Preferences.
Non-sensitive boolean prefs (biometric_login_enabled, journal_lock_enabled)
remain in Preferences as they contain no secrets."
```

---

### Task 3: Remove `cleartext: true` from Capacitor config

**Files:**
- Modify: `capacitor.config.json`

The server URL is already `https://www.myrecoverypal.com`. The `cleartext: true` setting adds an App Transport Security exception that is unnecessary and a red flag for Apple review.

**Step 1: Remove the cleartext line**

In `capacitor.config.json`, change the `server` block from:

```json
"server": {
    "url": "https://www.myrecoverypal.com",
    "cleartext": true
}
```

To:

```json
"server": {
    "url": "https://www.myrecoverypal.com"
}
```

**Step 2: Sync iOS project to propagate the change**

Run:
```bash
npx cap sync ios
```

**Step 3: Commit**

```bash
git add capacitor.config.json ios/
git commit -m "security: remove cleartext ATS exception from Capacitor config

Server already uses HTTPS. The cleartext: true setting added an unnecessary
App Transport Security exception that flags Apple review (Guideline 5.1.1)."
```

---

### Task 4: Switch APNs environment from development to production

**Files:**
- Modify: `ios/App/App/App.entitlements`

**Step 1: Update the entitlements file**

In `ios/App/App/App.entitlements`, change:

```xml
<key>aps-environment</key>
<string>development</string>
```

To:

```xml
<key>aps-environment</key>
<string>production</string>
```

**Step 2: Commit**

```bash
git add ios/App/App/App.entitlements
git commit -m "config: switch APNs environment to production for App Store submission"
```

---

### Task 5: Replace `alert()` calls in IAP code with toast notifications

**Files:**
- Modify: `static/js/capacitor-iap.js`

There are 5 `alert()` calls that need replacing. The app already has a toast system (used by optimistic UI in main.js). We'll add a simple toast function to the IAP module that creates dismissible toast notifications matching the existing app style.

**Step 1: Add toast helper function inside the IAP IIFE**

Add this function right after the `getCSRFToken` function (after line 42), before the `var MRPIAP = {` line:

```javascript
function showIAPToast(message, type) {
    var toast = document.createElement('div');
    toast.className = 'iap-toast iap-toast-' + (type || 'info');
    toast.textContent = message;
    document.body.appendChild(toast);
    // Trigger reflow then add visible class for animation
    toast.offsetHeight;
    toast.classList.add('iap-toast-visible');
    setTimeout(function() {
        toast.classList.remove('iap-toast-visible');
        setTimeout(function() { toast.remove(); }, 300);
    }, 3000);
}
```

**Step 2: Replace all 5 `alert()` calls**

Replace each alert:

1. Line 187: `alert('No subscription plans available at this time. Please try again later.');`
   → `showIAPToast('No subscription plans available. Please try again later.', 'error');`

2. Line 223: `alert('Purchase failed. Please try again.');`
   → `showIAPToast('Purchase failed. Please try again.', 'error');`

3. Line 242: `alert('No previous purchases found.');`
   → `showIAPToast('No previous purchases found.', 'info');`

4. Line 247: `alert('Could not restore purchases. Please try again.');`
   → `showIAPToast('Could not restore purchases. Please try again.', 'error');`

5. Line 253: `alert('Could not load subscription plans. Please try again.');`
   → `showIAPToast('Could not load subscription plans. Please try again.', 'error');`

**Step 3: Add toast CSS to the injected styles**

Append these toast styles to the existing `style.textContent` string (before the final `';`):

```css
.iap-toast { position: fixed; top: calc(20px + env(safe-area-inset-top)); left: 50%; transform: translateX(-50%) translateY(-20px); background: #333; color: white; padding: 12px 20px; border-radius: 10px; font-size: 0.9rem; z-index: 10001; opacity: 0; transition: opacity 0.3s, transform 0.3s; pointer-events: none; max-width: 90%; text-align: center; }
.iap-toast-visible { opacity: 1; transform: translateX(-50%) translateY(0); }
.iap-toast-error { background: #c0392b; }
.iap-toast-info { background: #2d6cb5; }
[data-theme="dark"] .iap-toast { background: #444; }
[data-theme="dark"] .iap-toast-error { background: #e74c3c; }
[data-theme="dark"] .iap-toast-info { background: #4a90d9; }
```

**Step 4: Commit**

```bash
git add static/js/capacitor-iap.js
git commit -m "fix: replace native alert() calls with toast notifications in IAP flow

Native alert() looks non-native and may trigger Apple Guideline 4.0 concerns.
Replaced all 5 alert() calls with animated toast notifications that match
the app's existing design language."
```

---

### Task 6: Bump static file cache-busting version

**Files:**
- Modify: `templates/base.html`

**Step 1: Update all `?v=` query strings**

Find all `?v=20260303` strings in `templates/base.html` and replace with `?v=20260303d` (or the next letter after the current highest). This ensures browsers and CDNs pick up the changed JS files.

Files that changed: `capacitor-biometric.js`, `capacitor-iap.js`

**Step 2: Commit**

```bash
git add templates/base.html
git commit -m "chore: bump static file cache version for biometric + IAP changes"
```

---

### Task 7: Sync iOS project and verify build

**Step 1: Sync Capacitor**

Run:
```bash
npx cap sync ios
```

**Step 2: Verify iOS build compiles clean**

Run:
```bash
xcodebuild -workspace ios/App/App.xcworkspace -scheme App \
  -configuration Release -destination 'generic/platform=iOS' \
  CODE_SIGNING_REQUIRED=NO CODE_SIGNING_ALLOWED=NO build 2>&1 | tail -5
```

Expected: `BUILD SUCCEEDED`

**Step 3: Final commit if any sync changes**

```bash
git add ios/
git commit -m "chore: sync Capacitor iOS project after critical fixes"
```

---

## Summary of Changes

| Fix | Guideline | Risk |
|-----|-----------|------|
| Credentials → iOS Keychain | 5.1.1 (Data Security) | **Rejection likely** without fix |
| Remove cleartext ATS exception | 5.1.1 (Data Security) | Moderate flag |
| APNs → production | Required for push | Push won't work in prod without this |
| Replace alert() with toasts | 4.0 (Design) | Minor flag, improves UX |
| Cache busting | N/A | Prevents stale JS on existing users |

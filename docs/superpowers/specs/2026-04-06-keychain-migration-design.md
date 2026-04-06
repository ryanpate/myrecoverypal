# iOS Keychain Credential Migration

**Date:** 2026-04-06
**Goal:** Move login credentials from `@capacitor/preferences` (UserDefaults — plaintext) to `@aparajita/capacitor-secure-storage` (iOS Keychain — encrypted) for Apple Guideline 5.1.1 compliance.
**Context:** The `@aparajita/capacitor-secure-storage` plugin is already in package.json but not wired up. 154 users may have credentials stored in Preferences that need transparent migration.

---

## Changes

### File: `static/js/capacitor-biometric.js`

**1. Add SecureStorage reference at init**

At the top of the IIFE (where `Preferences` is assigned from `Plugins`), also get `SecureStorage`:

```javascript
var SecureStorage = Plugins.SecureStorage;
```

**2. Migrate existing credentials on init**

After plugin references are set up, before any credential reads, add a one-time migration:

```javascript
(function migrateToSecureStorage() {
    if (!SecureStorage || !Preferences) return;
    Preferences.get({ key: PREF_LOGIN_USER }).then(function(result) {
        if (!result.value) return; // No old credentials — nothing to migrate
        var oldUser = result.value;
        Preferences.get({ key: PREF_LOGIN_PASS }).then(function(passResult) {
            var oldPass = passResult.value || '';
            // Write to Keychain
            SecureStorage.setItem({ key: PREF_LOGIN_USER, value: oldUser }).then(function() {
                return SecureStorage.setItem({ key: PREF_LOGIN_PASS, value: oldPass });
            }).then(function() {
                // Delete from plaintext storage
                Preferences.remove({ key: PREF_LOGIN_USER });
                Preferences.remove({ key: PREF_LOGIN_PASS });
                console.log('[Biometric] Migrated credentials to Keychain');
            });
        });
    }).catch(function() {});
})();
```

**3. Update credential functions to use SecureStorage**

`saveLoginCredentials(username, password)`:
- Change `Preferences.set` → `SecureStorage.setItem` for both PREF_LOGIN_USER and PREF_LOGIN_PASS

`getLoginCredentials()`:
- Change `Preferences.get` → `SecureStorage.getItem` for both keys

`clearLoginCredentials()`:
- Change `Preferences.remove` → `SecureStorage.removeItem` for both keys
- Also clear from old Preferences location (belt-and-suspenders for migration)

**4. Leave these on Preferences (non-sensitive booleans):**
- `isBiometricLoginEnabled` / `setBiometricLoginEnabled` — reads/writes PREF_BIO_LOGIN
- `isJournalLockEnabled` / `setJournalLockEnabled` — reads/writes PREF_JOURNAL_LOCK

### SecureStorage Plugin API

```javascript
SecureStorage.setItem({ key: 'key', value: 'value' })  // Promise<void>
SecureStorage.getItem({ key: 'key' })                   // Promise<{ value: string }>
SecureStorage.removeItem({ key: 'key' })                // Promise<void>
```

On iOS: uses Keychain. On Android: EncryptedSharedPreferences. On web: localStorage fallback.

### Post-Change: Native Sync

```bash
npx cap sync ios
```

Copies web assets and syncs SecureStorage native plugin code to the Xcode project. Required before archiving the next App Store build.

### What does NOT change
- Biometric auth flow (Face ID/Touch ID prompt unchanged)
- Journal lock toggle storage (stays in Preferences)
- Biometric enable/disable toggle (stays in Preferences)
- Any server-side code
- The credential keys (PREF_LOGIN_USER, PREF_LOGIN_PASS) — same keys, different store

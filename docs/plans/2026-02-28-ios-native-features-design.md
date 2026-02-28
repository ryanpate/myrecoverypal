# iOS Native Features Design

**Date:** 2026-02-28
**Goal:** Make the iOS app feel premium and worth downloading vs using the website
**Scope:** Face ID, iOS-style navigation, swipe gestures, native transitions, offline mode

---

## 1. Face ID / Biometric Lock

Two-layer biometric protection for privacy.

### App Lock (outer layer)
- On launch and resume from background after 5+ minutes, show full-screen lock overlay
- User taps "Unlock" -> Face ID / Touch ID prompt
- Falls back to device passcode on biometric failure
- Toggle in settings: "Lock App with Face ID" (off by default)
- Lock state stored via `@capacitor/preferences`

### Journal Lock (inner layer)
- Navigating to `/journal/` triggers biometric check even if app is unlocked
- Separate toggle: "Require Face ID for Journal" (on by default when app lock enabled)
- Denied -> redirected to previous page

### Plugin
- `@aparajita/capacitor-biometric-auth` (Capacitor 7 compatible)

### Files
- New: `static/js/capacitor-biometric.js` — biometric auth bridge
- Modify: `templates/base.html` — lock overlay HTML + script load
- Modify: `static/css/base-inline.css` — lock screen styles
- Modify: `apps/journal/templates/journal/` — biometric gate before render

---

## 2. iOS-Style Navigation

Replace hamburger menu with native-feeling iOS tab bar. Web version unchanged.

### Bottom Tab Bar (replaces `mobile-bottom-nav`)
- 5 tabs: **Feed** | **Groups** | **Coach** | **Journal** | **More**
- iOS appearance: filled/outline icon states, accent color on active, gray on inactive
- Haptic on tab switch
- Badge dots for unread items on Feed/Groups

### "More" Tab
- Settings-style grouped list with rounded cards and chevrons
- Items: Profile, Milestones, Community, Challenges, Messages, Notifications, Settings
- Replaces hamburger entirely on native

### Top Nav (simplified on native)
- App logo/title left, notification bell + avatar right
- No hamburger button

### Guard
- All changes wrapped in `.ios-native-app` / `.android-native-app` CSS
- Web version completely unchanged

### Files
- Modify: `templates/base.html` — native tab bar HTML, hide hamburger on native
- Modify: `static/css/base-inline.css` — iOS tab bar styles, More menu styles
- Modify: `static/js/capacitor-native.js` — haptic on tab switch, badge count sync

---

## 3. Swipe Gestures + Native Transitions

### Swipe Gestures
- **Edge swipe right** -> navigate back (iOS standard)
- **Swipe left on post cards** -> reveal action buttons (Share, Save) — iOS mail-style
- **Pull-to-refresh** -> enhance with rubber-band CSS physics

### Native Page Transitions
- Intercept link clicks inside native app
- Slide-in-from-right (forward), slide-out-to-right (back)
- Use View Transition API (iOS 18+), fall back to CSS animations
- Duration: 250ms (matches iOS UIKit)

### Implementation
- Pure CSS + JS, no native plugin needed
- Guard: only active when `body.ios-native-app` or `body.android-native-app` present

### Files
- New: `static/js/capacitor-transitions.js` — page transition + swipe gesture handler
- Modify: `static/css/base-inline.css` — transition keyframes, swipe action styles

---

## 4. Offline Mode

Cache-first for reads, queue writes for sync.

### Works Offline
- Social feed (last 50 posts in IndexedDB)
- Journal entries (full local copy, syncs when online)
- Daily check-in (queued, submitted on reconnect)
- Profile data, group list, milestones
- AI Coach — shows previous conversation, "Offline" state for new messages

### Requires Connectivity
- Creating posts with images (queued as draft)
- Following/unfollowing
- AI Coach new messages
- Push notifications

### Implementation
- Enhanced service worker for cache-first strategy on API responses
- IndexedDB for posts and journal entries
- `@capacitor/preferences` for small settings data
- Background sync via `@capacitor/app` state listener — flush write queue on foreground
- Offline indicator: subtle top banner "You're offline — changes will sync when connected"

### Files
- Modify: `static/js/sw.js` — enhanced service worker caching
- New: `static/js/capacitor-offline.js` — IndexedDB storage, write queue, sync logic
- Modify: `templates/base.html` — offline indicator banner
- Modify: `static/css/base-inline.css` — offline banner styles

---

## Priority Order

1. **Face ID** — highest user value, privacy is critical for recovery app
2. **iOS Navigation** — biggest visual difference from "just a website"
3. **Native Transitions** — makes every interaction feel native
4. **Offline Mode** — most complex, biggest differentiator

## Architecture Note

All features guard on `window.Capacitor.isNativePlatform()` — zero impact on the web version. CSS changes scoped to `.ios-native-app` / `.android-native-app` body classes set by `capacitor-native.js`.

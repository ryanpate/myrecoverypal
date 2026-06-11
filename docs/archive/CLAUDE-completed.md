# CLAUDE.md — Archived Completed Sections

These sections were completed and moved out of CLAUDE.md to keep it lean. Kept for historical reference; not active guidance.


---

## [Archived] Immediate TODOs for Beta Success (all complete)

## Immediate TODOs for Beta Success

### CRITICAL - User Acquisition (ALL COMPLETE)
- [x] **Onboarding wizard** - 5-step wizard with recovery stage, interests, profile, privacy, and smart user matching
- [x] **Suggested users** - Matching algorithm uses recovery_stage and interests for better connections
- [x] **Surface invite codes** - Added "Invite Friends" to quick actions, edit profile, and mobile menu
- [x] **Share buttons** - Milestone sharing on milestones page, celebration modal, and profile cards

### HIGH - Retention (ALL COMPLETE)
- [x] **Welcome email sequence** - Day 1, 3, 7 engagement emails via Celery Beat
- [x] **Push notification triggers** - Integrated with all notification types (logging mode, enable FCM/APNs when ready)
- [x] **Daily check-in reminder** - Sent at 5 PM to users with prior check-ins
- [x] **Weekly digest** - Sent Sundays at 10:30 AM with activity summary

### MEDIUM - Analytics (ALL COMPLETE)
- [x] **Basic funnel tracking** - Google Analytics G-81SZGNRESW already integrated
- [x] **Admin dashboard** - User engagement metrics at `/admin/dashboard/`
- [x] **A/B testing** - Onboarding variations at `/admin/dashboard/ab-tests/`

---


---

## [Archived] SEO Landing Pages & Blog Posts (all complete)

### SEO Landing Pages - ✅ ALL COMPLETE
Keyword-targeted landing pages:

| Page | Target Keywords | Status |
|------|-----------------|--------|
| `/alcohol-recovery-app/` | alcohol recovery app, sobriety app | ✅ Done |
| `/sober-grid-alternative/` | sober grid alternative | ✅ Done |
| `/drug-addiction-recovery-app/` | drug addiction app, NA app | ✅ Done |
| `/sobriety-counter-app/` | sobriety counter, sober day tracker | ✅ Done |
| `/sobriety-calculator/` | sobriety calculator, how long sober, clean time calculator | ✅ Done |
| `/free-aa-app/` | AA app, 12 step app, free AA meeting finder | ✅ Done |
| `/opioid-recovery-app/` | opioid recovery, fentanyl recovery app | ✅ Done |
| `/gambling-addiction-app/` | gambling addiction help, gambling recovery | ✅ Done |
| `/mental-health-recovery-app/` | mental health support app, anxiety recovery | ✅ Done |

### SEO Blog Posts - ✅ ALL COMPLETE
High-volume keyword blog posts (83K combined monthly searches):

| Blog Post | Target Keyword | Monthly Searches | Status |
|-----------|----------------|------------------|--------|
| How Long Does Alcohol Withdrawal Last? | alcohol withdrawal timeline | 22K/mo | ✅ Done |
| Signs of Alcoholism: Self-Assessment Guide | signs of alcoholism | 18K/mo | ✅ Done |
| How to Stop Drinking: Step-by-Step Guide | how to stop drinking | 14K/mo | ✅ Done |
| What is Sober Curious? Complete Guide | sober curious | 12K/mo | ✅ Done |
| High-Functioning Alcoholic: Signs & Help | high functioning alcoholic | 9K/mo | ✅ Done |
| Dopamine Detox for Addiction Recovery | dopamine detox addiction | 8K/mo | ✅ Done |

**Blog post URLs:**
- `/blog/how-long-does-alcohol-withdrawal-last/`
- `/blog/signs-of-alcoholism-self-assessment/`
- `/blog/how-to-stop-drinking-alcohol-guide/`
- `/blog/what-is-sober-curious-guide/`
- `/blog/high-functioning-alcoholic-signs-help/`
- `/blog/dopamine-detox-addiction-recovery/`


---

## [Archived] App Store Presence — completed detail

### HIGH - App Store Presence
**Critical for discovery - competitors get most users from app stores**

#### Completed - Code & Build
- [x] Account deletion feature (required by both stores) - `/accounts/delete-account/`
- [x] Capacitor push notification client-side bridge (`static/js/capacitor-push.js`)
- [x] Capacitor origins added to CSRF_TRUSTED_ORIGINS and CORS_ALLOWED_ORIGINS
- [x] Service worker guarded in native context (prevents stale content)
- [x] Signing keys added to `.gitignore`
- [x] Native iOS/Android projects tracked in git (removed from `.gitignore`)
- [x] Android: Release signing keystore generated and configured in `build.gradle`
- [x] Android: Release AAB built (`android/app/build/outputs/bundle/release/app-release.aab`, 3.4 MB)
- [x] iOS: Info.plist updated (background modes, camera/photo/FaceID privacy descriptions)
- [x] iOS: AppDelegate.swift updated with push notification token forwarding
- [x] iOS: Xcode 26.2 compatibility fix (SUPPORTED_PLATFORMS in project.pbxproj)
- [x] iOS: Release build verified (compiles clean)
- [x] iOS: Native features layer (`static/js/capacitor-native.js`) — haptics, native share sheet, keyboard tracking, app state, back button handler
- [x] iOS: RevenueCat/StoreKit 2 IAP bridge (`static/js/capacitor-iap.js`) — purchase flow, restore, sync with Django backend
- [x] iOS: Server-side iOS subscription sync endpoint (`/accounts/api/ios-subscription/sync/`)
- [x] iOS: `subscription_source` field on Subscription model (stripe/apple/manual) — migration 0020
- [x] iOS: Stripe UI hidden / IAP shown inside native app via `.stripe-only` / `.iap-only` CSS classes
- [x] iOS: Templates updated — pricing.html, recovery_coach.html, subscription_management.html
- [x] iOS: APNs key extraction in `start.sh` from `APNS_KEY_CONTENT` env var
- [x] iOS: Capacitor plugins installed (haptics, share, app, keyboard, browser, local-notifications, preferences, RevenueCat, biometric-auth)
- [x] iOS: `capacitor.config.json` updated with Keyboard + LocalNotifications config
- [x] iOS: Face ID / biometric login (`static/js/capacitor-biometric.js`) — biometric sign-in on login page (credential storage), journal lock, settings toggles on edit profile page
- [x] iOS: Native-styled hamburger menu — iOS grouped-list cards, chevrons, blur backdrop, FA icons (replaced tab bar)
- [x] iOS: Page transitions + swipe gestures (`static/js/capacitor-transitions.js`) — edge swipe back, 250ms slide transitions, View Transition API support (iOS 18+), pull-to-refresh
- [x] iOS: Offline mode (`static/js/capacitor-offline.js`) — IndexedDB cache for posts/journal, write queue with auto-flush on reconnect, fetch interceptor for cache-first reads

#### Pre-Submission Fixes (Priority: CRITICAL for Apple Approval)
- [x] **Move credential storage from `@capacitor/preferences` to iOS Keychain** ✅ Already implemented — `capacitor-biometric.js` uses `@aparajita/capacitor-secure-storage` (Keychain) as primary with Preferences fallback. Transparent migration at startup moves old plaintext credentials to Keychain and deletes from UserDefaults.
- [x] **Remove `"cleartext": true` from `capacitor.config.json`** ✅ Already clean — not present in config
- [x] **Change `aps-environment` from `development` to `production`** ✅ Already set to production in App.entitlements
- [x] **Replace `alert()` calls in `capacitor-iap.js` with toast/modal UI** ✅ Already cleaned up — no alert() calls found
- [ ] **Add Apple review notes template** to App Store Connect: explain Capacitor as legitimate native framework, list all native features (Face ID, haptics, share sheet, push, swipe gestures, transitions, offline mode), include IAP sandbox testing instructions, note health disclaimer modal and block/report moderation.

#### High-Impact Native Features (Strengthen Guideline 4.2 Compliance)
- [x] **Add WidgetKit sobriety counter widget** (Swift native extension) — displays days sober on home screen with small (day count + milestone countdown) and medium (progress ring with years/months breakdown, sobriety date, milestone progress bar) sizes. App Group `group.com.myrecoverypal.app` shared UserDefaults, WidgetBridge Capacitor plugin for JS↔native data sync, calendar-based milestone calculations (handles leap years). Widget Extension target with `DEVELOPMENT_TEAM` configured.
- [x] **Wire local notification scheduling to sobriety milestones** ✅ Schedules 9 AM notifications for upcoming milestones (7, 14, 30, 60, 90, 180, 365 days) via LocalNotifications plugin in capacitor-native.js

#### Remaining - Manual Steps
- [ ] **Android: Upload AAB to Google Play Console** (account ready)
- [ ] **Android: Complete store listing** (screenshots, description, data safety)
- [ ] **Android: Submit for review** (expect 1-3 days)
- [ ] **iOS: Create APNs Auth Key** in Apple Developer Portal → download `.p8` file
- [ ] **iOS: Configure Xcode signing** (set team, add Push Notifications + In-App Purchase capabilities)
- [x] **iOS: Set up RevenueCat** — project created, iOS app added, `premium` entitlement, default offering with `$rc_monthly` + `$rc_annual` packages, In-App Purchase Key (.p8) uploaded, API key copied
- [x] **iOS: Create subscription products** in App Store Connect — Premium Monthly ($4.99, `com.myrecoverypal.premium.monthly`) and Premium Yearly ($29.99, `com.myrecoverypal.premium.yearly`) in "Premium" subscription group
- [x] **iOS: Create demo account** (`review@myrecoverypal.com` / `applereview`) with sample data via `setup_review_account` management command
- [x] **iOS: Create App Store Connect record** — app created with bundle ID `com.myrecoverypal.app`
- [ ] **iOS: Set Railway env vars** — `APNS_KEY_CONTENT`, `APNS_KEY_ID`, `APNS_TEAM_ID`, `REVENUECAT_IOS_API_KEY`
- [x] **iOS: Archive and submit** via Xcode → App Store Connect (v1.0.0 submitted 2026-03-05, v1.1.0 submitted 2026-04-06)
- [x] **iOS: Complete App Store metadata** (screenshots, description, privacy nutrition labels, review notes)
- [x] App Store Optimization (ASO): keywords, screenshots, description
- [ ] Request reviews from existing users
- [x] Smart App Banner active in `base.html` with App Store ID 6760084657

#### App Store Listing Details
- **App name:** MyRecoveryPal
- **Bundle ID:** `com.myrecoverypal.app`
- **Category:** Health & Fitness
- **Secondary Category:** Social Networking
- **Version:** 1.0.0
- **Subtitle:** Recovery Community & AI Coach
- **Short description:** "Connect with others in recovery. Social feed, groups, AI coach & more."
- **Privacy policy:** `https://www.myrecoverypal.com/privacy/`
- **Target age:** 17+ (references alcohol/drug use in recovery context)
- **Keywords:** sobriety, recovery, sober, addiction, AA, NA, support, community, coach, tracker, journal, mental health, 12 step
- **Apple review notes:** Emphasize native features (Face ID login, native-styled menu with haptics, share sheet, push, swipe gestures, page transitions, offline mode, keyboard, WidgetKit home screen widget), Capacitor as legitimate native framework, IAP sandbox testing instructions, health disclaimer modal, block/report moderation

#### iOS Native Features (Guideline 4.2 Compliance)
| Feature | Plugin | File |
|---------|--------|------|
| Haptic feedback (like, check-in, share, follow) | `@capacitor/haptics` | `capacitor-native.js` |
| Native share sheet | `@capacitor/share` | `capacitor-native.js` |
| Keyboard height tracking + bottom nav hide | `@capacitor/keyboard` | `capacitor-native.js` |
| App state change (refresh on foreground) | `@capacitor/app` | `capacitor-native.js` |
| Back button handler (Android) | `@capacitor/app` | `capacitor-native.js` |
| Local notification scheduling | `@capacitor/local-notifications` | `capacitor-native.js` |
| In-app purchases (StoreKit 2) | `@revenuecat/purchases-capacitor` | `capacitor-iap.js` |
| Push notifications | `@capacitor/push-notifications` | `capacitor-push.js` |
| Face ID / Touch ID login + journal lock | `@aparajita/capacitor-biometric-auth` | `capacitor-biometric.js` |
| Native-styled hamburger menu (grouped cards, chevrons, blur) | Pure CSS/JS | `capacitor-native.js` + `base-inline.css` |
| Hamburger icon swap (FA bars ↔ xmark via MutationObserver) | Pure JS | `capacitor-native.js` |
| Page transitions (250ms slide) | Pure CSS/JS + View Transition API | `capacitor-transitions.js` |
| Edge swipe back gesture | Pure JS | `capacitor-transitions.js` |
| Pull-to-refresh (enhanced) | Pure JS | `capacitor-transitions.js` |
| Offline mode (IndexedDB + write queue) | Pure JS | `capacitor-offline.js` |
| Ultra-minimal nav bar (icon only, bell + badge) | Pure CSS/JS | `capacitor-native.js` + `base-inline.css` |
| 5-tab bottom bar (Feed, Coach, Check-in, Alerts, Profile) | Pure CSS/JS | `capacitor-native.js` + `base-inline.css` + `base.html` |
| Animated splash/loading overlay (sessionStorage, once per session) | Pure CSS/JS | `capacitor-native.js` + `base-inline.css` + `base.html` |
| Notification bell with red badge (99+ cap, live updates) | Pure JS | `capacitor-native.js` + `base-inline.css` |
| WidgetKit sobriety counter (small + medium, progress ring, milestones) | Native Swift WidgetKit | `SobrietyCounterWidget/` (Swift extension) |

#### iOS IAP Architecture
```
User taps Subscribe → capacitor-iap.js → RevenueCat SDK → Apple StoreKit 2
                                        ↓ (on success)
                              POST /accounts/api/ios-subscription/sync/
                                        ↓
                              Django Subscription model updated
                              (subscription_source = 'apple')
```
- Stripe buttons hidden on iOS via `.ios-native-app .stripe-only { display: none }`
- IAP buttons shown on iOS via `.ios-native-app .iap-only { display: block }`
- Body class `ios-native-app` set by `capacitor-native.js` on platform detection
- Server-side sync does NOT overwrite active Stripe subscriptions

#### Keystore Info (SAVE SECURELY)
- **File:** `android/app/myrecoverypal-release.keystore` (gitignored)
- **Alias:** `myrecoverypal`
- **Properties:** `android/keystore.properties` (gitignored)
- **WARNING:** Lost keystore = cannot update the app. Back up immediately.

---


---

## [Archived] Recommended Features for Better UX (all complete)

## Recommended Features for Better UX

### HIGH PRIORITY - Quick Wins (ALL COMPLETE)

| Feature | Impact | Effort | Status |
|---------|--------|--------|--------|
| ~~One-tap check-in widget~~ | High | Low | ✅ Done |
| ~~Milestone celebrations~~ | High | Low | ✅ Done |
| ~~Streak indicator~~ | High | Low | ✅ Done |
| ~~Quick reactions (❤️🙏💪🎉)~~ | Medium | Low | ✅ Done |
| ~~Pull-to-refresh~~ | Medium | Low | ✅ Done |

### MEDIUM PRIORITY - Retention Boosters

| Feature | Impact | Effort | Status |
|---------|--------|--------|--------|
| ~~Daily gratitude prompt~~ | High | Medium | ✅ Done |
| ~~Sobriety counter widget~~ | High | Medium | ✅ Done |
| ~~Meeting reminders~~ | High | Medium | ✅ Done |
| ~~Progress visualizations~~ | Medium | Medium | ✅ Done |
| ~~Accountability nudges~~ | Medium | Medium | ✅ Done |

### LOWER PRIORITY - Polish (ALL COMPLETE ✅)

| Feature | Impact | Effort | Status |
|---------|--------|--------|--------|
| ~~Dark mode~~ | Medium | Medium | ✅ Done |
| ~~Skeleton loaders~~ | Low | Low | ✅ Done |
| ~~Optimistic UI~~ | Medium | Medium | ✅ Done |
| ~~Infinite scroll~~ | Low | Medium | ✅ Done |
| ~~Image compression~~ | Low | Low | ✅ Done |

### Technical Debt to Address

- [x] **Service worker caching strategy** - ✅ COMPLETE. Added API exclusions, network-first for HTML, standalone offline page
- [ ] **Offline support** - Allow viewing cached content when offline
- [ ] **Performance audit** - Check for N+1 queries, slow page loads

---

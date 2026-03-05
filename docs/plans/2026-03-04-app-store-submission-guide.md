# App Store Submission Guide — MyRecoveryPal

> **Last Updated:** 2026-03-04
> **Bundle ID:** `com.myrecoverypal.app`
> **Version:** 1.0.0
> **Team ID:** 454YNT65J3

---

## PHASE 1: Pre-Submission Setup — ✅ COMPLETE

### Step 1: Create the Demo Review Account ✅

Go to `https://www.myrecoverypal.com/accounts/register/` and create:

- **Email:** `review@myrecoverypal.com`
- **Username:** `applereview`
- **Password:** 2026AppStore!

Then populate it with data:

- Set a sobriety date (e.g., 90+ days ago so milestones show)
- Complete 3-5 daily check-ins (different moods)
- Write 2 journal entries
- Create 1-2 social posts
- Follow a few existing users
- Join 1-2 groups
- Send 1-2 messages to the AI Coach

**Activate Premium on this account** via Django admin (`/admin/`) — find their Subscription and set `tier=premium`, `status=active`. The reviewer needs to see all premium features without buying.

### Step 2: Create App Store Connect Record ✅

1. Go to [App Store Connect](https://appstoreconnect.apple.com)
2. **My Apps** > **+** > **New App**
3. Fill in:
   - **Platform:** iOS
   - **Name:** `MyRecoveryPal`
   - **Primary Language:** English (U.S.)
   - **Bundle ID:** `com.myrecoverypal.app` (must match Xcode)
   - **SKU:** `myrecoverypal-ios-001`
   - **User Access:** Full Access

### Step 3: Set Up In-App Purchases in App Store Connect ✅

1. Go to your app > **Monetization** > **Subscriptions**
2. Create a **Subscription Group** called `Premium`
3. Add two subscriptions:

**Subscription 1 — Monthly:**

| Field | Value |
|-------|-------|
| Reference Name | `Premium Monthly` |
| Product ID | `com.myrecoverypal.premium.monthly` |
| Price | **$4.99** (Tier 3) |
| Duration | **1 Month** |
| Display Name | `Premium Monthly` |
| Description | `Full access to AI Coach, unlimited groups, journal export, and analytics.` |

**Subscription 2 — Yearly:**

| Field | Value |
|-------|-------|
| Reference Name | `Premium Yearly` |
| Product ID | `com.myrecoverypal.premium.yearly` |
| Price | **$29.99** (Tier 20) |
| Duration | **1 Year** |
| Display Name | `Premium Yearly` |
| Description | `All Premium features for a full year. Save over 50% vs monthly.` |

4. For each subscription, add **Subscription Pricing** and select your territories
5. Under **Review Information**, add a screenshot of the subscription purchase screen

### Step 4: Set Up RevenueCat ✅

1. Go to [RevenueCat Dashboard](https://app.revenuecat.com)
2. Create a new project: `MyRecoveryPal`
3. Add an iOS app with bundle ID `com.myrecoverypal.app`
4. Create an **Entitlement** called `premium`
5. Create **Offerings** > Default offering with two packages:
   - `$rc_monthly` → `com.myrecoverypal.premium.monthly`
   - `$rc_annual` → `com.myrecoverypal.premium.yearly`
6. Copy the **iOS API Key**
7. Set it on Railway: `REVENUECAT_IOS_API_KEY=<your-key>`
8. Connect App Store Connect to RevenueCat via **Shared Secret** (App Store Connect > General > App Information > App-Specific Shared Secret)

### Step 5: Set Up APNs (Push Notifications)

1. Go to [Apple Developer Portal](https://developer.apple.com/account) > **Certificates, Identifiers & Profiles** > **Keys**
2. Create a new key with **Apple Push Notifications service (APNs)** enabled
3. Download the `.p8` file (you can only download once)
4. Note the **Key ID** (10 characters)
5. Set these on Railway:

```
APNS_KEY_CONTENT=<paste the raw .p8 file content>
APNS_KEY_ID=<10-char key ID>
APNS_TEAM_ID=454YNT65J3
```

---

## PHASE 2: App Store Metadata

### Step 6: App Information Tab

| Field | Value |
|-------|-------|
| **Name** | `MyRecoveryPal` |
| **Subtitle** | `Sober Community & AI Coach` (27 chars) |
| **Category** | Health & Fitness |
| **Secondary Category** | Social Networking |
| **Content Rights** | Does not contain third-party content |
| **Age Rating** | 17+ (references alcohol/drug use in a recovery context) |

**Age Rating Questionnaire answers:**

- Infrequent/Mild references to Alcohol, Tobacco, or Drugs: **Yes** (recovery context)
- Medical/Treatment Information: **Yes** (recovery resources)
- User-generated content: **Yes** (social feed, groups)
- Unrestricted Web Access: **No**
- Everything else: **No**

### Step 7: Pricing and Availability

- **Price:** Free (with in-app purchases)
- **Availability:** All territories (or start with US/UK/CA/AU)
- **Pre-Orders:** No (submit for immediate release)

### Step 8: Version Information — Text Fields

**Promotional Text** (170 chars, can update anytime without new build):

```
Join a growing recovery community. Track sobriety, check in daily, connect with others, and chat with Anchor, your AI recovery coach. Start your 14-day free trial.
```

**Description** (front-load the first 252 characters — that's what shows before "more"):

```
MyRecoveryPal is a social recovery platform where people in recovery connect, support each other, and build a sober life together. Track your sobriety with a home screen widget, check in daily, join recovery groups, and chat with Anchor — your AI recovery coach.

YOUR RECOVERY CIRCLE
Follow others in recovery. Share milestones, encouragement, and honest reflections on a social feed built for people who understand what you're going through. React with support, comment, and build real connections.

AI RECOVERY COACH — ANCHOR
Talk to Anchor anytime — day or night. Anchor understands your recovery journey, remembers your context, and helps you work through cravings, tough moments, and daily reflections. 3 free messages to try, then unlimited with Premium.

SOBRIETY TRACKING
See your days, months, and years of sobriety at a glance — right on your home screen with our WidgetKit widget. Track milestones, celebrate anniversaries, and watch your progress grow.

DAILY CHECK-INS
Log your mood, cravings, energy, and gratitude every day. Build streaks, spot patterns in your recovery, and stay accountable.

RECOVERY GROUPS
Join public groups by addiction type, recovery stage, or interests. Start private groups for your circle. Post discussions, share resources, and support each other.

PRIVACY FIRST
Your journal is always private — never shared, never visible to other users. You control what's public: your sobriety date, your profile, your posts.

PREMIUM FEATURES ($4.99/mo or $29.99/yr with 14-day free trial)
- Anchor AI Coach: 20 messages per day
- Unlimited groups including private groups
- Unlimited journal with CSV export
- 90-day mood, craving, and energy analytics
- Premium badge on your profile

FREE FEATURES
- Social feed, messaging, and following
- Daily check-ins with streaks
- Join up to 5 groups
- 30-day journal
- 3 AI Coach trial messages
- Home screen sobriety widget
- Face ID login

Built by people in recovery, for people in recovery.
```

**Keywords** (100 characters, comma-separated, no spaces after commas — don't repeat words from title/subtitle):

```
sobriety,recovery,sober,addiction,AA,NA,12 step,tracker,journal,mental health,clean time,support
```

(96 characters)

**What's New** (for version 1.0.0):

```
Welcome to MyRecoveryPal — a social recovery community built by and for people in recovery.

Track your sobriety with a home screen widget, connect with others on the recovery feed, check in daily, and chat with Anchor, your AI recovery coach. Face ID login, offline support, and push notifications are all built in.

This is version 1.0. We're a small, growing community and we'd love for you to be part of it.
```

**URLs:**

| Field | URL |
|-------|-----|
| Support URL | `https://www.myrecoverypal.com/about/` |
| Marketing URL | `https://www.myrecoverypal.com/` |
| Privacy Policy URL | `https://www.myrecoverypal.com/privacy/` |

### Step 9: Screenshots

You need screenshots at **1320 x 2868 px** (iPhone 6.9" — covers all iPhone sizes).

Take these 6 screenshots on a physical iPhone (or Simulator with iPhone 15 Pro Max / 16 Pro Max):

| # | Screen | What to show | Why |
|---|--------|-------------|-----|
| 1 | Social Feed | Active feed with posts, reactions, suggested users | Hero shot — this is what users see in search results |
| 2 | Sobriety Widget | Home screen with the WidgetKit widget visible | Shows native quality, unique differentiator |
| 3 | AI Coach (Anchor) | Chat conversation with helpful response | Premium feature highlight |
| 4 | Daily Check-in | Check-in form with mood, cravings, gratitude | Core engagement loop |
| 5 | Progress/Milestones | Sobriety counter ring + milestone cards | Emotional hook |
| 6 | Groups | Group list or group detail with active posts | Social proof |

**Tips:**

- Use the review account with real-looking data
- Make sure the sobriety counter shows an impressive number (set date far back)
- Crop out the status bar time or set it to 9:41 (Apple's standard)
- No text overlays needed, but if you add them keep it minimal

**iPad screenshots:** Only required if you support iPad. If the app works on iPad through Capacitor, you'll need **2064 x 2752 px** screenshots too.

---

## PHASE 3: App Review Information

### Step 10: App Review Notes (Critical for Approval)

Paste this into the **App Review Notes** field in App Store Connect:

```
DEMO ACCOUNT
Email: review@myrecoverypal.com
Password: [YOUR PASSWORD HERE]
This account has Premium features active and sample data populated.

ABOUT THE APP
MyRecoveryPal is built with Capacitor 7, an Apple-supported native
framework. It is NOT a simple website wrapper. The app includes
extensive native iOS features:

NATIVE FEATURES
- Face ID / Touch ID login (credentials stored in iOS Keychain via
  @aparajita/capacitor-secure-storage)
- WidgetKit home screen widget (small + medium sizes) showing sobriety
  days, milestone countdown, and progress ring
- Haptic feedback on likes, check-ins, follows, and shares
- Native iOS share sheet for posts and milestones
- Push notifications via APNs
- Offline mode with IndexedDB caching and write queue
- Edge swipe-back gesture with 250ms iOS-style page transitions
- Pull-to-refresh on all content pages
- iOS-styled navigation with frosted glass blur backdrop
- 5-tab bottom navigation bar (Feed, Coach, Check-in, Alerts, Profile)
- Animated splash screen overlay
- Keyboard height tracking (hides bottom nav)

IN-APP PURCHASES
Monthly ($4.99) and Yearly ($29.99) Premium subscriptions via
StoreKit 2 / RevenueCat. To test: use a Sandbox Apple ID and tap
any "Go Premium" button. "Restore Purchases" is available on the
pricing page and subscription management page.

New users receive a 14-day free trial automatically.

HEALTH DISCLAIMER
A health disclaimer appears before users interact with the AI Coach
(Anchor). It states the app is not a substitute for professional
treatment. Crisis resources (988 Suicide & Crisis Lifeline, 741741
Crisis Text Line) are displayed on the AI Coach page.

CONTENT MODERATION
User-generated posts include block and report functionality.

ACCOUNT DELETION
Available in-app: Profile menu > Delete Account
Direct URL: myrecoverypal.com/accounts/delete-account/

PRIVACY POLICY
Accessible at myrecoverypal.com/privacy/ — reachable without login.
```

### Step 11: Sign-In Information

- **Sign-in required:** Yes
- **Username:** `review@myrecoverypal.com`
- **Password:** `[your password]`

### Step 12: Contact Information

Fill in your name, phone number, and email for Apple to reach you if they have questions during review.

---

## PHASE 4: App Privacy (Privacy Nutrition Labels)

### Step 13: App Privacy Questionnaire

In App Store Connect, go to **App Privacy** and answer:

**Does your app collect data?** Yes

**Data types to declare:**

| Data Type | Linked to User | Used for Tracking | Purpose |
|-----------|---------------|-------------------|---------|
| Contact Info > Email Address | Yes | No | App Functionality |
| Contact Info > Name | Yes | No | App Functionality |
| Health & Fitness | Yes | No | App Functionality |
| User Content > Photos or Videos | Yes | No | App Functionality |
| User Content > Other User Content | Yes | No | App Functionality |
| Purchases > Purchase History | Yes | No | App Functionality |
| Diagnostics > Crash Data | No | No | App Functionality |

**Do you or your third-party partners use data for tracking?** No

---

## PHASE 5: Build and Upload

### Step 14: Add PrivacyInfo.xcprivacy to Xcode Target

The file already exists at `ios/App/App/PrivacyInfo.xcprivacy`, but you need to add it to the Xcode build:

1. Open `ios/App/App.xcworkspace` in Xcode
2. In the Project Navigator, find the **App** group under the **App** target
3. Right-click > **Add Files to "App"...**
4. Select `ios/App/App/PrivacyInfo.xcprivacy`
5. Make sure **"App"** target is checked
6. Click **Add**

### Step 15: Verify Xcode Settings

1. Select the **App** target
2. **General** tab:
   - Version: `1.0.0`
   - Build: `1`
   - Bundle Identifier: `com.myrecoverypal.app`
3. **Signing & Capabilities**:
   - Team: Your team (454YNT65J3)
   - Check "Automatically manage signing"
   - Verify these capabilities are listed:
     - Push Notifications
     - App Groups (`group.com.myrecoverypal.app`)
4. Also select the **SobrietyCounterWidgetExtension** target and verify:
   - Bundle ID: `com.myrecoverypal.app.SobrietyCounterWidget`
   - Same team
   - App Groups capability with `group.com.myrecoverypal.app`

### Step 16: Archive and Upload

1. Select **Any iOS Device (arm64)** as the build destination (not a Simulator)
2. **Product** > **Archive**
3. Wait for the build (2-5 minutes)
4. When the Organizer window opens, select the archive
5. Click **Distribute App**
6. Choose **App Store Connect**
7. Choose **Upload** (not Export)
8. Check all options (upload symbols, manage signing)
9. Click **Upload**
10. Wait for processing (5-15 minutes)

### Step 17: Select Build in App Store Connect

1. Go to App Store Connect > your app > the version
2. Under **Build**, click the **+** button
3. Select the build you just uploaded
4. It may take 15-30 minutes to appear after upload

---

## PHASE 6: Submit for Review

### Step 18: Final Checklist Before Submitting

- [ ] All text fields filled (description, keywords, what's new, promotional text)
- [ ] Screenshots uploaded for iPhone 6.9"
- [ ] App review notes filled with demo credentials
- [ ] Sign-in information provided
- [ ] Privacy policy URL set
- [ ] Support URL set
- [ ] App privacy questionnaire completed
- [ ] In-app purchases created and attached to the version
- [ ] Build selected
- [ ] Age rating completed (17+)
- [ ] Pricing set to Free
- [ ] Content rights declared

### Step 19: Submit

1. Click **Add for Review**
2. Then **Submit to App Review**
3. Choose **Manually release this version** (so you control when it goes live) or **Automatically** if you want it live as soon as approved

**Expected review time:** 24-48 hours typically, sometimes up to 7 days for first submissions of health apps.

---

## PHASE 7: After Approval

1. **Uncomment the Smart App Banner** in `templates/base.html` — replace `YOUR_APP_STORE_ID` with your actual App Store ID
2. Set the `REVENUECAT_IOS_API_KEY` env var on Railway if not already done
3. Announce on your social channels
4. Request reviews from your existing users

---

## Common Rejection Reasons to Avoid

| Risk | Your Status | Action |
|------|------------|--------|
| Guideline 4.2 (web wrapper) | 12+ native features, WidgetKit widget | Covered in review notes |
| Guideline 5.1.1 (credential storage) | Keychain via SecureStorage | Already implemented |
| Missing PrivacyInfo.xcprivacy | Created at `ios/App/App/PrivacyInfo.xcprivacy` | Add to Xcode target (Step 14) |
| Missing Restore Purchases button | Present in capacitor-iap.js | Test it works |
| No account deletion | `/accounts/delete-account/` exists | Noted in review notes |
| Health claims | Disclaimer present | No clinical claims in description |
| APNs environment = development | Already set to `production` | Verified |

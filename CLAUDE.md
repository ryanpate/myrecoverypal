# CLAUDE.md - MyRecoveryPal Development Guide

**Last Updated:** 2026-02-28
**Project:** MyRecoveryPal - Social Recovery Platform
**Tech Stack:** Django 5.0.10, PostgreSQL, Redis, Celery, Capacitor Mobile
**Stage:** Beta Testing - User Acquisition Critical
**Current Users:** 18 registered, ~58 monthly active visitors

---

## Quick Reference

```bash
# Development
python manage.py runserver                    # Start dev server
python manage.py migrate                      # Run migrations
python manage.py collectstatic --noinput     # Collect static files
celery -A recovery_hub worker -l info        # Run Celery worker

# Mobile
npx cap sync android                          # Sync web assets to Android
npx cap sync ios                              # Sync web assets to iOS
npx cap open android                          # Open Android Studio
npx cap open ios                              # Open Xcode

# Android Release Build (requires Java 17+)
JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home" \
  ANDROID_HOME=~/Library/Android/sdk \
  ./android/gradlew -p android bundleRelease
# Output: android/app/build/outputs/bundle/release/app-release.aab

# iOS Release Build (unsigned verification)
xcodebuild -workspace ios/App/App.xcworkspace -scheme App \
  -configuration Release -destination 'generic/platform=iOS' \
  CODE_SIGNING_REQUIRED=NO CODE_SIGNING_ALLOWED=NO build
# For App Store: open Xcode → Product → Archive → Distribute
```

---

## Project Vision: Social-First Recovery Platform

**MyRecoveryPal is a SOCIAL MEDIA platform for recovery** - think "Instagram/Facebook for recovery" rather than a resource library.

### Core Principle
- **70% Social Features** - Posts, follows, groups, challenges, messaging
- **20% Resources** - Blog, meetings, services (supporting role)
- **10% Personal Tools** - Journal, milestones (private)

### User Flow
```
Signup → Social Feed (MyRecoveryCircle) → Follow Users → Join Groups → Participate in Challenges
```

Users land on the **Social Feed**, not a dashboard or resource page.

---

## Beta Priority: User Growth

**Critical Problem:** Small user base limits testing and revenue potential.

### Current Analytics (Jan 2026)

**Google Analytics (Dec 4-31, 2025):**
| Metric | Value | Assessment |
|--------|-------|------------|
| Total Active Users | 58 | Very low |
| New Users | 59 | Minimal growth |
| Sessions | 171 | Low |
| Avg Engagement | 89-296 sec | Good when engaged |
| Revenue | $0 | No monetization |
| Week 1 Retention | 6% | Needs improvement |

**Traffic Sources:**
- Direct: 46% (likely team/testing)
- Organic Social: 44% (TikTok/IG working)
- Referral: 7%
- **Organic Search: 0%** ⚠️ Critical gap

**Google Search Console:**
| Metric | Value | Problem |
|--------|-------|---------|
| Total Clicks | 7 | Almost invisible |
| Impressions | 37 | Not being shown |
| Indexed Queries | 1 | Catastrophic |
| Avg Position | 5.59 | Decent when shown |

**Key Insight:** Only 2 pages appear in `site:myrecoverypal.com` search. 54+ blog posts aren't indexed.

**Competitors for reference:**
- I Am Sober: 200K+ app reviews, 127M+ pledges
- Sober Grid: NSF/NIH funded, GPS-based community
- Nomo: Free with unlimited clocks

### Beta Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| Onboarding wizard | COMPLETE | 5-step flow with interests, recovery stage |
| Invite system | COMPLETE | Invite link in nav, profile, sidebar |
| Share buttons | COMPLETE | Twitter, Facebook, WhatsApp, native share |
| Suggested users | COMPLETE | Recovery stage + interests matching |
| Email engagement | COMPLETE | Day 1, 3, 7 welcome sequence |
| Check-in reminders | COMPLETE | Daily at 5 PM via Celery |
| Weekly digest | COMPLETE | Sundays at 10:30 AM |
| Push triggers | COMPLETE | Integrated with notifications (logging mode) |
| Analytics | COMPLETE | Google Analytics G-81SZGNRESW (Property 517028653) |

### Retention Email System

**Email Service:** `apps/accounts/email_service.py`
- Uses Resend HTTP API as primary method (more reliable on Railway)
- Falls back to SMTP if API fails
- Includes retry logic with exponential backoff
- Handles rate limiting (429 responses)

```python
from apps.accounts.email_service import send_email

send_email(
    subject="Your subject",
    plain_message="Plain text version",
    html_message="<p>HTML version</p>",
    recipient_email="user@example.com",
)
```

**Testing emails:**
```bash
python manage.py test_email recipient@example.com --resend-api
```

**Celery Beat Schedule:**
- `send_welcome_emails_day_3`: Daily at 10:00 AM
- `send_welcome_emails_day_7`: Daily at 10:15 AM
- `send_checkin_reminders`: Daily at 5:00 PM
- `send_weekly_digests`: Sundays at 10:30 AM

**Email Templates:** `apps/accounts/templates/emails/`
- `welcome_day_1.html` - Welcome + getting started
- `welcome_day_3.html` - Check-in + feature discovery
- `welcome_day_7.html` - First week celebration + stats
- `checkin_reminder.html` - Streak motivation
- `weekly_digest.html` - Activity summary

**User Fields for Tracking:**
- `welcome_email_1_sent`, `welcome_email_2_sent`, `welcome_email_3_sent`
- `last_checkin_reminder_sent`, `last_weekly_digest_sent`

### Push Notification System

**Service:** `apps/accounts/push_notifications.py`
- Currently logs notifications (can enable FCM/APNs when ready)
- Integrated with `create_notification()` helper
- Supports: follow, like, comment, message, pal_request, sponsor_request, group events

**To enable mobile push:**
1. Set up Firebase project and add `google-services.json`
2. Configure APNs certificates in Apple Developer Portal
3. Implement `send_fcm_notification` and `send_apns_notification` in push_notifications.py
4. See `PUSH_NOTIFICATIONS_SETUP.md` for full guide

### AI Recovery Coach

**Service:** `apps/accounts/coach_service.py`
**Models:** `RecoveryCoachSession`, `CoachMessage` (in `apps/accounts/models.py`)
**URL:** `/accounts/recovery-coach/`

AI-powered conversational coach for recovery support, powered by Claude Haiku via the Anthropic API.

**Rate Limits:**
- Free users: 3 trial messages (lifetime)
- Premium users: 20 messages per day

**System Prompt Includes User Context:**
- Sobriety date and days sober
- Recent mood/craving check-ins
- Recovery stage and interests
- Active recovery goals

**Safety Protocols:**
- Crisis detection refers users to 988 Suicide & Crisis Lifeline
- Never provides medical advice - directs to healthcare professionals
- Cannot prescribe, diagnose, or replace professional treatment
- All conversations stored for safety review

**Cost:** ~$0.001 per message (Claude Haiku)

**Usage:**
```python
from apps.accounts.coach_service import CoachService

# Start or resume a session
service = CoachService(user)
response = service.send_message("I'm struggling with cravings today")
```

### Admin Analytics Dashboard

**Access:** `/admin/dashboard/` (staff only)

Key metrics displayed:
- User Growth: Total users, new signups (7d/30d), onboarding rate
- Engagement: Check-ins, posts, mood distribution
- Retention: DAU/MAU ratio, active users, streak counts
- Social: Connections, groups, members per group
- Email: Welcome email delivery tracking

**A/B Testing:** `/admin/dashboard/ab-tests/`

### A/B Testing System

**Service:** `apps/accounts/ab_testing.py`

Tracks onboarding flow experiments with these variants:
- `control` - Current 5-step onboarding
- `simplified` - 3-step flow (skip recovery stage/interests)
- `progressive` - 5-step with skip option

**Initialize test:** `python manage.py init_ab_tests`

**Key conversions tracked:**
- started_onboarding, completed_step_1-5, completed_onboarding
- followed_user, first_post, first_checkin
- day_1_return, day_7_return

**Usage in views:**
```python
from apps.accounts.ab_testing import ABTestingService

# Get user's variant
variant = ABTestingService.get_variant(user, 'onboarding_flow')

# Track conversion
ABTestingService.track_conversion(user, 'onboarding_flow', 'completed_onboarding')
```

### Remaining Tasks

#### Retention (Priority: HIGH)
1. ~~Daily gratitude prompt in check-in~~ ✅ COMPLETE
2. ~~Prominent sobriety counter widget on profile~~ ✅ COMPLETE
3. ~~Meeting reminders (push before saved meetings)~~ ✅ COMPLETE
4. ~~Progress visualizations (mood/craving trends)~~ ✅ COMPLETE
5. ~~Accountability nudges for Recovery Pals~~ ✅ COMPLETE

#### Polish (Priority: MEDIUM) - ALL COMPLETE ✅
1. ~~Dark mode~~ ✅ COMPLETE
2. ~~Skeleton loaders for content~~ ✅ COMPLETE
3. ~~Optimistic UI for likes/comments~~ ✅ COMPLETE
4. ~~Infinite scroll on feeds~~ ✅ COMPLETE
5. ~~Image compression for uploads~~ ✅ COMPLETE

#### Technical Debt (Priority: LOW)
1. ~~Service worker caching review~~ ✅ COMPLETE
2. Improved offline support
3. Performance audit (N+1 queries)
4. **Static file cache busting** — WhiteNoise uses `StaticFilesStorage` (no content hashing) with 1-year cache. Must bump `?v=` query string in `base.html` when changing any static CSS/JS file, or switch to `CompressedManifestStaticFilesStorage`

#### Infrastructure - ALL COMPLETE ✅
1. ~~Enable mobile push (FCM/APNs)~~ ✅ COMPLETE
2. ~~Set up Celery Beat worker on Railway~~ ✅ COMPLETE

---

## Tech Stack

### Backend
- **Django 5.0.10** - Framework
- **PostgreSQL** - Database (via `DATABASE_URL`)
- **Redis 5.0.1** - Cache + Celery broker
- **Gunicorn 21.2.0** - WSGI server
- **Celery 5.3.4** - Background tasks

### Integrations
- **Stripe** - Subscriptions (14-day premium trial on signup) — hidden inside iOS app per Guideline 3.1
- **RevenueCat** - StoreKit 2 IAP wrapper for iOS subscriptions (free tier up to $2,500/mo revenue)
- **Cloudinary** - Media storage
- **SendGrid** - Email (production), Resend API key also configured
- **Sentry** - Error monitoring
- **Anthropic** - AI Recovery Coach (Claude Haiku)
- **Firebase** - Push notifications (Android FCM configured)
- **APNs** - iOS push notifications (HTTP/2 via httpx + PyJWT)

### Mobile
- **Capacitor 7.4.4** - Native wrapper (iOS + Android projects tracked in git)
- **12 Capacitor plugins:** push-notifications, status-bar, haptics, share, app, keyboard, browser, local-notifications, preferences, RevenueCat, biometric-auth
- **6 native JS modules:** capacitor-native.js, capacitor-push.js, capacitor-iap.js, capacitor-biometric.js, capacitor-transitions.js, capacitor-offline.js
- **Firebase Cloud Messaging** - Push notifications (Android configured)
- **APNs** - iOS push notifications (backend ready, needs key deployment to Railway)
- **Android:** Release AAB built and ready for Google Play upload
- **iOS:** Native features complete (Face ID login, ultra-minimal nav, 5-tab bottom bar, splash overlay, transitions, offline mode), IAP integrated, ready for Xcode Archive + App Store submission

---

## Django Apps

### apps.accounts (PRIMARY - 70% of features)
All social features live here:

**Social Models:**
- `SocialPost` - Posts with reactions, comments, visibility controls
- `SocialPostComment` - Threaded comments with likes
- `PostReaction` - Emoji reactions on posts (❤️🙏💪🎉)
- `UserConnection` - Follow/block with mutual tracking
- `RecoveryGroup` - 8 types, 3 privacy levels, group posts
- `GroupChallenge` - 10 types, badges, streaks, leaderboards
- `ChallengeParticipant` - Progress tracking
- `SponsorRelationship` - 1:1 mentorship
- `RecoveryPal` - Mutual accountability
- `DailyCheckIn` - Mood/craving with social sharing
- `ActivityFeed` - Aggregated stream
- `Notification` - 12 notification types
- `SupportMessage` - Direct messaging

**Growth Models (UNDERUTILIZED):**
- `WaitlistRequest` - Working waitlist
- `InviteCode` - **Working invite system, not surfaced to users**
- `SystemSettings` - Invite-only mode controls

**Key Files:**
- `apps/accounts/models.py` - 1,400+ lines
- `apps/accounts/views.py` - 2,400+ lines
- `apps/accounts/invite_models.py` - Invite/waitlist system

### apps.blog (Supporting)
Blog posts with trigger warnings, categories, tags.

### apps.journal (Private)
Personal journaling - entries are NEVER shared.

### resources/ (Supporting)
Educational content library.

### apps.support_services (Supporting)
Meeting finder and service directory.

### apps.newsletter (Supporting)
Email campaigns - underutilized for retention.

---

## Key Routes

```
/                              → Landing (unauthenticated)
/accounts/register/            → Registration
/accounts/social-feed/         → Main feed (default landing after login)
/accounts/community/           → User discovery
/accounts/groups/              → Groups
/accounts/challenges/          → Challenges
/accounts/delete-account/      → Account deletion (required by app stores)
/blog/                         → Community blog
/journal/                      → Private journal
/resources/                    → Resource library
/support/meetings/             → Meeting finder
```

---

## User Model

```python
User (extends AbstractUser):
    # Recovery fields
    sobriety_date = DateField(null=True)
    recovery_goals = TextField()
    is_sponsor = BooleanField()

    # Profile
    bio = TextField()
    location = CharField()
    avatar = ImageField()

    # Privacy
    is_profile_public = BooleanField(default=True)
    show_sobriety_date = BooleanField(default=True)
    allow_messages = BooleanField(default=True)

    # Methods
    get_days_sober()
    get_following(), get_followers()
    is_following(user), follow_user(user), unfollow_user(user)
    get_active_sponsor(), get_recovery_pal()
```

---

## Development Patterns

### Views
```python
# Class-based preferred
from django.contrib.auth.mixins import LoginRequiredMixin

class SocialFeedView(LoginRequiredMixin, ListView):
    model = SocialPost
    template_name = 'accounts/social_feed.html'
```

### Query Optimization
```python
# Always use select_related/prefetch_related
posts = SocialPost.objects.select_related('user').prefetch_related('likes', 'comments')
```

### Activity Creation
```python
# Activities auto-created via signals (apps/accounts/signals.py)
# For milestones, check-ins, blog posts
```

---

## Environment Variables

```bash
# Required
SECRET_KEY=<random>
DEBUG=False
DATABASE_URL=postgres://...
REDIS_URL=redis://...
ALLOWED_HOSTS=myrecoverypal.com,www.myrecoverypal.com

# Integrations
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
STRIPE_SECRET_KEY=...
STRIPE_PUBLISHABLE_KEY=...
RESEND_API_KEY=<resend-api-key>
ANTHROPIC_API_KEY=<anthropic-api-key>
SENTRY_DSN=...

# iOS Push Notifications (APNs)
APNS_KEY_CONTENT=<raw .p8 file content>
APNS_KEY_ID=<10-char key ID>
APNS_TEAM_ID=<Apple team ID>
APNS_KEY_PATH=/app/apns-auth-key.p8
APNS_USE_SANDBOX=false

# iOS In-App Purchases
REVENUECAT_IOS_API_KEY=<revenuecat-ios-api-key>
```

---

## Deployment

**Platform:** Railway (auto-deploy from `main`)

### Railway Services (Project: responsible-education)

| Service | Purpose | Start Command |
|---------|---------|---------------|
| **web** | Django app | `gunicorn recovery_hub.wsgi:application` (via start.sh) |
| **celery-worker** | Background tasks + Beat scheduler | `celery -A recovery_hub worker -l info -B` |
| **Postgres** | Database | Managed by Railway |
| **Redis** | Cache + Celery broker | Managed by Railway |

### Environment Variables (Required for both web and celery-worker)
```bash
SECRET_KEY, DATABASE_URL, REDIS_URL, DJANGO_SETTINGS_MODULE
EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
DEFAULT_FROM_EMAIL, SITE_URL, SENTRY_DSN
```

**Note:** `REDIS_URL` must include authentication credentials:
```
redis://default:<password>@redis.railway.internal:6379
```

```bash
# Local Development
./build.sh                                    # Build
python manage.py runserver                    # Web server
celery -A recovery_hub worker -l info -B     # Worker + Beat
```

---

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

## SEO & Traffic Growth Strategy

### Current SEO Assets
- **Landing Pages:** 8 SEO-optimized pages targeting high-volume keywords
- **Blog:** 58+ posts including 6 SEO-optimized articles (83K monthly search volume)
- **Schema:** Organization, WebSite, FAQPage, SoftwareApplication
- **Sitemap:** `/sitemap.xml` with 25+ URLs
- **Robots.txt:** Properly configured for crawling

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

### Google Search Console Indexing Status
**Submit remaining URLs via URL Inspection tool:**

**✅ INDEXED (Jan 5, 2026):**
- [x] `https://www.myrecoverypal.com/sobriety-calculator/`
- [x] `https://www.myrecoverypal.com/sobriety-counter-app/`
- [x] `https://www.myrecoverypal.com/sober-grid-alternative/`
- [x] `https://www.myrecoverypal.com/blog/how-long-does-alcohol-withdrawal-last/`
- [x] `https://www.myrecoverypal.com/blog/signs-of-alcoholism-self-assessment/`
- [x] `https://www.myrecoverypal.com/blog/how-to-stop-drinking-alcohol-guide/`

**Priority 1 - Remaining Blog Posts (29K monthly searches combined):**
- [ ] `https://www.myrecoverypal.com/blog/what-is-sober-curious-guide/` - 12K/mo searches
- [ ] `https://www.myrecoverypal.com/blog/high-functioning-alcoholic-signs-help/` - 9K/mo searches
- [ ] `https://www.myrecoverypal.com/blog/dopamine-detox-addiction-recovery/` - 8K/mo searches

**Priority 2 - SEO Landing Pages:**
- [ ] `https://www.myrecoverypal.com/alcohol-recovery-app/`
- [ ] `https://www.myrecoverypal.com/drug-addiction-recovery-app/`
- [ ] `https://www.myrecoverypal.com/free-aa-app/`
- [ ] `https://www.myrecoverypal.com/opioid-recovery-app/`
- [ ] `https://www.myrecoverypal.com/gambling-addiction-app/`
- [ ] `https://www.myrecoverypal.com/mental-health-recovery-app/`

**Priority 3 - Core Pages:**
- [ ] `https://www.myrecoverypal.com/`
- [ ] `https://www.myrecoverypal.com/blog/`
- [ ] `https://www.myrecoverypal.com/about/`
- [ ] `https://www.myrecoverypal.com/crisis/`

### MEDIUM - Backlink Building
- [ ] Sign up for Connectively (formerly HARO) - get quoted in articles
- [ ] Guest post outreach to: The Fix, Recovery.org, Sober Nation
- [ ] Submit to recovery app directories
- [ ] Local PR outreach (founder story)

### MEDIUM - Social & Community Marketing
- [ ] Reddit engagement: r/stopdrinking (900K+), r/addiction, r/REDDITORSINRECOVERY
- [ ] Pinterest: Recovery quotes, infographics, milestone images
- [ ] TikTok content: "Day 1 vs Day 365", body changes after quitting
- [ ] Instagram Reels: Behind-the-scenes, user stories

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

#### Remaining - Manual Steps
- [ ] **Android: Upload AAB to Google Play Console** (account ready)
- [ ] **Android: Complete store listing** (screenshots, description, data safety)
- [ ] **Android: Submit for review** (expect 1-3 days)
- [ ] **iOS: Create APNs Auth Key** in Apple Developer Portal → download `.p8` file
- [ ] **iOS: Configure Xcode signing** (set team, add Push Notifications + In-App Purchase capabilities)
- [ ] **iOS: Set up RevenueCat** — create project, add iOS app, create "premium" entitlement, copy API key
- [ ] **iOS: Create subscription products** in App Store Connect (monthly $4.99, yearly $29.99)
- [ ] **iOS: Set Railway env vars** — `APNS_KEY_CONTENT`, `APNS_KEY_ID`, `APNS_TEAM_ID`, `REVENUECAT_IOS_API_KEY`
- [ ] **iOS: Archive and submit** via Xcode → App Store Connect
- [ ] **iOS: Complete App Store metadata** (screenshots, description, privacy nutrition labels, review notes)
- [ ] **iOS: Create demo account** (`review@myrecoverypal.com`) with sample data for Apple review
- [ ] App Store Optimization (ASO): keywords, screenshots, description
- [ ] Request reviews from existing users
- [ ] Uncomment Smart App Banner `<meta>` tag in `base.html` after approval (replace `YOUR_APP_STORE_ID`)

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
- **Apple review notes:** Emphasize native features (Face ID login, native-styled menu with haptics, share sheet, push, swipe gestures, page transitions, offline mode, keyboard), Capacitor as legitimate native framework, IAP sandbox testing instructions, health disclaimer modal, block/report moderation

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

## Revenue Strategy

### Current State
- **Revenue:** $0
- **Monetization:** Freemium ($4.99/mo or $29.99/yr Premium) + BetterHelp affiliate + Ko-fi/BMAC donations
- **Stripe:** Web subscriptions (Free + Premium tiers, 14-day trial on signup)
- **Apple IAP:** iOS subscriptions via RevenueCat/StoreKit 2 (same tiers, Apple takes 15-30% cut)
- **AI Coach:** "Anchor" - 3 free trial messages, 20/day for Premium

### IMMEDIATE - ✅ ALL COMPLETE

#### 1. Donation System - ✅ COMPLETE
- [x] Ko-fi and Buy Me a Coffee integration added
- [x] Donation links in footer
- [x] One-time and monthly donation options

#### 2. Affiliate Marketing - ✅ COMPLETE
| Partner | Commission | Integration | Status |
|---------|------------|-------------|--------|
| BetterHelp | $100-200/referral | Blog post CTAs with UTM tracking | ✅ Done |

- [x] BetterHelp affiliate CTA on all blog posts (`_affiliate_cta.html`)
- [x] Affiliate disclosures included in CTA
- [ ] Amazon recovery books affiliate links (future)
- [ ] Treatment center directory partnerships (future)

#### 3. Premium Tier - ✅ COMPLETE
| Free | Premium ($4.99/mo or $29.99/yr) |
|------|--------------------------------|
| Unlimited social feed & messaging | All free features |
| Join up to 5 groups | AI Recovery Coach (20 msgs/day) |
| 30-day journal | Unlimited groups + private groups |
| 3 AI Coach trial messages | Unlimited journal + export |
| Daily check-in | 90-day analytics & charts |
| Community challenges | Premium badge |

- [x] Pricing page at `/accounts/pricing/` with therapy cost comparison
- [x] Stripe subscription tiers configured
- [x] Premium feature gates (AI Coach message limits, progressive upgrade hints)
- [x] 14-day free trial on signup

#### 4. Recovery Merchandise Store
- [ ] Milestone tokens/coins (physical)
- [ ] Recovery affirmation cards
- [ ] Journals with prompts
- [ ] Apparel (hoodies, t-shirts)

### MEDIUM-TERM - Business Development

#### 5. B2B Licensing
| Customer | Use Case | Pricing |
|----------|----------|---------|
| Treatment centers | White-label platform | $500-2,000/mo |
| EAP providers | Employee recovery support | $1,000-5,000/mo |
| Sober living facilities | Resident community | $200-500/mo |

#### 6. Recovery Coach Marketplace
- Connect users with certified recovery coaches
- 15-20% platform fee
- Video/chat sessions through platform

---

## 30-Day Revenue & Marketing Plan (Started 2026-02-21)

**Full plan:** `.claude/plans/mutable-munching-hummingbird.md`

### Code Changes - ✅ ALL 15 ITEMS COMPLETE

All conversion funnel fixes, email sequences, progressive upgrade hints, blog CTAs, pricing page updates, sitemap additions, and AI Coach landing page cost comparison have been implemented and deployed.

### AI Coach Rename
- Renamed from "Pal" to "Anchor" across all 9 files (25+ references)
- System prompt, chat UI, emails, blog CTAs, homepage, social feed

### Remaining Marketing Tasks (Manual - No Code)

#### Google Search Console (Priority: HIGH)
- [ ] Submit 8 remaining URLs via URL Inspection tool:
  - `/ai-recovery-coach/`, `/accounts/pricing/`
  - `/blog/what-is-sober-curious-guide/` (12K/mo searches)
  - `/blog/high-functioning-alcoholic-signs-help/` (9K/mo searches)
  - `/blog/dopamine-detox-addiction-recovery/` (8K/mo searches)
  - `/alcohol-recovery-app/`, `/free-aa-app/`, `/sobriety-counter-app/`

#### Reddit Marketing (Priority: HIGH)
- [ ] Research r/stopdrinking (900K members) community rules and culture
- [ ] Write Reddit Post 1: "I tracked my mood every day for 90 days in recovery" (r/stopdrinking)
- [ ] Write Reddit Post 2: "The one thing that helped me most at 2 AM when cravings hit" (r/addiction)
- [ ] Write Reddit Post 3: "Free sobriety calculator I built" with link to `/sobriety-calculator/` (r/sober)
- [ ] Post content and monitor engagement (one ban = 900K users lost)
- [ ] Write 2+ follow-up posts based on what performs best

**Reddit rules:** Never be promotional. Provide genuine value. Only share link if asked in comments.

#### TikTok Content (Priority: MEDIUM)
- [ ] Record TikTok 1: "Things that happen to your body when you stop drinking" (timeline format)
- [ ] Record TikTok 2: "I taught AI to be a recovery coach. Here's what happened." (demo Anchor)

#### Pinterest (Priority: LOW)
- [ ] Create 3-5 pins for highest-traffic blog posts (alcohol withdrawal timeline, signs of alcoholism, how to stop drinking)

#### 30-Day Review
- [ ] Check Google Analytics for traffic changes
- [ ] Check Google Search Console for new indexing
- [ ] Check Stripe dashboard for trial signups or payments
- [ ] Check Ko-fi/Buy Me a Coffee for donations
- [ ] Test full signup → AI Coach → upgrade flow manually

---

## Privacy & Safety

### Non-Negotiable
- Journal entries are ALWAYS private
- Sobriety date visibility controlled by user
- Anonymous posting available in groups
- Crisis resources always accessible
- No medical advice (professional help only)

### Content Safety
- Trigger warnings on sensitive content
- Moderation queue for group posts
- Block/report functionality

---

## File Structure

```
apps/
├── accounts/              # Social features (PRIMARY)
│   ├── models.py         # All social models
│   ├── views.py          # All social views
│   ├── payment_views.py  # Stripe + iOS IAP subscription views
│   ├── payment_models.py # Subscription, Transaction, Invoice models
│   ├── invite_models.py  # Invite/waitlist system
│   ├── coach_service.py  # AI Recovery Coach (Claude Haiku)
│   ├── push_notifications.py  # FCM + APNs push delivery
│   └── signals.py        # Activity creation
├── blog/                  # Community blog
├── journal/               # Private journaling
├── core/                  # Static pages
├── newsletter/            # Email campaigns
└── support_services/      # Meeting finder

resources/                 # Resource library
recovery_hub/             # Django config
templates/                # Global templates
static/
├── css/base-inline.css   # Main stylesheet (extracted from base.html)
└── js/
    ├── capacitor-native.js      # Native features (haptics, share, keyboard, app state, menu rebuild)
    ├── capacitor-push.js        # Push notification registration + deep linking
    ├── capacitor-iap.js         # iOS StoreKit 2 IAP via RevenueCat
    ├── capacitor-biometric.js   # Face ID / Touch ID login + journal lock + settings
    ├── capacitor-transitions.js # Page transitions, swipe gestures, pull-to-refresh
    └── capacitor-offline.js     # IndexedDB cache, write queue, offline detection
ios/                       # Capacitor iOS project (tracked in git)
android/                   # Capacitor Android project (tracked in git)
```

---

## AI Assistant Guidelines

1. **Social features are the priority** - not resources or education
2. **User growth is critical** - every feature should help acquire/retain users
3. **Privacy is paramount** - never expose journal entries or hidden data
4. **Invite system exists** - `InviteCode` model works, just needs UI
5. **Push notifications configured** - Firebase ready, triggers need implementation
6. **Mobile compatibility** - consider Capacitor for API changes
7. **Prefer editing existing code** - mature codebase, don't rewrite

### Questions to Ask
- "Does this help acquire or retain users?"
- "Does this need to work on mobile?"
- "Is this sensitive/private content?"
- "Should this create a notification?"

---

## Recovery Groups System

### Fixed Issues (2025-12-24)
The groups system had several critical bugs that have been fixed:

1. **my_groups() view** - Was passing `groups` instead of `memberships`, causing template to display incorrectly
2. **RecoveryGroupDetailView** - Was missing `get_context_data()`, so templates didn't receive `membership`, `is_member`, `members`, or `recent_posts`
3. **create_group()** - Was not extracting `group_type` from POST data (required field)
4. **No group posting** - Added `create_group_post()` view and URL
5. **No leave group** - Added `leave_group()` view and URL
6. **Approve pending members** - Added approve/reject views with UI for admins/moderators
7. **Edit group settings** - Added edit_group view and template for group admins
8. **Age display bug** - Fixed "21" showing without context, now shows "Dec 2024" format

### Group URLs
```
/accounts/groups/                           # List all groups
/accounts/groups/create/                    # Create new group
/accounts/groups/<id>/                      # Group detail
/accounts/groups/my-groups/                 # User's joined groups
/accounts/groups/<id>/join/                 # Join group (AJAX)
/accounts/groups/<id>/leave/                # Leave group (AJAX)
/accounts/groups/<id>/post/                 # Create post in group (AJAX)
/accounts/groups/<id>/edit/                 # Edit group settings (admin only)
/accounts/groups/<id>/approve/<user_id>/    # Approve pending member (AJAX)
/accounts/groups/<id>/reject/<user_id>/     # Reject pending member (AJAX)
/accounts/groups/<id>/post/<post_id>/comment/  # Add comment to post (AJAX)
/accounts/groups/<id>/post/<post_id>/like/     # Like/unlike post (AJAX)
/accounts/groups/<id>/post/<post_id>/pin/      # Pin/unpin post (AJAX, mod/admin)
/accounts/groups/<id>/transfer/                # Transfer ownership (AJAX)
/accounts/groups/<id>/members-for-transfer/    # Get members for transfer (AJAX)
/accounts/groups/<id>/archive/                 # Archive group (AJAX, admin only)
/accounts/groups/<id>/invite/                  # Generate invite link (AJAX)
/accounts/groups/<id>/join-invite/<code>/      # Join via invite link
```

### Group Features Complete

All group features have been implemented:
- Create, edit, and archive groups
- Join (public), request to join (private), invite links (secret/private)
- Post discussions with 6 types
- Like/unlike posts with notifications
- Pin/unpin posts (moderator/admin)
- Comment on posts with anonymous option
- Approve/reject pending members
- Transfer ownership
- Group notifications for joins, posts, comments

### Group Models Reference
```python
RecoveryGroup:
    - group_type: 8 types (addiction_type, location, recovery_stage, interest, age_group, gender, family, professional)
    - privacy_level: public, private, secret
    - creator, moderators, max_members
    - group_image, group_color

GroupMembership:
    - status: pending, active, moderator, admin, banned, left
    - joined_date, left_date, last_active

GroupPost:
    - post_type: discussion, milestone, resource, question, support, event
    - is_anonymous, is_pinned, likes

GroupPostComment:
    - post, author, content, is_anonymous
    - created_at, updated_at

Notification (group types):
    - group_invite: Group invitation
    - group_post: New post in group
    - group_comment: Comment on post
    - group_join: New member joined
```

---

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

## Changelog

- **2026-03-02:** Moved Face ID from app lock to login page biometric sign-in. Removed 5-minute background timeout lock screen (HTML overlay in `base.html`, CSS in `base-inline.css`, JS `appStateChange` listener). Replaced `isAppLockEnabled`/`setAppLockEnabled`/`shouldLockOnResume`/`setLastBackground` with `isBiometricLoginEnabled`/`setBiometricLoginEnabled`/`saveLoginCredentials`/`getLoginCredentials`/`clearLoginCredentials` in `capacitor-biometric.js`. Added "Sign in with Face ID" button to `login.html` (native only) — checks stored credentials + biometric auth, auto-fills and submits form. Credentials saved on successful password login when biometric login is enabled. Updated first-launch setup prompt text ("Sign in with Face ID" instead of "Lock App"). Updated settings toggles ("Sign in with [Face ID]" instead of "Lock App with [Face ID]"), disabling clears stored credentials. Journal lock remains independent and unchanged. Bumped static file `?v=` from `20260302g` to `20260302h`.
- **2026-03-01:** Native iOS UX overhaul — ultra-minimal nav, 5-tab bottom bar, notification bell, splash screen, social-first landing. Features added incrementally (one at a time) to avoid CSS conflicts with generic `nav{}` rule. Added 5-tab native bottom bar HTML in `base.html` (Feed `fa-house`, Coach `fa-robot`, Check-in `fa-circle-check`, Alerts `fa-bell` with badge, Profile `fa-user`), with CSS: hidden on web (`display:none`), `display:flex !important` + `position:fixed; bottom:0` on native, `top:auto` to override inherited `nav{top:0}`, frosted glass backdrop blur, safe-area padding, keyboard-open auto-hide, dark mode. Hides web `.mobile-bottom-nav` on native. Added haptic feedback on tab taps. Added ultra-minimal native nav bar CSS: hides logo text (icon only, 28px), tighter padding (6px 12px), hides theme toggle and notification dot on native. Injects notification bell with iOS-style red badge (99+ cap) before hamburger via JS, hooks `updateNotificationIndicator` for live badge updates on both bell and tab bar. Added animated splash/loading overlay (`#nativeSplashOverlay`): blue background with pulsing logo and expanding ring animation, shown once per session via `sessionStorage` flag, fades out after `window.load` + 300ms. Changed `LOGIN_REDIRECT_URL` from `accounts:hybrid_landing` to `accounts:social_feed` (social-first philosophy). Excluded `.native-bottom-tabs` from page transition click handler. All changes scoped to `.ios-native-app`/`.android-native-app` — web completely unchanged except login redirect.
- **2026-02-28:** Removed native tab bar, replaced with iOS-styled hamburger menu. Deleted tab bar HTML (nav + More menu overlay) from `base.html`, 169 lines of tab bar/More menu CSS from `base-inline.css`, and tab bar JS from `capacitor-native.js` and `capacitor-transitions.js`. Added native menu CSS overrides scoped to `.ios-native-app`/`.android-native-app`: blur backdrop, 300px panel with `#f2f2f7` background, grouped-list card sections (12px radius), chevron pseudo-elements (FA `\f054`), uppercase section labels, red logout, hidden Install App link, full dark mode. JS rebuilds hamburger button on native: removes CSS `<span>` lines, inserts FA `fa-bars` icon, `MutationObserver` swaps to `fa-xmark` on `.active` toggle, hides SVG close button (tap overlay to dismiss). Added cache-busting `?v=` query strings to all static CSS/JS in `base.html` (WhiteNoise uses `StaticFilesStorage` with 1-year cache, no filename hashing). Replaced AI Coach full-page disclaimer with accept-once modal popup (localStorage `anchor_disclaimer_accepted`) + compact one-line bar with "Details" re-open link. Web version completely unchanged.
- **2026-02-28:** iOS native features layer — Face ID, tab bar, transitions, offline mode. Installed `@aparajita/capacitor-biometric-auth` v9.1.2 (Capacitor 7 compatible). Created `static/js/capacitor-biometric.js` — two-layer biometric protection: app lock (auto-locks after 5+ min background, Face ID/Touch ID prompt with device passcode fallback) and journal lock (separate biometric gate on `/journal/` pages, redirects on denial). iOS-style toggle switches injected on edit-profile page via JS (adapts labels to detected biometry type — Face ID/Touch ID/Fingerprint). Created iOS-style 5-tab bottom navigation bar (Feed, Groups, Coach, Journal, More) replacing the web hamburger menu on native. "More" tab opens a bottom-sheet menu with 8 items (Profile, Milestones, Community, Challenges, Messages, Progress, Settings, Subscription) styled as iOS grouped-list with chevrons. Web bottom nav preserved unchanged via `.web-bottom-nav` class scoping. Hamburger hidden on native via JS. Created `static/js/capacitor-transitions.js` — edge swipe back gesture (30px edge zone, 80px threshold, visual chevron indicator), 250ms CSS page transitions matching iOS UIKit timing (slideInRight/slideOutLeft/slideOutRight), View Transition API support for iOS 18+ with CSS fallback, enhanced pull-to-refresh with rotation physics (120px threshold). Click delegation intercepts internal links for transitions but excludes tab bar and More menu. Created `static/js/capacitor-offline.js` — IndexedDB database (`mrp_offline`) with 5 object stores (posts, journal, checkins, write_queue, meta), social feed post caching (last 50), journal entry caching, write queue for offline mutations (auto-flushes on reconnect and app foreground), fetch interceptor (cache-first for GET `/social-feed/posts/`, queues non-GET when offline), amber offline banner. All features guard on `window.Capacitor.isNativePlatform()` — zero impact on web. All CSS scoped to `.ios-native-app` / `.android-native-app` body classes. Full dark mode support for tab bar, More menu, and biometric settings. Xcode build verified (BUILD SUCCEEDED). Total: 12 Capacitor plugins, 6 native JS modules.
- **2026-02-28:** iOS App Store publication — native features, IAP, and APNs. Installed 8 new Capacitor plugins (`@capacitor/haptics`, `share`, `app`, `keyboard`, `browser`, `local-notifications`, `preferences`, `@revenuecat/purchases-capacitor`) bringing total to 10 iOS plugins. Created `static/js/capacitor-native.js` — native features bridge providing haptic feedback on like/check-in/share/follow actions, native share sheet override, keyboard height tracking (hides bottom nav via `.keyboard-open` CSS class), Android back button handler, app state change listener (refreshes notification count on foreground), platform detection (`ios-native-app` body class). Created `static/js/capacitor-iap.js` — RevenueCat/StoreKit 2 IAP bridge handling purchase flow with bottom sheet modal, restore purchases, entitlement checking, and server-side sync to Django. Added `ios_subscription_sync` POST endpoint at `/accounts/api/ios-subscription/sync/` that receives RevenueCat `customerInfo`, updates `Subscription` model with `subscription_source='apple'`, and does NOT overwrite active Stripe subscriptions. Added `subscription_source` field (stripe/apple/manual) to `Subscription` model (migration 0020). Added `.stripe-only` / `.iap-only` CSS toggle classes to `base-inline.css` — Stripe UI hidden and IAP UI shown when `body.ios-native-app` is present. Updated `pricing.html` (Stripe buttons wrapped with `.stripe-only`, IAP + Restore Purchases buttons added with `.iap-only`, Stripe checkout script wrapped), `recovery_coach.html` (upgrade prompts use IAP on iOS), `subscription_management.html` ("Manage in iOS Settings" replaces Stripe portal on iOS). Added `NSFaceIDUsageDescription` to `Info.plist`. Updated `start.sh` with APNs key extraction from `APNS_KEY_CONTENT` env var. Added `PyJWT` and `python-dateutil` to `requirements.txt`. Added RevenueCat API key meta tag and Smart App Banner placeholder to `base.html`. Updated `capacitor.config.json` with Keyboard and LocalNotifications plugin config. All 3 Railway services (web, celery-worker, attractive-forgiveness) deployed successfully.
- **2026-02-25:** Conversion-focused landing page redesign (`apps/core/templates/core/index.html`). Replaced text-heavy homepage with visual, screenshot-driven design. New split-layout hero with `feed.webp` screenshot showing MyRecoveryCircle product. Added trust strip, 3-step "How It Works" section, dedicated MyRecoveryCircle showcase (with `create-post.webp` screenshot + feature checklist), dedicated Anchor AI Coach showcase (dark blue gradient, logo, "Try Anchor Free" CTA, professional disclaimer). Replaced 7 feature cards (most with empty icons) with 6 cards all using Font Awesome icons. Added visible FAQ accordion (5 items, previously only in JSON-LD schema). Reduced blog section from 6 to 3 highest-traffic articles. Removed SEO prose block, 8-card "Explore Resources" grid, and generic "About Our Mission" section — keywords redistributed into new sections naturally. Accessibility: `aria-expanded` dynamically updates on FAQ toggle, `aria-hidden="true"` on all 27 FA icons, `aria-controls` on FAQ buttons. Performance: `loading="eager"` + `fetchpriority="high"` on hero LCP image, `loading="lazy"` on below-fold images, `width`/`height` attributes to prevent CLS. Replaced `direction: rtl` CSS layout hack with `order` property. All JSON-LD structured data preserved unchanged.
- **2026-02-24:** Reduced Railway network egress to lower hosting costs. Added `GZipMiddleware` for ~70% compression on all HTML/JSON responses. Extracted 54KB inline CSS from `base.html` (3,290→1,139 lines) into cacheable `static/css/base-inline.css`. Converted 6 demo PNG screenshots (9.5MB) to WebP (503KB, 95% smaller) with `<picture>` fallback in `demo.html`. Removed dead AdSense script (~100KB wasted JS per page). Moved Chart.js (~200KB) from global `base.html` to only `progress.html` and `journal/stats.html` via `extra_js` block. Reduced notification polling from 30s to 120s (75% fewer API requests). Moved session storage from PostgreSQL to Redis (`SESSION_ENGINE = cache`). Set `WHITENOISE_MAX_AGE = 31536000` for 1-year browser caching of static assets. Homepage HTML response now ~15KB gzipped (was 113KB+ uncompressed).
- **2026-02-21:** Implemented all 15 code changes from 30-Day Revenue & Marketing Plan. Conversion funnel fixes: updated sitemap.xml with 7 missing URLs, registration page now mentions AI Coach + 14-day trial, removed fabricated aggregateRating from AI Coach landing page, added AI Coach promo card to social feed sidebar, added therapy cost comparison to pricing page. Email sequences: welcome day 1/3/7 emails now promote Anchor (AI Coach), new day 5 premium trial nudge email with Celery task (`send_premium_trial_nudge`, runs daily at 11 AM). AI Coach UX: progressive upgrade hints (toast after message 1, persistent banner after message 2). Blog CTAs: rewrote AI Coach CTA with crisis-moment copy, optimized BetterHelp affiliate CTA with recovery-specific angle and UTM params. AI Coach landing page: added 3-column therapy cost comparison section. Added `premium_nudge_sent` field to User model (migration 0019).
- **2026-02-21:** Renamed AI Coach from "Pal" to "Anchor" across entire codebase. Updated 25+ references in 9 files: coach_service.py system prompt, recovery_coach.html chat UI (header, disclaimer, welcome, typing indicator, upgrade text, placeholder, toast), social_feed.html promo card, welcome emails (day 1, 3), premium trial nudge email, blog AI Coach CTA, blog affiliate CTA, homepage (FAQ schema, feature card, SEO section). Preserved "Recovery Pal" (accountability partner feature) references untouched.
- **2026-02-20:** App Store Publishing - Phase 1-3 complete. Code changes: added account deletion feature at `/accounts/delete-account/` (required by both stores), created `capacitor-push.js` client-side bridge for native push notifications, added `capacitor://localhost` and `ionic://localhost` to CSRF/CORS settings, guarded service worker registration in Capacitor native context, added signing keys to `.gitignore`. Android: generated release keystore, configured signing in `build.gradle` via `keystore.properties`, built release AAB (3.4 MB) with `bundleRelease`. iOS: updated `Info.plist` with `UIBackgroundModes` (remote-notification) and camera/photo privacy descriptions, added push notification token forwarding in `AppDelegate.swift`, fixed Xcode 26.2 compatibility by adding `SUPPORTED_PLATFORMS` to `project.pbxproj`, set version to 1.0.0, verified clean release build. Tracked `android/` and `ios/` directories in git (removed from `.gitignore`, kept build artifacts and secrets excluded). Both platforms ready for store submission.
- **2026-02-19:** Fixed AI Coach page content hidden behind top navigation. Reset body padding-top on coach page and used explicit margin-top (100px) on `.coach-page` container to ensure full clearance below the fixed nav bar, with matching height calc to fill the remaining viewport.
- **2026-02-19:** Removed false claims and updated pricing messaging across homepage and all 10 SEO landing pages. Replaced "100% free forever" with "Free to Join" reflecting freemium model (free core + Premium $4.99/mo). Removed fake "1,000+ users" member counts and fabricated aggregateRating schemas (4.8 stars / 150 reviews). Removed "top-rated" / "highly-rated" claims. Updated FAQ answers across all pages to accurately describe free vs Premium tiers. Changed hero messaging to lean into being a new, growing community ("A Recovery Community Built Together") rather than inflating numbers. Pages updated: index.html, alcohol_recovery_app, drug_addiction_recovery_app, free_aa_app, gambling_addiction_app, mental_health_recovery_app, opioid_recovery_app, sober_grid_alternative, sobriety_counter_app, sobriety_calculator, demo.
- **2026-02-19:** Fixed AI Coach previous conversation rendering over page header. Root cause: context variable `messages` in `recovery_coach` view collided with Django's built-in messages framework. `base.html` checks `{% if messages %}` to render alert divs and was picking up the CoachMessage queryset, rendering each chat message as an alert overlay at the top of the page. Renamed context variable to `chat_messages` in view and template. Also made disclaimer collapsible — shows compact one-line bar (warning + crisis numbers) by default when conversation exists, auto-expanded for new conversations.
- **2026-02-19:** Made AI Coach feature prominent across entire site. Homepage: added AI Coach trust signal to hero, featured card (first in features grid) with NEW badge and gradient border, SEO content section, resources grid link, updated structured data/FAQ schema. Navigation: added robot icon + NEW badge to desktop nav, AI Recovery Coach with gradient accent in user dropdown (after MyRecoveryCircle), styled mobile menu entry, replaced Journal tab with AI Coach in mobile bottom nav (auth), replaced Blog tab with AI Coach in mobile bottom nav (unauth), added to footer Community section. SEO: created /ai-recovery-coach/ landing page with SoftwareApplication + FAQPage schema, feature cards, how-it-works, pricing comparison, FAQ. Blog: created AI Coach CTA partial shown on all blog posts (before affiliate CTA). Sitemap: added /ai-recovery-coach/ at 0.9 priority.
- **2026-02-19:** Added prominent legal disclaimer to AI Recovery Coach page. Replaces small one-line crisis banner with comprehensive amber warning banner covering: AI limitations, not a medical/mental health professional, no diagnosis/prescriptions/medical advice, AI responses may not be accurate, not a substitute for professional treatment, and crisis resources (988 Suicide & Crisis Lifeline, 741741 text line, 911).
- **2026-02-19:** Redesigned AI Recovery Coach chat UI to match site design language. Updated to use CSS variables (--gradient-primary, --primary-dark, --accent-green, --bg-light, --bg-lighter), consistent border-radius/shadows, proper dark mode with site colors, and PWA safe-area-inset handling for notch/Dynamic Island support. Welcome chips now include icons, crisis banner uses softer styling, assistant bubbles use bordered card style.
- **2026-02-19:** Implemented revenue strategy: AI Recovery Coach as premium subscription anchor ($4.99/mo), BetterHelp affiliate CTAs on blog posts, Ko-fi donation link in footer. Removed AdSense (denied for recovery content). Simplified pricing to Free + Premium tiers. Added coach_service.py with Claude Haiku integration, RecoveryCoachSession/CoachMessage models, chat UI at /accounts/recovery-coach/. Made messaging unlimited on free tier (was 10/month). Increased free group limit from 2 to 5.
- **2026-02-19:** Fixed PostgreSQL OperationalError connection drops on Railway. Root cause: `conn_max_age=0` created a new DB connection per request, overwhelming Railway's proxy (`caboose.proxy.rlwy.net`) with connection churn. Changed `conn_max_age` from 0 to 600 (reuse connections for 10 minutes, validated by `CONN_HEALTH_CHECKS`). Increased `connect_timeout` from 10s to 30s. Rewrote `DatabaseConnectionMiddleware` to use Django's `close_old_connections()` and added `process_exception()` handler to close dead connections on mid-request failures.
- **2026-02-08:** Updated iOS PWA install instructions on `/install/` page. Added missing step for tapping the "..." (More) button in Safari before the Share button. Added Safari-required info banner, in-app browser warning (for links opened from Facebook/Instagram/texts), toolbar visibility tips, and "Edit Actions" fallback for finding "Add to Home Screen". iOS instructions now 6 steps instead of 5.
- **2026-01-30:** Fixed suggested users not displaying on community, pal dashboard, and social feed pages. Root cause: `suggested_users` view was passing three separate context variables (`mutual_suggestions`, `similar_users`, `new_members`) but template expected unified `suggested_users` variable. Rewrote view to combine all suggestions with multi-level fallback logic: (1) mutual followers, (2) same recovery stage, (3) similar interests, (4) new members (last 30 days), (5) any active public users. Also fixed social feed suggestions which only showed users who had posted - added fallback for small user bases. Fixed duplicate URL name conflict between `/community/suggested/` and `/suggested-users/` routes.
- **2026-01-26:** Website testing and SEO fixes. Fixed /terms/ page 500 error (changed `{% url 'privacy' %}` to `{% url 'core:privacy' %}`). Shortened meta descriptions to 120-160 characters on index.html, alcohol_recovery_app.html, sobriety_calculator.html, and context_processors.py for better SEO. Added ADMIN_SECRET_KEY authentication to `create_seo_posts` view for triggering blog post creation on production without login.
- **2026-01-26:** Fixed Recovery Pal accept/decline functionality. Added `respond_pal_request` view and URL pattern `/pals/respond/<pal_id>/`. Fixed pal_dashboard view logic to properly identify sent requests (user1=current user) vs received requests (user2=current user). Updated template to use proper form actions with hidden action field for accept/decline.
- **2026-01-13:** Fixed email system to use Resend HTTP API instead of unreliable SMTP. Created `apps/accounts/email_service.py` with `send_email()` function that uses Resend HTTP API as primary method with SMTP fallback. Updated all Celery tasks (welcome emails, check-in reminders, weekly digests, meeting reminders, pal nudges) and newsletter tasks to use new service. Includes retry logic with exponential backoff and rate limit handling. Added `--resend-api` flag to `test_email` management command. Root cause was SMTP connections failing on Railway with "Connection unexpectedly closed" errors.
- **2026-01-11:** Added comprehensive Privacy Policy and Terms of Service pages. Privacy policy covers data collection, usage, third-party services, user rights, CCPA compliance, and data security. Terms of service includes health disclaimer with crisis resources, prohibited conduct specific to recovery platforms, user content policies, and subscription terms. Updated sitemap.xml with new lastmod dates.
- **2026-01-10:** Enhanced progress visualizations page: added mood distribution pie chart, weekly comparison (this week vs last week with percentage change), 90-day check-in calendar heatmap (GitHub-style), milestone progress bar with days until next milestone, and dark mode support for all charts.
- **2026-01-10:** Improved service worker caching strategy: removed duplicate sw.js, created standalone offline.html (doesn't require Django templates), added main.js to static cache, excluded API endpoints from caching (/api/, notifications, social feed posts), switched HTML pages to network-first strategy (shows fresh content, caches as fallback). Cache version bumped to v21.
- **2026-01-10:** Implemented mobile push notifications infrastructure. New `DeviceToken` model stores FCM/APNs tokens. API endpoints `/accounts/api/device-token/register/` and `/unregister/` for mobile apps. `push_notifications.py` updated with `send_fcm_notification()` and `send_apns_notification()` functions. Requires Firebase credentials JSON and APNs .p8 key file to enable. See `PUSH_NOTIFICATIONS_SETUP.md` for configuration guide.
- **2026-01-10:** Added image compression for uploads. New `image_utils.py` module provides validation (5MB limit, MIME type check), compression (max 1920px for posts, 1200px for groups, JPEG quality 85), and Cloudinary integration. Social post images and group images now auto-compressed before storage.
- **2026-01-10:** Fixed dark mode toggle not working - main.js was not included in base.html.
- **2026-01-10:** Implemented infinite scroll on social feed. New API endpoint `/accounts/social-feed/posts/` returns paginated JSON. IntersectionObserver detects scroll position and loads more posts automatically. Event handlers refactored to delegation pattern for dynamically loaded posts. Fallback to pagination for non-JS browsers.
- **2026-01-10:** Implemented optimistic UI for likes and comments on social feed. Like button toggles immediately before server response with rollback on error. Comments appear instantly with "Sending..." state, removed on failure. Toast notification system added for error feedback.
- **2026-01-10:** Added skeleton loaders to social feed for improved perceived loading performance. Shimmer animation placeholders for post cards replace spinners during page load. Reusable skeleton partials and JavaScript utilities for future expansion.
- **2026-01-10:** Added dark mode support with system preference detection and manual toggle. Theme toggle button in navigation bar (desktop and mobile). Preferences persist via localStorage. Includes comprehensive CSS overrides for all components.
- **2026-01-10:** Added accountability nudges for Recovery Pals - sends notifications and emails when a pal hasn't checked in for 3+ days. Both inactive user and their active pal receive prompts. Celery Beat task runs daily at 2 PM UTC with 3-day cooldown.
- **2026-01-10:** Added progress visualizations page at `/accounts/progress/` with Chart.js charts showing mood, craving, and energy trends over 7/30/90 days. Includes stats grid, insights section, and navigation links.
- **2026-01-10:** Added meeting reminders feature - sends push notifications and emails 30 minutes before bookmarked meetings. Includes Celery Beat task running every 15 minutes with timezone-aware scheduling.
- **2026-01-09:** Added prominent sobriety counter widget to profile page with gradient design, years/months/weeks breakdown, milestone progress bar, motivational messages, and share button.
- **2026-01-09:** Added daily gratitude prompt to check-in feature with quick-fill tags and featured gratitude section.
- **2026-01-09:** Fixed z-index issue where pagination was blocking top navigation menu.
- **2026-01-09:** Fixed empty feed problem for new users - added suggested users section with follow buttons when feed is sparse.
- **2026-01-09:** Implemented onboarding overhaul - users now land on social feed first with progressive profile completion banner.
- **2026-01-09:** Fixed pagination display bugs on community page (Total Members), my_challenges (badges count), and group_detail (posts count).
- **2026-01-07:** Fixed welcome emails not sending - REDIS_URL on web service was missing authentication credentials. Updated to use internal Redis URL with auth.
- **2026-01-07:** Created dedicated `celery-worker` service on Railway running `celery -A recovery_hub worker -l info -B` with Beat scheduler embedded. All scheduled tasks (welcome emails, check-in reminders, weekly digests) now execute properly.
- **2026-01-05:** Submitted 6 priority URLs to Google Search Console for indexing: sobriety-calculator, sobriety-counter-app, sober-grid-alternative, and 3 high-volume blog posts (alcohol withdrawal, signs of alcoholism, how to stop drinking).
- **2026-01-04:** Created `/sobriety-calculator/` interactive tool page with no-signup-required calculator, money saved estimator, health benefits timeline, and milestone tracker. Targets "sobriety calculator", "how long have I been sober", and "clean time calculator" keywords.
- **2026-01-02:** Created admin endpoint `/blog/admin/create-seo-posts/` to run blog post creation on production.
- **2026-01-02:** Published 6 SEO blog posts to production database.
- **2026-01-01:** Created 6 SEO-optimized blog posts targeting high-volume keywords (83K combined monthly searches): alcohol withdrawal, signs of alcoholism, how to stop drinking, sober curious, high-functioning alcoholic, dopamine detox.
- **2026-01-01:** Added comprehensive SEO & Traffic Growth Strategy section with landing page roadmap, blog optimization plan, backlink strategy, and social marketing tactics.
- **2026-01-01:** Added Revenue Strategy section with donation, affiliate, premium tier, merchandise, B2B licensing, and coach marketplace plans.
- **2026-01-01:** Added current analytics status from Google Analytics and Search Console data.
- **2026-01-01:** Created `/alcohol-recovery-app/` SEO landing page with schema markup.
- **2026-01-01:** Added SEO landing pages to sitemap.xml.
- **2026-01-01:** Completed SEO quick wins: alt text optimization, internal linking, FAQ schema, Core Web Vitals preconnect hints.
- **2025-12-27:** Added push notification triggers - integrated with create_notification() helper, logs for now (enable FCM/APNs when ready).
- **2025-12-27:** Added weekly digest email - sent Sundays at 10:30 AM with new followers, popular posts, unread notifications.
- **2025-12-27:** Added daily check-in reminder email - sent at 5 PM to users who haven't checked in, shows streak status.
- **2025-12-27:** Added welcome email sequence - Day 1 (immediate), Day 3, Day 7 with personalized stats and CTAs.
- **2025-12-27:** Added Celery Beat schedule for retention emails - scheduled tasks for engagement campaigns.
- **2025-12-27:** Added engagement email tracking fields - welcome_email_1_sent, welcome_email_2_sent, welcome_email_3_sent, last_checkin_reminder_sent, last_weekly_digest_sent.
- **2025-12-27:** Added milestone share buttons - milestones page (WhatsApp, native share), celebration modal, profile cards with hover-reveal share.
- **2025-12-27:** Surfaced invite codes - added "Invite Friends" link to quick actions sidebar, edit profile page, and mobile menu.
- **2025-12-27:** Added quick reactions with emoji picker - tap React button to show picker, reactions display as emoji summary.
- **2025-12-27:** Added pull-to-refresh gesture for mobile feed - pull down from top to reload content.
- **2025-12-27:** Added PostReaction model for emoji-based reactions on social posts.
- **2025-12-27:** Added milestone celebrations with confetti animation when users hit sobriety milestones (1, 7, 14, 30, 60, 90, 180, 365+ days).
- **2025-12-27:** Added streak indicator showing consecutive check-in days with fire emoji in the check-in widget.
- **2025-12-27:** Added progress bar showing days until next sobriety milestone.
- **2025-12-27:** Added one-tap check-in widget to social feed sidebar. Users can now check in their mood with a single click without navigating away.
- **2025-12-27:** Fixed infinite recursion bug in UserConnection.save() that caused errors when following certain users.
- **2025-12-27:** Fixed avatar fallback for users with broken/missing avatar images on community pages.
- **2025-12-27:** Redesigned onboarding wizard with 5 steps: recovery stage, interests, profile, privacy, connect. Added recovery_stage and interests fields to User model for smarter user matching.
- **2025-12-27:** Fixed notification click not marking as read (race condition in JS handler)
- **2025-12-24:** Completed all group features: archive groups, like/unlike posts, pin posts, invite links
- **2025-12-24:** Added group notifications, comments on posts, transfer ownership feature
- **2025-12-24:** Added approve/reject pending members, edit group settings, fixed age display bug
- **2025-12-24:** Fixed groups system bugs (my_groups context, group detail context, create_group missing group_type), added group posting and leave functionality
- **2025-12-11:** Streamlined for social-first focus, added beta growth priorities
- **2025-11-20:** Initial comprehensive documentation

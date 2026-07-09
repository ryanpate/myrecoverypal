# CLAUDE.md - MyRecoveryPal Development Guide

**Last Updated:** 2026-03-03
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

Users land on the **progress home** (`accounts:progress`) after login — the daily check-in + streak + sobriety counter live here. The Social Feed is one tap away in the nav.

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

**Rate Limits:** (see `apps/accounts/coach_service.py::can_send_message`)
- Free users: 3 routine messages per day (resets daily)
- Premium users: 20 messages per day
- **Crisis-triggered sessions are exempt** — a coach session opened from a
  struggling/high-craving check-in (`trigger='checkin_support'`) is never
  limited and its messages don't count toward the daily total, so a user is
  never paywalled mid-struggle.

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
6. ~~Daily pledge ritual on the progress home~~ ✅ COMPLETE — one-tap "I pledge to stay sober today" card (photo + personal reason + pledge streak). Backed by the `DailyPledge` model (separate from `DailyCheckIn` so it never touches mood analytics). Endpoint `POST /accounts/pledge-today/`; streak via `User.get_pledge_streak()`. Onboarding step 3 captures `pledge_reason`/`pledge_photo` and now lands on `accounts:progress`.
   - **Pledge v2 (2026-07-04):** (a) **Per-user timezone** — `User.timezone` (IANA, auto-detected from the browser via `POST /accounts/set-timezone/`), activated per request by `apps/accounts/middleware.py::UserTimezoneMiddleware`. ALL pledge/check-in "today" math uses `timezone.localdate()` (never `timezone.now().date()`), so streaks/pledges roll over at the user's local midnight, not UTC. (b) `DailyPledge` gained `note` + `photo`, editable after completion via `POST /accounts/pledge/update/`. (c) Share a pledge to the feed (`POST /accounts/pledge/share-feed/` → public `SocialPost`) or externally (share button → myrecoverypal.com link). (d) The check-in-page pledge card and the progress-home card are now **synced** (both read `pledged_today`/`pledge_streak` and write via the same endpoints — one `DailyPledge` per user-local day). NOTE: the check-in pledge affordances live in a `<div id="pledgeNoteForm">` (NOT a `<form>`) — never nest a form inside `#checkin-form`; the `CheckinNoNestedFormTests` parser test guards this.

#### Polish (Priority: MEDIUM) - ALL COMPLETE ✅
1. ~~Dark mode~~ ✅ COMPLETE
2. ~~Skeleton loaders for content~~ ✅ COMPLETE
3. ~~Optimistic UI for likes/comments~~ ✅ COMPLETE
4. ~~Infinite scroll on feeds~~ ✅ COMPLETE
5. ~~Image compression for uploads~~ ✅ COMPLETE

#### Technical Debt (Priority: LOW)
1. ~~Service worker caching review~~ ✅ COMPLETE
2. Improved offline support
3. ~~Performance audit (N+1 queries)~~ ✅ Phase 1 complete (reaction/comment N+1 fixed, progress view aggregates batched)
4. ~~Static file cache busting~~ ✅ COMPLETE — migrated to `CompressedManifestStaticFilesStorage` (content-hashed + pre-brotli). `{% static %}` auto-generates hashed URLs.

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
- `DailyPledge` - One-tap daily sobriety pledge (own model, `unique_together` per day; drives the pledge streak, kept separate from check-in/mood analytics)
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
    get_pledge_streak()   # consecutive DailyPledge days (distinct from get_checkin_streak)
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
CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
```

**Note:** The Cloudinary vars are required on `celery-worker` too, not just `web`.
Emails sent by the worker (shop digest, milestone celebrations) render
`product.image.url`. Without `CLOUDINARY_CLOUD_NAME`, `settings.py` skips the
Cloudinary storage backend and `.url` returns a relative `/media/...` path with
no domain — so product images show as broken in the email.

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

## SEO & Traffic Growth Strategy

### Current SEO Assets
- **Landing Pages:** 8 SEO-optimized pages targeting high-volume keywords
- **Blog:** 58+ posts including 6 SEO-optimized articles (83K monthly search volume)
- **Schema:** Organization, WebSite, FAQPage, SoftwareApplication
- **Sitemap:** `/sitemap.xml` with 25+ URLs
- **Robots.txt:** Properly configured for crawling

### SEO — Bulk-removing already-crawled thin pages (one-time manual step)

For the 170+ URLs in "Crawled, not indexed" that we've now properly noindexed (PR #136, May 2026), the natural deindex flow takes 4-8 weeks. To accelerate:

1. Open Google Search Console → property → **Indexing** → **Removals**
2. Click **New request** → **Remove all URLs with this prefix**
3. Submit each of:
   - `https://www.myrecoverypal.com/blog/tag/`
   - `https://www.myrecoverypal.com/blog/category/`
4. Each prefix submission removes URLs for 6 months. By that point, the natural deindex (driven by our `noindex` meta + header) is complete and the URLs stay out of the index.

This is a one-time manual step. The code-level work (noindex meta tag on thin pages + robots.txt no longer blocking the crawl) ships automatically with every deploy from now on.

If `/blog/tag/` and `/blog/category/` reappear in "Crawled, not indexed" later, that's expected — Google will keep recrawling them periodically. The noindex directive should win every time. Don't re-submit removal requests unless they actually get indexed.

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

### HIGH - SEO Technical Fixes (from March 2026 audit)
**Data:** 3,189 impressions → 85 clicks (2.7% CTR). Most keywords position 30-90+. Organic Search grew to 23% of traffic but still underperforming.

- [x] **Update 2025→2026** on all SEO landing page titles and schema (7 pages) — freshness signal
- [x] **Rewrite sober-grid-alternative meta tags** — was 622 impressions at position 6 with 0.16% CTR, rewrote title/description to target "Sober Grid shut down" queries
- [x] **Add Sober Grid shutdown content** — dedicated section with timeline, FAQ expansion, schema FAQ additions targeting position 3-6 queries
- [x] **Investigate March impression crash** ✅ Root cause: 85 of 115 indexed pages dropped (115→30). www/non-www duplicate content, 112 thin tag/category pages, auth pages indexed. Fixed with PREPEND_WWW, SEONoIndexMiddleware, robots.txt overhaul.
- [x] **Fix 404 errors** ✅ Added 14 total 301 redirects for common paths (signup, login, feed, dashboard, community, groups, meetings, coach, pricing, home)
- [x] **Improve /sobriety-calculator/ page** ✅ Expanded to 1,500+ words, pre-populated 90-day demo, 9 FAQs, noscript fallback, health timeline (12 stages), money savings breakdown
- [x] **Push dopamine-detox blog post to page 1** ✅ Added internal links from 5 landing pages (homepage, sobriety calculator, alcohol recovery, drug recovery, mental health)
- [x] **Boost /drug-addiction-recovery-app/** ✅ Added unique drug recovery content section (withdrawal timelines by substance) + internal links via _related_tools partial
- [x] **Internal linking overhaul** ✅ Created _related_tools.html partial, all 9 landing pages cross-link to top 3 traffic drivers. sober_grid_alternative went from 0→3 landing page links.
- [x] **Remove or noindex /store/ page** ✅ Noindexed + removed from sitemap + disallowed in robots.txt
- [ ] **Revive organic social** — dropped from 44% to 2% of traffic. TikTok/IG content creation paused

### App Store Presence

iOS app is **live** (App Store ID 6760084657, v1.1.0). The full submission checklist, iOS native-features table (Guideline 4.2 compliance), IAP architecture diagram, and App Store listing metadata are archived in [`docs/archive/CLAUDE-completed.md`](docs/archive/CLAUDE-completed.md).

**Open items:**
- [ ] Android: upload AAB to Google Play Console, complete store listing (screenshots, description, data safety), submit for review
- [ ] iOS: create APNs Auth Key (.p8), configure Xcode signing, set Railway env vars (`APNS_KEY_CONTENT`, `APNS_KEY_ID`, `APNS_TEAM_ID`, `REVENUECAT_IOS_API_KEY`)
- [ ] Request reviews from existing users

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

### Court Compliance Tier ($29.99/mo, $269/yr) — Added 2026-05-23, repriced 2026-07-09

Fourth subscription tier targeting court-ordered AA/NA/SMART attendees (DUI, drug court, family court). Court-ordered users have legally-mandated proof-of-attendance obligations — high willingness-to-pay, distinct from recovery-community Premium audience.

**Service files:**
- `apps/accounts/court_models.py` — `CourtReportProfile`, `MeetingAttendance`, `CourtReport`
- `apps/accounts/court_service.py` — WeasyPrint PDF rendering with two-pass SHA-256 hash embedding
- `apps/accounts/court_views.py` — dashboard, attendance CRUD, report generation, email-to-PO, public verify
- `apps/accounts/court_forms.py` — profile + attendance forms
- `apps/accounts/decorators.py::court_required` — tier-gating decorator

**Routes:**
- `/accounts/court/` — Court Compliance dashboard (court-tier only)
- `/accounts/court/profile/` — Setup court profile (case number, PO email, required meetings/week)
- `/accounts/court/attendance/` — Log of attended meetings
- `/accounts/court/reports/` — Generate and download PDF reports
- `/accounts/court/reports/<id>/email/` — Email PDF to probation officer
- `/verify/court/<hash>/` — Public hash verification (no auth)
- `/court-ordered-meeting-tracker/` — Public SEO landing page

**Key design notes:**
- The unused `pro` tier in `Subscription.TIER_CHOICES` was renamed to `court` (migration 0034). Helper methods are `is_court()` and decorator is `@court_required`.
- PDF rendering uses two-pass approach: render placeholder hash → compute real hash → re-render with real hash embedded. Guarantees the printed hash inside the PDF matches `sha256(pdf_bytes)`.
- Public verify endpoint at `/verify/court/<hash>/` intentionally does NOT show legal name or case number — only confirms a report with that fingerprint exists. Privacy by default.
- Court tier is a superset of Premium: `is_premium()` returns True for court-tier users.
- Program-neutral coverage (AA, NA, CA, MA, GA, SMART, Refuge, LifeRing, secular) — important because courts cannot constitutionally require 12-step-only attendance.
- WeasyPrint on macOS requires `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (Pango libs from Homebrew). Linux/Railway has the libs in the default path.
- `send_email()` in `email_service.py` now supports an `attachments` kwarg (list of `(filename, bytes, content_type)` tuples). Resend HTTP only; SMTP fallback ignores attachments.

**Phase 2 deferred:**
- GPS verification at meeting location
- Sponsor/chair digital signature flow (email-confirmed)
- QR code check-in at meetings
- Photo upload of paper attendance cards
- Calendar heatmap of attendance history
- Auto-recurring monthly email to probation officer

**Plan:** `docs/plans/2026-05-23-court-compliance.md`

**Stripe wiring: DONE** (verified live 2026-07-03 — product, prices, plan rows, checkout, and webhook all work; the old "mailto placeholder" TODO here was stale). **Reprice to $29.99/mo + $269/yr (2026-07-09):** run `python3 manage.py setup_court_stripe --commit` in a Railway shell (new defaults bake in the new prices; idempotent — creates new Stripe prices, transfers lookup_keys, archives old, syncs `SubscriptionPlan` rows). All price copy (pricing page + court landing page) renders from the plan rows, so it updates the moment the command runs.

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
├── App/SobrietyCounterWidget/  # WidgetKit extension (Swift)
│   ├── SobrietyCounterWidget.swift       # Data model, milestone logic, timeline provider
│   └── SobrietyCounterWidgetViews.swift  # SwiftUI views (small + medium)
├── App/Plugins/WidgetBridgePlugin.swift  # Capacitor↔Widget data bridge
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

## Changelog

Full project changelog moved to [`docs/CHANGELOG.md`](docs/CHANGELOG.md) to keep this guide lean. Add new entries there.

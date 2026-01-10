# CLAUDE.md - MyRecoveryPal Development Guide

**Last Updated:** 2026-01-09
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
npm run cap:sync                              # Sync to mobile platforms
npm run cap:open:android                      # Open Android Studio
npm run cap:open:ios                          # Open Xcode
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

#### Polish (Priority: MEDIUM)
1. ~~Dark mode~~ ✅ COMPLETE
2. Skeleton loaders for content
3. Optimistic UI for likes/comments
4. Infinite scroll on feeds
5. Image compression for uploads

#### Technical Debt (Priority: LOW)
1. Service worker caching review
2. Mobile gesture support
3. Improved offline support
4. Performance audit (N+1 queries)

#### Infrastructure
1. Enable mobile push (FCM/APNs)
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
- **Stripe** - Subscriptions (14-day premium trial on signup)
- **Cloudinary** - Media storage
- **SendGrid** - Email (production), Resend API key also configured
- **Sentry** - Error monitoring
- **Firebase** - Push notifications (configured, needs implementation)

### Mobile
- **Capacitor 7.4.4** - Native wrapper
- **Firebase Cloud Messaging** - Push notifications

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
SENTRY_DSN=...
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

### MEDIUM - Analytics (PARTIAL)
- [x] **Basic funnel tracking** - Google Analytics G-81SZGNRESW already integrated
- [ ] **Admin dashboard** - User engagement metrics in Django admin
- [ ] **A/B testing** - Onboarding variations

---

## SEO & Traffic Growth Strategy

### Current SEO Assets
- **Landing Pages:** 8 SEO-optimized pages targeting high-volume keywords
- **Blog:** 58+ posts including 6 SEO-optimized articles (83K monthly search volume)
- **Schema:** Organization, WebSite, FAQPage, SoftwareApplication
- **Sitemap:** `/sitemap.xml` with 25+ URLs
- **Ads.txt:** Google AdSense verification configured
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
- [ ] Publish to Apple App Store (Capacitor already configured)
- [ ] Publish to Google Play Store
- [ ] App Store Optimization (ASO): keywords, screenshots, description
- [ ] Request reviews from existing users

---

## Revenue Strategy

### Current State
- **Revenue:** $0
- **Google AdSense:** Applied (pending approval), ads.txt configured
- **Stripe:** Configured but no active subscriptions
- **Store:** Coming soon page exists

### IMMEDIATE - No Development Required

#### 1. Donation System
- [ ] Add Ko-fi or Buy Me a Coffee integration
- [ ] "Support Our Mission" button in footer/sidebar
- [ ] One-time and monthly donation options

#### 2. Affiliate Marketing
| Partner | Commission | Integration |
|---------|------------|-------------|
| Amazon (recovery books) | 4-10% | Link in resources |
| BetterHelp | $100-200/referral | Blog posts, resources |
| Treatment center directories | $50-500/lead | Meeting finder page |

- [ ] Create affiliate resources page
- [ ] Add affiliate disclosures to relevant pages

#### 3. Sponsored Content
Once traffic increases:
- Sponsored blog posts: $200-500 each
- Partners: Treatment centers, sober lifestyle brands

### SHORT-TERM - Development Required

#### 4. Premium Tier ("MyRecoveryPal Pro")
| Free | Premium ($4.99/mo or $29.99/yr) |
|------|--------------------------------|
| Social feed | Advanced analytics & charts |
| Basic groups | Unlimited private groups |
| Daily check-in | Guided meditations library |
| 30-day journal | Unlimited journal + export |
| 1 accountability pal | Unlimited pals |
| Community challenges | Create custom challenges |

- [ ] Create pricing page
- [ ] Implement Stripe subscription tiers
- [ ] Build premium feature gates

#### 5. Recovery Merchandise Store
- [ ] Milestone tokens/coins (physical)
- [ ] Recovery affirmation cards
- [ ] Journals with prompts
- [ ] Apparel (hoodies, t-shirts)

### MEDIUM-TERM - Business Development

#### 6. B2B Licensing
| Customer | Use Case | Pricing |
|----------|----------|---------|
| Treatment centers | White-label platform | $500-2,000/mo |
| EAP providers | Employee recovery support | $1,000-5,000/mo |
| Sober living facilities | Resident community | $200-500/mo |

#### 7. Recovery Coach Marketplace
- Connect users with certified recovery coaches
- 15-20% platform fee
- Video/chat sessions through platform

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
│   ├── invite_models.py  # Invite/waitlist system
│   └── signals.py        # Activity creation
├── blog/                  # Community blog
├── journal/               # Private journaling
├── core/                  # Static pages
├── newsletter/            # Email campaigns
└── support_services/      # Meeting finder

resources/                 # Resource library
recovery_hub/             # Django config
templates/                # Global templates
static/                   # CSS, JS, images
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

### LOWER PRIORITY - Polish

| Feature | Impact | Effort | Status |
|---------|--------|--------|--------|
| ~~Dark mode~~ | Medium | Medium | ✅ Done |
| **Skeleton loaders** | Low | Low | Replace spinners with content placeholders. Feels faster. |
| **Optimistic UI** | Medium | Medium | Likes/comments appear instantly. Feels more responsive. |
| **Infinite scroll** | Low | Medium | Replace pagination on feeds. Modern UX expectation. |
| **Image compression** | Low | Low | Auto-compress uploads for faster loading. |

### Technical Debt to Address

- [ ] **Service worker caching strategy** - Review what's cached, ensure updates propagate
- [ ] **Mobile gesture support** - Swipe actions for common tasks
- [ ] **Offline support** - Allow viewing cached content when offline
- [ ] **Performance audit** - Check for N+1 queries, slow page loads

---

## Changelog

- **2026-01-10:** Added dark mode support with system preference detection and manual toggle. Theme toggle button in navigation bar (desktop and mobile). Preferences persist via localStorage. Includes comprehensive CSS overrides for all components.
- **2026-01-10:** Added accountability nudges for Recovery Pals - sends notifications and emails when a pal hasn't checked in for 3+ days. Both inactive user and their active pal receive prompts. Celery Beat task runs daily at 2 PM UTC with 3-day cooldown.
- **2026-01-10:** Added progress visualizations page at `/accounts/progress/` with Chart.js charts showing mood, craving, and energy trends over 7/30/90 days. Includes stats grid, insights section, and navigation links.
- **2026-01-10:** Added meeting reminders feature - sends push notifications and emails 30 minutes before bookmarked meetings. Includes Celery Beat task running every 15 minutes with timezone-aware scheduling.
- **2026-01-09:** Fixed ads.txt to use hardcoded content for reliability - file-based approach was failing on production.
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
- **2026-01-02:** Added ads.txt route for Google AdSense verification at `/ads.txt`.
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

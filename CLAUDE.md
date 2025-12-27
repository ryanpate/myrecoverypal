# CLAUDE.md - MyRecoveryPal Development Guide

**Last Updated:** 2025-12-27
**Project:** MyRecoveryPal - Social Recovery Platform
**Tech Stack:** Django 5.0.10, PostgreSQL, Redis, Celery, Capacitor Mobile
**Stage:** Beta Testing - User Acquisition Critical

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

### Identified Gaps

| Gap | Status | Priority |
|-----|--------|----------|
| No onboarding flow | New users land on empty feed | CRITICAL |
| No referral system | Invite codes exist but aren't surfaced | CRITICAL |
| No share buttons | Milestones can't be shared externally | HIGH |
| No suggested users | Empty feed for new users | HIGH |
| No email engagement | Single welcome email only | HIGH |
| No push triggers | Firebase configured, not implemented | MEDIUM |
| No analytics | Can't measure engagement | MEDIUM |

### Recommended Implementation Order

#### Phase 1: First-Time User Experience (Week 1-2)
1. **Onboarding wizard** after registration
   - Step 1: Profile photo + bio
   - Step 2: Select interests (recovery stage, group types)
   - Step 3: Follow suggested users (5-10 active members)
2. **Seed content** - Ensure feed has posts even for new users
3. **Empty state CTAs** - "Your feed is empty - follow some people!"

#### Phase 2: Viral Growth (Week 2-3)
1. **Referral link in profile settings** - Surface existing InviteCode system
2. **"Invite Friends" button** - Generate shareable invite links
3. **Share milestone cards** - Social media sharing for achievements
4. **Achievement badges** - Shareable graphics for milestones

#### Phase 3: Retention (Week 3-4)
1. **Email drip campaign** - Day 1, 3, 7, 14 engagement emails
2. **Push notifications** - New follower, comment, group invite
3. **Daily check-in reminders** - If user hasn't checked in
4. **Weekly digest** - "Here's what you missed"

#### Phase 4: Analytics (Week 4+)
1. **Google Analytics / Mixpanel** - Basic funnel tracking
2. **Admin engagement dashboard** - User activity metrics
3. **A/B testing** - Onboarding variations

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
- **SendGrid** - Email
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
EMAIL_HOST_PASSWORD=<sendgrid-key>
SENTRY_DSN=...
```

---

## Deployment

**Platform:** Railway (auto-deploy from `main`)

```bash
# Build
./build.sh

# Web
gunicorn recovery_hub.wsgi:application

# Worker (separate service)
celery -A recovery_hub worker -l info
```

---

## Immediate TODOs for Beta Success

### CRITICAL - User Acquisition
- [x] **Onboarding wizard** - 5-step wizard with recovery stage, interests, profile, privacy, and smart user matching
- [x] **Suggested users** - Matching algorithm uses recovery_stage and interests for better connections
- [ ] **Surface invite codes** - Add "Invite Friends" to profile/settings
- [ ] **Share buttons** - External sharing for milestones

### HIGH - Retention
- [ ] **Welcome email sequence** - Day 1, 3, 7 engagement emails
- [ ] **Push notification triggers** - New follower, comment, like
- [ ] **Daily check-in reminder** - Email/push if inactive
- [ ] **Weekly digest** - Summary of missed activity

### MEDIUM - Analytics
- [ ] **Basic funnel tracking** - Registration → Activation → Retention
- [ ] **Admin dashboard** - User engagement metrics

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

| Feature | Impact | Effort | Why |
|---------|--------|--------|-----|
| **Daily gratitude prompt** | High | Medium | "Today I'm grateful for..." prompt increases positive engagement. |
| **Sobriety counter widget** | High | Medium | Prominent, beautiful display of days/months/years sober on profile. |
| **Meeting reminders** | High | Medium | Push notification before saved meetings. Integrates support_services. |
| **Progress visualizations** | Medium | Medium | Charts showing mood trends, craving patterns over time. |
| **Accountability nudges** | Medium | Medium | Prompt Recovery Pals to check in on each other if inactive. |

### LOWER PRIORITY - Polish

| Feature | Impact | Effort | Why |
|---------|--------|--------|-----|
| **Dark mode** | Medium | Medium | Essential for nighttime use, reduces eye strain. |
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

- **2025-12-27:** Added quick reactions with emoji picker (❤️🙏💪🎉) - tap React button to show picker, reactions display as emoji summary.
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

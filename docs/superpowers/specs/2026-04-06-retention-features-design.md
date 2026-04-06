# Retention Features Design Spec

**Date:** 2026-04-06
**Goal:** Improve daily retention at 154 users through three features: seeded feed content, daily pledge, and shareable milestone images.
**Context:** 154 registered users, 0 premium conversions. Users land on sparse feeds and have no daily habit loop. Competitors (I Am Sober) retain users with daily pledges. Milestone sharing drives organic viral growth.

---

## 1. Daily Recovery Thought Cards

### Purpose
Guarantee at least one piece of content in the social feed every day, even when no users have posted. Provides ambient value and makes the community feel alive.

### Model
New model `DailyRecoveryThought` in `apps/accounts/models.py`:

```python
class DailyRecoveryThought(models.Model):
    quote = models.TextField()  # The recovery quote
    author_attribution = models.CharField(max_length=200, blank=True)  # "— Marcus Aurelius" or ""
    reflection_prompt = models.CharField(max_length=300, blank=True)  # "What does this mean for your recovery today?"
    date = models.DateField(unique=True, db_index=True)  # One per day
    created_at = models.DateTimeField(auto_now_add=True)
```

### Data Seeding
Management command `seed_recovery_quotes` pre-loads 90+ quotes into the table with dates starting from today. Quotes sourced from public domain recovery/stoic/mindfulness literature (no copyrighted material). Each quote has an optional reflection prompt to encourage engagement.

### Celery Task
`publish_daily_thought` runs at 6:00 AM UTC daily. Picks the next unused quote (by date) and marks it as today's thought. If no pre-seeded quote exists for today, selects a random previously-used quote from 30+ days ago (recycling).

### Feed Integration
`social_feed_view` and `hybrid_landing_view` query `DailyRecoveryThought.objects.filter(date=today).first()` and pass it as `daily_thought` context variable. Template partial `_daily_thought.html` renders it as the first item in the feed, visually distinct from user posts:
- Gradient background (blue-to-cyan from brand palette)
- Large italic quote text
- Attribution line below quote
- Reflection prompt in lighter text
- No like/comment/reaction controls — it's ambient content, not a post

Included via `{% include 'accounts/partials/_daily_thought.html' %}` at the top of the post list in both `social_feed.html` and `hybrid_landing.html`.

### What it does NOT do
- Does not create `SocialPost` objects (avoids polluting user-generated content)
- Does not send notifications about new quotes
- Does not require user interaction

---

## 2. Daily Pledge (Integrated into Check-in)

### Purpose
Create a daily habit loop (open app → pledge → check in). I Am Sober's #1 retention feature is the daily pledge. Integrating into the existing check-in avoids creating a competing daily touchpoint.

### Model Changes
Add to `DailyCheckIn` in `apps/accounts/models.py`:

```python
pledge_taken = models.BooleanField(default=False)
pledge_time = models.DateTimeField(null=True, blank=True)
```

No migration dependency on other features.

### Check-in Flow Change
Current flow: Mood → Craving → Energy → Gratitude → Share
New flow: **Pledge → Mood → Craving → Energy → Gratitude → Share**

The pledge step is a full-width card in the check-in page:
- Large text: "I pledge to stay sober today"
- Single button: "Take My Pledge" (green, prominent)
- Optional: one-line text input "My reason today:" (stored as `pledge_reason` if we add the field, or reuse the existing `goal` field)
- After tapping, the pledge card animates to a checkmark and the mood step appears

If the user has already pledged today (existing `DailyCheckIn` with `pledge_taken=True` for today's date), the pledge step auto-skips to mood.

### Social Proof
When a user takes the pledge, create an `ActivityFeed` entry: "[Username] took today's pledge" — appears in the social feed as a lightweight activity item. This shows other users that the community is active without requiring full post creation.

### Streak Tracking
The existing `get_checkin_streak()` method on the User model already counts consecutive check-in days. No change needed — pledges are part of check-ins. The streak counter on the profile page and progress page already reflects this.

### Notification Copy Update
The 5 PM check-in reminder (Celery task `send_checkin_reminders`) gets updated subject line: "Take your daily pledge and check in" (was: "Time for your daily check-in").

### What it does NOT do
- Does not create a separate pledge page or interstitial modal
- Does not require the pledge to complete the check-in (user can skip to mood)
- Does not have its own separate streak counter (leverages check-in streak)

---

## 3. Shareable Milestone Images

### Purpose
Generate branded, social-media-ready images that users share to Instagram/TikTok/WhatsApp when they hit milestones or want to celebrate their progress. Each share is organic marketing reaching people who may know someone in recovery.

### Image Generation
New Django view at `GET /accounts/milestone-image/<int:days>/`:
- Requires authentication
- Returns a PNG image (Content-Type: image/png)
- Query param `?format=square` for 1080x1080 (default: 1080x1920 story format)

Uses Pillow to composite layers:
1. **Background template** — 3 pre-made gradient PNGs in `static/images/milestones/`:
   - `bg-early.png` (blue-to-cyan) for 1-29 days
   - `bg-mid.png` (green-to-teal) for 30-179 days
   - `bg-long.png` (purple-to-pink) for 180+ days
2. **Main text** — "90 Days Sober" centered, white, bold, large font
3. **Milestone badge** — smaller text below: "3 Months Clean" or milestone name
4. **Watermark** — "MyRecoveryPal.com" at bottom with small logo, semi-transparent

Font: Use a bundled TTF (e.g., Inter Bold or Montserrat Bold) in `static/fonts/` for consistent rendering across servers. Do not rely on system fonts.

### Image Caching
Cache generated images for 24 hours using Django's cache framework (`cache.set(f'milestone_img_{days}_{format}', img_bytes, 86400)`). Same milestone + format = same image bytes (user-specific data like username is NOT included in the image to enable caching).

### Trigger Points

**A. Milestone celebration modal (existing)**
The `milestone_to_celebrate` modal in `social_feed_view` and `progress_view` already shows confetti when users hit milestones. Add a "Share My Milestone" button below the celebration text:
- On iOS native: triggers `window.MRPNative.shareImage(imageUrl)` via the native share sheet
- On web: triggers Web Share API with the image URL, falls back to download link

**B. Progress page on-demand**
Add a "Share My Progress" button on `/accounts/progress/` page. Always visible (not gated to milestones). Generates image for the user's current day count.

### Share Flow
```
User taps "Share My Milestone"
  → JS fetches /accounts/milestone-image/<days>/?format=story
  → On iOS: Capacitor Share plugin with image file
  → On web: Web Share API (if supported) or download-and-share prompt
  → User picks Instagram/WhatsApp/Messages/etc.
```

### Background Template Creation
Create 3 gradient PNG templates (1080x1920 and 1080x1080 variants) using Pillow in a management command `generate_milestone_backgrounds`. This avoids needing a designer — programmatically generated gradients with subtle pattern overlay.

### What it does NOT do
- Does not include the user's name/username in the image (privacy + caching)
- Does not post to the social feed automatically (user chooses where to share externally)
- Does not require premium (sharing is a growth mechanic, not a monetization gate)

---

## Technical Notes

### New Files
- `apps/accounts/models.py` — add `DailyRecoveryThought` model, add `pledge_taken`/`pledge_time` to `DailyCheckIn`
- `apps/accounts/migrations/0025_*.py` — migration for new model + fields
- `apps/accounts/templates/accounts/partials/_daily_thought.html` — quote card partial
- `apps/accounts/management/commands/seed_recovery_quotes.py` — quote seeding command
- `apps/accounts/views.py` — `milestone_image_view` endpoint, update check-in view for pledge
- `apps/accounts/urls.py` — add milestone-image URL
- `static/images/milestones/` — 3 gradient background PNGs (generated)
- `static/fonts/` — bundled TTF font for image generation
- `apps/accounts/management/commands/generate_milestone_backgrounds.py` — background generator

### Modified Files
- `apps/accounts/templates/accounts/social_feed.html` — include daily thought partial
- `apps/accounts/templates/accounts/hybrid_landing.html` — include daily thought partial
- `apps/accounts/templates/accounts/daily_checkin.html` — add pledge step
- `apps/accounts/templates/accounts/progress.html` — add "Share My Progress" button
- `apps/accounts/templates/accounts/social_feed.html` — add "Share" button to milestone celebration modal
- `apps/accounts/tasks.py` — add `publish_daily_thought` task, update check-in reminder copy
- `recovery_hub/settings.py` — add `publish_daily_thought` to Celery Beat schedule

### Dependencies
- Pillow (already installed)
- A bundled TTF font file (Inter Bold or Montserrat Bold, both OFL-licensed)

### No premium gating
All three features are free. They are retention and growth mechanics, not monetization features. Gating them would be counterproductive at 154 users.

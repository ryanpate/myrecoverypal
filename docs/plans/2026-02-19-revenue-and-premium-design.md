# Revenue & Premium Feature Design

**Date:** 2026-02-19
**Status:** Approved
**Goal:** Make MyRecoveryPal financially sustainable while keeping core social features free.

---

## Problem

- 18 registered users, ~58 monthly visitors, $0 revenue
- Site costs money to serve on Railway (web + celery-worker + Postgres + Redis)
- AdSense denied multiple times (recovery/addiction content policy + low traffic)
- Stripe subscription infrastructure is fully built but not activated
- No premium features provide enough value to justify payment
- Blog generates SEO traffic (83K monthly search volume targeted) with zero monetization

## Solution: Three Revenue Streams

### 1. AI Recovery Coach (Premium Anchor Feature)

**What:** A chat-based AI recovery companion at `/accounts/recovery-coach/` powered by Claude API. Users get 24/7 access to CBT-informed coping strategies, journal reflection, guided exercises, and personalized recovery insights.

**Why it's worth $5/month:** Recovery coaching costs $100-300/month. An AI coach available anytime, with context about the user's recovery journey, is massive ROI.

**Architecture:**
- Django view handles POST requests with user message
- Server-side call to Claude API (Haiku model for cost efficiency)
- System prompt includes user context: sobriety days, recent check-in moods, recovery stage, interests
- Last 10 messages stored in DB for conversation continuity
- New `RecoveryCoachSession` and `CoachMessage` models

**System Prompt Design:**
- Recovery-focused, CBT and mindfulness informed, warm and empathetic
- Hard guardrails: never gives medical advice, always refers to professional help and crisis resources for danger signals (suicidal ideation, medical emergencies)
- Contextual: injects user's sobriety date, recent moods, recovery stage
- Stays on topic: recovery, coping, wellness, self-reflection only

**Cost Control:**
- Claude Haiku: ~$0.001 per message
- 20 messages/day limit for premium users
- 3 free trial messages for all users (then upgrade prompt)
- Context window: last 10 messages only (not full history)

**Rate Limiting:**
- Free users: 3 messages total (lifetime trial)
- Premium users: 20 messages/day
- Tracked via `CoachMessage` model with daily count

### 2. Affiliate Revenue (Blog Monetization)

**BetterHelp:**
- Sidebar CTA component on all blog posts: "Talk to a Licensed Therapist"
- Inline contextual CTAs within SEO blog posts (alcohol withdrawal, signs of alcoholism, etc.)
- Dedicated `/resources/therapy/` page
- Estimated: $100-200 per referral

**Amazon Associates:**
- Curated recovery book recommendations on `/resources/books/` page
- Contextual book links within relevant blog posts
- Estimated: 4-10% commission per sale

**Implementation:**
- New reusable template partial: `blog/_affiliate_cta.html`
- Include in `post_detail.html` sidebar and after content
- New standalone pages for therapy resources and book recommendations

### 3. Subscription Activation

**Current state:** Full Stripe infrastructure exists (models, views, webhooks, checkout, management). Not activated because no compelling premium value existed.

**Activation steps:**
1. Create Stripe Products and Prices in dashboard
2. Restructure tiers (see below)
3. Add contextual upgrade prompts at feature gates
4. Make free tier generous enough to hook users, premium compelling enough to convert

### Premium Tier Restructure

| Feature | Free | Premium ($4.99/mo or $29.99/yr) |
|---------|------|--------------------------------|
| Social feed, posts, reactions | Unlimited | Unlimited |
| Messaging | **Unlimited** | Unlimited |
| Groups | Join up to 5 | Unlimited + create private groups |
| Challenges | Join unlimited | Create custom challenges |
| Daily check-in | Yes | Yes |
| Journal | 30 entries/month | Unlimited + PDF export |
| Progress charts | 7-day view | 90-day + yearly trends |
| **AI Recovery Coach** | **3 trial messages** | **20 messages/day** |
| Premium badge | No | Yes |
| Priority support | No | Yes |

**Key change:** Messaging moves to unlimited on free tier. It's the core social action and capping it kills engagement before anyone would want to pay. The AI Coach replaces messaging as the premium gate.

**Drop the Pro tier.** With 18 users, two paid tiers is premature complexity. One free, one premium. Simplify.

### 4. Donation Link

- Ko-fi or Buy Me a Coffee button in footer
- "Support Our Mission" link
- No development beyond adding a link + footer partial

---

## New Models

### RecoveryCoachSession
```python
class RecoveryCoachSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coach_sessions')
    title = models.CharField(max_length=200, blank=True)  # Auto-generated from first message
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
```

### CoachMessage
```python
class CoachMessage(models.Model):
    session = models.ForeignKey(RecoveryCoachSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    tokens_used = models.IntegerField(default=0)  # For cost tracking
```

## New Views

- `recovery_coach()` - GET: render chat UI. POST: send message to Claude, return response.
- `coach_history()` - GET: list past sessions
- `new_coach_session()` - POST: start new conversation

## New Templates

- `accounts/recovery_coach.html` - Chat interface
- `blog/_affiliate_cta.html` - Reusable affiliate CTA partial
- `blog/_affiliate_sidebar.html` - Sidebar affiliate widget

## New URLs

- `/accounts/recovery-coach/` - AI coach chat
- `/accounts/recovery-coach/history/` - Past sessions
- `/accounts/recovery-coach/new/` - New session

## Files Modified

- `apps/accounts/models.py` - Add RecoveryCoachSession, CoachMessage
- `apps/accounts/views.py` - Add coach views
- `apps/accounts/urls.py` - Add coach routes
- `apps/accounts/decorators.py` - Update feature limits for new tier structure
- `apps/blog/templates/blog/post_detail.html` - Add affiliate CTAs
- `templates/base.html` - Add coach link to nav, remove Store, add donation link
- `recovery_hub/settings.py` - Add ANTHROPIC_API_KEY config
- `requirements.txt` - Add anthropic SDK
- `CLAUDE.md` - Update revenue strategy, remove AdSense references

## Environment Variables (New)

- `ANTHROPIC_API_KEY` - For Claude API calls

## Cost Estimates

- Claude Haiku per message: ~$0.001
- 20 messages/day/user = $0.02/day = $0.60/month per active premium user
- At $4.99/month subscription, gross margin ~88% on the AI feature alone
- Break-even: ~1 premium subscriber covers API costs for ~8 active users

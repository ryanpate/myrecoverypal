# Revenue & Premium Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add three revenue streams (AI Recovery Coach subscription, affiliate links, donations) to make MyRecoveryPal financially sustainable.

**Architecture:** Server-side Django views call the Anthropic Python SDK to power an AI recovery coach behind a premium paywall. Blog posts get affiliate CTAs as reusable template partials. Stripe subscriptions (already fully built) get activated with the coach as the premium anchor. Navigation and CLAUDE.md updated to reflect the new strategy.

**Tech Stack:** Django 5.0.10, Anthropic Python SDK (Claude Haiku), Stripe (existing), PostgreSQL

---

### Task 1: Update CLAUDE.md — Remove AdSense, Add Revenue Strategy

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update CLAUDE.md**

Remove all AdSense references. Replace the Revenue Strategy section with the new plan: AI Recovery Coach (premium anchor), affiliate revenue (BetterHelp + Amazon), Stripe subscriptions (activated), donations. Remove "Google AdSense: Applied (pending approval)" from Current State. Remove ads.txt references. Add AI Recovery Coach to the feature/tech documentation. Update the "Remaining Tasks" and "Immediate TODOs" sections. Add changelog entry.

Key content changes:
- Revenue Current State: remove AdSense line
- Revenue IMMEDIATE section: replace AdSense with affiliate links and donation system
- Revenue SHORT-TERM section: replace Premium tier table with new structure (AI Coach as anchor, messaging unlimited on free)
- Add new section: "AI Recovery Coach" documenting the architecture, models, views, system prompt design
- Integrations: add Anthropic SDK
- Environment Variables: add ANTHROPIC_API_KEY
- Changelog: add entry for revenue implementation

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "Update CLAUDE.md: remove AdSense, add AI coach and affiliate revenue strategy"
```

---

### Task 2: Add Anthropic SDK Dependency

**Files:**
- Modify: `requirements.txt` (after line 56)

**Step 1: Add anthropic to requirements.txt**

Add after the last line (line 56):

```
# AI Recovery Coach
anthropic>=0.42.0
```

**Step 2: Install the dependency**

Run: `pip install anthropic>=0.42.0`

**Step 3: Add ANTHROPIC_API_KEY to settings**

Modify: `recovery_hub/settings.py` (after line 721, after STRIPE settings)

Add:
```python
# AI Recovery Coach
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
```

**Step 4: Commit**

```bash
git add requirements.txt recovery_hub/settings.py
git commit -m "Add anthropic SDK dependency and API key config"
```

---

### Task 3: Create Recovery Coach Models

**Files:**
- Modify: `apps/accounts/models.py` (append after line 1772)

**Step 1: Add RecoveryCoachSession and CoachMessage models**

Append to end of `apps/accounts/models.py`:

```python
class RecoveryCoachSession(models.Model):
    """A conversation session between a user and the AI recovery coach."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coach_sessions')
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.title or 'New Session'} ({self.created_at.strftime('%b %d')})"


class CoachMessage(models.Model):
    """A single message in a recovery coach conversation."""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    session = models.ForeignKey(RecoveryCoachSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    tokens_used = models.IntegerField(default=0)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
```

**Step 2: Create and run migration**

Run: `python manage.py makemigrations accounts`
Run: `python manage.py migrate`

**Step 3: Commit**

```bash
git add apps/accounts/models.py apps/accounts/migrations/
git commit -m "Add RecoveryCoachSession and CoachMessage models"
```

---

### Task 4: Build the AI Coach Service

**Files:**
- Create: `apps/accounts/coach_service.py`

**Step 1: Create the coach service module**

This is the core AI integration. It handles:
- Building the system prompt with user context (sobriety days, recent moods, recovery stage)
- Calling the Anthropic API with conversation history
- Rate limiting (3 lifetime messages free, 20/day premium)
- Safety guardrails in the system prompt

```python
import logging
from datetime import date, timedelta
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

RECOVERY_COACH_SYSTEM_PROMPT = """You are a supportive AI recovery coach on MyRecoveryPal, a peer recovery community platform. Your name is Pal.

## Your Role
You are a warm, empathetic recovery companion — not a therapist, doctor, or counselor. You use evidence-based approaches (CBT, mindfulness, motivational interviewing) conversationally to help users reflect on their recovery journey.

## What You Do
- Listen actively and validate feelings
- Help identify triggers and coping strategies
- Offer CBT-based reframing techniques
- Guide breathing exercises and grounding techniques
- Celebrate milestones and progress
- Encourage journaling and check-ins on the platform
- Suggest connecting with other community members

## What You NEVER Do
- Give medical advice or diagnose conditions
- Recommend specific medications or dosages
- Tell someone to stop or change prescribed medication
- Act as a substitute for professional treatment
- Share information about other users
- Discuss topics unrelated to recovery, wellness, and personal growth

## Crisis Protocol
If a user expresses suicidal thoughts, self-harm, or immediate danger, ALWAYS respond with:
1. Acknowledge their pain with empathy
2. Provide these resources:
   - 988 Suicide & Crisis Lifeline: Call or text 988
   - Crisis Text Line: Text HOME to 741741
   - SAMHSA Helpline: 1-800-662-4357
3. Encourage them to reach out to a trusted person or go to their nearest emergency room
4. Do NOT attempt to counsel through a crisis — direct to professionals

## User Context
{user_context}

## Conversation Style
- Warm, conversational, never clinical or robotic
- Use the user's name occasionally
- Keep responses concise (2-4 paragraphs max)
- Ask reflective questions to encourage self-discovery
- Reference their recovery journey when relevant (sobriety milestones, mood patterns)
"""


def build_user_context(user):
    """Build contextual information about the user for the system prompt."""
    context_parts = []

    context_parts.append(f"Name: {user.first_name or user.username}")

    if user.sobriety_date:
        days = (date.today() - user.sobriety_date).days
        context_parts.append(f"Sobriety date: {user.sobriety_date.strftime('%B %d, %Y')} ({days} days sober)")

    if user.recovery_stage:
        context_parts.append(f"Recovery stage: {user.recovery_stage}")

    if user.interests:
        try:
            interests = user.interests if isinstance(user.interests, list) else []
            if interests:
                context_parts.append(f"Interests: {', '.join(interests)}")
        except (TypeError, ValueError):
            pass

    # Recent check-in moods (last 7 days)
    try:
        from apps.accounts.models import DailyCheckIn
        recent_checkins = DailyCheckIn.objects.filter(
            user=user,
            date__gte=timezone.now().date() - timedelta(days=7)
        ).order_by('-date')[:7]
        if recent_checkins:
            moods = [f"{c.date.strftime('%a')}: {c.mood}" for c in recent_checkins]
            context_parts.append(f"Recent moods (last 7 days): {', '.join(moods)}")
    except Exception:
        pass

    # Check-in streak
    try:
        streak = user.get_checkin_streak() if hasattr(user, 'get_checkin_streak') else 0
        if streak > 0:
            context_parts.append(f"Current check-in streak: {streak} days")
    except Exception:
        pass

    return "\n".join(context_parts) if context_parts else "No additional context available."


def get_message_count_today(user):
    """Count how many coach messages the user has sent today."""
    from apps.accounts.models import CoachMessage
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return CoachMessage.objects.filter(
        session__user=user,
        role='user',
        created_at__gte=today_start
    ).count()


def get_total_free_messages(user):
    """Count total coach messages a user has ever sent (for free tier limit)."""
    from apps.accounts.models import CoachMessage
    return CoachMessage.objects.filter(
        session__user=user,
        role='user'
    ).count()


def can_send_message(user):
    """Check if user can send a coach message. Returns (allowed, reason)."""
    is_premium = hasattr(user, 'subscription') and user.subscription.is_premium()

    if is_premium:
        today_count = get_message_count_today(user)
        if today_count >= 20:
            return False, "You've reached your daily limit of 20 messages. Your limit resets at midnight."
        return True, None
    else:
        total = get_total_free_messages(user)
        if total >= 3:
            return False, "upgrade_required"
        return True, None


def get_conversation_history(session, limit=10):
    """Get the last N messages from a session for context."""
    messages = session.messages.order_by('-created_at')[:limit]
    return [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(messages)
    ]


def send_coach_message(user, session, user_message):
    """
    Send a message to the AI coach and get a response.
    Returns (response_text, error) tuple.
    """
    import anthropic

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not configured")
        return None, "AI Coach is temporarily unavailable. Please try again later."

    # Build context and history
    user_context = build_user_context(user)
    system_prompt = RECOVERY_COACH_SYSTEM_PROMPT.format(user_context=user_context)
    history = get_conversation_history(session, limit=10)

    # Add the new user message to history
    history.append({"role": "user", "content": user_message})

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            messages=history,
        )

        assistant_text = response.content[0].text
        total_tokens = response.usage.input_tokens + response.usage.output_tokens

        return assistant_text, None

    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limit hit")
        return None, "The coach is busy right now. Please try again in a moment."
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return None, "AI Coach is temporarily unavailable. Please try again later."
    except Exception as e:
        logger.error(f"Unexpected error in coach service: {e}")
        return None, "Something went wrong. Please try again."
```

**Step 2: Commit**

```bash
git add apps/accounts/coach_service.py
git commit -m "Add AI recovery coach service with Claude API integration"
```

---

### Task 5: Build the Coach Views

**Files:**
- Modify: `apps/accounts/views.py` (append new views)
- Modify: `apps/accounts/urls.py` (add routes)

**Step 1: Add coach views to views.py**

Append to end of `apps/accounts/views.py`:

```python
# --- AI Recovery Coach Views ---

@login_required
def recovery_coach(request):
    """Main recovery coach chat interface."""
    from apps.accounts.models import RecoveryCoachSession, CoachMessage
    from apps.accounts.coach_service import can_send_message, get_message_count_today, get_total_free_messages

    is_premium = hasattr(request.user, 'subscription') and request.user.subscription.is_premium()

    # Get or create active session
    session = RecoveryCoachSession.objects.filter(user=request.user, is_active=True).first()
    if not session:
        session = RecoveryCoachSession.objects.create(user=request.user, title="New Conversation")

    messages_list = session.messages.order_by('created_at')
    allowed, reason = can_send_message(request.user)

    context = {
        'session': session,
        'messages': messages_list,
        'can_send': allowed,
        'limit_reason': reason,
        'is_premium': is_premium,
        'messages_today': get_message_count_today(request.user) if is_premium else get_total_free_messages(request.user),
        'message_limit': 20 if is_premium else 3,
        'sessions': RecoveryCoachSession.objects.filter(user=request.user).order_by('-updated_at')[:10],
    }
    return render(request, 'accounts/recovery_coach.html', context)


@login_required
@require_POST
def coach_send_message(request):
    """AJAX endpoint: send a message to the coach and get a response."""
    import json
    from apps.accounts.models import RecoveryCoachSession, CoachMessage
    from apps.accounts.coach_service import can_send_message, send_coach_message, get_message_count_today, get_total_free_messages

    user_message = request.POST.get('message', '').strip()
    session_id = request.POST.get('session_id')

    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

    if len(user_message) > 2000:
        return JsonResponse({'error': 'Message is too long. Please keep it under 2000 characters.'}, status=400)

    # Check rate limits
    allowed, reason = can_send_message(request.user)
    if not allowed:
        return JsonResponse({'error': reason, 'upgrade_required': reason == 'upgrade_required'}, status=429)

    # Get session
    try:
        session = RecoveryCoachSession.objects.get(id=session_id, user=request.user)
    except RecoveryCoachSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found.'}, status=404)

    # Save user message
    CoachMessage.objects.create(session=session, role='user', content=user_message)

    # Auto-title the session from first message
    if not session.title or session.title == "New Conversation":
        session.title = user_message[:100]
        session.save(update_fields=['title', 'updated_at'])

    # Get AI response
    response_text, error = send_coach_message(request.user, session, user_message)

    if error:
        return JsonResponse({'error': error}, status=500)

    # Save assistant message
    CoachMessage.objects.create(session=session, role='assistant', content=response_text)
    session.save(update_fields=['updated_at'])

    is_premium = hasattr(request.user, 'subscription') and request.user.subscription.is_premium()

    return JsonResponse({
        'response': response_text,
        'messages_used': get_message_count_today(request.user) if is_premium else get_total_free_messages(request.user),
        'message_limit': 20 if is_premium else 3,
    })


@login_required
@require_POST
def coach_new_session(request):
    """Start a new coach conversation session."""
    from apps.accounts.models import RecoveryCoachSession

    # Deactivate current active sessions
    RecoveryCoachSession.objects.filter(user=request.user, is_active=True).update(is_active=False)

    # Create new session
    session = RecoveryCoachSession.objects.create(user=request.user, title="New Conversation")

    return redirect('accounts:recovery_coach')


@login_required
def coach_load_session(request, session_id):
    """Load a previous coach conversation session."""
    from apps.accounts.models import RecoveryCoachSession

    # Deactivate all sessions
    RecoveryCoachSession.objects.filter(user=request.user, is_active=True).update(is_active=False)

    # Activate selected session
    try:
        session = RecoveryCoachSession.objects.get(id=session_id, user=request.user)
        session.is_active = True
        session.save(update_fields=['is_active'])
    except RecoveryCoachSession.DoesNotExist:
        pass

    return redirect('accounts:recovery_coach')
```

**Step 2: Add URL routes to urls.py**

Add before the closing `]` in `apps/accounts/urls.py` (before line 179):

```python
    # AI Recovery Coach
    path('recovery-coach/', views.recovery_coach, name='recovery_coach'),
    path('recovery-coach/send/', views.coach_send_message, name='coach_send_message'),
    path('recovery-coach/new/', views.coach_new_session, name='coach_new_session'),
    path('recovery-coach/session/<int:session_id>/', views.coach_load_session, name='coach_load_session'),
```

**Step 3: Commit**

```bash
git add apps/accounts/views.py apps/accounts/urls.py
git commit -m "Add AI recovery coach views and URL routes"
```

---

### Task 6: Build the Coach Chat Template

**Files:**
- Create: `apps/accounts/templates/accounts/recovery_coach.html`

**Step 1: Create the chat template**

A clean chat interface with:
- Sidebar showing past sessions
- Main chat area with message bubbles
- Input box at bottom with character count
- Rate limit indicator
- Upgrade prompt for free users who hit limit
- Crisis resources banner
- Mobile responsive

The template should extend `base.html` and follow the existing design patterns (gradient headers, card-based layouts, dark mode support). Messages from the user should be right-aligned (blue), coach responses left-aligned (white/gray). Include a typing indicator during API calls.

Key elements:
- Session list sidebar (collapsible on mobile)
- Chat messages area (scrollable, auto-scroll to bottom)
- Message input form with AJAX submission (POST to `coach_send_message`)
- "Messages remaining" counter
- "New Conversation" button
- Upgrade CTA when free limit reached (links to `accounts:pricing`)
- Crisis resources disclaimer at top: "Pal is an AI companion, not a therapist. If you're in crisis, call 988."
- Loading state while waiting for AI response

**Step 2: Commit**

```bash
git add apps/accounts/templates/accounts/recovery_coach.html
git commit -m "Add AI recovery coach chat template"
```

---

### Task 7: Add Affiliate CTAs to Blog Posts

**Files:**
- Create: `apps/blog/templates/blog/_affiliate_cta.html`
- Modify: `apps/blog/templates/blog/post_detail.html` (insert before comments section, ~line 685)

**Step 1: Create the affiliate CTA partial**

A reusable template partial with:
- BetterHelp CTA: "Struggling? Talk to a licensed therapist." with affiliate link placeholder
- Styled as a soft, non-intrusive card that fits the blog design
- Includes affiliate disclosure text: "We may receive compensation from BetterHelp if you sign up through our link."
- Dark mode compatible
- Responsive

Note: Use a placeholder URL like `https://www.betterhelp.com/?utm_source=myrecoverypal` — the actual affiliate link will be added once the BetterHelp affiliate account is approved. Use a settings variable or template variable so it can be updated easily.

**Step 2: Include the CTA in post_detail.html**

Insert the include tag before the comments section (before line 685):

```html
{% include "blog/_affiliate_cta.html" %}
```

**Step 3: Commit**

```bash
git add apps/blog/templates/blog/_affiliate_cta.html apps/blog/templates/blog/post_detail.html
git commit -m "Add affiliate CTA partial to blog post detail pages"
```

---

### Task 8: Update Navigation — Add Coach, Remove Store, Add Donation

**Files:**
- Modify: `templates/base.html`

**Step 1: Replace Store link with Recovery Coach link in nav**

Find the Store link (~line 2231-2232):
```html
<li><a href="{% url 'store:product_list' %}"
        class="{% if 'store' in request.resolver_match.namespace %}active{% endif %}">Store</a></li>
```

Replace with:
```html
<li><a href="{% url 'accounts:recovery_coach' %}"
        class="{% if request.resolver_match.url_name == 'recovery_coach' %}active{% endif %}">AI Coach</a></li>
```

Also update the mobile menu if Store appears there.

**Step 2: Add donation link to footer**

In the footer section (~line 2638-2669), add a "Support Us" link in the About section:
```html
<li><a href="https://ko-fi.com/myrecoverypal" target="_blank" rel="noopener">Support Our Mission</a></li>
```

Note: The Ko-fi URL is a placeholder. Replace with actual Ko-fi page URL once created.

**Step 3: Update copyright year**

Find (~line 2667):
```html
<p>&copy; 2025 MyRecoveryPal. All rights reserved. | Recovery is possible.</p>
```

Change `2025` to `2026`.

**Step 4: Commit**

```bash
git add templates/base.html
git commit -m "Update nav: add AI Coach link, remove Store, add donation link, fix copyright year"
```

---

### Task 9: Update Decorators — Remove Messaging Limit, Simplify Tiers

**Files:**
- Modify: `apps/accounts/decorators.py`

**Step 1: Update the check_feature_limit decorator**

The existing decorator enforces limits including `max_messages_per_month: 10`. Update the free tier limits:
- Remove `max_messages_per_month` limit (messaging is now unlimited for all)
- Keep `max_groups: 5` for free users (was 2, increase to 5)
- Keep `max_private_groups: 0` for free users

The `is_premium()` check already covers both 'premium' and 'pro' tiers, so the Pro tier removal is just a pricing/UI change, not a code change.

**Step 2: Commit**

```bash
git add apps/accounts/decorators.py
git commit -m "Update feature limits: unlimited messaging for free tier, increase group limit to 5"
```

---

### Task 10: Update Pricing Page — Simplify to Two Tiers

**Files:**
- Modify: `apps/accounts/templates/accounts/pricing.html`

**Step 1: Update the pricing template**

Changes:
- Remove the Professional/Pro tier entirely (simplify to Free + Premium)
- Add "AI Recovery Coach" as the featured premium benefit (with sparkle/star icon)
- Update Free tier features to show: unlimited messaging, 5 groups, 3 AI coach trial messages
- Update Premium tier features to show: unlimited everything + 20 AI coach messages/day + premium badge
- Add "Try 3 Free Messages" CTA that links to the coach page
- Keep the existing Stripe checkout JavaScript as-is (it works)

**Step 2: Commit**

```bash
git add apps/accounts/templates/accounts/pricing.html
git commit -m "Simplify pricing to two tiers, add AI Coach as premium anchor"
```

---

### Task 11: Final Commit — Verify and Push

**Step 1: Run migrations check**

Run: `python manage.py showmigrations accounts`
Verify all migrations applied.

**Step 2: Run Django check**

Run: `python manage.py check`
Expected: System check identified no issues.

**Step 3: Test the dev server starts**

Run: `python manage.py runserver`
Verify no import errors or crashes.

**Step 4: Push all changes**

```bash
git push origin main
```

---

## Environment Setup Required (Manual — Not Code)

After deploying, the following must be done manually:

1. **Railway:** Add `ANTHROPIC_API_KEY` environment variable to both web and celery-worker services
2. **Stripe Dashboard:** Create a Premium product with monthly ($4.99) and yearly ($29.99) prices. Note the price IDs.
3. **Stripe Dashboard:** Configure the webhook endpoint URL if not already done
4. **Ko-fi:** Create a Ko-fi page at ko-fi.com and update the footer link
5. **BetterHelp:** Apply for the BetterHelp affiliate program and update the link in `_affiliate_cta.html`
6. **Amazon Associates:** Apply for Amazon affiliate program for book recommendations (future task)

import logging
from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

RECOVERY_COACH_SYSTEM_PROMPT = """You are a supportive AI recovery coach on MyRecoveryPal, a peer recovery community platform. Your name is Anchor.

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

## Professional Support Referral
When a conversation reveals needs beyond what an AI companion can provide, gently recommend professional help. This includes:
- Ongoing depression, anxiety, PTSD, or trauma processing
- Co-occurring mental health disorders
- Grief, relationship issues, or deep emotional pain that keeps surfacing
- Medication questions or concerns about prescribed treatment
- Patterns where the user seems stuck and needs deeper therapeutic work
- Eating disorders, self-harm urges (non-crisis), or compulsive behaviors

When referring, do it naturally within your response — not as a script. After validating their feelings and offering what support you can, mention that a licensed therapist can provide the deeper, ongoing care this deserves. Then share:

"If you'd like to connect with a licensed therapist who understands recovery, BetterHelp makes it easy to get matched online: https://www.betterhelp.com/?utm_source=myrecoverypal&utm_medium=coach&utm_campaign=anchor_referral — most sessions run $60-90/week with insurance."

Keep it warm, not pushy. You are not replacing yourself — you are adding a teammate. Frame it as "I'm here for daily support AND a therapist can go deeper" rather than "you need more help than I can give." Continue the conversation normally after the referral — don't end on it.

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
        context_parts.append(
            f"Sobriety date: {user.sobriety_date.strftime('%B %d, %Y')} ({days} days sober)"
        )

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
            date__gte=timezone.now().date() - timedelta(days=7),
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
    """Count routine (non-exempt) coach messages the user has sent today."""
    from apps.accounts.models import CoachMessage

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return CoachMessage.objects.filter(
        session__user=user,
        role='user',
        created_at__gte=today_start,
    ).exclude(session__trigger__in=('checkin_support', 'sos')).count()


def can_send_message(user, session=None):
    """Check if user can send a coach message. Returns (allowed, reason).

    Crisis-triggered (checkin_support, sos) sessions are never limited.
    Free users get 3 routine messages/day; premium gets 20/day.
    """
    if session is not None and session.trigger in ('checkin_support', 'sos'):
        return True, None

    is_premium = hasattr(user, 'subscription') and user.subscription.is_premium()
    today_count = get_message_count_today(user)
    if is_premium:
        if today_count >= 20:
            return False, "You've reached your daily limit of 20 messages. Your limit resets at midnight."
        return True, None
    if today_count >= 3:
        return False, "upgrade_required"
    return True, None


def get_conversation_history(session, limit=10):
    """Get the last N messages from a session for context."""
    messages = session.messages.order_by('-created_at')[:limit]
    return [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(messages)
    ]


def get_previous_session_context(user, current_session, max_messages=6):
    """Premium continuity: a short transcript excerpt from the user's most
    recent OTHER session, so Anchor can pick up where they left off.
    Returns a string for the system prompt, or '' if there's no prior session.
    """
    from apps.accounts.models import RecoveryCoachSession

    prev = (RecoveryCoachSession.objects
            .filter(user=user)
            .exclude(pk=current_session.pk)
            .order_by('-updated_at')
            .first())
    if not prev:
        return ''
    messages = list(prev.messages.order_by('-created_at')[:max_messages])
    if not messages:
        return ''
    lines = []
    for msg in reversed(messages):
        speaker = 'User' if msg.role == 'user' else 'You (Anchor)'
        lines.append(f'{speaker}: {msg.content[:300]}')
    when = prev.updated_at.strftime('%B %d')
    return (
        f"\n\nCONTINUITY — excerpt from your previous conversation with this "
        f"user (from {when}). Use it to remember what they were working "
        f"through, but don't recite it back verbatim:\n" + "\n".join(lines)
    )


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

    # Build context and history. Premium gets real memory: a 4x deeper
    # history window plus continuity context from their previous session.
    is_premium = hasattr(user, 'subscription') and user.subscription.is_premium()
    user_context = build_user_context(user)
    system_prompt = RECOVERY_COACH_SYSTEM_PROMPT.format(user_context=user_context)

    history_limit = 40 if is_premium else 10
    history = get_conversation_history(session, limit=history_limit)

    if is_premium and len(history) < 2:
        # Fresh session: carry over what they were working through last time
        system_prompt += get_previous_session_context(user, session)

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


def generate_checkin_opener(user, checkin):
    """Anchor's proactive opening message for a check-in-triggered session.

    Returns assistant text; falls back to a static warm message on any error.
    """
    import anthropic

    fallback = ("I saw your check-in — sounds like today's been heavy. "
                "I'm here. What's going on right now?")
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        return fallback
    try:
        user_context = build_user_context(user)
        system_prompt = RECOVERY_COACH_SYSTEM_PROMPT.format(user_context=user_context)
        challenge = (checkin.challenge or '').strip()
        seed = (
            f"The user just logged a daily check-in: mood "
            f"'{checkin.get_mood_display()}', craving level "
            f"'{checkin.get_craving_level_display()}'."
            + (f" They wrote their challenge today is: \"{challenge}\"." if challenge else "")
            + " Open the conversation: gently acknowledge how they're doing right "
              "now and invite them to talk. 2-3 sentences, warm, no lists."
        )
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": seed}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"generate_checkin_opener failed: {e}")
        return fallback

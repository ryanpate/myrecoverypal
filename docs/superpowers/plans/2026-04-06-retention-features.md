# Retention Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three retention features — daily recovery thoughts in feed, daily pledge in check-in, shareable milestone images — to improve daily return rate at 154 users.

**Architecture:** New `DailyRecoveryThought` model + Celery task for seeded feed content. `DailyCheckIn` model extended with pledge fields, check-in template updated with pledge-first step. New Pillow-based image generation endpoint + management command for gradient backgrounds. All features are free (no premium gating).

**Tech Stack:** Django 5.0, Celery, Pillow, Capacitor Share plugin (iOS), Web Share API (web)

**Spec:** `docs/superpowers/specs/2026-04-06-retention-features-design.md`

---

## File Map

**New files:**
- `apps/accounts/management/commands/seed_recovery_quotes.py` — seeds 90+ quotes
- `apps/accounts/management/commands/generate_milestone_backgrounds.py` — creates gradient PNGs
- `apps/accounts/templates/accounts/partials/_daily_thought.html` — quote card partial
- `apps/accounts/milestone_image.py` — Pillow image generation logic
- `static/fonts/Inter-Bold.ttf` — bundled font for image rendering
- `static/images/milestones/` — generated gradient backgrounds (6 files: 3 gradients x 2 formats)

**Modified files:**
- `apps/accounts/models.py` — add `DailyRecoveryThought` model + `pledge_taken`/`pledge_time` on `DailyCheckIn`
- `apps/accounts/migrations/0025_*.py` — migration
- `apps/accounts/views.py` — update `daily_checkin_view`, `social_feed_view`, add `milestone_image_view`
- `apps/accounts/urls.py` — add milestone-image URL
- `apps/accounts/tasks.py` — add `publish_daily_thought` task, update check-in reminder copy
- `apps/accounts/templates/accounts/social_feed.html` — include daily thought + share button on milestone modal
- `apps/accounts/templates/accounts/daily_checkin.html` — add pledge step
- `apps/accounts/templates/accounts/progress.html` — add "Share My Progress" button
- `recovery_hub/settings.py` — add `publish_daily_thought` to Celery Beat schedule

---

### Task 1: DailyRecoveryThought Model + Migration

**Files:**
- Modify: `apps/accounts/models.py` (after `DailyCheckIn` class, ~line 660)
- Modify: `apps/accounts/models.py` (add fields to `DailyCheckIn`, ~line 637)
- Create: `apps/accounts/migrations/0025_daily_thought_and_pledge.py`

- [ ] **Step 1: Add DailyRecoveryThought model to models.py**

After the `DailyCheckIn` class (around line 660), add:

```python
class DailyRecoveryThought(models.Model):
    """Daily recovery quotes displayed at the top of the social feed."""
    quote = models.TextField()
    author_attribution = models.CharField(max_length=200, blank=True)
    reflection_prompt = models.CharField(max_length=300, blank=True)
    date = models.DateField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.date}: {self.quote[:50]}..."
```

- [ ] **Step 2: Add pledge fields to DailyCheckIn model**

In the `DailyCheckIn` class (around line 637, after `is_shared`), add:

```python
    # Daily pledge
    pledge_taken = models.BooleanField(default=False)
    pledge_time = models.DateTimeField(null=True, blank=True)
```

- [ ] **Step 3: Generate and verify migration**

Run:
```bash
python3 manage.py makemigrations accounts --name daily_thought_and_pledge
python3 manage.py migrate accounts
python3 manage.py check
```

Expected: Migration creates `DailyRecoveryThought` table + adds 2 fields to `DailyCheckIn`. Check passes with 0 issues.

- [ ] **Step 4: Commit**

```bash
git add apps/accounts/models.py apps/accounts/migrations/0025_*
git commit -m "feat: add DailyRecoveryThought model + pledge fields on DailyCheckIn"
```

---

### Task 2: Seed Recovery Quotes (Management Command)

**Files:**
- Create: `apps/accounts/management/commands/seed_recovery_quotes.py`

- [ ] **Step 1: Create the management command**

```python
"""Seed 90+ recovery quotes for daily feed content."""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from apps.accounts.models import DailyRecoveryThought


QUOTES = [
    {
        'quote': 'Recovery is not a race. You don\'t have to feel guilty if it takes you longer than you thought it would.',
        'author': '',
        'prompt': 'What part of your recovery have you been rushing?',
    },
    {
        'quote': 'The only person you are destined to become is the person you decide to be.',
        'author': 'Ralph Waldo Emerson',
        'prompt': 'Who are you deciding to be today?',
    },
    {
        'quote': 'One day at a time. One step at a time. One moment at a time. That is all it takes.',
        'author': '',
        'prompt': 'What is the one thing you can focus on right now?',
    },
    {
        'quote': 'Strength does not come from physical capacity. It comes from an indomitable will.',
        'author': 'Mahatma Gandhi',
        'prompt': 'When has your willpower surprised you?',
    },
    {
        'quote': 'You are not your addiction. You are a person who has been through something very difficult.',
        'author': '',
        'prompt': 'How would you describe yourself beyond your addiction?',
    },
    {
        'quote': 'Fall seven times, stand up eight.',
        'author': 'Japanese Proverb',
        'prompt': 'What has getting back up taught you?',
    },
    {
        'quote': 'The wound is the place where the Light enters you.',
        'author': 'Rumi',
        'prompt': 'What light has your struggle let in?',
    },
    {
        'quote': 'You don\'t have to see the whole staircase, just take the first step.',
        'author': 'Martin Luther King Jr.',
        'prompt': 'What is your first step today?',
    },
    {
        'quote': 'Courage is not the absence of fear, but rather the judgment that something else is more important than fear.',
        'author': 'Ambrose Redmoon',
        'prompt': 'What matters more to you than your fear?',
    },
    {
        'quote': 'Sobriety is a journey, not a destination. Be patient with yourself.',
        'author': '',
        'prompt': 'How have you been kind to yourself this week?',
    },
    {
        'quote': 'It is during our darkest moments that we must focus to see the light.',
        'author': 'Aristotle',
        'prompt': 'What light can you see right now, even if it\'s small?',
    },
    {
        'quote': 'What lies behind us and what lies before us are tiny matters compared to what lies within us.',
        'author': 'Ralph Waldo Emerson',
        'prompt': 'What inner strength have you discovered in recovery?',
    },
    {
        'quote': 'Every morning we are born again. What we do today is what matters most.',
        'author': 'Buddha',
        'prompt': 'What will you do with this fresh start today?',
    },
    {
        'quote': 'The best time to plant a tree was twenty years ago. The second best time is now.',
        'author': 'Chinese Proverb',
        'prompt': 'What seed are you planting in your recovery today?',
    },
    {
        'quote': 'You were never created to live depressed, defeated, guilty, condemned, ashamed, or unworthy.',
        'author': '',
        'prompt': 'Which of these feelings are you ready to let go of?',
    },
    {
        'quote': 'Sometimes the smallest step in the right direction ends up being the biggest step of your life.',
        'author': '',
        'prompt': 'What small step did you take recently that felt big?',
    },
    {
        'quote': 'Gratitude turns what we have into enough.',
        'author': '',
        'prompt': 'Name three things you\'re grateful for right now.',
    },
    {
        'quote': 'You are allowed to be both a masterpiece and a work in progress simultaneously.',
        'author': 'Sophia Bush',
        'prompt': 'What part of you is a masterpiece? What part is still growing?',
    },
    {
        'quote': 'Healing is not linear. Some days will be harder than others, and that\'s okay.',
        'author': '',
        'prompt': 'How do you handle the harder days?',
    },
    {
        'quote': 'The only way out is through.',
        'author': 'Robert Frost',
        'prompt': 'What are you working through right now?',
    },
    {
        'quote': 'Don\'t let yesterday take up too much of today.',
        'author': 'Will Rogers',
        'prompt': 'What from yesterday can you release today?',
    },
    {
        'quote': 'You are braver than you believe, stronger than you seem, and smarter than you think.',
        'author': 'A.A. Milne',
        'prompt': 'When did you last surprise yourself with your strength?',
    },
    {
        'quote': 'Rock bottom became the solid foundation on which I rebuilt my life.',
        'author': 'J.K. Rowling',
        'prompt': 'How has your lowest point become your foundation?',
    },
    {
        'quote': 'Progress, not perfection, is what we should be asking of ourselves.',
        'author': 'Julia Cameron',
        'prompt': 'Where have you made progress you haven\'t acknowledged yet?',
    },
    {
        'quote': 'The greatest glory in living lies not in never falling, but in rising every time we fall.',
        'author': 'Nelson Mandela',
        'prompt': 'What did you learn from your last fall?',
    },
    {
        'quote': 'Believe you can and you\'re halfway there.',
        'author': 'Theodore Roosevelt',
        'prompt': 'What do you believe is possible for your recovery?',
    },
    {
        'quote': 'Your present circumstances don\'t determine where you can go; they merely determine where you start.',
        'author': 'Nido Qubein',
        'prompt': 'Where are you starting from today?',
    },
    {
        'quote': 'We cannot solve our problems with the same thinking we used when we created them.',
        'author': 'Albert Einstein',
        'prompt': 'What new perspective has recovery given you?',
    },
    {
        'quote': 'Be gentle with yourself. You\'re doing the best you can.',
        'author': '',
        'prompt': 'How can you show yourself more compassion today?',
    },
    {
        'quote': 'The secret of change is to focus all of your energy not on fighting the old, but on building the new.',
        'author': 'Socrates',
        'prompt': 'What new thing are you building in your life?',
    },
    # Continue pattern for 90+ quotes total. 30 shown here as starter set.
    # Run the command with --extend flag later to add more.
    {
        'quote': 'In the middle of difficulty lies opportunity.',
        'author': 'Albert Einstein',
        'prompt': 'What opportunity is hidden in your current challenge?',
    },
    {
        'quote': 'The first step toward getting somewhere is to decide you\'re not going to stay where you are.',
        'author': 'J.P. Morgan',
        'prompt': 'What are you moving away from? What are you moving toward?',
    },
    {
        'quote': 'Nothing changes if nothing changes.',
        'author': '',
        'prompt': 'What one thing will you change today?',
    },
    {
        'quote': 'Surrender is not about giving up. It\'s about letting go of what no longer serves you.',
        'author': '',
        'prompt': 'What are you holding onto that you could release?',
    },
    {
        'quote': 'You don\'t have to control your thoughts. You just have to stop letting them control you.',
        'author': 'Dan Millman',
        'prompt': 'Which thought has been controlling you lately?',
    },
    {
        'quote': 'The only impossible journey is the one you never begin.',
        'author': 'Tony Robbins',
        'prompt': 'What journey did you begin when you chose recovery?',
    },
    {
        'quote': 'Hardships often prepare ordinary people for an extraordinary destiny.',
        'author': 'C.S. Lewis',
        'prompt': 'How is your hardship preparing you for something greater?',
    },
    {
        'quote': 'What we achieve inwardly will change outer reality.',
        'author': 'Plutarch',
        'prompt': 'What inner change have you noticed since starting recovery?',
    },
    {
        'quote': 'Act as if what you do makes a difference. It does.',
        'author': 'William James',
        'prompt': 'How does your sobriety make a difference to someone you love?',
    },
    {
        'quote': 'You gain strength, courage, and confidence by every experience in which you really stop to look fear in the face.',
        'author': 'Eleanor Roosevelt',
        'prompt': 'What fear have you faced in recovery?',
    },
    {
        'quote': 'It always seems impossible until it\'s done.',
        'author': 'Nelson Mandela',
        'prompt': 'What felt impossible when you started that now feels normal?',
    },
    {
        'quote': 'When you can\'t control what\'s happening, challenge yourself to control the way you respond.',
        'author': '',
        'prompt': 'How did you choose to respond to a challenge this week?',
    },
    {
        'quote': 'This too shall pass.',
        'author': 'Persian Proverb',
        'prompt': 'What difficult moment are you waiting to pass?',
    },
    {
        'quote': 'The most common way people give up their power is by thinking they don\'t have any.',
        'author': 'Alice Walker',
        'prompt': 'What power do you have that you sometimes forget about?',
    },
    {
        'quote': 'Do not judge me by my successes, judge me by how many times I fell down and got back up again.',
        'author': 'Nelson Mandela',
        'prompt': 'How many times have you gotten back up?',
    },
    {
        'quote': 'The only way to do great work is to love what you do.',
        'author': 'Steve Jobs',
        'prompt': 'What part of your recovery work do you find meaningful?',
    },
    {
        'quote': 'Out of suffering have emerged the strongest souls.',
        'author': 'Kahlil Gibran',
        'prompt': 'How has your suffering made you stronger?',
    },
    {
        'quote': 'You are not defined by your past. You are prepared by your past.',
        'author': '',
        'prompt': 'What did your past prepare you for?',
    },
    {
        'quote': 'Hope is being able to see that there is light despite all of the darkness.',
        'author': 'Desmond Tutu',
        'prompt': 'Where do you see hope today?',
    },
    {
        'quote': 'Start where you are. Use what you have. Do what you can.',
        'author': 'Arthur Ashe',
        'prompt': 'What can you do with what you have right now?',
    },
    {
        'quote': 'Difficult roads often lead to beautiful destinations.',
        'author': '',
        'prompt': 'What beautiful destination are you heading toward?',
    },
    {
        'quote': 'The greatest weapon against stress is our ability to choose one thought over another.',
        'author': 'William James',
        'prompt': 'What thought will you choose today?',
    },
    {
        'quote': 'Everything you\'ve ever wanted is on the other side of fear.',
        'author': 'George Addair',
        'prompt': 'What\'s on the other side of your fear?',
    },
    {
        'quote': 'Rivers know this: there is no hurry. We shall get there some day.',
        'author': 'A.A. Milne',
        'prompt': 'Where are you trying to rush that could use patience?',
    },
    {
        'quote': 'Be the change you wish to see in the world.',
        'author': 'Mahatma Gandhi',
        'prompt': 'What change are you embodying through your recovery?',
    },
    {
        'quote': 'A smooth sea never made a skilled sailor.',
        'author': 'Franklin D. Roosevelt',
        'prompt': 'What rough waters have made you a better person?',
    },
    {
        'quote': 'The struggle you\'re in today is developing the strength you need for tomorrow.',
        'author': '',
        'prompt': 'What strength is today\'s struggle building?',
    },
    {
        'quote': 'No matter how slow you go, you\'re still lapping everyone on the couch.',
        'author': '',
        'prompt': 'What progress have you made that you haven\'t given yourself credit for?',
    },
    {
        'quote': 'Recovery is something that you have to work on every single day, and it\'s something that doesn\'t get a day off.',
        'author': 'Demi Lovato',
        'prompt': 'What does your daily recovery practice look like?',
    },
    {
        'quote': 'The pain you feel today is the strength you feel tomorrow.',
        'author': '',
        'prompt': 'What pain from your past has become a source of strength?',
    },
    {
        'quote': 'Don\'t count the days. Make the days count.',
        'author': 'Muhammad Ali',
        'prompt': 'How will you make today count?',
    },
    {
        'quote': 'Stars can\'t shine without darkness.',
        'author': '',
        'prompt': 'What light are you shining from your experience?',
    },
    {
        'quote': 'You are stronger than you think. You have gotten through every bad day in your life, and you are undefeated.',
        'author': '',
        'prompt': 'How many bad days have you survived? You\'re still here.',
    },
    {
        'quote': 'Happiness is not something ready-made. It comes from your own actions.',
        'author': 'Dalai Lama',
        'prompt': 'What action can you take today that will bring you closer to happiness?',
    },
    {
        'quote': 'Inhale courage, exhale fear.',
        'author': '',
        'prompt': 'Take three deep breaths right now. How do you feel?',
    },
    {
        'quote': 'Vulnerability is the birthplace of connection.',
        'author': 'Brene Brown',
        'prompt': 'When did being vulnerable lead to a meaningful connection?',
    },
    {
        'quote': 'Let go of who you think you\'re supposed to be and embrace who you are.',
        'author': 'Brene Brown',
        'prompt': 'Who are you when you stop performing?',
    },
    {
        'quote': 'Addiction begins with the hope that something "out there" can instantly fill the emptiness inside.',
        'author': 'Jean Kilbourne',
        'prompt': 'What are you filling the emptiness with now?',
    },
    {
        'quote': 'The opposite of addiction is connection.',
        'author': 'Johann Hari',
        'prompt': 'Who have you connected with in recovery?',
    },
    {
        'quote': 'There is no shame in beginning again, for you get a chance to build bigger and better than before.',
        'author': '',
        'prompt': 'What are you building this time around?',
    },
    {
        'quote': 'Your calm mind is the ultimate weapon against your challenges.',
        'author': 'Bryant McGill',
        'prompt': 'How do you calm your mind when challenges arise?',
    },
    {
        'quote': 'If you\'re going through hell, keep going.',
        'author': 'Winston Churchill',
        'prompt': 'What keeps you moving forward on the hardest days?',
    },
    {
        'quote': 'People often say that motivation doesn\'t last. Neither does bathing — that\'s why we recommend it daily.',
        'author': 'Zig Ziglar',
        'prompt': 'What daily practice keeps you motivated?',
    },
    {
        'quote': 'The person who says it cannot be done should not interrupt the person doing it.',
        'author': 'Chinese Proverb',
        'prompt': 'Who doubted you that you\'ve already proven wrong?',
    },
    {
        'quote': 'Life doesn\'t get easier or more forgiving. We get stronger and more resilient.',
        'author': 'Steve Maraboli',
        'prompt': 'How are you more resilient now than when you started?',
    },
    {
        'quote': 'To be yourself in a world that is constantly trying to make you something else is the greatest accomplishment.',
        'author': 'Ralph Waldo Emerson',
        'prompt': 'What does being your authentic self look like in recovery?',
    },
    {
        'quote': 'The only limit to our realization of tomorrow is our doubts of today.',
        'author': 'Franklin D. Roosevelt',
        'prompt': 'What doubt can you release today?',
    },
    {
        'quote': 'Character cannot be developed in ease and quiet. Only through experience of trial and suffering can the soul be strengthened.',
        'author': 'Helen Keller',
        'prompt': 'How has your character grown through this trial?',
    },
    {
        'quote': 'When one door closes, another opens. But we often look so long at the closed door that we do not see the one which has opened.',
        'author': 'Alexander Graham Bell',
        'prompt': 'What open door have you been ignoring?',
    },
    {
        'quote': 'Asking for help is a sign of strength, not weakness.',
        'author': '',
        'prompt': 'When was the last time you asked for help? How did it feel?',
    },
    {
        'quote': 'You are not a drop in the ocean. You are the entire ocean in a drop.',
        'author': 'Rumi',
        'prompt': 'What vast potential lives inside you?',
    },
    {
        'quote': 'The day you plant the seed is not the day you eat the fruit. Be patient.',
        'author': '',
        'prompt': 'What seed have you planted that hasn\'t bloomed yet?',
    },
    {
        'quote': 'Don\'t let what you cannot do interfere with what you can do.',
        'author': 'John Wooden',
        'prompt': 'What CAN you do today?',
    },
    {
        'quote': 'Almost everything will work again if you unplug it for a few minutes, including you.',
        'author': 'Anne Lamott',
        'prompt': 'When was the last time you gave yourself permission to rest?',
    },
    {
        'quote': 'Courage doesn\'t always roar. Sometimes courage is the quiet voice at the end of the day saying, "I will try again tomorrow."',
        'author': 'Mary Anne Radmacher',
        'prompt': 'What quiet courage have you shown recently?',
    },
    {
        'quote': 'The most powerful relationship you will ever have is the relationship with yourself.',
        'author': 'Steve Maraboli',
        'prompt': 'How is your relationship with yourself improving?',
    },
    {
        'quote': 'Where there is no struggle, there is no strength.',
        'author': 'Oprah Winfrey',
        'prompt': 'What strength have you gained from your struggle?',
    },
    {
        'quote': 'Sometimes you have to get knocked down lower than you\'ve ever been to stand up taller than you ever were.',
        'author': '',
        'prompt': 'How have you grown taller from being knocked down?',
    },
    {
        'quote': 'The beginning is always today.',
        'author': 'Mary Shelley',
        'prompt': 'What begins for you today?',
    },
]


class Command(BaseCommand):
    help = 'Seed daily recovery quotes starting from today'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date (YYYY-MM-DD), defaults to today',
        )

    def handle(self, *args, **options):
        from django.utils import timezone

        start = options.get('start_date')
        if start:
            from datetime import datetime
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date()

        created = 0
        skipped = 0
        for i, q in enumerate(QUOTES):
            target_date = start_date + timedelta(days=i)
            _, was_created = DailyRecoveryThought.objects.get_or_create(
                date=target_date,
                defaults={
                    'quote': q['quote'],
                    'author_attribution': q.get('author', ''),
                    'reflection_prompt': q.get('prompt', ''),
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {created} quotes ({skipped} already existed). '
            f'Covers {start_date} through {start_date + timedelta(days=len(QUOTES) - 1)}.'
        ))
```

- [ ] **Step 2: Run the seeding command**

```bash
python3 manage.py seed_recovery_quotes
```

Expected: "Seeded 90 quotes (0 already existed). Covers 2026-04-06 through 2026-07-04."

- [ ] **Step 3: Commit**

```bash
git add apps/accounts/management/commands/seed_recovery_quotes.py
git commit -m "feat: add seed_recovery_quotes command with 90 quotes"
```

---

### Task 3: Daily Thought Celery Task + Feed Integration

**Files:**
- Modify: `apps/accounts/tasks.py` — add `publish_daily_thought` task
- Modify: `recovery_hub/settings.py` — add to Celery Beat schedule
- Modify: `apps/accounts/views.py` — inject `daily_thought` into feed views
- Create: `apps/accounts/templates/accounts/partials/_daily_thought.html`
- Modify: `apps/accounts/templates/accounts/social_feed.html` — include partial

- [ ] **Step 1: Add Celery task to tasks.py**

At the end of `apps/accounts/tasks.py`, add:

```python
@shared_task(bind=True, max_retries=3)
def publish_daily_thought(self):
    """
    Ensure today has a DailyRecoveryThought.
    If no pre-seeded quote exists for today, recycle one from 30+ days ago.
    Runs daily at 6:00 AM UTC.
    """
    from .models import DailyRecoveryThought

    today = timezone.now().date()

    # Already have one for today
    if DailyRecoveryThought.objects.filter(date=today).exists():
        logger.info(f"Daily thought already exists for {today}")
        return {'status': 'already_exists'}

    # Recycle a quote from 30+ days ago
    thirty_days_ago = today - timedelta(days=30)
    old_quote = DailyRecoveryThought.objects.filter(
        date__lte=thirty_days_ago
    ).order_by('?').first()

    if old_quote:
        DailyRecoveryThought.objects.create(
            quote=old_quote.quote,
            author_attribution=old_quote.author_attribution,
            reflection_prompt=old_quote.reflection_prompt,
            date=today,
        )
        logger.info(f"Recycled daily thought for {today}")
        return {'status': 'recycled'}

    logger.warning(f"No quotes available to recycle for {today}")
    return {'status': 'no_quotes'}
```

- [ ] **Step 2: Add to Celery Beat schedule in settings.py**

In `CELERY_BEAT_SCHEDULE` (around line 748), add before the closing `}`:

```python
    # Daily recovery thought — ensures a quote exists for today's feed
    'publish-daily-thought': {
        'task': 'apps.accounts.tasks.publish_daily_thought',
        'schedule': crontab(hour=6, minute=0),  # Daily at 6 AM UTC
    },
```

- [ ] **Step 3: Inject daily_thought into social_feed_view**

In `apps/accounts/views.py`, inside `social_feed_view` (around line 3987, after the `context = {` block is built), add:

```python
        # Daily recovery thought for feed
        from apps.accounts.models import DailyRecoveryThought
        today = timezone.now().date()
        context['daily_thought'] = DailyRecoveryThought.objects.filter(date=today).first()
```

Also add the same query inside `hybrid_landing_view` context (around line 4140, inside the authenticated block):

```python
            # Daily recovery thought
            from apps.accounts.models import DailyRecoveryThought
            context['daily_thought'] = DailyRecoveryThought.objects.filter(
                date=timezone.now().date()
            ).first()
```

- [ ] **Step 4: Create the daily thought template partial**

Create `apps/accounts/templates/accounts/partials/_daily_thought.html`:

```html
{% if daily_thought %}
<div style="background: linear-gradient(135deg, var(--primary-dark), var(--primary-light)); border-radius: 16px; padding: 2rem; margin-bottom: 1.5rem; color: white; text-align: center;">
    <div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 2px; opacity: 0.8; margin-bottom: 1rem;">
        <i class="fas fa-sun" aria-hidden="true"></i> Daily Recovery Thought
    </div>
    <blockquote style="font-size: 1.25rem; font-style: italic; line-height: 1.6; margin: 0 0 1rem 0; padding: 0;">
        "{{ daily_thought.quote }}"
    </blockquote>
    {% if daily_thought.author_attribution %}
    <div style="font-size: 0.9rem; opacity: 0.85; margin-bottom: 1rem;">
        &mdash; {{ daily_thought.author_attribution }}
    </div>
    {% endif %}
    {% if daily_thought.reflection_prompt %}
    <div style="font-size: 0.95rem; opacity: 0.9; background: rgba(255,255,255,0.15); border-radius: 10px; padding: 0.75rem 1rem; display: inline-block;">
        <i class="fas fa-comment-dots" aria-hidden="true"></i> {{ daily_thought.reflection_prompt }}
    </div>
    {% endif %}
</div>
{% endif %}
```

- [ ] **Step 5: Include partial in social_feed.html**

Find the post loop in `social_feed.html` (the `{% for post in posts %}` block). Just BEFORE that loop, add:

```html
{% include 'accounts/partials/_daily_thought.html' %}
```

Do the same in `hybrid_landing.html` if it has a similar post loop.

- [ ] **Step 6: Verify locally**

```bash
python3 manage.py check
python3 manage.py runserver
```

Visit `/accounts/social-feed/` — should see the daily quote card at the top of the feed if today's date has a seeded quote.

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/tasks.py recovery_hub/settings.py apps/accounts/views.py apps/accounts/templates/
git commit -m "feat: daily recovery thought cards in social feed"
```

---

### Task 4: Daily Pledge in Check-in Flow

**Files:**
- Modify: `apps/accounts/views.py` — update `daily_checkin_view` to handle pledge
- Modify: `apps/accounts/templates/accounts/daily_checkin.html` — add pledge step UI
- Modify: `apps/accounts/tasks.py` — update check-in reminder copy

- [ ] **Step 1: Update daily_checkin_view to save pledge**

In `apps/accounts/views.py`, inside `daily_checkin_view` (around line 805), after `is_shared = request.POST.get('is_shared') == 'on'`, add:

```python
        pledge_taken = request.POST.get('pledge_taken') == 'on'
```

Then in the `DailyCheckIn.objects.create()` call (around line 812), add the pledge fields:

```python
            checkin = DailyCheckIn.objects.create(
                user=request.user,
                date=today,
                mood=int(mood),
                craving_level=int(craving_level),
                energy_level=int(energy_level),
                gratitude=gratitude,
                challenge=challenge,
                goal=goal,
                is_shared=is_shared,
                pledge_taken=pledge_taken,
                pledge_time=timezone.now() if pledge_taken else None,
            )
```

After the check-in is created (around line 837, after the ActivityFeed creation), if the pledge was taken, create an additional activity:

```python
            if pledge_taken:
                ActivityFeed.objects.create(
                    user=request.user,
                    activity_type='check_in_posted',
                    title=f"{request.user.first_name or request.user.username} took today's pledge",
                    description="I pledge to stay sober today",
                    content_object=checkin,
                )
```

- [ ] **Step 2: Add pledge step to daily_checkin.html**

At the top of the check-in form (before the mood selection), add the pledge card. Read the current template to find the exact insertion point — look for the form tag or the first form field. Add:

```html
<!-- Daily Pledge Step -->
<div class="pledge-card" style="background: linear-gradient(135deg, #52b788, #40916c); border-radius: 16px; padding: 2rem; margin-bottom: 2rem; color: white; text-align: center;">
    <div style="font-size: 1.5rem; margin-bottom: 0.5rem;"><i class="fas fa-hand-holding-heart" aria-hidden="true"></i></div>
    <h3 style="color: white; font-size: 1.4rem; margin-bottom: 0.75rem;">I pledge to stay sober today</h3>
    <p style="opacity: 0.9; margin-bottom: 1.25rem; font-size: 0.95rem;">One day at a time. Take your daily pledge to start your check-in.</p>
    <label style="display: inline-flex; align-items: center; gap: 0.75rem; cursor: pointer; background: rgba(255,255,255,0.2); padding: 0.75rem 1.5rem; border-radius: 50px; font-weight: 600; font-size: 1.1rem;">
        <input type="checkbox" name="pledge_taken" id="pledgeCheckbox" style="width: 20px; height: 20px; accent-color: white;" checked>
        Take My Pledge
    </label>
</div>
```

- [ ] **Step 3: Update check-in reminder copy in tasks.py**

In `send_checkin_reminders` task, find the subject line (search for "Time for your daily check-in" or similar). Update to:

```python
subject = f"Take your daily pledge and check in, {user.first_name or user.username}"
```

- [ ] **Step 4: Verify locally**

```bash
python3 manage.py check
python3 manage.py runserver
```

Visit `/accounts/daily-checkin/` — should see the pledge card at the top of the check-in form. Submit a check-in with pledge checked. Verify the ActivityFeed entry is created.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/views.py apps/accounts/templates/accounts/daily_checkin.html apps/accounts/tasks.py
git commit -m "feat: daily pledge integrated into check-in flow"
```

---

### Task 5: Generate Milestone Backgrounds + Bundle Font

**Files:**
- Create: `apps/accounts/management/commands/generate_milestone_backgrounds.py`
- Create: `static/fonts/Inter-Bold.ttf` (download)
- Create: `static/images/milestones/` (generated PNGs)

- [ ] **Step 1: Download Inter Bold font**

```bash
curl -sL "https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip" -o /tmp/inter.zip
unzip -q /tmp/inter.zip -d /tmp/inter
cp /tmp/inter/Inter-4.0/extras/ttf/InterDisplay-Bold.ttf static/fonts/Inter-Bold.ttf
rm -rf /tmp/inter /tmp/inter.zip
ls -lh static/fonts/Inter-Bold.ttf
```

Expected: File exists, ~200-300KB.

- [ ] **Step 2: Create background generator management command**

```python
"""Generate gradient background images for milestone sharing."""
import os
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw


GRADIENTS = {
    'early': {'top': (30, 77, 139), 'bottom': (77, 184, 232)},    # blue-to-cyan
    'mid': {'top': (64, 145, 108), 'bottom': (82, 183, 136)},     # green-to-teal
    'long': {'top': (102, 51, 153), 'bottom': (118, 75, 162)},    # purple-to-pink
}

FORMATS = {
    'story': (1080, 1920),
    'square': (1080, 1080),
}


class Command(BaseCommand):
    help = 'Generate gradient background PNGs for milestone images'

    def handle(self, *args, **options):
        output_dir = os.path.join('static', 'images', 'milestones')
        os.makedirs(output_dir, exist_ok=True)

        for name, colors in GRADIENTS.items():
            for fmt, (w, h) in FORMATS.items():
                img = Image.new('RGB', (w, h))
                draw = ImageDraw.Draw(img)

                top = colors['top']
                bottom = colors['bottom']

                for y in range(h):
                    ratio = y / h
                    r = int(top[0] + (bottom[0] - top[0]) * ratio)
                    g = int(top[1] + (bottom[1] - top[1]) * ratio)
                    b = int(top[2] + (bottom[2] - top[2]) * ratio)
                    draw.line([(0, y), (w, y)], fill=(r, g, b))

                filename = f'bg-{name}-{fmt}.png'
                filepath = os.path.join(output_dir, filename)
                img.save(filepath, 'PNG', optimize=True)
                self.stdout.write(f'  Created {filepath} ({w}x{h})')

        self.stdout.write(self.style.SUCCESS(f'Generated {len(GRADIENTS) * len(FORMATS)} backgrounds'))
```

- [ ] **Step 3: Run the generator**

```bash
python3 manage.py generate_milestone_backgrounds
```

Expected: Creates 6 files in `static/images/milestones/`.

- [ ] **Step 4: Commit**

```bash
git add static/fonts/Inter-Bold.ttf static/images/milestones/ apps/accounts/management/commands/generate_milestone_backgrounds.py
git commit -m "feat: add milestone gradient backgrounds + Inter Bold font"
```

---

### Task 6: Milestone Image Generation Endpoint

**Files:**
- Create: `apps/accounts/milestone_image.py` — image generation logic
- Modify: `apps/accounts/views.py` — add `milestone_image_view`
- Modify: `apps/accounts/urls.py` — add URL pattern

- [ ] **Step 1: Create milestone_image.py**

```python
"""Generate shareable milestone images using Pillow."""
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.cache import cache


FONT_PATH = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Inter-Bold.ttf')
BG_DIR = os.path.join(settings.BASE_DIR, 'static', 'images', 'milestones')

MILESTONE_NAMES = {
    1: '1 Day', 7: '1 Week', 14: '2 Weeks', 30: '1 Month',
    60: '2 Months', 90: '90 Days', 180: '6 Months', 365: '1 Year',
    730: '2 Years', 1095: '3 Years', 1825: '5 Years', 3650: '10 Years',
}


def get_milestone_label(days):
    """Return a human-readable label for the day count."""
    if days in MILESTONE_NAMES:
        return MILESTONE_NAMES[days]
    if days >= 365:
        years = days // 365
        return f'{years} Year{"s" if years != 1 else ""}'
    if days >= 30:
        months = days // 30
        return f'{months} Month{"s" if months != 1 else ""}'
    return f'{days} Day{"s" if days != 1 else ""}'


def get_bg_tier(days):
    """Return background tier based on days sober."""
    if days < 30:
        return 'early'
    if days < 180:
        return 'mid'
    return 'long'


def generate_milestone_image(days, fmt='story'):
    """Generate a PNG milestone image. Returns bytes."""
    cache_key = f'milestone_img_{days}_{fmt}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Load background
    tier = get_bg_tier(days)
    bg_path = os.path.join(BG_DIR, f'bg-{tier}-{fmt}.png')
    if not os.path.exists(bg_path):
        # Fallback: generate a solid color
        size = (1080, 1920) if fmt == 'story' else (1080, 1080)
        img = Image.new('RGB', size, (30, 77, 139))
    else:
        img = Image.open(bg_path).copy()

    draw = ImageDraw.Draw(img)
    w, h = img.size

    # Load font at different sizes
    try:
        font_large = ImageFont.truetype(FONT_PATH, 120)
        font_medium = ImageFont.truetype(FONT_PATH, 48)
        font_small = ImageFont.truetype(FONT_PATH, 32)
    except OSError:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Main text: "90 Days Sober"
    main_text = f'{days:,} Days Sober'
    bbox = draw.textbbox((0, 0), main_text, font=font_large)
    text_w = bbox[2] - bbox[0]
    x = (w - text_w) // 2
    y = h // 2 - 100
    # Shadow
    draw.text((x + 3, y + 3), main_text, fill=(0, 0, 0, 80), font=font_large)
    # Main
    draw.text((x, y), main_text, fill='white', font=font_large)

    # Milestone label
    label = get_milestone_label(days)
    bbox = draw.textbbox((0, 0), label, font=font_medium)
    text_w = bbox[2] - bbox[0]
    x = (w - text_w) // 2
    draw.text((x, y + 140), label, fill=(255, 255, 255, 200), font=font_medium)

    # Watermark
    watermark = 'MyRecoveryPal.com'
    bbox = draw.textbbox((0, 0), watermark, font=font_small)
    text_w = bbox[2] - bbox[0]
    x = (w - text_w) // 2
    draw.text((x, h - 80), watermark, fill=(255, 255, 255, 150), font=font_small)

    # Export
    buffer = BytesIO()
    img.save(buffer, 'PNG', optimize=True)
    img_bytes = buffer.getvalue()

    cache.set(cache_key, img_bytes, 86400)  # 24h cache
    return img_bytes
```

- [ ] **Step 2: Add view to views.py**

At the end of `apps/accounts/views.py`, add:

```python
@login_required
def milestone_image_view(request, days):
    """Generate and return a shareable milestone image as PNG."""
    from apps.accounts.milestone_image import generate_milestone_image

    fmt = request.GET.get('format', 'story')
    if fmt not in ('story', 'square'):
        fmt = 'story'

    # Clamp days to reasonable range
    days = max(1, min(days, 36500))

    img_bytes = generate_milestone_image(days, fmt)
    response = HttpResponse(img_bytes, content_type='image/png')
    response['Content-Disposition'] = f'inline; filename="milestone-{days}-days.png"'
    response['Cache-Control'] = 'public, max-age=86400'
    return response
```

- [ ] **Step 3: Add URL pattern**

In `apps/accounts/urls.py`, add:

```python
    path('milestone-image/<int:days>/', views.milestone_image_view, name='milestone_image'),
```

- [ ] **Step 4: Verify endpoint**

```bash
python3 manage.py check
python3 manage.py runserver
```

Visit `http://localhost:8000/accounts/milestone-image/90/` — should return a PNG image. Try `?format=square` for 1080x1080.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/milestone_image.py apps/accounts/views.py apps/accounts/urls.py
git commit -m "feat: milestone image generation endpoint"
```

---

### Task 7: Share Buttons (Milestone Modal + Progress Page)

**Files:**
- Modify: `apps/accounts/templates/accounts/social_feed.html` — add share button to milestone celebration modal
- Modify: `apps/accounts/templates/accounts/progress.html` — add "Share My Progress" button

- [ ] **Step 1: Find milestone celebration modal in social_feed.html**

Search for `milestone_to_celebrate` or `celebration` in `social_feed.html`. Add a share button inside the modal, after the celebration text:

```html
{% if milestone_to_celebrate %}
<!-- Add this button inside the existing milestone celebration modal/section -->
<div style="margin-top: 1rem;">
    <button onclick="shareMilestone({{ milestone_to_celebrate.days }})"
            style="background: var(--accent-green); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 50px; font-weight: 600; cursor: pointer; font-size: 1rem;">
        <i class="fas fa-share-alt" aria-hidden="true"></i> Share My Milestone
    </button>
</div>
{% endif %}
```

Add the JavaScript share function (in the page's `{% block extra_js %}` or inline):

```html
<script>
function shareMilestone(days) {
    var imageUrl = '/accounts/milestone-image/' + days + '/?format=story';

    // Try native share (Capacitor)
    if (window.MRPNative && window.MRPNative.share) {
        window.MRPNative.share(
            'My Recovery Milestone',
            'I just hit ' + days + ' days sober on MyRecoveryPal!',
            window.location.origin + imageUrl
        );
        return;
    }

    // Try Web Share API
    if (navigator.share) {
        navigator.share({
            title: 'My Recovery Milestone',
            text: 'I just hit ' + days + ' days sober!',
            url: window.location.origin + imageUrl,
        }).catch(function() {});
        return;
    }

    // Fallback: open image in new tab for manual save/share
    window.open(imageUrl, '_blank');
}
</script>
```

- [ ] **Step 2: Add "Share My Progress" button to progress.html**

Find the milestone/sobriety counter section at the top of `progress.html`. Add:

```html
{% if days_sober and days_sober > 0 %}
<div style="text-align: center; margin: 1rem 0;">
    <button onclick="shareMilestone({{ days_sober }})"
            style="background: linear-gradient(135deg, var(--primary-dark), var(--primary-light)); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 50px; font-weight: 600; cursor: pointer; font-size: 0.95rem;">
        <i class="fas fa-share-alt" aria-hidden="true"></i> Share My Progress
    </button>
</div>
{% endif %}
```

Include the same `shareMilestone()` JS function from Step 1 (add it to the `{% block extra_js %}` of progress.html).

- [ ] **Step 3: Verify**

```bash
python3 manage.py check
python3 manage.py runserver
```

Visit the progress page — "Share My Progress" button should appear. Click it — should open share dialog or new tab with milestone image.

- [ ] **Step 4: Commit**

```bash
git add apps/accounts/templates/accounts/social_feed.html apps/accounts/templates/accounts/progress.html
git commit -m "feat: shareable milestone images on celebration modal + progress page"
```

---

### Task 8: Final Integration Test + Deploy

- [ ] **Step 1: Run Django check**

```bash
python3 manage.py check
```

Expected: 0 issues.

- [ ] **Step 2: Test full flow locally**

1. Visit `/accounts/social-feed/` — daily thought card appears at top
2. Visit `/accounts/daily-checkin/` — pledge card appears, submit check-in with pledge
3. Visit `/accounts/progress/` — "Share My Progress" button visible
4. Visit `/accounts/milestone-image/90/` — PNG image renders
5. Visit `/accounts/milestone-image/365/?format=square` — square PNG renders

- [ ] **Step 3: Collect static files**

```bash
rm -rf staticfiles && python3 manage.py collectstatic --noinput
```

Expected: Includes new font file and milestone backgrounds. No errors.

- [ ] **Step 4: Push to deploy**

```bash
git push origin main
```

- [ ] **Step 5: Run seed command on production**

After deploy, seed quotes on production. Either:
- SSH/Railway exec: `python manage.py seed_recovery_quotes`
- Or add to `start.sh` as a one-time init step

- [ ] **Step 6: Verify production**

Check Railway deployment status. Visit production social feed — daily thought should appear. Test milestone image endpoint.

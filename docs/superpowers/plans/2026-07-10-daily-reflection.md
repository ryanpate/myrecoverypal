# Daily Reflection + Reading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface the existing daily recovery thought on the progress home with a "Reflect in your journal" action (pre-filled private entry) and a deterministic "Today's reading" blog rotation, and expand the quote corpus to 365 unique entries.

**Architecture:** A small `apps/accounts/daily_content.py` module owns the two lookups (`get_daily_thought`, `get_daily_reading`); the social feed's inline lookup is refactored onto it. The journal app gains a `reflect_today` view that pre-fills the existing `JournalEntryForm` and delegates POST to the existing `create_entry`. The shared `_daily_thought.html` partial gains conditional action links. Content expansion extends the existing `seed_recovery_quotes` command's `QUOTES` list.

**Tech Stack:** Django 5.0.10. No migrations, no new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-10-daily-reflection-design.md`

## Global Constraints

- No schema changes anywhere on the branch (no migrations).
- Journal entries stay private — the reflect flow saves through the existing journal machinery only.
- Thought lookup uses `timezone.now().date()` (matches how the 6 AM UTC task creates the row — a localdate lookup could miss it). User-facing reflect "today" (entry title, duplicate guard) uses `timezone.localdate()` per repo convention. This split is deliberate; each use gets a code comment.
- All new corpus entries are ORIGINAL and program-neutral; nothing lifted or paraphrased from copyrighted recovery literature (AA "Daily Reflections" etc.). Attribution only for genuinely public-domain/widely-attributed general quotes.
- Tests run with `python manage.py test <module> -v 2` from the repo root; view tests use `@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)`.
- Surgical changes; commit per task with trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: daily_content helpers + feed refactor

**Files:**
- Create: `apps/accounts/daily_content.py`
- Modify: `apps/accounts/views.py` (~line 4216: replace the feed's inline `DailyRecoveryThought` lookup)
- Create: `apps/accounts/test_daily_content.py`

**Interfaces:**
- Consumes: `DailyRecoveryThought` (fields `quote`, `author_attribution`, `reflection_prompt`, `date` unique); `apps.blog.models.Post` (fields `status` with `'published'`, `slug`, `title`, ordering-safe `id`).
- Produces (Tasks 2-3 rely on):
  - `get_daily_thought() -> DailyRecoveryThought | None`
  - `get_daily_reading() -> Post | None` — deterministic per calendar day: `posts[timezone.now().date().toordinal() % count]` over `Post.objects.filter(status='published').order_by('id')`; `None` when no published posts.

- [ ] **Step 1: Write the failing tests**

Create `apps/accounts/test_daily_content.py`:

```python
"""Tests for the daily thought/reading lookups."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.daily_content import get_daily_reading, get_daily_thought
from apps.accounts.models import DailyRecoveryThought
from apps.blog.models import Post
from django.contrib.auth import get_user_model

User = get_user_model()


class DailyThoughtTests(TestCase):
    def test_returns_todays_thought(self):
        today = timezone.now().date()
        thought = DailyRecoveryThought.objects.create(
            quote="One day at a time.", date=today)
        DailyRecoveryThought.objects.create(
            quote="Yesterday's.", date=today - timedelta(days=1))
        self.assertEqual(get_daily_thought(), thought)

    def test_returns_none_when_no_thought_today(self):
        self.assertIsNone(get_daily_thought())


class DailyReadingTests(TestCase):
    def setUp(self):
        author = User.objects.create_user(username="author", password="x")
        self.posts = [
            Post.objects.create(
                title=f"Post {i}", slug=f"post-{i}",
                author=author, content="body", status="published",
            )
            for i in range(3)
        ]
        Post.objects.create(
            title="Draft", slug="draft", author=author,
            content="body", status="draft",
        )

    def test_deterministic_for_a_day_and_skips_drafts(self):
        first = get_daily_reading()
        second = get_daily_reading()
        self.assertEqual(first, second)
        self.assertIn(first, self.posts)  # never the draft

    def test_rotates_across_days(self):
        today = timezone.now().date()
        expected_index = today.toordinal() % 3
        self.assertEqual(get_daily_reading(), self.posts[expected_index])

    def test_none_when_no_published_posts(self):
        Post.objects.all().delete()
        self.assertIsNone(get_daily_reading())
```

(If `Post.objects.create` requires other non-null fields — check `apps/blog/models.py` — add the minimal extra defaults in `setUp` rather than changing the model.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.accounts.test_daily_content -v 2`
Expected: ERROR with `ModuleNotFoundError: No module named 'apps.accounts.daily_content'`

- [ ] **Step 3: Write the module**

Create `apps/accounts/daily_content.py`:

```python
"""Lookups for the shared daily-thought / daily-reading card.

Used by both the social feed and the progress home so the two surfaces
always agree on the day's content.
"""
from django.utils import timezone

from apps.accounts.models import DailyRecoveryThought


def get_daily_thought():
    """Today's DailyRecoveryThought, or None.

    Uses timezone.now().date() (server/UTC date), matching how the 6 AM UTC
    publish_daily_thought task keys the row — a per-user localdate lookup
    could miss the row entirely near midnight.
    """
    return DailyRecoveryThought.objects.filter(
        date=timezone.now().date()
    ).first()


def get_daily_reading():
    """Deterministic daily pick from published blog posts, or None.

    Same post for every user all day; cycles the whole archive as the
    ordinal advances. No state, no task, no model.
    """
    from apps.blog.models import Post

    posts = Post.objects.filter(status='published').order_by('id')
    count = posts.count()
    if not count:
        return None
    return posts[timezone.now().date().toordinal() % count]
```

- [ ] **Step 4: Refactor the feed lookup onto the helper**

In `apps/accounts/views.py` (~line 4216), replace:

```python
        # Daily recovery thought for feed
        from apps.accounts.models import DailyRecoveryThought
        context['daily_thought'] = DailyRecoveryThought.objects.filter(
            date=timezone.now().date()
        ).first()
```

with:

```python
        # Daily recovery thought for feed
        from apps.accounts.daily_content import get_daily_thought, get_daily_reading
        context['daily_thought'] = get_daily_thought()
        context['daily_reading'] = get_daily_reading()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.test_daily_content -v 2`
Expected: OK, 5 tests passing

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/daily_content.py apps/accounts/test_daily_content.py apps/accounts/views.py
git commit -m "feat(daily): shared daily thought/reading lookups; feed uses helper

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: journal reflect_today view

**Files:**
- Modify: `apps/journal/views.py` (add `reflect_today` after `create_entry`, ~line 137)
- Modify: `apps/journal/urls.py` (after the `write/` entry, ~line 14)
- Create: `apps/journal/test_reflect_today.py`

**Interfaces:**
- Consumes: `get_daily_thought()` from Task 1; existing `JournalEntryForm`, `create_entry`, `journal/entry_form.html`, `JournalEntry` (fields `user`, `title`, `content`, `created_at`).
- Produces: URL name `journal:reflect_today` at `/journal/reflect/` (used by Task 3's partial). Title format: `Daily Reflection — {localdate:%B %-d, %Y}`.

- [ ] **Step 1: Write the failing tests**

Create `apps/journal/test_reflect_today.py`:

```python
"""Tests for the daily-reflection journal flow."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import DailyRecoveryThought
from apps.journal.models import JournalEntry

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ReflectTodayTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="r", password="x")
        self.client.force_login(self.user)
        self.thought = DailyRecoveryThought.objects.create(
            quote="Progress, not perfection.",
            author_attribution="",
            reflection_prompt="Where did you make progress today?",
            date=timezone.now().date(),
        )

    def test_get_prefills_title_and_content(self):
        resp = self.client.get(reverse("journal:reflect_today"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Daily Reflection")
        self.assertContains(resp, "Progress, not perfection.")
        self.assertContains(resp, "Where did you make progress today?")

    def test_post_saves_private_entry_via_create_flow(self):
        resp = self.client.post(reverse("journal:reflect_today"), {
            "title": "Daily Reflection — test",
            "content": "My reflection.",
        })
        entry = JournalEntry.objects.get(user=self.user)
        self.assertRedirects(
            resp, reverse("journal:entry_detail", kwargs={"pk": entry.pk}),
            fetch_redirect_response=False)
        self.assertEqual(entry.content, "My reflection.")

    def test_second_get_today_redirects_to_existing_entry(self):
        entry = JournalEntry.objects.create(
            user=self.user, title="Daily Reflection — earlier",
            content="done already",
        )
        resp = self.client.get(reverse("journal:reflect_today"))
        self.assertRedirects(
            resp, reverse("journal:entry_detail", kwargs={"pk": entry.pk}),
            fetch_redirect_response=False)

    def test_other_users_reflection_does_not_trigger_redirect(self):
        other = User.objects.create_user(username="o", password="x")
        JournalEntry.objects.create(
            user=other, title="Daily Reflection — theirs", content="x")
        resp = self.client.get(reverse("journal:reflect_today"))
        self.assertEqual(resp.status_code, 200)

    def test_works_without_a_daily_thought(self):
        self.thought.delete()
        resp = self.client.get(reverse("journal:reflect_today"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Daily Reflection")

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("journal:reflect_today"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp["Location"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.journal.test_reflect_today -v 2`
Expected: ERROR with `NoReverseMatch: Reverse for 'reflect_today' not found`

- [ ] **Step 3: Add the view**

In `apps/journal/views.py`, directly after `create_entry`, add:

```python
@login_required
def reflect_today(request):
    """Journal entry pre-filled with today's recovery thought.

    POST delegates to create_entry so saving/streaks/redirects stay in one
    place. "Today" for the title and duplicate guard is the user's local
    day (timezone.localdate(), per repo convention); the thought itself is
    looked up by server date inside get_daily_thought.
    """
    if request.method == 'POST':
        return create_entry(request)

    today_local = timezone.localdate()

    existing = JournalEntry.objects.filter(
        user=request.user,
        title__startswith='Daily Reflection',
        created_at__date=today_local,
    ).first()
    if existing:
        return redirect('journal:entry_detail', pk=existing.pk)

    from apps.accounts.daily_content import get_daily_thought
    thought = get_daily_thought()

    title = f"Daily Reflection — {today_local.strftime('%B %-d, %Y')}"
    if thought:
        seed_lines = [f'"{thought.quote}"']
        if thought.author_attribution:
            seed_lines.append(f"— {thought.author_attribution}")
        if thought.reflection_prompt:
            seed_lines.append("")
            seed_lines.append(thought.reflection_prompt)
        seed_lines.append("")
        content = "\n".join(seed_lines)
    else:
        content = ""

    form = JournalEntryForm(initial={'title': title, 'content': content})
    return render(request, 'journal/entry_form.html', {'form': form})
```

Check the imports at the top of `apps/journal/views.py`: `timezone` (from django.utils), `redirect`, `login_required`, `JournalEntryForm`, `JournalEntry` — all should already be imported for the existing views; add only what's genuinely missing.

Note: `create_entry` may or may not carry `@login_required` — check; the delegation call goes through `reflect_today`'s own decorator either way.

- [ ] **Step 4: Add the URL**

In `apps/journal/urls.py`, after the `write/` line:

```python
    path('reflect/', views.reflect_today, name='reflect_today'),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python manage.py test apps.journal.test_reflect_today -v 2`
Expected: OK, 6 tests passing. (If `entry_form.html` posts to a hardcoded `{% url 'journal:create_entry' %}` action, the POST-delegation test still passes — saving through either URL lands in `create_entry`. If the form posts to `action=""`, the reflect URL handles it via the delegation branch. Either is acceptable; do not modify the template.)

- [ ] **Step 6: Commit**

```bash
git add apps/journal/views.py apps/journal/urls.py apps/journal/test_reflect_today.py
git commit -m "feat(journal): reflect-today entry pre-filled with the daily thought

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: partial actions + progress home surfacing

**Files:**
- Modify: `apps/accounts/templates/accounts/partials/_daily_thought.html` (add actions row)
- Modify: `apps/accounts/views.py` — `progress_view`, add context just before `return render(request, 'accounts/progress.html', context)` (~line 1362)
- Modify: `apps/accounts/templates/accounts/progress.html` (include partial directly above the pledge card, ~line 1631)
- Create: `apps/accounts/test_progress_daily_thought.py`

**Interfaces:**
- Consumes: `get_daily_thought()` / `get_daily_reading()` (Task 1); `journal:reflect_today` (Task 2); template context vars `daily_thought`, `daily_reading`, `todays_reflection`.
- Produces: the partial renders three conditional extras — reflect button (authenticated + `daily_thought` present), "View today's reflection" variant (when `todays_reflection` in context), reading link (when `daily_reading` present). Feed passes `daily_thought`/`daily_reading` (Task 1 already wired) but NOT `todays_reflection` (avoids an extra per-request query on the hot feed path — the reflect view itself redirects to the existing entry, so the plain button is always safe).

- [ ] **Step 1: Write the failing tests**

Create `apps/accounts/test_progress_daily_thought.py`:

```python
"""Tests for the daily thought/reading card on the progress home."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import DailyRecoveryThought
from apps.journal.models import JournalEntry

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ProgressDailyThoughtTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="p", password="x")
        self.client.force_login(self.user)
        DailyRecoveryThought.objects.create(
            quote="Progress, not perfection.",
            reflection_prompt="Where did you make progress today?",
            date=timezone.now().date(),
        )

    def test_progress_home_shows_thought_and_reflect_button(self):
        resp = self.client.get(reverse("accounts:progress"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Progress, not perfection.")
        self.assertContains(resp, reverse("journal:reflect_today"))
        self.assertContains(resp, "Reflect in your journal")

    def test_button_switches_after_todays_reflection(self):
        entry = JournalEntry.objects.create(
            user=self.user, title="Daily Reflection — today", content="x")
        resp = self.client.get(reverse("accounts:progress"))
        self.assertContains(resp, "View today")
        self.assertContains(
            resp, reverse("journal:entry_detail", kwargs={"pk": entry.pk}))

    def test_reading_link_renders_when_posts_exist(self):
        from apps.blog.models import Post
        author = User.objects.create_user(username="a2", password="x")
        post = Post.objects.create(
            title="Daily Read", slug="daily-read", author=author,
            content="body", status="published")
        resp = self.client.get(reverse("accounts:progress"))
        self.assertContains(resp, "Daily Read")
        self.assertContains(resp, post.get_absolute_url())

    def test_no_reading_link_without_posts(self):
        resp = self.client.get(reverse("accounts:progress"))
        self.assertNotContains(resp, "Today&#x27;s reading")
        self.assertEqual(resp.status_code, 200)

    def test_social_feed_still_renders_with_partial(self):
        resp = self.client.get(reverse("accounts:social_feed"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Progress, not perfection.")
```

(Adjust `Post.objects.create` defaults like Task 1 if the model requires more fields; check the exact "Today's reading" label escaping — `assertNotContains` with `Today` + `reading` split assertions is acceptable if apostrophe escaping differs.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.accounts.test_progress_daily_thought -v 2`
Expected: FAIL — progress page contains neither the quote nor the reflect URL yet (feed test may already pass).

- [ ] **Step 3: Add progress_view context**

In `apps/accounts/views.py`, inside `progress_view`, directly before `return render(request, 'accounts/progress.html', context)` (~line 1362), add:

```python
    # Daily thought + reading card (shared partial with the social feed).
    from apps.accounts.daily_content import get_daily_thought, get_daily_reading
    context['daily_thought'] = get_daily_thought()
    context['daily_reading'] = get_daily_reading()
    # User-local "today" for the reflect duplicate-guard (repo convention).
    from apps.journal.models import JournalEntry
    context['todays_reflection'] = JournalEntry.objects.filter(
        user=request.user,
        title__startswith='Daily Reflection',
        created_at__date=timezone.localdate(),
    ).first()
```

- [ ] **Step 4: Extend the partial**

In `apps/accounts/templates/accounts/partials/_daily_thought.html`, add inside `.daily-thought-inner`, after the reflection-prompt `{% endif %}` (keep everything above unchanged):

```django
        <div class="daily-thought-actions" style="margin-top: 0.9rem; display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: center;">
            {% if user.is_authenticated %}
                {% if todays_reflection %}
                <a href="{% url 'journal:entry_detail' pk=todays_reflection.pk %}"
                    style="font-weight: 600; text-decoration: none;">
                    <i class="fas fa-book-open" aria-hidden="true"></i> View today's reflection</a>
                {% else %}
                <a href="{% url 'journal:reflect_today' %}"
                    style="font-weight: 600; text-decoration: none;">
                    <i class="fas fa-pen" aria-hidden="true"></i> Reflect in your journal</a>
                {% endif %}
            {% endif %}
            {% if daily_reading %}
            <a href="{{ daily_reading.get_absolute_url }}"
                style="font-weight: 600; text-decoration: none;">
                <i class="fas fa-book" aria-hidden="true"></i> Today's reading: {{ daily_reading.title }}</a>
            {% endif %}
        </div>
```

- [ ] **Step 5: Include the partial on the progress home**

In `apps/accounts/templates/accounts/progress.html`, directly ABOVE the pledge card opening tag (`<div class="pledge-card" id="pledgeCard" ...>`, ~line 1631), add:

```django
{% include 'accounts/partials/_daily_thought.html' %}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.test_progress_daily_thought -v 2`
Expected: OK, 5 tests passing

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/templates/accounts/partials/_daily_thought.html apps/accounts/templates/accounts/progress.html apps/accounts/views.py apps/accounts/test_progress_daily_thought.py
git commit -m "feat(daily): thought card on progress home with reflect + reading actions

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: expand corpus to 365 entries

**Files:**
- Modify: `apps/accounts/management/commands/seed_recovery_quotes.py` (extend the `QUOTES` list from 109 to 365 entries)
- Create: `apps/accounts/test_seed_quotes.py`

**Interfaces:**
- Consumes: existing `QUOTES` list format — dicts with keys `"quote"` (required), `"author"` (optional), `"prompt"` (optional but required for all NEW entries).
- Produces: `len(QUOTES) == 365`, all quote texts unique.

This task is content authorship with a test as the acceptance gate. The 256 new entries must be:
- **Original** — written fresh for this command; nothing lifted or paraphrased from copyrighted recovery literature (AA Daily Reflections, 24 Hours a Day, etc.). Attribution (`"author"`) only for genuinely public-domain or widely-attributed general quotes (e.g., Marcus Aurelius, Seneca, proverbs); most entries should be unattributed originals.
- **Program-neutral** — no 12-step-only framing (no "Higher Power", step numbers, sponsor-assumptions); usable by AA, SMART, secular, and undecided members alike.
- **Varied** — spread across themes: cravings passing, self-compassion after setbacks, one-day-at-a-time, connection/asking for help, gratitude, identity change, handling boredom/stress/HALT, celebrating small wins, honesty, routines/sleep/health, helping others, patience with the process.
- **Each new entry has a `"prompt"`** — a single reflective question tied to the quote.
- Tone-matched to the existing 109 entries (read a dozen before writing).

Three examples of the expected shape:

```python
    {
        "quote": "A craving is loud on arrival and quiet on the way out. You only have to outlast the loud part.",
        "prompt": "What helped you outlast the loud part last time?",
    },
    {
        "quote": "You are allowed to be both a work in progress and proof of progress at the same time.",
        "prompt": "What's one piece of proof from this week?",
    },
    {
        "quote": "We must take charge of our own thoughts, or they will take charge of us.",
        "author": "Epictetus (paraphrase, public domain)",
        "prompt": "Which recurring thought deserves to be questioned today?",
    },
```

- [ ] **Step 1: Write the failing test**

Create `apps/accounts/test_seed_quotes.py`:

```python
"""Acceptance tests for the expanded daily-quote corpus."""
from datetime import date

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.management.commands.seed_recovery_quotes import QUOTES
from apps.accounts.models import DailyRecoveryThought


class QuoteCorpusTests(TestCase):
    def test_corpus_has_365_entries(self):
        self.assertEqual(len(QUOTES), 365)

    def test_all_quotes_unique(self):
        texts = [q["quote"].strip().lower() for q in QUOTES]
        self.assertEqual(len(texts), len(set(texts)))

    def test_new_entries_all_have_prompts(self):
        # Entries beyond the original 109 must each carry a prompt.
        missing = [i for i, q in enumerate(QUOTES[109:], start=109)
                   if not q.get("prompt")]
        self.assertEqual(missing, [])

    def test_command_is_idempotent(self):
        call_command("seed_recovery_quotes", start_date="2030-01-01")
        first_count = DailyRecoveryThought.objects.count()
        call_command("seed_recovery_quotes", start_date="2030-01-01")
        self.assertEqual(DailyRecoveryThought.objects.count(), first_count)
        self.assertEqual(first_count, 365)
```

(Check the command's argument spelling — it's `--start-date`, passed to `call_command` as `start_date="..."`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_seed_quotes -v 2`
Expected: FAIL — `test_corpus_has_365_entries` reports 109 != 365.

- [ ] **Step 3: Author the 256 new entries**

Append 256 new dict entries to `QUOTES` in `seed_recovery_quotes.py`, following the constraints and examples above. Work in batches (e.g., 4 × 64) and re-run the uniqueness test between batches to catch accidental repeats early.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.test_seed_quotes -v 2`
Expected: OK, 4 tests passing

- [ ] **Step 5: Spot-check quality**

Read 20 random new entries aloud-in-your-head for: originality, program-neutrality, no clichés-with-attribution problems (never attribute an original line to a real person), prompt actually connects to the quote. Fix any that fail.

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/management/commands/seed_recovery_quotes.py apps/accounts/test_seed_quotes.py
git commit -m "feat(daily): expand recovery-quote corpus to 365 original entries

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: verify, changelog, final review, merge, deploy

**Files:**
- Modify: `docs/CHANGELOG.md` (new entry at top of the list)

- [ ] **Step 1: Full test sweep**

Run: `python manage.py test apps.accounts.test_daily_content apps.journal.test_reflect_today apps.accounts.test_progress_daily_thought apps.accounts.test_seed_quotes -v 1`
Expected: OK, 20 tests (5 + 6 + 5 + 4)

- [ ] **Step 2: End-to-end verification**

Per `.claude/skills/verify/SKILL.md`: run the dev server, log in as a scratch user, confirm the thought card renders on `/accounts/progress/` with both action links; click Reflect → pre-filled form; save → private entry; revisit progress → button reads "View today's reflection"; confirm the social feed card still renders.

- [ ] **Step 3: Changelog entry**

Add at the top of the list in `docs/CHANGELOG.md`:

```markdown
- **2026-07-10:** Daily reflection + reading on the progress home. The existing daily-thought card (previously feed-only) now renders on `/accounts/progress/` via the shared `_daily_thought.html` partial, with two new actions: "Reflect in your journal" → new `journal:reflect_today` view (`/journal/reflect/`) that pre-fills a private entry with the day's quote + prompt (duplicate-guarded per user-local day — second visit links to the existing entry), and "Today's reading" → deterministic daily rotation over published blog posts (`apps/accounts/daily_content.py`, no new model/task). Quote corpus expanded from 109 to 365 original program-neutral entries in `seed_recovery_quotes` (nothing from copyrighted recovery literature); the 6 AM recycler stays as backstop. Run `python manage.py seed_recovery_quotes` in prod after deploy. 20 new tests.
```

- [ ] **Step 4: Commit, merge, deploy**

```bash
git add docs/CHANGELOG.md
git commit -m "docs: changelog entry for daily reflection + reading

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Then superpowers:finishing-a-development-branch (merge to main deploys via Railway). Post-deploy: run `python manage.py seed_recovery_quotes` in a Railway shell (seeds the next 365 days from today; existing dates skipped); verify the progress home card, reflect flow, and reading link live.

---

## Self-Review Notes

- Spec coverage: §1 progress card + partial safety → Tasks 1, 3; §2 reflect flow + localdate convention + duplicate guard → Task 2 (+ progress context in Task 3); §3 reading rotation → Task 1 (helper) + Task 3 (render); §4 corpus 365 + constraints + prod seed run → Tasks 4-5; spec testing list → Tasks 1-4 tests; verification → Task 5.
- Type consistency: `get_daily_thought()`/`get_daily_reading()` (T1) used verbatim in T2/T3; `journal:reflect_today` (T2) reversed in T3's partial/tests; `todays_reflection` context key matches partial conditional; QUOTES dict keys (`quote`/`author`/`prompt`) match the command's `handle()` mapping (`entry.get("author", "")`, `entry.get("prompt", "")`).
- Known judgment calls documented in-plan: server-date vs localdate split (Global Constraints); feed omits `todays_reflection` (T3 Interfaces, with rationale).
- Test counts: 5 + 6 + 5 + 4 = 20 (T5 sweep).

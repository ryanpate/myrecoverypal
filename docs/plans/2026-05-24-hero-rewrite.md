# Landing Page Hero Rewrite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the homepage hero with a tool-first, sobriety-calculator-led design that matches GSC tool-seeker search intent (per audit + brainstorm).

**Architecture:** Single template edit at `apps/core/templates/core/index.html`. Replace the `<section class="hero">` block content (~lines 1128–1163) with new copy + a stylized HTML/CSS sobriety counter card. Add scoped CSS to the existing `{% block extra_css %}`. No Python, no migrations, no JS, no new static assets.

**Tech Stack:** Django templates, plain HTML/CSS. Existing `.hero` gradient/grid stays — only inner content + new card styles change.

**Reference spec:** `docs/plans/2026-05-24-hero-rewrite-design.md`

---

## Pre-flight

- [ ] **Step 0.1: Verify branch + clean baseline**

Run:
```bash
git branch --show-current
git log --oneline -3
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts -v 0 2>&1 | tail -3
```

Expected:
- Branch is `feat/hero-rewrite`
- Latest commit is the design spec (`docs: hero rewrite design spec...`)
- 48 tests pass (baseline). No failures.

- [ ] **Step 0.2: Re-read existing hero block for exact line numbers**

Run:
```bash
grep -n "<!-- ===\|SECTION 1: HERO\|<section class=\"hero\"\|</section>" apps/core/templates/core/index.html | head -10
```

Note the exact line numbers of the `<section class="hero" id="home">` opening tag and its closing `</section>`. The current file is ~1500 lines and line numbers may drift slightly from what's documented in the spec.

- [ ] **Step 0.3: Note existing responsive breakpoint**

The existing landing page CSS uses `@media (max-width: 768px)` as the mobile breakpoint (verified at `apps/core/templates/core/index.html:997`). The design spec mentioned 600px/900px but **we follow the existing 768px convention** rather than introducing new breakpoints. Update the spec doc inline if needed.

Run:
```bash
grep -n "@media\|.hero-right.*display\|.hero-left" apps/core/templates/core/index.html | head -10
```

Expected: confirm the existing `.hero-right { display: none; }` at the 768px breakpoint (line ~1005). The new card **must override this** so the counter shows on mobile too (the spec calls for it stacked, not hidden).

---

## Task 1: Replace hero HTML + add new CSS

This is one atomic task because the HTML and CSS depend on each other — the new HTML references new CSS classes (`.hero-counter-card`, etc.) that don't exist yet. Splitting them would leave one intermediate commit in a visually-broken state.

**Files:**
- Modify: `apps/core/templates/core/index.html` (HTML block ~lines 1128–1163, plus CSS additions in `{% block extra_css %}`)

### Step 1.1: Add new CSS for the sobriety counter card

Open `apps/core/templates/core/index.html`. Find the existing `.hero-right` CSS rule (search for `.hero-right {` — should be near other `.hero-*` styles around line 350-400). Add a NEW block of CSS immediately after the existing hero CSS rules (still inside the `{% block extra_css %}` block, before the `MOBILE RESPONSIVE` comment at line ~995).

Add this CSS verbatim:

```css
/* ================================================
   HERO SOBRIETY COUNTER CARD (replaces feed.webp screenshot)
================================================ */
.hero-counter-card {
    background: linear-gradient(180deg, #0f2d56 0%, #1a2a44 100%);
    border-radius: 14px;
    padding: 0;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(255, 255, 255, 0.05);
    overflow: hidden;
    max-width: 380px;
    width: 100%;
    margin: 0 auto;
}

.hero-counter-card__top {
    background: linear-gradient(135deg, #1e4d8b 0%, #0f2d56 100%);
    padding: 1.75rem 1.5rem;
    text-align: center;
    color: white;
}

.hero-counter-card__label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    opacity: 0.7;
    margin-bottom: 0.5rem;
}

.hero-counter-card__days {
    font-size: 3.5rem;
    font-weight: 800;
    color: #52b788;
    line-height: 1;
    letter-spacing: -1px;
}

.hero-counter-card__elapsed {
    font-size: 0.85rem;
    opacity: 0.85;
    margin-top: 0.5rem;
}

.hero-counter-card__bottom {
    padding: 1rem 1.5rem 1.25rem;
    color: white;
}

.hero-counter-card__milestone-label {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    opacity: 0.6;
    margin-bottom: 0.35rem;
}

.hero-counter-card__milestone-name {
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 0.6rem;
}

.hero-counter-card__progress-track {
    background: rgba(255, 255, 255, 0.1);
    height: 6px;
    border-radius: 3px;
    overflow: hidden;
}

.hero-counter-card__progress-fill {
    background: linear-gradient(90deg, #52b788 0%, #74d2a5 100%);
    height: 100%;
    width: 78%;
    border-radius: 3px;
}

.hero-counter-card__remaining {
    font-size: 0.8rem;
    opacity: 0.7;
    margin-top: 0.5rem;
}

/* Make sure the card is visible on mobile (overrides existing .hero-right { display: none }) */
@media (max-width: 768px) {
    .hero-right {
        display: block !important;
        margin-top: 1.5rem;
    }
    .hero-counter-card {
        max-width: 320px;
    }
    .hero-counter-card__days {
        font-size: 3rem;
    }
}
```

### Step 1.2: Replace the hero HTML block

In the same file `apps/core/templates/core/index.html`, find the existing hero block:

```html
<!-- ================================================
     SECTION 1: HERO
================================================ -->
<section class="hero" id="home">
    <div class="hero-left">
        <h1>Recovery Is Better Together</h1>
        ...
    </div>
    <div class="hero-right">
        <div class="hero-screenshot-wrap">
            <picture>
                <source srcset="{% static 'images/demo/feed.webp' %}" type="image/webp">
                <img src="{% static 'images/demo/feed.png' %}" alt="MyRecoveryCircle social feed screenshot" class="hero-screenshot" loading="eager" fetchpriority="high" width="600" height="450">
            </picture>
        </div>
    </div>
</section>
```

Replace the entire `<section class="hero" id="home"> ... </section>` block with:

```html
<!-- ================================================
     SECTION 1: HERO  (tool-first, calculator-led)
================================================ -->
<section class="hero" id="home">
    <div class="hero-left">
        {% if user.is_authenticated %}
            <h1>Welcome back, {{ user.first_name|default:user.username }}.</h1>
            <p>Your community, your check-in, your coach — all where you left them.</p>

            <div class="hero-cta-group">
                <a href="{% url 'accounts:social_feed' %}" class="cta-button cta-button-pulse">Go to MyRecoveryCircle</a>
            </div>
        {% else %}
            <h1>How many days sober are you?</h1>
            <p>Find out free. Track every day. Get an AI coach in your corner whenever you need one.</p>

            <div class="hero-trust-badges">
                <span class="hero-trust-badge"><i class="fas fa-check-circle" aria-hidden="true"></i> Free forever</span>
                <span class="hero-trust-badge"><i class="fab fa-apple" aria-hidden="true"></i> Available on iOS</span>
                <span class="hero-trust-badge"><i class="fas fa-lock" aria-hidden="true"></i> Private &amp; secure</span>
            </div>

            <div class="hero-cta-group">
                <a href="{% url 'core:sobriety_calculator' %}" class="cta-button cta-button-pulse">Count My Days &rarr;</a>
                <a href="{% url 'accounts:login' %}" class="hero-secondary-link">Already have an account? Sign in</a>
            </div>
        {% endif %}
    </div>

    <div class="hero-right">
        <div class="hero-counter-card" role="img" aria-label="Example sobriety counter showing 3,003 days sober with progress toward 9-year milestone">
            <div class="hero-counter-card__top">
                <div class="hero-counter-card__label">Days Sober</div>
                <div class="hero-counter-card__days">3,003</div>
                <div class="hero-counter-card__elapsed">8 years, 2 months</div>
            </div>
            <div class="hero-counter-card__bottom">
                <div class="hero-counter-card__milestone-label">Next Milestone</div>
                <div class="hero-counter-card__milestone-name">9 Years</div>
                <div class="hero-counter-card__progress-track">
                    <div class="hero-counter-card__progress-fill"></div>
                </div>
                <div class="hero-counter-card__remaining">284 days to go</div>
            </div>
        </div>
    </div>
</section>
```

**Notes for the implementer:**
- The `aria-label` on the card explains the static example numbers for screen readers (the card isn't interactive; it's a visual mockup).
- The `{% url 'core:sobriety_calculator' %}` URL name should already exist in `apps/core/urls.py` — verify with `grep "sobriety_calculator" apps/core/urls.py` if uncertain. If it raises `NoReverseMatch` on render, fall back to hardcoded `/sobriety-calculator/` but flag the issue.
- The `cta-button-pulse` class is preserved on the primary CTA (matches the current pattern).
- The `hero-secondary-link` class already exists in the existing hero CSS (used for the current "See how it works" link).

### Step 1.3: Verify Django still renders the page

Run:
```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py check
```

Expected: `System check identified no issues (0 silenced).`

If it fails with a `NoReverseMatch` for `core:sobriety_calculator`, run this to confirm the URL name:
```bash
grep -n "sobriety.calculator\|sobriety_calculator" apps/core/urls.py
```

Expected: a line like `path('sobriety-calculator/', views.sobriety_calculator, name='sobriety_calculator')`. Adjust the template's `{% url %}` tag to match the actual name if different.

### Step 1.4: Start dev server and visually verify at desktop viewport

Run in one terminal:
```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py runserver
```

Open `http://localhost:8000/` in a browser at a **desktop viewport** (≥1200px wide).

Visually confirm:
- H1 reads "How many days sober are you?" (left side)
- Subhead reads "Find out free. Track every day. Get an AI coach in your corner whenever you need one."
- Three trust badges visible: "Free forever", "Available on iOS", "Private & secure"
- Primary button reads "Count My Days →" with the pulse animation
- Secondary link reads "Already have an account? Sign in"
- Right side shows a dark navy card with:
  - "DAYS SOBER" label
  - Large green "3,003" number
  - "8 years, 2 months" elapsed text
  - "NEXT MILESTONE / 9 Years" with a progress bar at ~78%
  - "284 days to go"

Click "Count My Days →" — should navigate to `/sobriety-calculator/`.
Click "Already have an account? Sign in" — should navigate to `/accounts/login/`.

### Step 1.5: Verify authenticated user state

In a separate browser tab (or after using the Django admin login at `http://localhost:8000/admin/`), navigate to `/` while logged in.

Confirm:
- H1 reads "Welcome back, [username]."
- Subhead reads "Your community, your check-in, your coach — all where you left them."
- Single CTA reads "Go to MyRecoveryCircle" → navigates to `/accounts/social-feed/`
- No trust badges shown
- Right-side counter card is still visible (same example numbers as anonymous view)

### Step 1.6: Verify tablet viewport (≤900px wide)

In browser dev tools, set viewport to 800px wide (tablet).

Confirm:
- Hero stacks vertically (text on top, card below)
- H1 size scales down (existing CSS handles this at 768px breakpoint)
- All elements remain readable and well-spaced
- Counter card is centered and ~320px wide

### Step 1.7: Verify mobile viewport (≤600px)

In browser dev tools, set viewport to 375px wide (iPhone SE-ish).

Confirm:
- Hero is fully stacked
- Counter card is visible (NOT `display: none`) and scaled to ~320px wide
- H1 wraps to 2 lines without overflow
- All three trust badges remain on screen (may wrap to multiple lines)
- Tap targets are at least 44×44px

### Step 1.8: Stop dev server and commit

Stop the server (`Ctrl+C` in the runserver terminal).

```bash
git add apps/core/templates/core/index.html
git commit -m "feat(landing): tool-first hero rewrite — calculator-led, question-led headline

Replaces 'Recovery Is Better Together' + social feed screenshot with
'How many days sober are you?' framing matching GSC tool-seeker queries.

- H1 directly mirrors top search query
- Primary CTA drives to /sobriety-calculator/ (no-signup tool)
- Hero visual replaced with stylized HTML/CSS sobriety counter card
  (no static asset, pixel control, fast load)
- Trust badges reduced from 4 to 3 honest claims (per Feb 19 cleanup
  pattern that removed inflated social proof)
- Authenticated user state preserves existing 'Welcome back' UX

Spec: docs/plans/2026-05-24-hero-rewrite-design.md"
```

---

## Task 2: Regression check + PR

### Step 2.1: Run the full test suite

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts -v 0
```

Expected: 48 tests pass (same baseline). This change doesn't touch Python code, so any test failure means an unrelated regression — investigate before continuing.

Run a broader check:
```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py check --deploy 2>&1 | tail -10
```

Expected: no new warnings introduced by this branch. Pre-existing warnings (HSTS, SECURE_SSL_REDIRECT, etc.) are fine.

### Step 2.2: Confirm the homepage URL itself resolves

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py shell -c "
from django.test import Client
from django.test.utils import override_settings
with override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False):
    c = Client()
    r = c.get('/')
    print('Status:', r.status_code)
    print('Has new H1:', b'How many days sober are you?' in r.content)
    print('Has counter card:', b'hero-counter-card' in r.content)
    print('Has calculator URL:', b'/sobriety-calculator/' in r.content)
    print('Old H1 gone:', b'Recovery Is Better Together' not in r.content)
"
```

Expected output:
```
Status: 200
Has new H1: True
Has counter card: True
Has calculator URL: True
Old H1 gone: True
```

If any of these is wrong, the rendered template doesn't match the spec — investigate and fix before proceeding.

### Step 2.3: Push branch

```bash
git push -u origin feat/hero-rewrite
```

### Step 2.4: Open the PR

```bash
gh pr create --base main --head feat/hero-rewrite \
  --title "feat(landing): tool-first hero rewrite (calculator-led, question-led headline)" \
  --body "$(cat <<'EOF'
## Summary

Replaces the homepage hero per the audit's #1 priority: the existing 'Recovery Is Better Together' hero was structurally misaligned with what people actually search for.

**Before:** Community-focused H1 + social feed screenshot → primary CTA was 'Join Free Today'

**After:** Question-led H1 + sobriety counter card visual → primary CTA is 'Count My Days' → `/sobriety-calculator/`

## Why

GSC data shows people search for tools ('sobriety calculator', 'how many days sober', 'sober app tracker'), not 'recovery community'. The current hero was getting 38.68% CTR but almost entirely from branded queries — non-branded discovery was failing because hero positioning didn't match search intent.

## What changed

- New H1: 'How many days sober are you?' (directly mirrors top search query)
- Primary CTA → `/sobriety-calculator/` (the existing no-signup tool — already built, just unsurfaced)
- Hero visual: stylized HTML/CSS counter card (no static asset, no real screenshot, pixel-controlled)
- Trust badges reduced 4 → 3 honest claims (Free forever / Available on iOS / Private & secure) — matches Feb 19 cleanup pattern removing inflated social proof
- Authenticated user state preserved with 'Welcome back' UX
- Rest of landing page (trust strip, How It Works, showcases, FAQ, blog, CTA banner) is unchanged

## Files

One file modified: `apps/core/templates/core/index.html` (HTML block + new CSS in `{% block extra_css %}`).

No Python changes. No migrations. No new static assets. No JS. No URL changes.

## Test plan

- [x] Visual verification at desktop (≥1200px), tablet (~800px), mobile (~375px)
- [x] Anonymous vs authenticated states both render correct copy + CTA
- [x] Primary CTA navigates to `/sobriety-calculator/`
- [x] Secondary link navigates to `/accounts/login/`
- [x] 48/48 tests pass
- [x] `manage.py check` clean
- [x] Homepage renders new H1, contains counter card markup, links to calculator
- [ ] Manual smoke after merge: open www.myrecoverypal.com on production, verify new hero

## Out of scope (separate audit follow-ups)

- Registration friction reduction (Audit Priority #2)
- Weekly Shop email + milestone coupons (Audit Priority #3)
- `noindex` thin blog tag/category pages (Audit Priority #4)
- A/B test infrastructure (no measurement of conversion lift in this PR)

Design spec: `docs/plans/2026-05-24-hero-rewrite-design.md`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: returns a PR URL. The PR should auto-pass any CI you have (this branch only touches a template).

---

## Self-Review

Walking the plan back against the spec:

**Spec coverage:**
- ✓ H1 / subhead / CTAs / trust badges → all in Step 1.2 code
- ✓ Authenticated user variant → in Step 1.2 code, verified in Step 1.5
- ✓ Stylized HTML/CSS counter card (no real screenshot) → Step 1.1 + 1.2
- ✓ Static example numbers (3,003 days, 9-year milestone at 78%, 284 days to go) → Step 1.2 HTML
- ✓ Responsive at desktop / tablet / mobile → verified in Steps 1.6 and 1.7; mobile-specific CSS in Step 1.1
- ✓ Mobile visibility override (`display: block !important` defeats existing `.hero-right { display: none }`) → Step 1.1, called out in Step 0.3
- ✓ Trust badges honesty constraint (3 badges, no fake social proof) → Step 1.2
- ✓ Files affected: only `apps/core/templates/core/index.html` → enforced in commit
- ✓ Success criteria (visual review, CTA routing, no regression, no JS errors, existing tests pass) → Steps 1.4–1.7 and 2.1–2.2

**Placeholder scan:** None. Every step has actual code or actual commands.

**Type consistency:** N/A (no Python types). HTML class names referenced in Step 1.2 (`hero-counter-card`, `hero-counter-card__top`, etc.) all match definitions in Step 1.1. URL names referenced (`core:sobriety_calculator`, `accounts:login`, `accounts:social_feed`) all already exist in the project.

**One spec deviation worth flagging:**
- Spec said breakpoints at 600px and 900px; implementation uses existing 768px breakpoint per Step 0.3. Reasoning documented in plan; spec doesn't strictly require new breakpoints.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-24-hero-rewrite.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?

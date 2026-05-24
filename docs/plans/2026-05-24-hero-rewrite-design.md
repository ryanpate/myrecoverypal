# Landing Page Hero Rewrite — Design

**Date:** 2026-05-24
**Status:** Approved direction; implementation plan to follow
**Audit reference:** Conversion audit identified the current hero as the highest-leverage fix — every landing page visitor sees it, and the current "Recovery Is Better Together" framing is misaligned with what Google Search Console shows people actually search for.

---

## Goal

Replace the homepage hero (`apps/core/templates/core/index.html` lines ~1128–1163 + associated CSS) with a **tool-first, sobriety-calculator-led** hero that matches the top tool-seeker search queries identified in GSC. The rest of the landing page stays untouched in this change.

## Why this change

| GSC query | Impressions | Position | Clicks |
|---|---|---|---|
| sobriety calculator | 32 | 83 | 0 |
| how many days sober calculator | 2 | 74 | 0 |
| sober app tracker | 9 | 61 | 0 |
| how long have i been sober | 1 | 56 | 0 |
| (current hero target: "recovery community") | — | — | — |

People search for **tools and the number** (days sober), not "community." The current hero leads with a social feed screenshot and "Recovery Is Better Together" — visually and verbally mismatched. The change moves the headline, primary CTA, and hero image to directly answer the tool-seeker's intent.

## Audience decisions locked in

1. **Primary audience:** Tool seekers (people searching "sobriety calculator", "days sober app", "sober grid alternative")
2. **Primary CTA destination:** `/sobriety-calculator/` — the existing no-signup tool
3. **Scope:** Hero section only. Trust strip, "How It Works", showcases, feature grid, FAQ, blog section, and final CTA banner all remain unchanged.

## Approved direction — "Question-Led" hero (Approach B from brainstorm)

### Final copy

**Anonymous user:**

- **H1:** *How many days sober are you?*
- **Subhead:** *Find out free. Track every day. Get an AI coach in your corner whenever you need one.*
- **Trust badges (3):**
  - `✓ Free forever`
  - `✓ Available on iOS`
  - `✓ Private & secure`
- **Primary CTA:** `Count My Days →` → `/sobriety-calculator/`
- **Secondary CTA:** `Already have an account? Sign in` (text link, smaller, below primary)

**Authenticated user:**

- **H1:** *Welcome back, {{ user.first_name|default:user.username }}.*
- **Subhead:** *Your community, your check-in, your coach — all where you left them.*
- **Trust badges:** *(removed for authenticated state)*
- **Primary CTA:** `Go to MyRecoveryCircle` → `/accounts/social-feed/` (existing behavior preserved)

### Visual treatment (right side of hero)

A **stylized HTML/CSS sobriety counter card** — no image asset, no real screenshot. Reasons: pixel control, no maintenance burden, accessible, fast to ship, looks crisp against the gradient background.

The card visually previews what the calculator returns, communicating value at a glance:

```
┌─────────────────────────────┐
│  ┌───────────────────────┐  │
│  │       DAYS SOBER      │  │  ← navy gradient header
│  │       ▓▓▓▓▓▓▓▓▓       │  │
│  │        3,003          │  │  ← large green number
│  │   8 years, 2 months   │  │
│  └───────────────────────┘  │
│                             │
│  NEXT MILESTONE             │  ← lighter footer
│  9 years                    │
│  ▓▓▓▓▓▓▓▓▓▓░░░░ 78%        │  ← progress bar
│  284 days to go             │
└─────────────────────────────┘
```

**Implementation:** Pure HTML + inline CSS in the template, no JavaScript. Uses the same navy/green palette as the existing site (`#0f2d56`, `#1e4d8b`, `#52b788`). The numbers shown are **static example values** (3,003 days), not a live calculation — this is a marketing surface, not a tool.

### Layout & responsive behavior

| Viewport | Behavior |
|---|---|
| Desktop (≥900px) | Split grid: text left (~55%), visual right (~45%). Matches current hero proportions. |
| Tablet (600–899px) | Stacked: text on top, visual below. Reduce H1 to ~2.2rem. |
| Mobile (<600px) | Stacked, single-column. H1 reduces to ~1.8rem. Visual card scales to ~80% viewport width, centered. |

The existing CSS class `.hero` and its responsive breakpoints stay — we modify content and inner structure, not the grid system.

### What's removed from the current hero

- **Old H1:** "Recovery Is Better Together" — replaced
- **Old subhead:** "Join a growing social community built by and for people in recovery..." — replaced
- **Old trust badges:** "Free to Join", "Private & Secure", "AI Coach Included", "Available on iOS" — reduced to 3 (the AI Coach one and Free-to-Join one collapse into the new wording; Available on iOS preserved)
- **Old hero image:** `feed.webp` (social feed screenshot) — replaced with HTML/CSS card
- **Old primary CTA:** "Join Free Today" → `/accounts/register/` — replaced with calculator CTA
- **Old secondary links:** "Download iOS App" + "See how it works" → both removed. iOS App and demo are still discoverable via the iOS app banner above hero and the showcases below; no need to repeat in the hero CTA group.

### What stays the same

- The iOS app banner section directly above the hero (lines ~1097–1123)
- The trust strip immediately below the hero (lines ~1168–1187)
- The `.hero` gradient background, animated `::before` overlay, and base layout grid
- All other sections of the landing page
- All structured data / JSON-LD (the hero copy doesn't appear in schema markup)

## Logged-in state design rationale

We preserve the existing pattern of "different CTA for authenticated users" because:
1. Search-driven anonymous traffic is the conversion target — they need the calculator wedge
2. Authenticated users hitting `/` are usually returning to the app — they need the fastest path to MyRecoveryCircle
3. No A/B complexity — single template, simple `{% if user.is_authenticated %}` branch

## Honesty constraints (preserved from prior cleanup)

In line with the 2026-02-19 cleanup that removed inflated claims ("1,000+ users", fake aggregateRating, "top-rated"):

- **No social proof claims** about user counts, ratings, or usage scale on the hero
- **No "trusted by [number]" framing**
- **No fabricated testimonials**
- Trust badges only state things that are factually true today

## Files affected

| File | Change |
|---|---|
| `apps/core/templates/core/index.html` | Replace hero `<section class="hero">` block (~lines 1128–1163). Update or add scoped CSS for the new visual card (within the existing `{% block extra_css %}`). |

**No other files change.** No new templates, no view changes, no model/migration changes, no JS, no new static assets, no URL changes.

## Success criteria

The change is successful if **all** of:
1. New hero renders correctly on desktop, tablet, and mobile (visual review)
2. Primary CTA navigates to `/sobriety-calculator/`
3. Anonymous and authenticated states each render their correct copy + CTA
4. No Lighthouse regression > 2 points on Performance or Accessibility
5. No JavaScript errors in browser console
6. Existing tests still pass (this change touches no Python code)

We will **not** measure conversion lift in this change — that requires A/B test infrastructure not in place. Validation that the new hero converts better than the old is a separate (much bigger) follow-up project; this is a directional bet based on the GSC data, not an experiment.

## Out of scope (explicit non-goals)

- A/B testing infrastructure
- Registration form changes (separate audit priority — Item #2)
- Shop email infrastructure (separate audit priority — Item #3)
- `noindex` of thin pages (separate audit priority — Item #4)
- Translation / i18n of new copy
- Dark-mode-specific hero treatment (existing dark mode applies to whole site uniformly)
- New imagery, illustrations, or video
- Performance optimization beyond not regressing

## Implementation hand-off notes

For the writing-plans skill:
- TDD doesn't really apply here (no Python logic) — verification is visual and via existing test suite passing
- The work is essentially one big template edit plus CSS additions
- Plan should include: read existing hero block, write new hero block with exact copy from this spec, write CSS for the new visual card, verify in browser at all three viewports, run `python3 manage.py test` to confirm no regression, commit, push, open PR
- No data migration, no env vars, no Stripe / external service changes
- Estimated effort: 3–5 hours including browser verification at three viewports

---

## Open questions

None. All design decisions are locked.

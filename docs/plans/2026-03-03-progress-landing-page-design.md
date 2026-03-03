# Progress Page as Landing Page — Design Document

**Date:** 2026-03-03
**Status:** Approved
**Goal:** Make the My Progress page the default landing page to drive check-in engagement, retention, and shareability.

---

## Overview

Replace the social feed as the default post-login landing page with a tabbed view: **My Progress** (default) and **My Feed** (AJAX-loaded). The progress tab gets an embedded full check-in form at the top and share buttons on all major sections. New users are immediately prompted to check in before seeing charts.

## Key Decisions

| Decision | Choice |
|----------|--------|
| New user experience | Force check-in first (full form shown, charts hidden until first check-in) |
| Check-in scope | Full check-in (mood, energy, craving, gratitude, challenge, goal) |
| Share targets | All major sections (milestone, streak, weekly comparison, heatmap, stats) |
| Navigation model | Tabbed: My Progress + My Feed on same page |
| Technical approach | AJAX tab loading (progress loads first, feed fetched on demand) |

---

## Design Details

### 1. Tab Bar

Sticky tab bar below the page header with two tabs:

- **My Progress** — active by default, underline indicator
- **My Feed** — loads social feed via AJAX on first click

Tab state preserved via URL hash (`#progress` / `#feed`). Direct links and browser back button work correctly.

### 2. Inline Check-in Form

Positioned at the top of the progress tab, before any charts.

**Not checked in today:** Full check-in form with:
- 6 mood emoji buttons (Struggling through Amazing)
- Energy slider (1-5)
- Craving slider (0-4)
- Gratitude text field with quick-fill tags
- Challenge and goal text fields
- Share with community toggle
- Submit button

Submits via AJAX. On success: collapses to compact summary bar, charts below refresh.

**Already checked in today:** Compact bar showing mood emoji, streak count, and Edit/Share buttons.

**New users (zero check-ins):** Full check-in form is prominent. Chart sections hidden (replaced with encouraging message) until first check-in is submitted. After submission, charts render with first data point.

### 3. Share Buttons

Small share icon button in the top-right corner of each major card:

| Section | Share Text |
|---------|------------|
| Milestone card | "I'm X days sober! Next milestone: Y days. #recovery #MyRecoveryPal" |
| Streak stat | "X-day check-in streak on MyRecoveryPal! #recovery" |
| Weekly comparison (improvement) | "My mood improved X% this week! #recovery #MyRecoveryPal" |
| Heatmap calendar | "My 90-day recovery check-in calendar #recovery #MyRecoveryPal" |
| Stats grid | "X check-ins, Y% rate, Z avg mood this month on MyRecoveryPal" |

Share options:
- **Mobile (Capacitor):** Native share sheet via `@capacitor/share`
- **Web:** Dropdown with Twitter/X, Facebook, WhatsApp, Copy Link
- **Post to Feed:** Creates a SocialPost with share text + link to user's profile

### 4. Feed Tab (AJAX Loading)

When user clicks "My Feed":
1. Tab underline animates to Feed
2. Progress content hides (`display: none`, stays in DOM)
3. First click: skeleton loader, fetch `/accounts/social-feed/fragment/`
4. Feed HTML injected into container div
5. Subsequent switches: toggle `display` only (no re-fetch)

### 5. New Endpoint: `social_feed_fragment`

Returns social feed content as an HTML fragment (no `base.html` wrapper). Reuses existing `social_feed_view` query logic. Template renders posts, sidebar, suggestions — no `<html>`, `<head>`, or nav.

### 6. Quick Check-in Endpoint Enhancement

Extend the existing `/accounts/quick-checkin/` POST endpoint to accept optional fields: `energy_level`, `craving_level`, `gratitude`, `challenge`, `goal`. Currently it only accepts `mood` and `gratitude`. This avoids creating a separate endpoint.

### 7. Configuration Changes

- `LOGIN_REDIRECT_URL` changes from `accounts:social_feed` to `accounts:progress`
- Mobile bottom tab bar "Feed" icon navigates to `/accounts/progress/#feed`

### 8. No Changes To

- Existing standalone `/accounts/daily-checkin/` page (still accessible)
- Existing social feed page at `/accounts/social-feed/` (still works independently)
- Any models or database migrations
- Chart.js configuration or visualization logic (reused as-is)

# Landing Page Conversion-Focused Redesign

**Date:** 2026-02-25
**Status:** Approved
**File:** `apps/core/templates/core/index.html`

## Problem

The current landing page is text-heavy with no product screenshots visible. Feature cards have empty icons. MyRecoveryCircle (the core social feed) and Anchor AI Coach (the premium differentiator) are mentioned but not visually showcased. Visitors can't see what the product looks like before signing up, hurting conversion.

## Approach: "Show, Don't Tell"

Replace text-heavy sections with visual proof. Put screenshots of MyRecoveryCircle and Anchor front-and-center. Reduce section count from 7 to 9 more focused sections with clear conversion flow.

## New Page Structure

### Section 1: Hero (Split Layout)
- **Left (text):** Headline "Recovery Is Better Together", subhead about social community + AI coach, trust badges (Free / Private / 24/7 AI Coach), primary CTA "Join Free Today" (green, pulsing), secondary "See how it works" link
- **Right (visual):** `feed.webp` screenshot in device-like frame showing MyRecoveryCircle
- Keeps existing gradient background

### Section 2: Social Proof / Trust Strip
- Narrow horizontal bar: "Free to join" | "Private & anonymous" | "24/7 AI support"
- Reinforces trust without taking up hero space

### Section 3: "How It Works" (3 Steps)
1. **Sign Up Free** — "Create your account in under a minute"
2. **Join MyRecoveryCircle** — "Your social feed for recovery"
3. **Get Support 24/7** — "Community + Anchor AI coach anytime"

### Section 4: MyRecoveryCircle Showcase
- Two-column: screenshot left, feature bullets right
- Heading: "MyRecoveryCircle — Your Recovery Social Feed"
- Bullets: share story, celebrate milestones, daily check-ins, follow others
- CTA: "Join the Circle" -> register
- Uses `feed.webp` or `create-post.webp`

### Section 5: Anchor AI Coach Showcase
- Reverse two-column: text left, Anchor logo right
- "NEW" badge, heading "Meet Anchor — Your 24/7 AI Recovery Coach"
- Key points: 24/7 available, 3 free messages, CBT & mindfulness, crisis resources
- CTA: "Try Anchor Free" -> /accounts/recovery-coach/
- Disclaimer: "Not a replacement for professional treatment"
- Uses `anchor-ai-coach.png`

### Section 6: Feature Grid (6 Cards with Icons)
| Feature | Icon |
|---------|------|
| Share Your Story | `fa-pen-to-square` |
| Celebrate Milestones | `fa-trophy` |
| Recovery Groups | `fa-users` |
| Daily Check-ins | `fa-calendar-check` |
| Recovery Challenges | `fa-fire` |
| Private Journal | `fa-book` |

### Section 7: FAQ Accordion
- Surface existing 6 FAQs from JSON-LD as visible accordion UI
- Same content, now human-readable on page
- Keeps structured data in `<script>` tags

### Section 8: Final CTA Banner
- Blue gradient: "Your Recovery Journey Starts Here"
- "Join Free Today" + "See how it works" secondary

### Section 9: Blog Articles (3 Cards)
- Top 3 highest-traffic only: alcohol withdrawal (22K/mo), signs of alcoholism (18K/mo), how to stop drinking (14K/mo)

## Removed Sections
- **SEO prose block** — Keywords redistributed into new sections naturally
- **8-card "Explore Resources" grid** — Too many links, dilutes conversion focus (pages still in nav/footer)
- **"About Our Mission"** — Generic; replaced by product showcases

## Assets Available
- `static/images/demo/feed.webp` — MyRecoveryCircle social feed screenshot
- `static/images/demo/create-post.webp` — Post composer screenshot
- `static/images/demo/milestone.webp` — Milestones page screenshot
- `static/images/demo/groups.webp` — Groups page screenshot
- `static/images/demo/community.webp` — Community page screenshot
- `static/images/demo/mobile.webp` — Mobile view screenshot
- `static/images/anchor-ai-coach.png` — Anchor AI Coach logo
- `static/images/logo-white.svg` — White brand logo

## SEO Preservation
- All target keywords from removed prose section woven into new section headings and copy
- JSON-LD structured data (SoftwareApplication, FAQPage, BreadcrumbList) preserved
- Meta title, description, keywords unchanged
- Blog article links preserved (reduced to top 3)
- Internal links to key pages maintained in feature cards and CTAs

## Constraints
- Single file change: `apps/core/templates/core/index.html`
- CSS stays inline in `{% block extra_css %}` (matches existing pattern)
- No new static assets needed — all images already exist
- Must work in both light mode and with existing base.html nav/footer
- Mobile responsive (existing breakpoints at 768px)

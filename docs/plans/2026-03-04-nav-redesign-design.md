# Nav Redesign — Minimal Top Bar + Smart Dropdown

**Date:** 2026-03-04
**Goal:** Reduce nav clutter, drive engagement with core loop (Feed → Check-in → Progress), and maximize Anchor AI premium conversion.
**Context:** 105 users, low engagement. Both web and iOS app.

## Desktop Nav

```
[MRP Logo]   Feed   Check-in   Progress   [🤖 Try Anchor AI]   🔔  [Avatar ▾]
```

- **3 visible links:** Feed, Check-in, Progress (the engagement loop)
- **Anchor AI button:** Gradient pill button, not a plain link. Primary CTA for premium conversion.
- **Notification bell:** Stays visible (drives re-engagement)
- **Avatar dropdown** (single organized list):
  - Profile
  - Journal
  - Groups
  - Community
  - Challenges
  - Messages
  - Milestones
  - Blog
  - Settings
  - Subscription
  - Logout

**Removed from top bar:** Blog, Journal, Groups, Challenges, Community, MyRecoveryCircle. No duplicate links between nav and dropdown.

## Mobile Slide Menu (hamburger)

Two sections instead of four:

**Quick Actions:** Feed, Check-in, Progress, Anchor AI Coach (highlighted)

**More:** Profile, Journal, Groups, Community, Challenges, Messages, Milestones, Blog, Settings, Subscription

## Mobile Bottom Nav (web, authenticated)

4 tabs:
- Feed (house icon)
- Check-in (circle-check icon)
- Anchor AI (robot icon, accent highlight)
- Profile (user icon)

## Native iOS/Android Bottom Tabs

No changes — current 5-tab bar (Feed, Coach, Check-in, Alerts, Profile) already matches this philosophy.

## Anchor AI Visual Treatment

- Gradient background (site primary colors)
- Rounded pill shape
- Subtle CSS pulse/glow animation on first page load
- Mobile: robot icon with accent color background in bottom nav

## Unauthenticated Nav

Simplify to: [Logo] [Login] [Sign Up (primary button)]

Blog/resources accessible from the landing page content, not the nav.

# Navigation Reorganization — Design

**Date:** 2026-05-26
**Status:** Approved direction; implementation plan to follow
**Trigger:** User feedback that the hamburger/user-dropdown menus are bloated and disorganized (17+ items, no grouping), and that Court Compliance — a $19.99/mo paid feature — is invisible to non-court users, killing upsell discoverability.

---

## Goal

Reorganize the four authenticated-user navigation surfaces (desktop top nav, desktop user dropdown, mobile slide-out menu, mobile bottom tab nav) into a cleaner, grouped structure. Make Court Compliance discoverable to all users (not just `tier='court'`). Drop duplicates and unused items.

## Why this change

Current state has measurable problems:

| Surface | Items | Issue |
|---|---|---|
| Desktop top nav | 5 | OK |
| Desktop user dropdown | 17 | No grouping, arbitrary order, includes duplicates |
| Mobile slide-out menu | 19 (2 sections: "Quick Actions" / "More") | Same as dropdown plus duplicates of top nav |
| Mobile bottom tab nav (web) | 4 | OK |
| iOS native bottom tab bar | 5 | OK (different from web mobile) |

Specific defects:

1. **Court Compliance is gated by `{% if user.subscription.is_court %}`** — line 303 of `base.html` for desktop dropdown, line 430 for mobile slide-out. Premium users (the primary upsell target) can't see it. Free users can't discover it. Only paying court-tier users see the link — but they already bought it.
2. **"MyRecoveryCircle" link in the dropdown** is the same URL as "Feed" in the top nav (`accounts:social_feed`). One slot wasted.
3. **"My Medallions" + "Create Medallion"** are two adjacent slots in both dropdown and slide-out for what is logically one feature.
4. **"Groups" + "Community"** are two slots for two URLs that are conceptually one community section.
5. **"Install App"** has its own pop-up banner mechanism plus the install link — both are dead weight for users who already installed.

## Decisions locked from brainstorm

| Topic | Decision |
|---|---|
| Consolidate Medallions | **Yes.** "My Medallions" + "Create Medallion" → one "Medallions" menu entry. The medallion-creator page gets a "My Saved Medallions" tab. |
| Consolidate Community | **Yes.** "Community" + "Groups" → one "Community" menu entry. Page restructure: `/accounts/community/` becomes a hub with tabs for Members / Groups / Challenges (or a similar coherent split — implementation has latitude). |
| Drop "Install App" from menu | **Yes.** Keep the existing pop-up banner. The link goes away. |
| Drop "MyRecoveryCircle" from dropdown | **Yes** (implicit — it duplicates Feed). |
| Keep "Blog" in dropdown | **Yes.** Stays for logged-in users (was offered as a possible cut, user declined). |
| Item grouping style | **Section headers** matching the existing mobile slide-out pattern (`MY RECOVERY` / `COMMUNITY` / `ACCOUNT`). |
| Court Compliance placement | **Top nav + dropdown + mobile slide-out.** Always visible to all users (not gated). Navy gradient pill in top nav matching the existing court visual language. Non-court users → `/court-ordered-meeting-tracker/` (public landing). Court-tier users → `/accounts/court/` (dashboard). |
| Top nav final item count | **6 items** (Feed, Check-in, Progress, Shop, Try Anchor AI pill, Court Compliance pill) |
| Mobile bottom tab nav | **UNCHANGED** (4 tabs). Court Compliance is reached via slide-out menu on mobile. |
| iOS native bottom tab bar | **UNCHANGED** (5 tabs). Court Compliance is reached via iOS slide-out menu. |

## Final structure

### Desktop top nav — 6 items

Order (left to right): `Feed · Check-in · Progress · Shop · [Try Anchor AI] · [Court Compliance]`

- First 4 items: existing plain styling
- "Try Anchor AI": existing purple gradient pill (`anchor-ai-cta` CSS class)
- "Court Compliance": NEW navy gradient pill — gavel icon (`fa-gavel`), navy gradient `linear-gradient(135deg, #1e4d8b 0%, #0f2d56 100%)`, white text. New CSS class: `court-cta`.

Active-state highlighting on the new Court item: when `request.path` starts with `/accounts/court/` OR equals `/court-ordered-meeting-tracker/`, add `active` class.

### Desktop user dropdown — 13 items in 3 sections

```
┌────────────────────────────────────┐
│  MY RECOVERY                       │
│  👤  Profile                       │
│  📖  Journal                       │
│  🏅  Milestones                    │
│  🎖  Medallions                    │
│  ✉   Messages                      │
│                                    │
│  COMMUNITY                         │
│  👥  Community                     │
│  🏆  Challenges  [3]               │
│  📰  Blog                          │
│                                    │
│  ACCOUNT                           │
│  👑  Subscription            [gold]│
│  ⚖   Court Compliance        [navy]│
│  ➕  Invite Friends         [green]│
│  ⚙   Settings                      │
│  ──────────                        │
│  🚪  Logout                        │
└────────────────────────────────────┘
```

**Markup pattern for section headers:**

```html
<div class="user-dropdown-section">
    <div class="user-dropdown-section-label">My Recovery</div>
    <a href="..."><i class="fas fa-user"></i> Profile</a>
    ...
</div>
```

**CSS for `.user-dropdown-section-label`:** small uppercase, ~10px font-size, color `#888`, padding `0.5rem 1rem 0.25rem`, letter-spacing `1.5px`, font-weight 600.

### Mobile slide-out menu — same 3 sections

Replaces the current "Quick Actions" + "More" split. Same item order as desktop dropdown for consistency. Same color/gradient treatment for Subscription / Court Compliance / Invite Friends.

The mobile menu has its own existing `.mobile-menu-section` + `.mobile-menu-label` classes (per `base.html:406, 440, 497`) — reuse those, just change the section labels and contents.

### Mobile bottom tab nav (web) — UNCHANGED

Still 4 tabs: Feed · Check-in · Anchor AI · Profile. No new tab for Court Compliance — it's accessible via the hamburger slide-out.

### iOS native bottom tab bar — UNCHANGED

5 tabs per CLAUDE.md (Feed, Coach, Check-in, Alerts, Profile). Court Compliance reachable via iOS slide-out menu.

## Required adjacent page changes

The menu reorg references two consolidated pages that don't exist as consolidated entities today. Both ship in the same PR:

### 1. Medallions consolidation

**Today:**
- `/accounts/my-medallions/` — list of saved medallions
- `/accounts/milestone-badge-creator/` — the creator tool

**After:**
- `/accounts/medallions/` — single page with two top-level tabs: **My Medallions** and **Create New**
- Old `/accounts/my-medallions/` and `/accounts/milestone-badge-creator/` URLs **redirect 301** to the new page with appropriate `?tab=` query param
- Single menu entry "Medallions" goes to the new URL with default `?tab=my` (or `?tab=create` if user has no saved medallions yet)

### 2. Community consolidation

**Today:**
- `/accounts/community/` — members directory
- `/accounts/groups/` — list of joinable recovery groups

**After:**
- `/accounts/community/` becomes a hub with tabs: **Members** (existing) and **Groups** (was `/accounts/groups/`)
- `/accounts/groups/` redirects 301 to `/accounts/community/?tab=groups`
- Challenges stays at `/accounts/challenges/` and stays in its own dropdown slot (it's structurally different — challenge-specific UI, not a directory)
- Single menu entry "Community" goes to `/accounts/community/` (default tab: Members)

## Files affected

| File | Change |
|---|---|
| `templates/base.html` | Top nav (lines ~204–228): add Court Compliance pill; Desktop user dropdown (lines ~262–323): replace with sectioned structure; Mobile slide-out menu (lines ~405–512): replace section labels and items to match. |
| `static/css/base-inline.css` | Add `.court-cta` class for the navy gradient pill, add `.user-dropdown-section` + `.user-dropdown-section-label` CSS. Reuse existing `.anchor-ai-cta` as the pattern reference. |
| `apps/accounts/urls.py` | Add `/accounts/medallions/` URL with new view (or alias to existing view with tab routing); add 301 redirects from old URLs. |
| `apps/accounts/views.py` | New `medallions_view` (or extend `my_medallions` / `milestone_badge_creator`) to render the tabbed page; add tab-based routing logic. |
| `apps/accounts/templates/accounts/medallions.html` | New unified template (or fold into one of the existing two and redirect the other). |
| `apps/accounts/templates/accounts/community.html` | Add tab navigation for Members / Groups. |
| `apps/accounts/templates/accounts/groups_list.html` | Either fold contents into the community hub OR keep but add breadcrumb back to community. |

## What stays the same

- All other top nav items (Feed / Check-in / Progress / Shop) — same URLs, same styling
- The notification dropdown next to the avatar
- The mobile bottom tab nav (web) — 4 tabs unchanged
- The iOS native bottom tab bar — 5 tabs unchanged
- Theme toggle button
- Footer (not a nav concern)
- Anonymous-user nav (the hamburger reorg specifically targets the authenticated experience)
- All existing URLs and view functions (consolidations add new URLs but keep the old ones as redirects)

## Success criteria

1. Logged-in user on Premium tier can see "Court Compliance" link in both top nav (navy pill) and user dropdown (under ACCOUNT section)
2. Clicking Court Compliance as a non-court user lands on `/court-ordered-meeting-tracker/`; clicking as a court-tier user lands on `/accounts/court/`
3. Dropdown has exactly 13 items in 3 labeled sections
4. Mobile slide-out has the same 3 sections as desktop dropdown
5. Old `/accounts/my-medallions/` and `/accounts/groups/` URLs 301-redirect to their consolidated equivalents
6. No console errors, no broken links, no Lighthouse regression
7. Both anonymous and authenticated states render correctly
8. iOS native app continues to work (tab bar unchanged)

## Out of scope (explicit non-goals)

- Anonymous-user nav reorg (only authenticated experience changes)
- iOS native bottom tab bar redesign
- Mobile bottom tab nav (web) redesign
- New iconography (reuse existing Font Awesome icons)
- Notification dropdown / system changes
- Theme toggle redesign
- Removing items not in the brainstorm "consolidate" list (Blog stays, etc.)
- A/B testing infrastructure
- User analytics for measuring nav-item click rates (separate observability work)

## Implementation hand-off notes

For the writing-plans skill:

- The work splits cleanly into 4 logical units: (a) Court Compliance always-visible templating, (b) Top nav navy pill + CSS, (c) Dropdown + mobile slide-out section restructure, (d) Page consolidations + 301 redirects
- TDD doesn't apply heavily here (mostly template + CSS) — verification is rendered-bytes assertions + manual visual check at desktop / tablet / mobile
- The two page consolidations (Medallions, Community) each need their own URL route + redirect + view tests
- Estimated effort: 2–3 days solo dev including manual cross-browser smoke
- No model changes, no migrations, no env vars, no Stripe / external service changes
- macOS dev: prefix all test commands with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`

## Open questions

None. All decisions locked.

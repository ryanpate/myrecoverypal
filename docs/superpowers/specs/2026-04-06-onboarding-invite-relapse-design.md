# Onboarding Simplification, Sponsor Invite, Non-Destructive Relapse Tracking

**Date:** 2026-04-06
**Goal:** Reduce signup friction (5→3 onboarding steps), enable organic growth via sponsor invites, and add compassionate relapse tracking that preserves recovery history.
**Context:** 154 users, 0 conversions. Onboarding drop-off unknown but 5 steps is too many. Users have no way to invite their sponsor/pal. Counter reset on relapse is the #1 complaint across competitor app reviews.

---

## 1. Simplified Onboarding (3 Steps)

### Purpose
Reduce onboarding from 5 steps to 3, getting users to the social feed faster. The progressive profile completion banner (already exists) handles the rest.

### Flow

**Step 1: Recovery Type**
Single-select cards: Alcohol, Drugs, Gambling, Mental Health, Other. Sets the user's primary recovery context for matching. Large tappable cards with icons, one selection required.

**Step 2: Name + Sobriety Date**
- Display name text input (required)
- "I quit on:" date picker (optional — user can skip)
- When date is entered, animate the day count immediately (emotional payoff)
- "Skip for now" link below the date picker

**Step 3: Welcome**
- "You're in!" confirmation
- If sobriety date entered: show animated day count
- Single CTA button: "Go to My Feed"
- Below: "Complete your profile later to connect with people like you"

### Implementation

The current onboarding template is `apps/accounts/templates/accounts/onboarding.html` with step logic controlled by the view. The A/B testing system has a `simplified` variant already defined.

Changes:
- Update the onboarding view to only render 3 steps when variant is `simplified`
- Make `simplified` the default variant (remove A/B randomization, always use simplified)
- Update the template to show the 3-step flow
- Set `has_completed_onboarding = True` after step 3
- The progressive profile completion banner in the social feed already prompts for: bio, avatar, location, interests, privacy settings

### What it does NOT do
- Does not collect interests during onboarding (deferred to progressive profile)
- Does not collect privacy settings (defaults to public profile, show sobriety date)
- Does not collect avatar/bio (deferred)
- Does not remove the 5-step flow code — just makes simplified the default

---

## 2. Invite Your Sponsor

### Purpose
Let users invite their sponsor (or anyone) via a shareable link. When the invitee registers, the sponsor relationship is auto-created. Leverages the existing `InviteCode` system.

### Model Change

Add `role` field to `InviteCode` in `apps/accounts/invite_models.py`:

```python
ROLE_CHOICES = (
    ('general', 'General'),
    ('sponsor', 'Sponsor'),
    ('pal', 'Recovery Pal'),
)
role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='general')
```

### Invite Generation

New view `create_sponsor_invite` at `/accounts/invite/sponsor/`:
- Requires authentication
- Creates an `InviteCode` with `role='sponsor'` and `created_by=request.user`
- Returns the invite URL: `https://www.myrecoverypal.com/accounts/register/?invite=CODE`
- Opens native share sheet (iOS) or copies to clipboard (web) with message: "I'm using MyRecoveryPal for my recovery. I'd love for you to be my sponsor on the app. Join here: [link]"

### Registration Integration

In the registration view, after successful signup:
1. Check for `invite` query param
2. Look up `InviteCode` by code
3. If found and `role == 'sponsor'`:
   - Create `SponsorRelationship(sponsor=new_user, sponsee=invite.created_by, status='pending')`
   - Create notification for inviter: "[Name] joined as your sponsor!"
   - Mark invite as used
4. If found and `role == 'pal'`:
   - Create `RecoveryPal(user1=new_user, user2=invite.created_by, status='pending')`
   - Create notification for inviter
   - Mark invite as used
5. If found and `role == 'general'`:
   - Existing behavior (just mark as used)

### UI Touchpoints

1. **Pal Dashboard** (`/accounts/pals/`) — "Invite Your Sponsor" button, prominent placement
2. **Social feed sidebar** — "Don't have a sponsor? Invite one" card (shown when user has no active sponsor)
3. **Edit profile page** — in the recovery connections section

### What it does NOT do
- Does not send email invites (share sheet handles delivery method)
- Does not create a separate landing page (registration page handles it)
- Does not force the invitee to accept the sponsor role (relationship starts as pending)

---

## 3. Non-Destructive Relapse Tracking

### Purpose
Allow users to log slips without losing their recovery history. Shows both "time in recovery" (never resets) and "current streak" (resets on slip). Framed compassionately — "progress, not perfection."

### New Model: RelapseLog

In `apps/accounts/models.py`:

```python
class RelapseLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='relapse_logs')
    relapse_date = models.DateField()
    notes = models.TextField(blank=True)
    substance = models.CharField(max_length=100, blank=True)
    trigger = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-relapse_date']
        indexes = [
            models.Index(fields=['user', '-relapse_date']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.relapse_date}"
```

### New Field on User Model

```python
recovery_start_date = models.DateField(null=True, blank=True,
    help_text="Original date recovery journey began. Never resets.")
```

The existing `sobriety_date` field becomes the "current streak start date."

### "Log a Slip" Flow

New view at `/accounts/log-slip/` (note: URL uses "slip" not "relapse" — less stigmatizing):
- Simple form: date (defaults to today), optional notes, optional trigger, optional substance
- On submit:
  1. If `recovery_start_date` is null, set it to current `sobriety_date` (preserves original date)
  2. Create `RelapseLog` entry
  3. Reset `sobriety_date` to the day after the slip date
  4. Create private `ActivityFeed` entry (visible only to user)
  5. Redirect to progress page with a supportive message: "Logging a slip takes courage. Your recovery journey continues."

### Display Changes

**Profile sobriety counter:**
- Primary: "[X] days sober" (current streak from `sobriety_date`)
- Secondary (if recovery_start_date != sobriety_date): "In recovery since [recovery_start_date]"
- No visual indication of relapse count to other users

**Progress page:**
- Current streak prominently displayed
- "Recovery Journey" section showing `recovery_start_date` and total time
- Private "Slip History" section (collapsible, only shown if relapses exist) with dates and notes
- "Log a Slip" button — subtle, not prominent, but accessible

**WidgetKit / Milestone images:**
- Use `sobriety_date` (current streak) — already how they work, no change needed

**Social feed:**
- Relapse logs do NOT appear in the public feed
- Private activity entry only visible to the user in their own activity timeline

### What it does NOT do
- Does not expose relapse history to other users
- Does not auto-post to social feed
- Does not use the word "relapse" in user-facing UI (uses "slip" throughout)
- Does not require logging a slip to reset the counter (user can also just edit sobriety_date directly)
- Does not change milestone calculations (milestones are based on current streak)

---

## Technical Notes

### New Files
- `apps/accounts/templates/accounts/onboarding_simplified.html` — 3-step onboarding template (or modify existing `onboarding.html`)
- `apps/accounts/templates/accounts/log_slip.html` — slip logging form
- `apps/accounts/migrations/0026_*.py` — RelapseLog model + recovery_start_date + InviteCode role field

### Modified Files
- `apps/accounts/models.py` — add `RelapseLog` model, `recovery_start_date` on User
- `apps/accounts/invite_models.py` — add `role` field to InviteCode
- `apps/accounts/views.py` — update onboarding view, add `create_sponsor_invite`, add `log_slip_view`, update registration to handle invite roles
- `apps/accounts/urls.py` — add new URL patterns
- `apps/accounts/templates/accounts/progress.html` — add slip history + log button
- `apps/accounts/templates/accounts/profile.html` or equivalent — show dual dates
- `apps/accounts/templates/accounts/pal_dashboard.html` — add invite sponsor button

### No premium gating
All three features are free. They drive retention and growth.

# Onboarding, Sponsor Invite, Relapse Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify onboarding (5→3 steps), add sponsor invite deep links, and add non-destructive relapse tracking with dual sobriety dates.

**Architecture:** Modify existing `onboarding_view` to default to 3-step simplified flow. Extend `InviteCode` with `role` field, hook into registration view. New `RelapseLog` model + `recovery_start_date` User field with "Log a Slip" form page.

**Tech Stack:** Django 5.0, existing InviteCode model, Capacitor Share plugin (iOS)

**Spec:** `docs/superpowers/specs/2026-04-06-onboarding-invite-relapse-design.md`

---

## File Map

**New files:**
- `apps/accounts/templates/accounts/log_slip.html` — slip logging form
- `apps/accounts/migrations/0026_*.py` — RelapseLog model + User.recovery_start_date + InviteCode.role

**Modified files:**
- `apps/accounts/models.py` — add `RelapseLog` model, add `recovery_start_date` on User
- `apps/accounts/invite_models.py` — add `role` field to InviteCode
- `apps/accounts/views.py` — simplify onboarding_view, add `create_sponsor_invite`, add `log_slip_view`, update register_view for invite roles
- `apps/accounts/urls.py` — add new URL patterns
- `apps/accounts/templates/accounts/onboarding.html` — rewrite for 3-step flow
- `apps/accounts/templates/accounts/progress.html` — add slip history + log button + dual dates
- `apps/accounts/templates/accounts/pal_dashboard.html` — add invite sponsor button

---

### Task 1: Models + Migration (RelapseLog, recovery_start_date, InviteCode.role)

**Files:**
- Modify: `apps/accounts/models.py` — add RelapseLog model + recovery_start_date on User
- Modify: `apps/accounts/invite_models.py` — add role field
- Create: `apps/accounts/migrations/0026_*.py`

- [ ] **Step 1: Add recovery_start_date to User model**

In `apps/accounts/models.py`, in the User class (around line 62, near `sobriety_date`), add:

```python
    recovery_start_date = models.DateField(
        null=True, blank=True,
        help_text="Original date recovery journey began. Never resets on relapse."
    )
```

- [ ] **Step 2: Add RelapseLog model**

After the `DailyRecoveryThought` model (added in previous plan), add:

```python
class RelapseLog(models.Model):
    """Tracks slips/relapses without destroying recovery history."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='relapse_logs')
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

- [ ] **Step 3: Add role field to InviteCode**

In `apps/accounts/invite_models.py`, in the InviteCode class (around line 158, after the `notes` field), add:

```python
    # Invite role — determines relationship created on registration
    ROLE_CHOICES = (
        ('general', 'General'),
        ('sponsor', 'Sponsor'),
        ('pal', 'Recovery Pal'),
    )
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default='general',
        help_text="Relationship to create when invitee registers"
    )
```

- [ ] **Step 4: Generate and run migration**

```bash
python3 manage.py makemigrations accounts --name relapse_invite_role
python3 manage.py migrate accounts
python3 manage.py check
```

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/models.py apps/accounts/invite_models.py apps/accounts/migrations/0026_*
git commit -m "feat: add RelapseLog model, recovery_start_date, InviteCode role"
```

---

### Task 2: Simplify Onboarding to 3 Steps

**Files:**
- Modify: `apps/accounts/views.py` — rewrite onboarding_view
- Modify: `apps/accounts/templates/accounts/onboarding.html` — 3-step template

- [ ] **Step 1: Rewrite onboarding_view**

In `apps/accounts/views.py`, replace the `onboarding_view` function (starts at line 152). The new version has 3 steps + completion:

```python
@login_required
def onboarding_view(request):
    """
    Simplified 3-step onboarding wizard.
    Step 1: Recovery Type
    Step 2: Name + Sobriety Date
    Step 3: Welcome / Complete
    """
    from .models import RECOVERY_STAGE_CHOICES

    user = request.user

    if user.has_completed_onboarding:
        return redirect('accounts:progress')

    ABTestingService.track_conversion(user, 'onboarding_flow', 'started_onboarding')

    step = int(request.GET.get('step', 1))
    step = max(1, min(step, 3))

    if request.method == 'POST':
        if step == 1:
            # Recovery Type
            recovery_stage = request.POST.get('recovery_stage', '').strip()
            if recovery_stage:
                user.recovery_stage = recovery_stage
                user.save(update_fields=['recovery_stage'])
            ABTestingService.track_conversion(user, 'onboarding_flow', 'completed_step_1')
            return redirect(reverse('accounts:onboarding') + '?step=2')

        elif step == 2:
            # Name + Sobriety Date
            first_name = request.POST.get('first_name', '').strip()
            sobriety_date = request.POST.get('sobriety_date', '').strip()

            if first_name:
                user.first_name = first_name[:30]

            if sobriety_date:
                try:
                    from datetime import datetime
                    parsed_date = datetime.strptime(sobriety_date, '%Y-%m-%d').date()
                    user.sobriety_date = parsed_date
                    # Set recovery_start_date if not already set
                    if not user.recovery_start_date:
                        user.recovery_start_date = parsed_date
                except ValueError:
                    pass

            user.save()
            ABTestingService.track_conversion(user, 'onboarding_flow', 'completed_step_2')
            return redirect(reverse('accounts:onboarding') + '?step=3')

        elif step == 3:
            # Complete
            user.has_completed_onboarding = True
            user.save(update_fields=['has_completed_onboarding'])
            ABTestingService.track_conversion(user, 'onboarding_flow', 'completed_onboarding')
            messages.success(request, "Welcome to MyRecoveryPal!")
            return redirect('accounts:social_feed')

    # GET — build context
    context = {
        'step': step,
        'total_steps': 3,
        'progress_percent': int((min(step, 3) / 3) * 100),
        'recovery_stage_choices': RECOVERY_STAGE_CHOICES if hasattr(user, 'recovery_stage') else [],
        'days_sober': user.get_days_sober() if user.sobriety_date else None,
    }

    return render(request, 'accounts/onboarding.html', context)
```

IMPORTANT: The old function is ~200 lines (lines 152-360). Replace the ENTIRE function. Read the file to find the exact end of the function (look for the next `def` or `@login_required` after it).

- [ ] **Step 2: Rewrite onboarding.html template**

Read the current `apps/accounts/templates/accounts/onboarding.html` and replace its content. The new template should have 3 steps:

**Step 1 — Recovery Type:** Large tappable cards for each recovery type (Alcohol, Drugs, Gambling, Mental Health, Other). Radio inputs styled as cards. Submit button "Continue".

**Step 2 — Name + Sobriety Date:** Text input for display name (first_name). Date picker for sobriety date with "I quit on:" label. When date changes, show animated day count via JS. "Skip for now" link below date picker. Submit button "Continue".

**Step 3 — Welcome:** "You're in!" heading. If sobriety date exists, show day count animation. Single CTA: "Go to My Feed" (submits form to complete onboarding). Subtext: "Complete your profile later."

Style it using the existing onboarding CSS classes (`.onboarding-container`, `.onboarding-card`, `.step-header`, etc.) from the current template. Keep the progress dots (3 instead of 5).

- [ ] **Step 3: Verify**

```bash
python3 manage.py check
```

- [ ] **Step 4: Commit**

```bash
git add apps/accounts/views.py apps/accounts/templates/accounts/onboarding.html
git commit -m "feat: simplify onboarding to 3 steps (recovery type, name+date, welcome)"
```

---

### Task 3: Sponsor Invite Flow

**Files:**
- Modify: `apps/accounts/views.py` — add `create_sponsor_invite` view, update `register_view`
- Modify: `apps/accounts/urls.py` — add invite URL
- Modify: `apps/accounts/templates/accounts/pal_dashboard.html` — add invite button

- [ ] **Step 1: Add create_sponsor_invite view**

At the end of `apps/accounts/views.py` (before `milestone_image_view`), add:

```python
@login_required
def create_sponsor_invite(request):
    """Generate an invite link with sponsor role and return share data."""
    from .invite_models import InviteCode

    role = request.GET.get('role', 'sponsor')
    if role not in ('sponsor', 'pal'):
        role = 'sponsor'

    # Create invite code with role
    invite = InviteCode.objects.create(
        created_by=request.user,
        role=role,
        max_uses=1,
        uses_remaining=1,
        notes=f'{role.title()} invite from {request.user.username}',
    )

    site_url = getattr(settings, 'SITE_URL', 'https://www.myrecoverypal.com')
    invite_url = f'{site_url}/accounts/register/?invite={invite.code}'

    if role == 'sponsor':
        share_text = (
            f"I'm using MyRecoveryPal for my recovery journey. "
            f"I'd love for you to be my sponsor on the app. "
            f"Join here: {invite_url}"
        )
    else:
        share_text = (
            f"I'm using MyRecoveryPal for my recovery. "
            f"Want to be recovery pals? Join here: {invite_url}"
        )

    return JsonResponse({
        'success': True,
        'invite_url': invite_url,
        'invite_code': invite.code,
        'share_text': share_text,
        'role': role,
    })
```

- [ ] **Step 2: Update register_view to handle invite roles**

In `apps/accounts/views.py`, inside `register_view` (around line 41), find the section AFTER the user is created and logged in (around line 79-93, after `login(request, user)`). Add role-based relationship creation:

```python
                # Handle invite code role-based relationship
                invite_code_str = request.POST.get('invite_code', '') or request.GET.get('invite', '')
                if invite_code_str:
                    try:
                        from .invite_models import InviteCode
                        invite = InviteCode.objects.get(code=invite_code_str, status='active')
                        if invite.created_by and invite.role == 'sponsor':
                            SponsorRelationship.objects.get_or_create(
                                sponsor=user,
                                sponsee=invite.created_by,
                                defaults={'status': 'pending'}
                            )
                            create_notification(
                                recipient=invite.created_by,
                                sender=user,
                                notification_type='sponsor_request',
                                message=f'{user.first_name or user.username} joined as your sponsor!',
                                link=f'/accounts/profile/{user.username}/',
                            )
                        elif invite.created_by and invite.role == 'pal':
                            RecoveryPal.objects.get_or_create(
                                user1=min(user, invite.created_by, key=lambda u: u.id),
                                user2=max(user, invite.created_by, key=lambda u: u.id),
                                defaults={'status': 'pending'}
                            )
                            create_notification(
                                recipient=invite.created_by,
                                sender=user,
                                notification_type='pal_request',
                                message=f'{user.first_name or user.username} joined as your recovery pal!',
                                link=f'/accounts/profile/{user.username}/',
                            )
                        # Mark invite as used
                        invite.use_code(user)
                    except (InviteCode.DoesNotExist, Exception):
                        pass  # Invalid invite code — continue registration normally
```

This needs to go in BOTH registration paths (invite-only mode AND open registration mode). Read the view carefully — there are two `if form.is_valid()` blocks. Add it to both, after the `login(request, user)` call.

NOTE: Check if `SponsorRelationship`, `RecoveryPal`, and `create_notification` are already imported. If not, add the imports inside the block.

- [ ] **Step 3: Add URL pattern**

In `apps/accounts/urls.py`, add:

```python
    path('invite/sponsor/', views.create_sponsor_invite, name='create_sponsor_invite'),
```

- [ ] **Step 4: Add invite button to pal_dashboard.html**

Read `apps/accounts/templates/accounts/pal_dashboard.html`. Find a prominent location (near the top, or next to existing "Find a Sponsor" content). Add:

```html
<!-- Invite Your Sponsor -->
<div style="background: linear-gradient(135deg, var(--primary-dark), var(--primary-light)); border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem; color: white; text-align: center;">
    <h3 style="color: white; margin-bottom: 0.5rem; font-size: 1.2rem;">
        <i class="fas fa-user-tie" aria-hidden="true"></i> Invite Your Sponsor
    </h3>
    <p style="opacity: 0.9; margin-bottom: 1rem; font-size: 0.95rem;">
        Send your sponsor an invite link to connect on MyRecoveryPal.
    </p>
    <button onclick="inviteSponsor()" style="background: var(--accent-green); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 50px; font-weight: 600; cursor: pointer; font-size: 1rem;">
        <i class="fas fa-share-alt" aria-hidden="true"></i> Send Invite Link
    </button>
</div>

<script>
function inviteSponsor() {
    fetch('/accounts/invite/sponsor/?role=sponsor')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.success) return;

            if (window.MRPNative && window.MRPNative.share) {
                window.MRPNative.share('Invite to MyRecoveryPal', data.share_text, data.invite_url);
                return;
            }

            if (navigator.share) {
                navigator.share({ title: 'Invite to MyRecoveryPal', text: data.share_text, url: data.invite_url }).catch(function() {});
                return;
            }

            // Fallback: copy to clipboard
            navigator.clipboard.writeText(data.invite_url).then(function() {
                alert('Invite link copied to clipboard!');
            });
        });
}
</script>
```

- [ ] **Step 5: Verify**

```bash
python3 manage.py check
```

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/views.py apps/accounts/urls.py apps/accounts/templates/accounts/pal_dashboard.html
git commit -m "feat: sponsor invite flow with deep-link role-based registration"
```

---

### Task 4: Non-Destructive Relapse Tracking ("Log a Slip")

**Files:**
- Modify: `apps/accounts/views.py` — add `log_slip_view`
- Create: `apps/accounts/templates/accounts/log_slip.html`
- Modify: `apps/accounts/urls.py` — add URL
- Modify: `apps/accounts/templates/accounts/progress.html` — add slip history + log button + dual dates

- [ ] **Step 1: Add log_slip_view**

At the end of `apps/accounts/views.py` (before `milestone_image_view`), add:

```python
@login_required
def log_slip_view(request):
    """Log a slip/relapse without destroying recovery history."""
    from .models import RelapseLog, ActivityFeed

    user = request.user

    if request.method == 'POST':
        slip_date_str = request.POST.get('slip_date', '').strip()
        notes = request.POST.get('notes', '').strip()
        substance = request.POST.get('substance', '').strip()
        trigger = request.POST.get('trigger', '').strip()

        if not slip_date_str:
            messages.error(request, 'Please enter the date of the slip.')
            return redirect('accounts:log_slip')

        try:
            from datetime import datetime
            slip_date = datetime.strptime(slip_date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect('accounts:log_slip')

        # Preserve original recovery start date
        if user.sobriety_date and not user.recovery_start_date:
            user.recovery_start_date = user.sobriety_date

        # Create relapse log
        RelapseLog.objects.create(
            user=user,
            relapse_date=slip_date,
            notes=notes,
            substance=substance,
            trigger=trigger,
        )

        # Reset current streak to day after slip
        from datetime import timedelta
        user.sobriety_date = slip_date + timedelta(days=1)
        user.save(update_fields=['sobriety_date', 'recovery_start_date'])

        # Private activity entry
        ActivityFeed.objects.create(
            user=user,
            activity_type='check_in_posted',
            title='Logged a slip',
            description='Continuing the recovery journey.',
        )

        messages.success(
            request,
            'Logging a slip takes courage. Your recovery journey continues.'
        )
        return redirect('accounts:progress')

    context = {
        'today': timezone.now().date(),
        'days_sober': user.get_days_sober(),
    }
    return render(request, 'accounts/log_slip.html', context)
```

- [ ] **Step 2: Create log_slip.html template**

Create `apps/accounts/templates/accounts/log_slip.html`:

```html
{% extends 'base.html' %}

{% block title %}Log a Slip - MyRecoveryPal{% endblock %}

{% block content %}
<div style="max-width: 600px; margin: 100px auto 2rem; padding: 0 1rem;">
    <div style="text-align: center; margin-bottom: 2rem;">
        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;"><i class="fas fa-hand-holding-heart" aria-hidden="true" style="color: var(--primary-light);"></i></div>
        <h1 style="color: var(--primary-dark); font-size: 1.8rem; margin-bottom: 0.5rem;">Log a Slip</h1>
        <p style="color: #666; font-size: 1.05rem; line-height: 1.6;">
            Progress, not perfection. Logging a slip is a sign of honesty and strength.
            Your recovery journey continues.
        </p>
    </div>

    <div style="background: white; border-radius: 16px; padding: 2rem; box-shadow: 0 2px 12px rgba(0,0,0,0.08);">
        <form method="post" action="{% url 'accounts:log_slip' %}">
            {% csrf_token %}

            <div style="margin-bottom: 1.5rem;">
                <label for="slip_date" style="display: block; font-weight: 600; color: var(--primary-dark); margin-bottom: 0.5rem;">When did the slip happen?</label>
                <input type="date" name="slip_date" id="slip_date" value="{{ today|date:'Y-m-d' }}" max="{{ today|date:'Y-m-d' }}" required
                       style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 1rem;">
            </div>

            <div style="margin-bottom: 1.5rem;">
                <label for="substance" style="display: block; font-weight: 600; color: var(--primary-dark); margin-bottom: 0.5rem;">What was involved? <span style="font-weight: 400; color: #999;">(optional)</span></label>
                <input type="text" name="substance" id="substance" placeholder="e.g., alcohol, pills"
                       style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 1rem;">
            </div>

            <div style="margin-bottom: 1.5rem;">
                <label for="trigger" style="display: block; font-weight: 600; color: var(--primary-dark); margin-bottom: 0.5rem;">What triggered it? <span style="font-weight: 400; color: #999;">(optional)</span></label>
                <input type="text" name="trigger" id="trigger" placeholder="e.g., stress, social event, loneliness"
                       style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 1rem;">
            </div>

            <div style="margin-bottom: 1.5rem;">
                <label for="notes" style="display: block; font-weight: 600; color: var(--primary-dark); margin-bottom: 0.5rem;">Notes to yourself <span style="font-weight: 400; color: #999;">(optional, private)</span></label>
                <textarea name="notes" id="notes" rows="3" placeholder="What would you do differently? What did you learn?"
                          style="width: 100%; padding: 0.75rem; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 1rem; resize: vertical;"></textarea>
            </div>

            <div style="background: #fff3cd; border-radius: 10px; padding: 1rem; margin-bottom: 1.5rem; font-size: 0.9rem; color: #856404;">
                <i class="fas fa-lock" aria-hidden="true"></i> <strong>This is completely private.</strong> Only you can see your slip history. It will not appear on your profile or in the social feed.
            </div>

            <button type="submit" style="width: 100%; padding: 0.875rem; background: var(--primary-dark); color: white; border: none; border-radius: 50px; font-weight: 600; font-size: 1.05rem; cursor: pointer;">
                Log Slip &amp; Continue My Journey
            </button>

            <div style="text-align: center; margin-top: 1rem;">
                <a href="{% url 'accounts:progress' %}" style="color: #999; text-decoration: none; font-size: 0.9rem;">Cancel</a>
            </div>
        </form>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Add URL pattern**

In `apps/accounts/urls.py`, add:

```python
    path('log-slip/', views.log_slip_view, name='log_slip'),
```

- [ ] **Step 4: Update progress.html with dual dates + slip history + log button**

Read `apps/accounts/templates/accounts/progress.html`. Find the sobriety counter section (where `days_sober` is displayed). Make these additions:

**A. Dual date display:** Below the main counter, if `recovery_start_date` exists and differs from `sobriety_date`:

```html
{% if user.recovery_start_date and user.recovery_start_date != user.sobriety_date %}
<p style="color: #666; font-size: 0.9rem; margin-top: 0.5rem;">
    <i class="fas fa-calendar-alt" aria-hidden="true"></i> In recovery since {{ user.recovery_start_date|date:"N j, Y" }}
</p>
{% endif %}
```

**B. "Log a Slip" link:** Add a subtle link somewhere on the progress page (below the milestone section or at the bottom):

```html
<div style="text-align: center; margin: 2rem 0; padding: 1rem; border-top: 1px solid #eee;">
    <a href="{% url 'accounts:log_slip' %}" style="color: #999; text-decoration: none; font-size: 0.9rem;">
        <i class="fas fa-pen-to-square" aria-hidden="true"></i> Had a slip? Log it privately
    </a>
</div>
```

**C. Slip history (private):** After the existing charts/stats section, if the user has relapses:

```html
{% if relapse_logs %}
<div style="margin-top: 2rem;">
    <h3 style="color: var(--primary-dark); font-size: 1.1rem; margin-bottom: 1rem; cursor: pointer;" onclick="document.getElementById('slipHistory').style.display = document.getElementById('slipHistory').style.display === 'none' ? 'block' : 'none'">
        <i class="fas fa-history" aria-hidden="true"></i> Slip History ({{ relapse_logs|length }}) <i class="fas fa-chevron-down" style="font-size: 0.8rem;"></i>
    </h3>
    <div id="slipHistory" style="display: none;">
        {% for log in relapse_logs %}
        <div style="background: #f8f9fa; border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem; border-left: 3px solid var(--primary-light);">
            <div style="font-weight: 600; color: var(--primary-dark);">{{ log.relapse_date|date:"N j, Y" }}</div>
            {% if log.trigger %}<div style="color: #666; font-size: 0.9rem; margin-top: 0.25rem;">Trigger: {{ log.trigger }}</div>{% endif %}
            {% if log.notes %}<div style="color: #555; font-size: 0.9rem; margin-top: 0.25rem;">{{ log.notes }}</div>{% endif %}
        </div>
        {% endfor %}
    </div>
</div>
{% endif %}
```

**D. Pass relapse_logs in the view context:**

In `apps/accounts/views.py`, inside `progress_view` (around line 1000), add to the context:

```python
    from apps.accounts.models import RelapseLog
    relapse_logs = RelapseLog.objects.filter(user=request.user)[:20]
```

And add `'relapse_logs': relapse_logs,` to the context dict.

- [ ] **Step 5: Verify**

```bash
python3 manage.py check
```

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/views.py apps/accounts/templates/accounts/log_slip.html apps/accounts/templates/accounts/progress.html apps/accounts/urls.py
git commit -m "feat: non-destructive relapse tracking with Log a Slip form"
```

---

### Task 5: Final Verification + Deploy

- [ ] **Step 1: Django check**

```bash
python3 manage.py check
```

- [ ] **Step 2: Collect static**

```bash
rm -rf staticfiles && python3 manage.py collectstatic --noinput
```

- [ ] **Step 3: Test locally**

1. Visit `/accounts/onboarding/` — should show 3-step flow
2. Visit `/accounts/invite/sponsor/` (logged in) — should return JSON with invite URL
3. Visit `/accounts/log-slip/` — should show slip form
4. Visit `/accounts/progress/` — should show "Had a slip?" link at bottom

- [ ] **Step 4: Push to deploy**

```bash
git push origin main
```

- [ ] **Step 5: Verify Railway deploy**

Check all services show SUCCESS with latest commit hash.

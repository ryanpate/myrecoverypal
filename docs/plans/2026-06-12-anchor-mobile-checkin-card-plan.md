# Phase 1a.1: Anchor card on AJAX/mobile check-in — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Offer Anchor on the AJAX/mobile check-in (`quick_checkin`) after a struggling/high-craving check-in, closing the 1a blind spot where mobile/hybrid-landing users never saw the contextual card.

**Architecture:** Add `needs_support` + `coach_url` to `quick_checkin`'s success JSON; reveal a hidden inline Anchor prompt in the hybrid-landing "checked in" state when `needs_support` is true. Reuses 1a's `coach_start_from_checkin` endpoint — no migration, no coach-logic change.

**Tech Stack:** Django 5.0, vanilla JS in a Django template.

**Spec:** `docs/plans/2026-06-12-anchor-mobile-checkin-card-design.md`

**Test command:** `python3 manage.py test apps.accounts.test_anchor_conversion -v2` (ephemeral DB; local sqlite stale). The file `apps/accounts/test_anchor_conversion.py` exists (from 1a) with helper `make_free_user` and imports (`TestCase`, `override_settings`, `patch`, models) at the top — APPEND.

**Facts:** `quick_checkin` (`accounts:quick_checkin`, URL `quick-checkin/`) requires only `mood` in POST (`craving_level`/`energy_level`/etc. optional, `energy_level` defaults to 3); it returns JSON `{'success': True, 'mood', 'mood_display', 'message', 'shared_to_feed'}` at views.py ~954-960. `reverse` is already imported in views.py. `DailyCheckIn.needs_support()` exists (1a).

---

### Task 1: Backend — add `needs_support` + `coach_url` to the success JSON

**Files:**
- Modify: `apps/accounts/views.py` (`quick_checkin` success `JsonResponse`)
- Modify: `apps/accounts/test_anchor_conversion.py` (append a class)

- [ ] **Step 1: Write the failing tests** — APPEND to `apps/accounts/test_anchor_conversion.py`:

```python
@override_settings(SECURE_SSL_REDIRECT=False, PREPEND_WWW=False, ALLOWED_HOSTS=['*'])
class QuickCheckinCardTest(TestCase):
    def _post(self, user, mood, craving):
        from django.urls import reverse
        self.client.force_login(user)
        return self.client.post(reverse('accounts:quick_checkin'),
                                {'mood': mood, 'craving_level': craving})

    def test_hard_checkin_returns_needs_support_and_coach_url(self):
        from django.urls import reverse
        user = make_free_user('qc1')
        resp = self._post(user, 1, 4)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['needs_support'])
        checkin = DailyCheckIn.objects.get(user=user)
        self.assertEqual(
            data['coach_url'],
            reverse('accounts:coach_start_from_checkin', args=[checkin.id]))

    def test_calm_checkin_needs_support_false(self):
        user = make_free_user('qc2')
        resp = self._post(user, 5, 0)
        data = resp.json()
        self.assertFalse(data['needs_support'])
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.QuickCheckinCardTest -v2`
Expected: FAIL — `KeyError: 'needs_support'` (the key isn't in the response yet).

- [ ] **Step 3: Implement** — in `apps/accounts/views.py`, the `quick_checkin` success response (currently):

```python
    return JsonResponse({
        'success': True,
        'mood': mood,
        'mood_display': checkin.get_mood_display(),
        'message': 'Check-in complete! 🌟',
        'shared_to_feed': share_to_feed,
    })
```

becomes:

```python
    return JsonResponse({
        'success': True,
        'mood': mood,
        'mood_display': checkin.get_mood_display(),
        'message': 'Check-in complete! 🌟',
        'shared_to_feed': share_to_feed,
        'needs_support': checkin.needs_support(),
        'coach_url': reverse('accounts:coach_start_from_checkin', args=[checkin.id]),
    })
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.QuickCheckinCardTest -v2`
Expected: PASS (2 tests). Also run the whole file (`python3 manage.py test apps.accounts.test_anchor_conversion -v1`) → expect 24 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/views.py apps/accounts/test_anchor_conversion.py
git commit -m "feat(checkin): quick_checkin returns needs_support + coach_url"
```

---

### Task 2: Frontend — reveal the inline Anchor prompt

**Files:**
- Modify: `apps/accounts/templates/accounts/hybrid_landing.html` (the `#checkin-done` block + the quick-checkin success handler)

- [ ] **Step 1: Add the hidden prompt to the "checked in" state**

In `apps/accounts/templates/accounts/hybrid_landing.html`, the `#checkin-done` block currently reads:

```html
                <div id="checkin-done" style="display: none;">
                    <div class="checkin-done">
                        <div class="checkin-done-emoji" id="checkin-mood-emoji"></div>
                        <div class="checkin-done-text">You've checked in today!</div>
                        <a href="{% url 'accounts:daily_checkin' %}" class="checkin-done-link">
                            Add more details →
                        </a>
                    </div>
                </div>
```

Insert the hidden Anchor prompt immediately AFTER the `</a>` (the "Add more details" link) and BEFORE the closing `</div></div>`:

```html
                        <a href="{% url 'accounts:daily_checkin' %}" class="checkin-done-link">
                            Add more details →
                        </a>
                        <div id="checkin-anchor-prompt" style="display:none; border:1px solid #1e4d8b; background:#f4f8fc; border-radius:12px; padding:14px; margin-top:14px; text-align:center;">
                            <div style="color:#1e4d8b; font-weight:600; margin-bottom:6px;">Today sounds heavy.</div>
                            <a id="checkin-anchor-link" href="#" style="background:#1e4d8b; color:#fff; padding:9px 18px; border-radius:8px; text-decoration:none; font-weight:600; display:inline-block;">
                                Talk it through with Anchor
                            </a>
                        </div>
```

- [ ] **Step 2: Reveal it in the success handler**

In the same file, the quick-checkin success handler currently does:

```javascript
            if (data.success) {
                showCheckedInState(selectedMood);
                // Show a brief success animation
                checkinWidget.style.transform = 'scale(1.02)';
                setTimeout(() => {
                    checkinWidget.style.transform = 'scale(1)';
                }, 200);
            } else if (data.already_checked_in) {
```

Add the reveal immediately after the `showCheckedInState(selectedMood);` line:

```javascript
            if (data.success) {
                showCheckedInState(selectedMood);
                if (data.needs_support && data.coach_url) {
                    const anchorLink = document.getElementById('checkin-anchor-link');
                    const anchorPrompt = document.getElementById('checkin-anchor-prompt');
                    if (anchorLink && anchorPrompt) {
                        anchorLink.href = data.coach_url;
                        anchorPrompt.style.display = 'block';
                    }
                }
                // Show a brief success animation
                checkinWidget.style.transform = 'scale(1.02)';
                setTimeout(() => {
                    checkinWidget.style.transform = 'scale(1)';
                }, 200);
            } else if (data.already_checked_in) {
```

- [ ] **Step 3: Verify the template renders**

Run: `python3 manage.py shell -c "from django.template.loader import get_template; get_template('accounts/hybrid_landing.html'); print('RENDER_OK')"`
Expected: `RENDER_OK` appears (ignore email-config log noise).

- [ ] **Step 4: Commit**

```bash
git add apps/accounts/templates/accounts/hybrid_landing.html
git commit -m "feat(checkin): reveal Anchor prompt on hard quick-checkin (mobile/landing)"
```

---

### Task 3: Verification

- [ ] **Step 1: Full anchor suite**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion -v1`
Expected: PASS (24 tests — the prior 22 plus the 2 new `QuickCheckinCardTest`).

- [ ] **Step 2: System check + migration drift**

Run: `python3 manage.py check` → `System check identified no issues`.
Run: `python3 manage.py makemigrations --check --dry-run` → `No changes detected` (this slice has no model changes).

- [ ] **Step 3: Manual verification note (no JS unit tests in this template)**

Manual check before/after deploy: on the hybrid landing (and in the mobile app, which loads the same page), submit a quick check-in with a low mood or high craving → the "Today sounds heavy / Talk it through with Anchor" prompt appears in the checked-in state and its button opens the coach (`coach_start_from_checkin`). A calm check-in shows no prompt.

This plan is implemented on a feature branch; integration/merge is handled by the finishing-a-development-branch skill after the final review (do NOT push to main from within the tasks).

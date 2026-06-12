# Phase 1b: Inline check-in on the home — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the progress home's link-out check-in prompt with an inline mood+craving AJAX widget (reusing `quick_checkin`), reveal the contextual Anchor card inline on hard check-ins, and delete the orphaned `hybrid_landing` page.

**Architecture:** The home (`progress.html`) already toggles `#checkinFormCard` vs `#checkinDoneBar` by `data-has-checkin`. We swap the form card's *contents* for an inline widget that POSTs to `quick_checkin` (which already returns `needs_support`/`coach_url`; we add `current_streak`), then update the done bar + reveal the Anchor card in JS without a page nav.

**Tech Stack:** Django 5.0, vanilla JS in a Django template.

**Spec:** `docs/plans/2026-06-12-inline-checkin-home-design.md`

**Test command:** `python3 manage.py test apps.accounts.test_anchor_conversion -v2` (ephemeral DB; local sqlite stale). The file `apps/accounts/test_anchor_conversion.py` (from 1a/1a.1) has helpers `make_free_user`, `make_checkin` and imports (`TestCase`, `override_settings`, `patch`, models, `reverse` per-method) — APPEND.

**Facts:** Home = `accounts:progress` (`progress_view` → `progress.html`). `quick_checkin` (`accounts:quick_checkin`) needs only `mood`; returns `{'success', 'mood', 'mood_display', 'message', 'shared_to_feed', 'needs_support', 'coach_url'}` (views.py ~954). `reverse` already imported in views.py. `get_checkin_streak()` exists on User (models.py:169). Mood emoji: 1😰 2😔 3😐 4😊 5😄 6🌟. Craving: 0 None…4 Intense. `{{ csrf_token }}` is available in the template.

---

### Task 1: Backend — `quick_checkin` returns `current_streak`

**Files:**
- Modify: `apps/accounts/views.py` (`quick_checkin` success JSON)
- Modify: `apps/accounts/test_anchor_conversion.py` (extend `QuickCheckinCardTest`)

- [ ] **Step 1: Write the failing test** — APPEND a method to the existing `QuickCheckinCardTest` class in `apps/accounts/test_anchor_conversion.py`:

```python
    def test_response_includes_current_streak(self):
        user = make_free_user('qc3')
        resp = self._post(user, 4, 0)
        data = resp.json()
        self.assertIn('current_streak', data)
        self.assertEqual(data['current_streak'], 1)
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.QuickCheckinCardTest.test_response_includes_current_streak -v2`
Expected: FAIL — `KeyError: 'current_streak'` / `'current_streak' not found`.

- [ ] **Step 3: Implement** — in `apps/accounts/views.py`, the `quick_checkin` success `JsonResponse` (which currently ends with the `needs_support`/`coach_url` keys from 1a.1) gains one more key:

```python
        'needs_support': checkin.needs_support(),
        'coach_url': reverse('accounts:coach_start_from_checkin', args=[checkin.id]),
        'current_streak': request.user.get_checkin_streak(),
    })
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.QuickCheckinCardTest -v2`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/views.py apps/accounts/test_anchor_conversion.py
git commit -m "feat(checkin): quick_checkin returns current_streak"
```

---

### Task 2: Home template — inline widget markup, done-bar ids, Anchor prompt

**Files:**
- Modify: `apps/accounts/templates/accounts/progress.html` (the `#checkinFormCard`/`#checkinDoneBar` block + a small CSS addition)
- Modify: `apps/accounts/test_anchor_conversion.py` (append a class)

- [ ] **Step 1: Write the failing tests** — APPEND to `apps/accounts/test_anchor_conversion.py`:

```python
@override_settings(SECURE_SSL_REDIRECT=False, PREPEND_WWW=False, ALLOWED_HOSTS=['*'])
class ProgressHomeWidgetTest(TestCase):
    def test_inline_mood_widget_present(self):
        from django.urls import reverse
        user = make_free_user('ph1')
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:progress'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-mood="1"')          # inline mood buttons
        self.assertContains(resp, 'id="inlineCheckinSubmit"')  # inline submit
        self.assertContains(resp, 'id="doneStreakBadge"')   # done-bar streak badge always in DOM
        self.assertContains(resp, 'id="homeAnchorPrompt"')  # hidden anchor prompt present

    def test_done_bar_marked_checked_in_when_checked_in(self):
        from django.urls import reverse
        user = make_free_user('ph2')
        make_checkin(user, mood=4, craving=0)  # today
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:progress'))
        self.assertContains(resp, 'data-has-checkin="true"')
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.ProgressHomeWidgetTest -v2`
Expected: FAIL — `test_inline_mood_widget_present` fails (no `data-mood`/`inlineCheckinSubmit`/`doneStreakBadge`/`homeAnchorPrompt` yet). The checked-in test should already pass.

- [ ] **Step 3: Replace the `#checkinFormCard` contents** — in `apps/accounts/templates/accounts/progress.html`, replace this block:

```html
    <div class="checkin-prompt-bar" id="checkinFormCard" style="display:none;">
        <div class="prompt-left">
            <div class="prompt-icon"><i class="fas fa-sun" aria-hidden="true"></i></div>
            <div>
                <div class="prompt-text">How are you feeling today?</div>
                <div class="prompt-sub">Check in to update your progress</div>
            </div>
        </div>
        <a href="{% url 'accounts:daily_checkin' %}" class="btn-checkin-prompt">
            <i class="fas fa-circle-check" aria-hidden="true"></i> Check In
        </a>
    </div>
```

with:

```html
    <div class="checkin-prompt-bar" id="checkinFormCard" style="display:none;">
        <div class="inline-checkin">
            <div class="prompt-text">How are you feeling today?</div>
            <div class="inline-mood-row" id="inlineMoodRow">
                <button type="button" class="inline-mood-btn" data-mood="1" aria-label="Struggling">😰</button>
                <button type="button" class="inline-mood-btn" data-mood="2" aria-label="Down">😔</button>
                <button type="button" class="inline-mood-btn" data-mood="3" aria-label="Okay">😐</button>
                <button type="button" class="inline-mood-btn" data-mood="4" aria-label="Good">😊</button>
                <button type="button" class="inline-mood-btn" data-mood="5" aria-label="Great">😄</button>
                <button type="button" class="inline-mood-btn" data-mood="6" aria-label="Amazing">🌟</button>
            </div>
            <div class="inline-craving-row" id="inlineCravingRow">
                <span class="inline-craving-label">Craving?</span>
                <button type="button" class="inline-craving-btn selected" data-craving="0">None</button>
                <button type="button" class="inline-craving-btn" data-craving="1">Mild</button>
                <button type="button" class="inline-craving-btn" data-craving="2">Moderate</button>
                <button type="button" class="inline-craving-btn" data-craving="3">Strong</button>
                <button type="button" class="inline-craving-btn" data-craving="4">Intense</button>
            </div>
            <div class="inline-checkin-actions">
                <button type="button" class="btn-checkin-prompt" id="inlineCheckinSubmit" disabled>
                    <i class="fas fa-circle-check" aria-hidden="true"></i> Check In
                </button>
                <a href="{% url 'accounts:daily_checkin' %}" class="checkin-add-details">Add more details →</a>
            </div>
        </div>
    </div>
```

- [ ] **Step 4: Give the done bar stable, always-present ids** — replace the `done-mood` div and the streak `{% if %}` badge inside `#checkinDoneBar`. Change:

```html
                <div class="done-mood">Feeling {% if todays_checkin %}{{ todays_checkin.get_mood_display }}{% endif %}</div>
```
to:
```html
                <div class="done-mood" id="doneMoodText">Feeling {% if todays_checkin %}{{ todays_checkin.get_mood_display }}{% endif %}</div>
```

and change:
```html
            {% if current_streak > 1 %}
            <span class="streak-badge">🔥 {{ current_streak }}-day streak</span>
            {% endif %}
```
to (always in DOM, hidden when ≤1 so JS can reveal/update it):
```html
            <span class="streak-badge" id="doneStreakBadge" style="{% if current_streak <= 1 %}display:none;{% endif %}">🔥 <span id="doneStreakCount">{{ current_streak }}</span>-day streak</span>
```

- [ ] **Step 5: Add the hidden Anchor prompt** — immediately AFTER the closing `</div>` of `#checkinDoneBar` (before `<div class="progress-container">`), insert:

```html
    <div id="homeAnchorPrompt" style="display:none; border:1px solid #1e4d8b; background:#f4f8fc; border-radius:12px; padding:14px; margin:0 0 14px; text-align:center;">
        <div style="color:#1e4d8b; font-weight:600; margin-bottom:6px;">Today sounds heavy.</div>
        <a id="homeAnchorLink" href="#" style="background:#1e4d8b; color:#fff; padding:9px 18px; border-radius:8px; text-decoration:none; font-weight:600; display:inline-block;">
            Talk it through with Anchor
        </a>
    </div>
```

- [ ] **Step 6: Add CSS for the widget** — inside the page's existing `<style>` block (near the other `.checkin-prompt-bar` rules), add:

```css
    .inline-checkin { width: 100%; }
    .inline-mood-row { display: flex; gap: 6px; justify-content: space-between; margin: 10px 0; }
    .inline-mood-btn { flex: 1; font-size: 1.6rem; line-height: 1; padding: 8px 0; border: 2px solid transparent; border-radius: 10px; background: rgba(0,0,0,0.04); cursor: pointer; transition: all .15s; }
    .inline-mood-btn:hover { background: rgba(30,77,139,0.08); }
    .inline-mood-btn.selected { border-color: #1e4d8b; background: rgba(30,77,139,0.12); }
    .inline-craving-row { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-bottom: 12px; }
    .inline-craving-label { font-size: .85rem; color: #777; margin-right: 4px; }
    .inline-craving-btn { font-size: .8rem; padding: 5px 10px; border: 1px solid #ddd; border-radius: 14px; background: #fff; cursor: pointer; }
    .inline-craving-btn.selected { border-color: #1e4d8b; background: rgba(30,77,139,0.12); color: #1e4d8b; font-weight: 600; }
    .inline-checkin-actions { display: flex; align-items: center; gap: 14px; }
    .checkin-add-details { font-size: .85rem; color: #1e4d8b; text-decoration: none; }
```

- [ ] **Step 7: Run the render test + the widget tests**

Run: `python3 manage.py shell -c "from django.template.loader import get_template; get_template('accounts/progress.html'); print('RENDER_OK')"` → expect `RENDER_OK`.
Run: `python3 manage.py test apps.accounts.test_anchor_conversion.ProgressHomeWidgetTest -v2` → expect PASS (2 tests).

- [ ] **Step 8: Commit**

```bash
git add apps/accounts/templates/accounts/progress.html apps/accounts/test_anchor_conversion.py
git commit -m "feat(home): inline mood+craving check-in widget markup + done-bar hooks"
```

---

### Task 3: Home JS — AJAX submit + inline done/Anchor reveal

**Files:**
- Modify: `apps/accounts/templates/accounts/progress.html` (add a `<script>` block)

- [ ] **Step 1: Add the widget JS** — add this `<script>` block near the end of the page's other scripts (after the page-load toggle IIFE at ~line 1972 is fine). It uses `{{ csrf_token }}` directly (available in the template) to avoid any cookie-helper scope concerns:

```html
<script>
(function() {
    var formCard = document.getElementById('checkinFormCard');
    var submitBtn = document.getElementById('inlineCheckinSubmit');
    if (!formCard || !submitBtn) return;

    var moodBtns = formCard.querySelectorAll('.inline-mood-btn');
    var cravingBtns = formCard.querySelectorAll('.inline-craving-btn');
    var selectedMood = null;
    var selectedCraving = '0';

    moodBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            moodBtns.forEach(function(b) { b.classList.remove('selected'); });
            btn.classList.add('selected');
            selectedMood = btn.getAttribute('data-mood');
            submitBtn.disabled = false;
        });
    });
    cravingBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            cravingBtns.forEach(function(b) { b.classList.remove('selected'); });
            btn.classList.add('selected');
            selectedCraving = btn.getAttribute('data-craving');
        });
    });

    submitBtn.addEventListener('click', function() {
        if (!selectedMood) return;
        submitBtn.disabled = true;
        var fd = new FormData();
        fd.append('mood', selectedMood);
        fd.append('craving_level', selectedCraving);
        fetch('{% url "accounts:quick_checkin" %}', {
            method: 'POST',
            headers: { 'X-CSRFToken': '{{ csrf_token }}' },
            body: fd
        }).then(function(r) { return r.json(); }).then(function(data) {
            if (data.success || data.already_checked_in) {
                formCard.style.display = 'none';
                var doneBar = document.getElementById('checkinDoneBar');
                var moodText = document.getElementById('doneMoodText');
                if (data.mood_display && moodText) {
                    moodText.textContent = 'Feeling ' + data.mood_display;
                }
                if (typeof data.current_streak !== 'undefined') {
                    var count = document.getElementById('doneStreakCount');
                    var badge = document.getElementById('doneStreakBadge');
                    if (count) { count.textContent = data.current_streak; }
                    if (badge) { badge.style.display = (data.current_streak > 1) ? '' : 'none'; }
                }
                if (doneBar) { doneBar.style.display = ''; }
                if (data.needs_support && data.coach_url) {
                    var link = document.getElementById('homeAnchorLink');
                    var prompt = document.getElementById('homeAnchorPrompt');
                    if (link && prompt) {
                        link.href = data.coach_url;
                        prompt.style.display = 'block';
                    }
                }
            } else {
                submitBtn.disabled = false;
                alert(data.error || 'Could not check in. Please try again.');
            }
        }).catch(function() {
            submitBtn.disabled = false;
            alert('Could not check in. Please try again.');
        });
    });
})();
</script>
```

- [ ] **Step 2: Verify the template renders**

Run: `python3 manage.py shell -c "from django.template.loader import get_template; get_template('accounts/progress.html'); print('RENDER_OK')"`
Expected: `RENDER_OK`.

- [ ] **Step 3: Manual verification note**

This is vanilla JS — verify by hand before/after deploy: on the home (web + iOS app), with no check-in today, tap a mood + optional craving + "Check In" → the widget swaps to the done bar with the correct mood and streak **without a page reload**; a low-mood/high-craving check-in additionally reveals the "Talk it through with Anchor" prompt linking into the coach. A calm check-in shows no prompt.

- [ ] **Step 4: Commit**

```bash
git add apps/accounts/templates/accounts/progress.html
git commit -m "feat(home): wire inline check-in AJAX submit + Anchor reveal"
```

---

### Task 4: Remove dead `hybrid_landing` code + fix routing + CLAUDE.md

**Files:**
- Delete: `apps/accounts/templates/accounts/hybrid_landing.html`
- Modify: `apps/accounts/views.py` (delete `hybrid_landing_view`)
- Modify: `apps/accounts/urls.py` (replace the lambda with a RedirectView)
- Modify: `CLAUDE.md` (correct the landing-page note)

- [ ] **Step 1: Confirm nothing references the dead code**

Run: `grep -rn "hybrid_landing_view\|hybrid_landing.html" --include="*.py" --include="*.html" .`
Run: `grep -rn "accounts:hybrid_landing" --include="*.py" --include="*.html" .`
Expected: the first finds only the `hybrid_landing_view` definition + the template file itself; the second finds nothing (the URL name isn't reversed anywhere). If either finds a live caller, STOP and report.

- [ ] **Step 2: Delete the orphaned view and template**

Delete the entire `def hybrid_landing_view(request):` function from `apps/accounts/views.py` (it spans from `def hybrid_landing_view` to just before the next top-level `def`). Then:
```bash
git rm apps/accounts/templates/accounts/hybrid_landing.html
```

- [ ] **Step 3: Replace the lambda with a RedirectView** — in `apps/accounts/urls.py`, change:
```python
    path('', lambda request: redirect('accounts:progress'), name='hybrid_landing'),
```
to:
```python
    path('', RedirectView.as_view(pattern_name='accounts:progress'), name='hybrid_landing'),
```
Ensure `from django.views.generic import RedirectView` is imported at the top of `urls.py` (add it if missing). Leave the `redirect` import if other lines still use it; if `redirect` is now unused in `urls.py`, remove that import.

- [ ] **Step 4: Update CLAUDE.md** — in `/Users/ryanpate/myrecoverypal/CLAUDE.md`, the "Project Vision" / User Flow section says users land on the Social Feed. Replace the inaccurate claim with the truth. Change the line:
```
Users land on the **Social Feed**, not a dashboard or resource page.
```
to:
```
Users land on the **progress home** (`accounts:progress`) after login — the daily check-in + streak + sobriety counter live here. The Social Feed is one tap away in the nav.
```

- [ ] **Step 5: Verify**

Run: `python3 manage.py check` → `System check identified no issues`.
Run: `python3 manage.py test apps.accounts.test_anchor_conversion -v1` → all pass (the home still renders; nothing imported the dead view).

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/views.py apps/accounts/urls.py CLAUDE.md
git commit -m "chore(home): remove orphaned hybrid_landing view/template; fix routing + docs"
```

---

### Task 5: Verification

- [ ] **Step 1: Full anchor suite**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion -v1`
Expected: PASS (the prior 24 + `test_response_includes_current_streak` + 2 `ProgressHomeWidgetTest` = 27 tests).

- [ ] **Step 2: Migration drift + check**

Run: `python3 manage.py makemigrations --check --dry-run` → `No changes detected`.
Run: `python3 manage.py check` → no issues.

- [ ] **Step 3: Regression**

Run: `python3 manage.py test apps.accounts.tests_signup apps.accounts.test_trial_expiration -v1`
Expected: PASS.

- [ ] **Step 4: Manual smoke (pre/post deploy)**

On the progress home, logged in with no check-in today: inline mood+craving widget appears; submit → inline done bar with correct streak, no reload; hard check-in → Anchor prompt appears and opens the coach. Confirm the old `hybrid_landing` URL (`/accounts/`) still redirects to the home.

This plan is implemented on a feature branch; integration/merge is handled by the finishing-a-development-branch skill after the final review (do NOT push to main from within the tasks).

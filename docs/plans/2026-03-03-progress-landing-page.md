# Progress Landing Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the My Progress page the default landing page with tabbed Progress/Feed navigation, inline full check-in, and share buttons on all progress sections.

**Architecture:** The existing `progress_view` becomes the post-login landing page. A tab bar switches between "My Progress" (server-rendered on load) and "My Feed" (AJAX-loaded via a new HTML fragment endpoint). The existing `quick_checkin` endpoint is extended to accept all check-in fields. Share buttons on each progress section use the native share sheet (Capacitor) or a web dropdown.

**Tech Stack:** Django 5.0.10, Chart.js, Capacitor `@capacitor/share`, vanilla JS

---

### Task 1: Extend quick_checkin endpoint to accept all check-in fields

**Files:**
- Modify: `apps/accounts/views.py:834-919`

**Step 1: Update the quick_checkin view to accept optional fields**

In `apps/accounts/views.py`, after line 872 (`gratitude = request.POST.get('gratitude', '').strip()[:280]`), add parsing for the additional fields. Then update the `DailyCheckIn.objects.create()` call at line 875 to use them instead of hardcoded defaults.

```python
# After line 872, add:
    # Get optional fields with safe defaults
    energy_level = request.POST.get('energy_level')
    craving_level = request.POST.get('craving_level')
    challenge = request.POST.get('challenge', '').strip()[:300]
    goal = request.POST.get('goal', '').strip()[:300]
    is_shared = request.POST.get('is_shared') != 'false'  # Default true

    try:
        energy_level = int(energy_level) if energy_level else 3
        energy_level = max(1, min(5, energy_level))
    except (ValueError, TypeError):
        energy_level = 3

    try:
        craving_level = int(craving_level) if craving_level else 0
        craving_level = max(0, min(4, craving_level))
    except (ValueError, TypeError):
        craving_level = 0
```

Then update the `DailyCheckIn.objects.create()` call (line 875-883) to use these values:

```python
    checkin = DailyCheckIn.objects.create(
        user=request.user,
        date=today,
        mood=mood,
        craving_level=craving_level,
        energy_level=energy_level,
        gratitude=gratitude,
        challenge=challenge,
        goal=goal,
        is_shared=is_shared,
    )
```

**Step 2: Run the dev server and test manually**

```bash
python manage.py runserver
```

Test with curl:
```bash
curl -X POST http://localhost:8000/accounts/quick-checkin/ \
  -H "Cookie: <session>" -H "X-CSRFToken: <token>" \
  -d "mood=4&energy_level=4&craving_level=1&gratitude=My+family&challenge=Work+stress&goal=Exercise"
```

Expected: JSON with `success: true`

**Step 3: Commit**

```bash
git add apps/accounts/views.py
git commit -m "feat: extend quick_checkin to accept all check-in fields"
```

---

### Task 2: Add tab bar and inline check-in to progress template

**Files:**
- Modify: `apps/accounts/templates/accounts/progress.html:441-620`

**Step 1: Add tab bar HTML after the `{% block content %}` tag (line 441)**

Insert a tab bar before the existing `.progress-container` div:

```html
{% block content %}
<!-- Tab Bar -->
<div class="landing-tabs" id="landingTabs">
    <button class="landing-tab active" data-tab="progress" id="tabProgress">
        <i class="fas fa-chart-line" aria-hidden="true"></i> My Progress
    </button>
    <button class="landing-tab" data-tab="feed" id="tabFeed">
        <i class="fas fa-comments" aria-hidden="true"></i> My Feed
    </button>
</div>

<!-- Progress Tab Content -->
<div id="progressContent">

<!-- Inline Check-in Section -->
{% if not todays_checkin %}
<div class="inline-checkin-card" id="inlineCheckinCard">
    <div class="inline-checkin-header">
        <h2><i class="fas fa-sun" aria-hidden="true"></i> Daily Check-in</h2>
        <span class="checkin-date">{{ today|date:"l, M j" }}</span>
    </div>
    <form id="inlineCheckinForm">
        {% csrf_token %}
        <div class="mood-grid">
            <label class="mood-option"><input type="radio" name="mood" value="1"><span class="mood-emoji">😰</span><span class="mood-label">Struggling</span></label>
            <label class="mood-option"><input type="radio" name="mood" value="2"><span class="mood-emoji">😔</span><span class="mood-label">Down</span></label>
            <label class="mood-option"><input type="radio" name="mood" value="3"><span class="mood-emoji">😐</span><span class="mood-label">Okay</span></label>
            <label class="mood-option"><input type="radio" name="mood" value="4" checked><span class="mood-emoji">😊</span><span class="mood-label">Good</span></label>
            <label class="mood-option"><input type="radio" name="mood" value="5"><span class="mood-emoji">😄</span><span class="mood-label">Great</span></label>
            <label class="mood-option"><input type="radio" name="mood" value="6"><span class="mood-emoji">🌟</span><span class="mood-label">Amazing</span></label>
        </div>

        <div class="slider-row">
            <div class="slider-group">
                <label><i class="fas fa-bolt" aria-hidden="true"></i> Energy</label>
                <input type="range" name="energy_level" min="1" max="5" value="3" id="energySlider">
                <span class="slider-value" id="energyValue">3</span>
            </div>
            <div class="slider-group">
                <label><i class="fas fa-fire" aria-hidden="true"></i> Cravings</label>
                <input type="range" name="craving_level" min="0" max="4" value="0" id="cravingSlider">
                <span class="slider-value" id="cravingValue">None</span>
            </div>
        </div>

        <div class="gratitude-section">
            <label><i class="fas fa-heart" aria-hidden="true"></i> Gratitude</label>
            <div class="quick-tags">
                <button type="button" class="quick-tag" data-value="My sobriety">My sobriety</button>
                <button type="button" class="quick-tag" data-value="My family">My family</button>
                <button type="button" class="quick-tag" data-value="Good sleep">Good sleep</button>
                <button type="button" class="quick-tag" data-value="This community">This community</button>
                <button type="button" class="quick-tag" data-value="A new day">A new day</button>
            </div>
            <textarea name="gratitude" placeholder="What are you grateful for today?" maxlength="280" rows="2"></textarea>
        </div>

        <div class="optional-fields">
            <div class="field-group">
                <label><i class="fas fa-mountain" aria-hidden="true"></i> Today's Challenge</label>
                <textarea name="challenge" placeholder="Optional" maxlength="300" rows="1"></textarea>
            </div>
            <div class="field-group">
                <label><i class="fas fa-bullseye" aria-hidden="true"></i> Today's Goal</label>
                <textarea name="goal" placeholder="Optional" maxlength="300" rows="1"></textarea>
            </div>
        </div>

        <div class="share-toggle">
            <label class="toggle-switch">
                <input type="checkbox" name="is_shared" checked>
                <span class="toggle-slider"></span>
            </label>
            <span>Share with community</span>
        </div>

        <button type="submit" class="checkin-submit-btn">
            <i class="fas fa-check-circle" aria-hidden="true"></i> Complete Check-in
        </button>
    </form>
</div>
{% else %}
<div class="checkin-done-bar" id="checkinDoneBar">
    <div class="checkin-done-left">
        <i class="fas fa-check-circle" style="color: #52b788;" aria-hidden="true"></i>
        <span>Checked in today: {{ todays_checkin.get_mood_display_with_emoji }}</span>
        <span class="streak-badge">🔥 {{ current_streak }} day streak</span>
    </div>
    <button class="share-btn-small" data-share="checkin" data-text="Checked in feeling {{ todays_checkin.get_mood_display }} on MyRecoveryPal! 🔥 {{ current_streak }}-day streak #recovery">
        <i class="fas fa-share-nodes" aria-hidden="true"></i>
    </button>
</div>
{% endif %}

<!-- Rest of progress content follows (existing .progress-container) -->
<div class="progress-container">
```

At the end of the existing progress content (after the empty state closing div around line 616), close the `#progressContent` div and add the feed container:

```html
</div><!-- end .progress-container -->
</div><!-- end #progressContent -->

<!-- Feed Tab Content (loaded via AJAX) -->
<div id="feedContent" style="display: none;">
    <div class="feed-skeleton" id="feedSkeleton">
        <div class="skeleton-post"></div>
        <div class="skeleton-post"></div>
        <div class="skeleton-post"></div>
    </div>
</div>
```

**Step 2: Commit template structure**

```bash
git add apps/accounts/templates/accounts/progress.html
git commit -m "feat: add tab bar, inline check-in, and feed container to progress template"
```

---

### Task 3: Add share buttons to all progress sections

**Files:**
- Modify: `apps/accounts/templates/accounts/progress.html:455-605`

**Step 1: Add share buttons to each major section**

Add a share button to each section header. The button uses a `data-share` attribute with the section name and `data-text` with the pre-composed share text.

**Milestone card** (line 457, inside `.milestone-card`): Add after the opening `<div class="milestone-card">`:
```html
<div class="milestone-card">
    <button class="section-share-btn" data-share="milestone" data-text="I'm {{ days_sober }} days sober! Next milestone: {{ next_milestone }} days. #recovery #MyRecoveryPal" aria-label="Share milestone">
        <i class="fas fa-share-nodes" aria-hidden="true"></i>
    </button>
```

**Weekly comparison** (line 484, inside `.weekly-comparison`): Add after opening tag:
```html
<div class="weekly-comparison">
    {% if weekly_comparison.mood_change > 0 %}
    <button class="section-share-btn" data-share="weekly" data-text="My mood improved {{ weekly_comparison.mood_change }}% this week! #recovery #MyRecoveryPal" aria-label="Share weekly progress">
        <i class="fas fa-share-nodes" aria-hidden="true"></i>
    </button>
    {% endif %}
```

**Stats grid** (line 511): Wrap in a relatively-positioned container and add share button:
```html
<div class="stats-section" style="position: relative;">
    <button class="section-share-btn" data-share="stats" data-text="{{ total_checkins }} check-ins, {{ checkin_rate }}% rate, {{ avg_mood }} avg mood this month on MyRecoveryPal #recovery" aria-label="Share stats">
        <i class="fas fa-share-nodes" aria-hidden="true"></i>
    </button>
    <div class="stats-grid">
```

**Streak stat card** (line 520-523): Add share button:
```html
<div class="stat-card" style="position: relative;">
    <button class="section-share-btn stat-share" data-share="streak" data-text="🔥 {{ current_streak }}-day check-in streak on MyRecoveryPal! #recovery" aria-label="Share streak">
        <i class="fas fa-share-nodes" aria-hidden="true"></i>
    </button>
    <div class="stat-value streak">{{ current_streak }}</div>
    <div class="stat-label">Day Streak 🔥</div>
</div>
```

**Heatmap calendar** (line 588): Add share button after chart-title:
```html
<div class="chart-card" style="position: relative;">
    <button class="section-share-btn" data-share="heatmap" data-text="My 90-day recovery check-in calendar #recovery #MyRecoveryPal" aria-label="Share calendar">
        <i class="fas fa-share-nodes" aria-hidden="true"></i>
    </button>
    <div class="chart-title">
```

**Step 2: Commit share buttons**

```bash
git add apps/accounts/templates/accounts/progress.html
git commit -m "feat: add share buttons to milestone, weekly, stats, streak, and heatmap sections"
```

---

### Task 4: Add CSS for tab bar, inline check-in, share buttons, and feed skeleton

**Files:**
- Modify: `apps/accounts/templates/accounts/progress.html:7-437` (the `<style>` block)

**Step 1: Add CSS at the end of the existing `<style>` block (before `</style>`)**

```css
/* ===== Tab Bar ===== */
.landing-tabs {
    display: flex;
    gap: 0;
    max-width: 1000px;
    margin: 0 auto 1rem;
    padding: 0 1rem;
    border-bottom: 2px solid #e5e7eb;
}
.landing-tab {
    flex: 1;
    padding: 0.75rem 1rem;
    background: none;
    border: none;
    border-bottom: 3px solid transparent;
    font-size: 0.95rem;
    font-weight: 600;
    color: #6b7280;
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
}
.landing-tab.active {
    color: #1e4d8b;
    border-bottom-color: #1e4d8b;
}
.landing-tab:hover:not(.active) {
    color: #374151;
    background: #f9fafb;
}
[data-theme="dark"] .landing-tabs { border-bottom-color: #374151; }
[data-theme="dark"] .landing-tab.active { color: #60a5fa; border-bottom-color: #60a5fa; }
[data-theme="dark"] .landing-tab { color: #9ca3af; }
[data-theme="dark"] .landing-tab:hover:not(.active) { color: #d1d5db; background: #1f2937; }

/* ===== Inline Check-in ===== */
.inline-checkin-card {
    max-width: 1000px;
    margin: 0 auto 1.5rem;
    padding: 1.5rem;
    background: white;
    border-radius: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
.inline-checkin-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}
.inline-checkin-header h2 { font-size: 1.2rem; margin: 0; }
.checkin-date { color: #6b7280; font-size: 0.9rem; }

.mood-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 0.5rem;
    margin-bottom: 1rem;
}
.mood-option {
    text-align: center;
    cursor: pointer;
    padding: 0.5rem 0.25rem;
    border-radius: 12px;
    border: 2px solid transparent;
    transition: all 0.2s;
}
.mood-option:has(input:checked) {
    border-color: #1e4d8b;
    background: #eff6ff;
}
.mood-option input { display: none; }
.mood-emoji { font-size: 1.8rem; display: block; }
.mood-label { font-size: 0.7rem; color: #6b7280; margin-top: 0.25rem; display: block; }

.slider-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1rem;
}
.slider-group label { font-size: 0.85rem; font-weight: 600; margin-bottom: 0.25rem; display: block; }
.slider-group input[type="range"] { width: 100%; accent-color: #1e4d8b; }
.slider-value {
    display: inline-block;
    background: #eff6ff;
    color: #1e4d8b;
    padding: 0.15rem 0.5rem;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 600;
}

.gratitude-section { margin-bottom: 1rem; }
.gratitude-section > label { font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem; display: block; }
.quick-tags { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.5rem; }
.quick-tag {
    padding: 0.3rem 0.7rem;
    border-radius: 20px;
    border: 1px solid #d1d5db;
    background: #f9fafb;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.2s;
}
.quick-tag:hover, .quick-tag.selected { background: #1e4d8b; color: white; border-color: #1e4d8b; }
.gratitude-section textarea {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    resize: none;
    font-size: 0.9rem;
}

.optional-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1rem;
}
.field-group label { font-size: 0.85rem; font-weight: 600; margin-bottom: 0.25rem; display: block; }
.field-group textarea {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    resize: none;
    font-size: 0.85rem;
}

.share-toggle {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
}
.toggle-switch { position: relative; display: inline-block; width: 44px; height: 24px; }
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.toggle-slider {
    position: absolute; cursor: pointer; inset: 0;
    background: #d1d5db; border-radius: 24px; transition: 0.2s;
}
.toggle-slider::before {
    content: ""; position: absolute; height: 18px; width: 18px;
    left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: 0.2s;
}
.toggle-switch input:checked + .toggle-slider { background: #52b788; }
.toggle-switch input:checked + .toggle-slider::before { transform: translateX(20px); }

.checkin-submit-btn {
    width: 100%;
    padding: 0.75rem;
    background: linear-gradient(135deg, #1e4d8b, #4db8e8);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
}
.checkin-submit-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(30,77,139,0.3); }
.checkin-submit-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

/* Checked-in bar */
.checkin-done-bar {
    max-width: 1000px;
    margin: 0 auto 1rem;
    padding: 0.75rem 1rem;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.checkin-done-left { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.streak-badge {
    background: #fff7ed;
    color: #c2410c;
    padding: 0.15rem 0.5rem;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 600;
}

/* ===== Share Buttons ===== */
.section-share-btn {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    background: rgba(255,255,255,0.85);
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0.35rem 0.5rem;
    cursor: pointer;
    color: #6b7280;
    font-size: 0.85rem;
    transition: all 0.2s;
    z-index: 2;
    backdrop-filter: blur(4px);
}
.section-share-btn:hover { background: #1e4d8b; color: white; border-color: #1e4d8b; }
.share-btn-small {
    background: none;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 0.3rem 0.5rem;
    cursor: pointer;
    color: #6b7280;
    font-size: 0.8rem;
    transition: all 0.2s;
}
.share-btn-small:hover { background: #1e4d8b; color: white; border-color: #1e4d8b; }

/* Make sections position relative for share btn */
.milestone-card, .weekly-comparison, .chart-card { position: relative; }

/* Share dropdown (web fallback) */
.share-dropdown {
    position: absolute;
    top: 2.5rem;
    right: 0.5rem;
    background: white;
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    padding: 0.5rem 0;
    z-index: 10;
    min-width: 180px;
    display: none;
}
.share-dropdown.show { display: block; }
.share-dropdown a, .share-dropdown button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    width: 100%;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 0.85rem;
    color: #374151;
    text-decoration: none;
}
.share-dropdown a:hover, .share-dropdown button:hover { background: #f3f4f6; }

/* ===== Feed Skeleton ===== */
.feed-skeleton .skeleton-post {
    background: white;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.feed-skeleton .skeleton-post::before {
    content: "";
    display: block;
    height: 60px;
    background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 8px;
    margin-bottom: 0.5rem;
}
.feed-skeleton .skeleton-post::after {
    content: "";
    display: block;
    height: 120px;
    background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 8px;
}
@keyframes shimmer { to { background-position: -200% 0; } }

/* Dark mode overrides */
[data-theme="dark"] .inline-checkin-card { background: #1f2937; }
[data-theme="dark"] .mood-option:has(input:checked) { border-color: #60a5fa; background: #1e3a5f; }
[data-theme="dark"] .gratitude-section textarea,
[data-theme="dark"] .field-group textarea { background: #111827; border-color: #374151; color: #e5e7eb; }
[data-theme="dark"] .quick-tag { background: #374151; border-color: #4b5563; color: #d1d5db; }
[data-theme="dark"] .quick-tag:hover, [data-theme="dark"] .quick-tag.selected { background: #2563eb; color: white; border-color: #2563eb; }
[data-theme="dark"] .checkin-done-bar { background: #064e3b; border-color: #065f46; }
[data-theme="dark"] .section-share-btn { background: rgba(31,41,55,0.85); border-color: #374151; color: #9ca3af; }
[data-theme="dark"] .section-share-btn:hover { background: #2563eb; color: white; }
[data-theme="dark"] .share-dropdown { background: #1f2937; }
[data-theme="dark"] .share-dropdown a, [data-theme="dark"] .share-dropdown button { color: #d1d5db; }
[data-theme="dark"] .share-dropdown a:hover, [data-theme="dark"] .share-dropdown button:hover { background: #374151; }
[data-theme="dark"] .feed-skeleton .skeleton-post { background: #1f2937; }
[data-theme="dark"] .slider-value { background: #1e3a5f; color: #60a5fa; }

/* Mobile responsive */
@media (max-width: 576px) {
    .mood-grid { grid-template-columns: repeat(3, 1fr); }
    .slider-row { grid-template-columns: 1fr; }
    .optional-fields { grid-template-columns: 1fr; }
    .mood-emoji { font-size: 1.5rem; }
}
```

**Step 2: Commit CSS**

```bash
git add apps/accounts/templates/accounts/progress.html
git commit -m "feat: add CSS for tab bar, inline check-in, share buttons, and feed skeleton"
```

---

### Task 5: Add JavaScript for tab switching, check-in submit, and share functionality

**Files:**
- Modify: `apps/accounts/templates/accounts/progress.html` (add JS at end of `{% block extra_js %}`)

**Step 1: Add JavaScript after the existing Chart.js block (after approximately line 901)**

```javascript
// ===== Tab Switching =====
(function() {
    const tabProgress = document.getElementById('tabProgress');
    const tabFeed = document.getElementById('tabFeed');
    const progressContent = document.getElementById('progressContent');
    const feedContent = document.getElementById('feedContent');
    let feedLoaded = false;

    function switchTab(tab) {
        if (tab === 'progress') {
            tabProgress.classList.add('active');
            tabFeed.classList.remove('active');
            progressContent.style.display = '';
            feedContent.style.display = 'none';
            window.location.hash = 'progress';
        } else {
            tabFeed.classList.add('active');
            tabProgress.classList.remove('active');
            progressContent.style.display = 'none';
            feedContent.style.display = '';
            window.location.hash = 'feed';
            if (!feedLoaded) loadFeed();
        }
    }

    function loadFeed() {
        feedLoaded = true;
        fetch('{% url "accounts:social_feed_fragment" %}', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(r => r.text())
        .then(html => {
            document.getElementById('feedSkeleton').style.display = 'none';
            const container = document.createElement('div');
            container.innerHTML = html;
            feedContent.appendChild(container);
            // Re-run inline scripts from feed fragment
            container.querySelectorAll('script').forEach(s => {
                const ns = document.createElement('script');
                ns.textContent = s.textContent;
                document.body.appendChild(ns);
            });
        })
        .catch(() => {
            document.getElementById('feedSkeleton').innerHTML =
                '<p style="text-align:center;padding:2rem;color:#6b7280;">Could not load feed. <a href="{% url "accounts:social_feed" %}">Open feed</a></p>';
        });
    }

    if (tabProgress) tabProgress.addEventListener('click', () => switchTab('progress'));
    if (tabFeed) tabFeed.addEventListener('click', () => switchTab('feed'));

    // Check URL hash on load
    if (window.location.hash === '#feed') switchTab('feed');
})();

// ===== Inline Check-in Submit =====
(function() {
    const form = document.getElementById('inlineCheckinForm');
    if (!form) return;

    // Slider value displays
    const energySlider = document.getElementById('energySlider');
    const cravingSlider = document.getElementById('cravingSlider');
    const energyValue = document.getElementById('energyValue');
    const cravingValue = document.getElementById('cravingValue');
    const cravingLabels = ['None', 'Mild', 'Moderate', 'Strong', 'Intense'];

    if (energySlider) energySlider.addEventListener('input', () => { energyValue.textContent = energySlider.value; });
    if (cravingSlider) cravingSlider.addEventListener('input', () => { cravingValue.textContent = cravingLabels[cravingSlider.value]; });

    // Quick tags
    document.querySelectorAll('.quick-tag').forEach(tag => {
        tag.addEventListener('click', () => {
            const textarea = form.querySelector('textarea[name="gratitude"]');
            const val = tag.dataset.value;
            textarea.value = textarea.value ? textarea.value + ', ' + val : val;
            tag.classList.toggle('selected');
        });
    });

    // Form submit
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const btn = form.querySelector('.checkin-submit-btn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

        const formData = new FormData(form);
        // Checkbox sends value only when checked
        if (!form.querySelector('input[name="is_shared"]').checked) {
            formData.set('is_shared', 'false');
        }

        fetch('{% url "accounts:quick_checkin" %}', {
            method: 'POST',
            body: formData,
            headers: { 'X-CSRFToken': formData.get('csrfmiddlewaretoken') }
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // Replace form with done bar
                const card = document.getElementById('inlineCheckinCard');
                card.outerHTML = `
                    <div class="checkin-done-bar" id="checkinDoneBar">
                        <div class="checkin-done-left">
                            <i class="fas fa-check-circle" style="color: #52b788;"></i>
                            <span>Checked in: ${data.mood_display}</span>
                            <span class="streak-badge">🔥 Check-in complete!</span>
                        </div>
                    </div>`;
                // Reload page to refresh charts with new data
                setTimeout(() => window.location.reload(), 500);
            } else {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check-circle"></i> Complete Check-in';
                alert(data.error || data.message || 'Could not save check-in');
            }
        })
        .catch(() => {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check-circle"></i> Complete Check-in';
            alert('Network error. Please try again.');
        });
    });
})();

// ===== Share Buttons =====
(function() {
    const siteUrl = 'https://www.myrecoverypal.com';

    async function shareContent(text, section) {
        const url = siteUrl + '/accounts/progress/';

        // Try native share (Capacitor) first
        if (window.Capacitor && window.Capacitor.isNativePlatform()) {
            try {
                const { Share } = await import('https://esm.sh/@capacitor/share');
                await Share.share({ text: text, url: url });
                return;
            } catch(e) { /* fall through to web */ }
        }

        // Try Web Share API
        if (navigator.share) {
            try {
                await navigator.share({ text: text, url: url });
                return;
            } catch(e) { /* cancelled or failed, fall through */ }
        }

        // Web fallback: show dropdown
        showShareDropdown(event.currentTarget, text, url);
    }

    function showShareDropdown(btn, text, url) {
        // Remove any existing dropdown
        document.querySelectorAll('.share-dropdown.show').forEach(d => d.remove());

        const encoded = encodeURIComponent(text + '\n' + url);
        const dropdown = document.createElement('div');
        dropdown.className = 'share-dropdown show';
        dropdown.innerHTML = `
            <a href="https://twitter.com/intent/tweet?text=${encoded}" target="_blank" rel="noopener">
                <i class="fab fa-x-twitter"></i> X / Twitter
            </a>
            <a href="https://www.facebook.com/sharer/sharer.php?quote=${encoded}" target="_blank" rel="noopener">
                <i class="fab fa-facebook"></i> Facebook
            </a>
            <a href="https://wa.me/?text=${encoded}" target="_blank" rel="noopener">
                <i class="fab fa-whatsapp"></i> WhatsApp
            </a>
            <button onclick="navigator.clipboard.writeText('${text.replace(/'/g, "\\'")} ${url}');this.innerHTML='<i class=\\'fas fa-check\\'></i> Copied!';setTimeout(()=>this.closest('.share-dropdown').remove(),1000)">
                <i class="fas fa-copy"></i> Copy Link
            </button>
            <button class="post-to-feed-btn" data-text="${text.replace(/"/g, '&quot;')}">
                <i class="fas fa-paper-plane"></i> Post to Feed
            </button>`;
        btn.parentElement.appendChild(dropdown);

        // Post to feed handler
        dropdown.querySelector('.post-to-feed-btn').addEventListener('click', function() {
            fetch('{% url "accounts:create_post" %}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: 'content=' + encodeURIComponent(this.dataset.text) + '&visibility=public'
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    this.innerHTML = '<i class="fas fa-check"></i> Posted!';
                    setTimeout(() => dropdown.remove(), 1000);
                }
            });
        });

        // Close dropdown on outside click
        setTimeout(() => {
            document.addEventListener('click', function close(e) {
                if (!dropdown.contains(e.target) && e.target !== btn) {
                    dropdown.remove();
                    document.removeEventListener('click', close);
                }
            });
        }, 10);
    }

    // Attach to all share buttons
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('[data-share]');
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            shareContent(btn.dataset.text, btn.dataset.share);
        }
    });
})();
```

**Step 2: Commit JavaScript**

```bash
git add apps/accounts/templates/accounts/progress.html
git commit -m "feat: add JS for tab switching, AJAX check-in, and share buttons"
```

---

### Task 6: Update progress_view to include check-in context

**Files:**
- Modify: `apps/accounts/views.py:944-1097`

**Step 1: Add today's check-in and date to the progress_view context**

At the top of the `progress_view` function (around line 958), add:

```python
    today = timezone.now().date()
    todays_checkin = DailyCheckIn.objects.filter(user=request.user, date=today).first()
```

In the context dict (around line 1074-1097), add these two entries:

```python
    context = {
        'today': today,
        'todays_checkin': todays_checkin,
        # ... existing keys ...
    }
```

**Step 2: Commit**

```bash
git add apps/accounts/views.py
git commit -m "feat: add today's check-in context to progress_view"
```

---

### Task 7: Create social_feed_fragment view and URL

**Files:**
- Modify: `apps/accounts/views.py` (add new view after `social_feed_view`)
- Modify: `apps/accounts/urls.py:73`
- Create: `apps/accounts/templates/accounts/social_feed_fragment.html`

**Step 1: Add the fragment view**

Add after the `social_feed_view` function (after line 3921):

```python
@login_required
def social_feed_fragment(request):
    """Return social feed content as an HTML fragment for AJAX tab loading."""
    # Reuse the same query logic from social_feed_view
    user = request.user
    following_ids = list(
        UserConnection.objects.filter(
            user=user,
            connection_type='follow'
        ).values_list('connected_user_id', flat=True)
    )

    # Get posts from followed users + own posts
    post_ids = set()
    following_posts = list(SocialPost.objects.filter(
        author_id__in=following_ids + [user.id],
        visibility__in=['public', 'friends']
    ).select_related('author').prefetch_related('likes', 'comments').order_by('-created_at')[:50])
    post_ids.update(p.id for p in following_posts)

    # Add public discover posts
    discover_posts = list(SocialPost.objects.filter(
        visibility='public'
    ).exclude(id__in=post_ids).select_related('author').prefetch_related('likes', 'comments').order_by('-created_at')[:20])

    visible_posts = following_posts + discover_posts

    paginator = Paginator(visible_posts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    today = timezone.now().date()
    todays_checkin = DailyCheckIn.objects.filter(user=user, date=today).first()

    context = {
        'page_obj': page_obj,
        'posts': page_obj,
        'todays_checkin': todays_checkin,
        'checkin_streak': user.get_checkin_streak(),
        'is_premium': hasattr(user, 'subscription') and user.subscription.is_premium(),
    }

    return render(request, 'accounts/social_feed_fragment.html', context)
```

**Step 2: Add URL pattern**

In `apps/accounts/urls.py`, add after the social-feed URL (line 73):

```python
    path('social-feed/fragment/', views.social_feed_fragment, name='social_feed_fragment'),
```

**Step 3: Create the fragment template**

Create `apps/accounts/templates/accounts/social_feed_fragment.html` — this is a stripped-down version of the social feed with NO `{% extends %}`, just the feed content:

```html
{% load static %}
<div class="social-feed-container" style="max-width:600px;margin:0 auto;padding:1rem;">
    <!-- Create Post Box -->
    <div class="create-post-box" style="background:white;border-radius:12px;padding:0.75rem 1rem;margin-bottom:1rem;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
        <form method="post" action="{% url 'accounts:create_post' %}" id="fragmentPostForm">
            {% csrf_token %}
            <div style="display:flex;align-items:center;gap:0.75rem;">
                {% if user.avatar %}
                <img src="{{ user.avatar.url }}" alt="{{ user.username }}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;">
                {% else %}
                <div style="width:36px;height:36px;border-radius:50%;background:hsl({{ user.id|add:100 }}, 45%, 50%);display:flex;align-items:center;justify-content:center;color:white;font-weight:600;font-size:0.9rem;">{{ user.username|slice:":1"|upper }}</div>
                {% endif %}
                <textarea name="content" placeholder="Share something with the community..." rows="2" style="flex:1;border:1px solid #d1d5db;border-radius:8px;padding:0.5rem;resize:none;font-size:0.9rem;"></textarea>
            </div>
            <div style="display:flex;justify-content:flex-end;margin-top:0.5rem;">
                <button type="submit" style="background:linear-gradient(135deg,#1e4d8b,#4db8e8);color:white;border:none;border-radius:8px;padding:0.4rem 1rem;font-size:0.85rem;cursor:pointer;">Post</button>
            </div>
        </form>
    </div>

    <!-- Posts -->
    {% for post in posts %}
    <div class="feed-post-card" style="background:white;border-radius:12px;padding:1rem;margin-bottom:1rem;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
        <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.75rem;">
            {% if post.author.avatar %}
            <img src="{{ post.author.avatar.url }}" alt="{{ post.author.username }}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;">
            {% else %}
            <div style="width:40px;height:40px;border-radius:50%;background:hsl({{ post.author.id|add:100 }}, 45%, 50%);display:flex;align-items:center;justify-content:center;color:white;font-weight:600;">{{ post.author.username|slice:":1"|upper }}</div>
            {% endif %}
            <div>
                <a href="{% url 'accounts:profile' username=post.author.username %}" style="font-weight:600;color:#1f2937;text-decoration:none;">{{ post.author.get_full_name|default:post.author.username }}</a>
                <div style="font-size:0.8rem;color:#6b7280;">{{ post.created_at|timesince }} ago</div>
            </div>
        </div>
        <div style="line-height:1.5;color:#374151;">{{ post.content|linebreaksbr }}</div>
        {% if post.image %}
        <img src="{{ post.image.url }}" style="width:100%;border-radius:8px;margin-top:0.75rem;" loading="lazy">
        {% endif %}
        <div style="display:flex;gap:1rem;margin-top:0.75rem;padding-top:0.5rem;border-top:1px solid #f3f4f6;">
            <button class="fragment-like-btn" data-post-id="{{ post.id }}" style="background:none;border:none;color:#6b7280;cursor:pointer;font-size:0.85rem;">
                <i class="{% if user in post.likes.all %}fas{% else %}far{% endif %} fa-heart" style="{% if user in post.likes.all %}color:#ef4444{% endif %}"></i> {{ post.likes.count }}
            </button>
            <a href="{% url 'accounts:post_detail' post_id=post.id %}" style="color:#6b7280;text-decoration:none;font-size:0.85rem;">
                <i class="far fa-comment"></i> {{ post.comments.count }}
            </a>
        </div>
    </div>
    {% empty %}
    <div style="text-align:center;padding:3rem 1rem;color:#6b7280;">
        <i class="fas fa-comments" style="font-size:3rem;margin-bottom:1rem;display:block;"></i>
        <p>No posts yet. Be the first to share!</p>
    </div>
    {% endfor %}
</div>
```

**Step 4: Commit**

```bash
git add apps/accounts/views.py apps/accounts/urls.py apps/accounts/templates/accounts/social_feed_fragment.html
git commit -m "feat: add social_feed_fragment endpoint for AJAX tab loading"
```

---

### Task 8: Update LOGIN_REDIRECT_URL and native bottom tab bar

**Files:**
- Modify: `recovery_hub/settings.py:258`
- Modify: `templates/base.html:562`

**Step 1: Change LOGIN_REDIRECT_URL**

In `recovery_hub/settings.py`, change line 258:

```python
# Before:
LOGIN_REDIRECT_URL = 'accounts:social_feed'
# After:
LOGIN_REDIRECT_URL = 'accounts:progress'
```

**Step 2: Update native bottom tab bar**

In `templates/base.html`, update line 562 to point the Feed tab to progress page:

```html
<!-- Before: -->
<a href="{% url 'accounts:social_feed' %}" class="native-tab {% if request.resolver_match.url_name == 'social_feed' or request.resolver_match.url_name == 'hybrid_landing' %}active{% endif %}" data-tab="feed">

<!-- After: -->
<a href="{% url 'accounts:progress' %}" class="native-tab {% if request.resolver_match.url_name == 'progress' %}active{% endif %}" data-tab="feed">
```

**Step 3: Commit**

```bash
git add recovery_hub/settings.py templates/base.html
git commit -m "feat: change landing page to progress, update native tab bar"
```

---

### Task 9: Bump static file cache version

**Files:**
- Modify: `templates/base.html` — update `?v=` query strings on CSS/JS includes

**Step 1: Find and update cache-busting version**

Search for the current `?v=` string in base.html and bump it (e.g., from `?v=20260302h` to `?v=20260303a`).

**Step 2: Commit**

```bash
git add templates/base.html
git commit -m "chore: bump static file cache version to 20260303a"
```

---

### Task 10: Manual testing and final commit

**Step 1: Start dev server and test**

```bash
python manage.py runserver
```

**Test checklist:**
- [ ] Login redirects to `/accounts/progress/`
- [ ] Tab bar shows "My Progress" (active) and "My Feed"
- [ ] Inline check-in form displays when not checked in today
- [ ] Mood selection, sliders, gratitude tags, and optional fields work
- [ ] Check-in submit via AJAX succeeds and collapses to done bar
- [ ] Charts refresh after check-in (page reload)
- [ ] Share buttons visible on milestone, weekly, stats, streak, heatmap
- [ ] Share dropdown opens on web with Twitter, Facebook, WhatsApp, Copy, Post to Feed
- [ ] Clicking "My Feed" tab loads feed content via AJAX
- [ ] Tab switching back to Progress preserves charts
- [ ] URL hash updates (#progress / #feed)
- [ ] Direct link to `/accounts/progress/#feed` loads feed tab
- [ ] Dark mode works for all new elements
- [ ] Mobile responsive (check at 375px width)
- [ ] Native bottom tab bar "Feed" icon points to progress page

**Step 2: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address testing feedback for progress landing page"
```

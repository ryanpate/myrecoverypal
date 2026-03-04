# Nav Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify navigation to 3 core links + Anchor AI premium CTA button, moving all other links to avatar dropdown and mobile menu.

**Architecture:** Replace 8 desktop nav links with 3 (Feed, Check-in, Progress) + a gradient Anchor AI CTA button. Consolidate mobile slide menu from 4 sections to 2. Simplify mobile bottom nav to 4 tabs. Add CSS for Anchor AI pill button with pulse animation. Native iOS/Android tabs unchanged.

**Tech Stack:** Django templates, CSS (base-inline.css), HTML (base.html)

**Design doc:** `docs/plans/2026-03-04-nav-redesign-design.md`

---

### Task 1: Simplify Desktop Nav Links

**Files:**
- Modify: `templates/base.html:190-217` (nav-links `<ul>`)

**Step 1: Replace desktop nav links**

Replace lines 190-217 in `base.html` (the `<ul class="nav-links">` block) with:

```html
<ul class="nav-links" id="navLinks">
    {% if user.is_authenticated %}
    <li><a href="{% url 'accounts:social_feed' %}"
            class="{% if request.resolver_match.url_name == 'social_feed' %}active{% endif %}">Feed</a></li>
    <li><a href="{% url 'accounts:daily_checkin' %}"
            class="{% if request.resolver_match.url_name == 'daily_checkin' %}active{% endif %}">Check-in</a></li>
    <li><a href="{% url 'accounts:progress' %}"
            class="{% if request.resolver_match.url_name == 'progress' %}active{% endif %}">Progress</a></li>
    <li><a href="{% url 'accounts:recovery_coach' %}"
            class="anchor-ai-cta {% if request.resolver_match.url_name == 'recovery_coach' %}active{% endif %}">
            <i class="fas fa-robot" aria-hidden="true"></i> Try Anchor AI
        </a></li>
    {% else %}
    <li><a href="{% url 'blog:post_list' %}"
            class="{% if 'blog' in request.resolver_match.namespace %}active{% endif %}">Blog</a></li>
    <li><a href="{% url 'core:ai_recovery_coach' %}"
            class="anchor-ai-cta {% if request.resolver_match.url_name == 'ai_recovery_coach' %}active{% endif %}">
            <i class="fas fa-robot" aria-hidden="true"></i> Try Anchor AI
        </a></li>
    {% endif %}
</ul>
```

**Removed from top bar:** Home, Blog, Journal, Groups, Challenges, Community, MyRecoveryCircle (8 links → 3 + CTA)

**Step 2: Verify template syntax**

Run: `python manage.py check --deploy 2>&1 | head -20`

**Step 3: Commit**

```bash
git add templates/base.html
git commit -m "feat: simplify desktop nav to Feed, Check-in, Progress + Anchor AI CTA"
```

---

### Task 2: Reorganize User Dropdown Menu

**Files:**
- Modify: `templates/base.html:250-315` (user-dropdown div)

**Step 1: Replace dropdown content**

Replace lines 251-314 in `base.html` (inside `<div class="user-dropdown" id="userDropdown">`) with a cleaner, organized list:

```html
<a href="{% url 'accounts:profile' username=user.username %}">
    <i class="fas fa-user"></i> Profile
</a>
<a href="{% url 'accounts:social_feed' %}">
    <i class="fas fa-circle-nodes"></i> MyRecoveryCircle
</a>
<a href="{% url 'journal:entry_list' %}">
    <i class="fas fa-book"></i> Journal
</a>
<a href="{% url 'accounts:groups_list' %}">
    <i class="fas fa-users-rectangle"></i> Groups
</a>
<a href="{% url 'accounts:community' %}">
    <i class="fas fa-people-group"></i> Community
</a>
<a href="{% url 'accounts:challenges_home' %}">
    <i class="fas fa-trophy"></i> Challenges
    {% if user_active_challenges_count > 0 %}
    <span class="message-count-badge">{{ user_active_challenges_count }}</span>
    {% endif %}
</a>
<a href="{% url 'accounts:messages' %}">
    <i class="fas fa-envelope"></i> Messages
</a>
<a href="{% url 'accounts:milestones' %}">
    <i class="fas fa-medal"></i> Milestones
</a>
<a href="{% url 'blog:post_list' %}">
    <i class="fas fa-newspaper"></i> Blog
</a>
<hr>
<a href="{% url 'accounts:subscription_management' %}">
    <i class="fas fa-crown"></i> Subscription
</a>
<a href="{% url 'accounts:invite_friends' %}" style="color: #52b788;">
    <i class="fas fa-user-plus"></i> Invite Friends
</a>
<a href="{% url 'accounts:edit_profile' %}">
    <i class="fas fa-gear"></i> Settings
</a>
<a href="{% url 'core:install_guide' %}" id="navInstallLink">
    <i class="fas fa-download"></i> Install App
</a>
<form method="post" action="{% url 'accounts:logout' %}" class="logout-form">
    {% csrf_token %}
    <button type="submit" class="logout-btn">
        <i class="fas fa-right-from-bracket"></i> Logout
    </button>
</form>
```

**Key changes:** Removed Dashboard (redundant with Progress), removed Recovery Pal link (niche), removed Anchor AI from dropdown (already in top nav CTA), removed pending check-ins alert (check-in is now in top nav), added icons to all items, removed inline gradient styles.

**Step 2: Commit**

```bash
git add templates/base.html
git commit -m "feat: reorganize user dropdown with icons, remove duplicates"
```

---

### Task 3: Simplify Mobile Slide Menu

**Files:**
- Modify: `templates/base.html:396-503` (mobile-menu-nav)

**Step 1: Replace mobile menu sections**

Replace lines 396-503 (the `<nav class="mobile-menu-nav">` block) with 2 sections:

```html
<nav class="mobile-menu-nav">
    <div class="mobile-menu-section">
        <div class="mobile-menu-label">Quick Actions</div>
        <a href="{% url 'accounts:social_feed' %}"
            class="{% if request.resolver_match.url_name == 'social_feed' %}active{% endif %}">
            <i class="fas fa-circle-nodes" style="margin-right: 0.5rem;"></i> Feed
        </a>
        <a href="{% url 'accounts:daily_checkin' %}"
            class="{% if request.resolver_match.url_name == 'daily_checkin' %}active{% endif %}">
            <i class="fas fa-circle-check" style="margin-right: 0.5rem;"></i> Check-in
        </a>
        <a href="{% url 'accounts:progress' %}"
            class="{% if request.resolver_match.url_name == 'progress' %}active{% endif %}">
            <i class="fas fa-chart-line" style="margin-right: 0.5rem;"></i> Progress
        </a>
        <a href="{% url 'accounts:recovery_coach' %}"
            class="{% if request.resolver_match.url_name == 'recovery_coach' %}active{% endif %}"
            style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15)); border-left: 3px solid #667eea; font-weight: 600;">
            <i class="fas fa-robot" style="margin-right: 0.5rem;"></i> Anchor AI Coach
        </a>
    </div>

    {% if user.is_authenticated %}
    <div class="mobile-menu-section">
        <div class="mobile-menu-label">More</div>
        <a href="{% url 'accounts:profile' username=user.username %}"
            class="{% if request.resolver_match.url_name == 'profile' %}active{% endif %}">
            <i class="fas fa-user" style="margin-right: 0.5rem;"></i> Profile
        </a>
        <a href="{% url 'journal:entry_list' %}"
            class="{% if 'journal' in request.resolver_match.namespace %}active{% endif %}">
            <i class="fas fa-book" style="margin-right: 0.5rem;"></i> Journal
        </a>
        <a href="{% url 'accounts:groups_list' %}"
            class="{% if 'group' in request.resolver_match.url_name %}active{% endif %}">
            <i class="fas fa-users-rectangle" style="margin-right: 0.5rem;"></i> Groups
        </a>
        <a href="{% url 'accounts:community' %}"
            class="{% if request.resolver_match.url_name == 'community' %}active{% endif %}">
            <i class="fas fa-people-group" style="margin-right: 0.5rem;"></i> Community
        </a>
        <a href="{% url 'accounts:challenges_home' %}"
            class="{% if 'challenge' in request.resolver_match.url_name %}active{% endif %}">
            <i class="fas fa-trophy" style="margin-right: 0.5rem;"></i> Challenges
        </a>
        <a href="{% url 'accounts:messages' %}"
            class="{% if request.resolver_match.url_name == 'messages' %}active{% endif %}">
            <i class="fas fa-envelope" style="margin-right: 0.5rem;"></i> Messages
        </a>
        <a href="{% url 'accounts:milestones' %}"
            class="{% if request.resolver_match.url_name == 'milestones' %}active{% endif %}">
            <i class="fas fa-medal" style="margin-right: 0.5rem;"></i> Milestones
        </a>
        <a href="{% url 'blog:post_list' %}"
            class="{% if 'blog' in request.resolver_match.namespace %}active{% endif %}">
            <i class="fas fa-newspaper" style="margin-right: 0.5rem;"></i> Blog
        </a>
        <a href="{% url 'accounts:subscription_management' %}"
            class="{% if request.resolver_match.url_name == 'subscription_management' %}active{% endif %}">
            <i class="fas fa-crown" style="margin-right: 0.5rem;"></i> Subscription
        </a>
        <a href="{% url 'accounts:invite_friends' %}"
            class="{% if request.resolver_match.url_name == 'invite_friends' %}active{% endif %}"
            style="color: #52b788;">
            <i class="fas fa-user-plus" style="margin-right: 0.5rem;"></i> Invite Friends
        </a>
        <a href="{% url 'accounts:edit_profile' %}"
            class="{% if request.resolver_match.url_name == 'edit_profile' %}active{% endif %}">
            <i class="fas fa-gear" style="margin-right: 0.5rem;"></i> Settings
        </a>
    </div>
    {% else %}
    <div class="mobile-menu-section">
        <div class="mobile-menu-label">Explore</div>
        <a href="{% url 'core:index' %}"
            class="{% if request.resolver_match.url_name == 'index' %}active{% endif %}">
            <i class="fas fa-home" style="margin-right: 0.5rem;"></i> Home
        </a>
        <a href="{% url 'blog:post_list' %}"
            class="{% if 'blog' in request.resolver_match.namespace %}active{% endif %}">
            <i class="fas fa-newspaper" style="margin-right: 0.5rem;"></i> Blog
        </a>
    </div>
    {% endif %}
</nav>
```

**Key changes:** 4 sections → 2 (Quick Actions + More), removed Dashboard and Install App links, removed Home for authenticated users (Feed replaces it), removed Recovery Pal (niche).

**Step 2: Commit**

```bash
git add templates/base.html
git commit -m "feat: simplify mobile slide menu to 2 sections"
```

---

### Task 4: Update Mobile Bottom Nav (web)

**Files:**
- Modify: `templates/base.html:528-563` (mobile-bottom-nav)

**Step 1: Replace authenticated mobile bottom nav**

Replace lines 529-546 (authenticated mobile bottom nav) with:

```html
<nav class="mobile-bottom-nav" id="mobileBottomNav">
    <a href="{% url 'accounts:social_feed' %}" class="{% if request.resolver_match.url_name == 'social_feed' %}active{% endif %}">
        <span>Feed</span>
    </a>
    <a href="{% url 'accounts:daily_checkin' %}" class="{% if request.resolver_match.url_name == 'daily_checkin' %}active{% endif %}">
        <span>Check-in</span>
    </a>
    <a href="{% url 'accounts:recovery_coach' %}"
        class="anchor-bottom-tab {% if request.resolver_match.url_name == 'recovery_coach' %}active{% endif %}">
        <span>Anchor AI</span>
    </a>
    <a href="{% url 'accounts:profile' username=user.username %}" class="{% if request.resolver_match.url_name == 'profile' %}active{% endif %}">
        <span>Profile</span>
    </a>
</nav>
```

**Key changes:** Circle → Feed, Community → Check-in, Account → Profile. Anchor stays. Added `anchor-bottom-tab` class for accent styling.

**Step 2: Commit**

```bash
git add templates/base.html
git commit -m "feat: update mobile bottom nav to Feed, Check-in, Anchor AI, Profile"
```

---

### Task 5: Add Anchor AI CTA Button CSS

**Files:**
- Modify: `static/css/base-inline.css` (add new rules near existing nav-links styles ~line 1390)

**Step 1: Add CSS for the Anchor AI nav button and remove old MyRecoveryCircle button styles**

Add after the existing `.nav-links` rules (around line 1393):

```css
/* Anchor AI CTA Button in Nav */
.nav-links a.anchor-ai-cta {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: #fff !important;
    padding: 0.5rem 1rem;
    border-radius: 25px;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    transition: all 0.3s ease;
    text-decoration: none;
    position: relative;
}

.nav-links a.anchor-ai-cta:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.nav-links a.anchor-ai-cta::after {
    display: none;
}

.nav-links a.anchor-ai-cta.active {
    box-shadow: 0 0 0 2px #fff, 0 0 0 4px #667eea;
}

/* Subtle pulse on first visit */
@keyframes anchor-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0.4); }
    50% { box-shadow: 0 0 0 8px rgba(102, 126, 234, 0); }
}

.nav-links a.anchor-ai-cta {
    animation: anchor-pulse 2s ease-in-out 3;
}

/* Anchor AI accent in mobile bottom nav */
.mobile-bottom-nav a.anchor-bottom-tab {
    color: #667eea;
    font-weight: 600;
}

.mobile-bottom-nav a.anchor-bottom-tab.active {
    color: #764ba2;
}
```

**Step 2: Remove old MyRecoveryCircle button CSS**

Remove or comment out `.nav-links a.myrecoverycircle-btn` and related rules (lines ~1373-1397 in base-inline.css) since that link is no longer in the top nav.

**Step 3: Update dark mode overrides**

Add dark mode rules for the Anchor AI CTA:

```css
[data-theme="dark"] .nav-links a.anchor-ai-cta {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: #fff !important;
}
```

**Step 4: Bump cache-busting version**

In `base.html`, update all `?v=20260304a` to `?v=20260304b` on static CSS/JS references.

**Step 5: Commit**

```bash
git add static/css/base-inline.css templates/base.html
git commit -m "feat: add Anchor AI CTA button styles, remove MyRecoveryCircle nav button"
```

---

### Task 6: Update Unauthenticated Nav

**Files:**
- Modify: `templates/base.html:332-334` (unauthenticated nav-right)

**Step 1: Replace login CTA with split buttons**

Replace line 333:
```html
<a href="{% url 'accounts:login' %}" class="cta-button">Login / Sign Up</a>
```

With:
```html
<a href="{% url 'accounts:login' %}" class="nav-login-link">Log in</a>
<a href="{% url 'accounts:register' %}" class="cta-button">Sign Up</a>
```

**Step 2: Add CSS for the login link**

Add to `base-inline.css`:

```css
.nav-login-link {
    color: var(--text-dark, #333);
    text-decoration: none;
    font-weight: 500;
    padding: 0.5rem 0.75rem;
    transition: color 0.3s ease;
}

.nav-login-link:hover {
    color: var(--primary-light);
}

[data-theme="dark"] .nav-login-link {
    color: #e0e0e0;
}
```

**Step 3: Commit**

```bash
git add templates/base.html static/css/base-inline.css
git commit -m "feat: split Login/Sign Up into separate nav buttons"
```

---

### Task 7: Smoke Test & Final Commit

**Step 1: Run Django system checks**

Run: `python manage.py check`
Expected: System check identified no issues.

**Step 2: Run template syntax check**

Run: `python manage.py validate_templates 2>&1 || echo "No validate_templates command, skip"`

**Step 3: Verify all URL names exist**

Run: `python manage.py shell -c "from django.urls import reverse; [reverse(u) for u in ['accounts:social_feed', 'accounts:daily_checkin', 'accounts:progress', 'accounts:recovery_coach', 'accounts:profile', 'accounts:groups_list', 'accounts:community', 'accounts:challenges_home', 'accounts:messages', 'accounts:milestones', 'accounts:edit_profile', 'accounts:subscription_management', 'accounts:invite_friends']]" 2>&1 | tail -5`

Expected: No `NoReverseMatch` errors. Note: `accounts:profile` requires `username` kwarg so it will error in this test — that's expected and fine since it's used with `user.username` in templates.

**Step 4: Visual verification checklist**

- [ ] Desktop: Only Feed, Check-in, Progress links + Anchor AI button visible
- [ ] Desktop: Avatar dropdown contains all moved links with icons
- [ ] Mobile: Slide menu has 2 sections (Quick Actions + More)
- [ ] Mobile: Bottom nav shows Feed, Check-in, Anchor AI, Profile
- [ ] Anchor AI button has gradient and pulse animation
- [ ] Dark mode: All elements styled correctly
- [ ] Unauthenticated: Shows Blog + Anchor AI CTA in nav, Log in + Sign Up buttons
- [ ] Native iOS tabs: Unchanged

**Step 5: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: nav redesign polish and adjustments"
```

# Landing Page Conversion-Focused Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite the homepage (`index.html`) to showcase MyRecoveryCircle and Anchor AI Coach with product screenshots, clear conversion flow, and reduced text-heavy content.

**Architecture:** Single-file template rewrite of `apps/core/templates/core/index.html`. All CSS is inline in `{% block extra_css %}`. All images already exist in `static/images/demo/`. No backend changes needed. The page uses Django template inheritance from `base.html` with blocks: `title`, `meta_description`, `meta_keywords`, `structured_data`, `extra_css`, `content`.

**Tech Stack:** Django templates, inline CSS, Font Awesome icons (already loaded via base.html from cdnjs), existing WebP/PNG screenshot assets.

**Design Doc:** `docs/plans/2026-02-25-landing-page-redesign-design.md`

---

### Task 1: Rewrite CSS Block — Hero, Trust Strip, How It Works

**Files:**
- Modify: `apps/core/templates/core/index.html:126-537` (replace entire `{% block extra_css %}` content)

**Context:** The current CSS block is 410 lines of inline styles (lines 126-537). We're replacing the entire block with new styles for the redesigned sections. The page extends `base.html` which provides the nav bar (fixed, ~70px tall) and footer.

**Step 1: Replace the CSS block**

Replace everything from `{% block extra_css %}` (line 126) through `{% endblock %}` (line 538) with new CSS covering all 9 sections. Key CSS classes needed:

```css
/* Reset body padding for landing page */
body { padding-top: 0; }

/* Section 1: Hero - split layout */
.hero { /* gradient bg, flexbox, min-height: 100vh, margin-top: -70px for nav overlap */ }
.hero-content { /* max-width: 1200px, grid: 1fr 1fr, gap: 3rem, align center */ }
.hero-text { /* text align left */ }
.hero-text h1 { /* 3.2rem, white, font-weight 800 */ }
.hero-text p { /* 1.3rem, rgba white 0.9 */ }
.hero-image { /* screenshot container with rounded corners, shadow, slight rotation */ }
.hero-image img { /* width 100%, border-radius 12px, box-shadow */ }
.trust-badges { /* flex, gap 1.5rem, margin-bottom 1.5rem */ }
.trust-badges span { /* flex, align-items center, gap 0.4rem, white text */ }
.cta-button { /* green bg #52b788, white text, rounded 50px, padding 1rem 3rem */ }
.cta-button-pulse { /* keyframe animation for glow */ }
.cta-secondary { /* transparent bg, white border, rounded */ }

/* Section 2: Trust strip */
.trust-strip { /* padding 2rem, bg white, flex center, gap 3rem */ }
.trust-strip-item { /* flex, align center, gap 0.5rem, color #555 */ }
.trust-strip-item i { /* color #52b788, font-size 1.2rem */ }

/* Section 3: How It Works */
.how-it-works { /* padding 5rem 2rem, bg white */ }
.steps-grid { /* grid 3 columns, gap 2rem, max-width 1000px, margin auto */ }
.step-card { /* text-align center, padding 2rem */ }
.step-number { /* 48px circle, gradient bg, white text, font-weight bold, margin auto */ }
.step-card h3 { /* color #1e4d8b, 1.3rem */ }
.step-card p { /* color #666, line-height 1.6 */ }

/* Section 4: MyRecoveryCircle showcase */
.showcase { /* padding 5rem 2rem */ }
.showcase-content { /* max-width 1200px, grid 1fr 1fr, gap 3rem, align center */ }
.showcase-content.reverse { /* direction rtl for alternate layout */ }
.showcase-content.reverse > * { /* direction ltr to fix child text */ }
.showcase-image img { /* width 100%, border-radius 15px, box-shadow */ }
.showcase-text h2 { /* color #1e4d8b, 2.2rem */ }
.showcase-text ul { /* list-style none, padding 0 */ }
.showcase-text ul li { /* padding 0.75rem 0, padding-left 2rem, relative */ }
.showcase-text ul li::before { /* checkmark, green color, absolute left */ }

/* Section 5: Anchor AI Coach showcase */
.anchor-showcase { /* padding 5rem 2rem, bg gradient blue */ }
.anchor-image { /* max-width 300px, margin auto */ }
.anchor-image img { /* width 100%, border-radius 50% or 15px */ }
.badge-new { /* inline-block, gradient bg, white text, rounded pill, small font */ }

/* Section 6: Feature grid */
.features { /* padding 5rem 2rem, bg white */ }
.features-grid { /* grid auto-fit minmax(300px, 1fr), gap 2rem */ }
.feature-card { /* bg white, padding 2rem, border-radius 15px, box-shadow, border, hover effect */ }
.feature-icon { /* font-size 2.5rem, gradient text */ }

/* Section 7: FAQ accordion */
.faq-section { /* padding 5rem 2rem, bg #f8f9fa */ }
.faq-item { /* bg white, border-radius 12px, margin-bottom 1rem, overflow hidden */ }
.faq-question { /* padding 1.5rem, cursor pointer, flex space-between, font-weight 600 */ }
.faq-answer { /* padding 0 1.5rem, max-height 0, overflow hidden, transition */ }
.faq-item.active .faq-answer { /* max-height 500px, padding-bottom 1.5rem */ }
.faq-chevron { /* transition rotate */ }
.faq-item.active .faq-chevron { /* transform rotate(180deg) */ }

/* Section 8: Final CTA */
.final-cta { /* padding 5rem 2rem, gradient blue bg, text center, white */ }

/* Section 9: Blog articles */
.blog-section { /* padding 4rem 2rem, bg white */ }
.blog-grid { /* grid auto-fit minmax(300px, 1fr), gap 1.5rem */ }
.blog-card { /* bg #f8f9fa, padding 1.5rem, border-radius 12px, shadow, hover */ }

/* Responsive */
@media (max-width: 768px) {
  .hero-content { grid-template-columns: 1fr; text-align: center; }
  .hero-image { display: none; /* hide on mobile for speed, or show below */ }
  .showcase-content { grid-template-columns: 1fr; }
  .showcase-content.reverse { direction: ltr; }
  .steps-grid { grid-template-columns: 1fr; }
  .features-grid { grid-template-columns: 1fr; }
  .blog-grid { grid-template-columns: 1fr; }
  .hero-text h1 { font-size: 2.2rem; }
  .trust-strip { flex-direction: column; gap: 1rem; }
  .anchor-showcase .showcase-content { grid-template-columns: 1fr; }
}
```

**Step 2: Verify template renders**

Run: `cd /Users/ryanpate/myrecoverypal && python manage.py check --deploy 2>&1 | head -20`

Expected: No template errors (deploy check may show warnings about HTTPS settings, that's fine).

**Step 3: Commit CSS changes**

```bash
git add apps/core/templates/core/index.html
git commit -m "refactor: rewrite landing page CSS for conversion-focused redesign"
```

---

### Task 2: Rewrite Content Block — Sections 1-3 (Hero, Trust Strip, How It Works)

**Files:**
- Modify: `apps/core/templates/core/index.html:540+` (replace `{% block content %}` through end)

**Context:** The current content block starts at line 540 and runs to line 820. We're replacing ALL of it. Keep the `{% block structured_data %}` block (lines 8-124) and `{% block title/meta_description/meta_keywords %}` blocks (lines 4-6) exactly as they are — they contain the JSON-LD schema and SEO meta tags. Only replace `{% block content %}`.

**Important:** The template uses `{% load static %}` on line 2 — this is already present and must stay. All image references use `{% static 'images/...' %}`.

**Step 1: Write sections 1-3**

Replace content block with:

```html
{% block content %}
<!-- Section 1: Hero - Split Layout -->
<section class="hero" id="home">
    <div class="hero-content">
        <div class="hero-text">
            <h1>Recovery Is Better Together</h1>
            <p>A social community where people in recovery connect, share their journey, and support each other — with a 24/7 AI coach when you need it most.</p>
            <div class="trust-badges">
                <span><i class="fas fa-check-circle"></i> Free to Join</span>
                <span><i class="fas fa-shield-alt"></i> Private & Secure</span>
                <span><i class="fas fa-robot"></i> 24/7 AI Coach</span>
            </div>
            {% if user.is_authenticated %}
            <a href="{% url 'accounts:social_feed' %}" class="cta-button">Go to MyRecoveryCircle</a>
            {% else %}
            <a href="{% url 'accounts:register' %}" class="cta-button cta-button-pulse">Join Free Today</a>
            <p style="margin-top: 0.75rem; font-size: 0.95rem; color: rgba(255,255,255,0.85);">No credit card required</p>
            <a href="{% url 'core:demo' %}" class="cta-secondary">See how it works &rarr;</a>
            {% endif %}
        </div>
        <div class="hero-image">
            <picture>
                <source srcset="{% static 'images/demo/feed.webp' %}" type="image/webp">
                <img src="{% static 'images/demo/feed.png' %}" alt="MyRecoveryCircle social feed showing sobriety tracking, community posts, and milestone celebrations" loading="eager">
            </picture>
        </div>
    </div>
</section>

<!-- Section 2: Trust Strip -->
<section class="trust-strip">
    <div class="trust-strip-item">
        <i class="fas fa-gift"></i>
        <span>Free to join — no credit card required</span>
    </div>
    <div class="trust-strip-item">
        <i class="fas fa-user-secret"></i>
        <span>Private & anonymous posting available</span>
    </div>
    <div class="trust-strip-item">
        <i class="fas fa-clock"></i>
        <span>24/7 AI-powered recovery support</span>
    </div>
</section>

<!-- Section 3: How It Works -->
<section class="how-it-works">
    <div class="container">
        <h2 class="section-title">How It Works</h2>
        <div class="steps-grid">
            <div class="step-card">
                <div class="step-number">1</div>
                <h3>Sign Up Free</h3>
                <p>Create your account in under a minute. Pick your interests and recovery stage to personalize your experience.</p>
            </div>
            <div class="step-card">
                <div class="step-number">2</div>
                <h3>Join MyRecoveryCircle</h3>
                <p>Your social feed for recovery. Share posts, follow others who inspire you, and celebrate milestones together.</p>
            </div>
            <div class="step-card">
                <div class="step-number">3</div>
                <h3>Get Support 24/7</h3>
                <p>Connect with the community and talk to Anchor, your AI recovery coach, whenever you need encouragement or coping strategies.</p>
            </div>
        </div>
    </div>
</section>
```

**Step 2: Verify page loads**

Run: `cd /Users/ryanpate/myrecoverypal && python manage.py check`

Expected: System check identified no issues.

**Step 3: Commit**

```bash
git add apps/core/templates/core/index.html
git commit -m "feat: add hero split layout, trust strip, and how-it-works sections"
```

---

### Task 3: Add Sections 4-5 (MyRecoveryCircle & Anchor Showcases)

**Files:**
- Modify: `apps/core/templates/core/index.html` (append after Section 3, before `{% endblock %}`)

**Step 1: Add MyRecoveryCircle showcase (Section 4)**

Insert after the How It Works section closing `</section>`:

```html
<!-- Section 4: MyRecoveryCircle Showcase -->
<section class="showcase" style="background: linear-gradient(135deg, #f0f7ff 0%, #f0faf5 100%);">
    <div class="showcase-content">
        <div class="showcase-image">
            <picture>
                <source srcset="{% static 'images/demo/create-post.webp' %}" type="image/webp">
                <img src="{% static 'images/demo/create-post.png' %}" alt="MyRecoveryCircle social feed with post composer, sobriety counter, and community activity" loading="lazy">
            </picture>
        </div>
        <div class="showcase-text">
            <h2>MyRecoveryCircle — Your Recovery Social Feed</h2>
            <p>A social network built specifically for people in recovery. Share your story with people who truly understand.</p>
            <ul>
                <li>Share your journey through posts, photos, and updates</li>
                <li>Celebrate milestones with reactions and comments</li>
                <li>Daily check-ins to track mood, cravings, and energy</li>
                <li>Follow others and build genuine connections</li>
                <li>Join recovery groups by addiction type, interest, or stage</li>
            </ul>
            {% if not user.is_authenticated %}
            <a href="{% url 'accounts:register' %}" class="cta-button" style="margin-top: 1rem;">Join the Circle</a>
            {% else %}
            <a href="{% url 'accounts:social_feed' %}" class="cta-button" style="margin-top: 1rem;">Go to MyRecoveryCircle</a>
            {% endif %}
        </div>
    </div>
</section>
```

**Step 2: Add Anchor AI Coach showcase (Section 5)**

Insert after Section 4:

```html
<!-- Section 5: Anchor AI Coach Showcase -->
<section class="anchor-showcase">
    <div class="showcase-content reverse">
        <div class="showcase-text" style="color: white;">
            <span class="badge-new">NEW</span>
            <h2 style="color: white;">Meet Anchor — Your 24/7 AI Recovery Coach</h2>
            <p style="color: rgba(255,255,255,0.9);">When cravings hit at 2 AM or you need someone to talk to, Anchor is there. Get personalized coping strategies, guided reflection, and encouragement — powered by AI, informed by evidence-based practices.</p>
            <ul style="color: rgba(255,255,255,0.9);">
                <li>Available 24 hours a day, 7 days a week</li>
                <li>3 free messages to try — no commitment</li>
                <li>Evidence-based CBT & mindfulness techniques</li>
                <li>Built-in crisis resources (988 Lifeline, 741741)</li>
            </ul>
            <a href="/accounts/recovery-coach/" class="cta-button" style="background: white; color: #1e4d8b; margin-top: 1rem;">Try Anchor Free</a>
            <p style="margin-top: 0.75rem; font-size: 0.85rem; color: rgba(255,255,255,0.7);">Not a replacement for professional medical or mental health treatment.</p>
        </div>
        <div class="anchor-image">
            <img src="{% static 'images/anchor-ai-coach.png' %}" alt="Anchor AI Recovery Coach - 24/7 AI-powered support for addiction recovery" loading="lazy">
        </div>
    </div>
</section>
```

**Step 3: Commit**

```bash
git add apps/core/templates/core/index.html
git commit -m "feat: add MyRecoveryCircle and Anchor AI Coach showcase sections"
```

---

### Task 4: Add Sections 6-7 (Feature Grid & FAQ Accordion)

**Files:**
- Modify: `apps/core/templates/core/index.html` (append after Section 5)

**Step 1: Add Feature Grid (Section 6)**

```html
<!-- Section 6: Feature Grid -->
<section class="features" id="features">
    <div class="container">
        <h2 class="section-title">Everything You Need for Recovery</h2>
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon"><i class="fas fa-pen-to-square"></i></div>
                <h3>Share Your Story</h3>
                <p>Post updates, share photos, and express yourself with a community that listens without judgment.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon"><i class="fas fa-trophy"></i></div>
                <h3>Celebrate Milestones</h3>
                <p>Track your sobriety days and celebrate every victory — from Day 1 to Year 10 and beyond.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon"><i class="fas fa-users"></i></div>
                <h3>Recovery Groups</h3>
                <p>Join groups by addiction type, recovery stage, location, or interest. Find your people.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon"><i class="fas fa-calendar-check"></i></div>
                <h3>Daily Check-ins</h3>
                <p>Track your mood, cravings, and energy daily. See trends over time and build healthy streaks.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon"><i class="fas fa-fire"></i></div>
                <h3>Recovery Challenges</h3>
                <p>Stay motivated with 30, 60, and 90-day challenges. Earn badges and compete on leaderboards.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon"><i class="fas fa-book"></i></div>
                <h3>Private Journal</h3>
                <p>Write privately about your journey. Your journal entries are always 100% private — never shared.</p>
            </div>
        </div>
    </div>
</section>
```

**Step 2: Add FAQ Accordion (Section 7)**

```html
<!-- Section 7: FAQ Accordion -->
<section class="faq-section">
    <div class="container" style="max-width: 800px; margin: 0 auto;">
        <h2 class="section-title">Frequently Asked Questions</h2>
        <div class="faq-list">
            <div class="faq-item">
                <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                    <span>Is MyRecoveryPal free to use?</span>
                    <i class="fas fa-chevron-down faq-chevron"></i>
                </div>
                <div class="faq-answer">
                    <p>MyRecoveryPal is free to join with core features like the social feed, groups, challenges, daily check-ins, and journaling. We also offer Premium for $4.99/month with advanced features like the AI Recovery Coach (20 messages/day), unlimited groups, detailed analytics, and more.</p>
                </div>
            </div>
            <div class="faq-item">
                <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                    <span>Who is MyRecoveryPal for?</span>
                    <i class="fas fa-chevron-down faq-chevron"></i>
                </div>
                <div class="faq-answer">
                    <p>MyRecoveryPal serves people in recovery from alcohol, drugs, or behavioral addictions, individuals in active addiction seeking support, family members and friends supporting loved ones, and anyone seeking mental health support and peer connection.</p>
                </div>
            </div>
            <div class="faq-item">
                <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                    <span>Is my information private and secure?</span>
                    <i class="fas fa-chevron-down faq-chevron"></i>
                </div>
                <div class="faq-answer">
                    <p>Yes, privacy and security are our top priorities. Your journal entries are always private, and you have full control over what information you share. We offer anonymous posting options in groups and never sell your data.</p>
                </div>
            </div>
            <div class="faq-item">
                <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                    <span>What is the AI Recovery Coach?</span>
                    <i class="fas fa-chevron-down faq-chevron"></i>
                </div>
                <div class="faq-answer">
                    <p>Anchor is a 24/7 AI-powered companion that provides personalized recovery support, evidence-based coping strategies informed by CBT and mindfulness, and encouragement. Free users can try it with 3 messages, while Premium members get 20 messages per day. Anchor is not a replacement for professional medical or mental health treatment.</p>
                </div>
            </div>
            <div class="faq-item">
                <div class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                    <span>Is MyRecoveryPal a replacement for professional treatment?</span>
                    <i class="fas fa-chevron-down faq-chevron"></i>
                </div>
                <div class="faq-answer">
                    <p>No. MyRecoveryPal is a peer support community and is not a replacement for professional medical treatment or therapy. We encourage members to work with healthcare professionals and use our platform as an additional support tool. If you're in crisis, call 988 (Suicide & Crisis Lifeline) or text HOME to 741741.</p>
                </div>
            </div>
        </div>
    </div>
</section>
```

**Step 3: Commit**

```bash
git add apps/core/templates/core/index.html
git commit -m "feat: add feature grid with icons and FAQ accordion section"
```

---

### Task 5: Add Sections 8-9 (Final CTA & Blog Articles) and Close Content Block

**Files:**
- Modify: `apps/core/templates/core/index.html` (append after Section 7, close with `{% endblock %}`)

**Step 1: Add Final CTA (Section 8)**

```html
<!-- Section 8: Final CTA -->
<section class="final-cta">
    <div class="container" style="max-width: 700px; margin: 0 auto;">
        <h2 style="font-size: 2.5rem; margin-bottom: 1rem; color: white;">Your Recovery Journey Starts Here</h2>
        <p style="font-size: 1.2rem; margin-bottom: 2rem; color: rgba(255,255,255,0.9); line-height: 1.6;">Join a supportive community that understands. Share your story, celebrate milestones, and get 24/7 support from people and AI who care.</p>
        {% if not user.is_authenticated %}
        <a href="{% url 'accounts:register' %}" class="cta-button" style="background: #52b788; color: white; font-size: 1.2rem; padding: 1rem 2.5rem;">Join Free Today</a>
        <p style="margin-top: 0.75rem; font-size: 0.9rem; color: rgba(255,255,255,0.7);">Free to join — no credit card required</p>
        {% else %}
        <a href="{% url 'accounts:social_feed' %}" class="cta-button" style="background: #52b788; color: white; font-size: 1.2rem; padding: 1rem 2.5rem;">Go to MyRecoveryCircle</a>
        {% endif %}
    </div>
</section>
```

**Step 2: Add Blog Articles (Section 9) — top 3 only**

```html
<!-- Section 9: Featured Blog Articles -->
<section class="blog-section">
    <div class="container" style="max-width: 1100px; margin: 0 auto;">
        <h2 class="section-title">Recovery Guides & Resources</h2>
        <p style="text-align: center; color: #666; margin-bottom: 2.5rem;">Expert advice and practical guides for your recovery journey</p>
        <div class="blog-grid">
            <a href="/blog/post/how-long-does-alcohol-withdrawal-last/" class="blog-card">
                <span class="blog-tag" style="background: linear-gradient(135deg, #1e4d8b, #4db8e8);">Health Guide</span>
                <h3>How Long Does Alcohol Withdrawal Last? Complete Timeline</h3>
                <p>Understand the stages, symptoms, and what to expect during alcohol detox.</p>
            </a>
            <a href="/blog/post/signs-of-alcoholism-self-assessment/" class="blog-card">
                <span class="blog-tag" style="background: linear-gradient(135deg, #52b788, #40916c);">Self-Assessment</span>
                <h3>Signs of Alcoholism: Self-Assessment Guide</h3>
                <p>Recognize the warning signs and take our confidential self-assessment quiz.</p>
            </a>
            <a href="/blog/post/how-to-stop-drinking-alcohol-guide/" class="blog-card">
                <span class="blog-tag" style="background: linear-gradient(135deg, #e74c3c, #c0392b);">Step-by-Step</span>
                <h3>How to Stop Drinking: Complete Guide</h3>
                <p>Practical strategies and proven methods to quit drinking for good.</p>
            </a>
        </div>
        <div style="text-align: center; margin-top: 2rem;">
            <a href="{% url 'blog:post_list' %}" style="display: inline-block; padding: 0.75rem 2rem; background: transparent; color: #1e4d8b; text-decoration: none; border: 2px solid #1e4d8b; border-radius: 25px; font-weight: 600; transition: all 0.3s;">
                View All Articles <i class="fas fa-arrow-right" style="margin-left: 0.5rem;"></i>
            </a>
        </div>
    </div>
</section>

{% endblock %}
```

**Step 3: Commit**

```bash
git add apps/core/templates/core/index.html
git commit -m "feat: add final CTA banner and blog articles section"
```

---

### Task 6: Visual QA & Responsive Testing

**Files:**
- Modify: `apps/core/templates/core/index.html` (CSS adjustments only)

**Step 1: Start dev server and test**

Run: `cd /Users/ryanpate/myrecoverypal && python manage.py runserver`

Open `http://localhost:8000/` in browser (make sure you're logged out).

**Step 2: Check each section visually**

Checklist:
- [ ] Hero: gradient visible, text left, screenshot right, CTA works
- [ ] Trust strip: 3 items in a row on desktop, stacked on mobile
- [ ] How It Works: 3 numbered steps in a row
- [ ] MyRecoveryCircle: screenshot left, text right, bullets have checkmarks
- [ ] Anchor: text left, logo right, blue gradient background, white text readable
- [ ] Feature grid: 6 cards, each has an icon, 2-3 per row
- [ ] FAQ: 5 items, click toggles open/close, chevron rotates
- [ ] Final CTA: blue gradient, button works
- [ ] Blog: 3 cards, links work
- [ ] Mobile (375px width): hero stacks vertically, all sections readable
- [ ] Nav bar doesn't overlap hero content
- [ ] Footer still renders normally

**Step 3: Fix any CSS issues found**

Adjust padding, font sizes, or responsive breakpoints as needed.

**Step 4: Commit fixes**

```bash
git add apps/core/templates/core/index.html
git commit -m "fix: landing page CSS adjustments from visual QA"
```

---

### Task 7: Final Commit & Cleanup

**Step 1: Verify no template errors**

Run: `cd /Users/ryanpate/myrecoverypal && python manage.py check`

Expected: System check identified no issues.

**Step 2: Verify collectstatic works**

Run: `cd /Users/ryanpate/myrecoverypal && python manage.py collectstatic --noinput --dry-run 2>&1 | tail -5`

Expected: No errors related to missing static files.

**Step 3: Final review of index.html**

Verify:
- `{% block structured_data %}` JSON-LD is preserved unchanged
- `{% block title %}`, `{% block meta_description %}`, `{% block meta_keywords %}` preserved
- All `{% static %}` paths reference existing files
- All `{% url %}` tags use valid route names
- No hardcoded localhost URLs
- `{% if user.is_authenticated %}` / `{% if not user.is_authenticated %}` used correctly

**Step 4: Squash into clean commit if desired, or leave as incremental commits**

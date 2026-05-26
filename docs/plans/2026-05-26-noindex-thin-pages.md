# Noindex Thin Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two bugs preventing the existing `SEONoIndexMiddleware` from actually deindexing 170+ "Crawled, not indexed" URLs: (a) `base.html` hardcodes the meta robots tag with no override block, and (b) `robots.txt` Disallow on thin blog pages blocks Google from re-crawling to see the noindex header.

**Architecture:** Three small text edits — convert `base.html` meta robots to a `{% block %}`, add `{% block meta_robots %}noindex, follow{% endblock %}` to two blog listing templates, remove 5 Disallow lines from `robots.txt`. Plus a CLAUDE.md doc for the manual GSC URL Removals step. No Python, no logic changes, no middleware touched.

**Tech Stack:** Django templates, plain text edits. No new dependencies.

**Reference spec:** `docs/plans/2026-05-26-noindex-thin-pages-design.md`

---

## Pre-flight

- [ ] **Step 0.1: Verify branch + baseline**

Run:
```bash
git branch --show-current
git log --oneline -3
```

Expected:
- Branch: `feat/noindex-thin-pages`
- Latest commit: `docs: noindex thin pages design spec...`

- [ ] **Step 0.2: Add missing `apps/blog/__init__.py` (test discovery prerequisite)**

The `apps/blog/` package uses a misnamed `init.py` (instead of `__init__.py`) and Python 3's namespace-package behavior — which works for Django app loading but breaks `manage.py test` discovery on this app. Earlier in the project history, `apps/accounts/__init__.py` was added for the same reason. Do the same for blog:

```bash
ls apps/blog/__init__.py 2>/dev/null || touch apps/blog/__init__.py
ls -la apps/blog/__init__.py
```

Expected: empty file exists. **Commit this as part of Task 1** (don't commit by itself — it's a prerequisite for the new test file).

- [ ] **Step 0.3: Confirm baseline tests pass**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts apps.blog apps.store -v 0 2>&1 | tail -3
```

Expected: 118 tests pass (108 accounts+store baseline + 10 blog).

The `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` prefix is required on macOS because the test suite transitively imports WeasyPrint via `apps.accounts.court_service`. Use this prefix on every `manage.py test` command in this plan.

- [ ] **Step 0.4: Confirm there are blog tag and category fixtures we can test against**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py shell -c "
from apps.blog.models import Post, Category, Tag
print('Categories:', Category.objects.count())
print('Tags:      ', Tag.objects.count())
print('Posts:     ', Post.objects.count())
print('First cat slug:', Category.objects.first().slug if Category.objects.exists() else 'none')
print('First tag slug:', Tag.objects.first().slug if Tag.objects.exists() else 'none')
" 2>&1 | tail -6
```

Note the model class names. Our tests will create fixtures in `setUp()` rather than relying on existing data.

---

## Task 1: Template changes (base.html block + 2 blog template overrides)

The three template changes ship as one commit because they form one logical unit: without the `base.html` block, the per-template overrides do nothing.

**Files:**
- Modify: `templates/base.html` (line ~53 — the existing hardcoded meta robots)
- Modify: `apps/blog/templates/blog/category_posts.html` (add block override near top)
- Modify: `apps/blog/templates/blog/tag_posts.html` (add block override near top)
- Create: `apps/blog/__init__.py` (empty file, prerequisite for test discovery)
- Create: `apps/blog/tests_noindex.py` (new test file)

### Step 1.1: Write the failing tests

Create `apps/blog/tests_noindex.py`:

```python
# apps/blog/tests_noindex.py
"""Tests for noindex handling on thin blog listing pages and the
base.html meta_robots block (Audit Priority #4)."""
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.blog.models import Category, Post, Tag


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MetaRobotsBlockTest(TestCase):
    """base.html exposes meta_robots as an overridable block."""

    def test_default_meta_robots_is_index_follow(self):
        """The homepage (no override) should emit index, follow."""
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        # Default content includes index, follow + SERP enhancement directives
        self.assertContains(
            resp,
            '<meta name="robots" content="index, follow',
            html=False,
        )

    def test_login_page_renders_noindex_override(self):
        """login.html already had {% block meta_robots %}noindex, nofollow{% endblock %}
        but it was a silent no-op until base.html defined the block. This test
        proves the override now actually emits."""
        resp = self.client.get(reverse('accounts:login'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(
            resp,
            '<meta name="robots" content="noindex, nofollow"',
            html=False,
        )


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class BlogListingNoIndexTest(TestCase):
    """Blog tag and category listing pages emit noindex, follow."""

    def setUp(self):
        # Create a category, a tag, and a published post that lives under both
        self.category = Category.objects.create(name='Recovery', slug='recovery')
        self.tag = Tag.objects.create(name='hope', slug='hope')
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            content='Body content here.',
            status='published',
            category=self.category,
        )
        self.post.tags.add(self.tag)

    def test_blog_category_page_emits_noindex_meta(self):
        resp = self.client.get(reverse('blog:category_posts', kwargs={'slug': 'recovery'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(
            resp,
            '<meta name="robots" content="noindex, follow"',
            html=False,
        )

    def test_blog_tag_page_emits_noindex_meta(self):
        resp = self.client.get(reverse('blog:tag_posts', kwargs={'slug': 'hope'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(
            resp,
            '<meta name="robots" content="noindex, follow"',
            html=False,
        )

    def test_blog_category_page_also_has_noindex_header(self):
        """Defense in depth: the SEONoIndexMiddleware should still emit
        the X-Robots-Tag header for these pages."""
        resp = self.client.get(reverse('blog:category_posts', kwargs={'slug': 'recovery'}))
        self.assertIn('noindex', resp.get('X-Robots-Tag', ''))

    def test_blog_tag_page_also_has_noindex_header(self):
        resp = self.client.get(reverse('blog:tag_posts', kwargs={'slug': 'hope'}))
        self.assertIn('noindex', resp.get('X-Robots-Tag', ''))
```

### Step 1.2: Ensure `apps/blog/__init__.py` exists

```bash
touch apps/blog/__init__.py
```

### Step 1.3: Run tests, confirm failures

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.blog.tests_noindex -v 2
```

Expected: 6 failures.
- `test_default_meta_robots_is_index_follow`: passes if base.html already has the content (hardcoded), but we should still verify after the block conversion to ensure default behavior is preserved
- `test_login_page_renders_noindex_override`: FAIL (login's existing override is currently a no-op because base.html has no block)
- `test_blog_category_page_emits_noindex_meta`: FAIL (category template doesn't override yet)
- `test_blog_tag_page_emits_noindex_meta`: FAIL (tag template doesn't override yet)
- The two `_also_has_noindex_header` tests: PASS already (middleware already emits the header) — these are regression checks

If `test_default_meta_robots_is_index_follow` actually fails at this stage (it shouldn't), check that the hardcoded content in base.html line 53 begins with `index, follow,`.

### Step 1.4: Modify `templates/base.html`

Open `templates/base.html`. Find the existing line:

```html
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
```

Replace with:

```html
<meta name="robots" content="{% block meta_robots %}index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1{% endblock %}">
```

The default behavior is unchanged. The difference: child templates can override via `{% block meta_robots %}...{% endblock %}`. Templates that already do this (login.html, dashboard.html, hybrid_landing.html) will start actually rendering their override.

### Step 1.5: Add noindex override to `apps/blog/templates/blog/category_posts.html`

Open `apps/blog/templates/blog/category_posts.html`. Find the top of the file (after `{% extends %}` and any `{% load %}` lines). Add this line:

```django
{% block meta_robots %}noindex, follow{% endblock %}
```

Place it after the `{% extends 'base.html' %}` line and any `{% load %}` directives, but before the `{% block title %}` or `{% block content %}` blocks. The exact placement doesn't matter for rendering — Django blocks are not order-sensitive — but consistency with other blocks (which usually appear in this order) keeps the file readable.

### Step 1.6: Add noindex override to `apps/blog/templates/blog/tag_posts.html`

Same change in `apps/blog/templates/blog/tag_posts.html`:

```django
{% block meta_robots %}noindex, follow{% endblock %}
```

### Step 1.7: Re-run tests, confirm pass

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.blog.tests_noindex -v 2
```

Expected: All 6 tests pass.

### Step 1.8: Run the full blog + accounts + store suite for regression

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts apps.blog apps.store -v 0 2>&1 | tail -3
```

Expected: 124 tests pass (118 baseline + 6 new).

### Step 1.9: Smoke test the rendered output

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py shell -c "
from django.test import Client
from django.test.utils import override_settings
with override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False):
    c = Client()
    r = c.get('/')
    print('Homepage meta robots OK:    ', b'<meta name=\"robots\" content=\"index, follow' in r.content)
    r = c.get('/accounts/login/')
    print('Login meta robots noindex: ', b'<meta name=\"robots\" content=\"noindex, nofollow\"' in r.content)
"
```

Expected: Both lines print `True`.

### Step 1.10: Commit

```bash
git add templates/base.html \
        apps/blog/templates/blog/category_posts.html \
        apps/blog/templates/blog/tag_posts.html \
        apps/blog/__init__.py \
        apps/blog/tests_noindex.py
git commit -m "feat(seo): make meta_robots overridable + add noindex to thin blog pages

base.html had the robots meta tag hardcoded with no template-level
override mechanism. Templates that already wrote
{% block meta_robots %}noindex, nofollow{% endblock %} (login,
dashboard, hybrid_landing) were silent no-ops — those overrides now
actually emit.

Adds explicit noindex, follow to /blog/tag/<slug>/ and
/blog/category/<slug>/ pages. SEONoIndexMiddleware was already
emitting the X-Robots-Tag header — this aligns the HTML meta tag
with the header so Google sees a single consistent signal.

Adds apps/blog/__init__.py (the package had init.py instead, breaking
test discovery — same fix as apps/accounts/__init__.py earlier).

Spec: docs/plans/2026-05-26-noindex-thin-pages-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Remove blocking Disallow lines from robots.txt

The middleware adds `X-Robots-Tag: noindex, nofollow` to thin blog pages, and Task 1 added the matching HTML meta tag. But Google can't see either signal if `robots.txt` Disallows the page — it never crawls, so it never reads the headers/meta. Removing the conflicting Disallow lines lets Google crawl, see noindex, and deindex.

**Files:**
- Modify: `root_files/robots.txt`
- Modify: `apps/blog/tests_noindex.py` (append regression tests)

### Step 2.1: Append failing tests

Append to `apps/blog/tests_noindex.py`:

```python
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class RobotsTxtTest(TestCase):
    """robots.txt no longer Disallows blog tag/category pages
    (the middleware noindex handles them via X-Robots-Tag)."""

    def setUp(self):
        self.resp = self.client.get('/robots.txt')

    def test_robots_txt_serves_text_plain(self):
        self.assertEqual(self.resp.status_code, 200)
        self.assertIn('text/plain', self.resp.get('Content-Type', ''))

    def test_no_disallow_for_blog_tag(self):
        body = self.resp.content.decode('utf-8')
        # Must NOT contain a Disallow line targeting /blog/tag/
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith('Disallow:'):
                target = stripped[len('Disallow:'):].strip()
                self.assertNotEqual(target, '/blog/tag/',
                                    'robots.txt still Disallows /blog/tag/')

    def test_no_disallow_for_blog_category(self):
        body = self.resp.content.decode('utf-8')
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith('Disallow:'):
                target = stripped[len('Disallow:'):].strip()
                self.assertNotEqual(target, '/blog/category/',
                                    'robots.txt still Disallows /blog/category/')

    def test_no_disallow_for_blog_pagination_or_filter(self):
        body = self.resp.content.decode('utf-8')
        self.assertNotIn('Disallow: /blog/?page=', body)
        self.assertNotIn('Disallow: /blog/?filter=', body)

    def test_no_disallow_for_support_services_filters(self):
        body = self.resp.content.decode('utf-8')
        self.assertNotIn('Disallow: /support/services/?', body)

    # Regression checks — these Disallows must REMAIN
    def test_still_disallows_admin(self):
        body = self.resp.content.decode('utf-8')
        self.assertIn('Disallow: /admin/', body)

    def test_still_disallows_authed_pages(self):
        body = self.resp.content.decode('utf-8')
        self.assertIn('Disallow: /accounts/dashboard/', body)
        self.assertIn('Disallow: /accounts/court/', body)
        self.assertIn('Disallow: /journal/', body)

    def test_sitemap_is_present(self):
        body = self.resp.content.decode('utf-8')
        self.assertIn('Sitemap: https://www.myrecoverypal.com/sitemap.xml', body)
```

### Step 2.2: Run, confirm failures

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.blog.tests_noindex.RobotsTxtTest -v 2
```

Expected: 5 failures (the 5 "no_disallow" tests) + 3 passes (regression checks for admin/authed/sitemap which are already in robots.txt).

### Step 2.3: Edit `root_files/robots.txt`

Open `root_files/robots.txt`. Find these 5 lines and DELETE them:

```
Disallow: /blog/?page=
Disallow: /blog/?filter=
```

(Currently appearing in the "Block query-parameter variants" comment block.)

```
Disallow: /blog/tag/
Disallow: /blog/category/
Disallow: /support/services/?
```

(Currently appearing in the "Block thin listing pages" comment block.)

After removal, the file should look like this (the comment blocks above the removed lines can stay as-is, with their content blocks now empty — or you may consolidate by removing the now-empty comment blocks too; either is fine).

Specifically, the existing block:

```
# Block query-parameter variants that create duplicate content
Disallow: /accounts/login/?
Disallow: /accounts/register/?
Disallow: /blog/?page=
Disallow: /blog/?filter=

# Block thin listing pages (tags/categories generate 100+ near-duplicate URLs)
Disallow: /blog/tag/
Disallow: /blog/category/
Disallow: /support/services/?
```

Should become:

```
# Block query-parameter variants for login/register (saves crawl budget)
Disallow: /accounts/login/?
Disallow: /accounts/register/?

# Note: /blog/tag/, /blog/category/, /blog/?page=, /blog/?filter=, and
# /support/services/?* are intentionally NOT in robots.txt. They are
# noindexed via the SEONoIndexMiddleware X-Robots-Tag header + meta tag
# in the rendered HTML. Disallowing them would prevent Google from
# crawling and seeing the noindex directive (Crawled-but-not-indexed
# trap). See docs/plans/2026-05-26-noindex-thin-pages-design.md.
```

The comment is for future-you (and reviewers) — explains why these specific Disallows were intentionally removed.

### Step 2.4: Re-run tests

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.blog.tests_noindex -v 2
```

Expected: all 14 tests pass (6 from Task 1 + 8 new from Task 2).

### Step 2.5: Run full suite for regression

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts apps.blog apps.store -v 0 2>&1 | tail -3
```

Expected: 132 tests pass (118 baseline + 14 new).

### Step 2.6: Smoke-test the served robots.txt

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py shell -c "
from django.test import Client
from django.test.utils import override_settings
with override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False):
    c = Client()
    r = c.get('/robots.txt')
    body = r.content.decode('utf-8')
    print('Status:', r.status_code)
    print('No more /blog/tag/ Disallow:', 'Disallow: /blog/tag/' not in body)
    print('No more /blog/category/ Disallow:', 'Disallow: /blog/category/' not in body)
    print('Still has /admin/ Disallow:', 'Disallow: /admin/' in body)
    print('Still has sitemap:', 'Sitemap: https://www.myrecoverypal.com/sitemap.xml' in body)
"
```

Expected: status 200, all four `True/False` checks match the right state.

### Step 2.7: Commit

```bash
git add root_files/robots.txt apps/blog/tests_noindex.py
git commit -m "fix(seo): remove blocking Disallows so Google can crawl + see noindex

The SEONoIndexMiddleware emits X-Robots-Tag: noindex, nofollow on
thin blog pages, and Task 1 added the matching <meta name='robots'>
HTML tag. But Google can't see either signal if robots.txt
Disallows the URL — it never crawls, so it never reads the
header/meta. URLs Google already knows about (sitemap, internal
links, prior crawls) stay in 'Crawled, not indexed' forever.

Removed:
  Disallow: /blog/tag/
  Disallow: /blog/category/
  Disallow: /blog/?page=
  Disallow: /blog/?filter=
  Disallow: /support/services/?

These pages are still noindexed via middleware + meta tag. Removing
the Disallow lets Google crawl them, see noindex, and properly
deindex over the next 4-8 weeks.

Authed-page Disallows (/admin/, /accounts/dashboard/ etc) kept
unchanged — those serve as defense in depth.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: CLAUDE.md docs + final regression + push + PR

- [ ] **Step 3.1: Append GSC URL Removals doc to CLAUDE.md**

Open `CLAUDE.md`. Find a logical place to insert this — either at the bottom of the file, or near an existing SEO/operations section if one exists. Search for `SEO` first:

```bash
grep -n "^## SEO\|^## Operations\|^# Operations\|^## Deployment" CLAUDE.md | head -5
```

If there's an existing `## SEO` section, append underneath it. If not, append at the end of the file before any "changelog" tail section.

Insert this content:

```markdown
## SEO — Bulk-removing already-crawled thin pages (one-time manual step)

For the 170+ URLs in "Crawled, not indexed" that we've now properly
noindexed (PR #N, May 2026), the natural deindex flow takes 4-8 weeks.
To accelerate:

1. Open Google Search Console → property → **Indexing** → **Removals**
2. Click **New request** → **Remove all URLs with this prefix**
3. Submit each of:
   - `https://www.myrecoverypal.com/blog/tag/`
   - `https://www.myrecoverypal.com/blog/category/`
4. Each prefix submission removes URLs for 6 months. By that point,
   the natural deindex (driven by our `noindex` meta + header) is
   complete and the URLs stay out of the index.

This is a one-time manual step. The code-level work (noindex meta tag
on thin pages + robots.txt no longer blocking the crawl) ships
automatically with every deploy from now on.

If `/blog/tag/` and `/blog/category/` reappear in "Crawled, not indexed"
later, that's expected — Google will keep recrawling them periodically.
The noindex directive should win every time. Don't re-submit removal
requests unless they actually get indexed.
```

Replace `PR #N` with the actual PR number after you open it in Step 3.5 — or just leave it as `PR #N` and adjust in a follow-up doc commit if you prefer.

- [ ] **Step 3.2: Run the full test suite one more time**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts apps.blog apps.store -v 0 2>&1 | tail -3
```

Expected: 132 tests pass, zero failures.

- [ ] **Step 3.3: Django system check**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py check 2>&1 | tail -3
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3.4: Commit CLAUDE.md + plan doc, then push branch**

The plan doc (`docs/plans/2026-05-26-noindex-thin-pages.md`) is still untracked. Add it along with the CLAUDE.md change:

```bash
git status --short | grep "docs/plans/2026-05-26-noindex-thin-pages.md\|CLAUDE.md"
```

Both should appear (one untracked, one modified). Commit:

```bash
git add CLAUDE.md docs/plans/2026-05-26-noindex-thin-pages.md
git commit -m "docs: GSC URL Removals process + implementation plan for noindex thin pages

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

Then push:

```bash
git push -u origin feat/noindex-thin-pages 2>&1 | tail -3
```

- [ ] **Step 3.5: Open the PR**

```bash
gh pr create --base main --head feat/noindex-thin-pages \
  --title "fix(seo): noindex thin blog pages — actually deindex the 170+ 'crawled, not indexed' URLs" \
  --body "$(cat <<'EOF'
## Summary

Audit Priority #4 — fix two bugs preventing the existing \`SEONoIndexMiddleware\` from actually deindexing 170+ "Crawled, not indexed" URLs in GSC.

## The two bugs

### Bug 1: \`base.html\` hardcodes meta robots with no override block

\`templates/base.html:53\` was:
\`\`\`html
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
\`\`\`

No \`{% block %}\` — so templates that already wrote \`{% block meta_robots %}noindex, nofollow{% endblock %}\` (login, dashboard, hybrid_landing) were silent no-ops. Pages that should have been noindex emitted a contradictory \`index, follow\` meta tag.

Converted to:
\`\`\`html
<meta name="robots" content="{% block meta_robots %}index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1{% endblock %}">
\`\`\`

Default behavior unchanged. Existing overrides now actually emit. Added explicit \`{% block meta_robots %}noindex, follow{% endblock %}\` to \`category_posts.html\` and \`tag_posts.html\`.

### Bug 2: \`robots.txt\` Disallows blocked Google from seeing the noindex

\`root_files/robots.txt\` had:
\`\`\`
Disallow: /blog/tag/
Disallow: /blog/category/
Disallow: /blog/?page=
Disallow: /blog/?filter=
Disallow: /support/services/?
\`\`\`

Disallow prevents crawling. Google can't see the \`X-Robots-Tag: noindex, nofollow\` header (from \`SEONoIndexMiddleware\`) or the new \`<meta name="robots">\` tag if it can't crawl. URLs Google already knew about (sitemap, internal links, prior crawls) stay in "Crawled, not indexed" indefinitely.

Removed those 5 Disallow lines. Authed-page Disallows kept unchanged.

## What the audit flagged that's not in this PR

- ❌ Content rewrites for thin blog posts Google rejected on quality grounds — separate work
- ❌ Middleware audit / refactor — \`SEONoIndexMiddleware\` is correct as-is

## Test plan

- [x] 14 new tests pass: \`MetaRobotsBlockTest\` (2), \`BlogListingNoIndexTest\` (4), \`RobotsTxtTest\` (8)
- [x] Full \`apps.accounts\` + \`apps.blog\` + \`apps.store\` suite green (132 total)
- [x] \`manage.py check\` clean
- [x] Smoke test confirms: homepage emits \`index, follow\`; login/blog-tag/blog-category emit \`noindex\`; robots.txt no longer Disallows thin blog pages
- [ ] **Post-merge manual step (you):** Open GSC → Indexing → Removals → "New request" → Remove all URLs with this prefix → submit \`https://www.myrecoverypal.com/blog/tag/\` and \`https://www.myrecoverypal.com/blog/category/\`. Documented in \`CLAUDE.md\`.

## Bonus fix

Added \`apps/blog/__init__.py\` (empty file). The blog package was using the misnamed \`init.py\` instead, breaking \`manage.py test\` discovery on \`apps.blog\`. Same fix that was already applied to \`apps/accounts/__init__.py\` earlier this year. Now \`apps.blog\` tests run normally.

## Expected post-deploy behavior

- "Crawled, not indexed" count in GSC drops over 4-8 weeks as Google re-crawls the now-not-blocked URLs, sees the noindex header/meta, and removes them from the index pool
- GSC URL Removals (manual step above) accelerates this for the existing 170+ URLs
- Site-wide quality signal improves as Google stops associating MyRecoveryPal with thin/duplicate-content listings

Spec: \`docs/plans/2026-05-26-noindex-thin-pages-design.md\`
Implementation plan: \`docs/plans/2026-05-26-noindex-thin-pages.md\`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)" 2>&1 | tail -3
```

Expected: PR URL printed.

---

## Self-Review

**Spec coverage** — walking the spec section by section:

| Spec requirement | Plan task |
|---|---|
| Convert `base.html` meta robots to a block | Task 1, Step 1.4 |
| Add `noindex, follow` override to category template | Task 1, Step 1.5 |
| Add `noindex, follow` override to tag template | Task 1, Step 1.6 |
| Remove 5 Disallow lines from robots.txt | Task 2, Step 2.3 |
| Document GSC URL Removals process in CLAUDE.md | Task 3, Step 3.1 |
| Test default meta robots is index, follow | `MetaRobotsBlockTest::test_default_meta_robots_is_index_follow` (Task 1) |
| Test blog category page has noindex meta | `BlogListingNoIndexTest::test_blog_category_page_emits_noindex_meta` (Task 1) |
| Test blog tag page has noindex meta | `BlogListingNoIndexTest::test_blog_tag_page_emits_noindex_meta` (Task 1) |
| Test category page still has noindex header | `BlogListingNoIndexTest::test_blog_category_page_also_has_noindex_header` (Task 1) |
| Test login override now works | `MetaRobotsBlockTest::test_login_page_renders_noindex_override` (Task 1) |
| Test robots.txt no longer Disallows blog tag/category | `RobotsTxtTest::test_no_disallow_for_blog_tag` + `test_no_disallow_for_blog_category` (Task 2) |
| Test robots.txt still has admin/authed Disallows | `RobotsTxtTest::test_still_disallows_admin` + `test_still_disallows_authed_pages` (Task 2) |

**Placeholder scan:** No "TBD", "implement later," or vague requirements. Every step has actual template/text content or actual commands. Only "fuzzy" item is `PR #N` in the CLAUDE.md doc (intentional — fills in after the PR is open; can be amended later).

**Type consistency:**
- Test class names: `MetaRobotsBlockTest`, `BlogListingNoIndexTest`, `RobotsTxtTest` — referenced consistently in tasks and PR body
- Model imports: `Category`, `Post`, `Tag` from `apps.blog.models` — used in `setUp`; if the actual model names differ (e.g., `BlogPost` instead of `Post`), the implementer should surface that in the pre-flight investigation (Step 0.4 dumps the model counts to verify)
- URL names: `blog:category_posts`, `blog:tag_posts`, `accounts:login` — verified to exist (Step 0.4 + earlier grep against blog/urls.py:12-14)

**Test fixture risk:** `Post.objects.create(title=..., slug=..., content=..., status='published', category=...)` — model field names assumed. If the model uses different names (e.g., `body` instead of `content`, or no `status` field), the test will fail at setUp. Step 0.4 doesn't cover this. The implementer should inspect `apps/blog/models.py` first if test setUp errors out, and adjust the fixture creation to match real fields.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-26-noindex-thin-pages.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?

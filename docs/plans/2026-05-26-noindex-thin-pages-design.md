# Noindex Thin Pages (Audit Priority #4) — Design

**Date:** 2026-05-26
**Status:** Approved direction; implementation plan to follow
**Audit reference:** GSC Coverage Drilldown (2026-05-23) shows 170+ URLs in "Crawled — currently not indexed." Most are blog tag/category listing pages or filter/pagination variants. The audit's recommendation was to add explicit `noindex` directives. This spec fixes two existing bugs blocking that from working.

---

## Goal

Make Google's noindex signal actually reach Google for thin/auto-generated pages, so the 170+ "Crawled, not indexed" URLs deindex properly over the next 4-8 weeks.

## Why this change

Two real bugs prevent the existing noindex infrastructure from working:

### Bug 1 — Conflicting signals in `base.html`

`templates/base.html` line 53 hardcodes `<meta name="robots" content="index, follow, ...">` on every page with no override mechanism. Some templates already write `{% block meta_robots %}noindex, nofollow{% endblock %}` (login, dashboard, hybrid_landing) — **but those overrides are silently ignored** because `base.html` doesn't define the block. Pages that should be noindex emit a contradictory `index, follow` meta tag.

### Bug 2 — `robots.txt` Disallow blocks crawling

`root_files/robots.txt` has `Disallow: /blog/tag/` and `Disallow: /blog/category/`. Disallow tells Google **not to crawl**, which means Google never re-crawls the page to **see** the `SEONoIndexMiddleware` noindex header. URLs Google already knows about (from sitemap entries, internal links, or prior crawls) stay in "crawled, not indexed" indefinitely because Google can't confirm the noindex.

The audit warned about exactly this: *"Disallow alone doesn't deindex."*

### What's already correct (no change needed)

`apps/accounts/middleware.py::SEONoIndexMiddleware` already emits `X-Robots-Tag: noindex, nofollow` on the right URL patterns:
- `/blog/tag/*` and `/blog/category/*` listing pages
- Any `/blog/*?filter=` or `/blog/*?page=` query variant
- All authenticated `/accounts/<private>/` pages
- Login/register with `?next=` parameters

The middleware is the source of truth — we just need to clear the conflicting/blocking signals so Google can act on its directive.

## Approved direction

Locked decisions:

| Topic | Decision |
|---|---|
| Scope | Fix the two bugs only. No content rewrites, no middleware audits, no context-processor refactor. |
| Robots directive for thin blog pages | `noindex, follow` (not `nofollow`) — Google still crawls outbound links to real blog posts so the content gets indexed; only the listing page is excluded from the index. |
| Auth-page Disallows in robots.txt | Keep all `/accounts/<private>/` Disallow lines (defense in depth — Google can't access these anyway, no point letting it try). |
| Login/register `?next=` Disallows | Keep (crawl-budget savings; not blocking real noindex flow since the middleware already noindexes login `?next=`). |

## Implementation

### Change 1 — `templates/base.html`

Replace line 53:

```html
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
```

with:

```html
<meta name="robots" content="{% block meta_robots %}index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1{% endblock %}">
```

Default behavior preserved (`index, follow` + SERP enhancement directives). Templates can override via the block.

**Knock-on effect:** Existing overrides in `login.html`, `dashboard.html`, and `hybrid_landing.html` start actually working. Their current `{% block meta_robots %}noindex, nofollow{% endblock %}` lines are silent no-ops today; after this change, those pages will emit the noindex meta tag in the rendered HTML. This is the intended fix.

### Change 2 — `apps/blog/templates/blog/category_posts.html`

Add at the top (after `{% extends %}` and `{% load %}` lines):

```django
{% block meta_robots %}noindex, follow{% endblock %}
```

### Change 3 — `apps/blog/templates/blog/tag_posts.html`

Same addition:

```django
{% block meta_robots %}noindex, follow{% endblock %}
```

`tag_posts.html` is a separate template from `post_list.html` per the existing `TagListView` — confirmed via `apps/blog/views.py:146`. No conditional logic needed.

### Change 4 — `root_files/robots.txt`

Remove these 5 lines:
```
Disallow: /blog/?page=
Disallow: /blog/?filter=
Disallow: /blog/tag/
Disallow: /blog/category/
Disallow: /support/services/?
```

Keep everything else (auth Disallows, system Disallows, all Allows, sitemap, crawl-delay).

After removal, robots.txt will have an explicit `Allow: /blog/` (line 8) that covers the now-removed Disallows. Google will crawl those URLs, hit the `X-Robots-Tag: noindex, nofollow` header from `SEONoIndexMiddleware`, and deindex over time.

### Change 5 — `CLAUDE.md`

Append a small section under "SEO" (or create one if none exists) documenting the manual GSC URL Removals step:

```markdown
## SEO — Bulk-removing already-crawled thin pages (GSC)

For 170+ URLs in "Crawled, not indexed" that we've now properly noindexed, the natural deindex flow takes 4-8 weeks. To accelerate:

1. Google Search Console → property → Indexing → Removals → "New request"
2. Choose "Remove all URLs with this prefix"
3. Submit each of:
   - `https://www.myrecoverypal.com/blog/tag/`
   - `https://www.myrecoverypal.com/blog/category/`
4. Each submission removes the URLs for 6 months. By that point, the natural deindex (driven by our noindex meta + header) is complete.

Do this once after deploying the noindex fixes. Not a recurring task.
```

## Files affected

| File | Change |
|---|---|
| `templates/base.html` | Convert hardcoded meta robots → `{% block meta_robots %}` |
| `apps/blog/templates/blog/category_posts.html` | Add `{% block meta_robots %}noindex, follow{% endblock %}` |
| `apps/blog/templates/blog/tag_posts.html` | Add `{% block meta_robots %}noindex, follow{% endblock %}` |
| `root_files/robots.txt` | Remove 5 Disallow lines |
| `CLAUDE.md` | Document manual GSC URL Removals step |
| `apps/blog/tests_noindex.py` (new) | Test suite |

No middleware changes. No view changes. No model changes. No migrations. No new dependencies.

## Test coverage

| Test | Asserts |
|---|---|
| `test_default_meta_robots_is_index_follow` | GET `/` HTML contains `<meta name="robots" content="index, follow` |
| `test_blog_category_page_has_noindex_meta` | GET `/blog/category/<slug>/` HTML contains `noindex, follow` in the meta robots tag |
| `test_blog_tag_page_has_noindex_meta` | GET `/blog/tag/<slug>/` HTML contains `noindex, follow` in the meta robots tag |
| `test_blog_category_page_still_has_noindex_header` | GET `/blog/category/<slug>/` response has `X-Robots-Tag: noindex, nofollow` (middleware regression check) |
| `test_login_page_renders_noindex_override` | GET `/accounts/login/` HTML contains `noindex` (regression test — the existing override should now actually emit) |
| `test_robots_txt_does_not_disallow_blog_tag_category` | GET `/robots.txt` body does NOT contain `Disallow: /blog/tag/` or `Disallow: /blog/category/` |
| `test_robots_txt_still_disallows_admin_and_authed` | GET `/robots.txt` body still contains `Disallow: /admin/` and `Disallow: /accounts/dashboard/` (regression check) |

## Success criteria

1. Hard-refreshing homepage shows `<meta name="robots" content="index, follow, ...">` in source (unchanged behavior)
2. Hard-refreshing a blog tag page shows `<meta name="robots" content="noindex, follow">` in source AND `X-Robots-Tag: noindex, nofollow` in response headers
3. `/robots.txt` no longer Disallows `/blog/tag/`, `/blog/category/`, `/blog/?page=`, `/blog/?filter=`, `/support/services/?`
4. `/accounts/login/` source now shows the noindex meta tag (verification that the broken override is now working)
5. All 7 tests above pass
6. Full `apps.accounts`, `apps.blog`, `apps.store` test suites stay green
7. After deploy, GSC URL Removals submitted manually for `/blog/tag/` and `/blog/category/` prefixes
8. Over the following 4-8 weeks, the "Crawled, not indexed" count in GSC drops as Google honors the noindex on re-crawl

## Out of scope (explicit non-goals)

- ❌ Content rewrites for thin blog posts Google rejected on quality grounds (separate work — those need writing/editing, not noindex)
- ❌ Middleware refactor — `SEONoIndexMiddleware` is correct as-is
- ❌ Adding more URL patterns to `NOINDEX_PREFIXES` — current coverage matches the GSC drilldown findings
- ❌ Performing the actual GSC URL Removals (documented as manual user step only)
- ❌ Context-processor approach (overkill for this scope)
- ❌ noindex for `/accounts/court/` (already covered by middleware + Disallow)
- ❌ Adjusting `max-image-preview` or other SERP enhancement directives

## Implementation hand-off notes

For writing-plans:
- Pure template/text edits — no Python logic changes
- TDD applies via render-bytes assertions (assert the meta tag is or isn't in the HTML response)
- macOS test runs need `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (project convention)
- Estimated effort: 1-2 hours implementation, 5 minutes manual GSC step post-deploy
- One PR, 5 files modified + 1 new test file

## Open questions

None. All decisions locked.

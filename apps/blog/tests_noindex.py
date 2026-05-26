# apps/blog/tests_noindex.py
"""Tests for noindex handling on thin blog listing pages and the
base.html meta_robots block (Audit Priority #4)."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.blog.models import Category, Post, Tag

User = get_user_model()


# Override STATICFILES_STORAGE during tests because the production
# CompressedManifestStaticFilesStorage requires `collectstatic` to have
# run first (it builds a manifest mapping). Tests don't run collectstatic,
# so any `{% static %}` reference to a file the manifest hasn't seen will
# raise ValueError. Plain StaticFilesStorage skips the manifest lookup.
_TEST_STORAGE = {
    'PREPEND_WWW': False,
    'SECURE_SSL_REDIRECT': False,
    'STATICFILES_STORAGE': 'django.contrib.staticfiles.storage.StaticFilesStorage',
}


@override_settings(**_TEST_STORAGE)
class MetaRobotsBlockTest(TestCase):
    """base.html exposes meta_robots as an overridable block."""

    def test_default_meta_robots_is_index_follow(self):
        """The homepage (no override) should emit index, follow."""
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
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


@override_settings(**_TEST_STORAGE)
class BlogListingNoIndexTest(TestCase):
    """Blog tag and category listing pages emit noindex, follow."""

    def setUp(self):
        # Create a category, a tag, and a published post that lives under both.
        self.author = User.objects.create_user(
            username='blogauthor',
            email='author@example.com',
            password='testpass123',
        )
        self.category = Category.objects.create(name='Recovery', slug='recovery')
        self.tag = Tag.objects.create(name='hope', slug='hope')
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            content='Body content here.',
            status='published',
            category=self.category,
            author=self.author,
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


def _response_body(response):
    """Read body from either an HttpResponse or a streaming response
    (WhiteNoise serves /robots.txt as a FileResponse, which has no
    .content attribute — use streaming_content instead)."""
    if getattr(response, 'streaming', False):
        return b''.join(response.streaming_content).decode('utf-8')
    return response.content.decode('utf-8')


@override_settings(**_TEST_STORAGE)
class RobotsTxtTest(TestCase):
    """robots.txt no longer Disallows blog tag/category pages
    (the middleware noindex handles them via X-Robots-Tag)."""

    def setUp(self):
        self.resp = self.client.get('/robots.txt')
        self.body = _response_body(self.resp)

    def test_robots_txt_serves_text_plain(self):
        self.assertEqual(self.resp.status_code, 200)
        self.assertIn('text/plain', self.resp.get('Content-Type', ''))

    def test_no_disallow_for_blog_tag(self):
        body = self.body
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith('Disallow:'):
                target = stripped[len('Disallow:'):].strip()
                self.assertNotEqual(target, '/blog/tag/',
                                    'robots.txt still Disallows /blog/tag/')

    def test_no_disallow_for_blog_category(self):
        body = self.body
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith('Disallow:'):
                target = stripped[len('Disallow:'):].strip()
                self.assertNotEqual(target, '/blog/category/',
                                    'robots.txt still Disallows /blog/category/')

    def test_no_disallow_for_blog_pagination_or_filter(self):
        body = self.body
        self.assertNotIn('Disallow: /blog/?page=', body)
        self.assertNotIn('Disallow: /blog/?filter=', body)

    def test_no_disallow_for_support_services_filters(self):
        body = self.body
        self.assertNotIn('Disallow: /support/services/?', body)

    # Regression checks — these Disallows must REMAIN
    def test_still_disallows_admin(self):
        body = self.body
        self.assertIn('Disallow: /admin/', body)

    def test_still_disallows_authed_pages(self):
        body = self.body
        self.assertIn('Disallow: /accounts/dashboard/', body)
        self.assertIn('Disallow: /accounts/court/', body)
        self.assertIn('Disallow: /journal/', body)

    def test_sitemap_is_present(self):
        body = self.body
        self.assertIn('Sitemap: https://www.myrecoverypal.com/sitemap.xml', body)

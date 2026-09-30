# apps/blog/tests_security.py
"""Blog post bodies are user-authored rich HTML (any logged-in member can
publish via /blog/write/), so they must be sanitized before rendering."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import Post

User = get_user_model()

_TEST_SETTINGS = {
    'PREPEND_WWW': False,
    'SECURE_SSL_REDIRECT': False,
    'STORAGES': {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
}


@override_settings(**_TEST_SETTINGS)
class PostContentSanitizedTest(TestCase):
    def _render(self, content):
        author = User.objects.create_user(
            username='author', email='author@example.com', password='pw-12345-xyz')
        post = Post.objects.create(
            title='A post', slug='a-post', author=author, content=content,
            status='published', published_at=timezone.now())
        resp = self.client.get(reverse('blog:post_detail', args=[post.slug]))
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_script_tag_is_not_rendered(self):
        html = self._render('<p>hello</p><script>window.pwnedByPost=1</script>')
        # The text may still appear escaped in meta/JSON-LD descriptions
        # (striptags); what must not survive is the executable tag.
        self.assertNotIn('<script>window.pwnedByPost', html)
        self.assertIn('<p>hello</p>', html)

    def test_event_handler_attributes_are_stripped(self):
        html = self._render('<img src="x" onerror="window.pwnedByAttr=1"><p onclick="window.pwnedByAttr=2">hi</p>')
        self.assertNotIn('pwnedByAttr', html)

    def test_javascript_urls_are_stripped(self):
        html = self._render('<a href="javascript:window.pwnedByHref=1">click</a>')
        self.assertNotIn('pwnedByHref', html)

    def test_formatting_used_by_existing_posts_survives(self):
        html = self._render(
            '<h2 class="graf">Title</h2><blockquote>quote</blockquote>'
            '<ul><li><strong>a</strong> <em>b</em></li></ul>'
            '<a href="https://example.com/x" target="_blank">link</a>'
            '<table><thead><tr><th>h</th></tr></thead><tbody><tr><td>c</td></tr></tbody></table>')
        self.assertIn('<h2 class="graf">Title</h2>', html)
        self.assertIn('<blockquote>quote</blockquote>', html)
        self.assertIn('<li><strong>a</strong> <em>b</em></li>', html)
        self.assertIn('href="https://example.com/x"', html)
        self.assertIn('target="_blank"', html)
        self.assertIn('<td>c</td>', html)

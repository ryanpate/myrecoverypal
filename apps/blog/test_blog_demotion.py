"""Personal-narrative posts must not compete for crawl budget.

The blog produced 0 clicks across 3 months of GSC data (73 published posts,
~240 impressions, zero clicks) while occupying 59% of the sitemap and 33 of
the 88 URLs in "Crawled - currently not indexed".

Six posts target real keywords and stay indexed. The other 67 are personal
recovery narratives with no search demand: noindex + out of the sitemap,
still fully reachable in the app.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import Post
from apps.blog.seo import SEO_INDEXED_SLUGS

User = get_user_model()


def _author():
    return User.objects.get_or_create(
        username='blogauthor', defaults={'email': 'author@example.com'})[0]


def make_post(slug, personal, **extra):
    defaults = dict(
        title=slug.replace('-', ' ').title(), slug=slug, author=_author(),
        content='<p>Body copy.</p>', status='published',
        is_personal_story=personal, published_at=timezone.now(),
    )
    defaults.update(extra)
    return Post.objects.create(**defaults)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PostNoIndexTests(TestCase):
    def test_personal_story_is_noindexed(self):
        p = make_post('the-lie-i-told-best', personal=True)
        html = self.client.get(p.get_absolute_url()).content.decode()
        self.assertIn('name="robots" content="noindex, follow"', html)

    def test_keyword_post_stays_indexable(self):
        p = make_post('dopamine-detox-addiction-recovery', personal=False)
        html = self.client.get(p.get_absolute_url()).content.decode()
        self.assertNotIn('noindex', html)
        self.assertIn('name="robots" content="index, follow', html)

    def test_noindex_uses_follow_so_link_equity_still_flows(self):
        """noindex,nofollow would strand the outbound links; noindex,follow
        keeps Google crawling through to the pages that matter."""
        p = make_post('nobodys-going-to-clap', personal=True)
        html = self.client.get(p.get_absolute_url()).content.decode()
        self.assertNotIn('noindex, nofollow', html)

    def test_post_is_still_reachable_by_readers(self):
        """Demoted, not deleted — these serve retained users in-app."""
        p = make_post('the-prayer-that-rewired-how-i-think', personal=True)
        self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 200)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class BlogSitemapTests(TestCase):
    def test_personal_story_is_not_in_the_sitemap(self):
        make_post('i-dont-have-a-vault-anymore', personal=True)
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertNotIn('i-dont-have-a-vault-anymore', xml)

    def test_keyword_post_is_in_the_sitemap(self):
        make_post('signs-of-alcoholism-self-assessment', personal=False)
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('signs-of-alcoholism-self-assessment', xml)

    def test_blog_index_itself_stays_in_the_sitemap(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('<loc>https://example.com/blog/</loc>', xml)

    def test_draft_posts_still_excluded(self):
        make_post('a-draft', personal=False, status='draft')
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertNotIn('a-draft', xml)


class SeoAllowlistTests(TestCase):
    """The six keyword-targeted posts, per CLAUDE.md's GSC indexing list."""

    def test_allowlist_contents(self):
        self.assertEqual(SEO_INDEXED_SLUGS, {
            'dopamine-detox-addiction-recovery',
            'high-functioning-alcoholic-signs-help',
            'how-long-does-alcohol-withdrawal-last',
            'how-to-stop-drinking-alcohol-guide',
            'signs-of-alcoholism-self-assessment',
            'what-is-sober-curious-guide',
        })

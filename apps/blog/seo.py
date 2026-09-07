"""Which blog posts are worth indexing.

The blog produced 0 clicks across 3 months of GSC data while occupying 59%
of the sitemap and 33 of the 88 URLs in "Crawled - currently not indexed".
Six posts were written against real keywords; the rest are personal
recovery narratives with no search demand.

The narratives are demoted, not deleted: noindex + out of the sitemap, but
fully reachable in the app, where they do serve retained users.

Source of truth for the six is CLAUDE.md's GSC indexing list. A post's
`is_personal_story` flag decides at runtime — this set only seeds it, so
new posts are controlled from the admin rather than from here.
"""
SEO_INDEXED_SLUGS = {
    'dopamine-detox-addiction-recovery',
    'high-functioning-alcoholic-signs-help',
    'how-long-does-alcohol-withdrawal-last',
    'how-to-stop-drinking-alcohol-guide',
    'signs-of-alcoholism-self-assessment',
    'what-is-sober-curious-guide',
}

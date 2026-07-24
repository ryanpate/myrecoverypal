# Sitemap Setup Guide for MyRecoveryPal

## Overview
This guide explains how to generate, verify, and submit your sitemap.xml to Google Search Console to improve your site's SEO and indexing.

## What's Been Set Up

### 1. Dynamic Sitemap (Django)
- **URL**: https://www.myrecoverypal.com/sitemap.xml
- **Configuration**: `recovery_hub/sitemaps.py`
- **Features**: Automatically updates as you add blog posts and pages
- **Includes**:
  - All public pages (home, about, contact, etc.)
  - All published blog posts (automatically)
  - Dynamic priorities based on content age

### 2. Static Sitemap File
- **Location**: `/sitemap.xml` (project root)
- **Purpose**: Backup/fallback sitemap
- **Updates**: Regenerated on each deployment via `build.sh`

### 3. Sitemap Generation Command
- **Command**: `python manage.py generate_sitemap`
- **Purpose**: Creates a fresh sitemap.xml file
- **When to use**: After adding new pages or blog posts

## How to Verify Your Sitemap

### Method 1: Check if Django sitemap is working
```bash
# In production, visit:
https://www.myrecoverypal.com/sitemap.xml

# You should see XML output with all your URLs
```

### Method 2: Manually generate static sitemap
```bash
# From your project directory:
python manage.py generate_sitemap

# This creates sitemap.xml in your project root
# You can then upload it to your server
```

## Submitting to Google Search Console

### Step 1: Access Google Search Console
1. Go to: https://search.google.com/search-console
2. Log in with your Google account
3. Add property: `www.myrecoverypal.com` (if not already added)

### Step 2: Verify Domain Ownership
If not already verified, Google will ask you to verify ownership using one of these methods:
- **Recommended**: HTML file upload
- DNS record (TXT record)
- HTML meta tag
- Google Analytics
- Google Tag Manager

### Step 3: Submit Your Sitemap
1. In Google Search Console, select your property
2. Click "Sitemaps" in the left sidebar
3. Enter your sitemap URL: `sitemap.xml`
4. Click "Submit"

### Step 4: Verify Submission
- Google will show the sitemap status
- Initial status: "Pending" (wait a few hours)
- Success status: "Success" with number of discovered URLs
- Check back in 24-48 hours to see indexing progress

## Testing Your Sitemap

### Online Validators
1. **XML Sitemap Validator**: https://www.xml-sitemaps.com/validate-xml-sitemap.html
   - Enter: `https://www.myrecoverypal.com/sitemap.xml`
   - Click "Validate"

2. **Google's Rich Results Test**: https://search.google.com/test/rich-results
   - Test individual pages from your sitemap

### Manual Check
```bash
# Use curl to fetch your sitemap:
curl https://www.myrecoverypal.com/sitemap.xml

# Should return XML with URLs
```

## Troubleshooting

### Issue: "Sitemap not found" (404 error)

**Solutions:**

1. **Verify Django sitemap URL is configured**:
   - Check `recovery_hub/urls.py` has the sitemap path
   - Restart your Django application

2. **Use the static sitemap**:
   ```bash
   # Generate static sitemap
   python manage.py generate_sitemap

   # Copy to your web server's root directory
   cp sitemap.xml /path/to/webroot/
   ```

3. **Check your web server configuration**:
   - Nginx: Ensure static files are served correctly
   - Apache: Check .htaccess allows sitemap.xml
   - Verify the file is accessible at domain.com/sitemap.xml

### Issue: "Couldn't fetch" in Google Search Console

**Solutions:**

1. **Check robots.txt**:
   - Verify `robots.txt` includes: `Sitemap: https://www.myrecoverypal.com/sitemap.xml`
   - Ensure robots.txt doesn't block the sitemap

2. **Check server headers**:
   ```bash
   curl -I https://www.myrecoverypal.com/sitemap.xml
   ```
   - Should return `200 OK`
   - Content-Type should be `application/xml` or `text/xml`

3. **Wait and retry**:
   - Google may take 24-48 hours to fetch new sitemaps
   - Try resubmitting after a day

### Issue: "Sitemap is HTML" error

This means the sitemap URL is returning an HTML page (like a 404 page) instead of XML.

**Solutions:**
1. Verify the dynamic sitemap works: `python manage.py shell`
   ```python
   from recovery_hub.sitemaps import sitemaps
   print(list(sitemaps.keys()))
   ```

2. Check for URL conflicts in `urls.py`
3. Ensure SITE_ID is set correctly in settings.py

## Automatic Sitemap Updates

### On Each Deployment
The `build.sh` script automatically:
1. Runs migrations
2. Generates a fresh sitemap.xml
3. Copies it to the static files directory

### When Publishing New Blog Posts
The dynamic sitemap automatically includes new published posts:
- No manual action needed
- New posts appear in sitemap immediately
- Google will discover them on next crawl

## Manual Sitemap Regeneration

If you need to manually update the sitemap:

```bash
# SSH into your server
cd /path/to/myrecoverypal

# Activate virtual environment (if using one)
source venv/bin/activate

# Generate new sitemap
python manage.py generate_sitemap

# Verify it was created
ls -lh sitemap.xml
cat sitemap.xml | head -20
```

## Best Practices

### 1. Keep Content Fresh
- Publish blog posts regularly
- Update existing pages monthly
- Google favors sites with fresh content

### 2. Monitor Search Console
- Check weekly for:
  - Sitemap errors
  - Indexing issues
  - Coverage reports
  - Performance metrics

### 3. Update Sitemap Priority
Edit `recovery_hub/sitemaps.py` to adjust priorities:
- 1.0: Most important (homepage)
- 0.8-0.9: High priority (blog, key pages)
- 0.5-0.7: Medium priority (secondary pages)
- 0.3-0.4: Low priority (legal pages)

### 4. Submit to Other Search Engines

**Bing Webmaster Tools**:
- URL: https://www.bing.com/webmasters
- Submit same sitemap: `sitemap.xml`

**Yandex Webmaster**:
- URL: https://webmaster.yandex.com
- Submit same sitemap: `sitemap.xml`

## Expected Results

### Timeline
- **Day 1**: Sitemap submitted
- **Day 2-3**: Google starts crawling
- **Week 1**: First pages indexed
- **Week 2-4**: Most pages indexed
- **Month 1-3**: Full indexing, ranking improvements

### Success Metrics
- **Index Coverage**: 80%+ of pages indexed
- **Crawl Rate**: Steady increase over time
- **Discovery**: New blog posts indexed within 1-7 days
- **Search Appearance**: Pages appear in search results

## Support

If you encounter issues:

1. **Check Django logs**:
   ```bash
   tail -f logs/django.log
   ```

2. **Run the management command with verbose output**:
   ```bash
   python manage.py generate_sitemap --output=sitemap.xml
   ```

3. **Test the dynamic sitemap**:
   ```bash
   curl -v https://www.myrecoverypal.com/sitemap.xml
   ```

4. **Review Google Search Console errors**:
   - Sitemaps section shows detailed errors
   - Coverage report shows indexing issues

## Additional Resources

- [Google Sitemap Guidelines](https://developers.google.com/search/docs/advanced/sitemaps/overview)
- [Django Sitemap Framework](https://docs.djangoproject.com/en/stable/ref/contrib/sitemaps/)
- [Google Search Console Help](https://support.google.com/webmasters/)

---

**Last Updated**: 2025-11-13
**Maintainer**: MyRecoveryPal Development Team

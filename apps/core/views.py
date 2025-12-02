from django.shortcuts import render, redirect
from django.views.generic import TemplateView


class IndexView(TemplateView):
    template_name = 'core/index.html'

    def dispatch(self, request, *args, **kwargs):
        # If user is authenticated, redirect to myrecoverycircle
        if request.user.is_authenticated:
            return redirect('accounts:social_feed')
        # Otherwise, show the home page
        return super().dispatch(request, *args, **kwargs)
class AboutView(TemplateView):
    template_name = 'core/about.html'

class ContactView(TemplateView):
    template_name = 'core/contact.html'

class PrivacyView(TemplateView):
    template_name = 'core/privacy.html'

class TermsView(TemplateView):
    template_name = 'core/terms.html'

class TeamView(TemplateView):
    template_name = 'core/team.html'


class GuidelinesView(TemplateView):
    template_name = 'core/guidelines.html'


class SuccessStoriesView(TemplateView):
    template_name = 'core/success_stories.html'


class CookiesView(TemplateView):
    template_name = 'core/cookies.html'


class CrisisView(TemplateView):
    template_name = 'resources/crisis.html'


class OfflineView(TemplateView):
    template_name = 'core/offline.html'


class InstallGuideView(TemplateView):
    template_name = 'core/install.html'


class GetAppView(TemplateView):
    template_name = 'core/get_app.html'


class DemoView(TemplateView):
    template_name = 'core/demo.html'


# Sitemap View - serves static sitemap.xml
def sitemap_view(request):
    """
    Serve the static sitemap.xml file.
    This is a fallback in case Django's sitemap framework has issues.
    """
    import os
    from django.conf import settings
    from django.http import HttpResponse

    # Try to find sitemap.xml in multiple locations
    sitemap_paths = [
        os.path.join(settings.BASE_DIR, 'sitemap.xml'),
        os.path.join(settings.STATIC_ROOT, 'sitemap.xml') if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT else None,
        os.path.join(settings.BASE_DIR, 'staticfiles', 'sitemap.xml'),
    ]

    sitemap_content = None
    for path in sitemap_paths:
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    sitemap_content = f.read()
                break
            except Exception:
                continue

    if sitemap_content:
        return HttpResponse(sitemap_content, content_type='application/xml')

    # If no static file found, return a minimal sitemap
    minimal_sitemap = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.myrecoverypal.com/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://www.myrecoverypal.com/blog/</loc>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://www.myrecoverypal.com/about/</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://www.myrecoverypal.com/contact/</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
</urlset>'''

    return HttpResponse(minimal_sitemap, content_type='application/xml')


# Robots.txt View - serves static robots.txt
def robots_txt_view(request):
    """
    Serve the robots.txt file.
    """
    import os
    from django.conf import settings
    from django.http import HttpResponse

    # Try to find robots.txt in multiple locations
    robots_paths = [
        os.path.join(settings.BASE_DIR, 'root_files', 'robots.txt'),
        os.path.join(settings.BASE_DIR, 'robots.txt'),
        os.path.join(settings.STATIC_ROOT, 'robots.txt') if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT else None,
    ]

    robots_content = None
    for path in robots_paths:
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    robots_content = f.read()
                break
            except Exception:
                continue

    if robots_content:
        return HttpResponse(robots_content, content_type='text/plain')

    # If no file found, return a minimal robots.txt
    minimal_robots = '''User-agent: *
Allow: /
Disallow: /admin/
Disallow: /accounts/dashboard/
Disallow: /journal/

Sitemap: https://www.myrecoverypal.com/sitemap.xml
'''

    return HttpResponse(minimal_robots, content_type='text/plain')


# Custom Error Handlers
def custom_404(request, exception):
    """Custom 404 error page"""
    return render(request, '404.html', status=404)


def custom_500(request):
    """Custom 500 error page"""
    return render(request, '500.html', status=500)


def custom_403(request, exception):
    """Custom 403 error page"""
    return render(request, '403.html', status=403)


def custom_400(request, exception):
    """Custom 400 error page"""
    return render(request, '400.html', status=400)

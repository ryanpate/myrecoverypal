from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.views.decorators.http import require_http_methods


class IndexView(TemplateView):
    template_name = 'core/index.html'

    def dispatch(self, request, *args, **kwargs):
        # If user is authenticated, redirect to progress page
        if request.user.is_authenticated:
            return redirect('accounts:progress')
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


class SoberGridAlternativeView(TemplateView):
    template_name = 'core/sober_grid_alternative.html'


class AlcoholRecoveryAppView(TemplateView):
    template_name = 'core/alcohol_recovery_app.html'


class DrugAddictionRecoveryAppView(TemplateView):
    template_name = 'core/drug_addiction_recovery_app.html'


class SobrietyCounterAppView(TemplateView):
    """Redirects to sobriety calculator - consolidated for better SEO"""
    def get(self, request, *args, **kwargs):
        return redirect('core:sobriety_calculator', permanent=True)


class FreeAAAppView(TemplateView):
    """Redirects to alcohol recovery app - consolidated for better SEO"""
    def get(self, request, *args, **kwargs):
        return redirect('core:alcohol_recovery_app', permanent=True)


class OpioidRecoveryAppView(TemplateView):
    """Redirects to drug addiction recovery app - consolidated for better SEO"""
    def get(self, request, *args, **kwargs):
        return redirect('core:drug_addiction_recovery_app', permanent=True)


class GamblingAddictionAppView(TemplateView):
    """Redirects to main index - consolidated for better SEO (niche addiction type)"""
    def get(self, request, *args, **kwargs):
        return redirect('core:index', permanent=True)


class MentalHealthRecoveryAppView(TemplateView):
    """Redirects to main index - consolidated for better SEO"""
    def get(self, request, *args, **kwargs):
        return redirect('core:index', permanent=True)


class SobrietyCalculatorView(TemplateView):
    template_name = 'core/sobriety_calculator.html'


class CleanTimeCalculatorView(TemplateView):
    """SEO landing page targeting NA / drug-recovery "clean time calculator"
    queries. The head term "sobriety calculator" is locked up by high-authority
    AA/treatment sites; "clean time calculator" is owned only by low-authority
    regional NA chapter pages, so this is a realistic top-3 opportunity.

    Shares the calculator widget with the sobriety calculator but is framed in
    NA language (clean date, key tags, drug recovery) with a substance-neutral
    recovery timeline — distinct enough to avoid duplicate-content overlap."""
    template_name = 'core/clean_time_calculator.html'


class SobrietyMedallionMakerView(TemplateView):
    """SEO landing page for the milestone badge creator.

    Targets: "sobriety medallion", "AA chip generator", "recovery badge maker".
    Dedicated SEO content lives here; the interactive creator is at
    /accounts/milestone-badge/.
    """
    template_name = 'core/sobriety_medallion_maker.html'

    def get_context_data(self, **kwargs):
        from apps.accounts.milestone_image import BADGE_STYLES
        context = super().get_context_data(**kwargs)
        context['badge_styles'] = BADGE_STYLES
        return context


class AIRecoveryCoachView(TemplateView):
    template_name = 'core/ai_recovery_coach.html'


class CourtOrderedMeetingTrackerView(TemplateView):
    template_name = 'core/court_ordered_meeting_tracker.html'

    def get_context_data(self, **kwargs):
        from apps.accounts.payment_models import SubscriptionPlan
        context = super().get_context_data(**kwargs)
        context['court_monthly_plan'] = SubscriptionPlan.objects.filter(
            tier='court', billing_period='monthly', is_active=True).first()
        context['court_yearly_plan'] = SubscriptionPlan.objects.filter(
            tier='court', billing_period='yearly', is_active=True).first()
        return context


class ForProbationOfficersView(TemplateView):
    """Print-friendly verification guide for POs / drug-court coordinators.
    Doubles as the outreach one-pager linked in emails to referral sources."""
    template_name = 'core/for_probation_officers.html'


class SupportLovedOneView(TemplateView):
    """SEO landing page for the Supporter feature — family/friends following a
    loved one's recovery with consent. Funnels to the Supporter tier."""
    template_name = 'core/support_a_loved_one.html'


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


# Ads.txt View - serves static ads.txt for Google AdSense
def ads_txt_view(request):
    """
    Serve the ads.txt file for Google AdSense verification.
    """
    from django.http import HttpResponse

    # Hardcoded ads.txt content for reliability
    # This ensures Google AdSense can always verify the file
    ads_content = "google.com, pub-5523870768931777, DIRECT, f08c47fec0942fa0"

    return HttpResponse(ads_content, content_type='text/plain')


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
    """Custom 404 error page — logs the missing URL for debugging"""
    import logging
    logger = logging.getLogger('django.request')
    logger.warning('404 Not Found: %s (Referer: %s, UA: %s)',
                   request.get_full_path(),
                   request.META.get('HTTP_REFERER', 'none'),
                   request.META.get('HTTP_USER_AGENT', 'none')[:100])
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


class JournalBonusView(View):
    """
    Public landing page for the journal QR funnel.
    GET: render the page.
    POST: capture email, store promo + email in session, redirect to
          register or login depending on whether email is registered.
    """
    template_name = 'core/journal_bonus.html'
    default_promo_code = 'PAL90'

    def get(self, request):
        code = request.GET.get('code') or self.default_promo_code
        return render(request, self.template_name, {
            'promo_code': code,
        })

    def post(self, request):
        from django.contrib.auth import get_user_model
        from urllib.parse import urlencode
        User = get_user_model()

        code = (request.POST.get('code') or self.default_promo_code).strip()
        email = (request.POST.get('email') or '').strip().lower()

        # Validate email
        validator = EmailValidator()
        try:
            validator(email)
        except ValidationError:
            return render(request, self.template_name, {
                'promo_code': code,
                'submitted_email': email,
                'form_error': 'Please enter a valid email address.',
            })

        # Stash promo in session for the downstream auth flow
        request.session['journal_promo'] = code

        # Branch on whether the email is already registered
        existing = User.objects.filter(email__iexact=email).first()
        if existing is None:
            register_url = reverse('accounts:register')
            qs = urlencode({'email': email})
            return redirect(f'{register_url}?{qs}')

        # Existing user — send them through login then to claim
        claim_url = reverse('core:journal_bonus_claim')
        login_url = reverse('accounts:login')
        next_qs = urlencode({'code': code})
        next_url = f'{claim_url}?{next_qs}'
        login_qs = urlencode({'next': next_url})
        return redirect(f'{login_url}?{login_qs}')


class FaithJournalView(JournalBonusView):
    """
    Christian Recovery Journal QR funnel. Same flow as JournalBonusView,
    different default promo code and template.
    """
    template_name = 'core/faith_journal.html'
    default_promo_code = 'CHRISTIAN60'


class LovedOneView(JournalBonusView):
    """
    Loved One's Recovery Journal QR funnel. Same flow as JournalBonusView,
    different default promo code and template. Audience: family/friends
    supporting someone in recovery.
    """
    template_name = 'core/loved_one.html'
    default_promo_code = 'LOVEDONE60'


@login_required
def journal_bonus_claim(request):
    """
    Login-required handler that consumes the session promo (or ?code=
    fallback) and applies it to the now-authenticated user. Used when
    an existing user comes back through the journal funnel.
    """
    from apps.accounts.promo_service import apply_promo_to_user

    code = request.session.pop('journal_promo', None) or request.GET.get('code')
    if code:
        applied, msg = apply_promo_to_user(request.user, code)
        if applied:
            messages.success(
                request,
                "Welcome back! 60 days of Premium has been added to your account."
            )
        elif msg == 'already premium':
            messages.info(
                request,
                "You already have Premium — thanks for picking up the journal!"
            )
        elif msg == 'already redeemed':
            messages.info(request, "You've already used this code.")
        # 'invalid code' → silent, no toast

    return redirect('accounts:social_feed')

from django.shortcuts import render, redirect
from django.views.generic import TemplateView

class IndexView(TemplateView):
    template_name = 'core/index.html'

    def dispatch(self, request, *args, **kwargs):
        # If user is authenticated, redirect to dashboard
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
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

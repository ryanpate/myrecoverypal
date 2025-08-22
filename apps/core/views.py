from django.shortcuts import render
from django.views.generic import TemplateView

class IndexView(TemplateView):
    template_name = 'core/index.html'

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

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView, ListView
from django.urls import reverse_lazy
from .models import User, UserProfile
from .forms import UserProfileForm, SobrietyDateForm
from apps.journal.models import Milestone

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['days_sober'] = user.get_days_sober()
        context['recent_entries'] = user.journal_entries.all()[:5]
        context['milestones'] = user.milestones.all()[:3]
        return context

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self):
        return self.request.user.profile

class SobrietyUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = SobrietyDateForm
    template_name = 'accounts/sobriety_update.html'
    success_url = reverse_lazy('accounts:dashboard')
    
    def get_object(self):
        return self.request.user

class MilestoneListView(LoginRequiredMixin, ListView):
    model = Milestone
    template_name = 'accounts/milestones.html'
    context_object_name = 'milestones'
    
    def get_queryset(self):
        return self.request.user.milestones.all()
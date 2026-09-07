# Update apps/support_services/urls.py
# Add this to your urlpatterns list

from django.urls import path, re_path
from . import views

app_name = 'support_services'

urlpatterns = [
    # Main pages
    path('', views.support_services_home, name='home'),

    # Meetings
    path('meetings/', views.meeting_list, name='meeting_list'),
    path('meetings/finder/', views.meeting_finder,
         name='meeting_finder'),  # Add this line
    path('meetings/submit/', views.submit_meeting, name='submit_meeting'),
    # Hub pages. These MUST precede meetings/<slug:slug>/ — a bare slug
    # converter would otherwise match "tx" and route /meetings/tx/ to the
    # detail view. The state pattern is pinned to exactly two letters.
    re_path(r'^meetings/(?P<state>[A-Za-z]{2})/$',
            views.state_hub, name='state_hub'),
    re_path(r'^meetings/(?P<state>[A-Za-z]{2})/(?P<city_slug>[a-z0-9-]+)/$',
            views.city_hub, name='city_hub'),

    path('meetings/<slug:slug>/', views.meeting_detail, name='meeting_detail'),

    # Services
    path('services/', views.service_list, name='service_list'),
    path('services/submit/', views.submit_service, name='submit_service'),
    path('services/<slug:service_id>/',
         views.service_detail, name='service_detail'),

    # Crisis resources
    path('crisis/', views.crisis_resources, name='crisis_resources'),

    # User features
    path('bookmarks/', views.my_bookmarks, name='my_bookmarks'),
    path('bookmark/<str:item_type>/<int:item_id>/',
         views.bookmark_toggle, name='bookmark_toggle'),

    # API endpoints
    path('api/meetings.json', views.meeting_guide_json, name='meeting_guide_json'),
    path('api/services.json', views.support_services_json, name='services_json'),
    path('api/nearby/', views.nearby_meetings, name='nearby_meetings'),
]

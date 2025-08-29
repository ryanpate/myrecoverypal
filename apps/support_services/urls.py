from django.urls import path
from . import views

app_name = 'support_services'

urlpatterns = [
    # Main pages
    path('', views.support_services_home, name='home'),

    # Meetings
    path('meetings/', views.meeting_list, name='meeting_list'),
    path('meetings/submit/', views.submit_meeting, name='submit_meeting'),
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

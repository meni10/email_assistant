from django.urls import path
from . import views
from django.contrib.auth import views as auth_views  
from django.views.generic import RedirectView
urlpatterns = [
    # In urls.py


# Add this path
path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico')),
    path('', views.home_view, name='home'),
    path('oauth/start/', views.oauth_start, name='oauth_start'),
    path("api/auth/status/", views.auth_status, name="auth_status"),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    path('unread-emails/', views.unread_emails_view, name='unread_emails'),
    path('generate/', views.generate_reply_view, name='generate_reply'),
    path('mark-as-read/<str:message_id>/', views.mark_as_read_view, name='mark_as_read'),
    # In urls.py, add this path
    path('email/<str:message_id>/', views.email_detail_view, name='email_detail'),
    path('save-draft/', views.save_draft_view, name='save_draft'),
     path('debug/<path:path>', views.debug_urls, name='debug_urls'),
    #   path('oauth/status/', views.oauth_status, name='oauth_status'),
     path("login/", auth_views.LoginView.as_view(template_name="my_custom_login.html"), name="login"),
    path('logout/', views.logout_view, name='logout'),
]
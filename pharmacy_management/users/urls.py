from django.urls import path
from . import views

urlpatterns = [

    # USER AUTH
    path('signup/', views.user_signup, name='user_signup'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.logout_view, name='logout'),

    # PASSWORD RESET
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset-confirm/', views.password_reset_confirm, name='password_reset_confirm'),

    # ADMIN
    path('admin-login/', views.admin_login, name='admin_login'),
]

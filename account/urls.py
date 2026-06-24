from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login', views.loginView, name='login'),
    path('logout', views.logoutView, name='logout'),
    path('register', views.registerView, name='register'),
    
    # 1. Trang nhập email để xin link reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='account/password_reset_form.html',
             email_template_name='account/password_reset_email.html'
         ), 
         name='password_reset'),

    # 2. Trang thông báo "Chúng tôi đã gửi mail, hãy check inbox"
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='account/password_reset_done.html'
         ), 
         name='password_reset_done'),

    # 3. Trang user bấm vào từ link trong email (chứa token bảo mật)
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='account/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),

    # 4. Trang thông báo "Đổi mật khẩu thành công! Bấm vào đây để đăng nhập"
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='account/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]

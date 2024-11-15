from django.urls import path
from .views import *

urlpatterns = [
    path('login/', login_view, name='login'),
    path('tasks/', get_all_tasks, name='get_all_tasks'),
    path('create_task/', create_task, name='create_task'),
    path('tasks/<int:task_id>/', update_task, name='update_task'),  
    path('tasks/delete/<int:task_id>/', delete_task, name='delete_task'),
    path('tasks/calendar/', get_tasks_calendar, name='get_tasks_calendar'),
    path('register/', register_view, name='register'),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('login-otp/', OTPLoginView.as_view(), name='login-otp'),
]

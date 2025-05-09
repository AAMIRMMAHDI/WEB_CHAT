from django.urls import path
from . import views

urlpatterns = [
    path('messages/', views.MessageList.as_view(), name='message-list'),
    path('users/', views.UserList.as_view(), name='user-list'),
    path('upload/', views.FileUpload.as_view(), name='file-upload'),
]
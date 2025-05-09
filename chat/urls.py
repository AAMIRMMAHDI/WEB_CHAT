from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/messages/', views.MessageList.as_view(), name='message-list'),
    path('api/users/', views.UserList.as_view(), name='user-list'),
    path('api/upload/', views.FileUpload.as_view(), name='file-upload'),
]
from django.urls import path
from chat import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/users/', views.UserList.as_view(), name='user-list'),
    path('api/messages/', views.MessageList.as_view(), name='message-list'),
    path('api/upload/', views.FileUploadView.as_view(), name='file-upload'),
    path('api/groups/', views.GroupList.as_view(), name='group-list'),
    path('api/stats/', views.StatsView.as_view(), name='stats'),
]
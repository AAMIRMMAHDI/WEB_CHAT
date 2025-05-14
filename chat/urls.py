from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/users/', views.UserList.as_view(), name='user_list'),
    path('api/users/current/', views.CurrentUserView.as_view(), name='current_user'),
    path('api/users/logout/', views.LogoutView.as_view(), name='logout'),
    path('api/users/chatted/', views.ChattedUsersView.as_view(), name='chatted_users'),
    path('api/messages/', views.MessageList.as_view(), name='message_list'),
    path('api/groups/', views.GroupList.as_view(), name='group_list'),
    path('api/groups/join/', views.GroupJoinView.as_view(), name='group_join'),
    path('api/groups/search/', views.GroupSearchView.as_view(), name='group_search'),
    path('api/upload/', views.FileUploadView.as_view(), name='file_upload'),
]
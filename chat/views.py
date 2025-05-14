from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from .models import User, Message, File, Group
from .serializers import UserSerializer, MessageSerializer, FileSerializer, GroupSerializer
from django.db import models

def index(request):
    return render(request, 'index.html')

class UserList(APIView):
    def get(self, request):
        search_query = request.GET.get('search', '')
        users = User.objects.all()
        if search_query:
            users = users.filter(models.Q(username__icontains=search_query) | models.Q(display_name__icontains=search_query))
        serializer = UserSerializer(users, many=True)
        return Response({'users': serializer.data})

    def post(self, request):
        username = request.data.get('username')
        display_name = request.data.get('display_name')
        password = request.data.get('password')
        if not username or not password:
            return Response({'status': 'error', 'message': 'نام کاربری و رمز عبور الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'display_name': display_name, 'password': password, 'is_online': True}
        )
        if not created and not check_password(password, user.password):
            return Response({'status': 'error', 'message': 'رمز عبور اشتباه است'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_online = True
        user.save()
        request.session['user_id'] = user.id
        return Response({'status': 'success', 'user_id': user.id, 'display_name': user.display_name or user.username})

class CurrentUserView(APIView):
    def get(self, request):
        user_id = request.session.get('user_id')
        if not user_id:
            return Response({'status': 'error', 'message': 'کاربر وارد نشده است'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.get(id=user_id)
        serializer = UserSerializer(user)
        return Response(serializer.data)

    def patch(self, request):
        user_id = request.session.get('user_id')
        if not user_id:
            return Response({'status': 'error', 'message': 'کاربر وارد نشده است'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.get(id=user_id)
        data = request.data.copy()
        if 'profile_image' in request.FILES:
            data['profile_image'] = request.FILES['profile_image']
        if 'password' in data and data['password']:
            data['password'] = make_password(data['password'])
        serializer = UserSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response({'status': 'error', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    def post(self, request):
        user_id = request.session.get('user_id')
        if user_id:
            user = User.objects.get(id=user_id)
            user.is_online = False
            user.save()
        request.session.flush()
        return Response({'status': 'success'})

class ChattedUsersView(APIView):
    def get(self, request):
        user_id = request.session.get('user_id')
        if not user_id:
            return Response({'status': 'error', 'message': 'کاربر وارد نشده است'}, status=status.HTTP_400_BAD_REQUEST)
        messages = Message.objects.filter(
            models.Q(sender_id=user_id) | models.Q(recipient_id=user_id)
        ).exclude(group__isnull=False)
        user_ids = set()
        for msg in messages:
            if msg.sender_id != user_id:
                user_ids.add(msg.sender_id)
            if msg.recipient_id != user_id:
                user_ids.add(msg.recipient_id)
        users = User.objects.filter(id__in=user_ids)
        serializer = UserSerializer(users, many=True)
        return Response({'users': serializer.data})

class FileUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        files = request.FILES.getlist('files')
        if not files:
            return Response({'status': 'error', 'message': 'هیچ فایلی انتخاب نشده است'}, status=status.HTTP_400_BAD_REQUEST)
        file_urls = []
        for file in files:
            file_type = 'image' if file.content_type.startswith('image') else 'other'
            file_obj = File.objects.create(file=file, file_type=file_type)
            file_urls.append({'id': file_obj.id, 'file': file_obj.file.url, 'file_type': file_obj.file_type})
        return Response({'status': 'success', 'file_urls': file_urls})

class MessageList(APIView):
    def get(self, request):
        group_id = request.GET.get('group_id')
        recipient_id = request.GET.get('recipient_id')
        last_message_id = request.GET.get('last_message_id', 0)
        messages = Message.objects.filter(id__gt=last_message_id)
        if group_id:
            messages = messages.filter(group_id=group_id)
        elif recipient_id:
            user_id = request.session.get('user_id')
            messages = messages.filter(
                models.Q(sender_id=user_id, recipient_id=recipient_id) |
                models.Q(sender_id=recipient_id, recipient_id=user_id)
            )
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        data['sender_id'] = request.session.get('user_id')
        file_urls = data.pop('file_urls', [])
        serializer = MessageSerializer(data=data)
        if serializer.is_valid():
            message = serializer.save()
            for file_data in file_urls:
                file_obj = File.objects.get(id=file_data['id'])
                message.files.add(file_obj)
            return Response({'status': 'success', 'message_id': message.id})
        return Response({'status': 'error', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class GroupList(APIView):
    def get(self, request):
        user_id = request.session.get('user_id')
        if not user_id:
            return Response({'status': 'error', 'message': 'کاربر وارد نشده است'}, status=status.HTTP_400_BAD_REQUEST)
        groups = Group.objects.filter(members__id=user_id)
        serializer = GroupSerializer(groups, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        data['creator_id'] = request.session.get('user_id')
        if 'image' in request.FILES:
            data['image'] = request.FILES['image']
        serializer = GroupSerializer(data=data)
        if serializer.is_valid():
            group = serializer.save()
            user = User.objects.get(id=data['creator_id'])
            group.members.add(user)
            return Response({'status': 'success', 'group_id': group.id})
        return Response({'status': 'error', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class GroupJoinView(APIView):
    def post(self, request):
        group_id = request.data.get('group_id')
        password = request.data.get('password', '')
        user_id = request.session.get('user_id')
        if not user_id:
            return Response({'status': 'error', 'message': 'کاربر وارد نشده است'}, status=status.HTTP_400_BAD_REQUEST)
        group = get_object_or_404(Group, id=group_id)
        if group.password and not check_password(password, group.password):
            return Response({'status': 'error', 'message': 'رمز عبور گروه اشتباه است'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.get(id=user_id)
        if user in group.members.all():
            return Response({'status': 'error', 'message': 'شما قبلاً عضو این گروه هستید'}, status=status.HTTP_400_BAD_REQUEST)
        group.members.add(user)
        return Response({'status': 'success', 'group_id': group.id})

class GroupSearchView(APIView):
    def get(self, request):
        search_query = request.GET.get('search', '')
        groups = Group.objects.all()
        if search_query:
            groups = groups.filter(models.Q(name__icontains=search_query) | models.Q(id__exact=search_query))
        serializer = GroupSerializer(groups, many=True)
        return Response({'groups': serializer.data})
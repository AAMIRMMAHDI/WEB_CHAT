from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from .models import User, Group, Message, File
from .serializers import UserSerializer, GroupSerializer, MessageSerializer, FileSerializer
import json
import os
from django.conf import settings
from django.core.files.storage import default_storage
import django.db.models as models


def index(request):
    """Render the main index page."""
    return render(request, 'index.html')


class UserView(APIView):
    def post(self, request):
        """Handle user login or registration."""
        data = request.data
        username = data.get('username')
        display_name = data.get('display_name')
        password = data.get('password')

        if not username or not password:
            return Response(
                {'status': 'error', 'message': 'نام کاربری و رمز عبور الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(username=username).first()
        if user:
            if user.check_password(password):
                request.session['user_id'] = user.id
                user.is_online = True
                user.save()
                return Response({
                    'status': 'success',
                    'user_id': user.id,
                    'username': user.username,
                    'display_name': user.display_name
                })
            else:
                return Response(
                    {'status': 'error', 'message': 'رمز عبور اشتباه است'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        user = User(username=username, display_name=display_name or username)
        user.set_password(password)
        user.is_online = True
        user.save()
        request.session['user_id'] = user.id
        return Response({
            'status': 'success',
            'user_id': user.id,
            'username': user.username,
            'display_name': user.display_name
        })

    def get(self, request):
        """Retrieve users, optionally filtered by search query."""
        query = request.GET.get('search', '')
        users = User.objects.filter(username__icontains=query) if query else User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response({'users': serializer.data})


class UserCurrentView(APIView):
    def get(self, request):
        """Retrieve the current logged-in user's details."""
        user_id = request.session.get('user_id')
        if not user_id:
            return Response(
                {'status': 'error', 'message': 'کاربر وارد نشده است'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        user = get_object_or_404(User, id=user_id)
        serializer = UserSerializer(user)
        return Response(serializer.data)

    def patch(self, request):
        """Update the current user's profile, including username, display name, password, or profile image."""
        user_id = request.session.get('user_id')
        if not user_id:
            return Response(
                {'status': 'error', 'message': 'کاربر وارد نشده است'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        user = get_object_or_404(User, id=user_id)

        if 'profile_image' in request.FILES:
            user.profile_image = request.FILES['profile_image']
            user.save()
            return Response({
                'status': 'success',
                'profile_image': user.profile_image.url if user.profile_image else None
            })

        data = request.data
        username = data.get('username')
        display_name = data.get('display_name')
        password = data.get('password')

        if username:
            user.username = username
        if display_name:
            user.display_name = display_name
        if password:
            user.set_password(password)
        user.save()
        return Response({
            'status': 'success',
            'username': user.username,
            'display_name': user.display_name
        })


class UserChattedView(APIView):
    def get(self, request):
        """Retrieve users the current user has chatted with."""
        user_id = request.session.get('user_id')
        if not user_id:
            return Response(
                {'status': 'error', 'message': 'کاربر وارد نشده است'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        sent_messages = Message.objects.filter(sender_id=user_id).values('recipient_id').distinct()
        received_messages = Message.objects.filter(recipient_id=user_id).values('sender_id').distinct()

        user_ids = set()
        for msg in sent_messages:
            if msg['recipient_id']:
                user_ids.add(msg['recipient_id'])
        for msg in received_messages:
            if msg['sender_id']:
                user_ids.add(msg['sender_id'])

        users = User.objects.filter(id__in=user_ids)
        serializer = UserSerializer(users, many=True)
        return Response({'users': serializer.data})


class GroupView(APIView):
    def get(self, request):
        """Retrieve groups the current user is a member of."""
        user_id = request.session.get('user_id')
        if not user_id:
            return Response(
                {'status': 'error', 'message': 'کاربر وارد نشده است'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        groups = Group.objects.filter(members__id=user_id)
        serializer = GroupSerializer(groups, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new group."""
        user_id = request.session.get('user_id')
        if not user_id:
            return Response(
                {'status': 'error', 'message': 'کاربر وارد نشده است'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        data = request.data
        name = data.get('name')
        description = data.get('description', '')
        password = data.get('password', '')
        image = request.FILES.get('image')  # Handle file upload correctly

        if not name:
            return Response(
                {'status': 'error', 'message': 'نام گروه الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        group = Group(name=name, description=description, password=password, creator_id=user_id)
        if image:
            group.image = image
        group.save()
        group.members.add(user_id)
        return Response({'status': 'success', 'group_id': group.id})


class GroupSearchView(APIView):
    def get(self, request):
        """Search for groups by name."""
        query = request.GET.get('search', '')
        groups = Group.objects.filter(name__icontains=query)
        serializer = GroupSerializer(groups, many=True)
        return Response({'groups': serializer.data})


class GroupJoinSerializer(serializers.Serializer):
    """Serializer for validating group join requests."""
    group_id = serializers.IntegerField()
    password = serializers.CharField(required=False, allow_blank=True)


class GroupJoinView(APIView):
    def post(self, request):
        """Handle joining a group with validation."""
        user_id = request.session.get('user_id')
        if not user_id:
            return Response(
                {'status': 'error', 'message': 'کاربر وارد نشده است'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = GroupJoinSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'status': 'error', 'message': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        group_id = serializer.validated_data['group_id']
        password = serializer.validated_data.get('password', '')

        group = get_object_or_404(Group, id=group_id)
        if group.password and not group.check_password(password):
            return Response(
                {'status': 'error', 'message': 'رمز عبور اشتباه است'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if group.members.filter(id=user_id).exists():
            return Response(
                {'status': 'error', 'message': 'شما قبلاً عضو این گروه هستید'},
                status=status.HTTP_400_BAD_REQUEST
            )

        group.members.add(user_id)
        return Response({'status': 'success', 'group_id': group.id})


class MessageView(APIView):
    def get(self, request):
        """Retrieve messages for the current user, optionally filtered by group or recipient."""
        user_id = request.session.get('user_id')
        if not user_id:
            return Response(
                {'status': 'error', 'message': 'کاربر وارد نشده است'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        last_message_id = request.GET.get('last_message_id', '0')
        group_id = request.GET.get('group_id')
        recipient_id = request.GET.get('recipient_id')

        try:
            last_message_id = int(last_message_id)
        except ValueError:
            return Response(
                {'status': 'error', 'message': 'شناسه پیام نامعتبر است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        messages = Message.objects.filter(id__gt=last_message_id)

        if group_id:
            try:
                group_id = int(group_id)
                if not Group.objects.filter(id=group_id, members__id=user_id).exists():
                    return Response(
                        {'status': 'error', 'message': 'شما عضو این گروه نیستید'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                messages = messages.filter(group_id=group_id)
            except ValueError:
                return Response(
                    {'status': 'error', 'message': 'شناسه گروه نامعتبر است'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif recipient_id:
            try:
                recipient_id = int(recipient_id)
                messages = messages.filter(
                    (models.Q(sender_id=user_id) & models.Q(recipient_id=recipient_id)) |
                    (models.Q(sender_id=recipient_id) & models.Q(recipient_id=user_id))
                )
            except ValueError:
                return Response(
                    {'status': 'error', 'message': 'شناسه گیرنده نامعتبر است'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            messages = messages.filter(
                models.Q(sender_id=user_id) |
                models.Q(recipient_id=user_id) |
                models.Q(group__members__id=user_id)
            )

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Send a new message with optional files."""
        user_id = request.session.get('user_id')
        if not user_id:
            return Response(
                {'status': 'error', 'message': 'کاربر وارد نشده است'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        data = request.data
        content = data.get('content', '').strip()
        group_id = data.get('group_id')
        recipient_id = data.get('recipient_id')
        file_urls = data.get('file_urls', [])

        if not content and not file_urls:
            return Response(
                {'status': 'error', 'message': 'محتوا یا فایل الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        message = Message(sender_id=user_id, content=content)
        if group_id:
            try:
                group_id = int(group_id)
                if not Group.objects.filter(id=group_id, members__id=user_id).exists():
                    return Response(
                        {'status': 'error', 'message': 'شما عضو این گروه نیستید'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                message.group_id = group_id
            except ValueError:
                return Response(
                    {'status': 'error', 'message': 'شناسه گروه نامعتبر است'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        if recipient_id:
            try:
                recipient_id = int(recipient_id)
                if not User.objects.filter(id=recipient_id).exists():
                    return Response(
                        {'status': 'error', 'message': 'گیرنده وجود ندارد'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                message.recipient_id = recipient_id
            except ValueError:
                return Response(
                    {'status': 'error', 'message': 'شناسه گیرنده نامعتبر است'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        message.save()

        for file_url in file_urls:
            File.objects.create(file=file_url['file'], file_type=file_url['file_type'], message=message)

        serializer = MessageSerializer(message)
        return Response({'status': 'success', 'message_id': message.id, 'message': serializer.data})


class MessageDetailView(APIView):
    def patch(self, request, pk):
        """Edit a message if the user is the sender."""
        user_id = request.session.get('user_id')
        if not user_id:
            return Response(
                {'status': 'error', 'message': 'کاربر وارد نشده است'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        message = get_object_or_404(Message, pk=pk)
        if message.sender_id != user_id:
            return Response(
                {'status': 'error', 'message': 'فقط صاحب پیام می‌تواند آن را ویرایش کند'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data
        content = data.get('content', '').strip()
        if not content:
            return Response(
                {'status': 'error', 'message': 'پیام نمی‌تواند خالی باشد'},
                status=status.HTTP_400_BAD_REQUEST
            )

        message.content = content
        message.save()
        serializer = MessageSerializer(message)
        return Response({'status': 'success', 'message': serializer.data})

    def delete(self, request, pk):
        """Delete a message if the user is the sender."""
        user_id = request.session.get('user_id')
        if not user_id:
            return Response(
                {'status': 'error', 'message': 'کاربر وارد نشده است'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        message = get_object_or_404(Message, pk=pk)
        if message.sender_id != user_id:
            return Response(
                {'status': 'error', 'message': 'فقط صاحب پیام می‌تواند آن را حذف کند'},
                status=status.HTTP_403_FORBIDDEN
            )

        message.delete()
        return Response({'status': 'success'})


class UploadView(APIView):
    def post(self, request):
        """Handle file uploads."""
        user_id = request.session.get('user_id')
        if not user_id:
            return Response(
                {'status': 'error', 'message': 'کاربر وارد نشده است'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        files = request.FILES.getlist('files')
        if not files:
            return Response(
                {'status': 'error', 'message': 'هیچ فایلی انتخاب نشده است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file_urls = []
        for file in files:
            file_path = os.path.join('uploads', file.name)
            default_storage.save(file_path, file)
            file_url = default_storage.url(file_path)

            file_type = 'other'
            if file.content_type.startswith('image'):
                file_type = 'image'
            elif file.content_type.startswith('video'):
                file_type = 'video'
            elif file.content_type.startswith('audio'):
                file_type = 'audio'

            file_obj = File.objects.create(file=file_url, file_type=file_type)
            file_urls.append({'file': file_url, 'file_type': file_type})

        return Response({'status': 'success', 'file_urls': file_urls})


class LogoutView(APIView):
    def post(self, request):
        """Log out the current user."""
        user_id = request.session.get('user_id')
        if user_id:
            user = get_object_or_404(User, id=user_id)
            user.is_online = False
            user.save()
            del request.session['user_id']
        return Response({'status': 'success'})
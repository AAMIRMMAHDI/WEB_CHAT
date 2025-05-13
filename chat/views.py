from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from .models import User, Message, File, Group, UserActivity
import os
import logging
from PIL import Image
import io
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'index.html')

class UserList(APIView):
    def get(self, request):
        try:
            users = User.objects.all()
            user_data = [
                {
                    'id': user.id,
                    'username': user.username,
                    'is_online': user.activities.filter(action='online').exists()
                } for user in users
            ]
            return Response({'users': user_data})
        except Exception as e:
            logger.error(f"Error fetching users: {str(e)}")
            return Response({'status': 'error', 'message': 'خطا در دریافت کاربران'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            username = request.data.get('username')
            password = request.data.get('password')
            action = request.data.get('action')

            if action == 'online':
                user_id = request.session.get('user_id')
                if not user_id:
                    logger.error("No user_id in session for online action")
                    return Response({'status': 'error', 'message': 'کاربر وارد نشده است'}, status=status.HTTP_400_BAD_REQUEST)
                UserActivity.objects.create(
                    user_id=user_id,
                    action='online',
                    details={'duration': request.data.get('duration', 0)}
                )
                return Response({'status': 'success'})

            if not username or not password:
                logger.error("Username or password missing")
                return Response({'status': 'error', 'message': 'نام کاربری و رمز عبور الزامی است'}, status=status.HTTP_400_BAD_REQUEST)

            user, created = User.objects.get_or_create(
                username=username,
                defaults={'password': make_password(password)}
            )

            if not created and not check_password(password, user.password):
                logger.error(f"Invalid password for user {username}")
                return Response({'status': 'error', 'message': 'رمز عبور اشتباه است'}, status=status.HTTP_400_BAD_REQUEST)

            request.session['user_id'] = user.id
            UserActivity.objects.create(user=user, action='login')
            logger.info(f"User {username} logged in successfully")
            return Response({'status': 'success', 'user_id': user.id})
        except Exception as e:
            logger.error(f"Error in user login: {str(e)}")
            return Response({'status': 'error', 'message': 'خطا در ورود'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FileUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        try:
            files = request.FILES.getlist('files')
            if not files:
                logger.error("No files provided in upload request")
                return Response({'status': 'error', 'message': 'هیچ فایلی انتخاب نشده است'}, status=status.HTTP_400_BAD_REQUEST)

            file_urls = []
            for file in files:
                if file.content_type.startswith('image'):
                    img = Image.open(file)
                    img = img.convert('RGB')
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=85)
                    output.seek(0)
                    file_name = f"compressed_{file.name}"
                    compressed_file = ContentFile(output.read(), name=file_name)
                    file_obj = File.objects.create(file=compressed_file, file_type='image')
                else:
                    file_type = 'video' if file.content_type.startswith('video') else 'audio' if file.content_type.startswith('audio') else 'other'
                    file_obj = File.objects.create(file=file, file_type=file_type)
                file_urls.append({'id': file_obj.id, 'file': file_obj.file.url, 'file_type': file_obj.file_type})
            
            logger.info(f"Files uploaded successfully: {len(file_urls)} files")
            return Response({'status': 'success', 'file_urls': file_urls})
        except Exception as e:
            logger.error(f"Error in file upload: {str(e)}")
            return Response({'status': 'error', 'message': f'خطا در آپلود فایل: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MessageList(APIView):
    def get(self, request):
        try:
            group_id = request.GET.get('group_id')
            recipient_id = request.GET.get('recipient_id')
            messages = Message.objects.all()

            if group_id:
                messages = messages.filter(group_id=group_id)
            elif recipient_id:
                messages = messages.filter(sender_id=recipient_id) | messages.filter(recipient_id=recipient_id)

            message_data = [
                {
                    'id': msg.id,
                    'sender': {'id': msg.sender.id, 'username': msg.sender.username} if msg.sender else None,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                    'group': {'id': msg.group.id, 'name': msg.group.name} if msg.group else None,
                    'recipient': {'id': msg.recipient.id, 'username': msg.recipient.username} if msg.recipient else None,
                    'files': [{'id': f.id, 'file': f.file.url, 'file_type': f.file_type} for f in msg.files.all()],
                    'delivered_at': msg.delivered_at.isoformat() if msg.delivered_at else None,
                    'read_at': msg.read_at.isoformat() if msg.read_at else None
                } for msg in messages
            ]
            return Response(message_data)
        except Exception as e:
            logger.error(f"Error fetching messages: {str(e)}")
            return Response({'status': 'error', 'message': 'خطا در دریافت پیام‌ها'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            content = request.data.get('content')
            sender_id = request.data.get('sender_id')
            group_id = request.data.get('group_id')
            recipient_id = request.data.get('recipient_id')
            file_urls = request.data.get('file_urls', [])

            if not sender_id:
                logger.error("Sender ID missing")
                return Response({'status': 'error', 'message': 'شناسه فرستنده الزامی است'}, status=status.HTTP_400_BAD_REQUEST)

            message = Message.objects.create(
                sender_id=sender_id,
                content=content,
                group_id=group_id,
                recipient_id=recipient_id
            )

            for file_data in file_urls:
                file_obj = File.objects.get(id=file_data['id'])
                message.files.add(file_obj)

            logger.info(f"Message created by user {sender_id}")
            return Response({'status': 'success', 'message_id': message.id})
        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            return Response({'status': 'error', 'message': 'خطا در ارسال پیام'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GroupList(APIView):
    def get(self, request):
        try:
            groups = Group.objects.all()
            group_data = [
                {
                    'id': group.id,
                    'name': group.name,
                    'members': [{'id': m.id, 'username': m.username} for m in group.members.all()]
                } for group in groups
            ]
            return Response(group_data)
        except Exception as e:
            logger.error(f"Error fetching groups: {str(e)}")
            return Response({'status': 'error', 'message': 'خطا در دریافت گروه‌ها'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            name = request.data.get('name')
            description = request.data.get('description', '')
            creator_id = request.data.get('creator_id')
            member_ids = request.data.get('member_ids', [])

            if not name or not creator_id:
                logger.error("Group name or creator ID missing")
                return Response({'status': 'error', 'message': 'نام گروه و شناسه سازنده الزامی است'}, status=status.HTTP_400_BAD_REQUEST)

            group = Group.objects.create(
                name=name,
                description=description,
                creator_id=creator_id
            )
            group.members.add(*member_ids, creator_id)
            logger.info(f"Group {name} created by user {creator_id}")
            return Response({'status': 'success', 'group_id': group.id})
        except Exception as e:
            logger.error(f"Error creating group: {str(e)}")
            return Response({'status': 'error', 'message': 'خطا در ایجاد گروه'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StatsView(APIView):
    def get(self, request):
        try:
            user_id = request.session.get('user_id')
            if not user_id:
                logger.error("No user_id in session for stats")
                return Response({'status': 'error', 'message': 'کاربر وارد نشده است'}, status=status.HTTP_400_BAD_REQUEST)

            message_count = Message.objects.filter(sender_id=user_id).count()
            file_count = File.objects.filter(message__sender_id=user_id).count()
            login_count = UserActivity.objects.filter(user_id=user_id, action='login').count()
            online_time = sum(
                activity.details.get('duration', 0)
                for activity in UserActivity.objects.filter(user_id=user_id, action='online')
            )

            return Response({
                'message_count': message_count,
                'file_count': file_count,
                'login_count': login_count,
                'online_time': online_time
            })
        except Exception as e:
            logger.error(f"Error fetching stats: {str(e)}")
            return Response({'status': 'error', 'message': 'خطا در دریافت آمار'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
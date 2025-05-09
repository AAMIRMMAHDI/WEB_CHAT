from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Message, User
from .serializers import MessageSerializer, UserSerializer
from django.core.files.storage import FileSystemStorage
from django.contrib.sessions.models import Session
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'index.html')

class MessageList(APIView):
    def get(self, request):
        messages = Message.objects.all().order_by('timestamp')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.error(f"Message validation error: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserList(APIView):
    def get(self, request):
        Session.objects.filter(expire_date__lt=datetime.now()).delete()
        sessions = Session.objects.all()
        users = []
        now = datetime.now()
        five_minutes_ago = now - timedelta(minutes=5)

        for session in sessions:
            session_data = session.get_decoded()
            username = session_data.get('username')
            last_activity = session_data.get('last_activity')
            if username and last_activity:
                last_activity_time = datetime.fromisoformat(last_activity)
                is_online = last_activity_time > five_minutes_ago
                try:
                    user = User.objects.get(username=username)
                    users.append({'id': user.id, 'username': username, 'is_online': is_online})
                except User.DoesNotExist:
                    continue

        logger.info(f"Users fetched: {users}")
        return Response({'users': users})

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            logger.error("Username or password missing")
            return Response({'status': 'error', 'message': 'نام کاربری و رمز عبور الزامی است'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                request.session['username'] = username
                request.session['user_id'] = user.id
                request.session['last_activity'] = datetime.now().isoformat()
                request.session.modified = True
                logger.info(f"User {username} logged in")
                return Response({'status': 'success', 'user_id': user.id})
            else:
                logger.error(f"Invalid password for {username}")
                return Response({'status': 'error', 'message': 'نام کاربری یا رمز عبور اشتباه است'}, status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            user = User(username=username)
            user.set_password(password)
            user.save()
            request.session['username'] = username
            request.session['user_id'] = user.id
            request.session['last_activity'] = datetime.now().isoformat()
            request.session.modified = True
            logger.info(f"User {username} registered")
            return Response({'status': 'success', 'user_id': user.id})

class FileUpload(APIView):
    def post(self, request):
        file = request.FILES['file']
        if file.size > 20 * 1024 * 1024 * 1024:  # 20 گیگابایت
            return Response({'status': 'error', 'message': 'حجم فایل باید کمتر از 20 گیگابایت باشد'}, status=status.HTTP_400_BAD_REQUEST)
        
        fs = FileSystemStorage(location='Uploads/')
        filename = fs.save(file.name, file)
        file_url = fs.url(filename)
        logger.info(f"File uploaded: {file_url}")
        return Response({'status': 'success', 'file_url': file_url})
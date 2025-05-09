from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Message
from .serializers import MessageSerializer
from django.core.files.storage import FileSystemStorage
from django.contrib.sessions.models import Session
from datetime import datetime, timedelta
import logging

# تنظیم لاگ برای دیباگ
logger = logging.getLogger(__name__)

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
        # حذف session‌های منقضی‌شده
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
                users.append({'username': username, 'is_online': is_online})

        logger.info(f"Users fetched: {users}")
        return Response({'users': users})

    def post(self, request):
        username = request.data.get('username')
        if username:
            request.session['username'] = username
            request.session['last_activity'] = datetime.now().isoformat()
            request.session.modified = True
            logger.info(f"User {username} added to session")
            return Response({'status': 'success'})
        logger.error("No username provided in POST request")
        return Response({'status': 'error', 'message': 'Username required'}, status=status.HTTP_400_BAD_REQUEST)

class FileUpload(APIView):
    def post(self, request):
        file = request.FILES['file']
        fs = FileSystemStorage(location='Uploads/')
        filename = fs.save(file.name, file)
        file_url = fs.url(filename)
        logger.info(f"File uploaded: {file_url}")
        return Response({'status': 'success', 'file_url': file_url})
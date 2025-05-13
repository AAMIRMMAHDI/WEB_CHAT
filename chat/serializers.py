# chat/serializers.py
from rest_framework import serializers
from .models import Message, User, File, Group, UserActivity

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ['id', 'file', 'file_type', 'created_at']

class GroupSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)
    creator_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='creator', write_only=True
    )
    member_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True, source='members', write_only=True, required=False
    )

    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'creator', 'creator_id', 'members', 'member_ids', 'created_at', 'invite_code']

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True, allow_null=True)
    group = GroupSerializer(read_only=True, allow_null=True)
    sender_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='sender', write_only=True
    )
    recipient_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='recipient', write_only=True, required=False, allow_null=True
    )
    group_id = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), source='group', write_only=True, required=False, allow_null=True
    )
    files = FileSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'recipient', 'group', 'sender_id', 'recipient_id', 'group_id', 'content', 'timestamp', 'delivered_at', 'read_at', 'files']

class UserActivitySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserActivity
        fields = ['id', 'user', 'action', 'timestamp', 'details']
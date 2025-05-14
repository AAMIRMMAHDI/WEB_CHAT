from rest_framework import serializers
from .models import User, Group, Message, File

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'display_name', 'profile_image', 'is_online']

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ['id', 'file', 'file_type', 'uploaded_at']

class GroupSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)
    creator_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='creator', write_only=True
    )
    image = serializers.ImageField(allow_null=True, required=False)

    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'creator', 'creator_id', 'members', 'image', 'created_at']

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
    file_urls = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model = Message
        fields = ['id', 'sender', 'recipient', 'group', 'sender_id', 'recipient_id', 'group_id', 'content', 'timestamp', 'delivered_at', 'read_at', 'files', 'file_urls']

    def create(self, validated_data):
        file_urls = validated_data.pop('file_urls', [])
        message = Message.objects.create(**validated_data)
        for file_data in file_urls:
            File.objects.create(
                file=file_data['file'],
                file_type=file_data['file_type'],
                message=message
            )
        return message
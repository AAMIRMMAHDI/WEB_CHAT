from django.db import models
from django.contrib.auth.hashers import make_password, check_password
import random

class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    display_name = models.CharField(max_length=150, blank=True, null=True)
    password = models.CharField(max_length=128)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_online = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True, auto_now=True)
    created_at = models.DateTimeField(null=True, blank=True, auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = f"کاربر_{random.randint(1000, 9999)}"
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def __str__(self):
        return self.display_name or self.username

    class Meta:
        indexes = [
            models.Index(fields=['username']),
        ]

class Group(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    password = models.CharField(max_length=128, blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(User, related_name='groups')
    image = models.ImageField(upload_to='groups/', blank=True, null=True)
    created_at = models.DateTimeField(null=True, blank=True, auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password) if self.password else not raw_password

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['name']),
        ]

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='received_messages')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    content = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.sender} -> {self.recipient or self.group}: {self.content[:50]}"

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['sender', 'recipient']),
            models.Index(fields=['group']),
        ]

class File(models.Model):
    file = models.FileField(upload_to='uploads/')
    file_type = models.CharField(max_length=20, choices=[
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    ])
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='files', null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

    class Meta:
        indexes = [
            models.Index(fields=['uploaded_at']),
        ]
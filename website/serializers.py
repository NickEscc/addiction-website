# website/serializers.py

from dj_rest_auth.registration.serializers import RegisterSerializer as AllAuthRegisterSerializer
from rest_framework import serializers
from django.contrib.auth.models import User

class CustomRegisterSerializer(AllAuthRegisterSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    class Meta(AllAuthRegisterSerializer.Meta):
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'first_name', 'last_name')

    def save(self, request):
        user = super().save(request)
        user.first_name = self.data.get('first_name')
        user.last_name = self.data.get('last_name')
        user.save()
        return user

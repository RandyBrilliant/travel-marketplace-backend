from django.shortcuts import render
from rest_framework import viewsets
from account.models import CustomUser
from account.serializers import UserSerializer

# Create your views here.
class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

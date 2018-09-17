from django.shortcuts import render

# Create your views here.
from rest_framework import status
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from users.serializers import CreateUserSerializer


class UsernameCountView(APIView):
    def get(self, request, username):
        count = User.objects.filter(username=username).count()

        data = {
            'username': username,
            'count': count
        }

        return Response(data)


class MobileCountView(APIView):
    def get(self, reuqest, mobile):
        count = User.objects.filter(mobile=mobile).count()

        data = {
            'mobile': mobile,
            'count': count
        }

        return Response(data)


# class UserView(GenericAPIView):
class UserView(CreateAPIView):
    serializer_class = CreateUserSerializer

    # def post(self, request):
    #     # 获取参数并进行校验，（参数完整性，是否同意协议， 手机号格式，是否已注册，密码是否一致， 短信验证码是否正确）
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     # 保存用户注册信息
    #     serializer.save()
    #     # 返回注册用户数据
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)


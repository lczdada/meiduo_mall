from rest_framework import status
from rest_framework.generics import CreateAPIView, GenericAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


from users.models import User
from users.serializers import CreateUserSerializer, UserDetailSerializer, EmailSerializer


# PUT /emails/verification/?token=xxx
class VerifyEmailView(APIView):
    """邮箱验证"""
    def put(self, request):
        # 获取token
        token = request.query_params.get('token')
        if not token:
            return Response({'message': '缺少token'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证token
        user = User.check_verify_email_token(token)

        if user is None:
            return Response({'message': "链接信息无效"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user.email_active = True
            user.save()
            return Response({'message': 'OK'})


# put /email
class EmailView(UpdateAPIView):
# class EmailView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmailSerializer

    def get_object(self):
        return self.request.user

    # def put(self, request):
    #     # 获取用户
    #     # user = self.request.user
    #     user = self.get_object()
    #     # 根据user
    #     serializer = self.get_serializer(user, data=request.data)
    #     # 对邮箱进行检验（email必传，格式）
    #     serializer.is_valid(raise_exception=True)
    #     # 设置用户的邮箱并发送邮件
    #     serializer.save()

        # return Response(serializer.data)


# /user/
class UserDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserDetailSerializer

    def get_object(self):
        return self.request.user


    # def get(self, request):
    #
    #     user = self.get_object()
    #     serializer = self.get_serializer(user)
    #     return Response(serializer.data)


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


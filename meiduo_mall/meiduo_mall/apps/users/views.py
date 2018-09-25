from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.generics import CreateAPIView, GenericAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from areas import constants
from goods.models import SKU
from goods.serializers import SKUSerializer
from users.models import User, Address
from users.serializers import CreateUserSerializer, UserDetailSerializer, EmailSerializer, UserAddressSerializer, \
    AddressTitleSerializer, AddUserBrosingHinstorySerializer


class UserBrowsingHistoryView(CreateAPIView):
    """用户浏览记录"""
    serializer_class = AddUserBrosingHinstorySerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """获取"""
        user_id = request.user.id
        redis_conn = get_redis_connection('history')
        history = redis_conn.lrange("history_%s" % user_id, 0, constants.USER_BROWSING_HISTORY_COUNTS_LIMIT - 1)
        skus = []
        for sku_id in history:
            sku = SKU.objects.get(id=sku_id)
            skus.append(sku)

        s = SKUSerializer(skus, many=True)

        return Response(s.data)


class AppendAddressView(GenericAPIView):
    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 获取请求的参数
        # 将数据进行反序列化
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        # 查询数据库的地址
        user = self.request.user
        addresses_set = user.addresses.filter(is_deleted=False)
        # 序列化并返回
        serializer = self.get_serializer(addresses_set, many=True)
        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': constants.USER_ADDRESS_COUNTS_LIMIT,
            'addresses': serializer.data,
        })


class DeleteAddressView(GenericAPIView):
    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        # 根据主键查询对应地址，删除
        user = request.user
        address = user.addresses.get(pk=pk)
        address.is_deleted = True
        address.save()
        # 返回结果给前端
        return Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, pk):
        # 根据主键查询相应的地址，修改
        user = request.user
        address = user.addresses.get(pk=pk)
        # 序列化对应数据并返回
        serializer = self.get_serializer(address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ModifyAddressTitleView(GenericAPIView):
    serializer_class = AddressTitleSerializer

    def put(self, request, pk):
        # 查询对应新闻地址修改
        user = request.user
        address = user.addresses.get(pk=pk)
        # 序列化后返回
        serializer = self.get_serializer(address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ModifyAddresssStatusView(GenericAPIView):
    serializer_class = AddressTitleSerializer

    def put(self, request, pk):
        # 查询对应新闻地址修改
        user = request.user
        address = user.addresses.get(pk=pk)
        # 序列化后返回
        user.default_address = address
        user.save()

        return Response({'message': 'OK'}, status=status.HTTP_201_CREATED)


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


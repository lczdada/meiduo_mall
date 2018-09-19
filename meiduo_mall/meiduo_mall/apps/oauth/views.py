from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.settings import api_settings

from meiduo_mall.utils.exceptions import logger
from oauth.models import OAuthQQUser
from oauth.serializers import OAuthQQUserSerializer
from oauth.utils import OAuthQQ

# Create your views here.


# url(r'^qq/authorization/$', views.QQAuthURLView.as_view()),
class QQAuthURLView(APIView):
    """qq登录的url地址"""

    def get(self, request):
        next = request.query_params.get('next', '/')
        # 获取qq登录的url地址
        oauth = OAuthQQ(state=next)
        login_url = oauth.get_login_url()

        return Response({'login_url': login_url})


class QQAuthUserView(CreateAPIView):
    """qq登录的用户"""
    serializer_class = OAuthQQUserSerializer

    def get(self, request):
        # 1. 获取QQ返回的code
        code = request.query_params.get('code')

        try:
            # 2. 根据code获取access_token
            oauth = OAuthQQ()
            access_token = oauth.get_access_token(code)
            # 3. 根据access_token获取授权QQ用户的openid
            openid = oauth.get_openid(access_token)
        except BaseException as e:
            logger.error(e)
            return Response({'message': 'qq服务异常'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 4. 根据openid 查询tb_oatu_qq表，判断用户是否已经绑定账号
        try:
            oauth_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 4.2 未绑定  返回token
            token = oauth.generate_save_user_token(openid)
            return Response({'access_token': token})
        else:
            # 4.1 已绑定 生成JWT token
            #　补充生成记录登录状态的token
            user = oauth_user.user
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)

            response = Response({'token': token, 'user_id': user.id, 'username': user.username})

            return response

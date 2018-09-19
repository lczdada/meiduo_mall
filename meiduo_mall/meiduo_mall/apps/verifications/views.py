import random

# Create your views here.

from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from verifications import constants
from celery_tasks.sms import tasks as sms_tasks
# 获取一个日志器
import logging
logger = logging.getLogger('django')


# GET /sms_code/(?P<mobile>1[3-9]\d{9})/
# url(r'sms_code/(?P<mobile>1[3-9])\d{9})/$', views.SMSCodeView.as_view()),
class SMSCodeView(APIView):
    """smscode"""
    def get(self, request, mobile):
        """发送短信验证码"""
        # 这里利用redis管道进行存储，省去每次连接数据库的麻烦
        redis_conn = get_redis_connection('verify_codes')
        # 判断是否在60秒内
        send_flag = redis_conn.get('send_flag_%s' % mobile)
        if send_flag:
            return Response({'message': '请求过于频繁'}, status=status.HTTP_400_BAD_REQUEST)
        # 生成短信验证码
        sms_code = 123456
        print('123456')
        # 保存到redis
        pl = redis_conn.pipeline()
        pl.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex('send_flag_%s'% mobile, constants.SEND_SMS_CODE_INTERVAL, 1)
        pl.execute()
        # 发送
        sms_code_expire = constants.SMS_CODE_REDIS_EXPIRES // 60
        # sms_tasks.send_sms_code.delay(mobile, sms_code, sms_code_expire)
        # try:
        #     ccp = CCP()
        #     # 注意： 测试的短信模板编号为1
        #     res = ccp.send_template_sms(mobile, [sms_code, sms_code_expire], constants.SMS_CODE_TEMP_ID)
        # except BaseException as e:
        #     logger.error(e)
        #     return Response({'message': '发送短信异常'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        #
        # if res != 0:
        #     return Response({'mesage': '发送短信失败'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({'message': 'OK'})

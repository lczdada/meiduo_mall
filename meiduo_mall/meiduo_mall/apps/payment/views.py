import os

from alipay import AliPay
from django.conf import settings
from django.shortcuts import render
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Create your views here.
from orders.models import OrderInfo


class PaymentStatusView(APIView):
    """支付结果"""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        data = request.query_params.dict()
        signature = data.pop('sign')

        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "keys/alipay_public_key.pem"),  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
        )

        success = alipay.verify(data, signature)

        if not success:
            return Response({'message': '非法请求'}, status=status.HTTP_403_FORBIDDEN)

        # 获取订单编号和支付宝流水号
        order_id = data.get('out_trade_no')
        trade_id = data.get('trade_no')

        # 校验订单id（order_id）
        try:
            order = OrderInfo.objects.get(
                order_id=order_id,
                user=request.user,
                status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']
            )
        except OrderInfo.DoesNotExist:
            return Response({'message': '订单信息有误'}, status=status.HTTP_400_BAD_REQUEST)

        # 更新订单的支付状态
        order.status = OrderInfo.ORDER_STATUS_ENUM['UNSEND']
        order.save()

        return Response({'trade_id': trade_id})


class PaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """
        获取支付网址和参数
        1. 校验订单是否有效
        2. 组织支付宝支付网址和参数
        3. 返回支付报支付网址
        """
        user = request.user
        try:
            order = OrderInfo.objects.get(
            order_id=order_id,
            user=user,
            pay_method=OrderInfo.PAY_METHODS_ENUM['ALIPAY'],  #支付宝支付
            status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'],  # DAIZHIFU
        )
        except OrderInfo.DoesNotExist:
            return Response({'message': '无效的订单'}, status=status.HTTP_400_BAD_REQUEST)
        # 组织参数
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/alipay_public_key.pem"),  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
     )

        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_amount),
            subject="美多商城%s" % order_id,
            return_url="http://www.meiduo.site:8080/pay_success.html",
        )

        # 返回支付宝支付网址
        alipay_url = settings.ALIPAY_URL + '?' + order_string

        return Response({'alipay_url': alipay_url})
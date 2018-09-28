from decimal import Decimal

from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Create your views here.
from goods.models import SKU
from orders.serializers import OrderSettlementSerializer, OrderSKUSerializer, OrderSerializer


# POST /orders/
class OrdersView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def post(self, request):
        """
        提交订单数据保存（订单创建）：
        1. 获取参数并进行校验（完整性，地址是否存在，支付方式）
        2. 保存提交的订单数据
        3. 返回应答， 订单保存成功
        """
        # 1. 获取参数并进行校验（完整性，地址是否存在，支付方式）
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 2. 保存提交的订单数据
        serializer.save()
        # 3. 返回应答， 订单保存成功
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# /orders/settlement/
class OrderSettlementView(APIView):
    """订单计算"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """获取"""
        user = request.user

        # 从购物车中获取用户勾选要结算的商品信息
        redis_conn = get_redis_connection('carts')
        sku_ids = redis_conn.smembers('cart_selected_%s' % user.id)
        cart_dict = redis_conn.hgetall('cart_%s' % user.id)

        # 组织数据
        cart = {}

        for sku_id, count in cart_dict.items():
            cart[int(sku_id)] = int(count)

        # 2. 根据商品id获取对应商品的信息， 组织运费
        skus = SKU.objects.filter(id__in=sku_ids)

        for sku in skus:
            # 给sku对象增加属性count， 保存用户索要结算的该商品的数量count
            sku.count = cart[sku.id]

        # 组织运费
        freight = Decimal(10)
        #
        # serializer = OrderSKUSerializer(skus, many=True)
        # resp_data = {
        #     'freight': freight,
        #     'skus': serializer.data
        # }
        # return Response(resp_data)

        # 组织数据
        res_dict = {
            'freight': freight,
            'skus': skus
        }

        serializer = OrderSettlementSerializer(res_dict)
        return Response(serializer.data)

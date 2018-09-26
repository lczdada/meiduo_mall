import base64
import pickle

from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
# Create your views here.


# /cart/
from carts import constants
from carts.serializers import CartSerializer, CartSKUSerializer
from goods.models import SKU


class CartView(APIView):
    def perform_authentication(self, request):
        pass

    def get(self, request):
        """
        购物车记录获取
        1. 获取user
        2. 获取用户的购物车记录
            2.1 如果用户已登录， 从redis中获取用户的redis
            2.2 如果用户未登录， 从cookie中获取购物车记录
        3. 根据用户购物车中的商品sku_id获取对应的商品的信息
        4. 将商品数据序列化并返回
        """
        # 1. 获取user
        try:
            user = request.user
        except Exception:
            user = None

        # 2. 获取用户的购物车记录
        if user is not None and user.is_authenticated:
            # 2.1 如果用户已登录， 从redis中获取用户的redis
            redis_conn = get_redis_connection('carts')
            # 从redis中获取用户购物车记录中的sku_id
            cart_key = 'cart_%s' % user.id
            # hgetall(key): 获取redis中hash的属性和值
            # {
            #     b'<sku_id>': b'<count>',
            #     ...
            # }
            redis_cart = redis_conn.hgetall(cart_key)
            # 从redis中获取用户购物车记录被勾选后商品的sku_id
            cart_selected_key = 'cart_selected_%s' % user.id
            # smembers(key): 获取redis中set的所有元素
            # (b'<sku_id>', b'<sku_id>', ...)
            redis_cart_selected = redis_conn.smembers(cart_selected_key) # set
            cart_dict = {}
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in redis_cart_selected
                }
        else:
            # 2.2 如果用户未登录， 从cookie中获取购物车记录
            cookie_cart = request.COOKIES.get('cart')  # None
            if cookie_cart:
                # 解析cookie购物车数据
                # {
                #     '<sku_id>': {
                #         'count': '<count>',
                #         'selected': '<selected>'
                #     },
                #     ...
                # }
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                cart_dict = {}
        # 3. 根据用户购物车中的商品sku_id获取对应的商品的信息
        sku_ids = cart_dict.keys()
        # select * from tb_sku where id  in (1,2,3)
        skus = SKU.objects.filter(id__in=sku_ids)

        for sku in skus:
            # 给sku对象增加属性count和selected
            # 分别保存用户购物车中添加的该商品的数量和勾选状态
            sku.count = cart_dict[sku.id]['count']
            sku.selected = cart_dict[sku.id]['selected']
        # 4. 将商品数据序列化并返回
        skus_serializer = CartSKUSerializer(skus, many=True)
        return Response(skus_serializer.data)

    def post(self, request):
        """
        购物车记录添加
        1.获取参数并进行校验（参数完整性， sku_id对应的商品是否存在，库存是否足够）
        2.保存用户的购物车记录
            2.1 登录的用户 redis
            2.2 未登录的用户 cookies
        3.返回应答，购物车记录添加成功

        """
        # 购物车记录添加
        # 1.获取参数并进行校验（参数完整性， sku_id对应的商品是否存在，库存是否足够）
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 获取参数
        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']
        # 获取user  不管登录没有都有user参数
        try:
            user = request.user
        except Exception:
            user = None
        # 2.保存用户的购物车记录
        if user is not None and user.is_authenticated:
            # 2.1 如果用户已登录，在redis中保护用户肚饿购物车记录
            # 获取redis链接
            redis_conn = get_redis_connection('carts')
            # 在redis中存储用户添加商品的count hash
            cart_key = 'cart_%s' % user.id
            pl = redis_conn.pipeline()
            # 如果sku_id商品在购物车已经添加过了，则是数量的累加
            # 如果没有添加过， 则是设置新的属性，值
            pl.hincrby(cart_key, sku_id, count)

            # 在redis中存储用户购物车记录勾选状态 set
            cart_selected_key = 'cart_selected_%s' % user.id

            if selected:
                # 勾选
                pl.sadd(cart_selected_key, sku_id)

            pl.execute()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            # 2.2 未登录的用户 cookies
            cookie_cart = request.COOKIES.get('cart')  # None
            if cookie_cart:
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                cart_dict = {}
            # 保存购物车记录
            if sku_id in cart_dict:
                # 商品在购物车记录里，则增加数量
                count += cart_dict[sku_id]['count']
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }
            # 3.返回应答，购物车记录添加成功
            response = Response(serializer.data, status=status.HTTP_201_CREATED)
            # 设置购物车cookie数据
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('cart', cart_data, max_age=constants.CART_COOKIE_EXPIRES)
            return response

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
from carts.serializers import CartSerializer, CartSKUSerializer, CartDeleteSerializer, CartSelectAllSerialzier
from goods.models import SKU


class CartSelectAllView(APIView):
    """购物车全选"""
    def perform_authentication(self, request):
        pass

    def put(self, request):
        # 获取勾选状态并进行校验
        serializer = CartSelectAllSerialzier(data=request.data)
        serializer.is_valid(raise_exception=True)
        selected = serializer.validated_data['selected']

        # 2.获取user
        try:
            user = request.user
        except Exception:
            user = None

        # 3. 设置购物车中的商品全部为勾选
        if user and user.is_authenticated:
            # 登录，修改redis
            connection = get_redis_connection('carts')
            cart_key = 'cart_%s' % user.id

            # 获取用户购物车所有商品id
            sku_ids = connection.hkeys(cart_key)

            # 将sku_ids 添加到用户购物车勾选的商品数据中
            cart_selected_key = 'cart_selected_%s' % user.id
            if selected:
                connection.sadd(cart_selected_key, *sku_ids)
            else:
                connection.srem(cart_selected_key, *sku_ids)

            return Response({'message': 'OK'})
        else:
            response = Response({'message': 'OK'})

            # 未登录， 设置cookie
            cookie_cart = request.COOKIES.get('cart')

            if not cookie_cart:
                return response
            else:
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))

            if not cart_dict:
                return response

            for sku_id in cart_dict.keys():
                cart_dict[sku_id]['selected'] = selected

            # 返回应答，全选成功
            cookie_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('cart', cookie_data, expires=constants.CART_COOKIE_EXPIRES)
            return response


class CartView(APIView):
    def perform_authentication(self, request):
        pass

    def delete(self, request):
        """购物车记录删除"""
        # 获取sku_id并进行校验
        serializer = CartDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sku_id = serializer.validated_data['sku_id']

        # 获取user
        try:
            user = request.user
        except Exception:
            user = None

        # 删除用户的购物车记录
        if user and user.is_authenticated:
            # 登录，删除redis的记录
            connection = get_redis_connection('carts')
            pl = connection.pipeline()

            # 删除购物车记录中对应的商品id和count hash
            cart_key = 'cart_%s' % user.id
            # hdel(key, *fields): 删除hash中的指定属性和值，如果属性field不存在，直接忽略
            pl.hdel(cart_key, sku_id)

            # 删除购物车记录对应商品勾选状态
            cart_selected_key = 'cart_selected_%s' % user.id

            # srem(key, *values): 删除set中指定元素，如果元素不存在，直接忽略
            pl.srem(cart_selected_key, sku_id)

            pl.execute()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            # 未登录删除cookie中的记录
            response = Response(status=status.HTTP_204_NO_CONTENT)
            cookie_cart = request.COOKIES.get('cart')
            if cookie_cart is None:
                return response
            # 解析购物车中的数据
            cart_dict = pickle.loads(base64.b64decode(cookie_cart))

            if not cart_dict:
                return response

            # 删除购物车对应商品记录
            if sku_id in cart_dict:
                del cart_dict[sku_id]
                cookie_data = base64.b64encode(pickle.dumps(cart_dict)).decode()

                # 设置购物车cookie信息
                response.set_cookie('cart', cookie_data, expires=constants.CART_COOKIE_EXPIRES)

            return response

    def put(self, request):
        """
        用户的购物车记录更新:
        1. 获取参数并进行校验(参数完整性，sku_id对应的商品是否存在，商品库存是否足够)
        2. 获取user并处理
        3. 更新用户的购物车记录
            3.1 如果用户已登录，更新redis中对应购物车记录
            3.2 如果用户未登录，更新cookie中对应购物车记录
        4. 返回应答，购物车记录更新成功
        """
        # 1. 获取参数并进行校验(参数完整性，sku_id对应的商品是否存在，商品库存是否足够)
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 获取参数
        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']

        # 2. 获取user并处理
        try:
            user = request.user
        except Exception:
            user = None
        # 3. 更新用户的购物车记录
        if user and user.is_authenticated:
            # 3.1 如果用户已登录，更新redis中对应购物车记录
            connection = get_redis_connection('carts')
            # 在redis中更新对应sku_id商品的购物车count hash
            cart_key = 'cart_%s' % user.id

            pl = connection.pipeline()

            # hset(key, field, value): 将redis中hash的属性field设置值为value
            pl.hset(cart_key, sku_id, count)
            # 在redis中更新sku_id商品的勾选状态 set
            cart_selected_key = 'cart_selected_%s' % user.id
            if selected:
                # 勾选
                # sadd(key, *members): 将set集合添加元素，不需要关注元素是否重复
                pl.sadd(cart_selected_key, sku_id)
            else:
                # 取消勾选
                # srem(key, *members): 从set集合移除元素，有则移除，无则忽略
                pl.srem(cart_selected_key, sku_id)
            pl.execute()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            response = Response(serializer.data)
            # 3.2 如果用户未登录，更新cookie中对应购物车记录
            cookie_cart = request.COOKIES.get('cart')  # None

            if cookie_cart is None:
                return response

            # 解析cookie中的购物车数据
            cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            if not cart_dict:
                return response

            # 更新用户购物车中sku_id商品的数量和勾选状态
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 4. 返回应答，购物车记录更新成功
            # 处理
            cookie_data = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 设置购物车cookie
            response.set_cookie('cart', cookie_data, expires=constants.CART_COOKIE_EXPIRES)
            return response

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
        if user and user.is_authenticated:
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
        if user and user.is_authenticated:
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

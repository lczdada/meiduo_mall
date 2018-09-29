from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django_redis import get_redis_connection
from rest_framework import serializers

from carts.serializers import CartSKUSerializer
from goods.models import SKU
from meiduo_mall.utils.exceptions import logger
from orders.models import OrderInfo, OrderGoods


class OrderSerializer(serializers.ModelSerializer):
    """下单数据序列化器"""
    class Meta:
        model = OrderInfo
        fields = ('order_id', 'address', 'pay_method')
        read_only_fields = ('order_id',)
        extra_kwargs = {
            'address': {
                'write_only': True,
                'required': True,
            },
            'pay_method': {
                'write_only': True,
                'required': True
            }
        }

    def create(self, validated_data):
        """保存订单"""
        address = validated_data['address']
        pay_method = validated_data['pay_method']

        # 组织参数
        # 获取登录用户
        user = self.context['request'].user
        # 订单编号 格式： 年月日时分秒 + 用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + '%010d' % user.id

        # 订单商品总数量和实付款
        total_count = 0
        total_amount = Decimal(0)

        # 运费
        freight = Decimal(10)

        # 订单状态
        status = OrderInfo.ORDER_STATUS_ENUM['UNSEND'] if pay_method == OrderInfo.PAY_METHODS_ENUM['CASH'] else OrderInfo.ORDER_STATUS_ENUM['UNPAID']
        with transaction.atomic():
            # 创建一个保存点
            save_id = transaction.savepoint()
            try:
                # 1.向订单基本信息表添加一条记录
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=total_count,
                    total_amount=total_amount,
                    freight=freight,
                    pay_method=pay_method,
                    status=status
                )
                # 2.订单有几个商品，　需要向订单商品表添加几条记录
                redis_conn = get_redis_connection('carts')
                # 从redis中获取用户购物车中被勾选的商品的sku_id
                cart_selected_key = 'cart_selected_%s' % user.id
                sku_ids = redis_conn.smembers(cart_selected_key)
                # 从redis中获取用户购物车中所有商品的sku_id 和对应数量count hash
                cart_key = 'cart_%s' % user.id
                cart_dict = redis_conn.hgetall(cart_key)

                for sku_id in sku_ids:
                    # 获取用户所要购买的该商品的数量count
                    count = cart_dict[sku_id]
                    count = int(count)
                    for i in range(3):
                        # 根据sku_id 获取对应商品
                        sku = SKU.objects.get(id=sku_id)
                        # print('user: %s try get lock' % user.id)
                        # sku = SKU.objects.select_for_update().get(id=sku_id)
                        # print('user: %s get locked' % user.id)
                        # 判断商品的库存
                        if count > sku.stock:
                            # 回滚事务到sid保存点
                            transaction.savepoint_rollback(save_id)
                            raise serializers.ValidationError('商品库存不足')

                        # 记录原始商品的库存
                        origin_stock = sku.stock
                        new_stock = origin_stock - count
                        new_sales = sku.sales + count

                        # 模拟订单并发问题
                        print('user : %s times: %s stock: %s' % (user.id, i, origin_stock))
                        # import time
                        # time.sleep(10)

                        # 减少商品的库存， 增加销量
                        # sku.stock -= count
                        # sku.sales += count
                        # sku.save()
                        # update 返回更新的行数
                        res = SKU.objects.filter(id=sku_id, stock=origin_stock).\
                            update(stock=new_stock, sales=new_sales)
                        if res == 0:
                            # 更新失败，重新尝试
                            if i == 2:
                                # 说明重新尝试了3次，更新仍然失败，直接报下单失败
                                # 回滚事务到sid保存点
                                transaction.savepoint_rollback(save_id)
                                raise serializers.ValidationError('商品库存不足')
                            continue

                        # 向订单商品列表中添加一条记录
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=count,
                            price=sku.price
                        )
                        # 累加订单商品的总数量和总金额
                        total_count += count
                        total_amount += sku.price*count
                        # 更新成功，跳出循环
                        break

                # 计算实付款
                total_amount += freight
                # 更新订单记录中商品总数量和实付款
                order.total_count = total_count
                order.total_amount = total_amount
                order.save()
            except serializers.ValidationError:
                raise
            except Exception as e:
                logger.error(e)
                transaction.savepoint_rollback(save_id)
                raise
            # 3.清除redis中对应的购物车记录
            pl = redis_conn.pipeline()
            pl.hdel(cart_key, *sku_ids)
            pl.srem(cart_selected_key, *sku_ids)
            pl.execute()

            # 返回订单对象
            return order


class OrderSKUSerializer(serializers.ModelSerializer):
    """购物车商品数据序列化器"""
    count = serializers.IntegerField(label='数量')

    class Meta:
        model = SKU
        fields = ('id', 'name', 'default_image_url', 'price', 'count')


class OrderSettlementSerializer(serializers.Serializer):
    """订单结算数据序列化器"""
    freight = serializers.DecimalField(label='运费', max_digits=10, decimal_places=2)
    skus = CartSKUSerializer(many=True)


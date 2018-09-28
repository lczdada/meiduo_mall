from rest_framework import serializers

from goods.models import SKU


class CartSelectAllSerialzier(serializers.Serializer):
    """购物车全选"""
    selected = serializers.BooleanField(label='全选')


class CartDeleteSerializer(serializers.Serializer):
    sku_id = serializers.IntegerField(label='商品id', min_value=1)

    def validate_sku_id(self, value):
        try:
            sku = SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError('商品不存在')

        return value


class CartSerializer(serializers.Serializer):
    sku_id = serializers.IntegerField(label='商品SKU编号')
    count = serializers.IntegerField(label='商品数量')
    selected = serializers.BooleanField(label='勾选状态', default=True)

    def validate(self, attrs):
        """对参数进行验证"""
        # sku_id 对应的商品是否存在
        sku_id = attrs['sku_id']

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            raise serializers.ValidationError('商品不存在')

        # 商品库存是否足够
        count = attrs['count']
        if count > sku.stock:
            raise serializers.ValidationError('商品库存不足')

        return attrs


class CartSKUSerializer(serializers.ModelSerializer):
    """购物车商品序列化器类"""
    count = serializers.IntegerField(label='商品数量')


    class Meta:
        model = SKU
        fields = ('id', 'name', 'price', 'default_image_url', 'count')

from django.shortcuts import render
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

# Create your views here.
# 获取某个第三级分类的所有商品信息
# 分页，排序

# GET /categories/(?P<category_id>\d+)/skus/
from goods.models import SKU
from goods.serializers import SKUSerializer


class SKUListView(ListAPIView):
    serializer_class = SKUSerializer
    # queryset = SKU.objects.filter(catogry_id=category_id, islanched=True)

    def get_queryset(self):
        """指定当前视图所使用的查询集"""
        category_id = self.kwargs['category_id']
        return SKU.objects.filter(category_id=category_id, is_launched=True)



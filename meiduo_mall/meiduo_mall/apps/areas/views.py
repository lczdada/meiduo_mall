from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.cache.mixins import CacheResponseMixin
from areas.models import Area
from areas.serializers import AreaSerializer, SubAreaSerializer


class AreaViewSet(CacheResponseMixin, ReadOnlyModelViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return AreaSerializer
        else:
            return SubAreaSerializer

    def get_queryset(self):
        if self.action == 'list':
            return Area.objects.filter(parent=None)
        else:
            return Area.objects.all()


# class AreasView(ListAPIView):
#     """获取省级地区"""
#     serializer_class = AreaSerializer
#     queryset = Area.objects.filter(parent=None)
#     # def get(self, request):
#     #     # 查询省级地区的信息
#     #     area = self.get_object()
#     #     # 省级地区的信息序列化并返回
#     #     serializer = self.get_serializer(area, many=True)
#     #
#     #     return Response(serializer.data)
#
#
# # GET /areas/(?P<pk>\d+)/
# class SubAreaView(RetrieveAPIView):
#     """获取指定地区的子地区信息"""
#     serializer_class = SubAreaSerializer
#     queryset = Area.objects.all()
#     # 根据id查询对应的市级地区的信息
#     # def get(self, request, pk):
#     #     area = self.get_object()
#     #     # 将地区信息序列化并返回(将其下级地区的信息嵌套序列化并返回)
#     #     serializer = self.get_serializer(area)
#     #     return Response(serializer.data)

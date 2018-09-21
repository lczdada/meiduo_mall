from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from areas.models import Area
from areas.serializers import AreaSerializer


class AreasView(ListAPIView):
    """获取省级地区"""
    serializer_class = AreaSerializer
    queryset = Area.objects.filter(parent=None)
    # def get(self, request):
    #     # 查询省级地区的信息
    #     area = self.get_object()
    #     # 省级地区的照片序列化并返回
    #     serializer = self.get_serializer(area, many=True)
    #
    #     return Response(serializer.data)

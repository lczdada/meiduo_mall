# 自定义分页类
from rest_framework.pagination import PageNumberPagination


class StandardResultPagination(PageNumberPagination):
    # 指定默认页容量
    page_sie = 2
    # 获取分页数据时传递页容量名称
    page_size_query_param = 'page_size'
    # 指定最大页容量
    max_page_size = 20


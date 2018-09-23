from django.db import models


# Create your models here.
class Pic(models.Model):
    """图片上传你测试模型类"""
    image = models.ImageField(verbose_name='图片')
    class Meta:
        db_table = 'tb_pic'
        verbose_name = 'FDFS上传文件测试'
        verbose_name_plural = verbose_name

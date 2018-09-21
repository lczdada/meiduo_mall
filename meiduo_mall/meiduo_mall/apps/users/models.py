from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as JWTSSerializer, BadData
from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
from users.constants import VERIFY_EMAIL_TOKEN_EXPIRES


class User(AbstractUser):
    mobile = models.CharField(max_length=11, unique=True, verbose_name='手机号')
    email_active = models.BooleanField(default=False, verbose_name='邮箱验证状态')

    class Meta:
        db_table = 'tb_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def generate_verify_email_url(self):
        """生成对应用户的邮箱验证链接地址"""
        data = {
            'id': self.id,
            'email': self.email
        }

        serializer = JWTSSerializer(settings.SECRET_KEY, expires_in=VERIFY_EMAIL_TOKEN_EXPIRES)

        token = serializer.dumps(data).decode()

        verify_url = 'http://www.meiduo.site:8080/success_verify_email.html?token=' + token

        return verify_url

    @staticmethod
    def check_verify_email_token(token):
        """检查验证邮件的token"""
        serializer = JWTSSerializer(settings.SECRET_KEY,  expires_in=VERIFY_EMAIL_TOKEN_EXPIRES)
        try:
            data = serializer.loads(token)
        except BadData:
            return None
        else:
            email = data.get('email')
            user_id = data.get('id')
            try:
                user = User.objects.get(id=user_id, email=email)
            except User.DoesNotExist:
                return None
            else:
                return user




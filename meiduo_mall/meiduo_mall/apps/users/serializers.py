import re

from django.conf import settings
from django.core.mail import send_mail
from django_redis import get_redis_connection
from rest_framework import serializers

from celery_tasks.email.tasks import send_verify_email
from users.models import User, Address


class EmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email')
        extra_kwargs = {
            'email': {
                'required': True
            }
        }

    def update(self, instance, validated_data):
        """
        设置用户邮箱并发送邮件
        :param instance: 创建序列化器时传递的对象
        :param validated_data:
        """
        # 设置用户的邮箱
        email = validated_data['email']
        instance.email = email
        instance.save()
        verify_url = instance.generate_verify_email_url()
        # celery发送邮件
        send_verify_email(email, verify_url)
        return instance


class CreateUserSerializer(serializers.ModelSerializer):
    """创建用户的序列化器类"""
    password2 = serializers.CharField(label='确认密码', write_only=True)
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    allow = serializers.CharField(label='是否同意协议', write_only=True)
    token = serializers.CharField(label='登录状态token', read_only=True)  # 增加token字段

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'password2', 'sms_code', 'mobile', 'allow', 'token')
        extra_kwargs = {
            'username': {
                'min_length': 5,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许5-20个字符的用户名',
                    'max_length': '仅允许5-20个字符的用户名'

                }
            },
            'password': {
                'write_only': True,
                'min_length': 5,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许5-20个字符的密码',
                    'max_length': '仅允许5-20个字符的密码'
                }
            }
        }

    def validate_allow(self, value):
        if value != 'true':
            raise serializers.ValidationError('请同意协议')

    def validate_mobile(self, value):
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机格式不正确')

        # 手机是否已经注册
        count = User.objects.filter(mobile=value).count()

        if count:
            raise serializers.ValidationError('手机号已存在')

        return value

    def validate(self, attrs):
        # 判断两次密码
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError('两次密码不一致')
        # 判断短信验证码
        redis_conn = get_redis_connection('verify_codes')
        mobile = attrs['mobile']
        real_sms_code = redis_conn.get('sms_%s' % mobile)  # bytes
        if real_sms_code is None:
            raise serializers.ValidationError('短信验证码已过期')
        # 对比
        sms_code = attrs['sms_code']  # str

        # bytes>str
        real_sms_code = real_sms_code.decode()
        if real_sms_code != sms_code:
            raise serializers.ValidationError('短信验证码错误')

        return attrs

    def create(self, validated_data):
        del validated_data['password2']
        del validated_data['sms_code']
        del validated_data['allow']

        # 保存用户的信息
        user = User.objects.create_user(**validated_data)

         # 补充生成记录登陆状态的token

        from rest_framework_jwt.settings import api_settings

        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        user.token = token

        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """用户详细信息序列化器类"""
    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'email', 'email_active')


class UserAddressSerializer(serializers.ModelSerializer):
    province = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province_id = serializers.IntegerField(label='省id', required=True)
    city_id = serializers.IntegerField(label='市id', required=True)
    district_id = serializers.IntegerField(label='区id', required=True)

    class Meta:
        model = Address
        exclude = ('user', 'is_deleted', 'create_time', 'update_time')

    def validate_mobile(self, value):
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def create(self, validated_data):
        """保存"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AddressTitleSerializer(serializers.ModelSerializer):
    """
    地址标题
    """
    class Meta:
        model = Address
        fields = ('title',)


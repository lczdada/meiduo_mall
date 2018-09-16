import logging

from celery_tasks.main import app
from .yuntongxun.sms import CCP

logger = logging.getLogger('django')

# 验证短信模板

SMS_CODE_TEMP_ID = 1

@app.task(name='send_sms_code')
def send_sms_code(mobile, code, expires):
    try:
        ccp = CCP()
        res = ccp.send_template_sms(mobile, [code, expires], SMS_CODE_TEMP_ID)
    except BaseException as e:
        logger.error(e)
    else:
        if res == 0:
            logger.info(f'发送成功{mobile}')
        else:
            logger.warning(f'发送失败{mobile}')

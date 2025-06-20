from flask import current_app
from flask_mail import Mail, Message

mail = Mail()

def init_mail(app):
    mail.init_app(app)

def send_email(to, subject, template, **kwargs):
    """
    이메일을 발송하는 유틸리티 함수.
    :param to: 수신자 이메일 주소 (문자열 또는 리스트)
    :param subject: 이메일 제목
    :param template: 이메일 템플릿 (렌더링된 HTML 문자열)
    :param kwargs: 템플릿 렌더링에 필요한 추가 인자
    """
    try:
        msg = Message(
            subject,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to] if isinstance(to, str) else to
        )
        msg.html = template
        mail.send(msg)
        current_app.logger.info(f"Email sent successfully to {to} with subject: {subject}")
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {to}: {e}")
        raise 
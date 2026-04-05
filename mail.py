import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Union

logger = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    return bool(os.getenv('MAIL_SERVER', '').strip())


def is_smtp_configured() -> bool:
    """Публичная проверка: настроен ли SMTP (для логики «письмо обязательно»)."""
    return _smtp_configured()


def send_email(
    subject: str,
    body_text: str,
    to_addrs: Union[str, List[str]],
    html_body: Union[str, None] = None,
) -> bool:
    """Отправка письма через SMTP. Переменные: MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER."""
    if isinstance(to_addrs, str):
        to_addrs = [to_addrs]

    server = os.getenv('MAIL_SERVER', '').strip()
    if not server:
        logger.warning(
            'MAIL_SERVER не задан — письмо не отправлено (только лог). '
            'Тема: %s, получатели: %s',
            subject,
            to_addrs,
        )
        logger.info('Текст письма:\n%s', body_text)
        return False

    port = int(os.getenv('MAIL_PORT', '587'))
    use_tls = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    use_ssl = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true' or port == 465
    username = os.getenv('MAIL_USERNAME', '').strip()
    password = os.getenv('MAIL_PASSWORD', '')
    default_sender = os.getenv('MAIL_DEFAULT_SENDER', username or 'noreply@localhost')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = default_sender
    msg['To'] = ', '.join(to_addrs)
    msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
    if html_body:
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(server, port, timeout=30) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.sendmail(default_sender, to_addrs, msg.as_string())
        else:
            with smtplib.SMTP(server, port, timeout=30) as smtp:
                if use_tls:
                    smtp.starttls()
                if username:
                    smtp.login(username, password)
                smtp.sendmail(default_sender, to_addrs, msg.as_string())
        return True
    except Exception as e:
        logger.exception('Ошибка отправки почты: %s', e)
        return False

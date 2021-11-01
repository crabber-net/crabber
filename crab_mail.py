from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import smtplib
import ssl
from typing import Dict, Optional


class CrabMail:
    def __init__(self, address: str, password: str):
        self.address: str = address
        self.password: str = password

    def send_mail(self, recipient: str, subject: str, body: str,
                  html_body: Optional[str] = None) -> bool:
        """ Sends plaintext or HTML email.

            :param recipient: The recipient's email address.
            :param subject: The subject line of the email.
            :param body: The body of the email. Must be plain text.
            :param html_body: Optional HTML body of the email. Clients will
                fallback on `body` if they cannot display HTML.
            :returns: Whether the message sent successfully.
        """
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = f'Crabber <{self.address}>'
        message['To'] = recipient

        # Attach plaintext body
        message.attach(MIMEText(body, 'plain'))
        # Attach HTML body if exists
        if html_body:
            message.attach(MIMEText(html_body, 'html'))

        # Login and send
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', port=465, context=context) \
                as server:
            server.login(self.address, self.password)
            send_status = server.sendmail(self.address, recipient,
                                          message.as_string())

        return not send_status

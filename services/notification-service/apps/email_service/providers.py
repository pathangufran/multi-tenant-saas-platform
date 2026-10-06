from dataclasses import dataclass
from django.core.mail import EmailMessage

@dataclass(frozen=True)
class EmailMessageData:
    recipient: str
    subject: str
    body: str
    sender: str
    
class EmailProvider:
    """
    Email provider abstraction.

    The initial implementation uses Django's configured
    email backend. Production can configure SMTP or another
    Django-compatible backend through settings.
    """
    
    @staticmethod
    def send(message: EmailMessageData) -> int:
        email = EmailMessage(
            subject=message.subject,
            body=message.body,
            from_email=message.sender,
            to=[message.recipient],
        )
        
        return email.send(
            fail_silently=False,
        )
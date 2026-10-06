from django.conf import settings
from .providers import EmailMessageData,EmailProvider

class EmailService:
    
    @staticmethod
    def send_email(
        *,
        recipient: str,
        subject: str,
        body: str,   
    ) -> int:
        
        recipient = recipient.strip()
        subject = subject.strip()
        
        if not recipient:
            raise ValueError(
                "Recipient is required."
            )
            
        if not subject:
            raise ValueError(
                "Subject is required."
            )
            
        if not body:
            raise ValueError(
                "Body is required."
            )
            
        message = EmailMessageData(
            recipient=recipient,
            subject=subject,
            body=body,
            sender=settings.DEFAULT_FROM_EMAIL,
        )
        
        return EmailProvider.send(message)
    
    @staticmethod
    def send_welcome_email(
        *,
        recipient: str,
        user_name: str,
    ) -> int:
        
        user_name = user_name.strip()
        
        if not user_name:
            raise ValueError(
                "User name is required."
            )
            
        return EmailService.send_email(
            recipient=recipient,
            subject="Welcome to the SaaS Platform",
            body=(
                f"Hello {user_name},\n\n"
                "Welcome to the SaaS Platform.\n\n"
                "Your account has been created successfully."
            ),
        )
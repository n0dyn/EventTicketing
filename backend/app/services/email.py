"""
Email service for sending notifications
"""
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi import BackgroundTasks
from jinja2 import Environment, FileSystemLoader

from app.core.config import settings
from app.models.user import User
from app.models.event import Event
from app.models.order import Order

logger = logging.getLogger(__name__)

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USER,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.EMAILS_FROM_EMAIL,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_STARTTLS=settings.SMTP_TLS,
    MAIL_SSL_TLS=settings.SMTP_SSL,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent / "../templates/email",
)

# Initialize FastMail
fastmail = FastMail(conf)

# Initialize Jinja2 environment for email templates
template_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "../templates/email"),
    autoescape=True
)


class EmailService:
    """Service for handling email operations"""
    
    @staticmethod
    async def send_email(
        email_to: str,
        subject: str,
        html_body: str,
        background_tasks: Optional[BackgroundTasks] = None
    ):
        """Send a single email"""
        try:
            message = MessageSchema(
                subject=subject,
                recipients=[email_to],
                body=html_body,
                subtype=MessageType.html,
            )
            
            if background_tasks:
                background_tasks.add_task(fastmail.send_message, message)
            else:
                await fastmail.send_message(message)
                
            logger.info(f"Email sent successfully to {email_to}")
            
        except Exception as e:
            logger.error(f"Failed to send email to {email_to}: {str(e)}")
            raise
    
    @staticmethod
    def render_template(template_name: str, context: Dict[str, Any]) -> str:
        """Render an email template with context"""
        try:
            template = template_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {str(e)}")
            raise
    
    @staticmethod
    async def send_welcome_email(
        user: User, 
        background_tasks: Optional[BackgroundTasks] = None
    ):
        """Send welcome email to new user"""
        subject = f"Welcome to {settings.PROJECT_NAME}!"
        
        context = {
            "user_name": user.full_name or user.email,
            "project_name": settings.PROJECT_NAME,
            "login_url": f"{settings.FRONTEND_URL}/auth/login",
        }
        
        html_body = EmailService.render_template("welcome.html", context)
        
        await EmailService.send_email(
            email_to=user.email,
            subject=subject,
            html_body=html_body,
            background_tasks=background_tasks
        )
    
    @staticmethod
    async def send_password_reset_email(
        email_to: str,
        reset_token: str,
        background_tasks: Optional[BackgroundTasks] = None
    ):
        """Send password reset email"""
        subject = f"Password reset - {settings.PROJECT_NAME}"
        
        context = {
            "project_name": settings.PROJECT_NAME,
            "reset_url": f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}",
            "valid_hours": 24,  # Token validity
        }
        
        html_body = EmailService.render_template("password_reset.html", context)
        
        await EmailService.send_email(
            email_to=email_to,
            subject=subject,
            html_body=html_body,
            background_tasks=background_tasks
        )
    
    @staticmethod
    async def send_order_confirmation_email(
        user: User,
        order: Order,
        event: Event,
        background_tasks: Optional[BackgroundTasks] = None
    ):
        """Send order confirmation email"""
        subject = f"Order Confirmation - {event.title}"
        
        context = {
            "user_name": user.full_name or user.email,
            "order_number": order.order_number,
            "event_title": event.title,
            "event_date": event.start_date,
            "event_location": event.location,
            "total_amount": order.total_amount,
            "currency": "USD",  # TODO: Make this configurable
            "project_name": settings.PROJECT_NAME,
        }
        
        html_body = EmailService.render_template("order_confirmation.html", context)
        
        await EmailService.send_email(
            email_to=user.email,
            subject=subject,
            html_body=html_body,
            background_tasks=background_tasks
        )
    
    @staticmethod
    async def send_ticket_delivery_email(
        user: User,
        order: Order,
        event: Event,
        tickets_data: List[Dict[str, Any]],
        background_tasks: Optional[BackgroundTasks] = None
    ):
        """Send email with ticket information"""
        subject = f"Your Tickets - {event.title}"
        
        context = {
            "user_name": user.full_name or user.email,
            "event_title": event.title,
            "event_date": event.start_date,
            "event_location": event.location,
            "order_number": order.order_number,
            "tickets": tickets_data,
            "project_name": settings.PROJECT_NAME,
        }
        
        html_body = EmailService.render_template("ticket_delivery.html", context)
        
        await EmailService.send_email(
            email_to=user.email,
            subject=subject,
            html_body=html_body,
            background_tasks=background_tasks
        )
    
    @staticmethod
    async def send_event_reminder_email(
        user: User,
        event: Event,
        hours_until_event: int,
        background_tasks: Optional[BackgroundTasks] = None
    ):
        """Send event reminder email"""
        subject = f"Reminder: {event.title} is starting soon!"
        
        context = {
            "user_name": user.full_name or user.email,
            "event_title": event.title,
            "event_date": event.start_date,
            "event_location": event.location,
            "hours_until": hours_until_event,
            "project_name": settings.PROJECT_NAME,
        }
        
        html_body = EmailService.render_template("event_reminder.html", context)
        
        await EmailService.send_email(
            email_to=user.email,
            subject=subject,
            html_body=html_body,
            background_tasks=background_tasks
        )
    
    @staticmethod
    async def send_payment_receipt_email(
        user: User,
        order: Order,
        payment_details: Dict[str, Any],
        background_tasks: Optional[BackgroundTasks] = None
    ):
        """Send payment receipt email"""
        subject = f"Payment Receipt - Order #{order.order_number}"
        
        context = {
            "user_name": user.full_name or user.email,
            "order_number": order.order_number,
            "payment_amount": payment_details.get("amount", order.total_amount),
            "payment_method": payment_details.get("payment_method", "Card"),
            "payment_date": payment_details.get("payment_date"),
            "transaction_id": payment_details.get("transaction_id"),
            "currency": "USD",
            "project_name": settings.PROJECT_NAME,
        }
        
        html_body = EmailService.render_template("payment_receipt.html", context)
        
        await EmailService.send_email(
            email_to=user.email,
            subject=subject,
            html_body=html_body,
            background_tasks=background_tasks
        )
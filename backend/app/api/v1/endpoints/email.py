"""
Email endpoints for testing and admin use
"""
from typing import Any

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_superuser
from app.models.user import User
from app.services.email import EmailService
from app.core.config import settings

router = APIRouter()


@router.post("/test")
async def send_test_email(
    email_to: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_superuser)
) -> Any:
    """
    Test email sending (superuser only)
    """
    if not settings.EMAILS_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="Email service is not configured"
        )
    
    try:
        html_body = EmailService.render_template("welcome.html", {
            "user_name": "Test User",
            "project_name": settings.PROJECT_NAME,
            "login_url": f"{settings.FRONTEND_URL}/auth/login"
        })
        
        await EmailService.send_email(
            email_to=email_to,
            subject=f"Test Email from {settings.PROJECT_NAME}",
            html_body=html_body,
            background_tasks=background_tasks
        )
        
        return {"message": f"Test email sent to {email_to}"}
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}"
        )


@router.post("/welcome/{user_id}")
async def send_welcome_email(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> Any:
    """
    Send welcome email to a user (superuser only)
    """
    if not settings.EMAILS_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="Email service is not configured"
        )
    
    from app.services.user import get_user_by_id
    
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        await EmailService.send_welcome_email(
            user=user,
            background_tasks=background_tasks
        )
        
        return {"message": f"Welcome email sent to {user.email}"}
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send welcome email: {str(e)}"
        )
"""
Background task scheduler using APScheduler
"""
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.tasks.email_tasks import send_event_reminders, send_daily_digest
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler = None


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the background task scheduler"""
    global scheduler
    
    if scheduler is not None:
        return scheduler
    
    scheduler = AsyncIOScheduler()
    
    # Add event reminder task - runs every hour
    scheduler.add_job(
        send_event_reminders,
        trigger=CronTrigger(minute=0),  # Run at the top of every hour
        id='send_event_reminders',
        name='Send Event Reminders',
        replace_existing=True,
        max_instances=1,
    )
    
    # Add daily digest task - runs at 8 AM daily
    scheduler.add_job(
        send_daily_digest,
        trigger=CronTrigger(hour=8, minute=0),  # Run at 8:00 AM daily
        id='send_daily_digest',
        name='Send Daily Digest',
        replace_existing=True,
        max_instances=1,
    )
    
    logger.info("Background task scheduler configured")
    return scheduler


def start_scheduler():
    """Start the background task scheduler"""
    global scheduler
    
    if scheduler is None:
        scheduler = create_scheduler()
    
    if not scheduler.running:
        scheduler.start()
        logger.info("Background task scheduler started")
    else:
        logger.info("Background task scheduler already running")


def stop_scheduler():
    """Stop the background task scheduler"""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Background task scheduler stopped")


def get_scheduler_status():
    """Get the current status of the scheduler"""
    global scheduler
    
    if scheduler is None:
        return {"status": "not_created"}
    
    return {
        "status": "running" if scheduler.running else "stopped",
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in scheduler.get_jobs()
        ]
    }


# For development/testing - manual task triggers
async def trigger_event_reminders():
    """Manually trigger event reminders task"""
    try:
        await send_event_reminders()
        logger.info("Manual event reminders task completed")
    except Exception as e:
        logger.error(f"Manual event reminders task failed: {str(e)}")
        raise


async def trigger_daily_digest():
    """Manually trigger daily digest task"""
    try:
        await send_daily_digest()
        logger.info("Manual daily digest task completed")
    except Exception as e:
        logger.error(f"Manual daily digest task failed: {str(e)}")
        raise
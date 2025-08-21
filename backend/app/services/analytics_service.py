"""
Comprehensive analytics and reporting service
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from enum import Enum
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, cast, String, Date, extract
from sqlalchemy.orm import selectinload

from app.models.event import Event
from app.models.user import User
from app.models.organization import Organization
from app.models.order import Order
from app.models.payment import Payment
from app.models.ticket import Ticket
from app.models.attendee import Attendee

logger = logging.getLogger(__name__)


class DateRange(str, Enum):
    """Date range options for analytics"""
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_YEAR = "this_year"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"


@dataclass
class AnalyticsMetric:
    """Analytics metric data structure"""
    name: str
    value: float
    change: Optional[float] = None
    change_percentage: Optional[float] = None
    period: str = ""


class DateRangeCalculator:
    """Utility for calculating date ranges"""
    
    @staticmethod
    def get_date_range(range_type: DateRange, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Tuple[datetime, datetime]:
        """Calculate start and end datetime for given range type"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if range_type == DateRange.TODAY:
            return today, today + timedelta(days=1)
        
        elif range_type == DateRange.YESTERDAY:
            yesterday = today - timedelta(days=1)
            return yesterday, today
        
        elif range_type == DateRange.LAST_7_DAYS:
            return today - timedelta(days=7), today
        
        elif range_type == DateRange.LAST_30_DAYS:
            return today - timedelta(days=30), today
        
        elif range_type == DateRange.LAST_90_DAYS:
            return today - timedelta(days=90), today
        
        elif range_type == DateRange.THIS_MONTH:
            month_start = today.replace(day=1)
            return month_start, today
        
        elif range_type == DateRange.LAST_MONTH:
            month_start = today.replace(day=1)
            last_month_end = month_start - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            return last_month_start, month_start
        
        elif range_type == DateRange.THIS_YEAR:
            year_start = today.replace(month=1, day=1)
            return year_start, today
        
        elif range_type == DateRange.LAST_YEAR:
            last_year = today.year - 1
            year_start = datetime(last_year, 1, 1)
            year_end = datetime(last_year + 1, 1, 1)
            return year_start, year_end
        
        elif range_type == DateRange.CUSTOM and start_date and end_date:
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            return start_dt, end_dt
        
        else:
            # Default to last 30 days
            return today - timedelta(days=30), today


class RevenueAnalyticsService:
    """Service for revenue analytics"""
    
    @staticmethod
    async def get_revenue_overview(
        db: AsyncSession,
        date_range: DateRange = DateRange.LAST_30_DAYS,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        organization_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get comprehensive revenue overview"""
        try:
            # Calculate date range
            range_start, range_end = DateRangeCalculator.get_date_range(date_range, start_date, end_date)
            
            # Base conditions
            conditions = [
                Order.status == "completed",
                Order.created_at >= range_start,
                Order.created_at <= range_end
            ]
            
            if organization_id:
                conditions.append(Event.organization_id == organization_id)
            
            # Current period revenue
            current_revenue_query = select(
                func.sum(Order.total_amount).label("total_revenue"),
                func.count(Order.id).label("total_orders"),
                func.avg(Order.total_amount).label("avg_order_value"),
                func.count(func.distinct(Order.user_id)).label("unique_customers")
            ).select_from(Order)
            
            if organization_id:
                current_revenue_query = current_revenue_query.join(Event)
            
            current_revenue_query = current_revenue_query.where(and_(*conditions))
            
            current_result = await db.execute(current_revenue_query)
            current_row = current_result.first()
            
            # Previous period for comparison
            period_duration = range_end - range_start
            prev_start = range_start - period_duration
            prev_end = range_start
            
            prev_conditions = [
                Order.status == "completed",
                Order.created_at >= prev_start,
                Order.created_at <= prev_end
            ]
            
            if organization_id:
                prev_conditions.append(Event.organization_id == organization_id)
            
            prev_revenue_query = select(
                func.sum(Order.total_amount).label("total_revenue"),
                func.count(Order.id).label("total_orders")
            ).select_from(Order)
            
            if organization_id:
                prev_revenue_query = prev_revenue_query.join(Event)
            
            prev_revenue_query = prev_revenue_query.where(and_(*prev_conditions))
            
            prev_result = await db.execute(prev_revenue_query)
            prev_row = prev_result.first()
            
            # Calculate metrics
            current_revenue = float(current_row.total_revenue or 0)
            prev_revenue = float(prev_row.total_revenue or 0)
            revenue_change = current_revenue - prev_revenue
            revenue_change_pct = (revenue_change / prev_revenue * 100) if prev_revenue > 0 else 0
            
            current_orders = current_row.total_orders or 0
            prev_orders = prev_row.total_orders or 0
            orders_change = current_orders - prev_orders
            orders_change_pct = (orders_change / prev_orders * 100) if prev_orders > 0 else 0
            
            avg_order_value = float(current_row.avg_order_value or 0)
            unique_customers = current_row.unique_customers or 0
            
            return {
                "period": {
                    "start": range_start.isoformat(),
                    "end": range_end.isoformat(),
                    "type": date_range
                },
                "metrics": {
                    "total_revenue": {
                        "value": current_revenue,
                        "change": revenue_change,
                        "change_percentage": round(revenue_change_pct, 2)
                    },
                    "total_orders": {
                        "value": current_orders,
                        "change": orders_change,
                        "change_percentage": round(orders_change_pct, 2)
                    },
                    "average_order_value": {
                        "value": avg_order_value,
                        "change": None,  # Would need more complex calculation
                        "change_percentage": None
                    },
                    "unique_customers": {
                        "value": unique_customers,
                        "change": None,
                        "change_percentage": None
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue overview: {str(e)}")
            return {"period": {}, "metrics": {}}
    
    @staticmethod
    async def get_daily_revenue_trend(
        db: AsyncSession,
        date_range: DateRange = DateRange.LAST_30_DAYS,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        organization_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get daily revenue trend data"""
        try:
            range_start, range_end = DateRangeCalculator.get_date_range(date_range, start_date, end_date)
            
            conditions = [
                Order.status == "completed",
                Order.created_at >= range_start,
                Order.created_at <= range_end
            ]
            
            if organization_id:
                conditions.append(Event.organization_id == organization_id)
            
            daily_query = select(
                cast(Order.created_at, Date).label("date"),
                func.sum(Order.total_amount).label("revenue"),
                func.count(Order.id).label("orders"),
                func.count(func.distinct(Order.user_id)).label("customers")
            ).select_from(Order)
            
            if organization_id:
                daily_query = daily_query.join(Event)
            
            daily_query = daily_query.where(and_(*conditions)).group_by(
                cast(Order.created_at, Date)
            ).order_by(cast(Order.created_at, Date))
            
            result = await db.execute(daily_query)
            
            return [
                {
                    "date": row.date.isoformat(),
                    "revenue": float(row.revenue or 0),
                    "orders": row.orders,
                    "customers": row.customers
                }
                for row in result
            ]
            
        except Exception as e:
            logger.error(f"Error getting daily revenue trend: {str(e)}")
            return []


class EventAnalyticsService:
    """Service for event-specific analytics"""
    
    @staticmethod
    async def get_event_performance(
        db: AsyncSession,
        event_id: int
    ) -> Dict[str, Any]:
        """Get comprehensive event performance metrics"""
        try:
            # Event details
            event = await db.get(Event, event_id)
            if not event:
                return {"error": "Event not found"}
            
            # Revenue metrics
            revenue_query = select(
                func.sum(Order.total_amount).label("total_revenue"),
                func.count(Order.id).label("total_orders"),
                func.avg(Order.total_amount).label("avg_order_value")
            ).where(
                and_(
                    Order.event_id == event_id,
                    Order.status == "completed"
                )
            )
            
            revenue_result = await db.execute(revenue_query)
            revenue_row = revenue_result.first()
            
            # Ticket sales
            ticket_sales_query = select(
                Ticket.name,
                Ticket.price,
                Ticket.quantity_total,
                Ticket.quantity_sold,
                (Ticket.quantity_total - Ticket.quantity_sold).label("quantity_available")
            ).where(Ticket.event_id == event_id)
            
            ticket_sales_result = await db.execute(ticket_sales_query)
            ticket_sales = ticket_sales_result.all()
            
            # Attendee demographics (if implemented)
            attendee_count_query = select(
                func.count(Attendee.id).label("total_attendees")
            ).where(Attendee.event_id == event_id)
            
            attendee_result = await db.execute(attendee_count_query)
            attendee_row = attendee_result.first()
            
            # Sales timeline
            daily_sales_query = select(
                cast(Order.created_at, Date).label("date"),
                func.sum(Order.total_amount).label("revenue"),
                func.count(Order.id).label("orders")
            ).where(
                and_(
                    Order.event_id == event_id,
                    Order.status == "completed"
                )
            ).group_by(cast(Order.created_at, Date)).order_by(cast(Order.created_at, Date))
            
            daily_sales_result = await db.execute(daily_sales_query)
            daily_sales = daily_sales_result.all()
            
            return {
                "event": {
                    "id": event.id,
                    "title": event.title,
                    "start_date": event.start_date.isoformat() if event.start_date else None,
                    "max_attendees": event.max_attendees
                },
                "revenue": {
                    "total": float(revenue_row.total_revenue or 0),
                    "orders": revenue_row.total_orders or 0,
                    "average_order": float(revenue_row.avg_order_value or 0)
                },
                "tickets": [
                    {
                        "name": ticket.name,
                        "price": float(ticket.price),
                        "total_quantity": ticket.quantity_total,
                        "sold_quantity": ticket.quantity_sold,
                        "available_quantity": ticket.quantity_available,
                        "sold_percentage": round((ticket.quantity_sold / ticket.quantity_total * 100) if ticket.quantity_total > 0 else 0, 2)
                    }
                    for ticket in ticket_sales
                ],
                "attendees": {
                    "total": attendee_row.total_attendees or 0
                },
                "sales_timeline": [
                    {
                        "date": row.date.isoformat(),
                        "revenue": float(row.revenue or 0),
                        "orders": row.orders
                    }
                    for row in daily_sales
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting event performance: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    async def get_top_events(
        db: AsyncSession,
        date_range: DateRange = DateRange.LAST_30_DAYS,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10,
        sort_by: str = "revenue"
    ) -> List[Dict[str, Any]]:
        """Get top performing events"""
        try:
            range_start, range_end = DateRangeCalculator.get_date_range(date_range, start_date, end_date)
            
            if sort_by == "revenue":
                order_column = func.sum(Order.total_amount).desc()
            elif sort_by == "orders":
                order_column = func.count(Order.id).desc()
            else:
                order_column = func.sum(Order.total_amount).desc()
            
            top_events_query = select(
                Event.id,
                Event.title,
                Event.start_date,
                func.sum(Order.total_amount).label("revenue"),
                func.count(Order.id).label("orders"),
                func.count(func.distinct(Order.user_id)).label("customers")
            ).join(Order).where(
                and_(
                    Order.status == "completed",
                    Order.created_at >= range_start,
                    Order.created_at <= range_end
                )
            ).group_by(Event.id, Event.title, Event.start_date).order_by(order_column).limit(limit)
            
            result = await db.execute(top_events_query)
            
            return [
                {
                    "event_id": row.id,
                    "title": row.title,
                    "start_date": row.start_date.isoformat() if row.start_date else None,
                    "revenue": float(row.revenue or 0),
                    "orders": row.orders,
                    "customers": row.customers
                }
                for row in result
            ]
            
        except Exception as e:
            logger.error(f"Error getting top events: {str(e)}")
            return []


class UserAnalyticsService:
    """Service for user analytics"""
    
    @staticmethod
    async def get_user_growth_metrics(
        db: AsyncSession,
        date_range: DateRange = DateRange.LAST_30_DAYS,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get user growth and engagement metrics"""
        try:
            range_start, range_end = DateRangeCalculator.get_date_range(date_range, start_date, end_date)
            
            # New user registrations
            new_users_query = select(
                func.count(User.id).label("new_users")
            ).where(
                and_(
                    User.created_at >= range_start,
                    User.created_at <= range_end
                )
            )
            
            new_users_result = await db.execute(new_users_query)
            new_users = new_users_result.scalar() or 0
            
            # Active users (made purchases)
            active_users_query = select(
                func.count(func.distinct(Order.user_id)).label("active_users")
            ).where(
                and_(
                    Order.created_at >= range_start,
                    Order.created_at <= range_end,
                    Order.status == "completed"
                )
            )
            
            active_users_result = await db.execute(active_users_query)
            active_users = active_users_result.scalar() or 0
            
            # User retention (users who made multiple purchases)
            retention_query = select(
                func.count(Order.user_id).label("user_id")
            ).where(
                and_(
                    Order.created_at >= range_start,
                    Order.created_at <= range_end,
                    Order.status == "completed"
                )
            ).group_by(Order.user_id).having(func.count(Order.id) > 1)
            
            retention_result = await db.execute(retention_query)
            repeat_customers = len(retention_result.all())
            
            # Daily user registrations
            daily_registrations_query = select(
                cast(User.created_at, Date).label("date"),
                func.count(User.id).label("registrations")
            ).where(
                and_(
                    User.created_at >= range_start,
                    User.created_at <= range_end
                )
            ).group_by(cast(User.created_at, Date)).order_by(cast(User.created_at, Date))
            
            daily_registrations_result = await db.execute(daily_registrations_query)
            daily_registrations = daily_registrations_result.all()
            
            return {
                "period": {
                    "start": range_start.isoformat(),
                    "end": range_end.isoformat()
                },
                "metrics": {
                    "new_users": new_users,
                    "active_users": active_users,
                    "repeat_customers": repeat_customers,
                    "retention_rate": round((repeat_customers / active_users * 100) if active_users > 0 else 0, 2)
                },
                "daily_registrations": [
                    {
                        "date": row.date.isoformat(),
                        "registrations": row.registrations
                    }
                    for row in daily_registrations
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting user growth metrics: {str(e)}")
            return {"period": {}, "metrics": {}, "daily_registrations": []}


class OrganizationAnalyticsService:
    """Service for organization analytics"""
    
    @staticmethod
    async def get_organization_performance(
        db: AsyncSession,
        organization_id: int,
        date_range: DateRange = DateRange.LAST_30_DAYS,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get organization performance metrics"""
        try:
            range_start, range_end = DateRangeCalculator.get_date_range(date_range, start_date, end_date)
            
            # Organization details
            org = await db.get(Organization, organization_id)
            if not org:
                return {"error": "Organization not found"}
            
            # Revenue and orders
            revenue_query = select(
                func.sum(Order.total_amount).label("total_revenue"),
                func.count(Order.id).label("total_orders"),
                func.count(func.distinct(Order.user_id)).label("unique_customers")
            ).join(Event).where(
                and_(
                    Event.organization_id == organization_id,
                    Order.status == "completed",
                    Order.created_at >= range_start,
                    Order.created_at <= range_end
                )
            )
            
            revenue_result = await db.execute(revenue_query)
            revenue_row = revenue_result.first()
            
            # Event count and performance
            events_query = select(
                func.count(Event.id).label("total_events"),
                func.count().filter(Event.start_date > datetime.utcnow()).label("upcoming_events"),
                func.count().filter(Event.is_active == True).label("active_events")
            ).where(Event.organization_id == organization_id)
            
            events_result = await db.execute(events_query)
            events_row = events_result.first()
            
            # Top events for this organization
            top_events_query = select(
                Event.title,
                Event.start_date,
                func.sum(Order.total_amount).label("revenue"),
                func.count(Order.id).label("orders")
            ).join(Order).where(
                and_(
                    Event.organization_id == organization_id,
                    Order.status == "completed",
                    Order.created_at >= range_start,
                    Order.created_at <= range_end
                )
            ).group_by(Event.id, Event.title, Event.start_date).order_by(
                func.sum(Order.total_amount).desc()
            ).limit(5)
            
            top_events_result = await db.execute(top_events_query)
            top_events = top_events_result.all()
            
            return {
                "organization": {
                    "id": org.id,
                    "name": org.name
                },
                "period": {
                    "start": range_start.isoformat(),
                    "end": range_end.isoformat()
                },
                "metrics": {
                    "revenue": float(revenue_row.total_revenue or 0),
                    "orders": revenue_row.total_orders or 0,
                    "customers": revenue_row.unique_customers or 0,
                    "total_events": events_row.total_events or 0,
                    "upcoming_events": events_row.upcoming_events or 0,
                    "active_events": events_row.active_events or 0
                },
                "top_events": [
                    {
                        "title": event.title,
                        "start_date": event.start_date.isoformat() if event.start_date else None,
                        "revenue": float(event.revenue or 0),
                        "orders": event.orders
                    }
                    for event in top_events
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting organization performance: {str(e)}")
            return {"error": str(e)}


# Global analytics service instances
revenue_analytics = RevenueAnalyticsService()
event_analytics = EventAnalyticsService()
user_analytics = UserAnalyticsService()
organization_analytics = OrganizationAnalyticsService()
"""
Advanced search and filtering service
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, cast, String, desc, asc
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.dialects.postgresql import TSVECTOR

from app.models.event import Event
from app.models.user import User
from app.models.organization import Organization
from app.models.order import Order
from app.models.ticket import Ticket
from app.core.input_validation import sanitize_search_query

logger = logging.getLogger(__name__)


class SortOrder(str, Enum):
    """Sort order options"""
    ASC = "asc"
    DESC = "desc"


class EventSortField(str, Enum):
    """Event sort field options"""
    CREATED_AT = "created_at"
    START_DATE = "start_date"
    TITLE = "title"
    PRICE = "price"
    POPULARITY = "popularity"
    RELEVANCE = "relevance"


class SearchFilter:
    """Advanced search filter builder"""
    
    def __init__(self):
        self.filters = []
        self.joins = set()
        self.sort_fields = []
        
    def add_text_search(self, query: str, fields: List[str]):
        """Add full-text search filter"""
        if not query:
            return self
            
        sanitized_query = sanitize_search_query(query)
        if not sanitized_query:
            return self
            
        # Create ILIKE conditions for each field
        conditions = []
        for field in fields:
            conditions.append(field.ilike(f"%{sanitized_query}%"))
        
        if conditions:
            self.filters.append(or_(*conditions))
        
        return self
    
    def add_date_range(self, field, start_date: Optional[date], end_date: Optional[date]):
        """Add date range filter"""
        if start_date:
            self.filters.append(field >= start_date)
        if end_date:
            self.filters.append(field <= end_date)
        return self
    
    def add_numeric_range(self, field, min_value: Optional[float], max_value: Optional[float]):
        """Add numeric range filter"""
        if min_value is not None:
            self.filters.append(field >= min_value)
        if max_value is not None:
            self.filters.append(field <= max_value)
        return self
    
    def add_in_filter(self, field, values: List[Any]):
        """Add IN filter for multiple values"""
        if values:
            self.filters.append(field.in_(values))
        return self
    
    def add_boolean_filter(self, field, value: Optional[bool]):
        """Add boolean filter"""
        if value is not None:
            self.filters.append(field == value)
        return self
    
    def add_location_filter(self, location_query: str, radius_km: Optional[float] = None):
        """Add location-based filter"""
        if location_query:
            sanitized_location = sanitize_search_query(location_query)
            if sanitized_location:
                self.filters.append(Event.location.ilike(f"%{sanitized_location}%"))
        # Note: For proper geographic search, you'd integrate PostGIS
        return self
    
    def add_sort(self, field, order: SortOrder = SortOrder.ASC):
        """Add sort field"""
        if order == SortOrder.DESC:
            self.sort_fields.append(desc(field))
        else:
            self.sort_fields.append(asc(field))
        return self
    
    def build_where_clause(self):
        """Build the WHERE clause from filters"""
        if not self.filters:
            return None
        return and_(*self.filters) if len(self.filters) > 1 else self.filters[0]


class EventSearchService:
    """Service for searching and filtering events"""
    
    @staticmethod
    async def search_events(
        db: AsyncSession,
        query: Optional[str] = None,
        category_ids: Optional[List[int]] = None,
        organization_ids: Optional[List[int]] = None,
        location: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_active: Optional[bool] = True,
        has_tickets_available: Optional[bool] = None,
        sort_by: EventSortField = EventSortField.START_DATE,
        sort_order: SortOrder = SortOrder.ASC,
        page: int = 0,
        page_size: int = 20
    ) -> Tuple[List[Event], int]:
        """
        Advanced event search with filtering and sorting
        """
        try:
            # Build search filter
            search_filter = SearchFilter()
            
            # Text search across title and description
            if query:
                search_filter.add_text_search(
                    query, 
                    [Event.title, Event.description, Event.location]
                )
            
            # Category filter
            if category_ids:
                search_filter.add_in_filter(Event.category_id, category_ids)
            
            # Organization filter
            if organization_ids:
                search_filter.add_in_filter(Event.organization_id, organization_ids)
            
            # Location filter
            if location:
                search_filter.add_location_filter(location)
            
            # Date range filter
            search_filter.add_date_range(Event.start_date, start_date, end_date)
            
            # Active status filter
            search_filter.add_boolean_filter(Event.is_active, is_active)
            
            # Base query with eager loading
            base_query = select(Event).options(
                selectinload(Event.organization),
                selectinload(Event.category),
                selectinload(Event.tickets)
            )
            
            # Apply WHERE filters
            where_clause = search_filter.build_where_clause()
            if where_clause is not None:
                base_query = base_query.where(where_clause)
            
            # Handle ticket availability filter
            if has_tickets_available is not None:
                if has_tickets_available:
                    # Events with available tickets
                    base_query = base_query.join(Ticket).where(
                        and_(
                            Ticket.quantity_available > 0,
                            Ticket.sale_start_date <= datetime.utcnow(),
                            or_(
                                Ticket.sale_end_date.is_(None),
                                Ticket.sale_end_date >= datetime.utcnow()
                            )
                        )
                    ).distinct()
            
            # Handle price filtering (requires joining with tickets)
            if min_price is not None or max_price is not None:
                if Ticket not in [j.mapper.class_ for j in base_query.column_descriptions]:
                    base_query = base_query.join(Ticket)
                
                search_filter.add_numeric_range(Ticket.price, min_price, max_price)
                updated_where = search_filter.build_where_clause()
                base_query = base_query.where(updated_where).distinct()
            
            # Apply sorting
            if sort_by == EventSortField.POPULARITY:
                # Sort by number of orders (popularity)
                base_query = base_query.outerjoin(Order).group_by(Event.id).order_by(
                    desc(func.count(Order.id)) if sort_order == SortOrder.DESC 
                    else asc(func.count(Order.id))
                )
            elif sort_by == EventSortField.PRICE:
                # Sort by minimum ticket price
                if Ticket not in [j.mapper.class_ for j in base_query.column_descriptions]:
                    base_query = base_query.join(Ticket)
                base_query = base_query.group_by(Event.id).order_by(
                    desc(func.min(Ticket.price)) if sort_order == SortOrder.DESC 
                    else asc(func.min(Ticket.price))
                )
            else:
                # Sort by event fields
                sort_field_map = {
                    EventSortField.CREATED_AT: Event.created_at,
                    EventSortField.START_DATE: Event.start_date,
                    EventSortField.TITLE: Event.title,
                }
                
                sort_field = sort_field_map.get(sort_by, Event.start_date)
                if sort_order == SortOrder.DESC:
                    base_query = base_query.order_by(desc(sort_field))
                else:
                    base_query = base_query.order_by(asc(sort_field))
            
            # Get total count for pagination
            count_query = select(func.count()).select_from(
                base_query.subquery()
            )
            total = await db.scalar(count_query)
            
            # Apply pagination
            paginated_query = base_query.offset(page * page_size).limit(page_size)
            
            # Execute query
            result = await db.execute(paginated_query)
            events = result.scalars().all()
            
            return events, total or 0
            
        except Exception as e:
            logger.error(f"Error in event search: {str(e)}")
            return [], 0
    
    @staticmethod
    async def get_search_suggestions(
        db: AsyncSession,
        query: str,
        limit: int = 10
    ) -> Dict[str, List[str]]:
        """
        Get search suggestions for autocomplete
        """
        if not query or len(query) < 2:
            return {"events": [], "locations": [], "organizations": []}
        
        sanitized_query = sanitize_search_query(query)
        if not sanitized_query:
            return {"events": [], "locations": [], "organizations": []}
        
        try:
            # Event title suggestions
            event_titles = await db.execute(
                select(Event.title)
                .where(
                    and_(
                        Event.title.ilike(f"%{sanitized_query}%"),
                        Event.is_active == True
                    )
                )
                .distinct()
                .limit(limit)
            )
            
            # Location suggestions
            locations = await db.execute(
                select(Event.location)
                .where(
                    and_(
                        Event.location.ilike(f"%{sanitized_query}%"),
                        Event.location.is_not(None),
                        Event.is_active == True
                    )
                )
                .distinct()
                .limit(limit)
            )
            
            # Organization suggestions
            organizations = await db.execute(
                select(Organization.name)
                .where(Organization.name.ilike(f"%{sanitized_query}%"))
                .distinct()
                .limit(limit)
            )
            
            return {
                "events": [title[0] for title in event_titles],
                "locations": [loc[0] for loc in locations if loc[0]],
                "organizations": [org[0] for org in organizations]
            }
            
        except Exception as e:
            logger.error(f"Error getting search suggestions: {str(e)}")
            return {"events": [], "locations": [], "organizations": []}
    
    @staticmethod
    async def get_popular_searches(
        db: AsyncSession,
        limit: int = 10
    ) -> List[str]:
        """
        Get popular search terms (in production, you'd track actual searches)
        """
        try:
            # For demo, return popular event titles
            popular_events = await db.execute(
                select(Event.title)
                .join(Order)
                .group_by(Event.title)
                .order_by(desc(func.count(Order.id)))
                .limit(limit)
            )
            
            return [title[0] for title in popular_events]
            
        except Exception as e:
            logger.error(f"Error getting popular searches: {str(e)}")
            return []


class UserSearchService:
    """Service for searching users (admin functionality)"""
    
    @staticmethod
    async def search_users(
        db: AsyncSession,
        query: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
        has_orders: Optional[bool] = None,
        registration_start: Optional[date] = None,
        registration_end: Optional[date] = None,
        sort_by: str = "created_at",
        sort_order: SortOrder = SortOrder.DESC,
        page: int = 0,
        page_size: int = 20
    ) -> Tuple[List[User], int]:
        """
        Search users with advanced filtering
        """
        try:
            search_filter = SearchFilter()
            
            # Text search
            if query:
                search_filter.add_text_search(
                    query,
                    [User.full_name, User.email]
                )
            
            # Boolean filters
            search_filter.add_boolean_filter(User.is_active, is_active)
            search_filter.add_boolean_filter(User.is_superuser, is_superuser)
            
            # Date range filter
            search_filter.add_date_range(User.created_at, registration_start, registration_end)
            
            # Base query
            base_query = select(User).options(selectinload(User.orders))
            
            # Apply filters
            where_clause = search_filter.build_where_clause()
            if where_clause is not None:
                base_query = base_query.where(where_clause)
            
            # Has orders filter
            if has_orders is not None:
                if has_orders:
                    base_query = base_query.join(Order).distinct()
                else:
                    base_query = base_query.outerjoin(Order).where(Order.id.is_(None))
            
            # Sorting
            sort_field_map = {
                "created_at": User.created_at,
                "email": User.email,
                "full_name": User.full_name,
            }
            
            sort_field = sort_field_map.get(sort_by, User.created_at)
            if sort_order == SortOrder.DESC:
                base_query = base_query.order_by(desc(sort_field))
            else:
                base_query = base_query.order_by(asc(sort_field))
            
            # Get total count
            count_query = select(func.count()).select_from(base_query.subquery())
            total = await db.scalar(count_query)
            
            # Apply pagination
            paginated_query = base_query.offset(page * page_size).limit(page_size)
            
            # Execute query
            result = await db.execute(paginated_query)
            users = result.scalars().all()
            
            return users, total or 0
            
        except Exception as e:
            logger.error(f"Error in user search: {str(e)}")
            return [], 0


class AnalyticsSearchService:
    """Service for analytics and reporting searches"""
    
    @staticmethod
    async def get_event_analytics(
        db: AsyncSession,
        event_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get event analytics with filtering
        """
        try:
            # Base conditions
            conditions = [Event.is_active == True]
            
            if event_id:
                conditions.append(Event.id == event_id)
            if organization_id:
                conditions.append(Event.organization_id == organization_id)
            if start_date:
                conditions.append(Event.created_at >= start_date)
            if end_date:
                conditions.append(Event.created_at <= end_date)
            
            where_clause = and_(*conditions) if len(conditions) > 1 else conditions[0]
            
            # Event statistics
            event_stats = await db.execute(
                select(
                    func.count(Event.id).label("total_events"),
                    func.count().filter(Event.start_date > datetime.utcnow()).label("upcoming_events"),
                    func.count().filter(Event.start_date <= datetime.utcnow()).label("past_events")
                )
                .where(where_clause)
            )
            
            # Revenue statistics
            revenue_stats = await db.execute(
                select(
                    func.sum(Order.total_amount).label("total_revenue"),
                    func.count(Order.id).label("total_orders"),
                    func.avg(Order.total_amount).label("avg_order_value")
                )
                .join(Event)
                .where(
                    and_(
                        where_clause,
                        Order.status == "completed"
                    )
                )
            )
            
            # Popular events
            popular_events = await db.execute(
                select(
                    Event.title,
                    func.count(Order.id).label("order_count"),
                    func.sum(Order.total_amount).label("revenue")
                )
                .join(Order)
                .where(
                    and_(
                        where_clause,
                        Order.status == "completed"
                    )
                )
                .group_by(Event.id, Event.title)
                .order_by(desc(func.count(Order.id)))
                .limit(10)
            )
            
            event_row = event_stats.first()
            revenue_row = revenue_stats.first()
            popular_events_list = popular_events.all()
            
            return {
                "events": {
                    "total": event_row.total_events if event_row else 0,
                    "upcoming": event_row.upcoming_events if event_row else 0,
                    "past": event_row.past_events if event_row else 0
                },
                "revenue": {
                    "total": float(revenue_row.total_revenue or 0) if revenue_row else 0,
                    "orders": revenue_row.total_orders if revenue_row else 0,
                    "average_order": float(revenue_row.avg_order_value or 0) if revenue_row else 0
                },
                "popular_events": [
                    {
                        "title": event.title,
                        "orders": event.order_count,
                        "revenue": float(event.revenue or 0)
                    }
                    for event in popular_events_list
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting event analytics: {str(e)}")
            return {"events": {}, "revenue": {}, "popular_events": []}


# Global search service instances
event_search = EventSearchService()
user_search = UserSearchService()
analytics_search = AnalyticsSearchService()
"""
Recurring Events Models
Supports complex recurring event patterns and series management
"""

from datetime import datetime, date, timedelta
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, Date, Time
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.db.base_class import Base


class RecurrenceType(PyEnum):
    """Types of recurrence patterns"""
    NONE = "none"
    DAILY = "daily" 
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class RecurrencePattern(Base):
    """
    Defines the recurrence pattern for events
    Supports complex scheduling rules
    """
    __tablename__ = "recurrence_patterns"

    id = Column(Integer, primary_key=True, index=True)
    
    # Pattern definition
    recurrence_type = Column(String, nullable=False)  # RecurrenceType enum
    interval_count = Column(Integer, default=1)  # Every N days/weeks/months
    
    # Weekly recurrence - days of week (0=Monday, 6=Sunday)
    weekdays = Column(JSON, nullable=True)  # [0, 1, 2, 3, 4] for weekdays
    
    # Monthly recurrence options
    month_day = Column(Integer, nullable=True)  # Day of month (1-31)
    month_week = Column(Integer, nullable=True)  # Week of month (1-4, -1=last)
    month_weekday = Column(Integer, nullable=True)  # Day of week (0-6)
    
    # Yearly recurrence
    year_month = Column(Integer, nullable=True)  # Month of year (1-12)
    year_day = Column(Integer, nullable=True)  # Day of month
    
    # End conditions
    end_date = Column(Date, nullable=True)  # End by date
    occurrence_count = Column(Integer, nullable=True)  # End after N occurrences
    
    # Advanced options
    exclude_dates = Column(JSON, nullable=True)  # List of dates to skip
    include_dates = Column(JSON, nullable=True)  # Additional specific dates
    timezone = Column(String, default="UTC")
    
    # Custom rule (for complex patterns)
    custom_rule = Column(Text, nullable=True)  # RRULE format or custom expression
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    event_series = relationship("EventSeries", back_populates="recurrence_pattern")

    def generate_dates(self, start_date: date, end_date: date = None, limit: int = 100) -> List[date]:
        """
        Generate list of dates based on recurrence pattern
        """
        dates = []
        current_date = start_date
        count = 0
        
        # Use end_date from pattern if not provided
        if end_date is None and self.end_date:
            end_date = self.end_date
        
        # Use occurrence_count if no end_date
        max_count = self.occurrence_count or limit
        
        while count < max_count:
            if end_date and current_date > end_date:
                break
                
            # Check if date should be included
            if self._should_include_date(current_date):
                dates.append(current_date)
                count += 1
            
            # Move to next potential date
            current_date = self._next_date(current_date)
            
            # Safety check to prevent infinite loops
            if count > 1000:
                break
                
        return dates
    
    def _should_include_date(self, check_date: date) -> bool:
        """Check if a date matches the recurrence pattern"""
        
        # Check exclude_dates
        if self.exclude_dates and check_date.isoformat() in self.exclude_dates:
            return False
        
        # Check include_dates (overrides pattern)
        if self.include_dates and check_date.isoformat() in self.include_dates:
            return True
        
        if self.recurrence_type == RecurrenceType.DAILY.value:
            return True
        
        elif self.recurrence_type == RecurrenceType.WEEKLY.value:
            if self.weekdays:
                return check_date.weekday() in self.weekdays
            return True
        
        elif self.recurrence_type == RecurrenceType.MONTHLY.value:
            if self.month_day:
                return check_date.day == self.month_day
            elif self.month_week and self.month_weekday is not None:
                return self._matches_monthly_pattern(check_date)
            return True
        
        elif self.recurrence_type == RecurrenceType.YEARLY.value:
            matches = True
            if self.year_month:
                matches = matches and check_date.month == self.year_month
            if self.year_day:
                matches = matches and check_date.day == self.year_day
            return matches
        
        return True
    
    def _matches_monthly_pattern(self, check_date: date) -> bool:
        """Check if date matches monthly week/weekday pattern"""
        if check_date.weekday() != self.month_weekday:
            return False
        
        # Calculate which week of the month this is
        first_day = check_date.replace(day=1)
        week_of_month = ((check_date.day - 1) // 7) + 1
        
        # Handle "last week" case (-1)
        if self.month_week == -1:
            # Check if this is the last occurrence of this weekday in the month
            next_week = check_date + timedelta(days=7)
            return next_week.month != check_date.month
        
        return week_of_month == self.month_week
    
    def _next_date(self, current_date: date) -> date:
        """Calculate the next date to check based on recurrence type"""
        
        if self.recurrence_type == RecurrenceType.DAILY.value:
            return current_date + timedelta(days=self.interval_count)
        
        elif self.recurrence_type == RecurrenceType.WEEKLY.value:
            return current_date + timedelta(weeks=self.interval_count)
        
        elif self.recurrence_type == RecurrenceType.MONTHLY.value:
            # Add months (approximate with 30 days, will be corrected)
            return current_date + timedelta(days=30 * self.interval_count)
        
        elif self.recurrence_type == RecurrenceType.YEARLY.value:
            # Add years (approximate with 365 days, will be corrected)
            return current_date + timedelta(days=365 * self.interval_count)
        
        else:
            return current_date + timedelta(days=1)


class EventSeries(Base):
    """
    Represents a series of recurring events
    Acts as a parent for multiple event instances
    """
    __tablename__ = "event_series"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Series metadata
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Template for all events in series
    template_data = Column(JSONB, nullable=True)  # Common event properties
    
    # Recurrence settings
    recurrence_pattern_id = Column(Integer, ForeignKey("recurrence_patterns.id"), nullable=False)
    
    # Series dates
    series_start_date = Column(Date, nullable=False)
    series_end_date = Column(Date, nullable=True)
    
    # Time settings (applied to all events)
    default_start_time = Column(Time, nullable=True)
    default_end_time = Column(Time, nullable=True)
    default_duration_minutes = Column(Integer, nullable=True)
    
    # Series status
    is_active = Column(Boolean, default=True)
    auto_publish = Column(Boolean, default=False)  # Auto-publish new instances
    
    # Generation settings
    advance_days = Column(Integer, default=30)  # Generate events N days in advance
    max_instances = Column(Integer, default=100)  # Max events to generate
    
    # Ownership and metadata
    owner_id = Column(String, ForeignKey("user.id"), nullable=False)
    organization_id = Column(String, ForeignKey("organization.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    recurrence_pattern = relationship("RecurrencePattern", back_populates="event_series")
    events = relationship("Event", back_populates="event_series", cascade="all, delete-orphan")
    owner = relationship("User", back_populates="event_series")
    organization = relationship("Organization", back_populates="event_series")
    
    @hybrid_property
    def total_events(self):
        """Count of generated events"""
        return len(self.events)
    
    @hybrid_property
    def upcoming_events(self):
        """Count of future events"""
        now = datetime.utcnow().date()
        return len([e for e in self.events if e.start_date >= now])
    
    def generate_events(self, days_ahead: int = None) -> List["Event"]:
        """
        Generate event instances based on recurrence pattern
        """
        from app.models.event import Event
        
        if not self.is_active:
            return []
        
        days_ahead = days_ahead or self.advance_days
        end_date = datetime.utcnow().date() + timedelta(days=days_ahead)
        
        # Get dates from recurrence pattern
        dates = self.recurrence_pattern.generate_dates(
            start_date=self.series_start_date,
            end_date=min(end_date, self.series_end_date) if self.series_end_date else end_date,
            limit=self.max_instances
        )
        
        # Check which events already exist
        existing_dates = {e.start_date for e in self.events}
        new_dates = [d for d in dates if d not in existing_dates]
        
        new_events = []
        for event_date in new_dates:
            event_data = self._prepare_event_data(event_date)
            
            event = Event(**event_data)
            new_events.append(event)
        
        return new_events
    
    def _prepare_event_data(self, event_date: date) -> Dict[str, Any]:
        """Prepare event data for a specific date"""
        
        # Start with template data
        event_data = self.template_data.copy() if self.template_data else {}
        
        # Override with series-specific data
        event_data.update({
            "title": self.title,
            "description": self.description,
            "start_date": event_date,
            "event_series_id": self.id,
            "owner_id": self.owner_id,
            "organization_id": self.organization_id,
            "is_published": self.auto_publish,
            "is_part_of_series": True
        })
        
        # Set times
        if self.default_start_time:
            start_datetime = datetime.combine(event_date, self.default_start_time)
            event_data["start_time"] = start_datetime
        
        if self.default_end_time:
            end_datetime = datetime.combine(event_date, self.default_end_time)
            event_data["end_time"] = end_datetime
        elif self.default_duration_minutes:
            start_datetime = event_data.get("start_time")
            if start_datetime:
                end_datetime = start_datetime + timedelta(minutes=self.default_duration_minutes)
                event_data["end_time"] = end_datetime
        
        return event_data


class EventInstance(Base):
    """
    Individual modifications to recurring event instances
    Allows customization of specific occurrences
    """
    __tablename__ = "event_instances"

    id = Column(Integer, primary_key=True, index=True)
    
    # Reference to the main event
    event_id = Column(String, ForeignKey("event.id"), nullable=False)
    event_series_id = Column(Integer, ForeignKey("event_series.id"), nullable=False)
    
    # Instance-specific modifications
    custom_title = Column(String, nullable=True)
    custom_description = Column(Text, nullable=True)
    custom_location = Column(String, nullable=True)
    
    # Time modifications
    custom_start_time = Column(DateTime, nullable=True)
    custom_end_time = Column(DateTime, nullable=True)
    
    # Status modifications
    is_cancelled = Column(Boolean, default=False)
    cancellation_reason = Column(Text, nullable=True)
    
    # Other modifications
    custom_data = Column(JSONB, nullable=True)  # Any other custom properties
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    event = relationship("Event", back_populates="event_instance")
    event_series = relationship("EventSeries")
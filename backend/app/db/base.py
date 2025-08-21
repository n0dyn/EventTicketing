"""
Import all the models, so that Base has them before being
imported by Alembic
"""

from app.db.base_class import Base  # noqa
from app.models.user import User  # noqa
from app.models.event import Event  # noqa
from app.models.organization import Organization  # noqa
from app.models.event_category import EventCategory  # noqa
from app.models.ticket import TicketType, Ticket  # noqa 
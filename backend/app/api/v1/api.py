from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    events,
    organizations,
    tickets,
    orders,
    payments,
    attendees,
    public_events,
    email,
    files,
    admin,
    search,
    analytics,
    health,
    websocket,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(attendees.router, prefix="/attendees", tags=["attendees"])
api_router.include_router(public_events.router, prefix="/events/public", tags=["public-events"])
api_router.include_router(email.router, prefix="/email", tags=["email"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
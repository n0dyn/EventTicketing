"""
Check-in System Service
Business logic for QR code generation, scanning, and attendee check-in management
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete, desc
from sqlalchemy.orm import selectinload, joinedload
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
import secrets
import logging

from app.models.checkin import (
    TicketQRCode, AttendeeCheckIn, CheckInLocation, 
    ScanSession, CheckInStats,
    CheckInStatus, AccessLevel, ScanResult
)
from app.models.event import Event
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.checkin import (
    TicketQRCodeCreate, CheckInLocationCreate, CheckInLocationUpdate,
    ScanRequest, ScanResponse, ScanSessionStart,
    BulkCheckInOperation, BulkCheckInResult,
    RealTimeCheckInData, CheckInAnalytics
)
from app.core.caching import cached, CacheInvalidator

logger = logging.getLogger(__name__)


class CheckInService:
    """Service for managing QR codes and check-in processes"""

    # QR Code Management
    
    async def generate_ticket_qr_code(
        self, 
        db: AsyncSession, 
        qr_data: TicketQRCodeCreate,
        user_id: str
    ) -> TicketQRCode:
        """Generate QR code for a ticket"""
        
        # Verify ticket ownership
        ticket_query = select(Ticket).join(Event).where(
            and_(
                Ticket.id == qr_data.ticket_id,
                or_(
                    Event.owner_id == user_id,  # Event organizer
                    Ticket.user_id == user_id   # Ticket holder
                )
            )
        )
        result = await db.execute(ticket_query)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            raise ValueError("Ticket not found or access denied")
        
        # Check if QR code already exists
        existing_query = select(TicketQRCode).where(
            TicketQRCode.ticket_id == qr_data.ticket_id
        )
        result = await db.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Regenerate if requested or if current one is invalid
            if not existing.is_valid:
                await db.delete(existing)
                await db.commit()
            else:
                return existing
        
        # Generate secret key for validation
        secret_key = secrets.token_urlsafe(32)
        
        # Create QR code record
        qr_code = TicketQRCode(
            **qr_data.model_dump(),
            secret_key=secret_key,
            generated_by=user_id
        )
        
        # Generate QR data
        qr_code.qr_code_data = qr_code.generate_qr_data()
        qr_code.qr_code_hash = self._hash_qr_data(qr_code.qr_code_data)
        
        db.add(qr_code)
        await db.commit()
        await db.refresh(qr_code)
        
        return qr_code

    async def get_ticket_qr_code(
        self, 
        db: AsyncSession, 
        ticket_id: str,
        user_id: str
    ) -> Optional[TicketQRCode]:
        """Get QR code for a ticket"""
        
        query = select(TicketQRCode).join(Ticket).join(Event).where(
            and_(
                TicketQRCode.ticket_id == ticket_id,
                or_(
                    Event.owner_id == user_id,  # Event organizer
                    Ticket.user_id == user_id   # Ticket holder
                )
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def generate_qr_code_image(
        self, 
        qr_data: str, 
        format: str = "PNG",
        size: int = 10
    ) -> str:
        """Generate QR code image and return as base64 string"""
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=size,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        if format.upper() == "SVG":
            factory = qrcode.image.svg.SvgPathImage
            img = qr.make_image(image_factory=factory)
            buffer = BytesIO()
            img.save(buffer)
            return base64.b64encode(buffer.getvalue()).decode()
        else:
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format=format)
            return base64.b64encode(buffer.getvalue()).decode()

    # Scanning and Check-in
    
    async def scan_qr_code(
        self, 
        db: AsyncSession, 
        scan_request: ScanRequest,
        scanner_user_id: str,
        session_token: Optional[str] = None
    ) -> ScanResponse:
        """Process QR code scan and perform check-in"""
        
        try:
            # Validate scan session if provided
            scan_session = None
            if session_token:
                scan_session = await self._get_active_scan_session(db, session_token, scanner_user_id)
                if scan_session:
                    scan_session.scans_performed += 1
                    scan_session.update_activity()
            
            # Find QR code
            qr_code = await self._find_qr_code_by_data(db, scan_request.qr_code_data)
            if not qr_code:
                await self._update_scan_stats(db, scan_session, False)
                return ScanResponse(
                    success=False,
                    result=ScanResult.INVALID_CODE,
                    message="Invalid QR code"
                )
            
            # Validate QR code data
            if not qr_code.validate_qr_data(scan_request.qr_code_data):
                await self._update_scan_stats(db, scan_session, False)
                return ScanResponse(
                    success=False,
                    result=ScanResult.INVALID_CODE,
                    message="QR code validation failed"
                )
            
            # Check if QR code is valid
            if not qr_code.is_valid:
                result_type = ScanResult.EXPIRED_TICKET if qr_code.valid_until and datetime.utcnow() > qr_code.valid_until else ScanResult.INVALID_CODE
                await self._update_scan_stats(db, scan_session, False)
                return ScanResponse(
                    success=False,
                    result=result_type,
                    message="QR code is not valid"
                )
            
            # Check for existing check-in
            existing_checkin = await self._get_existing_checkin(db, qr_code.id)
            if existing_checkin and not scan_request.force_check_in:
                await self._update_scan_stats(db, scan_session, False)
                return ScanResponse(
                    success=False,
                    result=ScanResult.ALREADY_USED,
                    message="Ticket already used for check-in",
                    check_in_id=existing_checkin.id,
                    attendee_info=self._format_attendee_info(existing_checkin)
                )
            
            # Validate event timing
            event_validation = await self._validate_event_timing(db, qr_code.event_id)
            if not event_validation["valid"] and not scan_request.force_check_in:
                await self._update_scan_stats(db, scan_session, False)
                return ScanResponse(
                    success=False,
                    result=ScanResult(event_validation["result"]),
                    message=event_validation["message"]
                )
            
            # Validate location access if specified
            location_validation = await self._validate_location_access(
                db, qr_code, scan_request.check_in_location
            )
            if not location_validation["valid"]:
                await self._update_scan_stats(db, scan_session, False)
                return ScanResponse(
                    success=False,
                    result=ScanResult.INSUFFICIENT_ACCESS,
                    message=location_validation["message"]
                )
            
            # Perform check-in
            check_in = await self._create_check_in_record(
                db, qr_code, scan_request, scanner_user_id, scan_session
            )
            
            # Update QR code usage
            qr_code.current_usage += 1
            
            # Update location occupancy if specified
            if scan_request.check_in_location:
                await self._update_location_occupancy(db, qr_code.event_id, scan_request.check_in_location, 1)
            
            # Update event statistics
            await self._update_event_check_in_stats(db, qr_code.event_id)
            
            await db.commit()
            await self._update_scan_stats(db, scan_session, True)
            
            # Get attendee and event info
            attendee_info = await self._get_attendee_info(db, check_in.user_id)
            event_info = await self._get_event_info(db, qr_code.event_id)
            
            return ScanResponse(
                success=True,
                result=ScanResult.SUCCESS,
                message="Check-in successful",
                check_in_id=check_in.id,
                attendee_info=attendee_info,
                event_info=event_info,
                warnings=event_validation.get("warnings", [])
            )
            
        except Exception as e:
            logger.error(f"Error during QR code scan: {e}")
            await self._update_scan_stats(db, scan_session, False)
            return ScanResponse(
                success=False,
                result=ScanResult.SYSTEM_ERROR,
                message="System error during check-in"
            )

    async def bulk_check_in(
        self, 
        db: AsyncSession, 
        bulk_request: BulkCheckInOperation,
        scanner_user_id: str,
        session_token: Optional[str] = None
    ) -> BulkCheckInResult:
        """Process multiple QR code scans in bulk"""
        
        start_time = datetime.utcnow()
        results = []
        summary = {}
        
        for qr_code_data in bulk_request.qr_codes:
            scan_request = ScanRequest(
                qr_code_data=qr_code_data,
                scanner_device_id=bulk_request.scanner_device_id,
                check_in_location=bulk_request.check_in_location,
                force_check_in=bulk_request.force_check_in
            )
            
            result = await self.scan_qr_code(db, scan_request, scanner_user_id, session_token)
            results.append(result)
            
            # Update summary
            result_type = result.result.value
            summary[result_type] = summary.get(result_type, 0) + 1
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return BulkCheckInResult(
            total_processed=len(bulk_request.qr_codes),
            successful=summary.get(ScanResult.SUCCESS.value, 0),
            failed=len(bulk_request.qr_codes) - summary.get(ScanResult.SUCCESS.value, 0),
            results=results,
            summary=summary,
            processing_time_seconds=processing_time
        )

    # Check-out
    
    async def check_out_attendee(
        self, 
        db: AsyncSession, 
        check_in_id: int,
        scanner_user_id: str,
        location: Optional[str] = None
    ) -> bool:
        """Check out an attendee"""
        
        # Get check-in record
        query = select(AttendeeCheckIn).where(
            and_(
                AttendeeCheckIn.id == check_in_id,
                AttendeeCheckIn.status == CheckInStatus.CHECKED_IN.value,
                AttendeeCheckIn.check_out_time.is_(None)
            )
        )
        result = await db.execute(query)
        check_in = result.scalar_one_or_none()
        
        if not check_in:
            return False
        
        # Update check-in record
        check_in.status = CheckInStatus.CHECKED_OUT.value
        check_in.check_out_time = datetime.utcnow()
        
        # Update location occupancy
        if check_in.check_in_location:
            await self._update_location_occupancy(db, check_in.event_id, check_in.check_in_location, -1)
        
        # Update event statistics
        await self._update_event_check_in_stats(db, check_in.event_id)
        
        await db.commit()
        return True

    # Location Management
    
    async def create_check_in_location(
        self, 
        db: AsyncSession, 
        location_data: CheckInLocationCreate,
        user_id: str
    ) -> CheckInLocation:
        """Create a check-in location for an event"""
        
        # Verify event ownership
        event_query = select(Event).where(
            and_(Event.id == location_data.event_id, Event.owner_id == user_id)
        )
        result = await db.execute(event_query)
        event = result.scalar_one_or_none()
        
        if not event:
            raise ValueError("Event not found or access denied")
        
        location = CheckInLocation(**location_data.model_dump())
        db.add(location)
        await db.commit()
        await db.refresh(location)
        
        return location

    async def update_check_in_location(
        self, 
        db: AsyncSession, 
        location_id: int,
        location_data: CheckInLocationUpdate,
        user_id: str
    ) -> Optional[CheckInLocation]:
        """Update a check-in location"""
        
        # Get location and verify ownership
        query = select(CheckInLocation).join(Event).where(
            and_(
                CheckInLocation.id == location_id,
                Event.owner_id == user_id
            )
        )
        result = await db.execute(query)
        location = result.scalar_one_or_none()
        
        if not location:
            return None
        
        # Update location
        update_data = location_data.model_dump(exclude_unset=True)
        await db.execute(
            update(CheckInLocation)
            .where(CheckInLocation.id == location_id)
            .values(**update_data)
        )
        await db.commit()
        
        return await self.get_check_in_location(db, location_id, user_id)

    async def get_check_in_location(
        self, 
        db: AsyncSession, 
        location_id: int,
        user_id: str
    ) -> Optional[CheckInLocation]:
        """Get a check-in location"""
        
        query = select(CheckInLocation).join(Event).where(
            and_(
                CheckInLocation.id == location_id,
                Event.owner_id == user_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_event_locations(
        self, 
        db: AsyncSession, 
        event_id: str,
        user_id: str
    ) -> List[CheckInLocation]:
        """Get all check-in locations for an event"""
        
        # Verify event access
        event_query = select(Event).where(
            and_(Event.id == event_id, Event.owner_id == user_id)
        )
        result = await db.execute(event_query)
        event = result.scalar_one_or_none()
        
        if not event:
            return []
        
        query = select(CheckInLocation).where(
            CheckInLocation.event_id == event_id
        ).order_by(CheckInLocation.name)
        
        result = await db.execute(query)
        return result.scalars().all()

    # Scan Session Management
    
    async def start_scan_session(
        self, 
        db: AsyncSession, 
        session_data: ScanSessionStart,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ScanSession:
        """Start a new scan session"""
        
        # Verify event access
        event_query = select(Event).where(
            and_(Event.id == session_data.event_id, Event.owner_id == user_id)
        )
        result = await db.execute(event_query)
        event = result.scalar_one_or_none()
        
        if not event:
            raise ValueError("Event not found or access denied")
        
        # End any existing active sessions for this user/device
        await db.execute(
            update(ScanSession)
            .where(
                and_(
                    ScanSession.user_id == user_id,
                    ScanSession.device_id == session_data.device_id,
                    ScanSession.is_active == True
                )
            )
            .values(is_active=False, ended_at=datetime.utcnow())
        )
        
        # Create new session
        session = ScanSession(
            session_token=ScanSession.generate_session_token(),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            **session_data.model_dump()
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        return session

    async def end_scan_session(
        self, 
        db: AsyncSession, 
        session_token: str,
        user_id: str
    ) -> bool:
        """End a scan session"""
        
        session = await self._get_active_scan_session(db, session_token, user_id)
        if not session:
            return False
        
        session.is_active = False
        session.ended_at = datetime.utcnow()
        
        await db.commit()
        return True

    # Statistics and Analytics
    
    @cached(ttl=60, key_prefix="real_time_checkin")
    async def get_real_time_check_in_data(
        self, 
        db: AsyncSession, 
        event_id: str,
        user_id: str
    ) -> RealTimeCheckInData:
        """Get real-time check-in data for an event"""
        
        # Verify event access
        event_query = select(Event).where(
            and_(Event.id == event_id, Event.owner_id == user_id)
        )
        result = await db.execute(event_query)
        event = result.scalar_one_or_none()
        
        if not event:
            raise ValueError("Event not found or access denied")
        
        # Get current statistics
        stats = await self._get_event_check_in_stats(db, event_id)
        
        # Get recent check-ins (last 15 minutes)
        recent_cutoff = datetime.utcnow() - timedelta(minutes=15)
        recent_checkins_query = select(func.count(AttendeeCheckIn.id)).where(
            and_(
                AttendeeCheckIn.event_id == event_id,
                AttendeeCheckIn.check_in_time >= recent_cutoff,
                AttendeeCheckIn.status == CheckInStatus.CHECKED_IN.value
            )
        )
        result = await db.execute(recent_checkins_query)
        recent_count = result.scalar() or 0
        
        # Get hourly check-ins
        hour_cutoff = datetime.utcnow() - timedelta(hours=1)
        hourly_checkins_query = select(func.count(AttendeeCheckIn.id)).where(
            and_(
                AttendeeCheckIn.event_id == event_id,
                AttendeeCheckIn.check_in_time >= hour_cutoff,
                AttendeeCheckIn.status == CheckInStatus.CHECKED_IN.value
            )
        )
        result = await db.execute(hourly_checkins_query)
        hourly_count = result.scalar() or 0
        
        return RealTimeCheckInData(
            event_id=event_id,
            current_attendees=stats.currently_at_event,
            total_capacity=stats.total_tickets,
            check_ins_last_hour=hourly_count,
            check_ins_last_15_min=recent_count,
            peak_time_today=stats.busiest_hour,
            busiest_location=stats.busiest_entrance
        )

    async def get_check_in_analytics(
        self, 
        db: AsyncSession, 
        event_id: str,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> CheckInAnalytics:
        """Get comprehensive check-in analytics"""
        
        # Verify event access
        event_query = select(Event).where(
            and_(Event.id == event_id, Event.owner_id == user_id)
        )
        result = await db.execute(event_query)
        event = result.scalar_one_or_none()
        
        if not event:
            raise ValueError("Event not found or access denied")
        
        # Set default date range if not provided
        if not start_date:
            start_date = event.start_time - timedelta(days=1)
        if not end_date:
            end_date = event.end_time + timedelta(days=1)
        
        # Get scan statistics
        scan_stats_query = select(
            func.count(AttendeeCheckIn.id).label("total_scans"),
            func.count(AttendeeCheckIn.id).filter(
                AttendeeCheckIn.scan_result == ScanResult.SUCCESS.value
            ).label("successful_scans"),
            func.count(AttendeeCheckIn.id).filter(
                AttendeeCheckIn.scan_result != ScanResult.SUCCESS.value
            ).label("failed_scans")
        ).where(
            and_(
                AttendeeCheckIn.event_id == event_id,
                AttendeeCheckIn.check_in_time.between(start_date, end_date)
            )
        )
        
        result = await db.execute(scan_stats_query)
        scan_stats = result.first()
        
        total_scans = scan_stats.total_scans or 0
        successful_scans = scan_stats.successful_scans or 0
        failed_scans = scan_stats.failed_scans or 0
        success_rate = (successful_scans / total_scans * 100) if total_scans > 0 else 0
        
        return CheckInAnalytics(
            event_id=event_id,
            date_range={"start": start_date, "end": end_date},
            total_scans=total_scans,
            successful_scans=successful_scans,
            failed_scans=failed_scans,
            success_rate=success_rate,
            unique_attendees=successful_scans,  # Simplified
            repeat_scan_rate=0.0,  # Would need more complex calculation
            average_dwell_time_minutes=120.0,  # Placeholder
            peak_periods=[],  # Would need hourly breakdown
            location_performance=[],  # Would need location analysis
            scan_patterns={},  # Would need pattern analysis
            recommendations=self._generate_analytics_recommendations(success_rate, total_scans)
        )

    # Helper Methods
    
    def _hash_qr_data(self, qr_data: str) -> str:
        """Generate hash for QR code data"""
        import hashlib
        return hashlib.sha256(qr_data.encode()).hexdigest()

    async def _find_qr_code_by_data(
        self, 
        db: AsyncSession, 
        qr_data: str
    ) -> Optional[TicketQRCode]:
        """Find QR code by data"""
        qr_hash = self._hash_qr_data(qr_data)
        
        query = select(TicketQRCode).where(TicketQRCode.qr_code_hash == qr_hash)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _get_active_scan_session(
        self, 
        db: AsyncSession, 
        session_token: str,
        user_id: str
    ) -> Optional[ScanSession]:
        """Get active scan session"""
        query = select(ScanSession).where(
            and_(
                ScanSession.session_token == session_token,
                ScanSession.user_id == user_id,
                ScanSession.is_active == True
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _get_existing_checkin(
        self, 
        db: AsyncSession, 
        qr_code_id: int
    ) -> Optional[AttendeeCheckIn]:
        """Check for existing check-in"""
        query = select(AttendeeCheckIn).where(
            and_(
                AttendeeCheckIn.qr_code_id == qr_code_id,
                AttendeeCheckIn.status == CheckInStatus.CHECKED_IN.value
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _validate_event_timing(
        self, 
        db: AsyncSession, 
        event_id: str
    ) -> Dict[str, Any]:
        """Validate if event is currently accepting check-ins"""
        
        query = select(Event).where(Event.id == event_id)
        result = await db.execute(query)
        event = result.scalar_one_or_none()
        
        if not event:
            return {"valid": False, "result": "wrong_event", "message": "Event not found"}
        
        now = datetime.utcnow()
        
        # Allow check-in 2 hours before event starts
        check_in_start = event.start_time - timedelta(hours=2)
        
        if now < check_in_start:
            return {
                "valid": False, 
                "result": "event_not_started", 
                "message": f"Check-in opens at {check_in_start.strftime('%H:%M')}"
            }
        
        # Allow check-in up to 1 hour after event ends
        check_in_end = event.end_time + timedelta(hours=1)
        
        if now > check_in_end:
            return {
                "valid": False,
                "result": "event_ended",
                "message": "Check-in period has ended"
            }
        
        warnings = []
        if now > event.end_time:
            warnings.append("Event has officially ended")
        elif now < event.start_time:
            warnings.append("Event has not started yet")
        
        return {"valid": True, "warnings": warnings}

    async def _validate_location_access(
        self, 
        db: AsyncSession, 
        qr_code: TicketQRCode,
        location_name: Optional[str]
    ) -> Dict[str, Any]:
        """Validate access to check-in location"""
        
        if not location_name:
            return {"valid": True}
        
        # Get location
        query = select(CheckInLocation).where(
            and_(
                CheckInLocation.event_id == qr_code.event_id,
                CheckInLocation.name == location_name
            )
        )
        result = await db.execute(query)
        location = result.scalar_one_or_none()
        
        if not location:
            return {"valid": True}  # Allow if location not found
        
        if not location.is_open:
            return {"valid": False, "message": f"Location '{location_name}' is currently closed"}
        
        if location.is_at_capacity:
            return {"valid": False, "message": f"Location '{location_name}' is at capacity"}
        
        # Check access level
        qr_access_level = AccessLevel(qr_code.access_level)
        required_level = AccessLevel(location.required_access_level)
        
        access_hierarchy = {
            AccessLevel.GENERAL: 0,
            AccessLevel.VIP: 1,
            AccessLevel.BACKSTAGE: 2,
            AccessLevel.STAFF: 3,
            AccessLevel.PRESS: 3
        }
        
        if access_hierarchy[qr_access_level] < access_hierarchy[required_level]:
            return {"valid": False, "message": f"Insufficient access level for '{location_name}'"}
        
        return {"valid": True}

    async def _create_check_in_record(
        self, 
        db: AsyncSession, 
        qr_code: TicketQRCode,
        scan_request: ScanRequest,
        scanner_user_id: str,
        scan_session: Optional[ScanSession]
    ) -> AttendeeCheckIn:
        """Create check-in record"""
        
        check_in = AttendeeCheckIn(
            qr_code_id=qr_code.id,
            ticket_id=qr_code.ticket_id,
            event_id=qr_code.event_id,
            user_id=qr_code.ticket.user_id,  # Get from ticket
            status=CheckInStatus.CHECKED_IN.value,
            check_in_location=scan_request.check_in_location,
            scanner_device_id=scan_request.scanner_device_id,
            scanner_user_id=scanner_user_id,
            latitude=scan_request.latitude,
            longitude=scan_request.longitude,
            accuracy=scan_request.accuracy,
            scan_result=ScanResult.SUCCESS.value
        )
        
        db.add(check_in)
        return check_in

    async def _update_scan_stats(
        self, 
        db: AsyncSession, 
        scan_session: Optional[ScanSession],
        success: bool
    ):
        """Update scan session statistics"""
        if scan_session:
            if success:
                scan_session.successful_scans += 1
            else:
                scan_session.failed_scans += 1
            await db.commit()

    async def _update_location_occupancy(
        self, 
        db: AsyncSession, 
        event_id: str,
        location_name: str,
        delta: int
    ):
        """Update location occupancy count"""
        await db.execute(
            update(CheckInLocation)
            .where(
                and_(
                    CheckInLocation.event_id == event_id,
                    CheckInLocation.name == location_name
                )
            )
            .values(current_occupancy=CheckInLocation.current_occupancy + delta)
        )

    async def _update_event_check_in_stats(
        self, 
        db: AsyncSession, 
        event_id: str
    ):
        """Update event check-in statistics"""
        # This would update the CheckInStats table
        # Implementation depends on specific requirements
        pass

    async def _get_event_check_in_stats(
        self, 
        db: AsyncSession, 
        event_id: str
    ) -> CheckInStats:
        """Get event check-in statistics"""
        from app.models.checkin import CheckInStats
        
        query = select(CheckInStats).where(CheckInStats.event_id == event_id)
        result = await db.execute(query)
        stats = result.scalar_one_or_none()
        
        if not stats:
            # Create default stats
            stats = CheckInStats(event_id=event_id)
            db.add(stats)
            await db.commit()
        
        return stats

    def _format_attendee_info(self, check_in: AttendeeCheckIn) -> Dict[str, Any]:
        """Format attendee information for response"""
        return {
            "check_in_id": check_in.id,
            "check_in_time": check_in.check_in_time.isoformat(),
            "location": check_in.check_in_location,
            "status": check_in.status
        }

    async def _get_attendee_info(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> Dict[str, Any]:
        """Get attendee information"""
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return {}
        
        return {
            "user_id": user.id,
            "name": user.full_name,
            "email": user.email
        }

    async def _get_event_info(
        self, 
        db: AsyncSession, 
        event_id: str
    ) -> Dict[str, Any]:
        """Get event information"""
        query = select(Event).where(Event.id == event_id)
        result = await db.execute(query)
        event = result.scalar_one_or_none()
        
        if not event:
            return {}
        
        return {
            "event_id": event.id,
            "title": event.title,
            "start_time": event.start_time.isoformat(),
            "location": event.location
        }

    def _generate_analytics_recommendations(
        self, 
        success_rate: float, 
        total_scans: int
    ) -> List[str]:
        """Generate recommendations based on analytics"""
        recommendations = []
        
        if success_rate < 80:
            recommendations.append("Low scan success rate detected. Consider staff training.")
        
        if total_scans < 10:
            recommendations.append("Low scan volume. Verify QR code distribution.")
        
        return recommendations


# Global service instance
checkin_service = CheckInService()
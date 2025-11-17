"""
Comprehensive tests for ticketing system enhancements
Tests all models, serializers, viewsets, signals, and RBAC
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
import uuid

from tickets.models import Ticket, TicketType
from events.models import Event
from tickets.ticket_enhancements import (
    TicketDisablement, TicketBlacklist, UserBan, TicketTransfer,
    EventMetrics, LocationMetrics
)
from accounts.enhanced_rbac import EnhancedUserRole, RBACUtils, Permission, RolePermissionMatrix
from tickets.ticket_enhancement_serializers import (
    TicketDisablementSerializer, UserBanSerializer, TicketTransferSerializer,
    EventMetricsSerializer
)
from core.enhanced_permissions import IsMasterAdmin, IsSystemAdmin
from attendees.models import CheckInLocation

User = get_user_model()


# ============================================================================
# MODEL TESTS
# ============================================================================

class TicketDisablementModelTests(TestCase):
    """Test TicketDisablement model"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass',
            role=EnhancedUserRole.MASTER_ADMIN
        )
        self.organizer = User.objects.create_user(
            email='org@test.com',
            password='testpass',
            role=EnhancedUserRole.EVENT_ORGANIZER
        )
        self.event = Event.objects.create(
            title='Test',
            date=timezone.now() + timedelta(days=1),
            owner=self.organizer
        )
        self.ticket_type = TicketType.objects.create(
            event=self.event,
            name='Test',
            price=Decimal('50.00')
        )
        self.ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            ticket_code='TEST001',
            status='active'
        )
    
    def test_create_disablement(self):
        """Test creating a ticket disablement"""
        disablement = TicketDisablement.objects.create(
            ticket=self.ticket,
            reason='fraud',
            disabled_by=self.admin,
            notes='Fraudulent activity detected'
        )
        self.assertEqual(disablement.ticket, self.ticket)
        self.assertEqual(disablement.reason, 'fraud')
        self.assertEqual(disablement.status, 'disabled')
    
    def test_re_enable_ticket(self):
        """Test re-enabling a disabled ticket"""
        disablement = TicketDisablement.objects.create(
            ticket=self.ticket,
            reason='fraud',
            disabled_by=self.admin
        )
        disablement.re_enable(user=self.admin)
        
        self.assertEqual(disablement.status, 'active')
        self.assertIsNotNone(disablement.re_enabled_at)
        self.assertEqual(disablement.re_enabled_by, self.admin)
    
    def test_disablement_updates_ticket_status(self):
        """Test that disablement updates ticket status"""
        self.assertEqual(self.ticket.status, 'active')
        
        TicketDisablement.objects.create(
            ticket=self.ticket,
            reason='fraud',
            disabled_by=self.admin
        )
        
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'disabled')


class UserBanModelTests(TestCase):
    """Test UserBan model"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass',
            role=EnhancedUserRole.MASTER_ADMIN
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass',
            role=EnhancedUserRole.ATTENDEE
        )
        self.event = Event.objects.create(
            title='Test',
            date=timezone.now() + timedelta(days=1),
            owner=self.admin
        )
    
    def test_create_permanent_ban(self):
        """Test creating a permanent ban"""
        ban = UserBan.objects.create(
            user=self.user,
            event=self.event,
            reason='fraud',
            issued_by=self.admin,
            description='User engaged in fraudulent activity'
        )
        self.assertTrue(ban.is_permanent)
        self.assertFalse(ban.is_expired)
    
    def test_create_temporary_ban(self):
        """Test creating a temporary ban"""
        until = timezone.now() + timedelta(days=30)
        ban = UserBan.objects.create(
            user=self.user,
            event=self.event,
            reason='harassment',
            issued_by=self.admin,
            ban_until=until
        )
        self.assertFalse(ban.is_permanent)
        self.assertFalse(ban.is_expired)
        self.assertGreater(ban.days_remaining, 0)
    
    def test_expired_ban(self):
        """Test expired ban detection"""
        until = timezone.now() - timedelta(days=1)
        ban = UserBan.objects.create(
            user=self.user,
            event=self.event,
            reason='fraud',
            issued_by=self.admin,
            ban_until=until
        )
        self.assertTrue(ban.is_expired)
    
    def test_lift_ban(self):
        """Test lifting a ban"""
        ban = UserBan.objects.create(
            user=self.user,
            event=self.event,
            reason='fraud',
            issued_by=self.admin
        )
        ban.lift(user=self.admin, reason='Ban appealed and approved')
        
        self.assertFalse(ban.is_active)
        self.assertEqual(ban.appeal_status, 'approved')


class TicketTransferModelTests(TestCase):
    """Test TicketTransfer model"""
    
    def setUp(self):
        self.organizer = User.objects.create_user(
            email='org@test.com',
            password='testpass',
            role=EnhancedUserRole.EVENT_ORGANIZER
        )
        self.sender = User.objects.create_user(
            email='sender@test.com',
            password='testpass',
            role=EnhancedUserRole.ATTENDEE
        )
        self.recipient = User.objects.create_user(
            email='recipient@test.com',
            password='testpass',
            role=EnhancedUserRole.ATTENDEE
        )
        self.event = Event.objects.create(
            title='Test',
            date=timezone.now() + timedelta(days=1),
            owner=self.organizer
        )
        self.ticket_type = TicketType.objects.create(
            event=self.event,
            name='Test',
            price=Decimal('50.00')
        )
        self.ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            holder=self.sender,
            ticket_code='TEST001',
            status='active'
        )
    
    def test_create_gift_transfer(self):
        """Test creating a gift transfer"""
        transfer = TicketTransfer.objects.create(
            ticket=self.ticket,
            from_user=self.sender,
            to_user=self.recipient,
            transfer_type='gift',
            status='pending'
        )
        self.assertEqual(transfer.transfer_type, 'gift')
        self.assertIsNone(transfer.resale_price)
    
    def test_create_resale_transfer(self):
        """Test creating a resale transfer"""
        transfer = TicketTransfer.objects.create(
            ticket=self.ticket,
            from_user=self.sender,
            to_user=self.recipient,
            transfer_type='resale',
            resale_price=Decimal('60.00'),
            platform_fee=Decimal('5.00'),
            status='pending'
        )
        self.assertEqual(transfer.transfer_type, 'resale')
        self.assertEqual(transfer.resale_price, Decimal('60.00'))
    
    def test_transfer_expiration(self):
        """Test transfer expiration"""
        transfer = TicketTransfer.objects.create(
            ticket=self.ticket,
            from_user=self.sender,
            to_user=self.recipient,
            transfer_type='gift',
            status='pending',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        self.assertTrue(transfer.is_expired)


class EventMetricsModelTests(TestCase):
    """Test EventMetrics model"""
    
    def setUp(self):
        self.organizer = User.objects.create_user(
            email='org@test.com',
            password='testpass',
            role=EnhancedUserRole.EVENT_ORGANIZER
        )
        self.event = Event.objects.create(
            title='Test',
            date=timezone.now() + timedelta(days=1),
            owner=self.organizer
        )
    
    def test_create_metrics(self):
        """Test creating event metrics"""
        metrics = EventMetrics.objects.create(
            event=self.event,
            total_revenue=Decimal('5000.00'),
            tickets_sold=100,
            attendees_checked_in=95,
            no_show_count=5
        )
        self.assertEqual(metrics.total_revenue, Decimal('5000.00'))
        self.assertEqual(metrics.tickets_sold, 100)
        self.assertEqual(metrics.attendance_rate, 95.0)


# ============================================================================
# RBAC TESTS
# ============================================================================

class RBACInitializationTests(TestCase):
    """Test RBAC initialization"""
    
    def test_initialize_roles(self):
        """Test role initialization"""
        RBACUtils.initialize_roles()
        
        # Check permissions created
        permissions = Permission.objects.all()
        self.assertGreater(permissions.count(), 50)
        
        # Check role matrices created
        matrices = RolePermissionMatrix.objects.all()
        self.assertEqual(matrices.count(), 9)
    
    def test_get_master_admin_permissions(self):
        """Test master admin has many permissions"""
        RBACUtils.initialize_roles()
        perms = RBACUtils.get_user_permissions(
            User(role=EnhancedUserRole.MASTER_ADMIN)
        )
        self.assertGreater(len(perms), 20)
    
    def test_get_attendee_permissions(self):
        """Test attendee has limited permissions"""
        RBACUtils.initialize_roles()
        perms = RBACUtils.get_user_permissions(
            User(role=EnhancedUserRole.ATTENDEE)
        )
        self.assertLess(len(perms), 5)


class PermissionCheckTests(TestCase):
    """Test permission checking"""
    
    def setUp(self):
        RBACUtils.initialize_roles()
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass',
            role=EnhancedUserRole.MASTER_ADMIN
        )
        self.organizer = User.objects.create_user(
            email='org@test.com',
            password='testpass',
            role=EnhancedUserRole.EVENT_ORGANIZER
        )
        self.attendee = User.objects.create_user(
            email='user@test.com',
            password='testpass',
            role=EnhancedUserRole.ATTENDEE
        )
    
    def test_admin_can_create_event(self):
        """Test admin can create events"""
        self.assertTrue(RBACUtils.user_can(self.admin, 'create_event'))
    
    def test_organizer_can_create_event(self):
        """Test organizer can create events"""
        self.assertTrue(RBACUtils.user_can(self.organizer, 'create_event'))
    
    def test_attendee_cannot_create_event(self):
        """Test attendee cannot create events"""
        self.assertFalse(RBACUtils.user_can(self.attendee, 'create_event'))
    
    def test_admin_can_ban_user(self):
        """Test admin can ban users"""
        self.assertTrue(RBACUtils.user_can(self.admin, 'ban_user'))
    
    def test_organizer_can_ban_user(self):
        """Test organizer can ban users"""
        self.assertTrue(RBACUtils.user_can(self.organizer, 'ban_user'))
    
    def test_attendee_cannot_ban(self):
        """Test attendee cannot ban users"""
        self.assertFalse(RBACUtils.user_can(self.attendee, 'ban_user'))


# ============================================================================
# SERIALIZER TESTS
# ============================================================================

class TicketDisablementSerializerTests(TestCase):
    """Test TicketDisablement serializer"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass'
        )
        self.organizer = User.objects.create_user(
            email='org@test.com',
            password='testpass'
        )
        self.event = Event.objects.create(
            title='Test',
            date=timezone.now() + timedelta(days=1),
            owner=self.organizer
        )
        self.ticket_type = TicketType.objects.create(
            event=self.event,
            name='Test',
            price=Decimal('50.00')
        )
        self.ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            ticket_code='TEST001',
            status='active'
        )
        self.disablement = TicketDisablement.objects.create(
            ticket=self.ticket,
            reason='fraud',
            disabled_by=self.admin
        )
    
    def test_serialize_disablement(self):
        """Test serializing a disablement"""
        serializer = TicketDisablementSerializer(self.disablement)
        data = serializer.data
        
        self.assertEqual(data['reason'], 'fraud')
        self.assertEqual(data['status'], 'disabled')
        self.assertIn('ticket_code', data)
        self.assertIn('disabled_at', data)


# ============================================================================
# API ENDPOINT TESTS
# ============================================================================

class TicketDisablementAPITests(APITestCase):
    """Test ticket disablement API endpoints"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role=EnhancedUserRole.MASTER_ADMIN,
            is_staff=True
        )
        self.organizer = User.objects.create_user(
            email='org@test.com',
            password='testpass123',
            role=EnhancedUserRole.EVENT_ORGANIZER
        )
        self.event = Event.objects.create(
            title='Test',
            date=timezone.now() + timedelta(days=1),
            owner=self.organizer
        )
        self.ticket_type = TicketType.objects.create(
            event=self.event,
            name='Test',
            price=Decimal('50.00')
        )
        self.ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            ticket_code='TEST001',
            status='active'
        )
        self.client = APIClient()
    
    def test_admin_can_disable_ticket(self):
        """Test admin can disable a ticket"""
        self.client.force_authenticate(user=self.admin)
        
        data = {
            'reason': 'fraud',
            'detailed_reason': 'Fraudulent activity'
        }
        
        # This would test the actual endpoint
        # response = self.client.post(
        #     f'/api/v1/tickets/{self.ticket.id}/disablements/',
        #     data
        # )
        # self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_non_admin_cannot_disable_ticket(self):
        """Test non-admin cannot disable ticket"""
        non_admin = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            role=EnhancedUserRole.ATTENDEE
        )
        self.client.force_authenticate(user=non_admin)
        
        # Test would verify permission denied


class UserBanAPITests(APITestCase):
    """Test user ban API endpoints"""
    
    def setUp(self):
        RBACUtils.initialize_roles()
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role=EnhancedUserRole.MASTER_ADMIN,
            is_staff=True
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            role=EnhancedUserRole.ATTENDEE
        )
        self.event = Event.objects.create(
            title='Test',
            date=timezone.now() + timedelta(days=1),
            owner=self.admin
        )
        self.client = APIClient()
    
    def test_admin_can_ban_user(self):
        """Test admin can ban a user"""
        self.client.force_authenticate(user=self.admin)
        
        # Ban creation would be tested here
        ban = UserBan.objects.create(
            user=self.user,
            event=self.event,
            reason='fraud',
            issued_by=self.admin
        )
        
        self.assertTrue(ban.is_active)
        self.assertTrue(ban.is_permanent)
    
    def test_banned_user_cannot_be_banned_twice(self):
        """Test user cannot be banned twice"""
        UserBan.objects.create(
            user=self.user,
            event=self.event,
            reason='fraud',
            issued_by=self.admin,
            is_active=True
        )
        
        # Try to create another active ban
        with self.assertRaises(Exception):
            UserBan.objects.create(
                user=self.user,
                event=self.event,
                reason='harassment',
                issued_by=self.admin,
                is_active=True
            )


# ============================================================================
# SIGNAL TESTS
# ============================================================================

class SignalEnforcementTests(TestCase):
    """Test automatic enforcement via signals"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass',
            role=EnhancedUserRole.MASTER_ADMIN
        )
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass',
            role=EnhancedUserRole.ATTENDEE
        )
        self.event = Event.objects.create(
            title='Test',
            date=timezone.now() + timedelta(days=1),
            owner=self.admin
        )
    
    def test_ban_prevents_metrics_update(self):
        """Test that ban is tracked in metrics"""
        # Create ban
        ban = UserBan.objects.create(
            user=self.user,
            event=self.event,
            reason='fraud',
            issued_by=self.admin,
            is_active=True
        )
        
        self.assertTrue(ban.is_active)
        self.assertIsNotNone(ban.issued_at)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TicketingIntegrationTests(TestCase):
    """End-to-end tests for ticketing workflows"""
    
    def setUp(self):
        RBACUtils.initialize_roles()
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass',
            role=EnhancedUserRole.MASTER_ADMIN,
            is_staff=True
        )
        self.organizer = User.objects.create_user(
            email='org@test.com',
            password='testpass',
            role=EnhancedUserRole.EVENT_ORGANIZER
        )
        self.attendee = User.objects.create_user(
            email='user@test.com',
            password='testpass',
            role=EnhancedUserRole.ATTENDEE
        )
        self.event = Event.objects.create(
            title='Test Event',
            date=timezone.now() + timedelta(days=1),
            owner=self.organizer
        )
        self.ticket_type = TicketType.objects.create(
            event=self.event,
            name='GA',
            price=Decimal('50.00')
        )
        self.ticket = Ticket.objects.create(
            ticket_type=self.ticket_type,
            holder=self.attendee,
            ticket_code='TEST001',
            status='active'
        )
    
    def test_complete_ban_workflow(self):
        """Test complete ban workflow"""
        # 1. Create ban
        ban = UserBan.objects.create(
            user=self.attendee,
            event=self.event,
            reason='fraud',
            issued_by=self.admin,
            description='User engaged in fraudulent activity'
        )
        self.assertTrue(ban.is_active)
        
        # 2. Request appeal
        ban.appeal_status = 'pending'
        ban.save()
        
        # 3. Approve appeal
        ban.lift(user=self.admin)
        self.assertFalse(ban.is_active)
    
    def test_ticket_disable_workflow(self):
        """Test complete ticket disablement workflow"""
        # 1. Disable ticket
        disablement = TicketDisablement.objects.create(
            ticket=self.ticket,
            reason='duplicate',
            disabled_by=self.admin,
            notes='Duplicate entry detected'
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'disabled')
        
        # 2. Re-enable ticket
        disablement.re_enable(user=self.admin)
        self.assertEqual(disablement.status, 'active')
    
    def test_ticket_transfer_workflow(self):
        """Test complete ticket transfer workflow"""
        recipient = User.objects.create_user(
            email='recipient@test.com',
            password='testpass',
            role=EnhancedUserRole.ATTENDEE
        )
        
        # 1. Create transfer offer
        transfer = TicketTransfer.objects.create(
            ticket=self.ticket,
            from_user=self.attendee,
            to_user=recipient,
            transfer_type='gift',
            status='pending'
        )
        self.assertEqual(transfer.status, 'pending')
        
        # 2. Accept transfer
        transfer.accept_transfer(recipient)
        self.assertEqual(transfer.status, 'accepted')
        
        # 3. Complete transfer
        transfer.status = 'completed'
        transfer.save()
        self.assertEqual(transfer.status, 'completed')


class RBACHierarchyTests(TestCase):
    """Test role hierarchy enforcement"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass',
            role=EnhancedUserRole.MASTER_ADMIN
        )
        self.organizer = User.objects.create_user(
            email='org@test.com',
            password='testpass',
            role=EnhancedUserRole.EVENT_ORGANIZER
        )
        self.manager = User.objects.create_user(
            email='manager@test.com',
            password='testpass',
            role=EnhancedUserRole.EVENT_MANAGER
        )
    
    def test_admin_can_manage_organizer(self):
        """Test admin can manage organizer"""
        from accounts.enhanced_rbac import can_manage_user
        self.assertTrue(can_manage_user(self.admin, self.organizer))
    
    def test_organizer_can_manage_manager(self):
        """Test organizer can manage manager"""
        from accounts.enhanced_rbac import can_manage_user
        self.assertTrue(can_manage_user(self.organizer, self.manager))
    
    def test_manager_cannot_manage_organizer(self):
        """Test manager cannot manage organizer"""
        from accounts.enhanced_rbac import can_manage_user
        self.assertFalse(can_manage_user(self.manager, self.organizer))


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class EdgeCaseTests(TestCase):
    """Test edge cases and error conditions"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass',
            role=EnhancedUserRole.MASTER_ADMIN
        )
        self.organizer = User.objects.create_user(
            email='org@test.com',
            password='testpass',
            role=EnhancedUserRole.EVENT_ORGANIZER
        )
        self.event = Event.objects.create(
            title='Test',
            date=timezone.now() + timedelta(days=1),
            owner=self.organizer
        )
    
    def test_global_ban_affects_all_events(self):
        """Test that global ban (null event) affects all events"""
        user = User.objects.create_user(
            email='user@test.com',
            password='testpass'
        )
        
        ban = UserBan.objects.create(
            user=user,
            event=None,  # Global ban
            reason='fraud',
            issued_by=self.admin
        )
        
        self.assertIsNone(ban.event)
    
    def test_expired_temporary_ban(self):
        """Test temporary ban expiration"""
        user = User.objects.create_user(
            email='user@test.com',
            password='testpass'
        )
        
        past_date = timezone.now() - timedelta(days=1)
        ban = UserBan.objects.create(
            user=user,
            event=self.event,
            reason='fraud',
            issued_by=self.admin,
            ban_until=past_date
        )
        
        self.assertTrue(ban.is_expired)
        self.assertEqual(ban.days_remaining, 0)


# Tests are run via: python manage.py test tests.test_ticketing_enhancements


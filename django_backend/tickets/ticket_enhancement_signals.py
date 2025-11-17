"""
Django signals for ticket enhancement enforcement
Automatically enforces bans and blacklist checks
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction

from orders.models import Order
from attendees.models import CheckIn, Ticket
from .ticket_enhancements import UserBan, TicketBlacklist, TicketTransfer, EventMetrics


# ============================================================================
# ORDER PLACEMENT - CHECK BAN
# ============================================================================

@receiver(pre_save, sender=Order)
def check_user_banned_on_order(sender, instance, **kwargs):
    """
    Check if user is banned before allowing order
    Called when Order is about to be saved
    """
    if instance.id is None:  # Only for new orders
        # Check if user is banned from event
        if UserBan.is_user_banned(instance.user, instance.event):
            raise ValidationError(
                f"User {instance.user.email} is banned from {instance.event.title}"
            )


# ============================================================================
# CHECK-IN - CHECK BAN AND BLACKLIST
# ============================================================================

@receiver(pre_save, sender=CheckIn)
def check_ban_and_blacklist_on_checkin(sender, instance, **kwargs):
    """
    Check if user is banned or ticket is blacklisted before check-in
    Called when CheckIn is about to be saved
    """
    if instance.id is None:  # Only for new check-ins
        # Get ticket and user
        ticket = instance.ticket
        user = instance.qr_code.ticket.order.user if instance.qr_code else None
        event = instance.event
        
        # Check if ticket is blacklisted
        if TicketBlacklist.is_ticket_blacklisted(ticket):
            instance.scan_result = 'invalid_code'
            instance.validation_errors.append('Ticket has been blacklisted')
            instance.status = 'invalid'
            # Don't raise - we want to record the attempt
        
        # Check if user is banned
        if user and UserBan.is_user_banned(user, event):
            instance.scan_result = 'invalid_code'
            instance.validation_errors.append('User is banned from this event')
            instance.status = 'invalid'
            # Log banned user entry attempt
            ban = UserBan.objects.filter(
                user=user,
                event=event
            ).first()
            if ban and ban.is_active:
                ban_attempt = {
                    'timestamp': timezone.now().isoformat(),
                    'location': instance.check_in_location,
                    'device': instance.scanner_device_id
                }
                if not hasattr(ban, '_entry_attempts'):
                    ban._entry_attempts = []
                ban._entry_attempts.append(ban_attempt)


@receiver(post_save, sender=CheckIn)
def log_invalid_checkin(sender, instance, created, **kwargs):
    """
    Log invalid check-in attempts (bans, blacklist)
    """
    if created and instance.status == 'invalid':
        # Update metrics for invalid checks
        metrics, _ = EventMetrics.objects.get_or_create(event=instance.event)
        
        if 'blacklist' in str(instance.validation_errors):
            metrics.suspicious_transactions += 1
        elif 'banned' in str(instance.validation_errors):
            metrics.banned_user_entry_attempts += 1
        
        metrics.save()


# ============================================================================
# TICKET TRANSFER - QR REGENERATION
# ============================================================================

@receiver(post_save, sender=TicketTransfer)
def regenerate_qr_on_transfer(sender, instance, created, **kwargs):
    """
    Regenerate QR code when transfer is completed
    """
    if not created and instance.status == 'completed':
        if instance.regenerate_qr and instance.ticket.qr_code_data:
            # Get the QR code object
            from attendees.models import TicketQRCode
            
            old_qr = TicketQRCode.objects.filter(ticket=instance.ticket).first()
            
            if old_qr:
                # Store old QR reference
                instance.old_qr_code = old_qr
                
                # Create new QR code for new owner
                new_qr = TicketQRCode.objects.create(
                    ticket=instance.ticket,
                    order=instance.ticket.order,
                    event=instance.ticket.event,
                    qr_code_data=old_qr.generate_qr_data(),  # Regenerate
                    secret_key=old_qr.secret_key,
                    access_level=old_qr.access_level,
                    usage_limit=old_qr.usage_limit,
                )
                
                instance.new_qr_code = new_qr
                instance.save()


# ============================================================================
# TICKET TRANSFER - UPDATE TICKET OWNERSHIP
# ============================================================================

@receiver(post_save, sender=TicketTransfer)
def update_ticket_on_transfer_accept(sender, instance, created, **kwargs):
    """
    Update ticket when transfer is accepted
    """
    if not created and instance.status == 'accepted':
        ticket = instance.ticket
        
        # Update ticket ownership
        ticket.order.user = instance.to_user
        ticket.order.save()
        
        # Update ticket status
        ticket.status = 'transferred'
        ticket.save()


# ============================================================================
# EVENT METRICS - UPDATE ON NEW TICKETS/ORDERS
# ============================================================================

@receiver(post_save, sender=Order)
def update_event_metrics_on_order(sender, instance, created, **kwargs):
    """
    Update event metrics when order is created
    """
    if created:
        metrics, _ = EventMetrics.objects.get_or_create(event=instance.event)
        metrics.total_purchased += 1
        metrics.total_revenue += instance.total_price
        
        # Calculate average price
        from django.db.models import Sum, Count
        total = Order.objects.filter(event=instance.event).aggregate(
            total=Sum('total_price'),
            count=Count('id')
        )
        if total['count'] > 0:
            metrics.avg_ticket_price = total['total'] / total['count']
        
        metrics.save()


# ============================================================================
# USER BAN - AUDIT LOGGING
# ============================================================================

@receiver(post_save, sender=UserBan)
def log_ban_action(sender, instance, created, **kwargs):
    """
    Log when user is banned
    """
    if created:
        from django.contrib.admin.models import LogEntry, ADDITION
        from django.contrib.contenttypes.models import ContentType
        
        # Log ban action
        try:
            LogEntry.objects.create(
                user=instance.issued_by,
                content_type=ContentType.objects.get_for_model(UserBan),
                object_id=instance.id,
                object_repr=str(instance),
                action_flag=ADDITION,
                change_message=f"Banned user {instance.user.email} - Reason: {instance.reason}"
            )
        except Exception as e:
            # Silently fail if logging fails
            pass


# ============================================================================
# TICKET BLACKLIST - AUDIT LOGGING
# ============================================================================

@receiver(post_save, sender=TicketBlacklist)
def log_blacklist_action(sender, instance, created, **kwargs):
    """
    Log when ticket is blacklisted
    """
    if created:
        from django.contrib.admin.models import LogEntry, ADDITION
        from django.contrib.contenttypes.models import ContentType
        
        # Log blacklist action
        try:
            LogEntry.objects.create(
                user=instance.blacklisted_by,
                content_type=ContentType.objects.get_for_model(TicketBlacklist),
                object_id=instance.id,
                object_repr=str(instance),
                action_flag=ADDITION,
                change_message=f"Blacklisted ticket - Reason: {instance.reason}"
            )
        except Exception as e:
            # Silently fail if logging fails
            pass


# ============================================================================
# APP CONFIG - REGISTER SIGNALS
# ============================================================================

def register_signals():
    """
    Function to register all signals
    Call this in apps.py ready() method
    """
    pass  # Signals auto-register when this module is imported


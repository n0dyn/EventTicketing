"""
Payment views for Django REST Framework
"""
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum
from django.utils import timezone
import stripe
from django.conf import settings

from .models import Payment, Refund
from .serializers import (
    PaymentSerializer, PaymentListSerializer, PaymentCreateSerializer,
    RefundSerializer, RefundListSerializer, RefundCreateSerializer,
    StripePaymentSerializer, RefundApproveSerializer
)

# Configure stripe
stripe.api_key = settings.STRIPE_SECRET_KEY if hasattr(settings, 'STRIPE_SECRET_KEY') else None


class PaymentViewSet(viewsets.ModelViewSet):
    """Payment viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method', 'user', 'order']
    search_fields = ['transaction_id', 'user__email']
    ordering_fields = ['amount', 'created_at', 'paid_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        elif self.action == 'list':
            return PaymentListSerializer
        return PaymentSerializer
    
    def get_queryset(self):
        queryset = Payment.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(user=self.request.user) |
                Q(order__buyer=self.request.user)
            ).distinct()
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def stripe_pay(self, request, pk=None):
        """Process Stripe payment"""
        payment = self.get_object()
        serializer = StripePaymentSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # Create payment intent with Stripe
                intent = stripe.PaymentIntent.create(
                    amount=int(payment.amount * 100),  # Stripe uses cents
                    currency=payment.currency.lower(),
                    payment_method=serializer.validated_data['payment_method_id'],
                    confirm=True
                )
                
                payment.stripe_payment_intent_id = intent.id
                payment.transaction_id = intent.id
                payment.status = 'completed' if intent.status == 'succeeded' else 'pending'
                payment.paid_at = timezone.now() if payment.status == 'completed' else None
                payment.save()
                
                return Response({
                    'status': 'success',
                    'payment': PaymentSerializer(payment).data,
                    'intent_status': intent.status
                })
            except stripe.error.CardError as e:
                return Response({
                    'error': 'Card declined',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({
                    'error': 'Payment failed',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark payment as paid (for manual payments)"""
        payment = self.get_object()
        if payment.status == 'completed':
            return Response(
                {'error': 'Payment already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.status = 'completed'
        payment.paid_at = timezone.now()
        payment.save()
        
        return Response({
            'status': 'success',
            'payment': PaymentSerializer(payment).data
        })
    
    @action(detail=False, methods=['get'])
    def my_payments(self, request):
        """Get current user's payments"""
        queryset = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get payment statistics"""
        queryset = self.get_queryset()
        stats = {
            'total_payments': queryset.count(),
            'total_amount': str(queryset.aggregate(Sum('amount'))['amount__sum'] or 0),
            'completed': queryset.filter(status='completed').count(),
            'pending': queryset.filter(status='pending').count(),
            'failed': queryset.filter(status='failed').count()
        }
        return Response(stats)


class RefundViewSet(viewsets.ModelViewSet):
    """Refund viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'reason', 'payment', 'payment__user']
    search_fields = ['payment__transaction_id']
    ordering_fields = ['amount', 'created_at', 'refunded_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RefundCreateSerializer
        elif self.action == 'list':
            return RefundListSerializer
        return RefundSerializer
    
    def get_queryset(self):
        queryset = Refund.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(payment__user=self.request.user)
            )
        return queryset
    
    def perform_create(self, serializer):
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a refund"""
        refund = self.get_object()
        
        if refund.status != 'pending':
            return Response(
                {'error': 'Only pending refunds can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = RefundApproveSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # If Stripe refund needed
                if refund.payment.stripe_payment_intent_id:
                    stripe_refund = stripe.Refund.create(
                        payment_intent=refund.payment.stripe_payment_intent_id,
                        amount=int(refund.amount * 100)
                    )
                    refund.stripe_refund_id = stripe_refund.id
                
                refund.status = 'completed'
                refund.refunded_at = timezone.now()
                refund.save()
                
                return Response({
                    'status': 'success',
                    'refund': RefundSerializer(refund).data
                })
            except stripe.error.InvalidRequestError as e:
                refund.status = 'failed'
                refund.save()
                return Response({
                    'error': 'Refund failed',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a refund request"""
        refund = self.get_object()
        
        if refund.status != 'pending':
            return Response(
                {'error': 'Only pending refunds can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        refund.status = 'rejected'
        refund.save()
        
        return Response({
            'status': 'success',
            'refund': RefundSerializer(refund).data
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get refund statistics"""
        queryset = self.get_queryset()
        stats = {
            'total_refunds': queryset.count(),
            'total_amount': str(queryset.aggregate(Sum('amount'))['amount__sum'] or 0),
            'approved': queryset.filter(status='completed').count(),
            'pending': queryset.filter(status='pending').count(),
            'rejected': queryset.filter(status='rejected').count()
        }
        return Response(stats)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET if hasattr(settings, 'STRIPE_WEBHOOK_SECRET') else None
        )
    except ValueError:
        return Response({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return Response({'error': 'Invalid signature'}, status=400)
    
    # Handle events
    if event['type'] == 'payment_intent.succeeded':
        intent = event['data']['object']
        try:
            payment = Payment.objects.get(stripe_payment_intent_id=intent.id)
            payment.status = 'completed'
            payment.paid_at = timezone.now()
            payment.save()
        except Payment.DoesNotExist:
            pass
    
    elif event['type'] == 'charge.refunded':
        charge = event['data']['object']
        try:
            payment = Payment.objects.get(stripe_payment_intent_id=charge.payment_intent)
            refund = Refund.objects.get(stripe_refund_id=charge.refund)
            refund.status = 'completed'
            refund.refunded_at = timezone.now()
            refund.save()
        except (Payment.DoesNotExist, Refund.DoesNotExist):
            pass
    
    return Response({'received': True})

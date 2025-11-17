"""
Order views for Django REST Framework
"""
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.utils import timezone
from .models import Order, OrderItem, Cart, CartItem
from .serializers import (
    OrderSerializer, OrderListSerializer, OrderCreateSerializer,
    OrderUpdateSerializer, CartSerializer, CartItemSerializer,
    CartAddItemSerializer, CartUpdateItemSerializer, CartCheckoutSerializer
)
from core.permissions import IsOrderOwner


class OrderItemViewSet(viewsets.ReadOnlyModelViewSet):
    """Order item read-only viewset"""
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['order', 'ticket_type']
    
    def get_queryset(self):
        queryset = OrderItem.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(order__buyer=self.request.user)
            )
        return queryset


class OrderViewSet(viewsets.ModelViewSet):
    """Order viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'event', 'buyer']
    search_fields = ['order_number', 'buyer__email']
    ordering_fields = ['created_at', 'total_amount', 'order_number']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return OrderUpdateSerializer
        elif self.action == 'list':
            return OrderListSerializer
        return OrderSerializer
    
    def get_queryset(self):
        queryset = Order.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(buyer=self.request.user)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark order as paid"""
        order = self.get_object()
        order.payment_status = 'paid'
        order.status = 'completed'
        order.save()
        return Response({
            'status': 'success',
            'message': 'Order marked as paid',
            'order': OrderSerializer(order).data
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()
        if order.status == 'completed':
            return Response(
                {'error': 'Cannot cancel completed order'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = 'cancelled'
        order.save()
        return Response({
            'status': 'success',
            'message': 'Order cancelled',
            'order': OrderSerializer(order).data
        })
    
    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """Get order items"""
        order = self.get_object()
        items = order.items.all()
        serializer = OrderItemSerializer(items, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        """Get current user's orders"""
        queryset = self.get_queryset().filter(buyer=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resend_confirmation(self, request, pk=None):
        """Resend order confirmation email"""
        order = self.get_object()
        # Email sending would go here
        return Response({
            'status': 'success',
            'message': 'Confirmation email sent'
        })


class CartItemViewSet(viewsets.ModelViewSet):
    """Cart item viewset"""
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)
    
    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        serializer.save(cart=cart)


class CartViewSet(viewsets.ViewSet):
    """Cart viewset - custom endpoints for cart operations"""
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        """Get current user's cart"""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart"""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartAddItemSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                from tickets.models import TicketType
                ticket_type = TicketType.objects.get(id=serializer.validated_data['ticket_type_id'])
                
                # Check if item already in cart
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    ticket_type=ticket_type,
                    defaults={'quantity': serializer.validated_data['quantity']}
                )
                
                if not created:
                    cart_item.quantity += serializer.validated_data['quantity']
                    cart_item.save()
                
                return Response({
                    'status': 'success',
                    'message': 'Item added to cart',
                    'cart': CartSerializer(cart, context={'request': request}).data
                })
            except TicketType.DoesNotExist:
                return Response(
                    {'error': 'Ticket type not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """Update item quantity in cart"""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartUpdateItemSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                cart_item_id = request.data.get('cart_item_id')
                cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)
                cart_item.quantity = serializer.validated_data['quantity']
                cart_item.save()
                
                return Response({
                    'status': 'success',
                    'message': 'Cart item updated',
                    'cart': CartSerializer(cart, context={'request': request}).data
                })
            except CartItem.DoesNotExist:
                return Response(
                    {'error': 'Cart item not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        """Remove item from cart"""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item_id = request.data.get('cart_item_id')
        
        try:
            cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)
            cart_item.delete()
            
            return Response({
                'status': 'success',
                'message': 'Item removed from cart',
                'cart': CartSerializer(cart, context={'request': request}).data
            })
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear entire cart"""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        
        return Response({
            'status': 'success',
            'message': 'Cart cleared',
            'cart': CartSerializer(cart, context={'request': request}).data
        })
    
    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """Checkout from cart"""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartCheckoutSerializer(data=request.data)
        
        if serializer.is_valid():
            if cart.items.count() == 0:
                return Response(
                    {'error': 'Cart is empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create order from cart
            try:
                total_amount = sum(
                    float(item.ticket_type.base_price) * item.quantity
                    for item in cart.items.all()
                )
                
                order = Order.objects.create(
                    buyer=request.user,
                    total_amount=total_amount,
                    payment_method=serializer.validated_data['payment_method'],
                    status='pending'
                )
                
                # Copy items from cart to order
                for cart_item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        ticket_type=cart_item.ticket_type,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.ticket_type.base_price
                    )
                
                # Clear cart
                cart.items.all().delete()
                
                return Response({
                    'status': 'success',
                    'message': 'Order created successfully',
                    'order': OrderSerializer(order).data
                }, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from .serializers import OrderItemSerializer

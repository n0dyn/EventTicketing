import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.order import Order, OrderStatus, Cart, CartItem
from app.models.ticket import TicketType, Ticket
from app.schemas.order import OrderCreate, OrderUpdate, CartItemCreate, CartItemUpdate


def get_order(db: Session, order_id: str) -> Optional[Order]:
    """
    Get order by ID
    """
    return db.query(Order).filter(Order.id == order_id).first()


def get_orders_by_user(
    db: Session, user_id: str, skip: int = 0, limit: int = 100
) -> List[Order]:
    """
    Get all orders for a user
    """
    return db.query(Order).filter(Order.user_id == user_id).offset(skip).limit(limit).all()


def create_order(db: Session, order_in: OrderCreate) -> Order:
    """
    Create a new order
    """
    db_order = Order(
        id=str(uuid.uuid4()),
        user_id=order_in.user_id,
        total_amount=order_in.total_amount,
        status=OrderStatus.PENDING,
        payment_method=order_in.payment_method,
        billing_address=order_in.billing_address,
        billing_city=order_in.billing_city,
        billing_country=order_in.billing_country,
        billing_postal_code=order_in.billing_postal_code,
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def update_order(db: Session, order_id: str, order_in: OrderUpdate) -> Optional[Order]:
    """
    Update an order
    """
    db_order = get_order(db, order_id)
    if not db_order:
        return None

    update_data = order_in.dict(exclude_unset=True)
    
    # If status is being changed to completed, set the completed_at timestamp
    if update_data.get("status") == OrderStatus.COMPLETED and db_order.status != OrderStatus.COMPLETED:
        update_data["completed_at"] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(db_order, field, value)
        
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def delete_order(db: Session, order_id: str) -> bool:
    """
    Delete an order
    """
    db_order = get_order(db, order_id)
    if not db_order:
        return False
    
    db.delete(db_order)
    db.commit()
    return True


# Cart functions
def get_user_cart(db: Session, user_id: str) -> Optional[Cart]:
    """
    Get cart by user ID or create if not exists
    """
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        # Create a new cart for the user
        cart = Cart(
            id=str(uuid.uuid4()),
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(days=7)  # Cart expires in 7 days
        )
        db.add(cart)
        db.commit()
        db.refresh(cart)
    
    return cart


def add_to_cart(db: Session, user_id: str, item_in: CartItemCreate) -> CartItem:
    """
    Add item to cart
    """
    # Get user's cart
    cart = get_user_cart(db, user_id)
    
    # Check if ticket type exists
    ticket_type = db.query(TicketType).filter(TicketType.id == item_in.ticket_type_id).first()
    if not ticket_type:
        raise HTTPException(status_code=404, detail="Ticket type not found")
        
    # Check if ticket type is already in cart
    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.ticket_type_id == item_in.ticket_type_id
    ).first()
    
    if existing_item:
        # Update quantity
        existing_item.quantity += item_in.quantity
        db.add(existing_item)
        db.commit()
        db.refresh(existing_item)
        return existing_item
    
    # Create new cart item
    db_item = CartItem(
        id=str(uuid.uuid4()),
        cart_id=cart.id,
        ticket_type_id=item_in.ticket_type_id,
        quantity=item_in.quantity
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_cart_item(db: Session, cart_item_id: str, item_in: CartItemUpdate) -> Optional[CartItem]:
    """
    Update cart item
    """
    db_item = db.query(CartItem).filter(CartItem.id == cart_item_id).first()
    if not db_item:
        return None
    
    update_data = item_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def remove_from_cart(db: Session, cart_item_id: str) -> bool:
    """
    Remove item from cart
    """
    db_item = db.query(CartItem).filter(CartItem.id == cart_item_id).first()
    if not db_item:
        return False
    
    db.delete(db_item)
    db.commit()
    return True


def clear_cart(db: Session, user_id: str) -> bool:
    """
    Clear all items from a user's cart
    """
    cart = get_user_cart(db, user_id)
    if not cart:
        return False
    
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    return True


def checkout(db: Session, user_id: str, order_data: Dict[str, Any]) -> Tuple[Order, List[Ticket]]:
    """
    Convert cart to order and create tickets
    """
    # Get user's cart
    cart = get_user_cart(db, user_id)
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Calculate total amount
    total_amount = 0
    for item in cart.items:
        ticket_type = db.query(TicketType).filter(TicketType.id == item.ticket_type_id).first()
        if not ticket_type:
            continue
        total_amount += ticket_type.price * item.quantity
    
    # Create order
    order_in = OrderCreate(
        user_id=user_id,
        total_amount=total_amount,
        **order_data
    )
    order = create_order(db, order_in)
    
    # Associate cart items with order
    for item in cart.items:
        item.order_id = order.id
        db.add(item)
    
    # Create tickets for each cart item
    tickets = []
    for item in cart.items:
        ticket_type = db.query(TicketType).filter(TicketType.id == item.ticket_type_id).first()
        if not ticket_type:
            continue
            
        for _ in range(item.quantity):
            ticket = Ticket(
                id=str(uuid.uuid4()),
                ticket_type_id=item.ticket_type_id,
                order_id=order.id,
                code=f"TICKET-{str(uuid.uuid4())[:8]}"  # Generate a unique ticket code
            )
            db.add(ticket)
            tickets.append(ticket)
    
    # Create a new empty cart for the user
    new_cart = Cart(
        id=str(uuid.uuid4()),
        user_id=user_id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(new_cart)
    
    db.commit()
    
    # Refresh objects
    db.refresh(order)
    for ticket in tickets:
        db.refresh(ticket)
    
    return order, tickets 
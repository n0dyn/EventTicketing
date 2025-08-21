from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app import schemas, services
from app.api import deps
from app.models.user import User

router = APIRouter()


# Cart endpoints
@router.get("/cart", response_model=schemas.Cart)
def get_cart(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Get current user's cart
    """
    return services.get_user_cart(db=db, user_id=current_user.id)


@router.post("/cart/items", response_model=schemas.CartItem)
def add_to_cart(
    *,
    db: Session = Depends(deps.get_db),
    item_in: schemas.CartItemCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Add item to cart
    """
    return services.add_to_cart(db=db, user_id=current_user.id, item_in=item_in)


@router.put("/cart/items/{item_id}", response_model=schemas.CartItem)
def update_cart_item(
    *,
    db: Session = Depends(deps.get_db),
    item_id: str,
    item_in: schemas.CartItemUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update item in cart
    """
    cart = services.get_user_cart(db=db, user_id=current_user.id)
    item = db.query(services.CartItem).filter(
        services.CartItem.id == item_id, 
        services.CartItem.cart_id == cart.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    
    return services.update_cart_item(db=db, cart_item_id=item_id, item_in=item_in)


@router.delete("/cart/items/{item_id}")
def remove_from_cart(
    *,
    db: Session = Depends(deps.get_db),
    item_id: str,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Remove item from cart
    """
    cart = services.get_user_cart(db=db, user_id=current_user.id)
    item = db.query(services.CartItem).filter(
        services.CartItem.id == item_id, 
        services.CartItem.cart_id == cart.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    
    success = services.remove_from_cart(db=db, cart_item_id=item_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove item from cart")
    
    return {"message": "Item removed from cart"}


@router.delete("/cart")
def clear_cart(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Clear all items from cart
    """
    success = services.clear_cart(db=db, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to clear cart")
    
    return {"message": "Cart cleared"}


@router.post("/cart/checkout", response_model=schemas.Order)
def checkout(
    *,
    db: Session = Depends(deps.get_db),
    order_data: dict = Body(...),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Checkout cart and create order
    """
    try:
        order, _ = services.checkout(db=db, user_id=current_user.id, order_data=order_data)
        return order
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checkout failed: {str(e)}")


# Order endpoints
@router.get("/orders", response_model=List[schemas.Order])
def get_orders(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get current user's orders
    """
    orders = services.get_orders_by_user(db=db, user_id=current_user.id, skip=skip, limit=limit)
    return orders


@router.get("/orders/{order_id}", response_model=schemas.Order)
def get_order(
    *,
    db: Session = Depends(deps.get_db),
    order_id: str,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get order by ID
    """
    order = services.get_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if the order belongs to the current user
    if order.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return order


@router.put("/orders/{order_id}", response_model=schemas.Order)
def update_order(
    *,
    db: Session = Depends(deps.get_db),
    order_id: str,
    order_in: schemas.OrderUpdate,
    current_user: User = Depends(deps.get_current_user_admin),
) -> Any:
    """
    Update order (admin only)
    """
    order = services.get_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = services.update_order(db=db, order_id=order_id, order_in=order_in)
    return order 
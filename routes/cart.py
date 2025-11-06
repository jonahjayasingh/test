from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from models import CartItem, Product, User, Order
from .auth import get_current_user
from datetime import datetime
from database import get_session
import logging
router = APIRouter(prefix="/cart", tags=["Cart"])


@router.post("/add")
def add_to_cart(
    request: dict = {
        "product_id": int,
        "quantity": int
    },
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    product_id = request['product_id']
    quantity = request['quantity']

    # Check if product exists
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate stock
    if quantity > product.stock_quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Only {product.stock_quantity} units available in stock. Maximum quantity allowed is {product.stock_quantity}."
        )

    # Check if cart item already exists
    existing_item = session.exec(
        select(CartItem)
        .where(CartItem.user_id == current_user.id)
        .where(CartItem.product_id == product_id)
    ).first()

    if existing_item:
        new_quantity = existing_item.quantity + quantity
        print(new_quantity, product.stock_quantity)
        if new_quantity > product.stock_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot add more than {product.stock_quantity} units to cart. Current quantity in cart is {existing_item.quantity}. Maximum allowed is {product.stock_quantity - existing_item.quantity}."
            )
        existing_item.quantity = new_quantity
        existing_item.updated_at = datetime.now()
        session.add(existing_item)
    else:
        new_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity,
        )
        session.add(new_item)

    session.commit()
    session.refresh(existing_item or new_item)  # ✅ fixed line

    # Reduce stock in Product table
    product = session.get(Product, product_id)
    product.stock_quantity -= quantity
    session.add(product)

    session.commit()
    session.refresh(product)

    return {
        "message": f"{product.name} added to cart successfully.",
    }



@router.get("/items/")
def get_cart_items(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    items = session.exec(
        select(CartItem).where(CartItem.user_id == current_user.id)
    ).all()

    # Attach product details for richer response
    response = []
    for item in items:
        product = session.get(Product, item.product_id)
        if product:
            response.append({
                "cart_item_id": item.id,
                "product_id": product.id,
                "product_name": product.name,
                "price": product.price,
                "quantity": item.quantity,
                "subtotal": product.price * item.quantity,
                "image_path": product.image_path,
                "stock_quantity": product.stock_quantity,
            })
    return response


@router.delete("/remove/{cart_item_id}")
def remove_from_cart(cart_item_id: int, session: Session = Depends(get_session)):
    cart_item = session.get(CartItem, cart_item_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    # Add stock back to Product table
    product = session.get(Product, cart_item.product_id)
    product.stock_quantity += cart_item.quantity
    session.add(product)

    session.delete(cart_item)
    session.commit()
    return {"message": "Item removed from cart"}


@router.delete("/clear/{user_id}")
def clear_cart(user_id: int, session: Session = Depends(get_session)):
    """Convenience endpoint to clear all cart items for a user."""
    items = session.exec(select(CartItem).where(CartItem.user_id == user_id)).all()
    if not items:
        raise HTTPException(status_code=404, detail="Cart is already empty")

    for item in items:
        # Add stock back to Product table
        product = session.get(Product, item.product_id)
        product.stock_quantity += item.quantity
        session.add(product)
        session.delete(item)

    session.commit()
    return {"message": "Cart cleared successfully"}

from fastapi import APIRouter, HTTPException, Depends,Request
from sqlmodel import Session
from models import Order, CartItem
from database import get_session
from .auth import get_current_user
from sqlmodel import select
from typing import List
import logging
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders")



router = APIRouter(prefix="/orders", tags=["Orders"])
# {'items': [{'product_id': 1, 'quantity': 3, 'price': 308.74}], 'address': 'hello', 'is_paid': False}
@router.post("/create")
async def create_order(
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    try:
        data = await request.json()
        print("Received data:", data)

        items = data.get("items", [])
        address = data.get("address")
        is_paid = data.get("is_paid", False)

        if not items or not address:
            raise HTTPException(status_code=400, detail="Items and address are required.")

        created_orders = []

        for item in items:
            # Validate fields
            if "product_id" not in item or "quantity" not in item or "price" not in item:
                raise HTTPException(status_code=400, detail="Each item must include product_id, quantity, and price.")

            # Find cart item by user + product
            cart_item = session.exec(
                select(CartItem).where(
                    CartItem.user_id == user.id,
                    CartItem.product_id == item["product_id"],
                    CartItem.in_order == True
                )
            ).first()

            if not cart_item:
                raise HTTPException(
                    status_code=404,
                    detail=f"No active cart item found for product_id {item['product_id']}."
                )

            # Mark as ordered
            cart_item.in_order = True
            session.add(cart_item)

            # Create order linked to that cart item
            order = Order(
                user_id=user.id,
                cart_id=cart_item.id,
                total_price=item["quantity"] * item["price"],
                address=address,
                is_paid=is_paid,
            )
            session.add(order)
            session.flush()
            created_orders.append(order)

        # ✅ Commit once at the end
        session.commit()

        return {
            "message": "Order(s) placed successfully",
            "orders": [
                {
                    "order_id": o.id,
                    "total_price": o.total_price
                }
                for o in created_orders
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        print("Order creation failed:", e)
        raise HTTPException(status_code=500, detail="Order creation failed.")


@router.get("/", response_model=Order)
def get_order_details(
    order_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    order = session.exec(select(Order).where(Order.user_id == user.id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/all", response_model=List[Order])
def get_all_orders(
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    orders = session.exec(select(Order).where(Order.user_id == user.id)).all()
    return orders



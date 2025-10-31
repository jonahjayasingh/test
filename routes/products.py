from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlmodel import Session, select
from typing import List
from pathlib import Path
import shutil
from datetime import datetime
from fastapi.staticfiles import StaticFiles
import logging

from database import get_session
from models import Product, ProductCategory, User
from .auth import get_current_user

router = APIRouter(prefix="/products", tags=["products"])

# Base upload directory
UPLOAD_DIR = Path("static/images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
)

# ----------------------------------------------------------
# Create Product (JSON-based, not used in the app but left for flexibility)
# ----------------------------------------------------------
@router.post("/", response_model=Product)
def create_product_json(
    product: Product,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


# ----------------------------------------------------------
# List all products
# ----------------------------------------------------------
@router.get("/", response_model=List[Product])
def list_products(
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    products = session.exec(select(Product)).all()
    return products


# ----------------------------------------------------------
# List products by category
# ----------------------------------------------------------
@router.get("/{category_id}", response_model=List[Product])
def list_products_by_category(
    category_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    products = session.exec(
        select(Product)
        .join(ProductCategory, Product.category_id == ProductCategory.id)
        .where(
            ProductCategory.user_id == user.id,
            ProductCategory.id == category_id
        )
    ).all()

    if not products:
        raise HTTPException(
            status_code=404,
            detail="No products found for this category and user."
        )

    return products


# ----------------------------------------------------------
# Update Product
# ----------------------------------------------------------
@router.put("/update/{product_id}", response_model=Product)
def update_product(
    product_id: int,
    name: str = Form(None),
    description: str = Form(None),
    price: float = Form(None),
    stock_quantity: int = Form(None),
    is_active: bool = Form(None),
    category_id: int = Form(None),
    file: UploadFile = File(None),
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check ownership
    if db_product.category.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this product")

    # --- Update fields dynamically ---
    if name is not None:
        db_product.name = name
    if description is not None:
        db_product.description = description
    if price is not None:
        db_product.price = price
    if stock_quantity is not None:
        db_product.stock_quantity = stock_quantity
    if is_active is not None:
        db_product.is_active = is_active
    if category_id is not None:
        db_product.category_id = category_id

    # --- Handle image replacement ---
    if file:
        # Remove old image if it exists
        if db_product.image_path:
            old_path = Path(db_product.image_path)
            if old_path.exists():
                try:
                    old_path.unlink()
                except Exception as e:
                    logging.warning(f"Failed to delete old image: {e}")

        # Ensure user directory exists
        user_obj = session.exec(select(User).where(User.id == db_product.category.user_id)).first()
        user_dir = UPLOAD_DIR / user_obj.username
        user_dir.mkdir(parents=True, exist_ok=True)

        # Save new image
        new_path = user_dir / f"{db_product.id}_{file.filename}"
        with new_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        db_product.image_path = str(new_path)

    db_product.updated_at = datetime.now()
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product


# ----------------------------------------------------------
# Delete Product
# ----------------------------------------------------------
@router.delete("/{product_id}/", response_model=dict)
def delete_product(
    product_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if the product belongs to the user
    if db_product.category.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this product"
        )

    # Delete image file if exists
    if db_product.image_path:
        old_path = Path(db_product.image_path)
        if old_path.exists():
            try:
                old_path.unlink()
            except Exception as e:
                logging.warning(f"Failed to delete old image: {e}")

    session.delete(db_product)
    session.commit()
    return {"message": "Product deleted successfully"}


# ----------------------------------------------------------
# Create Product (with image upload)
# ----------------------------------------------------------
@router.post("/{product_id}/")
def create_product(
    name: str = Form(...),
    description: str = Form(None),
    price: float = Form(...),
    stock_quantity: int = Form(...),
    category_id: int = Form(...),
    file: UploadFile = File(None),
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    # Create product entry first
    product = Product(
        name=name,
        description=description,
        price=price,
        stock_quantity=stock_quantity,
        category_id=category_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    session.add(product)
    session.commit()
    session.refresh(product)

    # Get user from category owner
    user_obj = session.exec(select(User).where(User.id == product.category.user_id)).first()
    user_dir = UPLOAD_DIR / user_obj.username
    user_dir.mkdir(parents=True, exist_ok=True)  # ✅ ensure directory exists

    # Save image if provided
    if file:
        file_path = user_dir / f"{product.id}_{file.filename}"
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        product.image_path = str(file_path)
        session.add(product)
        session.commit()
        session.refresh(product)

    return {
        "message": "Product created successfully",
        "product_id": product.id,
        "image_path": product.image_path,
    }

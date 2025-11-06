from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Path
)
from sqlmodel import Session, select
from typing import List
from pathlib import Path as FilePath
import shutil
from datetime import datetime
import logging
import os

from database import get_session
from models import Product, ProductCategory, User
from .auth import get_current_user

router = APIRouter(prefix="/products", tags=["products"])

# Base upload directory
UPLOAD_DIR = FilePath("static/images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
)

# ----------------------------------------------------------
# Create Product (with image upload)
# ----------------------------------------------------------
@router.post("/{category_id}", response_model=dict)
def create_product(
    category_id: int = Path(...),
    name: str = Form(...),
    description: str = Form(None),
    price: float = Form(...),
    stock_quantity: int = Form(...),
    is_active: bool = Form(True),
    file: UploadFile = File(None),
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    """Create a product under a given category, optionally uploading an image."""

    # Ensure the category exists
    category = session.exec(
        select(ProductCategory).where(ProductCategory.id == category_id)
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Create product record
    product = Product(
        name=name,
        description=description,
        price=price,
        stock_quantity=stock_quantity,
        is_active=is_active,
        category_id=category_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    # Create directory for this user/category
    category_folder = category.name.lower().replace(" ", "_")
    user_dir = UPLOAD_DIR / user.username / category_folder
    user_dir.mkdir(parents=True, exist_ok=True)

    # Handle image upload
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


# ----------------------------------------------------------
# List all products
# ----------------------------------------------------------
@router.get("/list", response_model=List[Product])
def list_products(
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    return session.exec(select(Product)).all()


# ----------------------------------------------------------
# Get product details by product_id
# ----------------------------------------------------------
@router.get("/details/{product_id}", response_model=Product)
def get_product_details_by_id(
    product_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ----------------------------------------------------------
# List products by category
# ----------------------------------------------------------
@router.get("/{category_id}", response_model=List[Product])
def get_products_by_category(
    category_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    query = (
        select(Product)
        .join(ProductCategory, Product.category_id == ProductCategory.id)
        .where(ProductCategory.id == category_id)
    )

    if user.is_admin:
        query = query.where(ProductCategory.user_id == user.id)

    products = session.exec(query).all()
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
        raise HTTPException(status_code=403, detail="Not authorized")

    # Update fields
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

    # Replace image
    if file:
        if db_product.image_path:
            old_path = Path(db_product.image_path)
            if old_path.exists():
                try:
                    old_path.unlink()
                except Exception as e:
                    logging.warning(f"Failed to delete old image: {e}")

        user_dir = UPLOAD_DIR / user.username
        user_dir.mkdir(parents=True, exist_ok=True)
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
@router.delete("/{product_id}", response_model=dict)
def delete_product(
    product_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    if db_product.category.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

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

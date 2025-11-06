from models import ProductCategory
from .auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, delete, select
from typing import List

from database import get_session
from models import ProductCategory, Product
from .auth import get_current_user

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("/", response_model=ProductCategory)
def create_category(
    category: ProductCategory,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    category.user_id = user.id 
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.get("/", response_model=List[ProductCategory])
def list_categories(session: Session = Depends(get_session), user=Depends(get_current_user)):
    if not user.is_admin:
        subquery = select(Product.id).where(Product.category_id == ProductCategory.id)

        categories = session.exec(
            select(ProductCategory).where(subquery.exists()).order_by(ProductCategory.name)
        ).all()
    else:
        categories = session.exec(select(ProductCategory).where(ProductCategory.user_id == user.id).order_by(ProductCategory.name)).all()
    return categories

@router.get("/{category_id}", response_model=ProductCategory)
def read_category(
    category_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    category = session.get(ProductCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.put("/{category_id}", response_model=ProductCategory)
def update_category(
    category_id: int,
    category_update: ProductCategory,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    category = session.get(ProductCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    category_update_data = category_update.dict(exclude_unset=True)
    for key, value in category_update_data.items():
        setattr(category, key, value)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category

@router.delete("/{category_id}", response_model=ProductCategory)
def delete_category(
    category_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user)
):
    product = session.exec(select(Product).where(Product.category_id == category_id)).first()
    if product:
        session.exec(delete(Product).where(Product.category_id == category_id))
    
    category = session.get(ProductCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    session.delete(category)
    session.commit()
    return category
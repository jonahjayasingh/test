from models import ProductCategory
from .auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from database import get_session
from models import ProductCategory
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
    return session.exec(select(ProductCategory)).all()

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
    print(category_id)
    category = session.get(ProductCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    session.delete(category)
    session.commit()
    return category
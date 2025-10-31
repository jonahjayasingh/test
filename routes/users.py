from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from database import get_session
from models import User
from routes.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=User)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/", response_model=List[User])
def list_users(session: Session = Depends(get_session), user=Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return session.exec(select(User)).all()


@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user_update: User,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.dict(exclude_unset=True)

    for field in ["id", "created_at", "categories"]:
        update_data.pop(field, None)

    for key, value in update_data.items():
        setattr(user, key, value)

    session.add(user)
    session.commit()
    session.refresh(user)
    return user

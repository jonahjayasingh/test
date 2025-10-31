from datetime import datetime
from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship, Column, DateTime
from pydantic import EmailStr

class ProductCategory(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str = Field()
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    user: Optional["User"] = Relationship(back_populates="categories")
    products: List["Product"] = Relationship(back_populates="category")

class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    username: str = Field(unique=True)
    email: EmailStr = Field(unique=True)
    password: str 
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    last_login_at: datetime = Field(default_factory=datetime.now)
    categories: List[ProductCategory] = Relationship(back_populates="user")

class Product(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    description: Optional[str] = None
    price: float
    image_path: Optional[str] = None
    stock_quantity: int
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.now, onupdate=datetime.now)
    )
    category_id: int = Field(foreign_key="productcategory.id")
    category: Optional[ProductCategory] = Relationship(back_populates="products")

class Order(SQLModel, table=True):
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    quantity: int
    total_price: float = Field(default=0.0)
    is_paid: bool = Field(default=False)
    order_date: datetime = Field(default_factory=datetime.now)

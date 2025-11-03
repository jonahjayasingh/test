from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from models import Order, CartItem
from database import get_session
from fastapi import FastAPI, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel
from typing import List

from . import models, database, auth
from .config import settings

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True

class RateResponse(BaseModel):
    currency: str
    rate: float

class RateHistoryResponse(BaseModel):
    currency: str
    rate: float
    timestamp: str

def get_current_user_dep(request: Request, db: Session = Depends(database.get_db)):
    return auth.get_current_user(request, db)


@app.post("/auth/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/auth/login")
def login(user: UserLogin, response: Response, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    return {"message": "Successfully logged in"}

@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Successfully logged out"}

@app.get("/api/rates", response_model=List[RateResponse])
def get_rates(current_user: models.User = Depends(get_current_user_dep), db: Session = Depends(database.get_db)):
    # Mock data for MVP
    rates = [
        {"currency": "USD", "rate": 1.0},
        {"currency": "EUR", "rate": 0.92},
        {"currency": "GBP", "rate": 0.79},
    ]
    return rates

@app.get("/api/rates/history", response_model=List[RateHistoryResponse])
def get_rates_history(current_user: models.User = Depends(get_current_user_dep), db: Session = Depends(database.get_db)):
    # Mock data for MVP
    history = [
        {"currency": "EUR", "rate": 0.91, "timestamp": "2023-10-26T10:00:00Z"},
        {"currency": "EUR", "rate": 0.92, "timestamp": "2023-10-27T10:00:00Z"},
        {"currency": "GBP", "rate": 0.78, "timestamp": "2023-10-26T10:00:00Z"},
        {"currency": "GBP", "rate": 0.79, "timestamp": "2023-10-27T10:00:00Z"},
    ]
    return history

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel
from typing import List
from sqlalchemy import func
from datetime import datetime, timezone

from . import models, database, auth
from .config import settings
from .tasks import periodic_rate_fetcher

models.Base.metadata.create_all(bind=database.engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(periodic_rate_fetcher())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
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
    db_user = db.query(models.User).filter(models.User.email == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(email=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/auth/login")
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not db_user or not auth.verify_password(form_data.password, db_user.hashed_password):
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
    # Fetch the latest rate for each currency using a subquery for the max timestamp
    subquery = db.query(
        models.CurrencyHistory.currency,
        func.max(models.CurrencyHistory.timestamp).label("max_timestamp")
    ).group_by(models.CurrencyHistory.currency).subquery()

    latest_rates = db.query(models.CurrencyHistory).join(
        subquery,
        (models.CurrencyHistory.currency == subquery.c.currency) &
        (models.CurrencyHistory.timestamp == subquery.c.max_timestamp)
    ).all()

    return latest_rates

@app.get("/api/rates/history", response_model=List[RateHistoryResponse])
def get_rates_history(current_user: models.User = Depends(get_current_user_dep), db: Session = Depends(database.get_db)):
    # Fetch history for the last 7 days
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    history = db.query(models.CurrencyHistory).filter(
        models.CurrencyHistory.timestamp >= seven_days_ago
    ).order_by(models.CurrencyHistory.timestamp.asc()).all()
    
    # Format the timestamp for the response to match the expected format string
    return [{"currency": h.currency, "rate": h.rate, "timestamp": h.timestamp.isoformat()} for h in history]

app.mount("/", StaticFiles(directory="backend/static", html=True), name="static")

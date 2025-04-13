from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4

class CardCondition(Enum):
    RAW = "Raw"
    PSA_9 = "PSA 9"
    PSA_10 = "PSA 10"

class BaseModel(BaseModel):
    """Base model for all models in the application"""
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return self.model_dump()

class User(BaseModel):
    """User model"""
    email: str
    username: str
    display_name: str
    collections: List[str] = []
    preferences: Dict[str, Any] = {}
    photo_url: Optional[str] = None
    is_active: bool = True
    last_login: Optional[datetime] = None

class Card(BaseModel):
    """Card model"""
    player_name: str
    year: int
    card_set: str
    card_number: str
    condition: str
    grade: Optional[str] = None
    value: float = 0.0
    purchase_price: float = 0.0
    purchase_date: Optional[datetime] = None
    photo: Optional[str] = None
    tags: List[str] = []
    notes: Optional[str] = None

class Collection(BaseModel):
    """Collection model"""
    name: str
    description: Optional[str] = None
    user_id: str
    cards: List[str] = []
    is_public: bool = False
    total_value: float = 0.0
    tags: List[str] = []

class DisplayCase(BaseModel):
    """Display case model"""
    name: str
    description: Optional[str] = None
    user_id: str
    cards: List[Dict[str, Any]] = []
    tags: List[str] = []
    total_value: float = 0.0
    likes: int = 0
    views: int = 0
    is_public: bool = False
    last_updated: Optional[datetime] = None

class UserSubscription(BaseModel):
    """User subscription model"""
    user_id: str
    plan: str = "free"
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_status: str = "active"
    current_period_end: Optional[datetime] = None
    features: List[str] = []

class UserUsage(BaseModel):
    """User usage statistics model"""
    user_id: str
    card_count: int = 0
    display_case_count: int = 0
    daily_search_count: int = 0
    last_search_reset: Optional[datetime] = None
    last_updated: Optional[datetime] = None

class UserProfile(BaseModel):
    """User profile model"""
    display_name: str
    email: str
    preferences: Dict[str, Any] = Field(default_factory=dict)
    collections: List[str] = Field(default_factory=list)  # List of collection IDs

class SubscriptionHistory(BaseModel):
    """Subscription history model"""
    user_id: str
    event_type: str  # e.g., 'subscription_created', 'subscription_updated', 'subscription_cancelled'
    plan: str
    amount: float = 0.0
    status: str
    event_time: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict) 
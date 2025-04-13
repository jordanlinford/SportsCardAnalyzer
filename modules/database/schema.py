from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field

class UserSubscription(BaseModel):
    user_id: str
    plan: str  # 'free', 'basic', 'premium'
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_status: str  # 'active', 'canceled', 'past_due'
    current_period_end: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class UserUsage(BaseModel):
    user_id: str
    card_count: int = 0
    display_case_count: int = 0
    daily_search_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.now)

class SubscriptionHistory(BaseModel):
    user_id: str
    event_type: str  # 'subscription_created', 'subscription_updated', 'subscription_canceled'
    plan: str
    amount: float
    status: str
    event_time: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict] = None 
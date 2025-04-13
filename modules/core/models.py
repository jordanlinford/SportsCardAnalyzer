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
    """Base model class for all domain models"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        data = self.dict()
        data['created_at'] = data['created_at'].isoformat()
        data['updated_at'] = data['updated_at'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create model from dictionary"""
        if 'created_at' in data:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)
    
    def update(self, **kwargs) -> None:
        """Update model fields"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()

class Card(BaseModel):
    """Card model representing a sports card"""
    player_name: str
    year: int
    card_set: str
    card_number: str
    variation: str = ""
    condition: CardCondition = CardCondition.RAW
    purchase_price: float = 0.0
    purchase_date: datetime = Field(default_factory=datetime.utcnow)
    current_value: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    notes: str = ""
    photo: str = ""
    roi: float = 0.0
    tags: List[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert card to dictionary format for storage."""
        data = super().to_dict()
        data.update({
            'player_name': self.player_name,
            'year': self.year,
            'card_set': self.card_set,
            'card_number': self.card_number,
            'variation': self.variation,
            'condition': self.condition.value,
            'purchase_price': self.purchase_price,
            'purchase_date': self.purchase_date.isoformat(),
            'current_value': self.current_value,
            'last_updated': self.last_updated.isoformat(),
            'notes': self.notes,
            'photo': self.photo,
            'roi': self.roi,
            'tags': self.tags
        })
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Card':
        """Create card from dictionary format."""
        # Convert string dates back to datetime objects
        if isinstance(data.get('purchase_date'), str):
            data['purchase_date'] = datetime.fromisoformat(data['purchase_date'])
        if isinstance(data.get('last_updated'), str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        
        # Convert condition string to enum
        if isinstance(data.get('condition'), str):
            data['condition'] = CardCondition(data['condition'])
        
        return cls(**data)

class Collection(BaseModel):
    """Collection model representing a group of cards"""
    name: str
    description: Optional[str] = None
    cards: List[str] = Field(default_factory=list)  # List of card IDs
    tags: List[str] = Field(default_factory=list)
    is_public: bool = False

class UserProfile(BaseModel):
    """User profile model"""
    display_name: str
    email: str
    preferences: Dict[str, Any] = Field(default_factory=dict)
    collections: List[str] = Field(default_factory=list)  # List of collection IDs 